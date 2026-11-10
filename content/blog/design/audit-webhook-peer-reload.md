---
title: "Audit Webhooks After a Peer Reload"
linkTitle: "Audit Webhook Peer Reload"
date: 2026-11-04
lastmod: 2026-11-10
author: "PGSTY SILO Maintainers"
summary: >
  Why a runtime change to audit_webhook leaves every server except the one that served it with a webhook target whose worker has already exited, which other subsystems share the defect, and why building logger targets on the server context is the minimum complete repair.
tags: [Design, Audit, Logging, Configuration, Operations]
weight: 10
draft: false
url: "/blog/design/audit-webhook-peer-reload/"
---

This record covers [issue #259](https://github.com/pgsty/silo/issues/259), reported by Henrik Feldt, evaluated against main at [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc). The fix completes earlier, uncommitted maintainer work. It adds the Kafka call site, a handoff of records queued in a target that never started, and Kafka test coverage.

**Status:** Shipped in [SILO Server 20261109](/blog/release/silo-20261109/) (`d998292387cc`).

## Short answer {#tldr}

The report is correct, and a focused test reproduces it. When an administrator changes `audit_webhook` at runtime, the server that receives the request applies the change with the process context. Every other server applies it in its peer reload handler, under a 30-second context that is cancelled as soon as the handler returns. The HTTP webhook target ties its only queue worker to the context it was initialized with, and with `queue_dir` its disk replay as well. On every server but one, the new target therefore stops working right after it is created. Its records wait in memory until `queue_size` is reached, and every record after that is dropped with `log buffer full`. Nothing restarts the worker. Restarting the affected servers is the reliable recovery, because startup builds the targets with the process context. A later change served by an affected server revives that server, but stops the targets on the others again.

The same defect affects `logger_webhook`, with or without `queue_dir`, and `audit_kafka` when `queue_dir` is set. No other dynamic subsystem binds long-lived work to the reload context.

The repair has three parts:

{.steps}
1. **Process context for the targets.** `applyDynamicConfigForSubSys` builds logger targets with the process context (`GlobalContext`) at its three logger call sites. Startup, the serving node, and the peers all apply configuration through this one function. The reload context is still used for logging.
2. **Queue store before the disk-queue worker.** The HTTP disk-queue worker starts only after its queue store has opened. Today the worker starts first. If the store cannot be opened, the worker stays alive without a store and crashes the server on the first record. This already happens at startup and on the serving node. Without this part, the first part would spread the crash to every server.
3. **Queued records follow the replacement.** With part 2, a target whose queue cannot be opened has no worker, and its records wait in memory. When a later reload replaces it, `Cancel` now hands those records to the replacement instead of discarding them, as far as the shared handoff buffer has room.

## Classification {#assessment}

| Aspect               | Assessment                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nature               | Context-lifetime defect in the peer configuration reload: long-lived logger targets are tied to a context that ends with the request. Inherited from upstream; not a regression in a published SILO release.                                                                                                                                                                                                                                       |
| Affected deployments | More than one server, and a runtime `mc admin config set` or `mc admin config reset` of `audit_webhook` or `logger_webhook` (with or without `queue_dir`), or of `audit_kafka` with `queue_dir`. A `subnet` proxy change that also updates `logger_webhook` goes through the same path.                                                                                                                                                            |
| Not affected         | Single-server deployments; targets that were present at startup and never changed at runtime; the server that served the admin request; `audit_kafka` without `queue_dir`; every other dynamic subsystem ([sweep](#sweep)).                                                                                                                                                                                                                        |
| Severity             | High. Audit records are dropped on all servers but one, until those servers restart or serve a later change themselves. The admin command reports success and S3 requests succeed; the drops show only in the server log and the logger metrics, so the gap tends to surface in an audit review rather than in operations. Where the audit webhook is part of a compliance control, the trail for that period is incomplete and cannot be rebuilt. |
| Reachability         | One routine admin command. A change to one target rebuilds every enabled target of that subsystem, so all of them stop on the other servers, not only the one that was named.                                                                                                                                                                                                                                                                      |
| Release urgency      | Release blocker for `SILO Server 20261109` (shipped in `RELEASE.2026-11-09T00-00-00Z`). Audit loss is not reported to the admin or S3 client and lasts until the affected servers restart or serve a later change themselves, while the change is small and stays off the S3 data path.                                                                                                                                                            |
| Remaining effort     | Complete; shipped in `SILO Server 20261109` (`d998292387cc`).                                                                                                                                                                                                                                                                                                                                                                                      |
{.wide .expand}

## When it happens {#trigger}

{.steps}
1. `mc admin config set ALIAS audit_webhook:NAME enable=on endpoint=…` reaches server A. A validates and saves the configuration. It applies the change through `applyDynamic`, which calls `applyDynamicConfigForSubSys` with `GlobalContext`. It then asks every peer to reload the subsystem (`SignalConfigReload`).
2. On each peer, `SignalServiceHandler` handles `serviceReloadDynamic`. It reads the saved configuration and calls `applyDynamicConfigForSubSys` under `context.WithTimeout(context.Background(), 30*time.Second)` with a deferred `cancel`.
3. `updateHTTPTargets` creates a new target for every enabled webhook of the subsystem and initializes each one with that context. It then swaps the target list and cancels the old targets.
4. The handler returns, and the context is cancelled. The new target's main worker returns from `startQueueProcessor`. Any additional worker shares the same context and is asked to stop as well, and nothing starts a new one.
5. Audit logging keeps calling `Send` on that server. `Send` accepts records into the target's channel until `queue_size` (default 100000) is reached. After that it returns `log buffer full`, and the server logs ``Unable to send audit event(s) to the target `NAME`: log buffer full``.

The reporter's node metrics show the pattern, 7.5 hours after a `config set` that ran on server 0 of three:

| Server                 | `target_queue_length` | `failed_messages` | `total_messages` |
| ---------------------- | --------------------- | ----------------- | ---------------- |
| 0 (served the request) | 0                     | 4                 | 2,097,356        |
| 1                      | 100000                | 674,917           | 774,917          |
| 2                      | 100000                | 712,215           | 812,215          |
{.wide .expand}

In this report, `total_messages` minus `failed_messages` equals the queue length on servers 1 and 2, which is consistent with nothing having been sent from them.

Three variants behave as follows:

- **HTTP webhook with `queue_dir`.** The worker that writes records to the disk queue is the same worker, and the disk replay stops with the same context. New records never reach the disk; they fill the memory queue as above. Records that were on disk before the change stay there; after a restart they are replayed once the endpoint is reachable. Records in the memory queue are lost when the server restarts.
- **Kafka with `queue_dir`.** `Send` writes straight to the disk queue, but the replay goroutine started by `initQueueStore` stops with the context. Records pile up on disk until `queue_size`, then `Send` fails with `the maximum store limit reached`. After a restart the replay sends what is on disk, once the brokers are reachable. The Kafka target's queue-length metric counts only its in-memory channel, which this mode does not use, and its message counters move only when the replay sends. The metrics therefore stay flat.
- **Kafka without `queue_dir`.** Not affected. The broker connection is made without the context, and the sender loop does not watch it.

## Root cause {#root-cause}

The `ctx` argument of a logger target's `Init` does two jobs. It is the context of the initialization call, and it is also the lifetime of the target's goroutines. `initMemoryStore` and `initDiskStore` derive the worker context with `context.WithCancel(ctx)` and keep the cancel function for `Cancel`. `startQueueProcessor` returns when that context is done. A target therefore stops working when `Cancel` is called or when the caller's context ends, whichever comes first. Either event only requests the shutdown; [Residual limits](#limits) lists the cases in which it does not complete promptly.

At startup (`lookupConfigs`) and on the serving node, the caller's context is `GlobalContext`. Targets then live until they are replaced or the server shuts down, which is the intended lifetime. On a peer, the caller's context ends when the RPC handler returns, a few milliseconds after the target is created.

The 30-second limit does not protect anything here. Within `applyDynamicConfigForSubSys`, the context is used for log calls, for the configuration lookup (which also uses it only for logging), and for target `Init`. HTTP `Init` does no network I/O: it starts a goroutine and, with `queue_dir`, opens a local directory. The Kafka target connects to the brokers in `init()`, which takes no context and is bounded by the client's own dial and metadata timeouts.

## Subsystem sweep {#sweep}

The same reload path handles every subsystem in `config.SubSystemsDynamic`. The question for each one is whether `applyDynamicConfigForSubSys` creates a goroutine or object that keeps the context after the call returns.

| Subsystem                                                                       | What the reload does                                                                                             | Verdict                                                                            |
| ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `logger_webhook`                                                                | `logger.UpdateHTTPWebhooks(ctx, …)` → `Init(ctx)`: queue worker, and with `queue_dir` the disk replay            | **Affected**, with and without `queue_dir`                                         |
| `audit_webhook`                                                                 | `logger.UpdateAuditWebhooks(ctx, …)`, same path                                                                  | **Affected**, with and without `queue_dir`                                         |
| `audit_kafka`                                                                   | `logger.UpdateAuditKafkaTargets(ctx, …)` → `Init(ctx)` → `initQueueStore`: disk replay started with `ctx.Done()` | **Affected with `queue_dir`**; without it the sender loop does not use the context |
| `api`                                                                           | `globalAPIConfig.init`, `setRemoteInstanceTransport`                                                             | Not affected: values and a transport, no context                                   |
| `ilm`                                                                           | `UpdateWorkers`, `ResizeWorkers`                                                                                 | Not affected: the workers use the transition and expiry states' own contexts       |
| `scanner`                                                                       | atomic stores, `scannerSleeper.Update`                                                                           | Not affected                                                                       |
| `subnet`                                                                        | `Update`, `ApplyEnv`                                                                                             | Not affected itself; a proxy change can also re-apply `logger_webhook`             |
| `compression`, `heal`, `batch`, `storage_class`, `drive`, `browser`, `callhome` | swap a configuration value under a lock                                                                          | Not affected                                                                       |
{.wide .expand}

Notification and Lambda targets are not dynamic subsystems on main.

Two parts of the issue text are narrower than written. The peer handler's whole-configuration branch (`applyDynamicConfig`) uses the same context, but no current admin path sends a reload without a subsystem. `mc admin config import` saves the configuration and needs a restart; it does not signal the peers.

## Where the behavior came from {#history}

### Provenance {#provenance}

**Introduced by upstream MinIO, not by SILO.** Every ingredient is an upstream commit that is an ancestor of the SILO fork point ([`27742d469`](https://github.com/pgsty/silo/commit/27742d469), 2025-12-03), and no SILO commit has changed the functions involved. The same code is in the last upstream release before the fork, `RELEASE.2025-10-15T17-29-55Z`, in the archived upstream `master`, and in every SILO release from `RELEASE.2025-12-03T12-00-00Z` through `RELEASE.2026-10-26T00-00-00Z`. We compared the code on each tag; the worker-before-store order, the context-bound replay, and the 30-second context are identical on all of them.

The defect needs a reload context that ends with the handler, and logger targets whose goroutines live as long as the context passed to `Init`. These come from different commits:

| Ingredient                                                                                                                                   | Commit (PR)                                                                                                                                                                                                                                                 | Date                   | First upstream release                                         |
| -------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- | -------------------------------------------------------------- |
| The peer reload applies a subsystem under the request's context, which ends when the handler returns.                                        | [`a89612549`](https://github.com/pgsty/silo/commit/a89612549) ([#11018](https://github.com/minio/minio/pull/11018)); per-subsystem form [`040ac5cad`](https://github.com/pgsty/silo/commit/040ac5cad) ([#14928](https://github.com/minio/minio/pull/14928)) | 2020-12-04; 2022-05-16 | `RELEASE.2020-12-10T01-54-29Z`; `RELEASE.2022-05-19T18-20-59Z` |
| Same lifetime after the grid conversion: `serviceReloadDynamic` creates a 30-second context with a deferred `cancel`.                        | [`e06168596`](https://github.com/pgsty/silo/commit/e06168596) ([#19004](https://github.com/minio/minio/pull/19004))                                                                                                                                         | 2024-02-19             | `RELEASE.2024-02-24T17-11-14Z`                                 |
| Logger and audit webhooks, and audit Kafka, become reloadable at run time.                                                                   | [`28f188e3e`](https://github.com/pgsty/silo/commit/28f188e3e) ([#14289](https://github.com/minio/minio/pull/14289)), [`3934700a0`](https://github.com/pgsty/silo/commit/3934700a0) ([#14390](https://github.com/minio/minio/pull/14390))                    | 2022-02-17, 2022-02-24 | `RELEASE.2022-02-17T23-22-26Z`, `RELEASE.2022-02-24T22-12-01Z` |
| `Init` takes a context. The disk replay of the HTTP target and of Kafka (`initQueueStore`) stops with it, and the HTTP worker sends with it. | [`57acacd5a`](https://github.com/pgsty/silo/commit/57acacd5a) ([#17121](https://github.com/minio/minio/pull/17121))                                                                                                                                         | 2023-05-09             | `RELEASE.2023-05-18T00-05-36Z`                                 |
| The HTTP queue worker returns when the `Init` context ends.                                                                                  | [`1fc4203c1`](https://github.com/pgsty/silo/commit/1fc4203c1) ([#19275](https://github.com/minio/minio/pull/19275))                                                                                                                                         | 2024-03-25             | `RELEASE.2024-03-26T22-10-45Z`                                 |
| The disk-queue worker starts before the queue store opens.                                                                                   | [`ba54b39c0`](https://github.com/pgsty/silo/commit/ba54b39c0) ([#19854](https://github.com/minio/minio/pull/19854))                                                                                                                                         | 2024-06-01             | `RELEASE.2024-06-04T19-20-08Z`                                 |
{.wide .expand}

What each step changed:

- **Before #17121 the defect could not occur.** `Init` and the HTTP worker took no context, so the peer's context could not stop a target, even though the reload already ran under a request context.
- **From #17121 (`RELEASE.2023-05-18T00-05-36Z`)** the reload context reaches the targets. With `queue_dir`, the disk replay of the HTTP target and of Kafka stops when the handler returns, which is the Kafka-with-`queue_dir` case in this record. The HTTP worker without `queue_dir` sends with the same context, so its sends fail with `context canceled` instead of being queued.
- **From #19275 (`RELEASE.2024-03-26T22-10-45Z`)** the HTTP worker returns when the context ends. This is the symptom in the report: records wait in memory until `queue_size` and are then dropped with `log buffer full`.
- **#19854 (`RELEASE.2024-06-04T19-20-08Z`)** fixed a crash that, by its own message, the #19275 refactor introduced. It moved the store opening into `initDiskStore` but kept the worker start in front of it. That order is the crash described under [Proposed fix](#fix). On peers it was mostly hidden, because the worker usually exited with the reload context before the first record arrived.
- **#19004 changed nothing about the lifetime.** The old request context also ended when the handler returned. The 30-second limit protects nothing, as the [root cause](#root-cause) section shows.

**SILO changes.** No SILO commit touched the peer reload case in `SignalServiceHandler`, `initDiskStore`, the HTTP worker, the Kafka `initQueueStore`, or the logger branches of `applyDynamicConfigForSubSys`. SILO commits near this code did not introduce, widen, or narrow the defect:

- [`9b11dc946`](https://github.com/pgsty/silo/commit/9b11dc946) (2026-09-03) swapped the `minio/pkg` import path for `silo-pkg` in these files.
- [`011b0df5f`](https://github.com/pgsty/silo/commit/011b0df5f) (2026-10-23) set the default Kafka protocol version in the broker client setup, which takes no context.
- [`5cb900bfa`](https://github.com/pgsty/silo/commit/5cb900bfa) and [`079ebb192`](https://github.com/pgsty/silo/commit/079ebb192) (2026-09-07 and 2026-09-08) made registration of system targets idempotent and serialized. Only the console logger uses that path, not the webhook reload.
- [`77bdc4c0c`](https://github.com/pgsty/silo/commit/77bdc4c0c), [`7a060cab1`](https://github.com/pgsty/silo/commit/7a060cab1), and [`9b76a2167`](https://github.com/pgsty/silo/commit/9b76a2167) changed other subsystem branches of `applyDynamicConfigForSubSys` (callhome, and the ILM access-tier workers that were added and later removed).

**Evidence.** The presence of each ingredient on every tag, and the absence of SILO changes in these functions, were checked in the git history. The behavior between #17121 and #19275 comes from reading that code; we did not run those old versions. The current behavior is reproduced by the test described under [Verification](#verification).

Related: [PR #249](https://github.com/pgsty/silo/pull/249), which adds live reload for notification webhooks and is still open, builds its targets with `GlobalContext` for the same reason. The [IAM policy reload record](/blog/design/iam-policy-cancellation/) covers the opposite case, where request work must follow the request context.

## Options {#options}

### Option A: process context at the logger call sites {#option-a}

This is the chosen option. `applyDynamicConfigForSubSys` passes `GlobalContext` to the three logger target updates and keeps the caller's context for logging. Every entry point applies configuration through this function, so one change covers startup, the serving node, and the peers. The lifetime decision sits where the long-lived objects are created, whatever the caller passes. PR #249 follows the same pattern for notification targets.

### Option B: detach inside the logger package {#option-b}

`updateHTTPTargets`, or `Init`, could wrap the context with `context.WithoutCancel`, which protects every caller. It would also detach targets from `GlobalContext`, so they would no longer stop when shutdown cancels it. That changes shutdown behavior for targets built at startup, which is unrelated to this defect. It also leaves a `ctx` parameter whose cancellation is silently ignored. If the package is to own the lifetime, the parameter should go away instead (Option D).

### Option C: process context in the peer handler {#option-c}

`serviceReloadDynamic` could pass `GlobalContext` and keep the 30-second limit only for work that is actually bounded. Today that work does not exist ([root cause](#root-cause)), so this would also fix the defect. But it repairs the caller rather than the function that creates the long-lived objects. Any other caller with a short context, such as a test or a future handler, would fall into the same trap. It is an acceptable alternative, but not the preferred one.

### Option D: targets own their lifetime {#option-d}

Split `Init` into initialization under the caller's context and a start whose lifetime belongs to the target and ends only with `Cancel`. This is the right long-term shape. It changes the `logger.Target` interface and every implementation (HTTP, Kafka, console, the test logger). Closing this defect does not need it, so it remains a follow-up candidate.

### Questions behind the choice {#questions}

- **Did any `Init` rely on the 30-second limit?** No. HTTP `Init` does no network I/O, and Kafka's broker connection does not take the context. Before the March 2024 refactor, HTTP initialization pinged the endpoint with the context; it no longer does.
- **Do repeated reloads leak goroutines?** Not because of this change. On every reload, `updateHTTPTargets` points each old target at its replacement (`AssignMigrateTarget`), sizes the shared leftover buffer (`CreateOrAdjustGlobalBuffer`), starts the new targets, and then calls `Cancel` on the old ones in the background. `Cancel` marks the target closed, so later `Send` calls go to the replacement, if there is one. It cancels the target's own context, which asks the worker and the disk replay to stop, waits for the workers to hand their leftover records to the shared buffer, hands over any records still in the channel (part 3 of the fix), and closes the channel. The shutdown of old targets has always been owned by `Cancel`, not by the caller's context, so using `GlobalContext` adds no goroutine per reload. A review probe ran 100 consecutive reloads of idle targets followed by a disable, for both queue modes, and the goroutine count returned to its starting value; this does not cover shutdown under a backlog or failing disk writes. On main, the old target's worker on a peer is already gone, and the records that piled up after it stopped are discarded when the channel closes. That is why a second `config set` through the same server does not recover the peers. Pre-existing exceptions, unchanged by this fix, are described under [Residual limits](#limits).

## Proposed fix {#fix}

{.steps}
1. **Process context for logger targets.** In `applyDynamicConfigForSubSys`, pass `GlobalContext` to `logger.UpdateHTTPWebhooks`, `logger.UpdateAuditWebhooks`, and `logger.UpdateAuditKafkaTargets`. Error reporting keeps using the caller's context. The earlier candidate fix covered the two HTTP call sites; the Kafka call site, which has the same defect when `queue_dir` is set, completes it.
2. **Open the queue store before starting the disk-queue worker.** `initDiskStore` currently starts the main worker, then opens the queue store. If opening fails, for example because `queue_dir` cannot be created or is not a directory, `Init` returns an error. The target stays registered, though, and its worker keeps running with no store. On the first record, the worker calls `PutMultiple` on the missing store, and the server panics. Today this happens at startup and on the serving node, where the context stays alive. On peers, the worker usually exited with the reload context first, which mostly hid the crash; it could still happen when the worker took a record before the reload context ended. Part 1 on its own would therefore turn the silent drop into a crash on every server. The fix opens the store first. On failure, it cancels the derived context and returns without starting a worker. On success, it assigns the store and then starts the worker and the replay. This also removes a data race, in which a worker could read the store field while `Init` was still setting it when an earlier target had left records in the shared buffer. A failed `Init` no longer leaves a worker behind.
3. **Hand queued records to the replacement.** With part 2, a target whose queue store failed to open has no worker. Records sent to it wait in its channel, up to `queue_size`. Nothing retries the initialization: the operator repairs `queue_dir` and applies the configuration again, and that reload builds a replacement target. Only a worker hands records over to the replacement, so `Cancel` would close the channel and discard them. `Cancel` now moves the records still in the channel to the shared buffer that the replacement reads. It does this after its `wg.Wait()` call for the workers returns and before it closes the channel, holding the channel lock and the buffer-map lock, with sends that never wait for room. If the shared buffer is full, the rest is dropped, as in the worker's own handoff. It also covers records that arrive after a worker's final drain. A single failed target replaced by a working one hands over all of its records; when several failed targets are replaced in quick succession, the buffer can still run out of room (see [Residual limits](#limits)).
4. **Regression test.** `TestDynamicWebhookOutlivesConfigContext` covers `audit_webhook` and `logger_webhook`, each with a memory queue, a disk queue, and a disk queue that cannot be opened, and `audit_kafka` with and without `queue_dir`. Each case applies the subsystem through `applyDynamicConfigForSubSys` under a short context, cancels it as the peer handler does, sends a record, and requires delivery. The Kafka cases use the mock broker of the Kafka client library and require a produce request after the reload context has ended; without `queue_dir` Kafka is not affected, so that case is a control. In the unopenable case, the record must stay queued while the store is unavailable. The test then repairs the directory and applies the configuration again, and the replacement target must deliver the record. Each case runs in a child process, without the logger and audit environment variables, so the global target registries do not leak between cases.

## Why it is sufficient and necessary {#sufficiency}

**Sufficient.** Every logger webhook or Kafka target in a running server is built by `applyDynamicConfigForSubSys`: at startup through `lookupConfigs` and `applyDynamicConfig`, on the serving node through `applyDynamic`, and on peers through `serviceReloadDynamic`. The only other callers of the three update functions are tests. With part 1, every path builds targets with the process context, so targets on peers get the same lifetime as on the serving node. The sweep finds no other subsystem that ties long-lived work to the reload context. Old targets are still stopped by `Cancel`, which owns their shutdown, within the limits listed under [Residual limits](#limits).

**Necessary.** Each part closes a path that otherwise stays open:

- Each of the three call sites starts goroutines from the context: the HTTP queue worker, the HTTP disk replay, and the Kafka disk replay. Leaving any of them out leaves that variant broken on peers.
- Without part 2, a `queue_dir` that cannot be opened crashes any server whose worker receives a record. With part 1, the worker lives on every server, so every server crashes on its first audit or log record, not mostly the serving node.
- Without part 3, repairing such a `queue_dir` and applying the configuration again discards every record the failed target accepted.
- Without the test, nothing keeps the peer path from drifting away from the serving node again.

**Deliberately excluded.**

- The peer handler keeps its 30-second context. It is still correct for the logging it covers.
- No `context.WithoutCancel` in the logger package, and no change to the `logger.Target` interface (Options B and D).
- Pre-existing behaviors that do not cause this symptom are left for separate issues. They are listed under [Residual limits](#limits).

## Cost and compatibility {#cost}

- No API, configuration, metric, storage-format, or dependency change.
- Targets on peers get the same lifetime as on the server that served the admin request. The pre-existing replacement and shutdown limits below therefore now apply to peers as well.
- One visible change: a `queue_dir` that cannot be opened no longer crashes the server at startup or on the serving node. The target stays registered and its error is logged (`Unable to update audit webhook targets: …`). Records wait in memory until `queue_size`, then are dropped with `log buffer full`, just as for any target that cannot send. Once the directory is repaired and the configuration applied again, the replacement takes over the waiting records, within the room of the shared handoff buffer.
- Rollback restores the old behavior. No state needs migration in either direction.

## Operator guidance {#operators}

On releases before `SILO Server 20261109`:

- **After a runtime change, restart the other servers.** After any `mc admin config set` or `mc admin config reset` that touches `audit_webhook`, `logger_webhook`, or `audit_kafka` with `queue_dir`, restart every server except the one that served the command. A `subnet` proxy change counts too when logger webhooks are configured. If a load balancer hides which server served the command, point the `mcli` alias at one server's own address for configuration changes, or restart all servers one at a time.
- **Unchanged targets are safe.** Targets that were present at startup, from environment variables or from the saved configuration, are built with the process context. They are not affected until the next runtime change.
- **Lost records stay lost.** Records dropped with `log buffer full` cannot be recovered. Records still in a memory queue are lost when the server restarts. With `queue_dir`, records that were on disk before the change are replayed after the restart, once the endpoint is reachable.

To detect the condition, read node metrics on each server separately:

- `minio_audit_target_queue_length` for the target (`target_id` such as `audit_http_0`, or `sys_http_0` for a logger webhook) climbs toward `queue_size` on some servers while it stays near zero on the serving one.
- `minio_audit_failed_messages` rises, and `minio_audit_total_messages` minus `minio_audit_failed_messages` typically stays flat at the queue length.
- The server log shows ``Unable to send audit event(s) to the target `NAME`: log buffer full``.
- For Kafka with `queue_dir`, the metrics stay flat. Watch the number of files under the target's queue directory and the `the maximum store limit reached` message instead.

The webhook online gauge usually stays at 0 for the new target on an affected server. It shows 0 when the endpoint is down as well, so it can only confirm the other signals.

## Residual limits {#limits}

These limits are pre-existing and are not caused by the reload context. Each exists today on the serving node and for targets built at startup; with the fix, peers behave the same. Each needs its own change.

- **Lost records are not recovered.** The fix prevents losses caused by the reload context. It does not recover records already dropped, and it does not repair the other handoff and shutdown losses below.
- **A full disk queue can still block an old target's shutdown.** With `queue_dir`, the default `max_retry=0`, and a disk queue that is already full when the target is replaced, the old worker keeps retrying the disk write and does not check its context. Its `Cancel` does not finish while the writes keep failing. The retry wait should honor the context, and the pending batch must then be handed over.
- **Records a worker has taken but not delivered are lost on replacement.** Without `queue_dir`, a worker encodes records into its current batch. When the target is replaced while that batch is unsent, for example while the endpoint is down, the batch is neither delivered nor handed over.
- **Old and new disk queues overlap during replacement.** Both targets open the same directory, each with its own index. A record that the old target writes after the replacement has opened the directory is invisible to the replacement's replay. If the old replay stops before sending it, the record stays on disk until the directory is opened again, for example at the next restart. Both replays can also send the same record twice. Kafka targets use one fixed directory name under `queue_dir`, so two Kafka targets with the same `queue_dir` share it.
- **A worker can start after an immediate `Cancel`.** A worker registers with the wait group only once it runs, so a `Cancel` right after `Init` may stop waiting before the worker exists. Reads of the channel field by workers and later updates of the worker start time are not synchronized either. The race detector reports these on main as well.
- **The shared handoff buffer can run out of room.** It is sized when a replacement is created, from the replaced target's queue and what the buffer already holds. Records that earlier replaced targets have not yet handed over are not counted. When several failed targets are replaced in quick succession, a review probe delivered 116 of 200 queued records; without the handoff in `Cancel` it delivered none.
- **Kafka shutdown does not release every client.** Without `queue_dir`, `Init` builds a client and the first send builds a second one; the first is never closed. With `queue_dir`, an initialization still running in the replay can publish a client after `Cancel` has returned.
- **A Kafka target without `queue_dir` can still start without a sender.** If the brokers are unreachable when the target is initialized, `Init` returns before it starts the sender loop, and the target fills its channel until `log buffer full`. This is independent of the context and is also left for a separate issue.

## Verification {#verification}

Executed on main at 69fcf50cd in disposable worktrees:

- With the fix, `go test ./cmd -run '^TestDynamicWebhookOutlivesConfigContext$'` passes all eight cases, also under the race detector. The full `./cmd` suite, `./internal/logger/...`, and `./internal/store/...` pass, the last two also under the race detector. `go vet ./cmd` is clean.
- With only the test applied and the production changes reverted, seven cases fail. The memory-queue and disk-queue cases report that the webhook stopped after the reload returned. Kafka with `queue_dir` never sends a produce request. The unopenable-queue cases either lose the record when the target is replaced or crash with a nil pointer dereference at the `PutMultiple` call in `startQueueProcessor`, from a worker started by `initDiskStore`; which one happens depends on whether the worker takes the record before the reload context ends. Kafka without `queue_dir` passes on both trees, as a control.
- Ablations, each with the rest of the fix in place. Without the Kafka call site, only the Kafka case with `queue_dir` fails. Without the store-before-worker order, both unopenable-queue cases crash at `PutMultiple`. Without the handoff in `Cancel`, both unopenable-queue cases lose the record when the configuration is applied again.
- The adversarial review added probes. With 32 records already in the shared buffer, a disk target initialized under the race detector without a report; main panics at `PutMultiple`. A hundred reloads of idle targets followed by a disable left the goroutine count unchanged. A Kafka `Init` against an unreachable broker took about 10 seconds despite a 10-millisecond context, so the reload context bounded nothing there. Probes on main and on the fix reproduced four of the [residual limits](#limits): the blocked shutdown with a full disk queue, the lost unsent batch, the overlapping disk queues, and the worker start race. The Kafka client shutdown was confirmed in the code and with a controlled interleaving.

Established by reading the code, not executed:

- The Kafka metrics behavior with `queue_dir`, the subsystem sweep, and the history.

**Cluster acceptance.** On 2026-11-05 four server processes ran on one host, with two drives each and a memory queue. `audit_webhook` was set twice at runtime through the first server, and then every server received three `HEAD` requests. On `69fcf50cd` only the first server's three records arrived, and `minio_audit_target_queue_length` stayed at 3 on each of the other three servers. With the fix all twelve records arrived, and the queue length was 0 on every server. The disk queue and `audit_kafka` were not part of this run: servers on one host cannot keep separate `queue_dir` paths under one cluster-wide setting, and no broker was available. The tests above cover both.

**Integration and release verification.** The fix was integrated for `SILO Server 20261109` on top of #278 and #281 together with the lock-domain, heal dry-run, #285, `delete-all`, and Console fixes without conflicts. Local runs passed the full `go test -tags kqueue,dev -p 4 ./cmd/... ./internal/...` suite and CI race-detector selections (including `TestDynamicWebhookOutlivesConfigContext` in the Ubuntu CI race workflow). An adversarial review of the combined branch checked lock domains, cleanup paths, and purge against restore with executed probes and found no defects. Release commit `d998292387cc` (`RELEASE.2026-11-09T00-00-00Z`) passed Go CI (including the untagged Ubuntu `CGO_ENABLED=0 MINIO_API_REQUESTS_MAX=10000 go test ./cmd/ -count=1 -timeout 30m` gate), VulnCheck, Test Release Pipeline, and release build verification.

## Review history {#review}

| Round                       | Outcome                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Adversarial review, round 1 | Approved with nits; no production defect introduced by the change was found. Six pre-existing defects were reported. One was fixed: records queued in a target that never started were discarded when a reload replaced it (part 3, with the test changed to recover through a second configuration application). The other five are listed under [Residual limits](#limits). The test children now run without the logger and audit environment variables. Corrections to this record were applied: restart is not the only recovery, the drops are visible in logs and metrics, the peer crash was mostly but not always hidden, and the shutdown and delivery claims were qualified. |
| Adversarial review, round 2 | Approved with nits, covering the handoff in `Cancel` and the reworked test. The handoff delivered every record of a single replaced target exactly once, kept records across concurrent buffer resizes, and survived repeated and concurrent `Cancel` calls; ordinary reloads with the endpoint up and down showed no new loss or duplication. One remaining loss was documented: rapid successive replacements of failed targets can exhaust the shared buffer (Residual limits). The test now cleans up only the last target. Further wording corrections were applied.                                                                                                               |
| Adversarial review, round 3 | Approved with nits. The test cleanup and the corrected wording were confirmed; two remaining phrases were made precise.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
{.wide .expand}

## References {#references}

- Issue: [#259](https://github.com/pgsty/silo/issues/259)
- Related notification webhook live reload: [PR #249](https://github.com/pgsty/silo/pull/249)
- Upstream history: [minio/minio#19004](https://github.com/minio/minio/pull/19004), [minio/minio#19275](https://github.com/minio/minio/pull/19275), [minio/minio#19854](https://github.com/minio/minio/pull/19854)
- Related context design: [IAM Policy Reloads: Lock Scope, Cancellation, and Time Budgets](/blog/design/iam-policy-cancellation/)
- Configuration: [Publish Server or Audit Logs to an External Service](/operations/monitoring/minio-logging/)

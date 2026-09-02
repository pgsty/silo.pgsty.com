---
title: "When the Total Is Unknown: Folder Download Progress"
linkTitle: "Folder Download Progress"
date: 2026-08-23
lastmod: 2026-09-02
author: "Ruohang Feng"
description: "PRD for replacing NaN% with truthful indeterminate progress when SILO Console downloads a streamed folder ZIP, without changing the server API or ordinary file downloads."
tags: [Design, Console, Download]
weight: 20
url: "/blog/design/dir-percentage/"
---

> **Status**: Shipped in SILO Console 2.2.0 (`16960f7ab`); the server embeds it since its Console pin was updated (`4d6e1ea8e`) · **Priority**: P1 · **Owner**: [`pgsty/silo-console`](https://github.com/pgsty/silo-console) · **Related issue**: [`pgsty/silo#62`](https://github.com/pgsty/silo/issues/62) · **PRD review**: Claude Fable 5 (`xhigh`) — **APPROVE** · **Implementation review**: Claude Fable 5 (`xhigh`), 2026-08-23 — **APPROVE**, no P0/P1/P2 findings

SILO Console shows `NaN%` in Downloads / Uploads while downloading a folder. The ZIP normally keeps streaming and the stored objects are intact, but the progress bar has crossed from "unknown" into an invalid determinate state. Users see a full-looking bar, assume the transfer failed or finished, and retry it.

The proposed repair is intentionally narrow:

> A download may enter determinate mode only when it has a finite, positive total measured in bytes applicable to that response. Without such a total, it remains indeterminate until completion, failure, or cancellation.

The server keeps streaming ZIPs. Ordinary files keep their percentages. The frontend gains one safe calculation boundary, reuses its existing indeterminate renderer, and closes one missing cancellation transition. This record defines why that is both sufficient and the smallest truthful fix.

## The observed failure {#failure}

The defect is present in the current `silo-console v2.1.1`, which is embedded by Silo `RELEASE.2026-08-06T00-00-00Z`.

Reproduction:

1. Put several objects below a prefix such as `folder/`.
2. Stay in the parent listing, select `folder/`, and click **Download**.
3. Open **Downloads / Uploads** before the transfer finishes.
4. The row displays `NaN%`; the ZIP request continues.

The runtime check used a prefix containing about 88.7 MiB and throttled Chromium to preserve the observation window. Two independent downloads produced the same `NaN%` state.

This is a frontend correctness bug. It is not evidence of corrupted objects, an altered disk format, or a failed S3 `GET`.

## What is actually happening {#root-cause}

The visible `NaN%` is the end of a contract mismatch across three layers.

### A prefix has no object size {#prefix-size}

S3 folders are common prefixes, not stored directory objects. In the listing model, a prefix ends in `/` and carries `size=0`. The Console already renders that size as `-`, correctly treating it as not applicable.

The generated API model marks `size` as `omitempty`, so logical zeroes are absent from listing JSON. The single-selection thunk nevertheless passes `object.size` straight into the download helper: a prefix or zero-byte object therefore supplies `undefined` at runtime (while synthetic prefix records may supply `0`). Neither value is a valid denominator.

### A streamed ZIP has no known wire length {#streamed-zip}

The server recognizes the trailing `/`, recursively lists the objects, then connects a `zip.Writer` to an `io.Pipe`. Objects are read, deflated, and copied to the HTTP response as the archive is produced.

That behavior is desirable: the server can send the first bytes without holding the complete archive in memory or on disk. Its consequence is equally deliberate: the final compressed byte length does not exist when headers are sent, so the response has `Content-Type: application/zip` and a filename, but no `Content-Length`.

The sum of source object sizes is not a substitute. Source sizes are uncompressed bytes; `ProgressEvent.loaded` counts response bytes after ZIP compression and framing. They are different units.

### A progress event does not imply a computable percentage {#progress-event}

The client currently computes every event as:

```ts
Math.round((event.loaded / fileSize) * 100)
```

For a prefix, the denominator is zero or absent. Depending on the value and event, JavaScript produces `NaN` (`loaded / undefined` or `0 / 0`) or `Infinity` (positive bytes divided by zero).

The progress callback then writes that non-finite value into Redux and sets `waitingForFile=false`. That second operation is the decisive state error: the task leaves the existing indeterminate branch merely because an event arrived, not because the event contained a usable total. The determinate progress component receives the invalid value and renders an invalid label.

The complete chain is:

```text
common prefix: size = 0
        |
        v
download(..., fileSize = 0)
        |
        v
streamed deflated ZIP, no Content-Length
        |
        v
event.loaded / 0 => NaN or Infinity
        |
        v
invalid percentage enters Redux; waitingForFile becomes false
        |
        v
determinate ProgressBar renders NaN%
```

Ordinary non-empty files avoid the defect because the server can stat the object, sets `Content-Length`, and the list size is positive. If the browser emits a progress event for an empty response, a zero-byte file reaches the same arithmetic boundary as a prefix even though it is a real object; it therefore belongs in the regression contract.

## Product contract {#contract}

The UI needs one honest distinction:

- **Determinate** means both transferred bytes and total bytes are known in the same unit.
- **Indeterminate** means the request is active but the total is unknown.

This yields four load-bearing invariants:

```text
determinate  => total is finite and total > 0
determinate  => percentage is finite and 0 <= percentage <= 100
unknown total => indeterminate
terminal state => not indeterminate
```

These invariants are more general than `objectPath.endsWith("/")`: they cover prefixes, zero-byte files, malformed metadata, and any future unknown-length response without inventing object-type exceptions.

## Goals and non-goals {#scope}

### Goals {#goals}

1. A folder download never displays `NaN%`, `Infinity%`, or a fabricated percentage.
2. Unknown-length transfers use the existing indeterminate animation.
3. Known-length ordinary files retain their current percentage behavior.
4. Completion, failure, and cancellation always leave indeterminate mode.
5. A zero-byte file never produces a non-finite percentage and still reaches success.
6. No non-finite or out-of-range download percentage enters Redux.
7. The fix can ship in Console first and then be consumed by Silo as a dependency update.

### Non-goals {#non-goals}

- Do not pre-generate or buffer a complete ZIP on the server.
- Do not use the sum of uncompressed object sizes as network progress.
- Do not redesign the entire Object Manager state model.
- Do not route folders through the current immediately-completing `BrowserDownload` path.
- Do not solve the browser memory cost of `XMLHttpRequest.responseType="blob"` here.
- Do not change whether a cancelled row remains visible until the user clears it.
- Do not redesign mid-stream ZIP error signaling after HTTP headers have been sent.
- Do not modify the S3 API, Console API, object layout, or archive contents.

Those are legitimate follow-ups, but coupling them to this defect would enlarge risk without being necessary to restore truthful progress.

## The decision {#decision}

The minimum production repair has four parts.

### D1. Calculate only from a valid total {#d1}

Add a small pure function, separate from DOM and Redux side effects:

```ts
type DownloadProgressEvent = Pick<
  ProgressEvent,
  "loaded" | "lengthComputable" | "total"
>;

export const calculateDownloadPercent = (
  event: DownloadProgressEvent,
  objectSize: number,
): number | null => {
  let total: number | null = null;

  if (Number.isFinite(objectSize) && objectSize > 0) {
    total = objectSize;
  } else if (
    event.lengthComputable &&
    Number.isFinite(event.total) &&
    event.total > 0
  ) {
    total = event.total;
  }

  if (
    total === null ||
    !Number.isFinite(event.loaded) ||
    event.loaded < 0
  ) {
    return null;
  }

  return Math.min(
    100,
    Math.max(0, Math.round((event.loaded / total) * 100)),
  );
};
```

The source priority preserves compatibility:

1. A finite positive `objectSize` retains the current ordinary-file calculation.
2. If object size is unavailable but the browser declares the response length computable and supplies a finite positive `event.total`, use it.
3. Otherwise return `null`: no truthful percentage exists yet.

The helper's output contract is complete: either `null`, or a finite number in `[0,100]`.

### D2. Keep unknown totals indeterminate {#d2}

Change the XHR handler to dispatch only a real percentage:

```ts
req.addEventListener("progress", (event) => {
  const percent = calculateDownloadPercent(event, fileSize);

  if (percent !== null) {
    progressCallback(percent);
  }

  // No valid total: preserve waitingForFile=true so the existing UI remains
  // indeterminate instead of manufacturing a determinate value.
});
```

Download rows already start with `waitingForFile=true`, and `ObjectHandled` already renders that state with `variant="indeterminate"`. There is no need to widen Redux to `number | null`, add another boolean, or change MDS.

When the first valid percentage arrives, the existing `updateProgress` action stores it and sets `waitingForFile=false`. When no valid percentage ever arrives, the row remains indeterminate until a terminal action.

### D3. Make cancellation terminal {#d3}

Completion and failure already clear `waitingForFile`. Cancellation does not. Add the missing transition in `cancelObjectInList`:

```ts
item.waitingForFile = false;
```

Without that line, the repaired prefix download would remain in the indeterminate rendering branch after abort, masking the Cancelled state. The row continues to follow the current product behavior: it remains as a cancelled record and can be removed manually. Automatic removal is not part of this change.

There is one event-order guard at the XHR boundary as well. `abort()` first produces `readystatechange(DONE, status=0)` and only then the `abort` event; without a status-zero return, the generic DONE branch marks the request failed before `onabort` can mark it cancelled. DONE/status zero is therefore left to the dedicated `onerror` or `onabort` handler, and `onabort` removes the stored request reference.

### D4. Normalize an omitted zero-byte size {#d4}

The single-selection thunk passes `object.size || 0`, matching the other download entry point. This restores the API model's omitted logical zero before the helper checks `Blob.size === fileSize`, so an HTTP 200 zero-byte object completes at 100% instead of being reported as incomplete.

### D5. Keep the server stream unchanged {#d5}

The folder handler continues to generate a deflated ZIP through `io.Pipe` and omit `Content-Length`. No API, archive, storage, or resource-management contract changes.

## State machine {#state-machine}

| State | `waitingForFile` | `percentage` | Terminal flag | Rendering |
| --- | ---: | ---: | --- | --- |
| Queued / no valid progress yet | `true` | `0` | none | indeterminate |
| Unknown-total transfer | `true` | `0` | none | indeterminate |
| Known-total transfer | `false` | `0..100` | none | determinate percentage |
| Completed | `false` | `100` | `done=true` | success |
| Failed | `false` | last value | `failed=true, done=true` | error |
| Cancelled | `false` | `0` | `cancelled=true, done=true` | cancelled |

The state does not move back from determinate to indeterminate. If a later event lacks a valid total after a valid percentage was observed, the handler simply retains the last valid value.

Failed and Cancelled both set `done=true` in the existing reducers. `ObjectHandled` uses `done` to change its close button from "abort request" to "remove record"; this repair preserves that behavior. The cancelled Redux value remains `0`, while the existing `ProgressBarWrapper` renders a full orange terminal bar with a Cancelled label because `ready=true`. That established presentation is not part of this repair.

`waitingForFile` is not the ideal long-term name for "no computable progress." Renaming it or replacing the booleans with a discriminated union would improve the model, but that is a separate refactor. In this repair, the field already expresses and renders the required state, so reusing it minimizes compatibility risk.

## Why this is sufficient {#proof}

The repair closes the bug by cases.

### Ordinary non-empty file {#case-file}

`objectSize > 0`, so the helper uses the same denominator as today. The result is finite and clamped, `updateProgress` enters determinate mode, and completion still sets 100%.

### Current streamed folder {#case-folder}

`objectSize` is normalized to `0`, while `lengthComputable=false` and `event.total=0`. The helper returns `null`; no invalid action is dispatched, so the row remains indeterminate. Completion sets `waitingForFile=false`, `percentage=100`, and `done=true`.

### Future response with a real length {#case-future}

If a proxy or later server implementation provides a trustworthy response total, `lengthComputable=true` and `event.total>0`. The same code automatically produces a real percentage without another product change.

### Zero-byte file {#case-zero}

The omitted listing size is normalized to zero, and both totals are then zero, so an intermediate percentage is mathematically undefined. The row stays indeterminate for its usually brief lifetime; the zero-byte Blob now equals the normalized expected size, and the successful response transitions directly to 100%. `0/0` is never evaluated.

### Failure and cancellation {#case-terminal}

Failure already exits indeterminate. The added cancellation transition does the same on abort. No terminal row can continue to look active merely because its total was unknown.

Mathematically, division occurs only when `total` belongs to `(0, +infinity)`. The result is then clamped to `[0,100]`. Therefore neither `NaN` nor `Infinity` can cross the calculation boundary into Redux or the determinate renderer.

## Rejected alternatives {#alternatives}

### Buffer the ZIP to obtain Content-Length {#alt-buffer}

The server could generate the complete archive in memory or a temporary file, measure it, and then send it. That would provide an exact wire total, but at the cost of memory or disk pressure, delayed first byte, cleanup complexity, and worse concurrent-download behavior. An observability defect does not justify discarding streaming.

### Sum the objects under the prefix {#alt-sum}

That sum is uncompressed logical data. `event.loaded` measures compressed response bytes plus ZIP framing. The units differ, so the bar could stop below 100%, exceed 100%, or move according to compression ratio rather than transfer completion. Reject.

### Convert invalid progress to 0% {#alt-zero}

This hides the string but lies about the state: determinate 0% means the total is known and no portion has transferred. Users would still interpret the transfer as stalled. Unknown must remain unknown.

### Special-case paths ending in `/` {#alt-folder-check}

That fixes the reported prefix but misses a real zero-byte object, invalid metadata, and other unknown-length responses. The correct boundary is denominator capability, not object type.

### Send folders through `BrowserDownload` {#alt-browser-download}

The current large-file path creates an anchor and immediately calls the completion callback after clicking it. It cannot report true completion, console-managed cancellation, or a subsequent HTTP failure. It may be the basis of a later streaming-download design, but today it would replace one lie with another.

### Sanitize inside ProgressBar {#alt-component}

A generic component guard could be useful defense in depth, but it would leave invalid data in Redux and hide the broken state transition from every other consumer. The primary repair belongs where progress becomes application state.

### Introduce `percentage: number | null` now {#alt-null-state}

A discriminated progress state would be cleaner than the current booleans if the Object Manager were being redesigned. Adding `null` while retaining `waitingForFile`, `done`, `failed`, and `cancelled` would instead create more contradictory combinations. Removing the old fields is larger than this bug requires. Reuse the already-rendered indeterminate state now; redesign it separately.

## Requirements and acceptance {#requirements}

### Functional requirements {#functional}

- **FR1:** An unknown total keeps the task indeterminate.
- **FR2:** A finite positive object size preserves ordinary-file percentages.
- **FR3:** A finite positive `event.total` is a fallback only when `lengthComputable=true`.
- **FR4:** Every dispatched percentage is finite and within `[0,100]`.
- **FR5:** A zero-byte file never displays non-finite progress and reaches success.
- **FR6:** Completion, failure, and cancellation leave indeterminate mode.
- **FR7:** Versioned objects, anonymous downloads, previews, and long-filename entry points retain their existing call contract.

### Non-functional requirements {#non-functional}

- No new server CPU, memory, disk-buffer, or request cost.
- No new frontend dependency or build step.
- No change to the S3 API, Console API, ZIP content, or stored objects.
- The calculation must be testable without a DOM or live store.
- TypeScript typecheck and the production frontend build must pass.

### Acceptance criteria {#acceptance}

1. While a folder ZIP without `Content-Length` is active, its row shows an indeterminate animation and no percentage text.
2. On successful completion, the row reports success/100% and the ZIP can be opened.
3. A normal non-empty file continues to show finite determinate progress and completes at 100%.
4. A zero-byte file never shows `NaN%` or `Infinity%` and completes successfully.
5. Cancelling an unknown-total download aborts the request and shows Cancelled, not an active animation.
6. No download path can place a non-finite or out-of-range percentage in Redux.

## Test plan {#tests}

### Pure calculation matrix {#unit-tests}

Use the existing `@playwright/test` runner for the pure module rather than adding a test framework. This needs one config-only addition in `web-app/playwright.config.ts`: a dependency-free `unit` project, for example with `testMatch: /.*\.unit\.ts/`. The existing `chromium` project depends on the auth setup against a live Console at `localhost:9090`; pure calculation and reducer tests must not be gated by that environment. No new dependency is introduced.

| Case | `loaded` | `objectSize` | `lengthComputable` | `event.total` | Expected |
| --- | ---: | ---: | --- | ---: | --- |
| Ordinary file, halfway | 50 | 100 | false | 0 | `50` |
| Common prefix | 1024 | 0 | false | 0 | `null` |
| Initial zero over zero | 0 | 0 | false | 0 | `null` |
| Response-total fallback | 50 | 0 | true | 200 | `25` |
| Zero total is unusable | 0 | 0 | true | 0 | `null` |
| Loaded exceeds total | 150 | 100 | true | 100 | `100` |
| Invalid object size | 10 | `NaN` | false | 0 | `null` |
| Omitted zero size | 10 | `undefined` | false | 0 | `null` |
| Invalid response total | 10 | 0 | true | `Infinity` | `null` |
| Negative loaded | -1 | 100 | true | 100 | `null` |

### State tests {#state-tests}

Cover the transition contract directly:

1. A new download starts with `waitingForFile=true`.
2. No valid progress action means it remains indeterminate.
3. Valid progress produces a finite value and `waitingForFile=false`.
4. Complete produces `done=true`, `waitingForFile=false`, `percentage=100`.
5. Failure produces `failed=true`, `done=true`, `waitingForFile=false`.
6. Cancel produces `cancelled=true`, `done=true`, `waitingForFile=false`, `percentage=0`.

### Browser regression {#e2e-tests}

Use the real Console test instance and Chromium:

1. Create a temporary bucket with several objects below `folder/`.
2. Select the prefix from its parent and start the download.
3. Apply CDP download throttling so the intermediate state is observable.
   Throttled runs must raise the default 30-second test timeout with `test.setTimeout`.
4. Open Downloads / Uploads and verify that the row exists, has no percentage label, and contains neither `NaN%` nor `Infinity%`.
5. Cancel it and verify the Cancelled terminal state.
6. Restore network conditions in `finally`.
7. Download again without throttling, wait for the browser download, and verify the ZIP.
8. Repeat the relevant assertions for one ordinary non-empty file and one zero-byte file.
9. Remove the bucket, objects, downloads, and temporary files in teardown.

The current Playwright project is Chromium-only, so CDP is an acceptable test mechanism. If Firefox or WebKit projects are later enabled, keep the pure and state tests cross-browser and gate only the throttled observation behind the Chromium project.

## Implementation boundary {#implementation}

Expected Console changes:

1. Add `downloadProgress.ts` containing the pure calculation.
2. Change `Objects/utils.ts` to dispatch only a non-null percentage, let status-zero terminal events reach their dedicated handlers, and clean up an aborted request.
3. Normalize omitted zero sizes in the single-selection thunk.
4. Change `cancelObjectInList` to clear `waitingForFile`.
5. Add calculation, state, and browser regression coverage using existing dependencies, with a dependency-free `unit` project in `playwright.config.ts`.

Expected unchanged code and contracts:

- The Go folder-download handler and its streaming ZIP.
- `ObjectHandled`, `ProgressBarWrapper`, and MDS.
- `IFileItem.percentage: number` and the existing thunk callback types.
- S3 and Console API routes.
- Stored object and archive formats.

## Delivery and rollback {#delivery}

The fix belongs in `pgsty/silo-console`, not the Silo server repository where the issue was reported.

Delivery order:

1. Transfer or cross-reference issue #62 to `pgsty/silo-console`.
2. Implement the bounded Console change.
3. Pass typecheck, production build, pure/state tests, and real browser regression.
4. Publish a new Console release.
5. Update Silo's pinned Console pseudo-version or release dependency.
6. Build a Silo candidate and repeat folder, ordinary-file, zero-byte, cancel, and ZIP-integrity checks.
7. Publish Silo and record both affected and fixed versions on the issue.

There is no data migration. If the frontend change regresses, Silo can roll back only the Console dependency; server data and API behavior remain compatible.

## Definition of done {#done}

- [x] The calculation returns only `null` or a finite `[0,100]` number.
- [x] Active unknown-total folder downloads render indeterminate.
- [x] Ordinary files retain determinate progress.
- [x] Zero-byte files never render invalid progress.
- [x] Complete, failed, and cancelled rows all leave indeterminate mode.
- [x] The streamed ZIP and server response contract remain unchanged.
- [x] Typecheck, production build, and automated regressions pass locally.
- [ ] A Console release is published.
- [ ] Silo updates the Console dependency and passes candidate verification.

## Follow-up work {#follow-ups}

Four adjacent improvements deserve separate design records:

1. Stream large folder downloads directly to the browser or filesystem instead of holding the full Blob in memory.
2. Replace the Object Manager's boolean combination with a discriminated progress/terminal state.
3. Improve end-to-end integrity and error signaling for ZIP failures after headers have been sent.
4. Add a generic non-finite-value guard to shared progress components as defense in depth.
5. Repair the pre-existing Blob JSON error decoder and request-trace cleanup on HTTP failure paths.

None is required to stop the current UI from lying. The next maintenance iteration should first restore the smallest honest contract: known totals get percentages; unknown totals remain unknown.

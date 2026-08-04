---
title: "The Parser Knew, the Schema Didn't: Config Keys That Could Take Every Notification Down"
linkTitle: "Notify Keyspace Registration"
date: 2026-08-04
author: "Ruohang Feng"
description: "NATS JWT credentials were rejected as an invalid key by the very server that reads them. The same gap was wired into the legacy migration, so an upgraded config failed validation at every boot — and one failing subsystem zeroes the whole notification list. Three upstream feature PRs each forgot the same registration; a fourth surface corrupted values silently."
tags: [Security, Bucket Notifications]
weight: 100
draft: false
url: "/blog/security/notify-keyspace-registration/"
---

**Status:** Fixed on the local `pgsty/minio` branch as `162ded343`, **unreleased**
**Classification:** Configuration-schema consistency and availability, **not a vulnerability**; includes one defensive hardening (credential values no longer echoed in validation errors)
**Affected scope:** `notify_nats` JWT/NKey/TLS-handshake-first options, `notify_amqp` `immediate`, and any pre-2020 config migrated with an enabled NATS target — whose failure then silences **every** notification backend
**Tracking:** `pgsty/minio` issue #39

> This article names two unfixed availability defects in neighbouring code (the Postgres/MySQL migration writes, and `kvFields` typo folding). Neither is exploitable — both break the operator's own configuration, loudly or not at all — and both are already named in the committed audit test's allowlist. Publication needs no hold beyond the release itself.

## Conclusions first {#summary}

- Three `notify_nats` options — `user_credentials`, `nkey_seed`, `tls_handshake_first` — and one `notify_amqp` option — `immediate` — were **read by the parser, written by the legacy migration, and registered nowhere.** `CheckValidKeys` rejected exactly what `GetNotifyNATS` required.
- One constant meant two things. `target.NATSUserCredentials` held the string `"MINIO_NOTIFY_NATS_USER_CREDENTIALS"`, sat in the environment-variable const block, and was used **both** as an env var name **and** as a config key. The snake_case config key for creds-file auth did not exist anywhere in the program.
- The reporter's error did not come from their command. It came from **the legacy migration**: the pre-fix migration reproduces the issue's error text **byte for byte**, including the `notify_nats:ONE` target name their command never mentioned. The migration wrote the store once; validation rejects it at **every boot** thereafter.
- The blast radius is the amplifier: `FetchEnabledTargets` fails fast on the first bad subsystem, its only caller just logs, and the global target list stays `nil` — so one broken NATS entry silently switches off Kafka, webhook, MQTT, and everything else.
- **Inherited from upstream.** Three feature PRs — #19139 (2024-02, `user_credentials`), #21008 (2025-04, `tls_handshake_first`), #21231 (2025-04, `nkey_seed`) — each added the parser and the env var, and each skipped the schema. Upstream is archived; the fork inherits both the defect and the duty.
- The fix registers the keys, splits the two-faced constant, corrects the migration — including a sibling bug that silently wrote `immediate`'s value under the `internal` key — tolerates the legacy on-disk spelling on the load path only, stops echoing values in invalid-key errors in **both** `CheckValidKeys` forms, and installs an AST audit that mechanically forbids this defect class across all ten notify subsystems.
- The audit found the next instance before the ink dried: the Postgres/MySQL legacy migrations write **five** unregistered keys, one of which is a plaintext database password. Recorded, allowlisted shrink-only, tracked for follow-up.

## The error that named a target nobody asked about {#the-report}

The report (issue #39, by `kuldeep-link11`, against a NATS cluster using JWT operator/accounts auth) is a clean reproduction: configure `notify_nats` with a credentials file, watch it bounce.

```console
$ mc admin config set us notify_nats:FITCHECK \
    address=nats-1:4222 subject=events.object.created \
    MINIO_NOTIFY_NATS_USER_CREDENTIALS=/jwt/creds/minio_notifier.creds \
    jetstream=off queue_dir=/data/queue-fitcheck queue_limit=100000

mc: <ERROR> ... found invalid keys
    (MINIO_NOTIFY_NATS_USER_CREDENTIALS=/jwt/creds/minio_notifier.creds
     nkey_seed= tls_handshake_first=off ) for 'notify_nats:ONE' sub-system,
    use 'mc admin config reset myminio notify_nats:ONE' to fix invalid keys
```

Two things in that error are wrong in ways the command cannot explain. The invalid-key list contains `nkey_seed=` and `tls_handshake_first=off` — keys the user never passed. And the rejected sub-system is `notify_nats:ONE`, while the command configured `notify_nats:FITCHECK`.

The second oddity is the whole case. Our reviewer established that the `mc admin config set` path **cannot even carry an unregistered key**: the server-side tokenizer, `kvFields`, splits the input line by searching for *registered* key names, so an unknown token never becomes a key at all — it is absorbed into the preceding key's value. Probed directly:

```
input:  subject=s MINIO_NOTIFY_NATS_USER_CREDENTIALS=/jwt/x.creds
stored: subject="s MINIO_NOTIFY_NATS_USER_CREDENTIALS=/jwt/x.creds"
```

So the rejection could not have been about the command line. It was `validateConfig` sweeping the whole subsystem and tripping over a **different, already-stored target** named `ONE` that carried all three keys. Only one code path in the tree writes those key names into a store: the legacy config migration. Driving the pre-fix migration on an enabled NATS target named `ONE` reproduces the issue's error text **character for character** — including the empty `nkey_seed=`, which is just what migration writes when the legacy config had no NKey.

That reframes the incident. This was not "the server rejected my command." It was: *an old config was migrated once, the migration wrote three keys the validator does not accept, and the store has been failing validation at every boot since* — taking every other notification target down with it, silently, because the failure is logged and swallowed. The reporter's command merely walked into the blast radius and got handed someone else's error.

## One constant, two meanings {#the-constant}

The declaration, as inherited (`internal/event/target/nats.go`, pre-fix):

```go
const (
    NATSAddress  = "address"
    NATSSubject  = "subject"
    NATSUsername = "username"
    NATSPassword = "password"
    NATSNKeySeed = "nkey_seed"            // config key — correct shape
    // ...
    EnvNATSUsername     = "MINIO_NOTIFY_NATS_USERNAME"
    NATSUserCredentials = "MINIO_NOTIFY_NATS_USER_CREDENTIALS"  // ← in the Env block
    EnvNATSPassword     = "MINIO_NOTIFY_NATS_PASSWORD"
)
```

`NATSUserCredentials` is named like a config key, valued like an env var, and shelved with the env vars. The parser used it as **both**: once as the env var to look up, once as the config key to read from the stored KVS. The migration used it as a key to *write*. There was no `"user_credentials"` string anywhere in the program — the config key for creds-file auth simply did not exist, which is why the reporter, finding no documented key, resorted to passing the env var name as one.

A name that means two things will eventually be wrong in one of them. Here it was wrong in both directions at once: as a key it was unregistered garbage; as the only spelling available it taught users and the migration to write garbage.

## Four surfaces, no handshake {#the-class}

A notify option in this codebase lives on four surfaces that must agree: the **defaults** (`DefaultNATSKVS` — what validation accepts and `mc admin config get` displays), the **help** (`HelpNATS` — what `mc admin config` documents), the **parser** (`GetNotifyNATS` — what the server actually reads), and the **migration** (`SetNotifyNATS` — what upgrades write). Nothing ties them together. Three upstream feature PRs each updated the parser and the env plumbing, and each forgot the first two surfaces:

| Key | Parser reads | Migration writes | Defaults | Help | Introduced |
| :-- | :-- | :-- | :-- | :-- | :-- |
| `user_credentials` | yes (via the two-faced constant) | yes (as the env-name string) | **no** | **no** | #19139, 2024-02 |
| `nkey_seed` | yes | yes | **no** | **no** | #21231, 2025-04 |
| `tls_handshake_first` | yes | yes | **no** | **no** | #21008, 2025-04 |
| `immediate` (AMQP) | yes | *see below* | **no** | **no** | config-KV rewrite era |

The AMQP row hides the quieter sibling. The AMQP migration did not skip `immediate` — it wrote `immediate`'s **value under the `internal` key**, and dropped `cfg.Internal` entirely:

```go
config.KV{
    Key:   target.AmqpInternal,          // wrong key
    Value: config.FormatBool(cfg.Immediate),  // right value
},
// cfg.Internal: written nowhere
```

Because `internal` *is* registered, this one passes validation. The NATS gaps break a migrated config loudly enough to be found eventually; the AMQP gap **corrupts it silently** — a migrated broker config carries the wrong flag with a clean bill of health. One defect class, two presentations: the unregistered key fails closed, the misrouted value fails wrong.

## The amplifier {#amplifier}

None of this would deserve the word "outage" without the aggregation semantics. `FetchEnabledTargets` iterates the ten notify subsystems and returns `(nil, err)` on the **first** failure; its only caller logs the error and moves on, leaving the global notification target list `nil`; every later lookup nil-guards into an empty list. One rejected `notify_nats` target therefore turns off **all** bucket notifications — Kafka, webhook, AMQP, MQTT, the lot — with nothing but one line in the server log.

We considered changing this to per-subsystem isolation and **decided not to**, in this fix. Skip-the-broken-subsystem is a real behavioural change to how operators experience a bad config: today it fails loudly-in-aggregate (everything stops), and configurations that operators have already reasoned about depend on validation being all-or-nothing. Rewiring that is a compatibility decision that deserves its own change, not a rider on a registration fix — and once registration is correct, *legal* configs no longer trigger the cascade at all. The decision is recorded as a doc comment on `FetchEnabledTargets` and pinned by a characterization test, so the next person to touch it changes it on purpose or not at all.

## The fix {#the-fix}

About a hundred lines of production change, carried by nine hundred lines of tests (`162ded343`: 8 files, +1029/−7).

**Registration.** All four keys enter their default KVS and help schema, placed where an operator would look for them (`user_credentials` beside `username`, `nkey_seed` after `token`, `tls_handshake_first` after `tls_skip_verify`, `immediate` beside `mandatory`). Registration is also what makes a key *visible*: all four now appear in `mc admin config get` output where they previously did not.

**The constant, split.** `NATSUserCredentials` becomes a real config key, `"user_credentials"`; a new `EnvNATSUserCredentials` carries the env string. Every env var name involved — `MINIO_NOTIFY_NATS_USER_CREDENTIALS`, `_NKEY_SEED`, `_TLS_HANDSHAKE_FIRST`, `MINIO_NOTIFY_AMQP_IMMEDIATE`, and their `_TARGET`-suffixed forms — is frozen byte-for-byte: they are public interface, they worked throughout (the env route was always the workaround), and a test now pins them **as raw string literals**, so no rename of a Go constant can drift them silently.

**Help flags, by precedent.** Both new NATS values are file *paths* (a `.creds` file; an NKey seed file), so they are marked `Sensitive` but not `Secret`, mirroring `cert_authority`/`client_cert`/`client_key` rather than `password`/`token`. `Secret` would additionally redact them from `mc admin config get` — hiding an operator's own configured path from them, which is why the private-key path `client_key` never had it either.

**Migration, corrected.** `SetNotifyNATS` now writes the real key; `SetNotifyAMQP` writes `immediate = cfg.Immediate` **and** `internal = cfg.Internal`.

If you are affected today, on a pre-fix build: the env var route works and always did, and `mc admin config reset myminio notify_nats:<target>` un-wedges a poisoned store at the cost of its settings. On the fixed build, poisoned stores simply load again — next section.

## Living with what the old migration already wrote {#tolerance}

Fixing the migration helps the next upgrade. It does nothing for stores the broken migration already wrote, which contain the literal key `MINIO_NOTIFY_NATS_USER_CREDENTIALS` — still unregistered, still fatal at every boot. Telling those operators to hand-reset their config would mean punishing them for our write.

So the load path tolerates it, narrowly. Validation accepts the legacy spelling **for the NATS subsystem only** — a test asserts AMQP still rejects it, so the tolerance cannot become a general escape hatch — and the parser falls back to it only when the real key is empty. Precedence is `env > user_credentials > legacy key`, and it holds **by construction** rather than by convention: the fallback result is passed as the *default* argument of the env lookup. All three orderings are tested. The legacy key stays out of the defaults and the help on purpose: it is tolerated, never advertised, never newly settable (`kvFields` sees to that).

The constant for it is a package-local literal, not an alias of `EnvNATSUserCredentials` — deliberately. It names bytes **already on disk**, so it must not follow any future rename of the env constant. The comment says so.

One trap discovered while wiring this, worth its own paragraph because it will bite someone eventually: the codebase has **two** `CheckValidKeys` — a free function and a method — and their `deprecatedKeys` parameters mean **opposite things**. The free function *tolerates* the listed keys (skips them); the method *subtracts them from the valid set* (rejects them). Refactoring this call from one form to the other would silently invert the tolerance into a ban. That asymmetry is now documented at the call site, which is the best one can do short of renaming an exported API.

The tolerance is written to be retired: the clean end state is to rewrite the legacy key into `user_credentials` once at load, then delete both the tolerance and the fallback. That is follow-up #2 below — and it also closes a small hole the tolerance leaves open: an unregistered key carries no `Sensitive` flag, so a tolerated legacy key ships its value (a path) unredacted in health-diagnostics bundles while `user_credentials` shows `*redacted*`.

## Secrets in error messages {#redaction}

The invalid-keys error that started all this printed the rejected pairs **with their values**: `found invalid keys (MINIO_NOTIFY_NATS_USER_CREDENTIALS=/jwt/creds/minio_notifier.creds ...)`. Those paths are mild. The mechanism is not: whatever value rides on a rejected key — a mistyped `nkey_sed=<seed>`, a bind password on a stale LDAP key — lands in the server log and in the `mc` client's terminal.

Both `CheckValidKeys` forms now print **key names only**, keeping the shape and the `mc admin config reset` hint. The second site was one step beyond the written task scope — the method form serves LDAP, OpenID, and the policy plugin, where a rejected value can be an actual bind password — and the independent review, asked to judge that extension, said it would have demanded it: fixing one of two identical leaks is a half-fix. Repo-wide, nothing parsed values out of that string and no test asserted the old text; the change is global and intended.

There is a converse worth recording: this redaction is what stands between the *next* defect of this class and a credential in the logs. The follow-up below found the Postgres/MySQL migrations writing a plaintext database password under an unregistered key — on a pre-redaction build, the resulting rejection prints that password.

## A guard that makes the class extinct {#the-audit}

Registering four keys fixes four keys. The class — four surfaces, no handshake — stays open unless something ties the surfaces together mechanically. The fix therefore ships an AST-based audit test that parses `parse.go` and `legacy.go`, resolves the constants (from the `target` package sources, so there is no hand-maintained list to rot), and asserts, for **all ten** notify subsystems:

- every key the parser reads is registered in that subsystem's defaults;
- every key the migration writes is registered (minus an explicit, shrink-only allowlist — next section);
- every help entry names a registered key.

Run against the pre-fix tree, it fails on exactly the four known gaps and nothing else — which is the red proof that it measures the right thing.

The adversarial review then attacked the audit itself with a mutation harness, on the theory that a guard you cannot watch fail is a guess — the discipline [the previous article](/blog/security/duplicate-part-numbers/) argued for. Seven of its nine mutations were caught. **Two were not**, and both blinded the audit *silently*: rename the parser's loop variable (the read-collector pattern-matched the receiver name `kv`), or switch a migration entry to Go's idiomatic elided composite-literal form (the write-collector demanded a typed `config.KV{...}`). In both cases the collector returns an **empty map**, the assertion loop iterates zero keys, and the test passes vacuously. Both are refactors a maintainer would make without a second thought; one of them is what `gofumpt` nudges you toward.

Two hardenings closed this, each verified in both directions — with the hardening the mutation is caught; with the hardening removed (the counterfactual) the vacuous pass returns:

- **A floor assertion in the reverse direction:** every *registered* key must be *seen being read*. This holds for all ten subsystems today — measured, not assumed, including the deprecated `streaming_*` keys read inside a nested conditional — so it costs nothing, and a blinded collector now produces one loud error per registered key (22 of them for NATS) instead of a green run.
- **A widened literal guard:** typed literals that are neither `config.KV` nor `config.KVS` are skipped; untyped (elided) literals have no type to check and are now inspected rather than ignored.

Final score: ten mutations, ten caught — the harness gained one variant along the way, and the closure round swept the full suite. The audit also enforces its own allowlist in both directions — removing an entry that is still needed fails, and an entry that goes stale (the migration no longer writes that key) fails too, so the allowlist can neither grow silently nor lie about the present.

## What the audit found next {#followups}

The write-side check refused to go green on two subsystems that had nothing to do with issue #39. `SetNotifyPostgres` and `SetNotifyMySQL` write five keys — `host`, `port`, `username`, `password`, `database` — that no default KVS registers and no parser reads. These are relics of the pre-DSN configuration shape, and the migration still emits them. Driving the real helpers confirms it: a migrated Postgres or MySQL notify target is rejected on the next load with `found invalid keys (host, port, username, password, database)` — the same failure mode as NATS, the same every-boot persistence, the same all-notifications blast radius through the fail-fast. And `password` there is a plaintext database password, which is exactly the value the redaction above now keeps out of the logs.

It is deliberately **not** fixed in this change. The scope was locked to the NATS and AMQP gaps, and the right treatment (register the five as deprecated, or stop writing them, or both) is a judgment call that deserves its own red/green cycle. It is pinned in the audit's `knownUnregisteredWrites` allowlist with a shrink-only comment, so it cannot be quietly forgotten: the day someone fixes it, the stale allowlist entry fails the test and demands its own deletion.

Open items, none in a released build as of 2026-08-04:

1. **Postgres/MySQL migration unregistered writes** — major, live at every boot for anyone migrating a pre-KV config with those targets enabled.
2. **Rewrite-on-load for the legacy NATS key**, then retire the F5 tolerance and fallback; also closes the health-bundle redaction gap for tolerated keys.
3. **`kvFields` typo folding** — an unknown key name in `mc admin config set` is silently absorbed into the preceding key's value instead of erroring. Pre-existing upstream wart; it protected nobody here and will corrupt someone's `subject` eventually.

## Review record {#review}

The change went through three gates before commit:

| Gate | Method | Outcome |
| :-- | :-- | :-- |
| Implementer | tests written first and run against the unmodified tree; the missing constant made the suite **fail to compile**, which is itself the red for the split; targeted reversal produced runtime reds for the rest | red established for every claim |
| Independent adversarial reviewer | detached worktree at the pre-fix commit; re-derived every red rather than trusting the report; mutation harness against the audit; probe tests for precedence edges; **reproduced the reporter's error byte-for-byte from the migration path** | **REVISE**, two demands |
| Closure round | both demands applied; counterfactual mutation runs (with and without each hardening) prove the hardenings load-bearing; reviewer re-diffed, re-ran, re-mutated | **ACCEPT**, 10/10 |

The honest accounting, in the house tradition: neither demand was a defect in the production fix. One was a lint gate (two British spellings that would have failed `make test` — and while fixing them, the implementer's rewritten comment introduced a third, `dialled`, which the same gate caught; the demand vindicated itself in real time). The other was the audit-blindness pair above — durability of the guard, not correctness of the change. What the review *did* overturn was the incident's origin story: the migration-path reproduction, the `ONE` target, and the `kvFields` absorption proof all came from the reviewer, and they change what operators should conclude — this was a boot-time outage lying in wait in stored configs, not a CLI validation quirk.

The implementer's red phase also surfaced three bugs in its own new tests before the fix landed, recorded rather than smoothed over: a fixture that assumed stored targets are layered over defaults when `config.Merge` actually passes them through verbatim; a characterization test that segfaulted on a nil HTTP transport (`FetchEnabledTargets` dereferences it unconditionally — hostile to testing, noted, unfixed); and an early draft keyed to the very constant the fix renames, which made it pass green pre-fix — rewritten against the literal string so it pins the on-disk schema rather than the Go symbol.

## Declined, and left open {#declined}

Declined, deliberately:

- **Per-subsystem error isolation in `FetchEnabledTargets`** — a compatibility decision, not a rider ([above](#amplifier)).
- **Registering or advertising the legacy key** — tolerated on load, absent from defaults and help, impossible to set anew.
- **Renaming `EnvNatsTLSHandshakeFirst`'s odd casing** — an aesthetic rename in a fork is diff noise that buys nothing.
- **Fixing the Postgres/MySQL migration here** — scope-locked, pinned in the allowlist instead ([above](#followups)).

Left open: the three follow-ups above, and one cosmetic consequence — a store that still carries the tolerated legacy key will show it verbatim in `mc admin config get` until rewrite-on-load lands.

## Closing {#closing}

Every one of these keys worked perfectly through the environment variable, which is why three feature PRs could ship, get reviewed, get used, and never notice that the config-file half of the interface was stillborn. The parser and the schema are two descriptions of the same contract, maintained by hand, four surfaces wide — and for two and a half years nothing in the build checked that they agree.

If only one sentence survives: **when two artifacts must stay identical and only convention binds them, the divergence is not a risk but a schedule** — put a machine between them, then mutate the machine until you have watched it catch the drift you fear.

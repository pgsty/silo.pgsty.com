---
title: "SN-2026-019: Notification Keyspace Registration and Validation Redaction"
linkTitle: "SN-2026-019: Notify Keyspace"
date: 2026-08-04
author: "[Ruohang Feng](https://vonng.com) ([`@Vonng`](https://github.com/Vonng))"
description: "How unregistered notification KVS keys broke config validation, knocked out active targets, and echoed secret values in error messages (SN-2026-019)."
url: "/blog/security/notify-keyspace-registration/"
tags: ["Security", "Notifications", "Configuration", "NATS", "AMQP", "PostgreSQL", "MySQL", "SILO"]
---

**`SN-2026-019`** covers a class of notification configuration defects fixed in [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) (`162ded343` and `672c07a0f`, [`pgsty/silo#39`](https://github.com/pgsty/silo/issues/39)): notification parser and legacy-migration paths read or wrote KVS configuration keys that were missing from `Default*KVS`, while `CheckValidKeys` echoed raw key values in validation errors and `FetchEnabledTargets` aborted all active notification targets on the first validation failure. In [Server 20260903](/blog/design/notify-url/) (`f1ba68358`), the discrete PostgreSQL and MySQL host/credential keys uncovered by our AST audit were retired in favor of `connection_string` and `dsn_string`.

## Conclusions first {#summary}

1. **Four uncoordinated surfaces drifted apart**: In the notification configuration subsystem, `Default*KVS` (valid key schema), `Help*` (help text and secret/sensitive classification), `GetNotify*` (parser), and `SetNotify*` (legacy config migration) were maintained by hand without a cross-check.
2. **One invalid target disabled all notification targets**: `FetchEnabledTargets` validates every notification subsystem sequentially and returns on the first error, leaving the global notification target list `nil` across the server.
3. **Validation errors echoed secret values**: When `CheckValidKeys` rejected an unknown or mistyped key, it formatted the error using `kv.String()`, printing `key=value`—including credentials or passwords—into logs and admin CLI responses.
4. **AST-enforced invariant**: Server `20260804` registers the missing NATS and AMQP keys, redacts values from `CheckValidKeys` errors, expands `HasSensitiveKeys`, and enforces a compile-time AST test ensuring every key read or written by `cmd/config/notify` is registered in `Default*KVS`.

---

## A Puzzling Bug Report {#the-report}

The investigation started from a bizarre symptom reported by `kuldeep-link11`: an operator ran `mc admin config set us notify_nats:FITCHECK address="..." subject="..."` and received an error complaining about a completely different target (`notify_nats:ONE`) and two keys (`nkey_seed= tls_handshake_first=off`) that the operator had never passed on the command line:

```text
Error: Invalid key/value pair 'nkey_seed= tls_handshake_first=off' found in subsystem 'notify_nats:ONE'
```

Two separate mechanisms combined to produce that confusing error:

1. **Tokenizer absorption on `mc admin config set`**: `kvFields` in `internal/config/parser.go` splits input tokens by matching only keys registered in `DefaultKVS`. When a user passes an unregistered key on the command line, `kvFields` does not recognize it as a key delimiter and silently absorbs `"nkey_seed=..."` as part of the preceding key's value (such as `subject`).
2. **Legacy migration poisoning on `notify_nats:ONE`**: Earlier in the deployment's life, the legacy configuration migrator (`SetNotifyNATS` in `cmd/config/notify/legacy.go`) had serialized `notify_nats:ONE` directly into the KVS struct—bypassing `kvFields`—and written `nkey_seed` and `tls_handshake_first` as discrete KVS keys. When the operator later edited `notify_nats:FITCHECK`, `validateConfig` re-validated all stored targets and tripped over `notify_nats:ONE`.

---

## One Constant Used for Two Different Namespaces {#the-constant}

Inspecting `internal/config/notify/target/nats.go` immediately revealed a second bug right next to `nkey_seed`:

```go
const (
    NATSAddress = "address"
    NATSSubject = "subject"
    ...
    EnvNATSAddress         = "MINIO_NOTIFY_NATS_ADDRESS"
    EnvNATSSubject         = "MINIO_NOTIFY_NATS_SUBJECT"
    NATSUserCredentials    = "MINIO_NOTIFY_NATS_USER_CREDENTIALS"
)
```

When PR [`minio/minio#19139`](https://github.com/minio/minio/pull/19139) added NATS user credentials support in February 2024, `NATSUserCredentials` was placed inside the `Env*` constant block with the value `"MINIO_NOTIFY_NATS_USER_CREDENTIALS"`, and then used as **both** the environment variable name and the KVS key name in `DefaultNATSKVS`. As a result, setting `user_credentials=/path/to/creds` via `mc admin config set notify_nats` was rejected as an unknown key, whereas the literal string `MINIO_NOTIFY_NATS_USER_CREDENTIALS=/path/to/creds` was what `DefaultNATSKVS` expected on disk.

---

## Four Uncoordinated Surfaces {#the-class}

Auditing all notification targets in `cmd/config/notify/` showed that every target defines four separate surfaces:
- `Default*KVS` (`cmd/config/notify/config.go`): the canonical list of valid KVS keys enforced by `CheckValidKeys`,
- `Help*` (`cmd/config/notify/help.go`): user-facing help metadata and `Type` (`Sensitive` / `Secret`),
- `GetNotify*` (`cmd/config/notify/parse.go`): reads KVS keys and `MINIO_NOTIFY_*` environment variables,
- `SetNotify*` (`cmd/config/notify/legacy.go`): migrates older JSON config structs into KVS pairs.

Across NATS and AMQP, four keys had drifted across those four surfaces:

| Target | Key | Introduced In | `Default*KVS` | `Help*` | `GetNotify*` | `SetNotify*` | Failure Mode |
|---|---|---|---|---|---|---|---|
| `notify_nats` | `user_credentials` | [`#19139`](https://github.com/minio/minio/pull/19139) (2024-02) | Registered as `MINIO_NOTIFY_NATS_USER_CREDENTIALS` | Missing | Read `MINIO_NOTIFY_NATS_USER_CREDENTIALS` | Wrote `MINIO_NOTIFY_NATS_USER_CREDENTIALS` | `user_credentials` rejected on `mc admin config set` |
| `notify_nats` | `nkey_seed` | [`#21231`](https://github.com/minio/minio/pull/21231) (2025-05) | Missing | Missing | Read `nkey_seed` | Wrote `nkey_seed` | Stored config fails `CheckValidKeys` |
| `notify_nats` | `tls_handshake_first` | [`#21008`](https://github.com/minio/minio/pull/21008) (2025-02) | Missing | Present | Read `tls_handshake_first` | Wrote `tls_handshake_first` | Stored config fails `CheckValidKeys` |
| `notify_amqp` | `immediate` | Initial KVS migration | Missing | Missing | Read `immediate` | Wrote `cfg.Immediate` into `AmqpInternal`! | `immediate` rejected; `SetNotifyAMQP` overwrote `internal` with `cfg.Immediate` |

Notice the AMQP bug in the last row: `SetNotifyAMQP` in `cmd/config/notify/legacy.go` had a copy-paste typo that wrote `strconv.FormatBool(cfg.Immediate)` under the key `target.AmqpInternal` and never serialized `cfg.Internal` at all.

---

## Blast-Radius Amplifier: All-or-Nothing Target Loading {#amplifier}

Why did a broken `notify_nats:ONE` target matter so much? In `cmd/config/notify/parse.go`, `FetchEnabledTargets` loads all ten notification subsystems (`amqp`, `elasticsearch`, `kafka`, `mqtt`, `mysql`, `nats`, `nsq`, `postgres`, `redis`, `webhook`) in sequence. If **any** subsystem returns a validation error from `CheckValidKeys`, `FetchEnabledTargets` returns early before populating the active target map.

Consequently, a single invalid key in an unused `notify_nats` target causes startup or config reload to leave the global notification target list empty, silently disabling **all** bucket notifications (such as active Kafka or Webhook targets) until an administrator removes the offending config entry.

We considered changing `FetchEnabledTargets` to isolate errors per subsystem and keep other targets running, but declined that change: across SILO, configuration validation is intentionally all-or-nothing so that `mc admin config set` rejects broken configurations rather than partially applying them. Fixing key registration removes the false-positive failures without weakening config transaction semantics.

---

## Fixing Key Registration and Classification {#the-fix}

Commit `162ded343` fixes the NATS and AMQP keyspace defects:

1. **Split key constant from env constant**: `target.NATSUserCredentials` is now `"user_credentials"`, and `target.EnvNATSUserCredentials` is `"MINIO_NOTIFY_NATS_USER_CREDENTIALS"`.
2. **Register all four keys in `DefaultNATSKVS` and `DefaultAMQPKVS`**: `user_credentials`, `nkey_seed`, and `tls_handshake_first` are registered in `DefaultNATSKVS`, and `immediate` is registered in `DefaultAMQPKVS`.
3. **Complete `HelpNATS` and `HelpAMQP`**: Added help entries for `user_credentials`, `nkey_seed`, and `immediate`. Both `user_credentials` and `nkey_seed` take local file paths on the server filesystem (just like `client_key`), so we classified them as `config.Sensitive` rather than `config.Secret`.
4. **Fix `SetNotifyAMQP`**: `SetNotifyAMQP` now writes `cfg.Internal` to `target.AmqpInternal` and `cfg.Immediate` to `target.AmqpImmediate`.

---

## Narrow Backward Tolerance for Stored NATS Configs {#tolerance}

What if a deployment prior to `20260804` had worked around `#19139` by storing the literal key `MINIO_NOTIFY_NATS_USER_CREDENTIALS=/path/to/creds` in its persisted cluster configuration?

Simply renaming `NATSUserCredentials` to `"user_credentials"` would cause `CheckValidKeys` to reject that persisted configuration on upgrade—triggering the exact `FetchEnabledTargets` outage described above.

While designing backward tolerance, we uncovered a subtle trap between two identically named functions in `internal/config`:
- The **free function** `config.CheckValidKeys(subSys, kvs, defaultKVS, deprecatedKeys...)` accepts an optional variadic list of deprecated keys and permits them during load validation.
- The **method** `kvs.CheckValidKeys(subSys, defaultKVS)` calls `CheckValidKeys(subSys, kvs, defaultKVS)` **without** passing any deprecated keys.

We updated the NATS load path (`GetNotifyNATS`) to tolerate `"MINIO_NOTIFY_NATS_USER_CREDENTIALS"` via the deprecated-key list on `config.CheckValidKeys`, and implemented deterministic precedence when populating `UserCredentials`:
1. `MINIO_NOTIFY_NATS_USER_CREDENTIALS` environment variable (highest precedence),
2. `user_credentials` KVS key,
3. Legacy `MINIO_NOTIFY_NATS_USER_CREDENTIALS` KVS key (fallback when `user_credentials` is empty).

---

## Redacting Values in Validation Errors (`SN-2026-019`) {#redaction}

Before `20260804`, both `config.CheckValidKeys` and `KVS.CheckValidKeys` built their error string by appending `kv.String()` (`key=value`) for every unrecognized key. If an administrator mistyped a secret key name—for example, `pasword=Hunter2` or `auth_tokn=eyJ...`—or if a legacy migrator wrote an unregistered credential key, the error message echoed the cleartext secret into the console response and server error logs.

Commit `162ded343` changes both `CheckValidKeys` functions to report **only** the offending key names (`kv.Key`), never `kv.Value`.

In commit `672c07a0f`, we also audited `config.HasSensitiveKeys` (`internal/config/config.go`), which masks secrets when exporting configurations via `mc admin config get` or generating health-diagnostics bundles. We expanded `HasSensitiveKeys` to cover all credential key names used across notification, identity, and KMS subsystems (`password`, `auth_token`, `secret_key`, `client_secret`, `nkey_seed`, `user_credentials`, `sasl_password`, `connection_string`, and `dsn_string`).

---

## Enforcing the Invariant with an AST Audit Test {#the-audit}

To make sure `Default*KVS`, `parse.go`, and `legacy.go` can never drift apart again, we wrote an AST-based verification test in `cmd/config/notify/config_audit_test.go`. Using `go/ast`, the test parses `parse.go` and `legacy.go`, resolves every `kvs.Get(...)` and `kvs.Set(...)` call back to its string constant definition in `internal/config/notify/target`, and verifies that every referenced key exists in the corresponding `Default*KVS`.

While reviewing the audit test itself, we found and closed two blind spots in our initial test implementation:

1. **Reverse floor assertion**: Checking only that `parse.go ⊆ Default*KVS` would pass even if the AST walker broke and extracted zero keys! We added the reverse check requiring every key registered in `Default*KVS` (except documented universal keys like `enable` and `comment`) to be read in `parse.go` and asserting a minimum key-count floor per subsystem.
2. **Untyped composite literals**: In `legacy.go`, helper tables constructed `config.KVS{...}` using untyped `{Key, Value}` composite literals rather than calling `kvs.Set()`. Extending the AST visitor to inspect `config.KVS` composite literals immediately surfaced a second bug in the codebase.

---

## What the AST Audit Caught: PostgreSQL and MySQL Discrete Keys {#followups}

As soon as the AST visitor inspected `config.KVS` composite literals in `legacy.go`, it flagged `SetNotifyPostgres` and `SetNotifyMySQL`: both functions wrote five discrete keys—`host`, `port`, `username`, `password`, and `database`—that were read by `GetNotifyPostgres` / `GetNotifyMySQL` (`parse.go`) when `connection_string` / `dsn_string` was empty, yet were **completely absent** from `DefaultPostgresKVS` and `DefaultMySQLKVS`!

In addition, because `password` was not registered in `DefaultPostgresKVS` or `DefaultMySQLKVS`, passing `password=...` or migrating a legacy PostgreSQL/MySQL config triggered `CheckValidKeys` and printed the database password in the error message prior to `162ded343`.

We handled this in two steps across two releases:
- **Short-term fix in Server 20260804 (`672c07a0f`)**: Registered `host`, `port`, `username`, `password`, and `database` in `DefaultPostgresKVS` and `DefaultMySQLKVS` (and marked `password` as `Secret` in `HelpPostgres` / `HelpMySQL`) so that existing configurations and the new AST invariant were immediately consistent.
- **Architectural cleanup in [Server 20260903](/blog/design/notify-url/) (`f1ba68358`)**: Having two parallel ways to configure database connections (`connection_string` vs. discrete `host`/`port`/`username`/`password`/`database` keys) caused `SetNotifyPostgres` and `SetNotifyMySQL` to overwrite `connection_string` with empty discrete fields during config round-trips. Server `20260903` retired the five discrete keys across `Default*KVS`, `Help*`, `parse.go`, and `legacy.go`, standardizing exclusively on `connection_string` (PostgreSQL) and `dsn_string` (MySQL).

---

## Declined Changes {#declined}

- **Do not change `kvFields` tokenizer framing in this patch**: Changing `kvFields` to split on arbitrary `key=value` tokens rather than known `DefaultKVS` keys would alter how unquoted spaces inside values (such as SQL queries or subjects) are parsed. With `Default*KVS` now verified by the AST audit, valid keys are always recognized by `kvFields`.
- **Do not weaken `FetchEnabledTargets` fail-fast validation**: As explained in [Blast-Radius Amplifier](#amplifier), configuration validation remains atomic across all subsystems.

## Review Record {#review}

Code review verified the AST audit's reverse floor assertions, untyped `config.KVS` composite literal inspection, `CheckValidKeys` value redaction (`162ded343`), and `HasSensitiveKeys` credential coverage (`672c07a0f`).

## Summary {#closing}

Shipped in [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) (`162ded343` and `672c07a0f`) with follow-up cleanup in [Server 20260903](/blog/design/notify-url/) (`f1ba68358`), all notification KVS keys are verified against `Default*KVS` by AST tests and unrecognized-key errors redact values.

---
title: "DSN-Only Database Notifications: A Compatibility Boundary for #53"
date: 2026-08-23
lastmod: 2026-08-24
author: "Ruohang Feng"
summary: >
  SILO will keep PostgreSQL and MySQL notification targets, but standardize their configuration on complete connection strings. Pre-KV discrete database fields are an unsupported migration input and must abort server startup with an explicit error instead of being accepted and silently disabling every bucket notification.
tags: [Design, Notification, Compatibility]
weight: 10
draft: false
url: "/blog/design/notify-url/"
---

This document is the product requirements and final design record for [SILO issue #53](https://github.com/pgsty/silo/issues/53). It records the accepted compatibility boundary, implementation, and verification for PostgreSQL and MySQL bucket-notification targets.

## Decision {#decision}

SILO will retain PostgreSQL and MySQL notification targets, but support exactly one current configuration form for each:

- PostgreSQL requires a complete `connection_string`.
- MySQL requires a complete `dsn_string`.

The old five-field form — `host`, `port`, `username`, `password`, and `database` — remains unsupported by the current KV configuration system. SILO will not re-register those keys and will not synthesize a DSN from them during legacy migration.

The legacy migration contract is deliberately narrow:

| Legacy target | Result |
| --- | --- |
| Disabled | Ignore it; no target is emitted. |
| Enabled with a non-empty `connection_string` or `dsn_string` | Migrate only the canonical connection-string key and the other registered target settings. |
| Enabled with only discrete connection fields | Reject migration and abort server startup before the new configuration is activated, with an actionable error that names the subsystem and target but never prints a credential. |

This is a configuration-boundary decision, not removal of the database-notification feature.

**Status:** implemented in server commit `f1ba68358`; release pending.<br>
**Owner:** SILO server repository.  
**Tracking:** [pgsty/silo#53](https://github.com/pgsty/silo/issues/53).  
**Target:** the next SILO patch release after implementation and verification.

## Context {#context}

SILO inherited two generations of database-notification configuration from MinIO.

The pre-KV JSON configuration could describe a database connection either as a complete string or as five fields:

```text
host
port
username
password
database
```

The current KV configuration exposes only the driver-native form:

```text
notify_postgres  -> connection_string
notify_mysql     -> dsn_string
```

This direction is not new. MinIO deprecated the five discrete fields in `RELEASE.2020-04-10T03-34-42Z` and instructed operators to move to `connection_string` or `dsn_string`. SILO's current help tables, environment-variable documentation, and examples already present the complete string as the supported interface.

SILO is a new community fork with an explicit migration step. Its compatibility contract prioritizes the S3 and Admin APIs, current `MINIO_*` settings, on-disk data, and current KV configuration. It does not need to perpetuate every pre-2020 configuration spelling when a supported canonical form has existed for years.

## The defect {#defect}

Before the fix, the legacy migration helpers, `SetNotifyPostgres` and `SetNotifyMySQL`, wrote both forms into the new KV configuration. Even when the old target already had a complete connection string, the helpers also emitted all five discrete keys, usually with empty values.

The new parser rejects those keys because neither `DefaultPostgresKVS` nor `DefaultMySQLKVS` registers them. Key validation checks key presence, not whether the corresponding value is empty. Both legacy source forms therefore fail:

```text
old complete string -> canonical string + five empty unknown keys -> rejected
old discrete fields -> empty canonical string + five populated unknown keys -> rejected
```

The failure is amplified by notification initialization. `FetchEnabledTargets` is fail-fast across notification subsystems: the first invalid subsystem returns an error and a nil target list. The caller logs the error and continues starting the object server, leaving healthy Webhook, Kafka, NATS, and other targets unavailable as well.

Merely returning an error from the two migration helpers does not fix that behavior. The error propagates through `readConfigWithoutMigrate` and `initConfig`, but `initConfigSubsystem` currently logs non-retriable configuration errors as "some features may be missing" and returns success. The server then starts without assigning `globalServerConfig`; notification failure is only one consequence, because region, storage class, compression, identity, and other stored settings may also be absent. The implementation must therefore carry a typed database-migration error to the startup boundary and make that error fatal. Classifying it as retriable is also wrong because the server would retry forever without any state change that could repair the configuration.

The resulting behavior is especially dangerous because object I/O still works. Operators can see a healthy S3 service while every configured event pipeline has stopped. Targets are never constructed, so delivery or later replay of events produced during the outage must not be assumed.

There is also a diagnostic-exposure issue. The unregistered `password` key has no sensitivity metadata and may be copied verbatim into health or diagnostic material. The registered `connection_string` and `dsn_string` keys are already treated as sensitive values.

## Why the first fix was reverted {#reverted-fix}

The first repair registered the five discrete keys and taught the parser to read them. That made migrated targets pass `CheckValidKeys`, and it appeared attractive because the target argument structures and constructors still contain code for the old fields.

It also broke the documented connection-string path.

The shared `mc admin config set` tokenizer discovers field boundaries by looking for registered key names. It is not fully quote-aware. Once `port` became a registered key, this valid input contained what looked like a second top-level field:

```text
connection_string="host=db port=5432 dbname=events user=app"
```

The tokenizer split at the `port=` inside the quoted value, truncated `connection_string`, and handed the remainder to the `port` parser. The command then failed with `invalid port`.

Under the current tokenizer, registering common words such as `host`, `port`, and `password` creates a direct conflict between the connection-string grammar and the top-level KV grammar. The attempted registration fix was therefore reverted. Re-registering those keys is not an acceptable solution.

## Product judgment {#product-judgment}

Database notification targets are a specialized but useful capability. They provide a direct database-backed namespace view or access journal without requiring an external event bus. That remains valuable for small deployments and for users already operating PostgreSQL or MySQL.

The legacy spelling of their connection parameters has much less value. A five-field model cannot represent the useful range of driver options: TLS modes and certificates, connection timeouts, application names, Unix sockets, multi-host PostgreSQL settings, MySQL driver parameters, and future driver capabilities. Supporting both forms also creates precedence, merging, redaction, and testing questions that do not exist with one canonical value.

The complete string is the better abstraction boundary: SILO owns notification semantics, while the database driver owns connection syntax.

The product decision is therefore to keep the capability and remove the compatibility illusion. An unsupported legacy target must be rejected clearly; it must not be accepted and transformed into a configuration that later disables unrelated targets.

## Goals {#goals}

1. Establish `connection_string` and `dsn_string` as the only supported live configuration interfaces for database notifications.
2. Allow a legacy JSON target that already contains the canonical string to cross the migration boundary without modification to its connection semantics.
3. Reject enabled discrete-only legacy targets before a partial or invalid KV configuration is activated.
4. Replace the current silent runtime failure mode of #53 — healthy targets disabled while the server appears healthy — with an explicit startup-time failure that operators must resolve before the server runs.
5. Ensure no migration error, log line, health report, or diagnostic bundle exposes a database password.
6. Remove the ten Postgres/MySQL exceptions from the source-level unregistered-write audit.
7. Make the compatibility boundary and operator remediation explicit in release and migration documentation.

## Non-goals {#non-goals}

- Supporting both DSN and discrete database fields in the current KV interface.
- Automatically synthesizing a DSN from old discrete fields.
- Rewriting the shared KV tokenizer.
- Changing `FetchEnabledTargets` fail-fast semantics in this patch.
- Silently skipping an enabled database target and continuing with partial notification coverage.
- Removing PostgreSQL or MySQL notification targets.
- Deleting the legacy struct fields needed to decode and identify unsupported input. They remain on shared target argument structs that are also used by live constructors, whose discrete-field connection-string synthesis is unreachable from current KV configuration; those fields must not become supported configuration keys.
- Correcting ignored errors from the other eight legacy notification setters. Their pre-existing silent-skip behavior remains unchanged in this narrowly scoped database-migration patch and requires a separate audit and design decision.

## Functional requirements {#functional-requirements}

### Current configuration {#current-configuration}

1. `notify_postgres` accepts `connection_string`; `notify_mysql` accepts `dsn_string`.
2. The five discrete keys remain unregistered and rejected by current configuration commands.
3. Existing full strings must continue to support the database driver's syntax, including parameters whose names contain `host`, `port`, `user`, `password`, or `database`.
4. No new public environment variables or KV keys are introduced.
5. The declared legacy variables `MINIO_NOTIFY_POSTGRES_HOST`/`PORT`/`USERNAME`/`PASSWORD`/`DATABASE` and their MySQL equivalents are not wired into current parsing and remain unsupported. They must not be documented as working alternatives to the complete-string variables.

### Legacy migration {#legacy-migration}

1. `SetNotifyPostgres` must return without emitting a target when the legacy target is disabled.
2. For an enabled target, `SetNotifyPostgres` must require a non-empty `ConnectionString` and write only registered Postgres keys. If both a canonical string and discrete fields are present, the canonical string wins and every discrete value is discarded.
3. `SetNotifyMySQL` must apply the equivalent rule to `DSN`.
4. Neither helper may emit `host`, `port`, `username`, `password`, or `database`.
5. A missing canonical string must return a typed or wrapped migration error identifying the subsystem and target name.
6. `cmd/config-migrate.go` must check and propagate both helper errors. Ignoring them is forbidden.
7. No partially migrated configuration may be activated or persisted after either helper fails.
8. Error text may name the required key and remediation, but must not include any connection-field value.
9. The propagated typed migration error must abort server startup. It must not be downgraded to the non-fatal "some features may be missing" path in `initConfigSubsystem`, and it must not enter the retriable-error loop.
10. Validation errors for a supplied canonical string follow the same startup-fatal and secrecy rules; wrapping must add target context without repeating the DSN or its components.

Recommended error shape:

```text
notify_postgres:archive uses unsupported legacy discrete connection fields;
set connection_string before migrating to SILO
```

### Operator remediation {#operator-remediation}

An operator encountering the error must choose an explicit remediation path. This applies both before an initial switch to SILO and when upgrading a deployment that is already running SILO: legacy migration output is not persisted, so the same old JSON source can re-enter migration on every start. A deployment that currently starts with notifications silently broken can therefore fail to start after this repair until the source configuration is corrected.

1. On a compatible intermediate MinIO release, replace the old fields with `connection_string` or `dsn_string`, verify the target, and then migrate to SILO.
2. Disable or remove the legacy database target, migrate the server, and recreate the target with the canonical string afterward.
3. For a fresh SILO installation, create the target directly with the canonical string; no legacy migration is involved.
4. For an existing SILO deployment that still reads a legacy JSON file, stop on the previous working release, back up the source configuration, then convert, disable, or remove the database target before starting the fixed release. Do not delete or rewrite unrelated configuration.

Documentation must not suggest that a discrete-only target will be converted automatically.

## Availability trade-off {#availability-trade-off}

This decision intentionally turns one unsupported configuration from a degraded startup into a hard startup failure. The immediate availability cost is real: a server that previously served objects while all notifications were silently dead may refuse to start after the repair.

That cost is accepted because an object server that appears healthy while configured event sinks are absent creates silent, potentially unrecoverable downstream data loss. SILO is a new fork with an explicit migration boundary, and the discrete form has been deprecated since 2020. A fatal, actionable precondition is preferable to an upgrade that reports success with reduced notification coverage. The release note must make this startup behavior prominent; it must not be buried as an internal migration cleanup.

## Security requirements {#security-requirements}

1. The unsupported-input error must never format the legacy argument structure or its values.
2. Tests must use a sentinel password and assert that it is absent from returned errors and captured logs.
3. Migrated output must contain the registered sensitive connection-string key and no standalone password key.
4. If a diagnostic bundle was exported from an affected deployment before this repair, operators should treat the database password as potentially disclosed and rotate it.

## Alternatives considered {#alternatives}

### Register and parse the discrete fields {#alternative-register}

**Benefit:** preserves the old source form and uses already existing argument fields.  
**Rejected because:** registration makes common field names visible to the shared tokenizer and corrupts quoted connection strings. It also expands the supported public configuration surface after the fields were deprecated in 2020.

### Synthesize a canonical string during migration {#alternative-synthesize}

**Benefit:** preserves discrete-only legacy installations.  
**Rejected because:** it creates permanent code and test ownership for an obsolete input form, including PostgreSQL quoting, MySQL DSN formatting, socket and IPv6 behavior, defaults, and future driver drift. For a new fork with an explicit migration boundary, the benefit does not justify the continuing surface.

### Skip only the unsupported target {#alternative-skip}

**Benefit:** keeps the object server and other notification targets running.  
**Rejected because:** silently discarding a configured event sink can cause unobservable and unrecoverable event loss. A clear migration failure is safer than an apparently successful upgrade with reduced notification coverage.

### Change global notification fail-fast behavior {#alternative-fail-fast}

**Benefit:** limits the blast radius of future invalid targets.  
**Rejected for this change because:** it neither repairs the database target nor closes the credential-exposure path, and it changes system-wide error semantics. It may be evaluated independently with its own operational contract.

### Remove database notification targets {#alternative-remove-targets}

**Benefit:** removes the complete database-specific maintenance surface.  
**Rejected because:** the targets remain useful and self-contained. The defect belongs to an obsolete configuration form, not to the notification capability itself.

## Implementation scope {#implementation-scope}

The server change should remain narrow:

1. Update `internal/config/notify/legacy.go` so the two database setters emit only canonical registered keys and reject enabled targets without a canonical string.
2. Update `cmd/config-migrate.go` to propagate the two database-helper errors with subsystem and target context.
3. Define a typed database-migration error and update `cmd/server-main.go` so `initConfigSubsystem` returns it as fatal instead of logging and ignoring it. It must remain non-retriable.
4. Leave ignored errors from the other eight legacy notification setters unchanged in this patch; record them for a separate audit rather than expanding #53 implicitly.
5. Remove all ten Postgres/MySQL entries from `knownUnregisteredWrites`; the ratchet should become empty unless another independently justified legacy exception exists.
6. Add focused migration, startup, validation, secrecy, and coexistence tests.
7. Update database-notification and migration documentation in `silo.pgsty.com`.

The patch must not register the old keys, change the generic tokenizer, or refactor unrelated notification targets.

## Acceptance criteria {#acceptance-criteria}

The implementation is complete only when all of the following are demonstrated:

1. A legacy PostgreSQL target with a complete connection string migrates, passes `CheckValidKeys`, and is returned by `GetNotifyPostgres` unchanged.
2. A legacy MySQL target with a complete DSN does the equivalent.
3. Discrete-only enabled targets for both databases fail before target initialization with an actionable error containing the subsystem and target name, and server startup aborts.
4. Missing-string and malformed-string errors contain none of the sentinel host, username, password, database, or DSN values.
5. Disabled discrete legacy targets do not create configuration entries and do not block migration.
6. Migrated KVS output contains none of the ten discrete keys, including empty ones.
7. When a legacy target contains both a canonical string and conflicting discrete values, only the canonical string is migrated and no discrete sentinel appears in any output KVS value.
8. A `SetKVS` regression test using the real `DefaultPostgresKVS` and `DefaultMySQLKVS` key sets accepts a quoted connection string containing `port=`, `host=`, or `password=`.
9. A configuration containing healthy Webhook, Kafka, or NATS targets cannot reach `FetchEnabledTargets` with an invalid migrated database target because `readConfigWithoutMigrate` fails without yielding, persisting, or activating a partial configuration, and startup aborts on that typed error.
10. `initConfigSubsystem` returns the typed migration error; it neither logs-and-continues nor enters the retriable loop.
11. `knownUnregisteredWrites` no longer contains Postgres or MySQL exceptions.
12. The following verification passes:

    ```sh
    go test ./internal/config/notify ./internal/config ./internal/event/target -count=1
    go test -v ./cmd -run 'Test(ReadConfigWithoutMigrate|InitConfigSubsystem)' -count=1
    git diff --check
    ```

    The verbose `cmd` output must show that tests with both prefixes actually ran; a zero-match warning is a failed acceptance check. The normal server CI suite must also pass. In the documentation checkout, run `make check`.

## Implementation result {#implementation-result}

Server commit [`f1ba68358`](https://github.com/pgsty/silo/commit/f1ba68358) implements the accepted design without expanding the public configuration surface:

- the two legacy database setters emit only `connection_string` or `dsn_string` plus registered target settings;
- disabled targets remain ignored, while enabled targets without a canonical string return a value-free `LegacyDatabaseTargetError`;
- only the two database migration errors are newly propagated;
- the typed error is non-retriable, escapes `initConfigSubsystem`, and is classified as fatal by `serverMain` before `logger.FatalIf` exits the process;
- the ten Postgres/MySQL exceptions were removed from `knownUnregisteredWrites`;
- focused tests cover complete-string round trips, canonical precedence, discarded discrete values, secrecy, failed-migration atomicity, startup classification, and the real tokenizer key sets.

The final local Claude Code review used Claude Fable 5 at `max` effort and returned **GO** with high confidence and no blocking findings. Verification included the focused package set, race tests, `go vet ./cmd`, and the complete `go test ./cmd -count=1` suite. The review authorized only the six-file server commit; publication remains a separate gate.

Cross-repository review found no implementation changes are required in `pgsty/mc`, `pgsty/silo-pkg`, or `pgsty/silo-console`: the client forwards configuration text, the package repository owns no notification schema, and Console already serializes its form into the canonical `connection_string` or `dsn_string`. The public reference and compatibility documentation is updated with this record.

## Release and compatibility statement {#release}

The release note must describe this as an enforced compatibility boundary:

> SILO database notification targets require `connection_string` for PostgreSQL and `dsn_string` for MySQL. The pre-2020 discrete `host`/`port`/`username`/`password`/`database` form is not migrated. Convert or recreate such targets before switching the deployment to SILO.

Deployments already running SILO with an old-format source configuration are equally affected: after this release the server will not start until each enabled legacy database target is converted, disabled, or removed.

The issue should close only after the repair is present in a published server tag. A merged patch, a local site build, and a published release are separate completion gates.

## Review record {#review-record}

Claude Fable 5 reviewed the first draft at `xhigh` effort on 2026-08-23 and returned **approve with required changes**. The required calibration was incorporated: startup-fatal propagation now extends through `initConfigSubsystem`; already-running SILO deployments are covered; the availability trade-off is explicit; canonical-string precedence, dead legacy environment variables, other ignored helper errors, and executable tests are specified.

The same model then completed a final source-backed verification pass. Final verdict: **approve**, with no blocking findings. It confirmed that the English and Chinese records are aligned, the requirements are implementable against the current server tree, and the acceptance criteria cover the startup, migration, parser-regression, and secrecy boundaries.

After implementation, a separate local Claude Code review using Claude Fable 5 at `max` effort traced the path through `ExitFunc(1)`, inspected driver error behavior, ran the focused, race, vet, and full `cmd` suites, and returned **GO** with high confidence and no blocking findings.

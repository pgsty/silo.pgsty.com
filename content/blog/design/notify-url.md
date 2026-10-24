---
linkTitle: "Database notification migration"
title: "DSN-Only Database Notifications: A Compatibility Boundary for #53"
date: 2026-08-23
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  SILO retains PostgreSQL and MySQL notification targets while standardizing their configuration on complete connection strings. Pre-KV discrete database fields are an unsupported migration input and abort server startup with an explicit error instead of silently disabling every bucket notification.
tags: [Design, Notification, Compatibility]
weight: 10
draft: false
url: "/blog/design/notify-url/"
---

Shipped in [SILO Server 20260903](/blog/release/silo-20260903/) via commit [`f1ba68358`](https://github.com/pgsty/silo/commit/f1ba68358), this design resolves [SILO issue #53](https://github.com/pgsty/silo/issues/53) by establishing the compatibility boundary, legacy-migration behavior, and startup error handling for PostgreSQL and MySQL bucket-notification targets.

## Decision {#decision}

SILO retains PostgreSQL and MySQL notification targets and standardizes each on a single canonical configuration key:

- PostgreSQL requires a complete `connection_string`.
- MySQL requires a complete `dsn_string`.

The pre-2020 five-field form—`host`, `port`, `username`, `password`, and `database`—remains unsupported by the KV configuration system. SILO does not register those five keys and does not synthesize a DSN from them during legacy JSON migration.

The legacy migration contract handles three input states:

| Legacy Target State | Migration Result |
| --- | --- |
| Disabled | Ignored; no KV target is emitted. |
| Enabled with a non-empty `connection_string` or `dsn_string` | Migrates only the canonical connection-string key and registered target settings. |
| Enabled with only discrete connection fields | Rejects migration and aborts server startup before activating the new configuration, logging an actionable error that names the subsystem and target without printing credentials. |

## Context {#context}

SILO inherited two generations of database-notification configuration from upstream MinIO. The pre-KV JSON configuration could represent a database connection either as a single connection string or as five discrete fields:

```text
host
port
username
password
database
```

The current KV configuration system exposes only the driver-native connection string:

```text
notify_postgres  -> connection_string
notify_mysql     -> dsn_string
```

Upstream deprecated the five discrete fields in `RELEASE.2020-04-10T03-34-42Z` and directed operators to migrate to `connection_string` or `dsn_string`. SILO's CLI help tables, environment-variable documentation, and Console UI already use the complete connection string as the supported interface.

## The Defect {#defect}

Before [`f1ba68358`](https://github.com/pgsty/silo/commit/f1ba68358), the legacy migration helpers `SetNotifyPostgres` and `SetNotifyMySQL` wrote both representations into the new KV configuration. Even when the legacy JSON target already specified a complete `connection_string` or `dsn_string`, the helpers also emitted all five discrete keys (typically with empty values).

The KV parser rejected those migrated entries because neither `DefaultPostgresKVS` nor `DefaultMySQLKVS` registers the five discrete keys, and `CheckValidKeys` validates key names regardless of whether their values are empty. Both legacy JSON forms therefore failed KV validation:

```text
old complete string -> canonical string + five empty unknown keys -> rejected
old discrete fields -> empty canonical string + five populated unknown keys -> rejected
```

Notification initialization amplified the impact of that parser error. `FetchEnabledTargets` evaluates notification subsystems fail-fast: the first invalid subsystem returns an error and a `nil` target list. The caller logged the error and continued starting the object server, leaving healthy Webhook, Kafka, NATS, and other notification targets disabled as well.

Simply returning an error from `SetNotifyPostgres` and `SetNotifyMySQL` was not sufficient on its own. While that error propagates through `readConfigWithoutMigrate` and `initConfig`, `initConfigSubsystem` previously logged non-retriable configuration errors as `"some features may be missing"` and returned success. The server then started without assigning `globalServerConfig`, leaving not only notifications broken but also region, storage class, compression, identity, and other persisted settings unapplied. Conversely, marking the error as retriable would cause the server to loop indefinitely on a static configuration error. The migration failure therefore has to propagate as a typed, non-retriable, startup-fatal error (`LegacyDatabaseTargetError`).

This failure mode was particularly hazardous because S3 object reads and writes continued normally while every configured event pipeline was offline. In addition, the unregistered `password` key lacked secret-redaction metadata and could be included in plain text inside diagnostic bundles, whereas `connection_string` and `dsn_string` are registered as sensitive keys.

## Why the First Fix Was Reverted {#reverted-fix}

An initial fix in `20260804` ([`SN-2026-019`](/blog/security/notify-keyspace-registration/)) registered the five discrete keys in `DefaultPostgresKVS` and `DefaultMySQLKVS` and wired the parser to read them. While that allowed migrated targets to pass `CheckValidKeys`, it broke the documented `connection_string` interface.

The shared `mcli admin config set` KV tokenizer identifies key/value boundaries by scanning for registered key names and is not quote-aware. Once `port` was registered as a top-level key in `notify_postgres`, a valid libpq key/value connection string inside quotes looked like a second top-level KV parameter:

```text
connection_string="host=db port=5432 dbname=events user=app"
```

The tokenizer split the input at `port=` inside the quoted string, truncated `connection_string` to `"host=db`, and passed `5432 dbname=events user=app"` to the integer `port` parser, failing with `invalid port`.

Under the shared KV tokenizer grammar, registering common words such as `host`, `port`, and `password` creates an irreconcilable grammar collision with key/value connection strings. That registration change was therefore reverted in favor of enforcing `connection_string` and `dsn_string` exclusively.

## Product Judgment {#product-judgment}

Database notification targets provide a direct database-backed namespace view or access journal without requiring an external message broker, which remains valuable for deployments already operating PostgreSQL or MySQL.

By contrast, the five-field parameter model cannot express standard driver options such as TLS modes and CA paths, connect timeouts, application names, Unix domain sockets, multi-host PostgreSQL failover, or MySQL driver flags. Maintaining both forms also creates precedence, merging, and secret-redaction ambiguity. Keeping SILO responsible for notification delivery semantics while delegating connection syntax to the database driver's native DSN string provides a clean boundary.

## Goals {#goals}

1. Establish `connection_string` and `dsn_string` as the sole supported configuration keys for PostgreSQL and MySQL notifications.
2. Allow legacy JSON targets that already contain a non-empty canonical connection string to migrate cleanly.
3. Reject enabled discrete-only legacy targets before activating or persisting a partial KV configuration.
4. Replace silent runtime notification failure with an explicit startup-time failure (`LegacyDatabaseTargetError`).
5. Ensure no migration error, log line, health report, or diagnostic bundle leaks a database password.
6. Remove all ten Postgres/MySQL exceptions from the `knownUnregisteredWrites` audit ratchet.
7. Document operator remediation paths clearly.

## Non-Goals {#non-goals}

- Supporting both DSN strings and discrete database fields in the KV interface.
- Synthesizing a DSN string from legacy discrete fields during migration.
- Rewriting the shared KV tokenizer grammar.
- Altering `FetchEnabledTargets` fail-fast semantics across notification subsystems.
- Silently skipping an enabled invalid database target and starting with partial notification coverage.
- Removing PostgreSQL or MySQL notification support.
- Deleting the legacy Go struct fields used to unmarshal old JSON files and detect unsupported discrete-only configurations.
- Changing error handling for the other eight legacy notification setters outside PostgreSQL and MySQL.

## Functional Requirements {#functional-requirements}

### Current Configuration {#current-configuration}

1. `notify_postgres` accepts `connection_string`; `notify_mysql` accepts `dsn_string`.
2. The five discrete keys (`host`, `port`, `username`, `password`, `database`) remain unregistered and are rejected by `admin config set`.
3. Complete connection strings continue to support native driver syntax, including embedded `host=`, `port=`, `user=`, `password=`, and `dbname=` tokens.
4. Legacy environment variables `MINIO_NOTIFY_POSTGRES_HOST`/`PORT`/`USERNAME`/`PASSWORD`/`DATABASE` and their MySQL equivalents remain unwired and unsupported.

### Legacy Migration {#legacy-migration}

1. `SetNotifyPostgres` and `SetNotifyMySQL` return `nil` without emitting a target when the legacy target is disabled (`Enable == false`).
2. When enabled, `SetNotifyPostgres` requires a non-empty `ConnectionString` and writes only registered Postgres keys. If both `ConnectionString` and discrete fields are present in the legacy JSON, `ConnectionString` wins and the discrete values are discarded.
3. `SetNotifyMySQL` applies the identical rule to `DSN`.
4. Neither helper ever emits `host`, `port`, `username`, `password`, or `database`.
5. An enabled target with an empty canonical connection string returns a `LegacyDatabaseTargetError` identifying the subsystem (`notify_postgres` or `notify_mysql`) and target ID without echoing field values:

```text
notify_postgres:archive uses unsupported legacy discrete connection fields;
set connection_string before migrating to SILO
```

6. `cmd/config-migrate.go` checks and propagates errors from both database migration helpers before persisting or activating the migrated configuration.
7. `initConfigSubsystem` propagates `LegacyDatabaseTargetError` as a non-retriable fatal error to `serverMain`.

### Operator Remediation {#operator-remediation}

Because legacy JSON migration output is only persisted after a successful migration pass, a deployment that still boots from an old JSON configuration file will re-enter migration on startup. Operators with enabled discrete-only database targets should follow one of four paths:

1. **Before migrating to SILO:** On the prior release, replace the discrete fields with `connection_string` or `dsn_string`, verify event delivery, and then upgrade.
2. **Disable and recreate:** Disable or remove the legacy database target, upgrade the server, and recreate the target using `connection_string` or `dsn_string`.
3. **Fresh installation:** Configure `notify_postgres` or `notify_mysql` directly with `connection_string` or `dsn_string`.
4. **Existing deployment reading legacy JSON:** Back up the source configuration, then convert, disable, or remove the discrete database target before starting SILO Server 20260903 or later.

## Availability Trade-Off {#availability-trade-off}

This design intentionally converts an unsupported legacy database target from a degraded startup (where S3 I/O works while all bucket notifications are silently offline) into an immediate startup abort. An object store that appears healthy while dropping every configured audit or pipeline event creates unrecoverable downstream data loss; failing fast at startup forces the configuration error to be resolved before traffic is served.

## Security Requirements {#security-requirements}

1. `LegacyDatabaseTargetError` never formats the legacy struct or its field values into the error message.
2. Regression tests inject sentinel passwords and assert that neither returned errors nor captured logs contain the sentinel.
3. Migrated KV output uses only the registered sensitive keys (`connection_string` and `dsn_string`).
4. Operators who exported diagnostic bundles from an affected pre-20260903 deployment with discrete database targets should rotate that database password.

## Rejected Alternatives {#alternatives}

### Register and Parse the Five Discrete Fields {#alternative-register}

**Benefit:** Preserves the pre-2020 JSON field names and reuses existing struct fields.<br>
**Reason rejected:** Registering `host`, `port`, and `password` causes the shared KV tokenizer to split quoted `connection_string` values containing `port=` or `host=`, breaking the primary documented interface.

### Synthesize a Canonical Connection String During Migration {#alternative-synthesize}

**Benefit:** Automatically converts discrete-only legacy configurations.<br>
**Reason rejected:** Requires permanent code and test maintenance for PostgreSQL quoting rules, MySQL DSN escaping, Unix sockets, IPv6 brackets, and driver defaults for a format deprecated since 2020.

### Skip Only the Unsupported Target {#alternative-skip}

**Benefit:** Keeps S3 object service and other notification targets online.<br>
**Reason rejected:** Silently dropping an enabled notification target causes unannounced event loss.

### Change Global `FetchEnabledTargets` Fail-Fast Behavior {#alternative-fail-fast}

**Benefit:** Isolates failures between independent notification subsystems.<br>
**Reason rejected:** Does not fix the broken database migration helper or the unredacted `password` key, and alters system-wide notification startup semantics outside the scope of `#53`.

### Remove Database Notification Targets Entirely {#alternative-remove-targets}

**Benefit:** Eliminates all database-specific notification code.<br>
**Reason rejected:** PostgreSQL and MySQL notification targets remain useful and self-contained; the defect lies solely in the obsolete five-field configuration format.

## Implementation Scope {#implementation-scope}

The implementation in [`f1ba68358`](https://github.com/pgsty/silo/commit/f1ba68358) touches six files across `internal/config/notify/legacy.go`, `cmd/config-migrate.go`, and `cmd/server-main.go`:

1. Update `internal/config/notify/legacy.go` so the two database setters emit only canonical registered keys and reject enabled targets lacking a canonical string.
2. Update `cmd/config-migrate.go` to propagate the two database helper errors with subsystem and target context.
3. Define `LegacyDatabaseTargetError` and update `cmd/server-main.go` so `initConfigSubsystem` returns it as a non-retriable fatal error instead of logging and continuing.
4. Remove all ten Postgres/MySQL entries from `knownUnregisteredWrites`.

## Acceptance Criteria {#acceptance-criteria}

1. Legacy PostgreSQL targets with a non-empty `connection_string` migrate cleanly, pass `CheckValidKeys`, and round-trip through `GetNotifyPostgres`.
2. Legacy MySQL targets with a non-empty `dsn_string` migrate cleanly, pass `CheckValidKeys`, and round-trip through `GetNotifyMySQL`.
3. Enabled discrete-only targets for either database fail before target initialization with `LegacyDatabaseTargetError` naming the subsystem and target ID, aborting server startup.
4. Missing-string and malformed-string errors never include sentinel host, username, password, database, or DSN values.
5. Disabled discrete legacy targets emit no KVS entries and do not block startup.
6. Migrated KVS output never contains any of the ten discrete keys, even with empty values.
7. When a legacy target contains both a canonical string and conflicting discrete values, only the canonical string is migrated.
8. `SetKVS` regression tests against `DefaultPostgresKVS` and `DefaultMySQLKVS` accept quoted connection strings containing `port=`, `host=`, and `password=`.
9. Configurations pairing healthy Webhook, Kafka, or NATS targets with an invalid legacy database target fail in `readConfigWithoutMigrate` without persisting or activating partial state.
10. `initConfigSubsystem` returns `LegacyDatabaseTargetError` directly without logging-and-continuing or entering the retry loop.
11. `knownUnregisteredWrites` removes all ten Postgres/MySQL exceptions.
12. All unit, race, and startup suites pass:

```sh
go test ./internal/config/notify ./internal/config ./internal/event/target -count=1
go test -v ./cmd -run 'Test(ReadConfigWithoutMigrate|InitConfigSubsystem)' -count=1
```

## Implementation Result {#implementation-result}

Commit [`f1ba68358`](https://github.com/pgsty/silo/commit/f1ba68358) implements the design without expanding the public configuration surface. Cross-repository verification confirmed that `pgsty/mc`, `pgsty/silo-pkg`, and `pgsty/silo-console` require no changes because `mcli` forwards raw KV text and Console already serializes database forms into `connection_string` and `dsn_string`.

### Release Compatibility Statement {#release}

SILO database notification targets require `connection_string` for PostgreSQL and `dsn_string` for MySQL. The pre-2020 discrete `host`/`port`/`username`/`password`/`database` form is not migrated; convert, disable, or remove such targets before upgrading to [SILO Server 20260903](/blog/release/silo-20260903/) or later.

### Design Review Calibration {#review-record}

During design review of the initial specification, four calibrations were incorporated before landing the commit:

- extending fatal error propagation through `initConfigSubsystem` to `ExitFunc(1)` so `serverMain` terminates via `logger.FatalIf` instead of starting without `globalServerConfig`;
- documenting that existing deployments still booting from unmigrated legacy JSON files also hit the startup gate;
- specifying canonical-string precedence when a legacy JSON record contains both `ConnectionString`/`DSN` and leftover discrete fields;
- leaving error handling of the other eight non-database legacy notification setters unchanged to keep `#53` tightly scoped.

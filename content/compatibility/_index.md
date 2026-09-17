---
title: "Compatibility"
linkTitle: "Compatibility"
description: "Can SILO replace MinIO? A user-facing index of 12 compatible improvements, 4 minor differences, and 8 changes to check when their conditions apply."
url: "/compatibility/"
weight: 7
type: docs
icon: fa-solid fa-code-compare
sidebar_expanded: true
---

**Most applications using standard S3 APIs can switch from MinIO to SILO without code changes.** Common S3 APIs, SigV4, SDK integration and object storage layouts carry over. Deployment, authorization and replicated state require the checks below: SILO is a **conditional drop-in replacement**.

{{< cards >}}
{{< card title="🟢 12 compatible improvements" link="#compatible" >}}
Normal usage needs no adaptation and gains capabilities or correctness fixes.
{{< /card >}}
{{< card title="🔵 4 minor differences" link="#minor" >}}
Mostly presentation, UI interaction and response information; usually no application changes.
{{< /card >}}
{{< card title="🟠 8 conditional checks" link="#conditional" >}}
When a condition applies, verify or adjust deployment, policies, tools or upgrade procedures.
{{< /card >}}
{{< /cards >}}

**Reviewed: 2026-09-16.** This index covers source and companion-component changes since the fork. The published Server on that date is still **20260903**; later source fixes are not part of that release. Check the [component matrix](/compatibility/versions/) for delivery status. The 24 entries group user scenarios; they are **not API counts, compatibility percentages or failure probabilities**.

## 🟢 Compatible improvements: 12 categories {#compatible}

Normal usage needs no migration work for these capabilities. Dependencies on old bugs, mixed versions or damaged historical state are covered by the orange entries.

| Category and change | When it applies | Impact and action | Details |
| --- | --- | --- | --- |
| <span id="g01"></span>**G01 · Full Web administration**<br>Restores full Web management of buckets, objects, users, policies and the system. | Managing a deployment in a browser. | More capable administration; ordinary S3 applications need no changes. | [Console features](/compatibility/console/#scope) |
| <span id="g02"></span>**G02 · Chinese UI and text preview**<br>Adds English/Chinese UI and bounded, safe text preview. | Switching language or previewing text objects. | Changes the Console experience, not stored object content. | [Languages](/compatibility/console/#i18n), [text preview](/blog/design/console-text-preview/) |
| <span id="g03"></span>**G03 · Per-bucket CORS**<br>The existing CORS APIs now persist and enforce per-bucket cross-origin rules. | Browser cross-origin access with bucket CORS configured. | Bucket rules override global CORS; object access still requires authorization. | [CORS behavior](/blog/release/silo-20260903/#cors-trust) |
| <span id="g04"></span>**G04 · Native health checks**<br>Adds `silo healthcheck` for container and operational probes. | Choosing to use the new probe command. | Existing HTTP health endpoints remain available. | [Command and scope](/compatibility/feature/healthcheck/#command) |
| <span id="g05"></span>**G05 · Client checksum audit**<br>Adds `mcli checksum verify` to read objects and verify checksums. | Explicitly running an integrity audit. | Read-only checks and reports; no object modification or repair. | [Audit command](/reference/minio-mc/mc-checksum-verify/#command-mc.checksum.verify) |
| <span id="g06"></span>**G06 · Upload and copy checksums**<br>Valid uploads, multipart completion and copies compute, retain and return checksums more accurately. | Using the affected upload or copy paths. | Better SDK interoperability; invalid requests are covered by [O04](#o04). | [Multipart uploads](/blog/design/uploadpart-checksum/#decision), [S3 fixes](/blog/release/silo-20260903/#s3-correctness) |
| <span id="g07"></span>**G07 · Encryption and compression fixes**<br>Corrects data and logical-size handling across SSE-C, KMS, compression and copying. | Using these encryption, compression or copy combinations. | Improves new requests; it does not automatically repair all historical damage. | [SSE-C and old objects](/blog/design/ssec-replica-integrity/), [federated copies](/blog/design/federated-copy-object/) |
| <span id="g08"></span>**G08 · Concurrent bucket configuration**<br>A shared metadata lock prevents concurrent bucket updates from overwriting each other. | Concurrent policy, lifecycle, encryption or other bucket updates. | More reliable administration with the same calling pattern. | [Shared configuration lock](/blog/release/silo-20260903/#bucket-metadata) |
| <span id="g09"></span>**G09 · Tag and Object Lock replication**<br>Replication preserves and orders tag, retention and lock state more accurately. | Replicating or healing tags and Object Lock metadata. | Reduces lost state and stale-event overwrites; see [O07](#o07) for mixed versions. | [Tag ordering](/blog/design/replicated-tag-ordering/), [lock ordering](/blog/design/object-lock-replication-ordering/) |
| <span id="g10"></span>**G10 · Pool migration and healing**<br>Rebalance, decommission and recovery handle tags, versions and delete markers more accurately. | Moving pools, healing or recovering replication. | Better metadata preservation and retries; historical anomalies still need inspection. | [Multi-pool consistency](/blog/design/multi-pool-object-consistency/), [replication recovery](/blog/design/replication-reliability/) |
| <span id="g11"></span>**G11 · Notifications and streaming**<br>Fixes NATS/AMQP setting recognition and flushing of notification and Select streams. | Using those notification targets or streaming APIs. | More accurate configuration and event output; see [O03](#o03) for old database settings. | [Notification settings](/compatibility/server/#notify-audit), [stream flushing](/compatibility/server/#s3-behavior) |
| <span id="g12"></span>**G12 · Stability and resource cleanup**<br>Fixes concurrent collection, buffer ownership and connection cleanup. | Concurrent I/O, metric collection or request cancellation. | Reduces related crashes and resource problems; no universal speedup is implied. | [Read buffers](/compatibility/server/#s3-behavior), [runtime and metrics](/compatibility/server/#observability) |
{.silo-compatibility-table}

## 🔵 Minor differences: 4 categories {#minor}

Ordinary applications usually need no changes. Tools that hard-code product strings, metric meanings or response fields should still be checked.

| Category and change | When it applies | Impact and action | Details |
| --- | --- | --- | --- |
| <span id="b01"></span>**B01 · Product identity**<br>Banners, logs, HTTP product identity and UI labels use SILO. | Reading output or matching product names. | Presentation changes; adapt name-matching scripts. Installation changes are in [O01](#o01). | [Server identity](/compatibility/server/#identity), [client output](/compatibility/mcli/#identity) |
| <span id="b02"></span>**B02 · Paginated Console listings**<br>Object listings use cursors, with sorting, filtering and selection limited to the current page. | Browsing, filtering or selecting objects in Console. | UI habits change; direct S3 application access does not. | [Pagination boundaries](/compatibility/console/#pagination) |
| <span id="b03"></span>**B03 · Richer monitoring and diagnostics**<br>Adds diagnostic metrics and corrects quota, replication counters and status meanings. | Using affected metrics, dashboards or alerts. | Metric namespaces remain; review the affected displays and alert rules. | [Metric changes](/compatibility/server/#observability), [Console metrics](/compatibility/console/#metrics) |
| <span id="b04"></span>**B04 · Additional response fields**<br>Some copy, multipart and Console responses include checksum or session fields. | Reading those API responses. | Standard clients usually handle them; parsers rejecting unknown fields belong in [O05](#o05). | [Multipart responses](/blog/design/complete-multipart-checksum-type/), [copy responses](/blog/design/copyobject-ssec-checksum-response/#impact), [Console API](/compatibility/console/#api-output) |
{.silo-compatibility-table}

## 🟠 Conditional checks: 8 categories {#conditional}

**If the condition applies, check the entry.** These are not necessarily rare: deployment naming affects migrating administrators, while custom signing mainly affects custom clients.

| Category and change | When it applies | Impact and action | Details |
| --- | --- | --- | --- |
| <span id="o01"></span>**O01 · Installation and startup**<br>Artifacts become `silo` / `mcli`; verify services, images, directories and permissions. | Migrating MinIO packages, containers, systemd or Helm. | Administrators perform a deployment migration check; application code usually stays the same. | [Containers](/compatibility/migration/#docker), [packages and accounts](/compatibility/binary/#layout), [client configuration](/compatibility/mcli/#naming) |
| <span id="o02"></span>**O02 · Custom authorization policies**<br>Password changes, permanent version deletion and some bucket operations use corrected authorization rules. | Custom Allow/Deny rules, object ARNs granting bucket operations, or source-IP conditions. | Effective permissions may change; verify policies and proxy trust. | [Passwords](/compatibility/password-permissions/#preserve-the-behavior-of-existing-policies), [version deletion](/compatibility/migration/#since-20260806), [bucket authorization](/blog/security/object-grant-bucket-reach/), [proxy trust](/compatibility/server/#trusted-proxies) |
| <span id="o03"></span>**O03 · Older auth and notification settings**<br>Legacy authentication, database notifications and some TLS/environment-file usage need adjustment or validation. | OIDC HMAC tokens, discrete legacy database settings, old proxies/TLS or unusual environment files. | Login, notifications or startup may fail; migrate the relevant configuration. | [OIDC algorithms](/compatibility/server/#auth-iam), [database connections](/blog/design/notify-url/#operator-remediation), [TLS](/blog/design/go127-tls-oidc-discovery/), [environment files](/blog/design/config-env-file/#compatibility) |
| <span id="o04"></span>**O04 · Programs relying on old bugs**<br>Validation, conditions, errors, exit codes and listing limits change on affected paths. | Expecting invalid requests to succeed, `If-Match` to be ignored, or more than 1,000 multipart uploads per page. | Check error handling, retries, pagination and final batch exit codes. | [Checksum errors](/blog/design/complete-multipart-checksum-errors/#impact), [conditional deletion](/blog/design/conditional-delete/), [multipart listing](/blog/design/list-multipart-uploads/#implementation), [CLI exit codes](/compatibility/mcli/#current-release) |
| <span id="o05"></span>**O05 · Custom clients and administration tools**<br>Private APIs, signed-header coverage, Console automation and Go package paths have changed. | Using `ReadMultiple`, custom signing, strict parsing, Go embedding or customized Console clients. | Verify custom integrations and builds separately; ordinary S3 SDKs do not use the private storage API. | [Private APIs](/compatibility/server/#storage-rest), [signing](/blog/design/signed-header-coverage/#impact), [Console API](/compatibility/console/#api-output), [Go modules](/compatibility/server/#source-compatibility) |
| <span id="o06"></span>**O06 · Multi-pool conditions and strict multipart listing**<br>Multi-pool writes/deletes verify metadata more strictly; strict multipart listing needs upgrade preparation. | Multi-pool conditional writes, specific-version deletion or explicitly enabling strict listing. | Failures can return 503 while GET still works; strict needs all writers upgraded and old uploads drained. The default remains legacy. | [Multi-pool conditions](/blog/design/multi-pool-object-consistency/#conditions), [strict-mode contract](/blog/design/list-multipart-uploads/#implementation) |
| <span id="o07"></span>**O07 · Replication, mixed versions and rollback**<br>IAM revocations and bucket-configuration deletion state require coordinated upgrades and recovery. | Multiple sites, shared IAM, mixed versions or downgrades. | Preserve a complete recovery point and test all peers; replacing the binary alone is not a rollback guarantee. | [IAM upgrades](/operations/replication/iam-upgrade/), [configuration convergence](/blog/design/bucket-metadata-convergence/#rollout), [rollback scope](/compatibility/migration/#rollback) |
| <span id="o08"></span>**O08 · Self-update and upstream online services**<br>In-place updates, SUBNET and upstream hosted-support integrations are disabled. | Using `admin update`, `mcli update` or MinIO online support workflows. | Upgrade through packages, images or orchestration; ordinary S3 access is unaffected by this change. | [Server updates](/compatibility/server/#offline-services), [client updates](/compatibility/mcli/#self-update), [SUBNET](/compatibility/mcli/#subnet) |
{.silo-compatibility-table}

## Comparison scope and release boundaries {#scope}

The server comparison starts at upstream source [`27742d469462`](https://github.com/minio/minio/commit/27742d469462e1561c776f88ca7a1f26816d69e2), dated **2025-12-03**. The commonly referenced final upstream release tag is dated **2025-10-15**; these are different comparison points. See the [Console](/compatibility/console/) and [client](/compatibility/mcli/) pages for their separate baselines. This index covers APIs, capabilities, observable behavior and operations; one fix can affect several scenarios.

Upstream MinIO/MC compatibility is **best effort**. The supported, release-tested combination is **SILO + SILO Console + mcli + silo-pkg**. Retained protocols, environment variables and storage layouts do not guarantee arbitrary upstream mixed-version operation or downgrades. The [detailed server audit](/compatibility/server/) retains historical baselines and individual findings; the [component matrix](/compatibility/versions/) separates published components from unreleased source.

The experimental [access-frequency pool tiering](/compatibility/access-tiering-removal/) that was added and later withdrawn is outside these 24 categories: it was not an upstream feature at the fork and never shipped in public Server 20260903. Ordinary lifecycle expiration, remote tiering, rebalance and pool decommission remain available.

For migration, select the relevant [O01–O08 conditions](#conditional), then follow the [migration guide](/compatibility/migration/).

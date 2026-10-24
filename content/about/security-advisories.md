---
title: "Security Advisories"
linkTitle: "Advisories"
description: "The PGSTY SILO security advisory ledger: CVE and SN-2026 identifiers, fix commits, affected subsystems, exposure boundaries, upgrade guidance, and dependency security updates."
url: "/about/security-advisories/"
weight: 41
type: docs
icon: fa-solid fa-shield-halved
---

This ledger summarizes security fixes and upgrade-impacting security notes across the `pgsty/silo` stack. Each advisory with its own deep-dive investigation links to its full article in the [Security Chronicle](/blog/security/) or [Design Notes](/blog/design/); this page serves as the canonical index of identifiers, fix commits, exposure conditions, and upgrade boundaries.

Entries with a public CVE use that identifier. Because upstream `minio/minio` is archived and no longer coordinates CVE assignments for inherited code, findings without a CVE carry a stable `SN-<year>-<sequence>` identifier (`SN-2026-002` through `SN-2026-019`) so release notes, commits, and issues can reference them unambiguously. `SN-2026-001` tracks a non-security streaming-flush regression in `trackingResponseWriter` ([Server 20260804](/blog/release/silo-20260804/)).

## Current Release Boundary {#boundary}

The current production baseline is **[Server 20261018](/blog/release/silo-20261018/)**, **[Console v2.4.2](/blog/release/console-2.4.2/)**, **[mcli 20261018](/blog/release/mcli-20261018/)**, and **[silo-pkg v3.14.3](/blog/release/pkg-3.14.3/)** (with unified Go 1.27.3 and dependency maintenance tracked in [20261024](/blog/release/silo-20261024/)):

- **Server 20261018** fixes [SN-2026-015](#sn-2026-015) (`PutObjectRetention` governance bypass), [SN-2026-016](#sn-2026-016) (version-addressed and in-place Object Lock overwrites), and [SN-2026-017](#sn-2026-017) (Admin credential authorization boundaries), and adds scoped STS token revocation (`0cd388c66`). Server 20260916 and earlier remain affected by `SN-2026-015` through `SN-2026-017`; deploy the upgrade to every Server node and replication peer accepting writes. See the [October security note](/blog/security/20261018-release-hardening/) and [Component Version Matrix](/compatibility/versions/).
- **Server 20260916** and **Console v2.4.1** include [SN-2026-011](#sn-2026-011) through [SN-2026-014](#sn-2026-014), which are absent from Server 20260903.
- **Server 20260903** includes [SN-2026-006](#sn-2026-006) through [SN-2026-010](#sn-2026-010).
- **Server 20260804** and **silo-pkg v3.11.0 / v3.12.0** include [SN-2026-002](#sn-2026-002) through [SN-2026-005](#sn-2026-005), [SN-2026-018](#sn-2026-018), and [SN-2026-019](#sn-2026-019).

## Inherited Upstream Advisory Baseline {#inherited}

SILO cut its first community release (`RELEASE.2025-12-03T12-00-00Z`) from upstream history that already contained `CVE-2025-62506`.

| ID | Upstream Remediation | SILO Inheritance | Summary & Release Note |
| :-- | :-- | :-- | :-- |
| [`CVE-2025-62506`](https://github.com/advisories/GHSA-jjjj-jwhf-8rgr) | [minio/minio#21642](https://github.com/minio/minio/pull/21642), merged as [`c1a49490`](https://github.com/minio/minio/commit/c1a49490c78e9c3ebcad86ba0662319138ace190) | [`pgsty/silo@c1a49490`](https://github.com/pgsty/silo/commit/c1a49490c78e9c3ebcad86ba0662319138ace190) | Resets `DenyOnly` while evaluating a restricted session policy so a service account or STS session cannot mint an unrestricted child service account. Upstream first fixed this in [`RELEASE.2025-10-15T17-29-55Z`](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z); every SILO release starting with [`RELEASE.2025-12-03T12-00-00Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2025-12-03T12-00-00Z) contains it. Operators migrating from an older upstream build should upgrade and audit service accounts created by restricted service or STS identities. See the [chronicle](/blog/security/cve-2025-62506/). |
| `CVE-2026-32285` | Same upstream commit [`c1a49490`](https://github.com/minio/minio/commit/c1a49490c78e9c3ebcad86ba0662319138ace190) ([pgsty/silo#26](https://github.com/pgsty/silo/issues/26)) | Already present (`v1.1.2` `buger/jsonparser`) | External vulnerability feeds mislabeled the `CVE-2025-62506` session-policy commit (`c1a49490`) as a `buger/jsonparser` vulnerability; `go.mod` already selects `v1.1.2` and `govulncheck` confirms no reachable vulnerable symbols. No code change required. See the [chronicle](/blog/security/cve-2026-32285/). |

## Advisories Since `RELEASE.2026-03-21T00-00-00Z` {#advisories}

| ID | Fixed By | Affected Area | Chronicle / Release Note |
| :-- | :-- | :-- | :-- |
| [`CVE-2026-33322`](#cve-2026-33322) | [`d24f449e0`](https://github.com/pgsty/silo/commit/d24f449e0) | OIDC STS (`AssumeRoleWithWebIdentity`, `AssumeRoleWithClientGrants`) | [Chronicle](/blog/security/cve-2026-33322/) |
| [`CVE-2026-33419`](#cve-2026-33419) | [`3b950f8fa`](https://github.com/pgsty/silo/commit/3b950f8fa) + follow-ups | LDAP STS authentication & rate limiting | [Chronicle](/blog/security/cve-2026-33419/) |
| [`CVE-2026-34204`](#cve-2026-34204) | [`56fa63bfd`](https://github.com/pgsty/silo/commit/56fa63bfd) | Replication metadata header sanitization | [Chronicle](/blog/security/cve-2026-34204/) |
| [`CVE-2026-39414`](#cve-2026-39414) | [`3252d5b7f`](https://github.com/pgsty/silo/commit/3252d5b7f), [`5dc705936`](https://github.com/pgsty/silo/commit/5dc705936) | S3 Select oversized CSV and JSON Lines records | [Chronicle](/blog/security/cve-2026-39414/) |
| [`CVE-2026-41145`](https://github.com/advisories/GHSA-hv4r-mvr4-25vw) | [`f444b6f37`](https://github.com/pgsty/silo/commit/f444b6f37) | `STREAMING-UNSIGNED-PAYLOAD-TRAILER` presigned query auth | [Chronicle](/blog/security/cve-2026-41145/) |
| [`CVE-2026-40344`](https://github.com/advisories/GHSA-9c4q-hq6p-c237) | [`efb6e5b00`](https://github.com/pgsty/silo/commit/efb6e5b00) | Snowball `PutObjectExtract` unsigned-trailer auth | [Chronicle](/blog/security/cve-2026-40344/) |
| [`CVE-2026-42600`](https://github.com/advisories/GHSA-xh8f-g2qw-gcm7) | [`73ac52472`](https://github.com/pgsty/silo/commit/73ac52472) (`73ac5244d`) | Internode `ReadMultiple` (`/rmpl`) path traversal | [Chronicle](/blog/security/cve-2026-42600/) |
| [`SN-2026-002`](#sn-2026-002) | [`ca7baa670`](https://github.com/pgsty/silo/commit/ca7baa670) .. [`a36fd8fff`](https://github.com/pgsty/silo/commit/a36fd8fff) | Internode RPC, peerREST, and `xlStorage` path/memory containment | [Chronicle](/blog/security/internode-path-containment/) |
| [`SN-2026-003`](#sn-2026-003) | [silo-pkg v3.11.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.11.0), [`2f55347f7`](https://github.com/pgsty/silo/commit/2f55347f78352aed8e08866d370c9426c73362cf), [`7a8fa5bc2`](https://github.com/pgsty/silo/commit/7a8fa5bc2), [`eb74f7e40`](https://github.com/pgsty/silo/commit/eb74f7e40) | S3 policy condition value sources (`s3:VersionId`, tags, `signatureAge`) | [Chronicle](/blog/security/s3-versionid-conditions/) |
| [`SN-2026-004`](#sn-2026-004) | `silo-pkg` [`v3.11.0`](https://github.com/pgsty/silo-pkg/releases/tag/v3.11.0) (`d8b1fa7`), [`97b7d2804`](https://github.com/pgsty/silo/commit/97b7d2804) | Bucket-level write isolation from object-only `arn:aws:s3:::bucket/*` grants | [Chronicle](/blog/security/object-grant-bucket-reach/) |
| [`SN-2026-005`](#sn-2026-005) | `silo-pkg` [`v3.12.0`](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.0) (`2b087a1`), [`eee05a17c`](https://github.com/pgsty/silo/commit/eee05a17c) | Bare ARN prefix (`arn:aws:s3:::`) rejection on policy writes | [Chronicle](/blog/security/s3-versionid-conditions/#sn-2026-005) · [pkg v3.12.0](/blog/release/pkg-3.12.0/) |
| [`SN-2026-006`](#sn-2026-006) | [`b73581b05`](https://github.com/pgsty/silo/commit/b73581b05), [`c4fd97d0b`](https://github.com/pgsty/silo/commit/c4fd97d0b), [`e2b0cf32f`](https://github.com/pgsty/silo/commit/e2b0cf32f) ([#82](https://github.com/pgsty/silo/issues/82)) | Zero-byte SSE-C object key authentication | [Chronicle](/blog/security/20260903-server-hardening/#sn-2026-006) |
| [`SN-2026-007`](#sn-2026-007) | [`474cd5801`](https://github.com/pgsty/silo/commit/474cd5801), [`74c97d005`](https://github.com/pgsty/silo/commit/74c97d005), [`21870fa2e`](https://github.com/pgsty/silo/commit/21870fa2e), [`e2b0cf32f`](https://github.com/pgsty/silo/commit/e2b0cf32f) ([#84](https://github.com/pgsty/silo/issues/84)) | `GetObjectAttributes` SSE-C key verification | [Chronicle](/blog/security/20260903-server-hardening/#sn-2026-007) |
| [`SN-2026-008`](#sn-2026-008) | [`938603458`](https://github.com/pgsty/silo/commit/938603458) .. [`04b097fd9`](https://github.com/pgsty/silo/commit/04b097fd9) | Post-auth trust boundary for internal `X-Minio-Source-*` headers | [Chronicle](/blog/security/20260903-server-hardening/#sn-2026-008) · [Design](/blog/design/cors-replication-trust/) |
| [`SN-2026-009`](#sn-2026-009) | [`58735ee38`](https://github.com/pgsty/silo/commit/58735ee38), [`229fe2b3c`](https://github.com/pgsty/silo/commit/229fe2b3c), [`0c8b02344`](https://github.com/pgsty/silo/commit/0c8b02344), [`4dbeb15d8`](https://github.com/pgsty/silo/commit/4dbeb15d8) | Target-state IAM action check for user/group enable vs. disable | [Chronicle](/blog/security/20260903-server-hardening/#sn-2026-009) · [Design](/blog/design/user-status-permissions/) |
| [`SN-2026-010`](#sn-2026-010) | [`75a6734e4`](https://github.com/pgsty/silo/commit/75a6734e4) .. [`d2d47a41f`](https://github.com/pgsty/silo/commit/d2d47a41f), [`04b097fd9`](https://github.com/pgsty/silo/commit/04b097fd9) ([#58](https://github.com/pgsty/silo/issues/58)) | Explicit object version deletion requires `s3:DeleteObjectVersion` | [Chronicle](/blog/security/20260903-server-hardening/#sn-2026-010) · [Release](/blog/release/delete-object-version-authorization/) |
| [`SN-2026-011`](#sn-2026-011) | [`123325430`](https://github.com/pgsty/silo/commit/123325430), [#173](https://github.com/pgsty/silo/pull/173), [#177](https://github.com/pgsty/silo/pull/177) | SigV4 `SignedHeaders` coverage across all `X-Amz-` headers | [Chronicle](/blog/security/20260913-signed-header-status/) · [Design](/blog/design/signed-header-coverage/) |
| [`SN-2026-012`](#sn-2026-012) | [`c4b5e1cb4`](https://github.com/pgsty/silo/commit/c4b5e1cb4), [#177](https://github.com/pgsty/silo/pull/177) | Presigned payload SHA-256 verification when supplied via header | [Chronicle](/blog/security/20260916-release-hardening/#sn-2026-012) |
| [`SN-2026-013`](#sn-2026-013) | [`f99ed829b`](https://github.com/pgsty/silo/commit/f99ed829b5eba549160725f035156c9e020b6a07), [`0cd388c66`](https://github.com/pgsty/silo/commit/0cd388c666f8211f552604ae73448a066e9c25ce) | Durable IAM revocation records and scoped STS revocation | [Chronicle](/blog/security/20260916-release-hardening/#sn-2026-013) · [Design](/blog/design/iam-revocations/) |
| [`SN-2026-014`](#sn-2026-014) | [`silo-console#56`](https://github.com/pgsty/silo-console/pull/56), [#209](https://github.com/pgsty/silo/pull/209) | Console anonymous share-download proxy path restriction | [Chronicle](/blog/security/20260916-release-hardening/#sn-2026-014) · [Console v2.4.1](/blog/release/console-2.4.1/) |
| [`SN-2026-015`](#sn-2026-015) | [`14042b5aa`](https://github.com/pgsty/silo/commit/14042b5aa3cbda79eb7aa79aa2ae6931e026e270), [#234](https://github.com/pgsty/silo/pull/234), [#235](https://github.com/pgsty/silo/pull/235) | `PutObjectRetention` authorization and governance-bypass enforcement | [Chronicle](/blog/security/20260926-governance-retention-bypass/) · [Design](/blog/design/governance-retention-bypass-repair/#sn-2026-015) |
| [`SN-2026-016`](#sn-2026-016) | [`14042b5aa`](https://github.com/pgsty/silo/commit/14042b5aa3cbda79eb7aa79aa2ae6931e026e270), [`0d3ba5d4c`](https://github.com/pgsty/silo/commit/0d3ba5d4cb1245b9f950f491ab0827c9d25fd338) | Version-addressed and in-place Object Lock overwrite prevention | [Chronicle](/blog/security/20261018-release-hardening/#object-lock) · [Design](/blog/design/governance-retention-bypass-repair/#sn-2026-016) |
| [`SN-2026-017`](#sn-2026-017) | [`2616d43fb`](https://github.com/pgsty/silo/commit/2616d43fb29fa0e97b875948f6e595163a72f56b), [`995439260`](https://github.com/pgsty/silo/commit/995439260), [#242](https://github.com/pgsty/silo/pull/242) | Delegated IAM Admin credential and policy containment boundaries | [Chronicle](/blog/security/20261018-release-hardening/#sn-2026-017) · [Design](/blog/design/iam-admin-authorization/) |
| [`SN-2026-018`](#sn-2026-018) | [`fe6dc4780`](https://github.com/pgsty/silo/commit/fe6dc4780) | Forwarded client IP trust boundary (`MINIO_API_TRUSTED_PROXIES`) | [Chronicle](/blog/security/source-address-trust/) |
| [`SN-2026-019`](#sn-2026-019) | [`672c07a0f`](https://github.com/pgsty/silo/commit/672c07a0f), [`f1ba68358`](https://github.com/pgsty/silo/commit/f1ba68358) | Notification key registration & `config.HasSensitiveKeys` credential redaction | [Chronicle](/blog/security/notify-keyspace-registration/) · [Design](/blog/design/notify-url/) |

## Exposure and Upgrade Guidance {#exposure}

### CVE-2025-62506 — Session-Policy Privilege Escalation {#cve-2025-62506}

Remote exploitation: yes (authenticated service account or STS session carrying an inline session policy). Upstream fixed the `DenyOnly` evaluation reset in `c1a49490` (`RELEASE.2025-10-15T17-29-55Z`), and every SILO release since `RELEASE.2025-12-03T12-00-00Z` inherits it. Operators migrating from an unpatched upstream MinIO release should upgrade and audit child service accounts created by restricted parent sessions. See the [CVE-2025-62506 chronicle](/blog/security/cve-2025-62506/).

### CVE-2026-32285 — Mislabeled `jsonparser` Advisory {#cve-2026-32285}

Public feeds describe `CVE-2026-32285` as a `buger/jsonparser` vulnerability, but its referenced upstream fix (`c1a49490`) is the session-policy commit for `CVE-2025-62506`. SILO already selects `github.com/buger/jsonparser v1.1.2` and `govulncheck` confirms no reachable vulnerable symbols. See the [CVE-2026-32285 investigation](/blog/security/cve-2026-32285/).

### CVE-2026-33322 — OIDC JWT Algorithm Confusion {#cve-2026-33322}

Remote exploitation: yes, if OIDC is enabled (`AssumeRoleWithWebIdentity` or `AssumeRoleWithClientGrants`) and an attacker knows or can guess `client_secret` to forge an `HS256`/`HS384`/`HS512` token. Commit `d24f449e0` binds JWT verification strictly to the provider's asymmetric JWKS keys and removes the `client_secret` HMAC fallback from `token.Parse`. Deployments that relied on symmetric HMAC id_tokens must switch their IdP to asymmetric signing (`RS256`, `ES256`, etc.).

### CVE-2026-33419 — LDAP STS Enumeration and DoS {#cve-2026-33419}

Remote exploitation: yes, if LDAP is configured (`AssumeRoleWithLDAPIdentity`). Returns a uniform `400 InvalidParameterValue` on authentication failure without leaking internal directory errors, bounds concurrent LDAP bind operations with a reserve/commit/cancel/refund lifecycle, and removes the shared per-username rate-limit bucket (which previously allowed an attacker who knew a victim's `LDAPUsername` to lock out that user from rotating source IPs). See the [LDAP STS chronicle](/blog/security/cve-2026-33419/).

### CVE-2026-34204 — Replication Metadata Injection {#cve-2026-34204}

Remote exploitation: yes. Blocks untrusted `X-Minio-Replication-*` headers on client `PutObject` and `CopyObject` requests from being stored as internal replication metadata and leaving objects unreadable. Upgrade any server that accepts untrusted object writes. See [SN-2026-008](#sn-2026-008) and [Replica Metadata Normalization](/blog/design/replica-metadata-normalization/) for the subsequent replication-header hardening.

### CVE-2026-39414 — S3 Select Oversized Record Memory Exhaustion {#cve-2026-39414}

Remote exploitation: yes (`s3:SelectObjectContent`). Rejects CSV and JSON Lines records exceeding 1 MiB (`maxCharsPerRecord`) with `OverMaxRecordSize` instead of buffering unbounded lines in memory. The April patch (`3252d5b7f`) enforced the limit on CSV and standard JSON readers; the June follow-up (`5dc705936`) routes JSON Lines on AVX2/AVX-512 CPUs through the bounded `json.PReader` instead of `simdj.NewReader`, closing the hardware-specific SIMD bypass. See the [S3 Select chronicle](/blog/security/cve-2026-39414/).

### CVE-2026-41145 — Unsigned-Trailer Query Authentication Bypass {#cve-2026-41145}

Remote exploitation: yes. Closes the presigned query-string authentication bypass when `X-Amz-Content-Sha256: STREAMING-UNSIGNED-PAYLOAD-TRAILER` is sent on `PutObject` or `PutObjectPart`. Upgrade any server reachable by clients on object write endpoints.

### CVE-2026-40344 — Snowball Auto-Extract Authentication Bypass {#cve-2026-40344}

Remote exploitation: yes. Verifies SigV4 authentication in `newUnsignedV4ChunkedReader()` before `PutObjectExtract` begins `untar()` extraction on Snowball unsigned-trailer uploads, guaranteeing that unauthenticated streams never reach the tar extractor.

### CVE-2026-42600 — Internode `ReadMultiple` Path Traversal {#cve-2026-42600}

Remote exploitation: yes (requires cluster-root / internode JWT). Removes the unused `/rmpl` (`xlStorage.ReadMultiple`) RPC endpoint that allowed msgpack request payloads to traverse outside configured drive roots. Single-node deployments do not register internode routes; distributed erasure deployments should upgrade.

### SN-2026-002 — Internode Payload Path and Memory Containment {#sn-2026-002}

Remote exploitation: yes (requires cluster-root / internode JWT). Completes `CVE-2026-42600` across the remaining internode protocol surfaces (`storageREST`, `peerREST`, `grid` WebSocket multiplexing, and `xlStorage`). Enforces path containment at two storage-layer chokepoints (`getVolDir`/`NSScanner` and `getStorage()` via `guardPaths`, `hasBadPathComponent`, and `isVolumeRootAlias`), caps caller-declared slice allocations (`maxDeleteVersions = 1000`, `max BitrotVerifier` size), validates erasure `DataBlocks`/`ParityBlocks` before division to prevent per-frame node panics, and verifies shard lengths before reporting intact data. Single-node deployments do not register these routes; no S3 API behavior changes. See the [internode containment chronicle](/blog/security/internode-path-containment/).

### SN-2026-003 — Policy Condition Value Sources {#sn-2026-003}

Remote exploitation: yes (policy-dependent). Prevents raw HTTP query parameters or headers that spell internal IAM condition-key names from shadowing or synthesizing server-derived condition values; confines `s3:signatureAge` to verified SigV4 presigned requests; separates query-only list parameters from header-backed `x-amz-*` condition keys; prevents client request tags from impersonating stored `ExistingObjectTag` values; and evaluates `s3:VersionId` against the whitespace-trimmed version ID only when `?versionId` is actually present. See the [version-ID and condition chronicle](/blog/security/s3-versionid-conditions/) and [condition value sources reference](/administration/identity-access-management/policy-based-access-control/#condition-value-sources).

### SN-2026-004 — Object-Grant Bucket Reach {#sn-2026-004}

Remote exploitation: yes (policy-dependent). Withholds 12 sensitive bucket-level write actions from object-only resource patterns (`arn:aws:s3:::bucket/*`): `PutBucketPolicy`, `DeleteBucketPolicy`, `PutBucketObjectLockConfiguration`, `PutBucketVersioning`, `PutReplicationConfiguration`, `PutBucketLifecycle`, `DeleteBucket`, `ForceDeleteBucket`, `PutBucketCors`, `DeleteBucketCors`, `PutBucketQOS`, and `PutInventoryConfiguration`, and requires a single `Allow` statement to match both the action and the resource (monotone intersection). **Read the [SN-2026-004 chronicle](/blog/security/object-grant-bucket-reach/) before upgrading if you maintain custom bucket-scoped IAM policies:** add the bare bucket ARN (`arn:aws:s3:::bucket`) alongside `arn:aws:s3:::bucket/*` in any statement intended to grant those 12 bucket-level writes. Built-in canned policies, `Deny` statements, and `NotResource` exclusions are unaffected. Setting `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` in the process environment before startup restores legacy matching (`MINIO_CONFIG_ENV_FILE` is read too late for package init).

### SN-2026-005 — Bare ARN Prefix Rejection {#sn-2026-005}

Policy-hardening change (`silo-pkg v3.12.0` / Server `eee05a17c`). Rejects S3, S3 Tables, and KMS ARN namespace prefixes that name no resource (`arn:aws:s3:::` and its historical `*arn:aws:s3:::` form) in both `Resource` and `NotResource` when creating named policies or creating/updating service-account session policies. Existing stored policies continue loading, matching, importing, and replicating without disruption, but re-submitting a policy containing a bare prefix requires replacing it with the concrete bucket/object ARN or an explicit wildcard (`arn:aws:s3:::*`). Note that a bare ARN prefix (`arn:aws:s3:::`) is distinct from a valid bare bucket ARN (`arn:aws:s3:::bucket`). See the [SN-2026-003 / SN-2026-005 chronicle](/blog/security/s3-versionid-conditions/#sn-2026-005) and [silo-pkg v3.12.0 release notes](/blog/release/pkg-3.12.0/).

### SN-2026-006 — Zero-Byte SSE-C Object Key Authentication {#sn-2026-006}

Remote exploitation: yes (requires read access to the object). Zero-byte SSE-C objects previously returned `200 OK` without unsealing the customer-provided key, allowing a caller with the wrong SSE-C key to pass `HeadObject`/`GetObject` or copy/overwrite the object under a newly chosen key. Zero-byte SSE-C reads and copies now unseal and verify the customer key, returning `403 AccessDenied` on key mismatch as on AWS S3. Shipped in [Server 20260903](/blog/security/20260903-server-hardening/#sn-2026-006).

### SN-2026-007 — `GetObjectAttributes` on SSE-C Objects {#sn-2026-007}

Remote exploitation: yes (requires read access to the object). `GetObjectAttributes` previously returned object attributes for SSE-C objects without authenticating the customer key, and skipped the check whenever a client sent `X-Minio-Source-Replication-Request`. Wrong SSE-C keys now return `403 AccessDenied`, and unauthenticated replication markers return `400 InvalidArgument`; authorized replication peers holding `s3:ReplicateObject` remain unaffected. Shipped in [Server 20260903](/blog/security/20260903-server-hardening/#sn-2026-007).

### SN-2026-008 — Post-Auth Trust Boundary for Internal Replication Headers {#sn-2026-008}

Remote exploitation: yes (any authenticated principal with read or write access to the object). Completes `CVE-2026-34204`: internal headers (`X-Minio-Source-Etag`, `X-Minio-Source-Mtime`, `X-Minio-Source-Replication-Request`, `X-Minio-Source-DeleteMarker`, replication SSE key headers, and `X-Amz-Bucket-Replication-Status`) were previously trusted on mere presence in several handlers. Server 20260903 strips these headers from a post-authentication clone unless the caller sends the exact marker value and holds `s3:ReplicateObject` or `s3:ReplicateDelete`. Site replication service accounts and bucket-replication targets holding replication permissions are unaffected. See the [chronicle](/blog/security/20260903-server-hardening/#sn-2026-008) and [CORS & Replication Trust Design](/blog/design/cors-replication-trust/).

### SN-2026-009 — User and Group Status Authorization {#sn-2026-009}

Remote exploitation: yes (authenticated Admin API). `SetUserStatus` and `UpdateGroupStatus` previously checked `admin:EnableUser` and `admin:EnableGroup` regardless of whether the request enabled or disabled the target, allowing an operator granted only enable permission to disable accounts (and vice versa). Status changes now check `admin:EnableUser` / `admin:DisableUser` and `admin:EnableGroup` / `admin:DisableGroup` according to the requested target state. Policies granting `admin:*` or `consoleAdmin` are unaffected; least-privilege policies granting only one action of the pair now authorize only that direction. See the [chronicle](/blog/security/20260903-server-hardening/#sn-2026-009) and [User Status Permissions Design](/blog/design/user-status-permissions/).

### SN-2026-010 — Explicit Object Version Delete Authorization {#sn-2026-010}

Remote exploitation: yes (authenticated S3 API). `DeleteObject?versionId=...` and `DeleteObjects` entries carrying a `VersionId` were previously authorized against `s3:DeleteObject` with only a negative check for `Deny s3:DeleteObjectVersion`. Explicit version deletes now require `s3:DeleteObjectVersion`, matching AWS S3. **Two policy effects:** principals granted only `s3:DeleteObject` can still create delete markers on unversioned `DELETE` calls but can no longer permanently delete specific versions; and policies that relied solely on `Deny s3:DeleteObject` alongside `Allow s3:*` to block permanent version deletion must also add `Deny s3:DeleteObjectVersion`. Replication targets retain the `s3:ReplicateDelete` contract. See [DeleteObjectVersion Authorization](/blog/release/delete-object-version-authorization/).

### SN-2026-011 — Unsigned `X-Amz-*` Operation Headers {#sn-2026-011}

Remote exploitation: yes (holder of a presigned URL or intercepted `Authorization`-header `PUT` request). Because `cmd/api-router.go` dispatches `PUT` requests carrying `x-amz-copy-source` to `CopyObjectHandler`, an attacker holding a presigned `PUT` URL could append an unsigned `x-amz-copy-source: /src/secret` header and trick the server into copying any object readable by the signer into the destination object. Reported by Oren Yomtov.

Fixed in [Server 20260916](/blog/release/silo-20260916/) ([status note](/blog/security/20260913-signed-header-status/), `123325430`, PR #173 and #177). Both `doesPresignedSignatureMatch` and `doesSignatureMatch` now invoke `checkUnsignedHeaders` and reject any request carrying an unsigned `X-Amz-` header with `400 AccessDenied` (`ErrUnsignedHeaders`). `X-Amz-Content-Sha256` is the sole explicit header exemption because its payload digest is bound by the canonical request and verified by `SN-2026-012`; PR #177 also derives `s3:signatureAge` directly from the signed `X-Amz-Date` without mutating `r.Header`. Standard AWS SDKs, `mcli`, and `minio-go` already sign all `X-Amz-` headers; custom clients that append `X-Amz-*` headers to a presigned URL must include them in `X-Amz-SignedHeaders` at signing time. See [Signed Header Coverage Design](/blog/design/signed-header-coverage/).

### SN-2026-012 — Header-Only Presigned Payload Hash Verification {#sn-2026-012}

Remote exploitation: yes (holder of a presigned URL whose payload hash was bound via `X-Amz-Content-Sha256` header rather than query string). Generic authenticated handlers such as `PutBucketPolicy` previously verified the signature against the header digest but did not verify the consumed request body against that digest, allowing a holder of the presigned URL to substitute a different body. Commit `c4b5e1cb4` ([Server 20260916](/blog/security/20260916-release-hardening/#sn-2026-012)) binds generic body verification to the same effective payload hash used during signature verification (query parameter first, header fallback) and rejects tampered bodies with `XAmzContentSHA256Mismatch`.

### SN-2026-013 — Durable IAM Revocation and Scoped STS Revocation {#sn-2026-013}

Remote exploitation: requires a previously issued credential and a restart, peer-sync delay, or same-name parent recreation scenario. Before [Server 20260916](/blog/security/20260916-release-hardening/#sn-2026-013) (`#191`, `#192`, `f99ed829b`), disabling or deleting a user, rotating credentials, or recreating a user under the same name could leave previously minted STS tokens or child service accounts valid until JWT expiration, or allow stale site-replication records to resurrect deleted identities. Server 20260916 persists deletion tombstones, parent revocation timestamps, and group-grant revisions under `.minio.sys/iam/revocations/`, and [Server 20261018](/blog/security/20261018-release-hardening/#sts-revocation) (`0cd388c66`) adds `POST /minio/admin/v3/sts-revoke` for per-principal and per-token (`jti`) STS revocation without invalidating unrelated sessions. Coordinate upgrades across all nodes sharing an IAM backend; see [IAM Revocations Design](/blog/design/iam-revocations/) and the [IAM Upgrade Runbook](/operations/replication/iam-upgrade/).

### SN-2026-014 — Anonymous Console Share-Download Proxy Restriction {#sn-2026-014}

Remote exploitation: yes (anonymous caller reaching the Console `/api/v1/download-shared-object` endpoint). The Console share-download proxy previously accepted arbitrary paths and query parameters on its configured S3 origin, allowing an unauthenticated caller to reach internal origin paths (such as `/minio/v2/metrics/cluster`) that operators had isolated behind the Console network boundary. Reported by Jiri Pejchal (`@jiri-pejchal`). Fixed in **[Console v2.4.1](/blog/release/console-2.4.1/)** (`silo-console#56`) and embedded in **[Server 20260916](/blog/security/20260916-release-hardening/#sn-2026-014)** (`#209`): the proxy now restricts forwarding strictly to single-object `GET` downloads on the configured S3 origin, rejects `/minio/*` system paths and subresource management queries before dialing, and refuses HTTP redirects.

### SN-2026-015 — `PutObjectRetention` Authorization and Governance Bypass {#sn-2026-015}

Remote exploitation: yes (authenticated S3 caller). Three flaws in `PutObjectRetentionHandler` (`cmd/object-handlers.go`) allowed an authenticated caller to: (1) modify object retention without holding `s3:PutObjectRetention` by supplying `X-Amz-Bypass-Governance-Retention: true` when holding `s3:BypassGovernanceRetention` (short-circuiting the base action check); (2) clear (`Mode: ""`) or shorten an active `GOVERNANCE` lock using only `s3:PutObjectRetention` without `s3:BypassGovernanceRetention`; and (3) bypass IAM `Deny` policies on `s3:object-lock-remaining-retention-days` when clearing retention. Fixed in **[Server 20261018](/blog/security/20261018-release-hardening/#object-lock)** (PR #234, #235, `14042b5aa`): `s3:PutObjectRetention` is unconditionally enforced before object lookup, weakening or clearing an active `GOVERNANCE` lock requires both `X-Amz-Bypass-Governance-Retention: true` and `s3:BypassGovernanceRetention`, and clearing retention evaluates `s3:object-lock-remaining-retention-days = 0`. See the [SN-2026-015 / SN-2026-016 Advisory](/blog/security/20260926-governance-retention-bypass/) and [Repair Architecture](/blog/design/governance-retention-bypass-repair/#sn-2026-015).

### SN-2026-016 — Version-Addressed and In-Place Object Lock Overwrites {#sn-2026-016}

Remote exploitation: yes (authenticated S3 writer). Callers supplying `?versionId=<existing-uuid>` on `PutObject`, `CopyObject`, `CompleteMultipartUpload`, or `PutObjectExtract`, or overwriting unversioned/`null`-version objects in place (including directory objects and multipart completions), could overwrite an existing version protected by `COMPLIANCE` or `GOVERNANCE` retention or `LegalHold` without triggering an Object Lock check. Fixed in **[Server 20261018](/blog/security/20261018-release-hardening/#object-lock)** (`14042b5aa`, `0d3ba5d4c`): S3 handlers reject caller-supplied `?versionId=` unless the request is an authenticated replication write (`isReplicationRequest`), preflight checks fail closed on unreadable metadata, and storage write paths (`PutObject`, `CopyObject`, `CompleteMultipartUpload`, `PutObjectDir`) re-verify destination version lock state (`checkObjectLockForOverwrite`) inside the namespace write lock. Upgrade every Server node and replication peer accepting writes. See the [Repair Architecture](/blog/design/governance-retention-bypass-repair/#sn-2026-016).

### SN-2026-017 — Delegated IAM Admin Credential Authorization Boundaries {#sn-2026-017}

Remote exploitation: yes (authenticated delegated IAM administrator or restricted derived credential). In Server 20260916 and earlier, delegated admins holding `admin:CreateUser`, `admin:AttachUserOrGroupPolicy`, or `admin:UpdateServiceAccount` could assign policies broader than their own effective permissions, mutate higher-privilege users/groups/service accounts, or use self-service admin routes to escape session-policy or `Deny` restrictions. Fixed in **[Server 20261018](/blog/security/20261018-release-hardening/#sn-2026-017)** (`2616d43fb`, `995439260`, PR #242): delegated IAM mutations now enforce target-policy containment (`authorizePolicyChange`, `authorizeGroupTargets`, `authorizeTargetUser`) and block non-root self-permission escalation (`ErrAdminChangeUserSelfPermission`). See [IAM Admin Authorization Design](/blog/design/iam-admin-authorization/).

### SN-2026-018 — Client Source Address Trust Boundary (`MINIO_API_TRUSTED_PROXIES`) {#sn-2026-018}

#### Forwarded-Header Trust Policy {#source-address-trust}

Opt-in security hardening (`fe6dc4780`, shipped in [Server 20260804](/blog/release/silo-20260804/)). By default, inherited upstream code trusts `X-Forwarded-For` and `X-Real-IP` from any direct peer, allowing clients that can reach the server directly (or behind an appending proxy) to spoof `aws:SourceIp` IAM conditions and evade per-IP LDAP rate limits. `MINIO_API_TRUSTED_PROXIES` establishes an enforceable trust boundary: when set to `none`, forwarded headers are never trusted; when set to a comma-separated list of proxy IPs or CIDRs, forwarded headers are accepted only from listed peers (plus loopback sidecars) and `X-Forwarded-For` is walked right-to-left past trusted hops to extract the first untrusted client IP. Multi-node clusters that enable `MINIO_API_TRUSTED_PROXIES` must include their own cluster node IPs/CIDRs in the list so peer-forwarded S3 requests preserve the original client IP. See the [Source Address Trust Chronicle](/blog/security/source-address-trust/) and [Settings Reference](/reference/minio-server/settings/core/#client-source-address-trust).

### SN-2026-019 — Notification Key Registration and Secret Redaction {#sn-2026-019}

Config-subsystem hardening (`672c07a0f` in [Server 20260804](/blog/release/silo-20260804/), followed by `f1ba68358` in [Server 20260903](/blog/release/silo-20260903/)). Auditing `notify_postgres` and `notify_mysql` revealed that `config.HasSensitiveKeys` did not redact `password`, `dsn_string`, or `connection_string` when returning validation errors or `GetConfigKV` payloads, and five discrete connection keys were missing from the registered `Keyspace`. Commit `672c07a0f` added credential redaction in `config.HasSensitiveKeys` and a structural test verifying key registration across all config subsystems; [Server 20260903](/blog/design/notify-url/) subsequently retired the five discrete keys in favor of `connection_string` and `dsn_string` to eliminate split-brain overwrites during startup migration. See the [Notification Keyspace Chronicle](/blog/security/notify-keyspace-registration/) and [Notify URL Design](/blog/design/notify-url/).

## Dependency Security Updates {#dependencies}

[Server 20261018](/blog/release/silo-20261018/) builds with Go 1.27.2 and selects `golang.org/x/net v0.61.0`, `golang.org/x/crypto v0.58.0`, `golang.org/x/text v0.43.0`, and `github.com/go-jose/go-jose/v4 v4.1.6` (note that the [`go-jose` RSA JWK parsing fix](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q) rejects RSA keys larger than 4096 bits; verify OIDC/JWKS identity providers before upgrading). Unified Go 1.27.3 and static `curl 8.23.0` updates are tracked in [SILO 20261024](/blog/release/silo-20261024/).

| Advisory / Scope | Fixed By | Summary |
| :-- | :-- | :-- |
| `CVE-2026-39883` | `1869bd30b`, `e4fa06394` | Updates OpenTelemetry dependencies (`RELEASE.2026-03-21`). |
| 2026-03-25 release | [`RELEASE.2026-03-25`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-03-25T00-00-00Z) | OTel SDK, Paho MQTT, and `x/crypto` updates addressing `CVE-2026-24051`, `CVE-2025-10543`, and `CVE-2025-58181`. |
| `CVE-2026-34986` | [`68e0ba997`](https://github.com/pgsty/silo/commit/68e0ba997) | Upgrades `go-jose` to `v4.1.4`. |
| Go 1.26.2 stdlib | [`db4c0fd5e`](https://github.com/pgsty/silo/commit/db4c0fd5e) | Fixes `CVE-2026-32280` and `CVE-2026-32281` (`crypto/x509`) and `CVE-2026-32283` (`crypto/tls`). |
| Go 1.26.4 & module refresh | `df627ff89`, `3e61b1d3a` | Fixes `CVE-2026-32952` (Azure NTLM) and `CVE-2026-41602` (Thrift), plus NATS and Prometheus dependency updates (`RELEASE.2026-06-18`). |
| Go 1.26.5 stdlib | [Go 1.26.5](https://go.dev/doc/devel/release#go1.26.5) ([Server 20260806](/blog/release/silo-20260806/)) | Fixes `GO-2026-4946`, `GO-2026-4947`, and `GO-2026-4948` in `crypto/tls` and `os`. |
| [GO-2026-6061](https://pkg.go.dev/vuln/GO-2026-6061) / [GHSA-hrxh-6v49-42gf](https://github.com/advisories/GHSA-hrxh-6v49-42gf) | [`4dfc27ce3`](https://github.com/pgsty/silo/commit/4dfc27ce3) | Updates gRPC to `v1.82.1` (xDS RBAC engine and HTTP/2 transport fixes) and `golang.org/x/text` to `v0.39.0` ([GO-2026-5970](https://pkg.go.dev/vuln/GO-2026-5970) / `CVE-2026-56852`). |
| [GO-2026-5841](https://pkg.go.dev/vuln/GO-2026-5841) | [`c1aec0518`](https://github.com/pgsty/silo/commit/c1aec0518) | Updates `github.com/klauspost/compress` to `v1.18.7`. |
| Go 1.27.1 & September stack refresh | [Go 1.27.1](https://go.dev/doc/devel/release#go1.27.1) via [`43f4bb7ed`](https://github.com/pgsty/silo/commit/43f4bb7ed), [`edc8be6ed`](https://github.com/pgsty/silo/commit/edc8be6ed), [`4d6e1ea8e`](https://github.com/pgsty/silo/commit/4d6e1ea8e) | Upgrades toolchain to Go 1.27.1, updates `etcd` client (`v3.7.1`), `jwx` (`v3.0.13`), and `klauspost/compress` (`v1.19.2`), and converges on upstream `minio-go v7.3.1` ([Server 20260903](/blog/release/silo-20260903/)). |
| [GO-2026-6354](https://pkg.go.dev/vuln/GO-2026-6354) / [GO-2026-6355](https://pkg.go.dev/vuln/GO-2026-6355) | [`edf36bcbf`](https://github.com/pgsty/silo/commit/edf36bcbf) | Updates `golang.org/x/crypto` to `v0.56.0`, fixing SFTP/SSH channel deadlock DoS (`startSFTPServer` → `sftp.Server.Listen` → `ssh.NewServerConn`). |
| [CVE-2026-84304](https://github.com/advisories/GHSA-vp52-pcj8-j9qc) | gRPC `v1.83.1` | Fixes unauthenticated heap exhaustion on fragmented HTTP/2 `DATA` frames in gRPC-Go. |
| [CVE-2026-79921 / GHSA-6c5v-hqjr-5xxp](https://github.com/advisories/GHSA-6c5v-hqjr-5xxp) | [`d63c92e39`](https://github.com/pgsty/silo/commit/d63c92e39) ([Server 20260916](/blog/release/silo-20260916/)) | Updates `amqp091-go` to `v1.14.0`, preventing a malicious AMQP broker from exhausting memory via oversized frames. |
| Go 1.27.2 & October dependency refresh | [`0cd388c66`](https://github.com/pgsty/silo/commit/0cd388c666f8211f552604ae73448a066e9c25ce) ([Server 20261018](/blog/security/20261018-release-hardening/#dependencies)) | Upgrades to Go 1.27.2, `x/net v0.61.0`, `x/crypto v0.58.0`, `x/text v0.43.0`, and `go-jose/v4 v4.1.6` (`GHSA-mgcc-cww5-fp2q`). |

## Operationally Significant Security-Related Fixes {#operational}

| Change | Fixed By | Summary |
| :-- | :-- | :-- |
| Replicated Object Lock timestamp ordering | [`f4c1286c9`](https://github.com/pgsty/silo/commit/f4c1286c9) ([Server 20260903](/blog/release/silo-20260903/)) | Replicated `CopyObject` previously rebuilt metadata from the incoming request before comparing replication timestamps and stored the legal-hold timestamp under the retention key, allowing a stale replica event to turn off a newer legal hold or shorten a newer retention period. The handler now captures stored state first, applies replica updates only when their timestamp is newer, and keeps retention and legal-hold timestamps under distinct keys. See [Object Lock Replication Ordering](/blog/design/object-lock-replication-ordering/). |
| `ldaps://` TLS configuration propagation | [`ce1c537eb`](https://github.com/pgsty/silo/commit/ce1c537eb1dd6c4efa1cf75cf5df0e2c489c947a) (`RELEASE.2026-03-25`) | Restores TLS configuration propagation for `ldaps://` `DialURL()` connections so `MINIO_IDENTITY_LDAP_TLS_SKIP_VERIFY` and custom root CAs take effect. |
| Signed-field and policy-input alignment | [#177](https://github.com/pgsty/silo/pull/177), [`87d8b5967`](https://github.com/pgsty/silo/commit/87d8b5967) ([Server 20260916](/blog/release/silo-20260916/)) | Rejects ambiguous repeated `x-amz-copy-source` headers, derives `s3:signatureAge` statelessly from the signed `X-Amz-Date`, and binds `s3:x-amz-content-sha256` policy evaluation to the verified payload digest. |
| Cross-pool conditional `PUT` and `DELETE` | [#207](https://github.com/pgsty/silo/pull/207), [`5e7d60308`](https://github.com/pgsty/silo/commit/5e7d60308) ([Server 20260916](/blog/release/silo-20260916/)) | Evaluates conditional write and delete preconditions (`If-Match`, `If-None-Match`) against the authoritative logical object under a shared cross-pool lock so a stale copy in an older pool cannot authorize an overwrite. See [Multi-Pool Object Consistency](/blog/design/multi-pool-object-consistency/). |

## Ledger Provenance {#attribution}

This page is maintained from the advisory ledger originally tracked in `pgsty/silo` (`docs/security/advisories.md` through `f99ed829b5eba` / `40220bd836cb`) and aligned with the [Component Version Matrix](/compatibility/versions/). Full root-cause traces, rejected design alternatives, and verification commands live in the linked [Security Chronicle](/blog/security/) and [Design Notes](/blog/design/) articles.

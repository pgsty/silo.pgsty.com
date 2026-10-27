---
title: "SILO at One Year: What Actually Changed Since Upstream MinIO?"
linkTitle: "SILO at One Year"
date: 2026-10-26
lastmod: 2026-10-27
author: Ruohang Feng
description: "From MinIO's final public release on 2025-10-15 to SILO 20261026: 376 days, 604 commits, 7 CVEs, 18 security boundary hardenings, S3 protocol and checksum repairs, replication and multi-pool storage fixes, and a restored administration console and CLI."
summary: >
  From MinIO's final public release on 2025-10-15 to SILO 20261026: 376 days and 604 commits. Here is the engineering ledger of what SILO actually changed across security boundaries, S3 protocol and checksums, replication and lifecycle, storage write/rollback and multi-pool safety, Console and mcli, and operational delivery—plus the boundaries that remain unchanged.
tags: [post, minio, silo]
weight: 5
url: "/blog/post/silo-one-year/"
---

On October 15, 2025, MinIO shipped its final public open-source release, [`RELEASE.2025-10-15T17-29-55Z`](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z) (commit `9e49d5e7a648`). Over the next four months, upstream placed the repository into "maintenance mode," deleted the `minio/console` repository outright, and in February 2026 archived the main server repository—routing all subsequent CVE patches and bug fixes exclusively to its commercial AIStor product.

On October 26, 2026, SILO tagged [`RELEASE.2026-10-26T00-00-00Z`](https://github.com/pgsty/silo/commit/c3ad836aed0d8a7d23c2e44a5eaa3009d08525e3) (commit `c3ad836aed0d`). Across 376 days, the server repository accumulated **604 commits**, evolving alongside its companion repositories `silo-console`, `mcli`, and `silo-pkg`.

A question we hear often from operators evaluating the fork is straightforward: **Over the past year, did SILO merely rebrand the binary and apply surface-level CVE patches, or did it fix substantive storage and protocol bugs? Compared with the final upstream MinIO release, what actually changed?**

Here is the short answer: **SILO preserved MinIO's erasure-coding storage layout (`xl.meta` v1.3), HighwayHash bitrot protection, and fundamental read/write quorum rules, while focusing a full year of engineering on security boundaries, S3 protocol and checksum correctness, replication and lifecycle convergence, failed-write rollback and multi-pool safety, and a restored administration console and CLI.**

| Area | Key Substantive Changes (`2025-10-15` → `2026-10-26`) |
| --- | --- |
| **Security & Authorization** | Patched **7 post-fork CVEs** (OIDC algorithm confusion, LDAP STS enumeration and brute-force, replication SSE header injection, S3 Select unbounded record OOM, unsigned-trailer signature bypass, Snowball extraction authorization bypass, and `/rmpl` path traversal) plus **18 `SN-2026-*` security boundary hardenings** (enforced SigV4 `SignedHeaders` for `X-Amz-*` operational headers, policy condition key isolation, bucket-level write action boundaries, service-account delegation ceilings, Object Lock bypass validation, and durable IAM revocations against stale-event resurrection) |
| **S3 Protocol & Checksums** | Replaced upstream's `NotImplemented` stubs with full per-bucket CORS persistence and `OPTIONS` preflight; implemented conditional `DELETE` (`If-Match`) and multi-pool conditional `PUT` / `CompleteMultipartUpload`; fixed plaintext checksums and logical part sizes across multipart uploads, `CopyObject`, SSE-C, and server-side compression; changed tampered-encryption errors from HTTP `206` to `500` |
| **Replication & Lifecycle** | Preserved `FULL_OBJECT` checksum types during multipart replication initiation (`#255`); preserved raw SSE-C ciphertext and seals across trusted replication peers; added modification timestamps to object tags and Object Lock retention for out-of-order convergence; prevented versioned lifecycle expiration from deleting remote tier data when only adding a delete marker (`#253`) |
| **Storage & Multi-Pool Safety** | Two-stage multi-pool bulk deletion (`#257`), migration version checks, `LIST` recovery under drive disagreement (`#239`), and storage RPC delete options for overwrite rollback; existing timeout/cancellation semantics remain, including the possibility of late commits, delayed rollback and stale reads |
| **Console & mcli** | Restored and rebuilt the full administration UI in **SILO Console v2.5.1** (`<3 MB` zero-telemetry bundle, EN/ZH toggle, cursor pagination, Tasks center, Metrics V3, high-latency WebSocket diagnostic repairs); shipped **mcli 20261026** with read-only `checksum verify`, nonzero exit codes on partial or permission failures, and safe `mirror` delete propagation |
| **Operations & Delivery** | Wired `--read-header-timeout` / `MINIO_READ_HEADER_TIMEOUT` (30s absolute HTTP/1 header deadline); added trusted-proxy settings (`MINIO_API_TRUSTED_PROXIES`) and native `silo healthcheck`; permanently removed self-update and `SUBNET` call-home; built a verified multi-arch supply chain on Go 1.27.3, UBI 9.8 / distroless images, RPM/DEB/APK packages, Windows ZIP archives, GPG signatures, SPDX SBOMs, and Sigstore attestations |
{.wide .expand}

Equally important are the boundaries that have **not** changed:

1. **No distributed fencing, and no claim that every consistency problem is solved.** Late commits after lease expiration or network partitions remain possible; strict generation read refusal, automatic cross-pool read recovery, public persistent `ListMultipartUploads` scanning (`#79`), access-frequency pool tiering, and multi-pool overwrite affinity (`#245`) were tested and withdrawn or deferred when their capacity or availability costs proved unacceptable.
2. **No head-to-head full-cluster throughput benchmark between the two tags.** We record targeted microbenchmarks and amortized overhead checks, not synthetic cluster-wide throughput claims.
3. **On-disk compatibility does not mean arbitrary mixed-version operation or rolling downgrade.** Durable IAM revocations (`siloParentRevocation`) and replication metadata tombstones require coordinated upgrades across participating nodes.

The sections below walk through each area in detail, with exact commit references, design records, and operational boundaries.

---

## 1. Baseline and Product Stack: What Changed and What Stayed the Same {#baseline-and-stack}

Our comparison uses two fixed points:

- **Upstream baseline**: `minio/minio` [`RELEASE.2025-10-15T17-29-55Z`](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z) (commit `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a`, October 15, 2025). Note: between that final release and archiving the repo in February 2026, upstream merged 9 unreleased commits (such as POST policy tag constraints in `fa18589d1c` and conditional PUT read-quorum adjustments in `18f97e70b1`), which never shipped in an upstream release and were addressed independently in SILO.
- **SILO target**: `pgsty/silo` [`RELEASE.2026-10-26T00-00-00Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-10-26T00-00-00Z), source `c3ad836aed0d8a7d23c2e44a5eaa3009d08525e3`, released with mcli / KES 20261026, Console v2.5.1 and silo-pkg v3.15.2. See the [release notes](/blog/release/silo-20261026/) and [component matrix](/compatibility/versions/).

Across `9e49d5e7a648..c3ad836aed0d`, `git rev-list --count` reports **604 reachable commits**. This includes features, fixes, tests, documentation and release engineering; the sections below describe delivered behavior rather than treating commit counts as feature counts.

### The Four-Component Coordinated Stack

Because the server embeds the Console frontend and imports `mc` administration packages alongside shared policy and encryption libraries, maintaining the server alone is not enough. SILO maintains a coordinated four-component product graph (plus optional external KES):

| Component | Upstream `2025-10-15` State | SILO `20261026` State | Key Evolution |
| --- | --- | --- | --- |
| **Server (`pgsty/silo`)** | Go 1.24.0, `minio` binary | **Go 1.27.3**, `silo` binary ([`c3ad836aed0d`](https://github.com/pgsty/silo/commit/c3ad836aed0d8a7d23c2e44a5eaa3009d08525e3)) | Retains `github.com/minio/minio` module path; delivers 7 CVE fixes, 18 security boundary hardenings, and storage/replication repairs |
| **Console (`pgsty/silo-console`)** | Stripped-down `v1.7.7` (object browser only) | **[v2.5.1](https://github.com/pgsty/silo-console/releases/tag/v2.5.1)** ([`fff1618d9abb`](https://github.com/pgsty/silo-console/commit/fff1618d9abbf1f6125f1914bd50818e2bc347ed)) | Upstream deleted `minio/console`; SILO restored the full admin console with a `<3 MB` zero-telemetry bilingual frontend |
| **Client (`pgsty/mc`)** | `mc` `cf909e1063a9` | **[mcli 20261026](https://github.com/pgsty/mc/releases/tag/RELEASE.2026-10-26T00-00-00Z)** ([`0ceb298cdcd0`](https://github.com/pgsty/mc/commit/0ceb298cdcd05f2ffdc4ea62d7d01a3666c3e8cc)) | Shipped as `mcli` (avoiding collision with Midnight Commander `mc`), adding `checksum verify` and honest error exit codes |
| **Shared Pkg (`pgsty/silo-pkg`)** | `minio/pkg/v3 v3.1.3` | **[v3.15.2](https://github.com/pgsty/silo-pkg/releases/tag/v3.15.2)** ([`0416eb1f4505`](https://github.com/pgsty/silo-pkg/commit/0416eb1f450536ca2cc3592c2c2a06a3df88d4e0)) | Maintained directly as `github.com/pgsty/silo-pkg/v3` for IAM policy evaluation, condition key isolation, TLS trust, and KMS |
| **S3 SDK (`minio/minio-go/v7`)** | `v7.0.91` | **`v7.4.2-0.20261025165926-320af050c445`** | Uses the verified upstream module commit (including short-stream multipart, negative-offset `ReadAt`, and batch-delete fixes) |
| **KMS (`pgsty/kes`)** | External optional service | **[KES 20261026](/blog/release/silo-20261026/#kes)** ([`e9b4f1acebc1`](https://github.com/pgsty/kes/commit/e9b4f1acebc11d61b42f876da8df48f548750cc9)) | Go 1.27.3; OpenBao KV v2 and local Moto Secrets Manager compatibility checks; updated AWS and GCP clients |
{.wide .expand}

### Foundations Intentionally Preserved

So existing MinIO deployments can switch to `pgsty/silo` in place without data migration or client changes, SILO keeps the core storage and wire contracts unchanged:

- **Erasure coding and bitrot protection**: Reed-Solomon erasure coding and per-block HighwayHash256 verification remain unchanged.
- **Read and write quorum rules**: Read quorum remains $K$ (data shards); write quorum remains $K$ when data and parity shard counts differ, and $K+1$ when data shards equal parity shards (for example, 16-drive 12+4 uses R12/W12, while 8+8 uses R8/W9).
- **On-disk format and system namespace**: `xl.meta` stays at version `1.3` and `.minio.sys` retains its layout, allowing existing drives to mount directly.
- **Wire and configuration compatibility**: `MINIO_*`, `MC_*`, and `CONSOLE_*` environment variables, `/minio/health/*` probes, `/minio/v2/metrics/*` and `/minio/metrics/v3` scrape endpoints, and `X-Minio-*` headers remain supported (see the [compatibility overview](/compatibility/) and [migration guide](/compatibility/migration/)).

---

## 2. Security, Authentication, and Authorization: 7 CVEs and 18 Security Boundary Hardenings {#security}

Because SILO retains the `github.com/minio/minio` Go module path while upstream advisories publish open-ended affected version ranges, automated scanners frequently flag SILO for every historical MinIO CVE.

To separate fact from scanner noise: vulnerabilities such as `CVE-2025-62506` (service-account privilege escalation), `CVE-2025-31489`, and `CVE-2025-27414` were **already fixed** in upstream's `2025-10-15` baseline. By contrast, the **7 CVEs below** were disclosed *after* `2025-10-15`, left unpatched in upstream open-source MinIO, and fixed and verified in SILO:

| CVE / Advisory | Severity | Root Cause and Impact | SILO Fix and Code Evidence |
| --- | --- | --- | --- |
| **[CVE-2026-33322](/blog/security/cve-2026-33322/)** | Critical (9.8) | OIDC JWT algorithm confusion: when a token header specified HMAC (`HS256`), upstream verified it using the OIDC `ClientSecret` as a symmetric key, letting anyone with `ClientSecret` forge arbitrary identities including `consoleAdmin` | Enforce asymmetric JWKS public-key verification only and reject HMAC-signed OIDC tokens (`cmd/jwt.go`, `internal/config/identity/openid/`) |
| **[CVE-2026-33419](/blog/security/cve-2026-33419/)** | High | LDAP STS endpoint leaked whether usernames existed and lacked rate limiting, enabling username enumeration and password brute-forcing for STS credentials | Unify bind-failure authentication errors and enforce sliding-window rate limiting keyed by trusted client IP + normalized username without penalizing successful logins (`cmd/sts-handlers.go`) |
| **[CVE-2026-34204](/blog/security/cve-2026-34204/)** | High | Unauthenticated `X-Minio-Replication-*` headers on ordinary `PUT`/`COPY` requests could inject broken encryption metadata and render objects permanently unreadable | Strip unauthorized replication headers and SSE replication metadata at request ingress (`cmd/auth-handler.go`, `cmd/object-handlers-common.go`) |
| **[CVE-2026-39414](/blog/security/cve-2026-39414/)** | High | S3 Select accumulated newline-free CSV or JSON Lines streams without bound, allowing a single request to trigger an out-of-memory (OOM) crash | Enforce strict per-record byte limits in the CSV and JSON Lines parsers (`internal/s3select/`) |
| **[CVE-2026-41145](/blog/security/cve-2026-41145/)** | High | `STREAMING-UNSIGNED-PAYLOAD-TRAILER` write paths bypassed signature verification on specific routes, allowing anonymous or forged-signature object writes | Enforce full authentication and signature validation across all `aws-chunked` and unsigned-trailer ingress paths (`cmd/auth-handler.go`) |
| **[CVE-2026-40344](/blog/security/cve-2026-40344/)** | High | Snowball archive batch-extraction upload path lacked entry-point authentication and per-entry authorization checks | Require caller authentication at ingress and evaluate bucket/prefix policy authorization for every extracted archive entry (`cmd/bucket-handlers.go`, `cmd/object-handlers.go`) |
| **[CVE-2026-42600](/blog/security/cve-2026-42600/)** | High | Internode storage endpoint `/rmpl` (`ReadMultiple`) lacked drive-root path containment, allowing path traversal outside the drive root | Remove the unused `ReadMultiple` endpoint from the internode storage REST protocol and enforce strict drive-root path containment across all storage RPC handlers (`cmd/storage-rest-server.go`) |
{.wide .expand}

### 18 `SN-2026-*` Security Boundary Hardenings

Beyond public CVEs, adversarial code review and multi-node testing uncovered **18 additional security boundary defects** tracked in our [Security Advisories ledger](/about/security-advisories/):

1. **SigV4 SignedHeaders Integrity and Policy Condition Isolation ([SN-2026-011](/blog/security/20260913-signed-header-status/), [SN-2026-003](/blog/security/s3-versionid-conditions/))**:
   - Upstream allowed callers to attach unsigned `X-Amz-*` operational headers (such as governance bypass, tagging, or checksum headers) to an otherwise valid SigV4 request. SILO requires every `X-Amz-*` operational header present on the request to be covered by `SignedHeaders`.
   - Upstream populated IAM policy condition maps directly from client headers and query parameters, allowing callers to spoof server-authoritative condition keys such as `s3:prefix`, `s3:versionid`, `s3:ExistingObjectTag/*`, or `aws:PrincipalType`. SILO isolates server-authoritative condition keys in `silo-pkg` and binds `s3:VersionId` checks to the actual target version in `DeleteObjects` and `GetObject`.
2. **Bucket-Level Write Boundaries, Version-Deletion Authorization, and Admin Action Splits ([SN-2026-004](/blog/security/object-grant-bucket-reach/), [SN-2026-005](/blog/security/s3-versionid-conditions/#sn-2026-005), [SN-2026-009 and 010](/blog/security/20260903-server-hardening/), [SN-2026-017](/blog/design/iam-admin-authorization/))**:
   - Tightened resource ARN matching for 12 bucket-level write actions (`s3:CreateBucket`, `s3:DeleteBucket`, `s3:PutBucketPolicy`, `s3:PutLifecycleConfiguration`, etc.) so object wildcard grants (`arn:aws:s3:::bucket/*`) or bare `arn:aws:s3:::` ARNs cannot mutate bucket configurations.
   - Require `s3:DeleteObjectVersion` for permanent deletion of an explicit version ID, including `null`; an ordinary delete that creates a delete marker still uses `s3:DeleteObject`. Batch deletion checks each entry independently.
   - Split user status toggling out of `admin:CreateUser` into `admin:EnableUser` / `admin:DisableUser`; separated self-service password changes into `admin:ChangeMyPassword` (see [password-permission migration](/compatibility/password-permissions/)); and enforced parent-account ownership checks across IAM admin access-key creation, inspection, and listing endpoints.
3. **Service-Account Delegation Ceilings and Object Lock Governance Bypass ([SN-2026-015 and 016](/blog/security/20260926-governance-retention-bypass/))**:
   - Fixed inline session-policy evaluation so parent `Deny` rules are never dropped when the inline policy omits a matching `Allow`, and re-verified live parent privileges on temporary STS and service-account sessions.
   - Required `x-amz-bypass-governance-retention: true` when `PutObject` overwrites a `GOVERNANCE`-locked object, and validated retention XML payloads before evaluating Object Lock governance bypass in `PutObjectRetention`.
4. **Durable IAM Revocations, Policy Reload Lock Isolation, and LDAP Long DNs ([SN-2026-013](/blog/security/20260916-release-hardening/#sn-2026-013))**:
   - Previously, in multi-node and site-replicated clusters, delayed site-replication events or missed peer notifications could resurrect deleted users, policies, or service accounts. SILO persists deletion tombstones, revision numbers, and parent revocation cutoffs (`siloParentRevocation`) across both object-backed IAM and STS enumeration, and reloads committed state on peer delete notifications.
   - Moved slow IAM policy loads and KMS decryption outside the hot authentication-cache lock while propagating KMS request cancellation ([design record](/blog/design/iam-policy-cancellation/)); fixed LDAP `StartTLS` precedence and hex-escaped long DN path-component limits ([design record](/blog/design/ldap-long-dn/)).

---

## 3. S3 Protocol Completeness and End-to-End Checksums {#s3-and-checksums}

On the S3 protocol surface, SILO focused on three goals: **implementing stubbed-out bucket APIs, aligning multi-pool conditional write semantics, and ensuring end-to-end plaintext checksum and size accuracy across multipart, encrypted, and compressed objects.**

| Feature / Scenario | Upstream MinIO (`2025-10-15`) | SILO (`20261026`) | Design Record |
| --- | --- | --- | --- |
| **Per-bucket CORS** | `GetBucketCors`/`PutBucketCors`/`DeleteBucketCors` returned `NotImplemented` stubs | Full per-bucket CORS XML persistence (up to 100 rules, 64 KiB), dynamic `OPTIONS` preflight matching, site replication, and bucket metadata export/import | [Per-Bucket CORS](/blog/release/silo-20260903/#cors-trust) |
| **Conditional `DELETE`** | No `If-Match` support on `DELETE` | Single-object `DELETE` supports `If-Match: "<etag>"` and `If-Match: *` under the shared object lock; batch `DeleteObjects` does not support per-entry ETag conditions | [Conditional DELETE](/blog/design/conditional-delete/) |
| **Multi-pool conditional `PUT` & multipart completion** | Checked only the target write pool, allowing stale pool copies to accept outdated ETags or reject current ones | Resolves the logical current object across all storage pools (including draining pools) before evaluating `If-Match` / `If-None-Match` | [Multi-Pool Object Consistency](/blog/design/multi-pool-object-consistency/) |
| **Server-computed part checksums** | A checksum-enabled multipart upload rejected parts without explicit checksum headers, including copied parts | Computes plaintext part checksums using the algorithm declared at upload initialization, before compression or encryption, and persists them in `xl.meta`; uploads without a declared algorithm do not acquire a default `CRC32C` checksum | [Part Checksums](/blog/design/uploadpart-checksum/) |
| **`CompleteMultipartUpload` verification** | Permissive on duplicate part numbers, missing checksums, or `FULL_OBJECT` type mismatches | Enforces strictly ascending part numbers (`InvalidPartOrder` on duplicates) and validates part checksums and `FULL_OBJECT` / `COMPOSITE` rollups | [Checksum Integrity Repairs](/blog/design/complete-multipart-checksum-errors/) |
| **`CopyObject` / `UploadPartCopy` checksums** | Server-side copies of encrypted or compressed objects could copy ciphertext bitrot hashes and omit `ChecksumType` in responses | Computes or verifies checksums against plaintext logical bytes and returns accurate `ChecksumType` in `CopyObjectResult` / `CopyPartResult` | [Checksum Integrity Repairs](/blog/design/copyobject-ssec-checksum-response/) |
| **SSE-C same-object key rotation & zero-byte objects** | In-place `CopyObject` with a new SSE-C key updated metadata without re-encrypting payload bytes; zero-byte SSE-C objects and part attributes skipped unsealing | Rewrites ciphertext on same-object SSE-C key rotation and validates customer keys on zero-byte SSE-C reads and `GetObjectAttributes` part listings | [SSE-C Key Rotation](/blog/release/silo-20260903/#copyobject-ssec), [Zero-Byte Validation](/blog/security/20260903-server-hardening/#sn-2026-006) |
| **Logical part sizes for encrypted/compressed objects** | `GetObjectAttributes` and `?partNumber=N` could report physical encrypted/compressed shard sizes | Returns exact plaintext logical part sizes across `GetObjectAttributes` and part-number `GET`/`HEAD` requests | [Multipart Part Logical Size](/blog/release/silo-20260916/#encryption) |
| **`ObjectTampered` HTTP status** | Returned HTTP `206 Partial Content` when stored encryption metadata was tampered with | Returns HTTP `500` (`XMinioObjectTampered`) so clients and caches never treat tampered objects as valid partial responses | [ObjectTampered 500 Status](/blog/release/silo-20260916/#encryption) |
| **DNS federation `CopyObject`** | Cross-cluster federated copies could stream raw `.minio.sys` ciphertext, leaving the destination object undecryptable | Streams decrypted plaintext via standard S3 client reads and re-seals at the destination | [Federated CopyObject](/blog/design/federated-copy-object/) |
{.wide .expand}

---

## 4. Replication and Lifecycle Correctness {#replication-and-lifecycle}

In clusters running active-active replication or remote tiering, the most damaging bugs are silent divergence between sites or premature deletion of tiered data. Over the past year, SILO fixed six replication and lifecycle failure modes:

| Area | Upstream Behavior and Risk | SILO Behavior |
| --- | --- | --- |
| **Multipart `FULL_OBJECT` checksum replication (`#255`)** | When replicating a multipart object with a `CRC32`/`CRC32C` `FULL_OBJECT` checksum, the source omitted `x-amz-checksum-type: FULL_OBJECT` on `NewMultipartUpload`, causing the target to validate as `COMPOSITE` and fail `CompleteMultipartUpload` with `BadDigest` | Propagates `ChecksumType` in `putReplicationOpts` so multipart replication and `CopyObject` share the full checksum header contract ([design record](/blog/design/replication-full-object-checksum/)) |
| **SSE-C replica integrity** | Replicating SSE-C objects regenerated KMS/DARE seals or corrupted the customer-key seal on the target replica | Preserves raw SSE-C ciphertext, random IVs, and cryptographic seals across trusted replication peers ([design record](/blog/design/ssec-replica-integrity/)) |
| **Timestamped tag deletion & out-of-order convergence** | Tag deletion sent an empty string without advancing a revision timestamp, letting delayed replication events resurrect deleted tags; SSE-KMS copies also dropped tag revision timestamps | Adds `replication-tag-modtime` timestamps and deletion tombstones, preserves timestamps across SSE-KMS copies, and rejects stale out-of-order tag events ([design record](/blog/design/replicated-tag-ordering/)) |
| **Object Lock retention ordering** | Concurrent cross-site Object Lock retention updates lacked deterministic ordering, allowing stale events to overwrite newer retention dates | Adds `replication-retention-modtime` and converges retention state under persistence locks ([design record](/blog/design/object-lock-replication-ordering/)) |
| **Delete-marker replication & version purge** | Exact-version purges could create delete markers on drives missing the version, and MRF retry queues could conflate marker creation with permanent version purge | Separates delete-marker creation from permanent version purge, re-checks source state under the replication lock before sending queued marker creations, and requires write-quorum majority confirmation for missing-version purges ([design record](/blog/design/replication-reliability/)) |
| **Tiered versioned lifecycle expiration (`#253`)** | When a lifecycle `Expiration` rule on a versioned bucket (or versioning-suspended bucket with non-`null` versions) only wrote a delete marker, upstream could still delete the remote tier payload backing historical versions | Distinguishes delete-marker insertion from permanent version expiration, keeping remote tier payloads intact whenever expiration only adds a delete marker |
{.wide .expand}

SILO also isolated per-job and per-target cancellation contexts and fixed `ReplicatedCount` / `FailedCount` accounting in replication resync ([Replication Resync Correctness](/blog/design/replication-reliability/#resync)), and added per-bucket locks plus optional field-level tombstones (`MINIO_SITE_REPLICATION_METADATA_TOMBSTONES`) for bucket configuration convergence ([Bucket Metadata Convergence](/blog/design/bucket-metadata-convergence/)).

---

## 5. Storage Mutation, Rollback, and Multi-Pool Safety {#storage-and-multipool}

Slow drives, failed writes, concurrent overwrites and multi-pool scaling need distinct safeguards. The 20261026 release retains the shipped multi-pool locking, deletion, migration and listing repairs, with explicit timeout and rollback limits.

### 1. Storage RPC and Timeout Boundaries

This release forwards storage RPC deletion options, including the previous data directory needed for overwrite rollback. Drive/RPC deadlines, request cancellation, object locking, read quorum and healing retain their established behavior.

**A returned timeout does not prove that underlying I/O stopped or that the write did not commit.** Late commits or delayed `UndoWrite` can still affect newer writes; partial failures, lease loss and network partitions can still expose stale values or tags. This release adds no distributed fencing and cannot repair previously inconsistent objects.

The October maintenance candidates explored admitted-I/O waits, per-drive object mutation locks, rollback ownership checks, backup serialization and generating PUT timestamps inside the commit lock. These changes were withdrawn in [`dcc2f20ba`](https://github.com/pgsty/silo/commit/dcc2f20ba81c51a11dab047bb65c86e0dc6a6038) and are not delivered capabilities. Their tests and microbenchmarks do not establish guarantees for the final source.

The missing-staging-`xl.meta` classification shipped in 20261018 remains: HTTP 503 `SlowDownWrite` allows retry rather than falsely reporting an absent object. See the [error classification design](/blog/design/stale-metadata-reuse/) and [final maintenance boundaries](/blog/design/multi-pool-object-consistency/#maintenance-20261026).

### 2. Multi-Pool Locking, Two-Stage Bulk Deletion, and Migration Safety

For multi-pool deployments:

- **Shared cross-pool namespace locks**: Fixed pool-local lock isolation where concurrent writes, deletes, and metadata updates on different pools failed to serialize against one another.
- **Two-stage multi-pool deletion (`#257`)**: Previously, multi-pool `DeleteObjects` issued parallel deletes across all pools; if the pool holding the newest version succeeded while a pool holding an older copy failed due to a drive error, the stale copy resurfaced as the current object. SILO now deletes in two stages—cleaning non-authoritative duplicate pools first and removing the authoritative copy only after stale copies are gone, while protecting referenced remote tier objects on partial failure ([Multi-Pool Delete Safety](/blog/design/multi-pool-delete-safety/)).
- **Rebalance and decommission safeguards**: Preserved object tags and revision timestamps across pool migration and prevented decommission from overwriting newer versions or dropping delete markers on the destination pool ([Multi-Pool Object Consistency](/blog/design/multi-pool-object-consistency/#migration-20261018)).

### 3. `LIST` Recovery Under Drive Disagreement (`#239`)

During rolling restarts with concurrent overwrites, minority drive disagreements or unresolved entries could cause `ListObjects` to omit readable keys. While keeping the lock-free fast path intact, SILO now confirms eligible unresolved latest-object entries on demand, distinguishes real deletions from drive read errors, and propagates terminal errors through pagination ([LIST Recovery Design Record](/blog/design/listing-recovery-lock-cost/)).

---

## 6. Restoring the Full Control Plane: SILO Console v2.5.1 and mcli 20261026 {#console-and-mcli}

For day-to-day operators, the most visible difference between SILO and upstream MinIO is the administration control plane.

### SILO Console v2.5.1: From a Stripped Browser Back to a Full Admin Console

In mid-2025, upstream stripped the embedded community Console down to `v1.7.7`—removing cluster administration, IAM, policies, lifecycle, replication, diagnostics, and monitoring panels to leave only a bare object browser—and subsequently deleted `github.com/minio/console`.

Building on the community restoration initiated by Georg Mangold (`@gmangold`), SILO shipped six major Console releases (`v2.0.0` through `v2.5.1`), restoring the full administration suite while making the frontend smaller, faster, and telemetry-free:

| Dimension | Upstream `2025-10-15` Embedded Console (`v1.7.7`) | SILO Console `v2.5.1` |
| --- | --- | --- |
| **Administrative Scope** | Basic bucket and object browser only; all admin panels removed | **Full administration console**: Overview dashboard, Buckets, Object Browser, Lifecycle, Replication, Tiering, Notifications, IAM (Users/Groups/Service Accounts/Policies with built-in policy Reset), IDP (OIDC/LDAP), KMS, Diagnostics (Health/Trace/Logs/Watch/Speedtest/Profile), and background Tasks |
| **Bundle Size & Telemetry** | ~10 MB bundle with external font/script dependencies and call-home hooks | **`< 3 MB`** byte-for-byte reproducible bundle, zero telemetry, zero external network dependencies, responsive light/dark themes |
| **Localization** | English only | **Native English and Simplified Chinese toggle** across UI, error messages, and documentation links |
| **Metrics Integration** | Legacy endpoints or removed | Native **Metrics V3** integration that distinguishes real zeros from missing node data |
| **Large-Bucket Browsing & Previews** | Unbounded directory fetches prone to browser freezes | **Cursor pagination** (default 100, up to 1,000 per page), bounded 1 MiB text/Markdown/CSV/code preview, and native streaming ZIP multi-object downloads |
| **High-Latency Diagnostics (`#63`)** | Health-report downloads over high-latency links failed with WebSocket `1006` / `1011` truncation | Fixed WebSocket close handshakes across all six diagnostic streams and repaired the `madmin v3` stream decoder pre-read bug, verified under 250 ms each-way injected latency |
{.wide .expand}

Console 2.5.1 also fixes group membership during status changes, OIDC group permissions, TLS-proxy session cookies, credential exports and keyboard focus. See the [Console 2.5 series notes](/blog/release/console-2.5.1/).

### mcli 20261026: Honest Exit Codes and Read-Only Checksum Verification

On the client side, `pgsty/mc` ships as `mcli` (while preserving `MC_*` environment variables and `~/.mc` / `~/.silo` configuration compatibility) and fixes long-standing CLI reliability gaps:

- **Read-only `mcli checksum verify`**: Verifies end-to-end `FULL_OBJECT` checksums across buckets, prefixes, or object versions directly against the server without mutating objects or writing local files, supporting `--versions`, `--Algo`, and `--json`.
- **Nonzero exit codes on partial or permission failures**:
  - `mcli admin info --json` now exits nonzero when access is denied or a node reports `status: error` (upstream exited `0`);
  - `mcli mirror`, `mcli mv`, `mcli retention`, `mcli legalhold`, and `mcli sql` all return nonzero exit codes on partial object failures, source-deletion errors, or permission denials;
  - Downloads interrupted mid-stream fail immediately rather than reporting a truncated file as complete.
- **Safe `mirror` delete propagation and `--dry-run` restarts**: Prevented `mirror --remove` from deleting destination objects when source listing fails; added `--dry-run` to `mcli admin service restart`; and honored optional persisted `region` settings in alias configurations.

The 20261026 client also isolates cached identities, drains resync JSON through terminal states, fixes rate overflow, returns nonzero for partially failed start/cancel operations, and adds batch `pending` output with bounded fallback when live metrics are missing. See the [mcli changes and script migration notes](/blog/release/silo-20261026/#mcli).

---

## 7. Operations, Configuration, and Supply-Chain Delivery {#operations-and-delivery}

Across server operations and artifact delivery, SILO made four practical changes:

1. **Enforced request-header timeouts and trusted-proxy boundaries**:
   - Upstream defined `--read-header-timeout` / `MINIO_READ_HEADER_TIMEOUT` without wiring it into `http.Server`, leaving HTTP/1 connections vulnerable to slowloris-style trickle headers. SILO wired the setting into the HTTP server with a 30-second absolute HTTP/1 header deadline ([design record](/blog/design/request-header-timeouts/)).
   - Added `MINIO_API_TRUSTED_PROXIES` and `MINIO_IDENTITY_LDAP_STS_TRUSTED_PROXIES` so `X-Forwarded-For` is never trusted blindly by default; added `CONSOLE_WS_MAX_MESSAGE_BYTES` and `CONSOLE_WS_MAX_DECOMPRESSED_BYTES` to bound embedded Console WebSocket frames.
   - Added a native `silo healthcheck` subcommand for shell-free distroless containers and tightened `MINIO_CONFIG_ENV_FILE` parsing to reject malformed lines.
2. **Hardened event notification targets**:
   - Fixed NATS reconnect handling and JetStream async reply subjects, AMQP confirm-mode lock contention, PostgreSQL/MySQL TLS configuration loading, and preserved Kafka's default protocol version `2.1`.
3. **Permanently removed self-update and call-home**:
   - Removed in-place binary self-update (`MINIO_UPDATE`) and all `SUBNET` registration, telemetry, license checks, and phone-home endpoints. Upgrades are managed cleanly through OS packages (`RPM`/`DEB`/`APK`) and container images.
4. **Rebuilt a verifiable multi-architecture supply chain**:
   - Built all components with **Go 1.27.3** (including built-in `crypto/x509` distrusted-intermediate checks), UBI 9.8 and distroless container variants, static `curl 8.23.0`, and Red Hat's `RHSB-2026-012` root CA blocklist.
   - Published Linux (`amd64`/`arm64`/`ppc64le`/`s390x`), macOS (`amd64`/`arm64`), and Windows (`amd64`/`arm64` ZIP) archives, RPM/DEB/APK packages, and multi-arch Docker Hub images (`pgsty/silo`, `pgsty/silo-console`, `pgsty/mc`, `pgsty/kes`) backed by GPG signatures, SPDX SBOMs, and GitHub Sigstore build attestations (see [Downloads](/download/)).

---

## 8. Honest Boundaries: Withdrawn Experiments and Open Limits {#boundaries-and-lessons}

Maintaining storage software in production requires knowing **what to roll back when an idea does not survive real capacity or failure testing**. Over the past year, we implemented, benchmarked, and deliberately withdrew or closed four designs:

1. **Withdrew public persistent `ListMultipartUploads` disk scanning ([#79](https://github.com/pgsty/silo/issues/79))**:
   - **Goal**: Upstream's `ListMultipartUploads` reads only a node-local in-memory cache, losing visibility of incomplete uploads across restarts. In September we implemented a persistent scan across storage pools and erasure sets.
   - **Why we rolled it back**: Capacity testing showed scan latency grew linearly with prefix depth and abandoned upload count, timing out at 20,000 incomplete uploads and amplifying drive I/O. In Server 20261018 we withdrew public persistent scanning and retired the optional `strict` mode, returning to the node-local cache plus exact-key lookup (see [ListMultipartUploads Design and Capacity Evidence](/blog/design/list-multipart-uploads/#implementation)).
2. **Deferred strict generation read refusal and automatic cross-pool read recovery**:
   - **Goal**: When partial overwrite failures left split object generations across drives or pools, we tested refusing divergent reads or auto-recovering across pools during `GET`.
   - **Why we deferred it**: Fault-injection testing showed that refusing reads after a failed partial overwrite broke MinIO's established availability contract (where the prior readable version remains accessible). Those strict diagnostics remain gated behind the non-default `consistency_strict` build tag while production builds preserve existing read-quorum and healing behavior.
3. **Closed multi-pool overwrite affinity without merge ([#245](https://github.com/pgsty/silo/pull/245))**:
   - **Goal**: In multi-pool clusters, unversioned overwrites can land on a different pool and leave stale copies on the old pool. PR `#245` routed overwrites back to the object's existing pool.
   - **Why we closed it**: When the historical pool lost write quorum due to failed drives while another pool remained healthy, forced affinity caused overwrites to fail outright—and two rounds of multi-node `m3` benchmarks showed small-object overwrite latency still missed our bar (see [Overwrite Pool Affinity](/blog/design/overwrite-pool-affinity/)).
4. **Removed experimental access-frequency intra-cluster tiering (`ilm access_*`)**:
   - The experimental feature never met production reliability requirements and was removed in Server 20260916 (see [Access-Frequency Tiering Removal](/compatibility/access-tiering-removal/)).

### Remaining Operational and Upgrade Boundaries

When evaluating or upgrading to SILO, keep these boundaries in mind:

- **No distributed lock fencing**: If a node loses its lock lease during a GC pause, network partition, or stalled drive, an already-admitted commit on that node can still land late; partial metadata updates can still briefly expose stale tags or attributes. The release retains existing timeout semantics; a returned request is not proof that underlying I/O has stopped.
- **No unverified cluster-wide throughput claims**: We verify hot-path microbenchmarks (for example, `silo-pkg v3.14.3` reduced `ContainsAdminAction` from 24 allocations and `742.5 ns/op` to zero allocations and `5.53 ns/op`), but we have not run a head-to-head multi-node benchmark between `2025-10-15` and `2026-10-26` on dedicated hardware.
- **Coordinated upgrades for new IAM and replication state**: While on-disk `xl.meta` v1.3 remains compatible, features such as durable IAM revocations (`siloParentRevocation`) and site-replication metadata tombstones require all participating nodes to upgrade together rather than running mixed versions indefinitely or performing rolling downgrades (see the [Component Matrix](/compatibility/versions/) and [IAM Upgrade Guide](/operations/replication/iam-upgrade/)).
- **Known minor items**: The repository's Helm chart (`7.0.3`) default server image tag still points to `RELEASE.2026-09-16T00-00-00Z` (override `image.tag` in `values.yaml` when deploying newer releases), and two legacy batch-lifecycle handlers in Console (batch expiration and batch transition creation) have early-return/empty-slice quirks that do not affect single-rule configuration and are queued for the next Console patch.

---

## Closing Note {#conclusion}

When we forked MinIO a year ago, the goal was simple: keep a production-grade open-source S3 server alive with timely CVE patches, a complete administration console, honest bug fixes, and clean binary and container distributions.

One year later—604 commits, 7 CVE patches, 18 security boundary hardenings, and dozens of root-cause write-ups in our [Design Archive](/blog/design/) and [Security Archive](/blog/security/)—that is the ledger of what SILO has done.

If you are running open-source MinIO, see the [Migration Guide](/compatibility/migration/) and [Downloads page](/download/). If you hit a reproducible protocol, replication, or storage bug in production, open an issue at [`pgsty/silo`](https://github.com/pgsty/silo).

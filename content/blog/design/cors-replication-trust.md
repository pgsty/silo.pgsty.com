---
title: "No I/O Before Auth, No Privilege From Headers"
linkTitle: "CORS & Replication Trust"
date: 2026-09-01
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  A pre-authentication CORS lookup turned arbitrary URL path segments into metadata I/O and cache entries, while a client-controlled replication marker acquired privileges across SSE-C reads, source timestamps, checksums, Object Lock, events, and deletes. This note defines SILO's resident-only CORS hot path, two-level replication trust model, and post-signature sanitization boundary.
tags: [Design, Security, CORS, Replication, SSE-C, Compatibility]
weight: 12
draft: false
url: "/blog/design/cors-replication-trust/"
---

This note documents the CORS hot-path and replication-request trust repair merged in [PR #101](https://github.com/pgsty/silo/pull/101) (`938603458` through `04b097fd9`), tracked as [SN-2026-008](/about/security-advisories/#sn-2026-008), and shipped in [Server 20260903](/blog/release/silo-20260903/).

## Overview {#tldr}

Two defects that appeared unrelated shared a single architectural root cause:

1. Any request carrying an `Origin` header caused the outermost CORS middleware to treat the first URL path segment as a bucket name and synchronously load its metadata from disk before authentication.
2. Any request carrying `X-Minio-Source-Replication-Request` caused downstream handlers to treat the operation as internal replication merely because the header was present.

In both cases, **untrusted request syntax acquired expensive or privileged internal meaning before crossing an authorization boundary**.

The repair enforces two invariants:

```text
before authentication:  parse cheaply; never perform storage I/O
after authentication:   derive one trust decision; downstream code consumes it
```

For CORS, the outer middleware reads only bucket metadata already resident in memory. For replication, handlers authenticate the original signed request first, authorize the required replication action (`s3:ReplicateObject` or `s3:ReplicateDelete`), and attach a private trust decision to the request context. Untrusted internal headers are stripped only after SigV4 verification completes. Downstream option builders, encryption paths, Object Lock checks, event emitters, and metadata writers consume that context decision rather than inspecting raw headers.

## Failure A: Pre-Authentication CORS Amplification {#cors-failure}

`corsHandler` wraps the entire HTTP router. Every request carrying an `Origin` header reaches it before SigV4 authentication, request validation, and API concurrency limiters.

Previously, per-bucket CORS evaluation called the general bucket metadata loader:

```text
Origin-bearing request
  -> first URL segment treated as "bucket"
  -> GetCorsConfig
  -> GetConfig cache miss
  -> read .metadata.bin
  -> probe ten legacy config paths
  -> insert default BucketMetadata record into metadataMap
```

When `.metadata.bin` did not exist on disk, the loader probed ten legacy configuration file paths. When none existed, it returned a newly allocated empty `BucketMetadata` struct rather than `NoSuchBucket`, and `GetConfig` inserted that synthetic entry into the in-memory `metadataMap`.

An unauthenticated client could therefore send `Origin`-bearing requests for an unbounded sequence of syntactically valid, nonexistent bucket names and trigger two effects per distinct name:

- Unthrottled erasure/storage metadata reads (`.metadata.bin` plus ten legacy probes) before authentication.
- Unbounded growth of the in-memory bucket `metadataMap` (pruned only every 15 minutes on distributed clusters, and never pruned until restart on single-node deployments).

## Failure B: A Marker Header Treated as Authority {#replication-failure}

SILO and MinIO-compatible replication engines exchange internal headers to preserve source state across sites, anchored by:

```http
X-Minio-Source-Replication-Request: true
```

Before this repair, multiple code paths treated the presence or string value of that header as proof that the caller was a trusted replication peer:

- `GetObject`, `HeadObject`, and `GetObjectAttributes` on an SSE-C object could set `NoDecryption` and return raw ciphertext without requiring the customer key to any caller holding ordinary `s3:GetObject` permission.
- Caller-supplied source ETag and modification time (`MTime`) could overwrite server-generated values.
- Source tagging, retention, and legal-hold timestamps could influence last-writer-wins conflict resolution.
- Past Object Lock `RetainUntilDate` timestamps were accepted via a raw header check.
- Delete-marker version IDs and timestamps could be injected by the caller.
- Object creation and access notifications could be suppressed.
- Multipart actual object size and encrypted checksum metadata could be injected during `CompleteMultipartUpload`.
- `X-Amz-Replication-Status: REPLICA` could be persisted from ordinary `PutObject`, `CopyObject`, Snowball/PAX archives, or browser `POST` policy uploads.

The earlier [CVE-2026-34204 repair](/blog/security/cve-2026-34204/) prevented ordinary `PutObject` and `CopyObject` calls from importing replication SSE metadata, but it did not establish a single post-authorization authority shared by all consumers of replication headers.

## Replication Trust Design {#design}

### One Exact Marker, Two Trust Levels {#trust-levels}

The marker header `X-Minio-Source-Replication-Request` is considered present only when it appears as a single header line with the exact lowercase value `"true"`. Multiple header values, mixed case, or any other string are treated as untrusted.

After authenticating the caller, the handler derives two distinct trust flags:

| Decision | Requirements | Enabled Semantics |
| --- | --- | --- |
| `trusted` | Authenticated non-anonymous principal + exact marker + `s3:ReplicateObject` (or `s3:ReplicateDelete`) on the target resource | Source ETag/MTime and timestamps; multipart actual size and encrypted checksum transfer; notification and re-replication suppression; delete version/pool pinning |
| `replicaTrusted` | `trusted` + raw request status `REPLICA` (or a multipart upload whose stored initiation status is `REPLICA`) | `REPLICA` status persistence; replication SSE sealed-key import; SSE-C raw ciphertext (`NoDecryption`) path; replica Object Lock exceptions |

Separating `trusted` from `replicaTrusted` is required by the wire protocol because legitimate multipart part uploads, multipart completions, and batch replication writes send `X-Minio-Source-Replication-Request: true` without repeating `X-Amz-Replication-Status: REPLICA` on every request.

Incoming requests are classified as follows:

| Incoming Request Shape | Receiver Outcome |
| --- | --- |
| No marker | Ordinary S3 operation |
| Marker present, caller lacks replication permission | Internal replication headers stripped and ignored; request proceeds as an ordinary S3 operation |
| `X-Amz-Replication-Status: REPLICA` without replication permission | Rejected with `403 AccessDenied` |
| Exact marker + replication permission, no `REPLICA` | `trusted` only |
| Exact marker + replication permission + `REPLICA` | Both `trusted` and `replicaTrusted` |

Explicitly rejecting unauthorized `REPLICA` claims with `403 AccessDenied` prevents a misconfigured replica write from silently downgrading into a new `PENDING` source object that would trigger a reverse replication loop.

### Authenticate Original Request, Then Sanitize {#signature-boundary}

Because AWS SigV4 signs `x-amz-*` and `x-minio-*` headers, stripping internal headers before signature verification would alter the canonical request and fail valid requests with `SignatureDoesNotMatch`. The execution order is therefore strict:

```text
original HTTP request
  -> SigV4 signature and authentication check
  -> ordinary S3 action authorization
  -> replication action authorization (s3:ReplicateObject / s3:ReplicateDelete)
  -> derive trusted / replicaTrusted flags
  -> bind trust decision to request context
  -> clone request and strip untrusted internal headers (sharing original trailer)
  -> option builders, encryption, Object Lock, storage, and notifications
```

The header-stripped request clone shares the original `http.Request.Trailer` map so `aws-chunked` streaming-checksum uploads continue working for ordinary clients. Snowball/PAX batch archives isolate trust per archive entry (`ff44527a3`) while preserving legitimate request defaults across worker goroutines (`ab3ae99ca`).

### Replica Status Removed from Generic Metadata {#replica-status}

`X-Amz-Replication-Status` is removed from the generic user-metadata extraction allowlist. Ordinary `PutObject`, `CopyObject`, `CreateMultipartUpload`, Snowball extraction, and HTML `POST` policy forms can no longer persist `REPLICA` status by submitting the header or form field; the server sets `REPLICA` only inside a verified `replicaTrusted` branch.

### Object Lock Receives an Explicit Decision {#object-lock}

The Object Lock parser no longer inspects `X-Minio-Source-Replication-Request` directly. Instead, handlers pass `allowPastRetainDate` explicitly from `replicaTrusted`, and use the same `replicaTrusted` decision when checking whether an existing compliance or legal-hold version may be overwritten by an incoming replica.

## Replication Wire Matrix {#wire-matrix}

| Operation | Marker | `REPLICA` Header on Request | Receiver Decision |
| --- | --- | --- | --- |
| Replicated `PutObject` | Yes | Yes | `replicaTrusted` |
| Replicated `CreateMultipartUpload` | Yes | Yes | Persist trusted multipart `REPLICA` provenance |
| Replicated `UploadPart` | Yes | No | `trusted`; promoted to `replicaTrusted` only when stored MPU status is `REPLICA` |
| Replicated `CompleteMultipartUpload` | Yes | No | `trusted`; preserves source ETag/MTime, actual size, and encrypted checksum |
| `CopyObject` metadata replication | Yes | Yes | `replicaTrusted` |
| Replicated `DeleteObject` | Yes | Yes | `replicaTrusted` (requires `s3:ReplicateDelete` plus `s3:DeleteObject`, with no explicit deny on `s3:DeleteObjectVersion`) |
| Batch replication `PUT` / `Complete` | Yes | No | `trusted` (target credentials must hold `s3:ReplicateObject`) |
| Proxy / readiness / validity probes | Probe headers | No | Probe headers are preserved; validity probes verify replication permissions under the rule prefix (`c9ad74673`, `5db7be4ee`) |

## CORS Resident-Only State Machine {#cors-state-machine}

The outer CORS middleware calls a dedicated resident-only accessor that acquires a single in-memory read lock and performs zero storage I/O:

| In-Memory Bucket Metadata State | CORS Decision | Storage I/O |
| --- | --- | --- |
| Resident, valid per-bucket CORS config | Apply per-bucket CORS rule (a failed background refresh retains the last valid config) | None |
| Resident, no per-bucket CORS config | Use global CORS fallback | None |
| Resident, corrupted stored CORS XML | Fail closed (omit CORS headers and log once) | None |
| Non-resident while initial startup load is still running | Fail closed | None |
| Non-resident after startup: known disk bucket whose metadata failed to load | Fail closed | None |
| Non-resident after startup: nonexistent, reserved, invalid, or `.minio.sys` name | Use global CORS fallback | None |

Both startup-in-progress and known load-failure states fail closed: because a presigned URL carries its own credentials in the query string, the bucket's custom CORS policy is the only browser origin boundary protecting it, and falling back to the permissive global CORS policy during a metadata load failure would expose the presigned URL to arbitrary origins.

## Rejected Alternatives {#alternatives}

| Rejected Alternative | Reason for Rejection |
| --- | --- |
| Validate bucket syntax before calling the old CORS loader | Attackers can generate an unbounded stream of syntactically valid, nonexistent bucket names that still trigger pre-auth storage I/O |
| Call `GetBucketInfo` before loading CORS | Replaces 11 metadata probes with at least 1 unthrottled storage stat call per attacker-supplied bucket name |
| Cache negative bucket lookups with a TTL | Bounds cache lifetime, not attacker key cardinality or initial storage I/O amplification |
| Strip replication headers before SigV4 authentication | Breaks SigV4 canonical request verification (`SignatureDoesNotMatch`) |
| Reject every request carrying `X-Minio-Source-Replication-Request` | Breaks legitimate marker-only batch replication and multipart replication calls |
| Require `REPLICA` on every trusted replication call | Breaks replicated `UploadPart`, `CompleteMultipartUpload`, and batch replication wire compatibility |
| Store a boolean in `ObjectOptions` while leaving events and Object Lock on raw headers | Leaves two authorities that can disagree |

## Implementation and Verification {#implementation}

The implementation is structured into seven boundaries:

1. A dedicated request-trust helper parses the exact marker, evaluates replication IAM permissions, binds the private trust struct to `req.Context()`, and returns the post-auth sanitized request clone.
2. `putOpts`, `copyDstOpts`, `getOpts`, and `delOpts` builders extract source replication fields only when the context decision is `trusted` or `replicaTrusted`.
3. `DecryptObjectInfo`, notification event builders, multipart completion, delete options, and Object Lock consume the same context decision.
4. S3 handlers compute replication trust immediately after their authentication check.
5. `PutObjectPart` combines current-request `trusted` state with the multipart upload's persisted `REPLICA` provenance.
6. Generic metadata extraction excludes `X-Amz-Replication-Status`.
7. `corsHandler` calls the resident-only metadata accessor and never invokes the load-on-miss getter.

### Verification Matrix {#verification}

Automated and black-box two-site TLS replication tests verify:

- Hundreds of distinct nonexistent bucket names across actual and preflight CORS requests with zero storage metadata reads and zero `metadataMap` growth.
- Least-privilege SSE-C `GetObject`, `HeadObject`, and `GetObjectAttributes` calls rejecting forged, wrong-case, or unauthorized replication markers.
- Marker-only batch `PutObject` preserving source ETag/MTime only when the caller holds `s3:ReplicateObject`.
- Unauthorized `REPLICA` `PutObject` and `DeleteObject` returning `403 AccessDenied`.
- Browser `POST` policy uploads unable to inject `REPLICA` status.
- Object Lock past retention dates rejected without `replicaTrusted` and accepted for authorized replicas.
- End-to-end SSE-C single-part (`4 KiB`), multipart (`12 MiB`, 3 parts), `CopyObject`, and delete-marker replication across two live TLS-enabled SILO nodes with matching ETag, version ID, SSE-C key MD5, and decrypted SHA-256 digests.

## Compatibility and Follow-Up Work {#impact}

- **Ordinary clients:** Unchanged; untrusted internal replication headers are ignored rather than acquiring privileged internal behavior.
- **Batch replication:** Target credentials must include `s3:ReplicateObject` as documented in [Batch Replication](/administration/batch-framework-job-replicate/); without it, marker-only writes fall back to ordinary writes and generate fresh ETag and `MTime` values.
- **Rolling upgrades:** Wire and on-disk formats are unchanged. Upgraded nodes enforce the resident-only CORS lookup and replication trust boundary immediately.

### Subsequent Follow-Ups {#residual-risks}

- **Replication execution reliability (2026-09-09):** [Replication Reliability: Delete Completion, MRF Visibility, and Resync Cancellation](/blog/design/replication-reliability/) documents the fixes in [PR #162](https://github.com/pgsty/silo/pull/162) for [#153](https://github.com/pgsty/silo/issues/153), [#152](https://github.com/pgsty/silo/issues/152), and [#137](https://github.com/pgsty/silo/issues/137) after trusted requests enter the replication pipeline.
- **Rate-limited diagnostics:** Receivers log a rate-limited warning when a marker-bearing request lacks replication permission so operators can spot misconfigured batch replication policies without log flooding.

## Conclusion {#conclusion}

Merged in [`0079723d3`](https://github.com/pgsty/silo/commit/0079723d38b59cc37781523915a60bcfa21c9706) ([PR #159](https://github.com/pgsty/silo/pull/159)) and shipped in [Server 20260916](/blog/release/silo-20260916/), the resident-only CORS lookup and post-authentication replication trust boundary close both the unauthenticated bucket-metadata probe path and untrusted replication-header injection.

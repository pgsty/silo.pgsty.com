---
title: "Replica Metadata Normalization: What a Trusted Copy May Not Re-Inject"
linkTitle: "Replica Metadata Normalization"
date: 2026-09-16
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  The decision record for PR #194 (fix 4fcdf37ce): trusted replication COPY re-extracted raw request metadata through the permissive path, so transport-only aws-chunked encodings and GHSA-redacted user metadata came back into stored objects. Covers the expected encoding mappings, the Snowball behavior change, why upgrading does not repair existing objects, and the status of the stored-metadata remediation proposal.
tags: [Design, Replication, S3, Review]
weight: 9
draft: false
url: "/blog/design/replica-metadata-normalization/"
---

Shipped in [SILO Server 20260916](/blog/release/silo-20260916/) (`40220bd836cbd066ca424fa4dc5dbb90057fb55a`), [PR #194](https://github.com/pgsty/silo/pull/194) (commit [`4fcdf37ce`](https://github.com/pgsty/silo/commit/4fcdf37ce), merged as [`9f3037e941`](https://github.com/pgsty/silo/commit/9f3037e941a49ab4cd8a0eed7c0f01083fbe4bbe), retaining Mikhail Khadarenka's original implementation from [PR #187](https://github.com/pgsty/silo/pull/187)) fixes a regression where a trusted replication receiver re-extracted raw request headers through the permissive metadata extractor, re-injecting transport-only `aws-chunked` `Content-Encoding` tokens and GHSA-redacted user metadata into stored replica objects.

## What Went Wrong {#problem}

The ordinary S3 `PUT` path normalizes incoming request metadata before storing an object: it strips the transport-only `aws-chunked` token from `Content-Encoding`, and deletes the `X-Amz-Meta-X-Amz-Unencrypted-Content-Length` and `X-Amz-Meta-X-Amz-Unencrypted-Content-Md5` user-metadata keys removed by the [GHSA-76wf-9vgp-pj7w](https://github.com/google/security-research/security/advisories/GHSA-76wf-9vgp-pj7w) mitigation.

However, when the trusted replication receiver restored internal replication metadata on an incoming replica write, it re-ran the same general-purpose header extractor with the `allowReplication` boolean flag enabled. Re-running that extractor replayed every supported standard header and all `X-Amz-Meta-*` user metadata from the raw HTTP request over the already-normalized metadata map. As a consequence, on a trusted replica write the server could persist and later return via `GET` or `HEAD`:

- `Content-Encoding: aws-chunked` (a SigV4 streaming transport framing token that must never be stored as object metadata) or the unsplit `aws-chunked,gzip` string instead of `gzip`;
- the two GHSA-redacted `X-Amz-Meta-X-Amz-Unencrypted-Content-*` keys on trusted replica writes;
- for Snowball archive entries lacking their own PAX metadata header, the outer archive request's `Content-Type`, `Cache-Control`, `Expires`, and user metadata.

The object payload bytes on disk were unaffected, but the stored `xl.meta` headers were polluted. This regression was introduced in commit [`56fa63bfd`](https://github.com/pgsty/silo/commit/56fa63bfd) (2026-04-15, the replication header trust boundary hardening for [CVE-2026-34204](/blog/security/cve-2026-34204/)), whose authentication and trust-boundary enforcement remains intact.

## The Fix {#fix}

In `cmd/handler-utils.go`, commit [`4fcdf37ce`](https://github.com/pgsty/silo/commit/4fcdf37ce) deletes the boolean dual-mode helper and separates standard metadata extraction from replication-specific restoration:

- The ordinary metadata extractor unconditionally skips internal replication-only header keys.
- A dedicated replica metadata extractor (`extractReplicationMetadata`) walks only the replication-to-internal header mapping table and restores **only** the six replication-scoped fields:
  1. SSE-C sealed key material (`x-minio-internal-server-side-encryption-ssec-key`),
  2. SSE-C sealed algorithm (`x-minio-internal-server-side-encryption-ssec-seal-algorithm`),
  3. SSE-C initialization vector (`x-minio-internal-server-side-encryption-ssec-iv`),
  4. Encrypted multipart marker (`x-minio-internal-encrypted-multipart`, honored by key presence even with an empty value),
  5. Actual logical object size (`x-minio-internal-actual-size`),
  6. SSE-C checksum identity mapping.
- `extractReplicationMetadata` never re-reads standard S3 headers (`Content-Encoding`, `Content-Type`, `Cache-Control`, `Expires`) or `X-Amz-Meta-*` user metadata.

Stored `Content-Encoding` values after the fix:

| Requested `Content-Encoding` | Stored `Content-Encoding` |
| :-- | :-- |
| `aws-chunked` | *(none)* |
| `aws-chunked,gzip` | `gzip` |
| `gzip` | `gzip` |

Note that `aws-chunked, gzip` (with a space after the comma) continues to store ` gzip` with a leading space, and `gzip, aws-chunked` continues to store the full string; both match pre-existing parser behavior on the ordinary `PUT` path and are pinned as status-quo test assertions.

## Operator-Visible Behavior Changes {#behavior}

- **Trusted Snowball archive entries:** Entries inside a trusted Snowball archive no longer inherit the outer HTTP request's ordinary metadata (`Content-Type`, `Cache-Control`, `Expires`, and user metadata) when PAX records are absent or omit those fields. Per-entry `minio.metadata.*` PAX records still apply, the six replication-scoped fields still apply to authorized entries, and the outer archive's storage class is still inherited. (The in-tree batch producer calls `PutObjectsSnowball` with the auto-extract marker without marking the outer request as a trusted replica, so it was unaffected.)
- **GHSA-redacted keys:** `X-Amz-Meta-X-Amz-Unencrypted-Content-Length` and `-Md5` are never re-inserted during replica metadata restoration, matching ordinary `PUT` requests.
- **Unchanged boundaries:** Authentication, `s3:ReplicateObject` permission gating, and replication trust semantics are unchanged, and the ordinary `PUT` extraction path is byte-for-byte identical.

## Why Upgrading Does Not Rewrite Existing Polluted Objects {#existing}

Upgrading to [SILO Server 20260916](/blog/release/silo-20260916/) stops new metadata pollution on incoming writes, but does not scan or rewrite existing objects on disk. Two operational consequences follow:

1. **Authoritative source vs. normalized replica divergence:** If an authoritative source object still carries polluted metadata (for example, from an earlier bidirectional replication cycle) while its replica has been normalized, resync or healing comparisons may detect a metadata mismatch and repeatedly schedule metadata replication. Always remediate the authoritative source version first so replicas converge from the clean source.
2. **Limits of ordinary S3 self-`COPY`:** Issuing a standard S3 `CopyObject` to self is not a universal in-place repair tool for versioned buckets because it creates a new object version (or shifts modification timestamps) rather than rewriting a specific historical `versionId`'s metadata in place.

The [Replica Metadata Audit runbook](/operations/replication/replica-metadata-audit/) provides a read-only inventory scanner and classification rules to identify affected object versions across buckets.

### Stored-Metadata Remediation Design Guidelines {#remediation}

When planning remediation for historical objects flagged by the audit runbook:

- Build a complete version inventory (including non-current versions, not just the latest version).
- Verify payload encoding by comparing against the trusted source version or an independent checksum—never guess from the polluted `Content-Encoding` header alone, and never gunzip an object merely because a header label says `gzip`.
- Remediate the authoritative source's exact versions first and allow replication to converge downstream copies.
- Retain immutable inventories and metadata backups, validate on a local clone first, and preserve version identity, Object Lock retention and legal hold, object tags, replication status, and encryption context. Never hand-edit `xl.meta` files on disk.

## Known Scope Limits {#limits}

- The browser `POST` form upload handler (`cmd/bucket-handlers.go`) calls the low-level header extractor directly without normalizing `aws-chunked` encodings; that pre-existing path is outside the replication receiver and tracked separately.

## Verification {#verification}

Regression tests (`TestExtractReplicationMetadata*`, `TestAPIReplicaContentEncoding`, `TestAPISnowballReplicaContentEncoding`, and `-race` replication trust / SSE-C round-trip suites) verify the header mapping table, all six restored replication fields, and equivalence with the ordinary `PUT` path across single-drive and 16-drive erasure backends (64 HTTP leaf cases: 44 controls and 20 regression cases that failed prior to `4fcdf37ce`, plus 16 helper unit cases).

For the coordinated upgrade matrix, see the [component version matrix](/compatibility/versions/#september-reliability). Related September replication and HTTP hardening designs: [Replicated Tag Ordering](/blog/design/replicated-tag-ordering/) · [Request Header Timeouts](/blog/design/request-header-timeouts/) · [Replica Metadata Audit](/operations/replication/replica-metadata-audit/).

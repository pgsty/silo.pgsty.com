---
title: "SILO Next Release: Pre-Release Hardening Notes"
linkTitle: "SILO Next Hardening"
date: 2026-08-29
lastmod: 2026-08-29
author: "Ruohang Feng"
description: "Draft compatibility, integrity, site-replication, client, and release-pipeline notes for the SILO release after 20260806."
tags: [Release, Draft, Compatibility, Checksum, S3]
weight: 9
draft: true
url: "/blog/release/silo-next-hardening/"
---

> **Draft — no release tag, package, or image exists yet.** This page records
> the code and compatibility boundary being validated before the release after
> `RELEASE.2026-08-06T00-00-00Z`. Commit IDs, artifact hashes, and the final
> version will be filled only after source PRs and hosted CI are complete.

## Integrity and encryption fixes {#integrity}

- Metadata-only `CopyObject` of a null version now records compression metadata
  for the bytes the object layer actually stores. Both compression directions
  and SSE-C key rotation are covered; the previous failure modes ranged from a
  loud `s2: corrupt input` to silent short-object reads.
- Zero-byte SSE-C reads authenticate a supplied customer key even though no
  decryptor is constructed. GET, CopyObject, and UploadPartCopy now match the
  non-empty-object 403 behavior; internal no-decryption, replication, restore,
  range, and request-precondition ordering are preserved.
- `GetObjectAttributes` now unseals the SSE-C key before returning plaintext
  object size or completed multipart layout. Correct, wrong, and missing keys
  are covered for zero-byte and non-empty objects.
- CopyObject checksum metadata is decrypted with the destination key when the
  destination is re-encrypted, and explicit multipart checksum-type assertions
  are no longer accepted without their value.

## Checksum compatibility {#checksum}

SILO implements CRC32, CRC32C, CRC64NVME, SHA1, and SHA256. Requests asserting
MD5, SHA512, XXHASH64, XXHASH3, XXHASH128, or an unknown future
`x-amz-checksum-*` value/trailer now return 400 `InvalidArgument` rather than
200 with the assertion silently discarded. This includes PutObject,
CreateMultipartUpload, UploadPart, CopyObject, and UploadPartCopy.

CRC64NVME is full-object only. CRC64NVME plus `COMPOSITE` is rejected instead
of canonicalized silently. A cross-vendor replication job carrying one of the
unsupported algorithms will now fail visibly and must be retried with a
supported algorithm. See the [checksum verification design](/blog/design/checksum-verify/).

## CORS and bucket metadata {#cors-metadata}

- Per-bucket CORS replication, tombstones, strict XML/wire validation, status,
  heal, and recovery are already merged and documented in the CORS design
  records.
- Requests without an `Origin` header bypass per-bucket CORS metadata entirely.
  Admin, Console, health, and ordinary non-browser traffic no longer pay failed
  bucket-metadata reads before authentication. Operational or invalid-document
  errors remain fail-closed; a missing/no-config bucket still uses global CORS.
- Invalid CORS accepted by an earlier development build can be repaired through
  a valid `PUT ?cors` or `DELETE ?cors`. Do that before changing unrelated
  bucket metadata.

## Site replication and Object Lock {#site-replication}

- Live, initial-sync, and heal events now put Object Lock XML in
  `ObjectLockConfig`. New receivers retain a legacy `Tags` fallback for rolling
  upgrades.
- Adopting a pre-existing same-name bucket preserves its full Object Lock
  retention and enabled custom versioning rules, including excluded prefixes.
  Missing configs are bootstrapped; suspended or invalid versioning is enabled
  deliberately.
- Per-site status totals are derived from each site's valid payload rather than
  cumulative counters. Bucket policy and quota totals are now accurate;
  malformed fields emit bounded diagnostics without suppressing unrelated
  bucket statistics. Reported totals may therefore decrease or move to the
  correct site after upgrade.

The wider source-timestamp/tombstone repair for policy, tags, SSE, quota,
versioning, and Object Lock remains staged behind a peer-capability design.
This release must not claim that every inherited metadata type converges under
all delayed/mixed-version event schedules.

## MCLI and image boundary {#mcli}

The client source is split into independent review units:

- read-only `mcli checksum verify`, including reliable non-TTY JSON Lines and
  explicit quiet/report/exit semantics;
- strict validation on policy-write commands while historical reads remain
  permissive;
- regular PUT semantics for empty `mcli pipe` input, changing its ETag from a
  one-part multipart form to the standard empty-object MD5;
- tag-idempotent Release workflow retries.

The Server image must not promise the audit command until a new immutable MCLI
release exists and `Dockerfile.goreleaser` pins its real amd64/arm64 asset
checksums. The `mc` compatibility alias remains.

## Security and authorization compatibility {#authorization}

- Group enable/disable authorization is selected from the requested target
  status. A principal with only the enable action can no longer disable a
  group, and vice versa.
- New MCLI policy-write commands reject unknown fields, bare ARN statements,
  conflicting Resource/NotResource, empty statements, and missing Version for
  named policies. Existing stored/session policies remain readable under their
  historical compatibility rules.
- Config environment-file discovery preserves named targets and broader valid
  environment names. In `silo-pkg`, only exact `env://` and `env+tls://` values
  are remote references; ordinary values such as `envreview` remain literal.

## Release pipeline {#release-pipeline}

Both MCLI and Server release jobs serialize by resolved tag, verify tag-to-HEAD
identity, reject published/duplicate state, and replace only one unfinalized
Draft from scratch. The Server build lane refuses to replace a Draft carrying
the finalize lane's GPG-derived provenance marker, so retries cannot silently
restore SBOMs or attestations for unsigned RPM bytes.

Before publication, a controlled Draft/retry exercise must prove one Draft and
one copy of every asset, finalized-Draft refusal, and published-release
immutability. Tags remain immutable and are never moved.

## Deliberately deferred {#deferred}

- full source-time/tombstone convergence across all inherited site-replication
  metadata types, pending a mixed-version capability channel;
- prefix, delimiter, and pagination support for `ListMultipartUploads`, which
  requires redesigning the hashed multipart index and in-memory cache;
- persistence of the five newer checksum algorithms, which requires an on-disk
  and rolling-upgrade compatibility design.

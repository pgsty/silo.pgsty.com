---
title: "Silo Next Release"
linkTitle: "silo next"
date: 2026-09-02
author: "Ruohang Feng"
description: "Draft notes for the release after 20260806: replication and CORS request trust, Object Lock and metadata consistency fixes, AWS-aligned checksum and delete authorization, the embedded Console security fixes, and the upgrade checks operators need."
tags: [Release, silo]
weight: 9
draft: true
url: "/blog/release/silo-next/"
---

> **Draft.** The version tag, commit, commit count, and artifact digests are filled in when the tag is cut. Until then this page describes the state of `main` after the pre-release cleanup branch is merged.

**Version:** to be assigned · **Commit:** to be assigned · **Previous release:** [20260806](/blog/release/silo-20260806/)

## Highlights {#highlights}

- **Request trust is authenticated, not header-driven.** Replication-only headers grant replication semantics only with the exact marker and `s3:ReplicateObject` / `s3:ReplicateDelete`; other requests have them removed after signature verification. The pre-authentication CORS lookup reads resident metadata only, so arbitrary path segments no longer cause metadata reads or cache growth.
- **Per-bucket CORS.** `PUT`/`GET`/`DELETE ?cors` are real; a bucket configuration overrides the server-wide policy and converges across site-replication peers.
- **Metadata consistency.** `metadata.lock` serializes every bucket-configuration writer; `ForceCreate` and site adoption keep existing configuration; a locked bucket always carries plain Enabled versioning.
- **AWS-aligned authorization.** Explicit version deletes require `s3:DeleteObjectVersion`; user and group status changes require the action matching the target status; policy writes reject bare ARN prefixes.
- **Checksums.** Server-side part checksums, federated `UploadPartCopy`, `ChecksumType` in `CompleteMultipartUpload`, AWS-aligned completion errors, and rejection of unknown algorithms and of `CRC64NVME` with `COMPOSITE`.
- **SSE-C.** Zero-byte objects and `GetObjectAttributes` authenticate the customer key; null-version and in-place key-rotation copies no longer rewrite objects into unreadable ciphertext.
- **Components.** Go 1.27.0; upstream `minio-go` (the `silo-go` fork is retired); embedded Console `43f8447fd` with the v2.3.0 security fixes; bundled `mcli` 20260901.

## Security fixes {#security}

Recorded in the repository ledger as SN-2026-006 through SN-2026-010: zero-byte SSE-C key authentication, `GetObjectAttributes` SSE-C authentication, replication request trust (completing CVE-2026-34204), user and group status authorization, and `DeleteObjectVersion` authorization. All are inherited from upstream and affect every earlier release. Public advisory posts follow this release.

## Behavior changes and upgrade checks {#upgrade}

Read [Upgrading from RELEASE.2026-08-06](/compatibility/migration/#since-20260806) before upgrading. In short: grant `s3:DeleteObjectVersion` where versions are deleted and deny it where `Deny s3:DeleteObject` was meant to block permanent deletes; split enable and disable admin grants; expect bare ARN prefixes to be rejected on policy writes; give legacy PostgreSQL and MySQL notification targets a connection string; configure bucket CORS only after every replication site runs this release.

## Known issues {#known-issues}

- **Conditional delete.** `DeleteObject` ignores the HTTP `If-Match` header and `DeleteObjects` ignores the `<ETag>` element of each `<Object>` entry ([#10](https://github.com/pgsty/silo/issues/10)); both perform an unconditional delete. A repair exists on a local branch and is not part of this release.
- **Multi-site configuration deletion.** Deleting a bucket policy, SSE, tag, or quota configuration on one site can be restored by a peer that still holds it ([#77](https://github.com/pgsty/silo/issues/77)); only CORS uses the tombstone-aware register. Inherited from upstream.
- **Mixed-version replication groups.** A peer still on 20260806 accepts but ignores bucket CORS and keeps reporting a CORS mismatch. Upgrade every site first.
- **Rollback.** 20260806 ignores bucket CORS and drops it when it rewrites that bucket's metadata.
- **Embedded Console.** The server embeds the last Console commit before the `pgsty/silo-pkg` module-path migration; Console 2.3.0's remaining changes arrive once the server imports that path directly.

## Verification {#verification}

Full `cmd` and `internal` suites, the `cmd` race suite, lint, generated-file and compatibility-baseline guards, `govulncheck`, and `make verify` across six deployment shapes (FS, erasure, distributed erasure, erasure sets, multi-pool, IPv6 multi-pool) pass on the release candidate.

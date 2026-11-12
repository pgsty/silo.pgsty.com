---
title: "SN-2026-024: GetObjectAttributes and Read-Only ZIP Archive Tag-Policy and GetObject Bypass"
linkTitle: "SN-2026-024 · Attributes & ZIP AuthZ"
date: 2026-11-11
author: "Ruohang Feng"
description: "GetObjectAttributes and the S3 ZIP extraction extension (x-minio-extract: true) evaluated IAM policies before reading stored object tags, listed archive members using only s3:ListBucket without s3:GetObject, and wrote generated ZIP indexes back to object metadata during read requests."
tags: [Security, S3, Authorization, Tagging, Archive, SILO]
weight: 1
draft: false
url: "/blog/security/20261111-attributes-and-archive-tag-authz/"
---

**Status:** Shipped in **[SILO 20261112](/blog/release/silo-20261112/)** ([`f746d0707`](https://github.com/pgsty/silo/commit/f746d07076faaf9be1479aadfaf904a4793fa8c0), [`296c9710b`](https://github.com/pgsty/silo/commit/296c9710b16467e53fd4d861bf0b01f35fe6e555))\
**Identifier:** `SN-2026-024` ([Security Advisory Ledger](/about/security-advisories/#sn-2026-024), [#342](https://github.com/pgsty/silo/issues/342))\
**Severity:** High\
**Affected scope:** **SILO Server** (`RELEASE.2026-11-09T00-00-00Z` and earlier) and inherited upstream MinIO releases since `2021-06-10` ([`ba5fb2365`](https://github.com/pgsty/silo/commit/ba5fb2365cc9797fcf4952041e9cfb035b8277f8)) and `2024-01-05` ([`9b8ba97f9`](https://github.com/pgsty/silo/commit/9b8ba97f9fc0a39ea6632443a102bd42f8067da3))\
**Unaffected components:** `silo-console`, `mcli`, `silo-pkg`, and `kes`

Standard `GetObject` and `HeadObject` handlers in SILO authenticate the caller first, read the addressed object version's `ObjectInfo`, and then authorize `s3:GetObject` (or `s3:GetObjectVersion`) against `objInfo.UserTags` so IAM policies conditioned on `s3:ExistingObjectTag/<key>` take effect. Inherited from upstream MinIO, two read surfaces bypassed that post-metadata authorization step: `GetObjectAttributes` (`GET /<bucket>/<key>?attributes`) and the read-only `.zip` archive S3 extension (`x-minio-extract: true` on `GET`, `HEAD`, and `ListObjectsV2`). In addition, `ListObjectsV2` archive member listing enumerated `.zip` contents using only bucket-level `s3:ListBucket` without checking `s3:GetObject` on the archive object itself, and reading an unindexed `.zip` archive persisted generated index metadata back onto the object during read verbs.

## Summary {#summary}

- **What went wrong:**
  1. **`GetObjectAttributes` skipped `s3:ExistingObjectTag` evaluation:** `getObjectAttributesHandler` (`cmd/object-handlers.go`) ran `checkRequestAuthType` (which passes `existingObjectTags = ""`) **before** `objectAPI.GetObjectInfo`, and never re-evaluated `s3:GetObjectAttributes` / `s3:GetObject` (or their `*Version*` counterparts) against `objInfo.UserTags`. Callers blocked by `Deny` on `s3:ExistingObjectTag/*` received `200 OK` with checksums, part counts, and sizes, while callers relying on tag-conditioned `Allow` statements were falsely rejected (`403 AccessDenied`).
  2. **ZIP member `GET` / `HEAD` bypassed `s3:ExistingObjectTag` (`x-minio-extract: true`):** `getObjectInArchiveFileHandler` and `headObjectInArchiveFileHandler` (`cmd/s3-zip-handlers.go`) likewise authorized `s3:GetObject` with empty tags before reading the `.zip` object's metadata, allowing callers explicitly denied access to tagged `.zip` archives (for example, `classification=secret`) to stream plaintext member files out of the archive by sending `GET /bucket/archive.zip/secret.txt` with `x-minio-extract: true`.
  3. **ZIP member `ListObjectsV2` bypassed `s3:GetObject`:** `listObjectsV2InArchive` (`GET /bucket?list-type=2&prefix=archive.zip/` with `x-minio-extract: true`) relied solely on the caller's bucket-level `s3:ListBucket` check in `listObjectsV2Handler`. A principal granted `s3:ListBucket`—even under an explicit `Deny` on `s3:GetObject` for `archive.zip`—could read the `.zip` central directory from storage and enumerate every internal member filename, uncompressed byte size, and timestamp.
  4. **Read-path metadata mutation on unindexed `.zip` objects:** When a `.zip` object had not been uploaded with a prebuilt archive index (`X-Amz-Meta-Snowball-Auto-Extract`), `readObjectZIPInfo` called `PutObjectMetadata` during `GET`, `HEAD`, and `ListObjectsV2` to persist the generated index onto the stored version—mutating object metadata from read-only HTTP verbs without write authorization.
- **Upstream provenance:** The `.zip` extraction S3 extension was introduced in upstream MinIO [`ba5fb2365`](https://github.com/pgsty/silo/commit/ba5fb2365cc9797fcf4952041e9cfb035b8277f8) (`2021-06-10`, [minio/minio#12267](https://github.com/minio/minio/pull/12267)); `GetObjectAttributes` was introduced in [`9b8ba97f9`](https://github.com/pgsty/silo/commit/9b8ba97f9fc0a39ea6632443a102bd42f8067da3) (`2024-01-05`, [minio/minio#18732](https://github.com/minio/minio/pull/18732)).
- **Fix:** Commits [`f746d0707`](https://github.com/pgsty/silo/commit/f746d07076faaf9be1479aadfaf904a4793fa8c0) and [`296c9710b`](https://github.com/pgsty/silo/commit/296c9710b16467e53fd4d861bf0b01f35fe6e555) authenticate upfront, authorize both `GetObjectAttributes` actions and all three `.zip` read paths (`GET`, `HEAD`, `ListObjectsV2`) against the archive/object version's stored `UserTags`, require `s3:GetObject` on the `.zip` object before listing its internal members, and keep read-time `.zip` index construction strictly in memory via `readObjectZIPInfo` (`PutObjectMetadata` runs only on uploads that explicitly request indexing).

---

## 1. Upstream Provenance and Root Cause {#provenance}

### Why Pre-Lookup `checkRequestAuthType` Misses Object Tags {#pre-lookup}

In `cmd/auth-handler.go`, `checkRequestAuthType` combines `authenticateRequest` and `authorizeRequest` (`authorizeRequestWithExistingTags(..., "")`) into a single call suitable for bucket-level or write-new-object handlers where no stored object tags exist yet. Handlers that read an existing object and support `s3:ExistingObjectTag/<key>`—such as `GetObjectHandler` and `HeadObjectHandler`—instead split the two steps:

1. Call `authenticateRequest` to verify the SigV4/presigned signature (or identify an anonymous caller) before touching storage.
2. Read `ObjectInfo` (or attach `opts.CheckPrecondFn`) and call `authorizeRequestWithExistingTags(ctx, r, action, objInfo.UserTags)` against the addressed version's real tags.

Both [`ba5fb2365`](https://github.com/pgsty/silo/commit/ba5fb2365cc9797fcf4952041e9cfb035b8277f8) (`cmd/s3-zip-handlers.go`) and [`9b8ba97f9`](https://github.com/pgsty/silo/commit/9b8ba97f9fc0a39ea6632443a102bd42f8067da3) (`getObjectAttributesHandler` in `cmd/object-handlers.go`) used `checkRequestAuthType` before `GetObjectInfo` and never re-ran policy evaluation once `objInfo.UserTags` was loaded:

- On **`GetObjectAttributes`**, AWS S3 requires the caller to hold **both** `s3:GetObjectAttributes` and `s3:GetObject` (or `s3:GetObjectVersionAttributes` and `s3:GetObjectVersion` when `?versionId=` is supplied), evaluated against the target version's stored tags. Evaluating both actions with `""` skipped any tag-conditioned `Deny` on either action and rejected any tag-conditioned `Allow`.
- On **`.zip` member `GET` and `HEAD` (`x-minio-extract: true`)**, an attacker denied `s3:GetObject` on `arn:aws:s3:::vault/*` whenever `s3:ExistingObjectTag/confidential == "true"` received `403 AccessDenied` on `GET /vault/bundle.zip`, yet received `200 OK` and full member plaintext on `GET /vault/bundle.zip/report.csv` with `x-minio-extract: true`.

### Bucket-List Privilege Boundary vs. Archive Content Inspection {#list-boundary}

`listObjectsV2Handler` (`cmd/bucket-listobjects-handlers.go`) authorizes `s3:ListBucket` on the bucket before branching to `listObjectsV2InArchive` when `r.Header.Get("x-minio-extract") == "true"` and `prefix` contains `.zip/`. Unlike normal prefix listing—which reads only S3 object keys in the bucket namespace—`listObjectsV2InArchive` opens the `.zip` object's payload bytes via `getFilesListFromZIPObject` (`GetObjectNInfo`) to parse its ZIP central directory. Treating internal archive payload parsing as covered by `s3:ListBucket` crossed the S3 data-access boundary: principals granted inventory-only `s3:ListBucket` (even with an explicit `Deny` on `s3:GetObject`) could inspect internal filenames and sizes inside confidential `.zip` objects.

---

## 2. Impact Scope {#impact}

| Endpoint / Feature                                | Security & Functional Impact                                                                                                                                                                    |
| :------------------------------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`GetObjectAttributes` (`?attributes`)**         | Bypasses `Deny` rules conditioned on `s3:ExistingObjectTag/*` (disclosing ETags, checksums, object size, storage class, and multipart layout); falsely denies tag-conditioned `Allow` policies. |
| **ZIP `GET` / `HEAD` (`x-minio-extract: true`)**  | Full plaintext read bypass of `Deny` rules conditioned on `s3:ExistingObjectTag/*` for any file stored inside a `.zip` object; false `403` on tag-conditioned `Allow` policies.                 |
| **ZIP `ListObjectsV2` (`x-minio-extract: true`)** | Principals holding only `s3:ListBucket` can read the internal directory structure and member sizes of any `.zip` object in the bucket, bypassing `Deny s3:GetObject` and tag conditions.        |
| **Unindexed `.zip` archive reads**                | `GET`/`HEAD`/`LIST` previously invoked `PutObjectMetadata` to cache the generated ZIP index on disk, mutating stored metadata during read operations.                                           |
{.wide .expand}

---

## 3. Solution Design: Why It Is Necessary and Sufficient {#fix}

Commits [`f746d0707`](https://github.com/pgsty/silo/commit/f746d07076faaf9be1479aadfaf904a4793fa8c0) and [`296c9710b`](https://github.com/pgsty/silo/commit/296c9710b16467e53fd4d861bf0b01f35fe6e555) align `GetObjectAttributes` and all three `.zip` archive read operations with SILO's post-metadata tag authorization and read-only storage invariants (alongside [`89028732a`](https://github.com/pgsty/silo/commit/89028732ab2dc69d852ca8eb37cbd50fe84d9ce4) / [#294](https://github.com/pgsty/silo/pull/294) preserving `5xx` storage errors on tag-conditioned `GetObject`/`HeadObject` reads):

1. **`GetObjectAttributes` (`cmd/object-handlers.go`):**
   - Selects `[s3:GetObjectAttributes, s3:GetObject]` (or `[s3:GetObjectVersionAttributes, s3:GetObjectVersion]` when `opts.VersionID != ""`), runs `authenticateRequest` upfront, reads `objInfo`, and evaluates **both** required actions against `objInfo.UserTags` via `authorizeRequestWithExistingTags` (or `authorizeRequestWithUnreadTags` when `GetObjectInfo` returns an error).
   - Preserves standard S3 missing-object masking (`AccessDenied` when the caller lacks `s3:ListBucket`, `NoSuchKey`/`NoSuchVersion` when permitted) while surfacing genuine retryable storage errors (`503 SlowDownRead`) to authorized callers instead of misreporting them as `403`.
2. **ZIP `GET`, `HEAD`, and `ListObjectsV2` (`cmd/s3-zip-handlers.go`, `cmd/bucket-listobjects-handlers.go`):**
   - Sets `ReqInfo.ObjectName = zipPath` (the `.zip` object's own key, matching the ARN carrying the tags and permissions) and authenticates upfront on `GET`/`HEAD`.
   - Authorizes `s3:GetObject` against `zipObjInfo.UserTags` both on initial `GetObjectInfo` and inside `opts.CheckPrecondFn` whenever `GetObjectNInfo` opens a byte range of the `.zip` archive—closing any race if tags change between the metadata lookup and ranged payload read.
   - In `listObjectsV2InArchive`, requires `s3:GetObject` on `zipPath` (evaluated with `zipObjInfo.UserTags` and `authorizeRequestWithUnreadTags` on lookup errors), returning `PrefixAccessDenied` (`403 AccessDenied`) when the caller is not permitted to read the `.zip` object.
3. **Side-effect-free `readObjectZIPInfo` (`cmd/s3-zip-handlers.go`):**
   - Separates `readObjectZIPInfo` (pure in-memory central-directory index builder used by `GET`, `HEAD`, and `ListObjectsV2`) from `updateObjectMetadataWithZipInfo` (used exclusively by upload handlers when the uploader explicitly sets `x-minio-extract: true` with write permission).

### Sufficiency and Necessity {#sufficiency}

- **Necessary:** Authorizing only on the initial `GetObjectInfo` in the `.zip` handlers would leave the subsequent `GetObjectNInfo` range read unguarded against concurrent tag updates; re-checking inside `opts.CheckPrecondFn` binds authorization to the exact `ObjectInfo` generation opened for reading. Likewise, separating `readObjectZIPInfo` from `PutObjectMetadata` is required so read-only callers neither mutate `xl.meta` nor fail when reading archives in WORM-protected or read-only environments.
- **Sufficient:** Every S3 entry point that reads `.zip` members (`getObjectInArchiveFileHandler`, `headObjectInArchiveFileHandler`, `listObjectsV2InArchive`) and `getObjectAttributesHandler` now enforces post-lookup `UserTags` evaluation, verified across allow/deny tag matrices, missing keys, and unreadable quorum states in `cmd/object-attributes-archive-tags_test.go` and `cmd/object-attributes-read-error_test.go`.

---

## 4. Trade-Offs, Caveats, and Operational Costs {#tradeoffs}

| Dimension                                          | Engineering Trade-Off                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| :------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Repeated reads of unindexed `.zip` archives**    | Previously, the first `GET`/`HEAD`/`LIST` with `x-minio-extract: true` on an ordinary `.zip` object wrote a compressed directory index back into `xl.meta`. Because read verbs are now strictly side-effect-free, unindexed `.zip` objects rebuild their directory index in memory from the ZIP central directory tail on each read. Workloads that repeatedly extract members from large `.zip` archives can still persist the index at upload time by passing `x-minio-extract: true` on `PutObject` / `CompleteMultipartUpload`. |
| **Archive member listing requires `s3:GetObject`** | Clients or scripts that previously listed inside `prefix=archive.zip/` with `x-minio-extract: true` using a role that held **only** `s3:ListBucket` (without `s3:GetObject` on `archive.zip`) now receive `403 AccessDenied`. Grant `s3:GetObject` on the archive prefix if archive content listing is intended.                                                                                                                                                                                                                    |
{.wide .expand}

---

## Upgrade and Mitigation Guidance {#remediation}

1. **Upgrade SILO Server** to **[SILO 20261112](/blog/release/silo-20261112/)** (`RELEASE.2026-11-12T00-00-00Z`) or later (commits [`f746d0707`](https://github.com/pgsty/silo/commit/f746d07076faaf9be1479aadfaf904a4793fa8c0) and [`296c9710b`](https://github.com/pgsty/silo/commit/296c9710b16467e53fd4d861bf0b01f35fe6e555)).
2. **Temporary mitigation prior to upgrade:** On unpatched deployments that rely on `s3:ExistingObjectTag/*` `Deny` rules to isolate sensitive objects (especially `.zip` archives), block incoming client requests carrying the `x-minio-extract` HTTP header or `?attributes` query parameter at the reverse proxy until the server upgrade is complete.
3. **Review archive-listing IAM roles:** If an internal application intentionally uses `ListObjectsV2` with `x-minio-extract: true` to browse `.zip` contents, ensure its IAM policy includes `s3:GetObject` (and satisfies any tag conditions) on those `.zip` objects in addition to `s3:ListBucket`.

See the [Security Advisory Ledger](/about/security-advisories/#sn-2026-024), [Server Compatibility Notes](/compatibility/server/#candidate-after-20261109), and [SN-2026-022 (Active-Active Tagging Proxy Auth)](/blog/security/20261111-tagging-replication-proxy-auth/).

---
title: "Explicit Version Deletes Now Require DeleteObjectVersion"
linkTitle: "Version Delete Authorization"
date: 2026-09-02T00:00:00+08:00
author: "Ruohang Feng"
description: "SILO now selects DeleteObject or DeleteObjectVersion from each request's effective version ID, while preserving the established least-privilege replication target policy."
tags: [Release, Security, IAM, S3, Compatibility]
weight: 9
draft: false
url: "/blog/release/delete-object-version-authorization/"
---

Starting in [Server 20260903](/blog/release/silo-20260903/) ([pgsty/silo#104](https://github.com/pgsty/silo/pull/104), tracking [issue #58](https://github.com/pgsty/silo/issues/58)), SILO maps object-delete authorization to the operation the request actually performs:

| Request | Required action |
| --- | --- |
| No `versionId` | `s3:DeleteObject` |
| Version UUID | `s3:DeleteObjectVersion` |
| Explicit `versionId=null` | `s3:DeleteObjectVersion` |
| `DeleteObjects` | Applied independently to each XML entry |

Previously, SILO required `s3:DeleteObject` for every delete operation and evaluated `s3:DeleteObjectVersion` only as an explicit-deny check. A principal holding only `DeleteObject` could permanently remove a specific historical version, whereas a least-privilege purge principal holding only `DeleteObjectVersion` was denied.

With this change, a `DeleteObject`-only principal can perform an unversioned delete or create a delete marker, but receives `AccessDenied` when targeting a version UUID or `null` version. A `DeleteObjectVersion`-only principal can permanently remove a named version, but cannot create a delete marker. Explicit denies and `s3:versionid` conditions retain normal policy precedence. Multi-object delete (`DeleteObjects`) evaluates each entry's own `VersionId` so a query-string parameter cannot alter another entry's condition value.

## Replication compatibility {#replication-compatibility}

Bucket and site replication target policies do **not** need to add `s3:DeleteObjectVersion`. Authenticated replication requests establish delete trust through the exact internal replication marker and `s3:ReplicateDelete`, preserving the deployed `s3:DeleteObject + s3:ReplicateDelete` receiver contract. An explicit deny on `s3:DeleteObjectVersion` continues to block replicated version purges.

This separation keeps upgraded replication targets compatible with existing least-privilege policies without granting new standalone delete capabilities to `ReplicateDelete`-only credentials. Two-site regression tests verified that a target user holding the documented minimal policy (without `DeleteObjectVersion`) converges both permanent version deletes and delete markers.

## Upgrade impact {#upgrade-impact}

- Review user, service-account, OPA, and external authorization policies that currently grant only `s3:DeleteObject` for principals that run `mc rm --version-id`, `mc rm --versions`, Console delete-all-versions, or SDK deletes with an explicit `versionId`, and grant `s3:DeleteObjectVersion` where needed.
- External authorization plugins now receive a single `s3:DeleteObjectVersion` check for ordinary named-version deletes instead of the former deny-only check followed by `s3:DeleteObject`.
- `X-Minio-Force-Delete` prefix cleanup remains gated by `s3:DeleteObject`.
- Wire and storage formats are unchanged.

See [Object Deletion](/administration/object-management/object-delete/) for the full permission matrix.

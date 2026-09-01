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

> **Release status:** this change is implemented in
> [pgsty/silo#104](https://github.com/pgsty/silo/pull/104), tracking
> [issue #58](https://github.com/pgsty/silo/issues/58). Publishing this note
> does not by itself mean that a server release, package, image, or deployment
> contains the change.

SILO now maps object-delete authorization to the operation the request will
actually perform:

| Request | Required action |
| --- | --- |
| No `versionId` | `s3:DeleteObject` |
| Version UUID | `s3:DeleteObjectVersion` |
| Explicit `versionId=null` | `s3:DeleteObjectVersion` |
| `DeleteObjects` | The mapping is applied independently to every XML entry |

Previously, SILO required `s3:DeleteObject` for every case and used
`s3:DeleteObjectVersion` only as an explicit-deny check. A principal holding
only `DeleteObject` could therefore permanently remove a named historical
version. Conversely, a least-privilege purge principal holding only
`DeleteObjectVersion` could not perform the operation it was intended for.

After this change, a `DeleteObject`-only principal can still perform an
unversioned delete or create a delete marker, but receives `AccessDenied` for a
named UUID or `null` version. A `DeleteObjectVersion`-only principal can remove
the named version but cannot create a delete marker. Explicit denies and
`s3:versionid` conditions retain normal policy precedence. Multi-delete uses
each entry's `VersionId`; a query-level decoy cannot change another entry's
condition value.

## Replication compatibility {#replication-compatibility}

Bucket and site replication target policies do **not** need to add
`s3:DeleteObjectVersion`. An authenticated request earns replication delete
trust through an exact internal marker and `s3:ReplicateDelete`; the receiver
then preserves the deployed `s3:DeleteObject + s3:ReplicateDelete` contract.
An explicit deny on `s3:DeleteObjectVersion` continues to block a replicated
version purge.

This distinction prevents an upgraded target from silently rejecting permanent
delete replication and also avoids granting new delete capability to a
`ReplicateDelete`-only credential. A real two-site regression used a target
user with the documented minimal policy and no `DeleteObjectVersion`; both a
permanent version delete and a delete marker converged successfully.

## Upgrade impact {#upgrade-impact}

- Review user, service-account, OPA, and external authorization policies that
  currently grant only `s3:DeleteObject` but perform `mc rm --version-id`,
  `mc rm --versions`, Console delete-all-versions, or SDK deletes with
  `versionId`.
- External authorization plugins now see one `s3:DeleteObjectVersion` decision
  for an ordinary named-version delete instead of the former deny-only check
  followed by `s3:DeleteObject`.
- `X-Minio-Force-Delete` prefix cleanup remains gated by `s3:DeleteObject`; it
  is not an explicit-version S3 request.
- There is no wire or storage-format migration. Rolling back restores the old
  authorization mapping but does not alter stored objects or metadata.

See [Object Deletion](/administration/object-management/object-delete/) for the
operator-facing permission matrix.

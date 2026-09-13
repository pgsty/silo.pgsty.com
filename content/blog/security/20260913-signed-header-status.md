---
title: "SN-2026-011: Fix and Release Status"
linkTitle: "SN-2026-011: Fix and Release Status"
date: 2026-09-13
author: "Vonng"
description: "The signed-header fix is on Server main; the latest public Server remains affected."
tags: [Security, silo]
weight: 1
url: "/blog/security/20260913-signed-header-status/"
---

**Status on 2026-09-13:** SN-2026-011 is fixed on Server main, starting with
[`123325430`](https://github.com/pgsty/silo/commit/1233254309b15571f101b2b26d531951ceaeef1e).
The latest published Server, `RELEASE.2026-09-03T13-18-01Z`, and earlier public
Server releases are affected. No new fixed Server release is established by
the pkg v3.14.0 or mcli 20260913 publication.

A holder of a signed PUT request could add an unsigned `x-amz-copy-source`
header and turn the permitted write into a copy of another object readable by
the signing key. A destination that permits anonymous reads can expose those
copied bytes. This affects both presigned and Authorization-header requests;
the holder does not need the signing credentials.

The patch checks the received `x-amz-*` headers against the signed-header set,
with the protocol's explicit exceptions, before dispatching the requested
operation. Follow-up request-signing and checksum regressions are documented in
the [signed-header review](/blog/design/signed-header-coverage/).

Operators must update the **Server** to source containing the fix or a future
release that explicitly includes it. Restrict write-signing credentials to the
required objects and avoid exposing unnecessary read grants or anonymous
readable upload destinations while planning that update. Updating a client or
Console alone does not remove the Server defect.

Reported by Oren Yomtov. The [canonical advisory ledger](https://github.com/pgsty/silo/blob/main/docs/security/advisories.md)
records SN-2026-011 and its source fix; a CVE was requested. Do not substitute
a dependency scan's clean reachability result for this application-level status.
See the [component matrix](/compatibility/versions/) for released versus main
source and the [Server changelog](https://github.com/pgsty/silo/blob/main/CHANGELOG.md)
for the remaining release contents.

---
title: "SN-2026-011: Fix and Release Status"
linkTitle: "SN-2026-011: Fix and Release Status"
date: 2026-09-13
author: "Vonng"
description: "Signed-header verification fix (123325430) for SN-2026-011, shipped in Server 20260916."
tags: [Security, silo]
weight: 1
url: "/blog/security/20260913-signed-header-status/"
---

`SN-2026-011` was fixed on `main` starting with [`123325430`](https://github.com/pgsty/silo/commit/1233254309b15571f101b2b26d531951ceaeef1e) on 2026-09-13 and shipped in [Server 20260916](/blog/release/silo-20260916/). Server `RELEASE.2026-09-03T13-18-01Z` and earlier releases are affected (`silo-pkg v3.14.0` and `mcli 20260913` are client/library releases and do not patch existing Server deployments).

A holder of a signed `PUT` request could append an unsigned `x-amz-copy-source` header and turn the authorized upload into a server-side `CopyObject` of another object readable by the signing key. If the destination permits anonymous reads, the copied object's contents become readable without holding the signing credentials. Both presigned URLs and `Authorization`-header requests were affected.

The fix verifies received `x-amz-*` headers against the request's signed-header set (retaining only explicit protocol exceptions) before dispatching the operation. Follow-up request-signing and checksum coverage is documented in the [signed-header design note](/blog/design/signed-header-coverage/).

## Remediation

Upgrade **SILO Server** to [Server 20260916](/blog/release/silo-20260916/) or later. Until all Server nodes are upgraded, scope write-signing credentials to the minimum required object prefixes and avoid granting broad read permissions to principals that issue presigned uploads into publicly readable buckets.

Reported by Oren Yomtov. See the [security advisory ledger](/about/security-advisories/#sn-2026-011), the [September 16 release hardening summary](/blog/security/20260916-release-hardening/), and the [component version matrix](/compatibility/versions/).

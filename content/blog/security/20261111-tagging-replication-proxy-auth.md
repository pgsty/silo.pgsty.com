---
title: "SN-2026-022: Active-Active Tagging Proxy Authentication and Remote Tag-Policy Bypass"
linkTitle: "SN-2026-022 · Tagging Proxy Auth"
date: 2026-11-11
author: "Ruohang Feng"
description: "Active-active replication proxied S3 DeleteObjectTagging before authenticating the caller and proxied PutObjectTagging, GetObjectTagging, and DeleteObjectTagging without evaluating stored remote replica tags against IAM s3:ExistingObjectTag conditions."
tags: [Security, S3, Replication, Tagging, IAM, SILO]
weight: 1
draft: false
url: "/blog/security/20261111-tagging-replication-proxy-auth/"
---

**Status:** Fixed on `main` ([`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697), [`67a90dfef`](https://github.com/pgsty/silo/commit/67a90dfef458d3e5228e849711118bc162abed30), [`293ab78b4`](https://github.com/pgsty/silo/commit/293ab78b4cc505c3ab8170a4b2b4b29c04ad74f9)); scheduled for the next post-[`20261109`](/blog/release/silo-20261109/) Server release\
**Identifier:** `SN-2026-022` ([Security Advisory Ledger](/about/security-advisories/#sn-2026-022), [#337](https://github.com/pgsty/silo/issues/337))\
**Severity:** Critical\
**Affected scope:** **SILO Server** (`RELEASE.2026-11-09T00-00-00Z` and earlier) and inherited upstream MinIO releases since `2024-01-12` ([`b2b26d9c9`](https://github.com/pgsty/silo/commit/b2b26d9c958a82fbd9f7e0dc70fc2133838576d0))\
**Unaffected components:** `silo-console`, `mcli`, `silo-pkg`, and `kes`

When active-active bucket or site replication is enabled, an S3 object version may temporarily or permanently reside on a remote replication target while absent from the local cluster receiving a client request. To keep tagging operations transparent across peers, `GetObjectTaggingHandler`, `PutObjectTaggingHandler`, and `DeleteObjectTaggingHandler` (`cmd/object-handlers.go`) proxy requests for locally missing objects to active-active replication targets via `proxyTaggingToRepTarget` (`cmd/bucket-replication.go`), signing the outbound request with the server's privileged replication credentials.

Inherited from upstream MinIO, this proxy path contained two distinct security defects: `DeleteObjectTaggingHandler` looked up the local object and proxied to remote targets **before** authenticating or authorizing the caller, and all three tagging handlers proxied locally missing objects without fetching or evaluating the remote replicas' stored tags against IAM `s3:ExistingObjectTag/<key>` conditions.

## Summary {#summary}

- **What went wrong:**
  1. **Unauthenticated remote tag deletion and key-existence oracle:** `DeleteObjectTaggingHandler` executed `getObjectInfo` and `proxyTaggingToRepTarget` ahead of `checkRequestAuthType`. A completely unauthenticated `DELETE /<bucket>/<key>?tagging` request for an object present only on an active-active peer wiped the remote object's tags (`204 No Content`) using the server's internal replication target credentials, and distinguished missing keys (`404 NoSuchKey`) from present local keys (`403 AccessDenied`) on private buckets without `s3:ListBucket`.
  2. **Tag-conditioned policy bypass across replication peers:** When an object was absent locally, `GetObjectTagging`, `PutObjectTagging`, and `DeleteObjectTagging` evaluated IAM policies against an empty tag string (`""`) and forwarded the operation to active-active targets without inspecting the tags actually stored on those replicas—allowing callers blocked by `Deny` rules on `s3:ExistingObjectTag/*` (such as `classification=restricted`) to read, overwrite, or erase remote tags, while falsely rejecting callers whose `Allow` rule required a matching tag.
- **Upstream provenance:** Both defects were introduced in upstream MinIO commit [`b2b26d9c9`](https://github.com/pgsty/silo/commit/b2b26d9c958a82fbd9f7e0dc70fc2133838576d0) (`2024-01-12`, [minio/minio#18649](https://github.com/minio/minio/pull/18649), *"support proxying of tagging requests in replication"*). Every upstream MinIO release after January 2024 and SILO Server `20261109` and earlier are affected.
- **Fix:** Commits [`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697), [`67a90dfef`](https://github.com/pgsty/silo/commit/67a90dfef458d3e5228e849711118bc162abed30), and [`293ab78b4`](https://github.com/pgsty/silo/commit/293ab78b4cc505c3ab8170a4b2b4b29c04ad74f9) authenticate every tagging request upfront, gate remote probing on `authorizeRequestWithUnreadTags` so unauthorized callers cannot trigger cross-site reads, inspect and authorize stored tags on **every selected** present replica before returning or mutating tags, tolerate missing replicas caused by replication lag, and fail closed when any selected target cannot be read.

---

## 1. Upstream Provenance and Root Cause {#provenance}

### Unauthenticated Execution in `DeleteObjectTaggingHandler` {#unauth-delete}

In `PutObjectTaggingHandler` and `GetObjectTaggingHandler`, upstream code called `checkRequestAuthType` (or `authenticateRequest`) before touching storage. In `DeleteObjectTaggingHandler`, however, [`b2b26d9c9`](https://github.com/pgsty/silo/commit/b2b26d9c958a82fbd9f7e0dc70fc2133838576d0) inserted the local lookup and active-active proxy block directly above authentication:

```go
// Inherited upstream order in DeleteObjectTaggingHandler (cmd/object-handlers.go)
oi, err := getObjectInfo(ctx, bucket, object, opts)
if err != nil {
    if (isErrObjectNotFound(err) || isErrVersionNotFound(err)) &&
        proxyTaggingToRepTarget(ctx, w, r, bucket, object, tags, opts) {
        writeSuccessNoContent(w)
        return
    }
    writeErrorResponse(ctx, w, toAPIError(ctx, err), r.URL)
    return
}
// Authentication and authorization ran only if getObjectInfo succeeded locally!
if s3Error := checkRequestAuthType(ctx, r, deleteObjectTaggingAction(...), bucket, object); s3Error != ErrNone {
    ...
}
```

Two consequences followed immediately:

1. **Remote tag erasure without credentials:** Whenever `(bucket, object)` was absent on the receiving cluster (`ObjectNotFound` or `VersionNotFound`) and a matching replication rule selected a proxy-enabled target holding the object, `proxyTaggingToRepTarget` called `clnt.RemoveObjectTagging(ctx, bucket, object, ...)` using the replication target's own admin/replication credentials and returned `204 No Content`—never checking whether the incoming HTTP request was even signed.
2. **Private-bucket key-existence oracle:** Even on non-replicated buckets, an unauthenticated `DELETE /bucket/key?tagging` returned `404 NoSuchKey` when `getObjectInfo` failed with `ObjectNotFound`, versus `403 AccessDenied` once `getObjectInfo` succeeded and reached `checkRequestAuthType`.

### Blind Proxying Across Tag-Conditioned IAM Policies {#blind-proxy}

AWS S3 and SILO support attribute-based access control (ABAC) on object tags via `s3:ExistingObjectTag/<key>`:

- `GetObjectTagging` / `GetObjectVersionTagging`
- `PutObjectTagging` / `PutObjectVersionTagging` (which evaluates **both** `s3:ExistingObjectTag/<key>` on current tags and `s3:RequestObjectTag/<key>` on replacement tags)
- `DeleteObjectTagging` / `DeleteObjectVersionTagging`

When an object exists locally, the handler reads `oi.UserTags` from `xl.meta` and calls `authorizeRequestWithExistingTags(ctx, r, action, oi.UserTags)`. When the object was missing locally, however, `b2b26d9c9` proxied `GET`, `PUT`, and `DELETE` directly to active-active peers without reading remote tags:

- Callers subject to an explicit `Deny` when `s3:ExistingObjectTag/tier == "prod"` bypassed the `Deny` whenever their request landed on a site that had not yet received the object, because `ExistingObjectTag` evaluated as empty locally and the peer executed the proxied request under the replication service account.
- Conversely, callers granted `Allow` **only** when `s3:ExistingObjectTag/team == "analytics"` received a false `403 AccessDenied` whenever their request hit a site missing the local copy.
- In topologies with **two or more active-active replication targets**, tags on Target A and Target B can temporarily diverge while an earlier tag update is still propagating. Authorizing only the first responding target—or letting a mutation proceed on Target A before discovering that Target B carries a `Deny`-triggering tag—would violate atomicity of authorization across replicas.

---

## 2. Impact Scope {#impact}

| Deployment Topology                          | Exposed Surface                                                                                                                                                                                                                                                                 |
| :------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Active-active bucket or site replication** | Anonymous callers can delete remote object tags (`DELETE ?tagging`) for objects absent on the ingress site; authenticated callers can bypass `s3:ExistingObjectTag` `Deny` policies on `GET`/`PUT`/`DELETE ?tagging`, and conditional `Allow` policies falsely fail with `403`. |
| **One-way or asynchronous replication**      | `replicateSync=false` does not itself disable proxying. Matching replication rules and proxy-target state determine selection; one-way or asynchronous mode is not an unaffected boundary.                                                                                      |
| **Standalone / non-replicated buckets**      | Unauthenticated or unauthorized `DELETE ?tagging` leaks whether `(bucket, key)` exists (`404 NoSuchKey` vs `403 AccessDenied`) even when the caller lacks `s3:ListBucket`; local tag authorization on existing objects is unaffected.                                           |
{.wide .expand}

---

## 3. Solution Design: Why It Is Necessary and Sufficient {#fix}

Commits [`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697), [`67a90dfef`](https://github.com/pgsty/silo/commit/67a90dfef458d3e5228e849711118bc162abed30), and [`293ab78b4`](https://github.com/pgsty/silo/commit/293ab78b4cc505c3ab8170a4b2b4b29c04ad74f9) unify `GetObjectTaggingHandler`, `PutObjectTaggingHandler`, and `DeleteObjectTaggingHandler` around a single local-and-remote authorization pipeline:

1. **Unconditional upfront authentication:** All three handlers run `authenticateRequest` before reading local metadata or considering replication targets. Anonymous requests on private buckets stop immediately unless bucket policy grants anonymous access.
2. **Pre-probe gate (`authorizeRequestWithUnreadTags`):** When `getObjectInfo` returns `ObjectNotFound` or `VersionNotFound`, the server does **not** blindly dial remote peers for every authenticated user. Instead, `authorizeTaggingProxy` evaluates whether the caller could *possibly* be allowed under **some** tag assignment (`authorizeRequestWithUnreadTags`). Callers with no matching `Allow` statement (or an unconditional `Deny` independent of tags) are rejected locally without generating cross-site RPC traffic or leaking remote existence; missing-object error masking (`404` vs `403`) honors `s3:ListBucket` consistently across `GET`, `PUT`, and `DELETE`, while transient local storage errors (`503 SlowDownRead`) are preserved for authorized callers rather than collapsed into `AccessDenied`.
3. **Two-phase remote inspection across selected targets (`readTaggingProxyTargets`):**
   - **Phase 1 (Read & Authorize Every Selected Present Replica):** `getProxyTargets` selects matching replication targets. `readTaggingProxyTargets` first skips targets without a client, already marked offline, or disabled for proxying, then calls `GetObjectTagging`. The following error handling applies to the selected targets:
     - If the peer returns `NoSuchKey` or `NoSuchVersion` (for example, because replication to a third site is lagging), that absent replica is skipped rather than aborting the request—unless *zero* peers hold the object, in which case standard `404` / `403` masking applies.
     - If **any** peer fails with a network, authentication, or `5xx` storage error, authorization **fails closed** immediately and aborts before any mutation runs, because that unreadable replica could hold a tag that triggers an explicit `Deny`.
     - For every peer where the object version is present, the server runs `authorizeRequestWithExistingTags(ctx, r, action, targetTags.String())` (including incoming `RequestObjectTag` headers on `PutObjectTagging`). If **any** present replica fails authorization, the entire request is denied (`403 AccessDenied`).
   - **Phase 2 (Mutate Retained Verified Targets):** PUT and DELETE reuse only the client handles authorized in Phase 1. At least one attempted write must succeed; an error is returned when all attempted writes fail. Skipped targets cannot count as successful writes. This is not an atomic transaction across targets.

### Sufficiency and Necessity {#sufficiency}

- **Necessary:** Every component of the two-phase flow closes a distinct failure mode verified by adversarial tests (`cmd/tagging-proxy-authz_test.go`):
  - Without upfront `authenticateRequest`, anonymous callers reach storage and proxy paths.
  - Without `authorizeRequestWithUnreadTags`, any authenticated caller with zero permissions on the bucket could force cross-site `GetObjectTagging` fan-out on arbitrary keys.
  - Authorizing only one peer fails in multi-target topologies when Peer 1 has stale tags and Peer 2 already carries a `Deny` tag; conversely, requiring *all* peers to hold the object breaks active-active availability during normal replication lag.
  - Failing open on an unreadable peer would allow an attacker or transient outage to bypass tag-based `Deny` rules.
- **Sufficient:** All three S3 tagging endpoints (`GET`, `PUT`, `DELETE`) share `readTaggingProxyTargets` (`cmd/bucket-replication.go`), ensuring identical authentication, `ExistingObjectTag` / `RequestObjectTag` evaluation, missing-key masking (`s3:ListBucket`), and multi-target failure semantics.

---

## 4. Trade-Offs, Caveats, and Operational Costs {#tradeoffs}

| Dimension                                            | Engineering Trade-Off                                                                                                                                                                                                                                                                                     |
| :--------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Extra remote `GET` before proxied `PUT`/`DELETE`** | Locally present objects do not need these proxy reads. When an object is absent locally, the proxy reads tags from each selected eligible target before returning or mutating remote tags.                                                                                                                |
| **Fail-closed availability under peer outage**       | A selected target that fails during the tag read aborts the proxy request before mutation. Targets already marked offline or disabled for proxying are skipped during selection; this does not guarantee inspection of every configured peer.                                                             |
| **TOCTOU window across independent sites**           | Active-active S3 replication does not hold distributed cross-site locks across WAN links. Phase 1 authorizes the tags observed immediately prior to Phase 2's remote write; concurrent independent tag writes on two sites continue to reconcile via replication tagging timestamps (`TaggingTimestamp`). |
{.wide .expand}

---

## Upgrade and Mitigation Guidance {#remediation}

1. **Upgrade every SILO Server node across all replicated sites** to the post-`20261109` release containing [`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697), [`67a90dfef`](https://github.com/pgsty/silo/commit/67a90dfef458d3e5228e849711118bc162abed30), and [`293ab78b4`](https://github.com/pgsty/silo/commit/293ab78b4cc505c3ab8170a4b2b4b29c04ad74f9). Because any unpatched peer accepting client S3 traffic can still proxy unauthenticated `DELETE ?tagging` calls using its replication credentials, every site in an active-active mesh must be upgraded.
2. **Temporary mitigation prior to upgrade:** If untrusted network clients can reach S3 endpoints on an active-active cluster before upgrade, block unauthenticated `?tagging` `DELETE` requests at the reverse proxy / load balancer (for example, rejecting `DELETE` requests carrying query parameter `tagging` when the `Authorization` header and `X-Amz-Signature` query parameter are both absent).
3. **Post-upgrade audit:** Deployments relying on object tags for ABAC isolation (`s3:ExistingObjectTag/*`) on active-active replicated buckets should audit recent audit logs for unexpected `DeleteObjectTagging` or `PutObjectTagging` operations and verify tag integrity across peers.

See the [Security Advisory Ledger](/about/security-advisories/#sn-2026-022), [Candidate Server Compatibility Notes](/compatibility/server/#candidate-after-20261109), and [SN-2026-024 (`GetObjectAttributes` & ZIP Tag Authorization)](/blog/security/20261111-attributes-and-archive-tag-authz/).

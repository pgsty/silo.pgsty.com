---
title: "SN-2026-003: s3:versionid Condition Evaluation and Request Condition Hardening"
linkTitle: "SN-2026-003: s3:versionid Conditions"
date: 2026-08-04
author: "[Ruohang Feng](https://vonng.com) ([`@Vonng`](https://github.com/Vonng))"
description: "Why Null conditions on s3:versionid were inverted, how fixing only getConditionValues opened a DeleteObjects XML bypass, and how SN-2026-003 and SN-2026-005 harden IAM policy evaluation."
url: "/blog/security/s3-versionid-conditions/"
tags: ["Security", "IAM", "S3", "Versioning", "Bucket Policy", "SILO"]
---

**`SN-2026-003`** and **`SN-2026-005`** cover a set of S3 IAM policy evaluation fixes shipped in [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) (`80c2c9d03`, `2f55347f7`, `eee05a17c`, and [silo-pkg `v3.12.0`](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.0) commit `2b087a1`; [`pgsty/silo#40`](https://github.com/pgsty/silo/issues/40), [`pgsty/silo#53`](https://github.com/pgsty/silo/issues/53)):
1. **`SN-2026-003` (`80c2c9d03`)**: `getConditionValues` populated `args.ConditionValues["versionid"] = []string{""}` even when a request carried no `versionId`, causing IAM `Null` conditions on `s3:versionid` to evaluate as if the key were always present; fixing that alone would have opened a `DeleteObjects` XML `<VersionId>` bypass without per-entry rebinding in `authorizeRequestWithTags`.
2. **Condition-source isolation (`2f55347f7`)**: Separated query parameters, HTTP headers, internal server keys, and `s3:ExistingObjectTag/<key>` vs. `s3:RequestObjectTag/<key>` so untrusted query strings or headers cannot spoof internal condition keys.
3. **`SN-2026-005` (`2b087a1` / `eee05a17c`)**: Added `ParseConfigStrict` to reject degenerate bare resource prefixes (`"arn:aws:s3:::"` and `"*arn:aws:s3:::"`) when writing IAM and bucket policies.

## Conclusions first {#summary}

1. **Unconditional empty slice inverted `Null` checks**: In `silo-pkg`, `nullFunc.evaluate` tests whether a condition key is absent by checking `len(rvalues) == 0`. Because `getConditionValues` unconditionally assigned `args.ConditionValues["versionid"] = []string{vid}` (producing `[]string{""}` when `vid == ""`), `len(rvalues)` was always `1`—making `Null: {"s3:versionid": "true"}` always `false` and `Null: {"s3:versionid": "false"}` always `true`.
2. **Fixing `getConditionValues` alone breaks `DeleteObjects`**: In multi-object `DeleteObjects` (`POST /?delete`), the target `<VersionId>` is inside each XML `<Object>` element, not in the URL query string. If `getConditionValues` simply omits `"versionid"` when the URL query has no `versionId`, a policy denying versioned deletes (`Deny s3:DeleteObjectVersion` or `Condition: {"Null": {"s3:versionid": "false"}}`) would fail to match `DeleteObjects` XML entries unless `authorizeRequestWithTags` rebinds `ConditionValues["versionid"]` from `ReqInfo.VersionID`.
3. **Whitespace trimming closes a `Deny` bypass**: Version-reading handlers called `strings.TrimSpace(r.URL.Query().Get("versionId"))`, whereas `getConditionValues` did not trim whitespace. A request with `?versionId=V%20` bypassed `Deny StringEquals {"s3:versionid": "V"}` while still deleting or reading version `V`.

---

## Why `Null` on `s3:versionid` Was Inverted {#the-defect}

In `silo-pkg/bucket/policy/condition/nullfunc.go`, the IAM `Null` condition operator checks whether a condition key is missing from the request context:

```go
func (f nullFunc) evaluate(values map[string][]string) bool {
    rvalues, ok := values[http.CanonicalHeaderKey(f.k.Name())]
    if !ok {
        return f.v
    }
    return f.v && len(rvalues) == 0
}
```

However, in `cmd/signature-v4-utils.go`, `getConditionValues` populated `"versionid"` at the end of the function without checking whether `vid` was non-empty:

```go
var vid string
if v := r.Form.Get("versionId"); v != "" {
    vid = v
} else if u, err := url.Parse(r.Header.Get(xhttp.AmzCopySource)); err == nil {
    vid = u.Query().Get("versionId")
}
args["versionid"] = []string{vid}
```

When a caller sent an unversioned request (`DELETE /bucket/key` with no `versionId` query parameter), `vid` was `""`, and `args["versionid"]` became `[]string{""}` (`len == 1`). Consequently:
- A policy allowing only unversioned operations via `"Null": {"s3:versionid": "true"}` evaluated `len(rvalues) == 0` as `false` and **denied** valid unversioned requests.
- A policy restricting version-specific operations via `"Null": {"s3:versionid": "false"}` evaluated `!f.v && len(rvalues) > 0` as `true` and matched even when no `versionId` was supplied.

---

## The Trap: Why Omitting Empty `vid` Alone Opens a `DeleteObjects` Bypass {#the-trap}

The obvious one-line fix—only writing `args["versionid"] = []string{vid}` when `vid != ""`—turned out to hide a dangerous authorization bypass in `DeleteMultipleObjectsHandler` (`POST /{bucket}?delete`).

Unlike single-object `DELETE /{bucket}/{object}?versionId=V`, a multi-object `DeleteObjects` request carries no `versionId` in the URL query string. Instead, the request body contains an XML list of `<Object><Key>...</Key><VersionId>V</VersionId></Object>` entries. Inside `DeleteMultipleObjectsHandler`, the server loops over each XML entry, sets `r.WithContext` (`ReqInfo.VersionID = obj.VersionID`), and calls `authorizeRequestWithTags` for `DeleteObjectAction`.

Consider what happens if an administrator configures a policy that allows normal delete-marker creation (`s3:DeleteObject` when `s3:versionid` is null) or denies permanent version deletion via:

```json
{
  "Effect": "Deny",
  "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"],
  "Resource": ["arn:aws:s3:::mybucket/*"],
  "Condition": {
    "Null": {"s3:versionid": "false"}
  }
}
```

Because `authorizeRequestWithTags` calls `getConditionValues(r, ...)`—which inspects `r.Form.Get("versionId")` on the HTTP request URL rather than `ReqInfo.VersionID`—omitting empty `vid` in `getConditionValues` without propagating `ReqInfo.VersionID` means `args["versionid"]` is absent during every per-object check in `DeleteObjects`. Worse still, an attacker could pass a decoy query parameter on the batch URL (`POST /mybucket?delete&versionId=decoy`) while putting the protected `<VersionId>target-v1</VersionId>` inside the XML body!

---

## The Two-Part Fix (`80c2c9d03`) {#the-fix}

Commit `80c2c9d03` fixes both halves together:

1. **Omit `"versionid"` when `vid == ""` in `getConditionValues`**:
   ```go
   if vid != "" {
       args["versionid"] = []string{vid}
   }
   ```
2. **Rebind `"versionid"` from `ReqInfo.VersionID` for `DeleteObjectAction` in `authorizeRequestWithTags`** (`cmd/auth-handler.go`):
   ```go
   if action == iampolicy.DeleteObjectAction {
       reqInfo := logger.GetReqInfo(ctx)
       if vid := strings.TrimSpace(reqInfo.VersionID); vid != "" {
           conditionValues["versionid"] = []string{vid}
       } else {
           delete(conditionValues, "versionid")
       }
   }
   ```

Why rebind `conditionValues["versionid"]` only when `action == iampolicy.DeleteObjectAction` rather than for every action? Because in `CopyObjectHandler`, `ReqInfo.VersionID` holds the destination query parameter (if any), whereas the `GetObjectAction` authorization check on the copy source must evaluate `s3:versionid` from `x-amz-copy-source` (`?versionId=...` on the source URL). Restricting the `ReqInfo.VersionID` override to `DeleteObjectAction` ensures both single-object `DeleteObjectHandler` and per-entry `DeleteMultipleObjectsHandler` evaluate the exact version being deleted—and explicitly `delete(conditionValues, "versionid")` when `reqInfo.VersionID` is empty so that a URL query decoy (`POST /bucket?delete&versionId=query-level-decoy`) cannot spoof an unversioned XML entry.

---

## Closing the Whitespace Normalization Gap {#trim}

While auditing every caller that reads `versionId`, we noticed that object handlers (`GetObjectHandler`, `HeadObjectHandler`, `DeleteObjectHandler`, `PutObjectRetentionHandler`, etc.) extract the query parameter with:

```go
versionID := strings.TrimSpace(r.URL.Query().Get(xhttp.VersionID))
```

In contrast, `getConditionValues` read `r.Form.Get("versionId")` (and `u.Query().Get("versionId")` from `x-amz-copy-source`) **without** `strings.TrimSpace`.

If a policy denied access to a specific version via `"StringEquals": {"s3:versionid": "v1"}`, a caller requesting `?versionId=v1%20` (with a trailing space) had `"versionid": ["v1 "]` during policy evaluation—evading the `StringEquals` deny rule—after which the handler trimmed `"v1 "` to `"v1"` and operated on the protected version. Applying `strings.TrimSpace` to both query `versionId` and `x-amz-copy-source` `versionId` inside `getConditionValues` closes that mismatch.

---

## Call-Chain Impact and Condition-Source Isolation (`2f55347f7`) {#impact}

| Operation | Source of `s3:versionid` | Pre-`20260804` Behavior | Server `20260804` Behavior |
|---|---|---|---|
| `GetObject` / `DeleteObject` (no `versionId`) | Absent | `["versionid"] = [""]` (`Null:true` fails) | Key omitted (`Null:true` matches) |
| `GetObject` / `DeleteObject` (`?versionId=v1%20`) | URL query `versionId` | Policy sees `"v1 "`, handler uses `"v1"` | Both policy and handler see `"v1"` |
| `CopyObject` (`x-amz-copy-source: /b/k?versionId=v1`) | `x-amz-copy-source` query | Untrimmed `vid` | Trimmed `vid` |
| `DeleteObjects` (`POST /?delete` with `<VersionId>`) | Per-entry `ReqInfo.VersionID` | Ignored XML `<VersionId>`; read URL query | Rebound per XML entry; URL decoy ignored |

In companion commit `2f55347f7` ([`pgsty/silo#53`](https://github.com/pgsty/silo/issues/53)), we also hardened `getConditionValues` across all other request condition keys:
- **Reserved internal keys**: Client query parameters and HTTP headers can no longer overwrite server-derived condition keys (`username`, `userid`, `principaltype`, `authtype`, `signatureversion`, `tlsVersion`, `cipherSuite`).
- **`s3:signatureAge`**: Computed directly from the validated SigV4 timestamp rather than trusting client-supplied values.
- **Tag condition separation**: `s3:ExistingObjectTag/<key>` is populated exclusively from stored object tags, and `s3:RequestObjectTag/<key>` exclusively from `x-amz-tagging` on the incoming request.

---

## SN-2026-005: Bare ARN Prefix Rejection {#sn-2026-005}

During the same IAM condition audit, we investigated **`SN-2026-005`** ([silo-pkg `v3.12.0`](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.0) commit `2b087a1`, wired into [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) in `eee05a17c`): what happens when a policy contains a degenerate resource string with an empty bucket and object suffix, such as `"arn:aws:s3:::"` or `"*arn:aws:s3:::"`?

Because the legacy parser stripped the `arn:aws:s3:::` prefix and accepted an empty resource pattern `""`, that pattern could never match any real bucket or object. In an `Allow` statement, it was merely a dead rule—but in a **`Deny` statement on `Resource`** or an **`Allow` statement using `NotResource`**, a degenerate `arn:aws:s3:::` pattern failed open!

To prevent administrators from saving policies that silently fail open without risking startup failures on existing clusters:
- `silo-pkg v3.12.0` adds `policy.ParseConfigStrict`, which rejects degenerate bare ARN prefixes (`arn:aws:s3:::` and `*arn:aws:s3:::`).
- Server `20260804` (`eee05a17c`) calls `ParseConfigStrict` on all policy **write** paths (bucket policies, named IAM policies, and service-account/STS inline policies), while keeping stored policy load paths on permissive `ParseConfig` so existing deployments never fail to boot.

---

## Why `SN-2026-003` Is Tracked as an Advisory Rather Than a CVE {#not-a-cve}

Exploiting the `s3:versionid` evaluation bugs required an authenticated caller operating against a policy that explicitly used `s3:versionid` conditions (`Null`, `StringEquals`, or `StringNotEquals`). Standard `s3:DeleteObjectVersion` action checks were unaffected unless conditioned on `s3:versionid`. We track the condition evaluation and `DeleteObjects` rebinding fixes under `SN-2026-003` and the bare ARN prefix rejection under `SN-2026-005`.

---

## Scope Boundaries and Related Fixes {#boundary}

1. **Multi-Delete Object Lock governance bypass (`75a6734e4` / `#104`)**: While auditing `DeleteMultipleObjectsHandler`, we noted how per-entry headers and retention checks interact; [Server 20260903](/blog/security/20260903-server-hardening/) (`75a6734e4`, `SN-2026-008`) subsequently tightened `DeleteMultipleObjectsHandler` so `x-amz-bypass-governance-retention` is only evaluated against the specific locked entry rather than across the batch.
2. **Snowball `PutObjectExtract` `minio.versionId` PAX header**: Noted during our `versionId` audit and closed in [Server 20261018](/blog/security/20260926-governance-retention-bypass/) (`SN-2026-016`, `14042b5aa`).
3. **Other condition keys (`username`, `userid`, `signatureversion`, `authType`)**: We intentionally scoped `80c2c9d03` to `s3:versionid` rather than changing empty-slice semantics for identity keys that are always defined on authenticated requests.

---

## Verification {#verification}

Regression tests in `cmd/signature-v4-utils_test.go`, `cmd/auth-handler_test.go`, and `cmd/bucket-policy_test.go` verify:
- `Null: {"s3:versionid": "true"}` and `Null: {"s3:versionid": "false"}` across versioned and unversioned `GetObject`, `DeleteObject`, `CopyObject`, and `DeleteObjects` calls,
- `?versionId=v1%20` whitespace trimming against `Deny StringEquals {"s3:versionid": "v1"}`,
- `POST /bucket?delete&versionId=query-level-decoy` with both versioned and unversioned XML `<Object>` entries,
- Rejection of `arn:aws:s3:::` and `*arn:aws:s3:::` via `ParseConfigStrict`.

## Source References {#source}

- [`80c2c9d03`](https://github.com/pgsty/silo/commit/80c2c9d03) — `s3:versionid` condition omission, whitespace trimming, and `DeleteObjects` per-entry rebinding (`SN-2026-003`)
- [`2f55347f7`](https://github.com/pgsty/silo/commit/2f55347f7) — request condition-source isolation (`#53`)
- [`eee05a17c`](https://github.com/pgsty/silo/commit/eee05a17c) / [`silo-pkg@2b087a1`](https://github.com/pgsty/silo-pkg/commit/2b087a1) — `ParseConfigStrict` bare ARN prefix rejection (`SN-2026-005`)

## Summary {#closing}

Shipped in [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z), `80c2c9d03` and `eee05a17c` (`silo-pkg v3.12.0`) ensure accurate `s3:versionid` condition evaluation across single-object and batch `DeleteObjects` operations while rejecting degenerate bare S3 ARN prefixes on policy writes.

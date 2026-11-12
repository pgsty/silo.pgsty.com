---
title: "SN-2026-023: Authenticated STREAMING-UNSIGNED-PAYLOAD-TRAILER Replay Window and Missing SigV4 Condition Keys"
linkTitle: "SN-2026-023 · Unsigned-Trailer Replay"
date: 2026-11-11
author: "Ruohang Feng"
description: "Header-authenticated STREAMING-UNSIGNED-PAYLOAD-TRAILER uploads skipped the 15-minute X-Amz-Date clock-skew check, leaving captured upload headers replayable indefinitely with arbitrary same-length bodies, and omitted s3:signatureversion and s3:authType during policy evaluation."
tags: [Security, S3, SigV4, Streaming, Authentication, SILO]
weight: 1
draft: false
url: "/blog/security/20261111-streaming-unsigned-trailer-replay/"
---

**Status:** Shipped in **[SILO 20261112](/blog/release/silo-20261112/)** ([`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697), [`296c9710b`](https://github.com/pgsty/silo/commit/296c9710b16467e53fd4d861bf0b01f35fe6e555))\
**Identifier:** `SN-2026-023` ([Security Advisory Ledger](/about/security-advisories/#sn-2026-023), [#338](https://github.com/pgsty/silo/issues/338))\
**Severity:** High\
**Affected scope:** **SILO Server** (`RELEASE.2026-11-09T00-00-00Z` and earlier) and inherited upstream MinIO releases since `2023-05-05` ([`76913a9fd`](https://github.com/pgsty/silo/commit/76913a9fd5c6e5c2dbd4e8c7faf56ed9e9e24091))\
**Unaffected components:** `silo-console`, `mcli`, `silo-pkg`, and `kes`

AWS S3's `STREAMING-UNSIGNED-PAYLOAD-TRAILER` mode signs the initial HTTP request headers using Signature Version 4 (`Authorization: AWS4-HMAC-SHA256 ...`) while transmitting `aws-chunked` body chunks and trailing checksums without per-chunk cryptographic signatures. Because the canonical request binds the literal token `"STREAMING-UNSIGNED-PAYLOAD-TRAILER"` rather than a SHA-256 digest of the payload, bounding the validity window of the signed `X-Amz-Date` header (`globalMaxSkewTime = 15 minutes`) is the sole time bound preventing old captured request headers from being replayed.

Inherited from upstream MinIO, `setAuthMiddleware` (`cmd/auth-handler.go`) enforced `parseAmzDateHeader` and `globalMaxSkewTime` on `authTypeSigned`, `authTypeStreamingSigned`, and `authTypeStreamingSignedTrailer`, **omitting `authTypeStreamingUnsignedTrailer`**. Any captured header block from an authenticated unsigned-trailer upload remained accepted indefinitely—hours, days, or months later, for as long as the access key remained active—and could be paired with **arbitrary replacement payload bytes** of the same `X-Amz-Decoded-Content-Length`. In addition, `getConditionValuesWithTags` (`cmd/bucket-policy.go`) left `s3:signatureversion` and `s3:authType` unpopulated for both trailer streaming modes.

## Summary {#summary}

- **What went wrong:**
  1. **Unbounded replay with arbitrary same-length body substitution:** Neither `setAuthMiddleware` nor `doesSignatureMatch` (`cmd/signature-v4.go`) checked clock skew on `authTypeStreamingUnsignedTrailer`. Once an `Authorization`-authenticated `STREAMING-UNSIGNED-PAYLOAD-TRAILER` header set was logged, proxied, or intercepted, an attacker could replay those exact headers at any future date and stream completely different content of equal decoded length to overwrite the target `(bucket, key)` (or `PutObjectPart` / `PutObjectExtract` target).
  2. **Missing SigV4 policy condition keys on trailer streams:** `getConditionValuesWithTags` populated `s3:signatureversion = "AWS4-HMAC-SHA256"` and `s3:authType = "REST-HEADER"` for legacy `authTypeStreamingSigned`, but left both values empty for `authTypeStreamingSignedTrailer` and authenticated `authTypeStreamingUnsignedTrailer`. An `Allow` requiring those values could reject legitimate trailer uploads, while a `Deny` requiring them could fail to match.
- **Upstream provenance:** Introduced in upstream MinIO commit [`76913a9fd`](https://github.com/pgsty/silo/commit/76913a9fd5c6e5c2dbd4e8c7faf56ed9e9e24091) (`2023-05-05`, [minio/minio#16484](https://github.com/minio/minio/pull/16484), *"Signed trailers for signature v4"*), and left unaddressed when upstream later added signature verification for unsigned-trailer readers in [`8c7097528`](https://github.com/pgsty/silo/commit/8c70975283f9f4ce80f331a25c7475a36279e519) (`2025-04-03`, [minio/minio#21103](https://github.com/minio/minio/pull/21103)).
- **Fix:** Commits [`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697) and [`296c9710b`](https://github.com/pgsty/silo/commit/296c9710b16467e53fd4d861bf0b01f35fe6e555) enforce the 15-minute `X-Amz-Date` skew window in `setAuthMiddleware` whenever `authTypeStreamingUnsignedTrailer` carries an `Authorization` header (keeping anonymous public-bucket streaming uploads intact), verify header signatures and `checkUnsignedHeaders` coverage across streaming seed signatures, and populate the exact AWS S3 `s3:signatureversion` and `s3:authType` condition values for both trailer streaming modes.

---

## 1. Upstream Provenance and Root Cause {#provenance}

### Why `authTypeStreamingUnsignedTrailer` Missed the Skew Gate {#skew-gap}

In SILO and upstream MinIO, Signature Version 4 header validation splits responsibilities between two layers:

1. **`doesSignatureMatch` (`cmd/signature-v4.go`):** Parses `X-Amz-Date` (or `Date`) solely to derive the `YYYYMMDD` signing key scope and verify the HMAC over the canonical request. It assumes the HTTP middleware already enforced `globalMaxSkewTime` (`15 * time.Minute`).
2. **`setAuthMiddleware` (`cmd/auth-handler.go`):** Calls `parseAmzDateHeader(r)` and rejects requests whose timestamp differs from `UTCNow()` by more than `globalMaxSkewTime` with `ErrRequestTimeTooSkewed`.

When upstream added trailer-based streaming modes in [`76913a9fd`](https://github.com/pgsty/silo/commit/76913a9fd5c6e5c2dbd4e8c7faf56ed9e9e24091) (`2023-05-05`), `getRequestAuthType` classified **any** request carrying `X-Amz-Content-Sha256: STREAMING-UNSIGNED-PAYLOAD-TRAILER`—both signed requests with an `Authorization` header and anonymous uploads to public buckets—under a single enum value `authTypeStreamingUnsignedTrailer`. Because anonymous uploads have no `X-Amz-Date` header, upstream added only `authTypeStreamingSignedTrailer` to the skew-check `switch` in `setAuthMiddleware`:

```go
// Inherited upstream switch in setAuthMiddleware (cmd/auth-handler.go)
switch aType {
case authTypeSigned, authTypeStreamingSigned, authTypeStreamingSignedTrailer:
    // authTypeStreamingUnsignedTrailer was omitted!
    amzDate, errCode := parseAmzDateHeader(r)
    if errCode != ErrNone {
        writeErrorResponse(r.Context(), w, errorCodes.ToAPIErr(errCode), r.URL)
        return
    }
    if checkSkewTime(UTCNow(), amzDate) != ErrNone { ... }
}
```

When upstream subsequently patched unsigned-trailer authentication in [`8c7097528`](https://github.com/pgsty/silo/commit/8c70975283f9f4ce80f331a25c7475a36279e519) (`2025-04-03`, and later SILO fixes [`CVE-2026-41145`](/about/security-advisories/#cve-2026-41145) and [`CVE-2026-40344`](/about/security-advisories/#cve-2026-40344)), `newUnsignedV4ChunkedReader` called `reqSignatureV4Verify` -> `doesSignatureMatch`, which verified the header HMAC without checking clock skew. As a result, an `X-Amz-Date` from years in the past (or future) passed authentication cleanly.

Why is an unbounded replay window uniquely severe on `STREAMING-UNSIGNED-PAYLOAD-TRAILER`? For a request whose signed `X-Amz-Content-Sha256` contains the actual payload digest, that digest binds the body bytes. This does not apply to payload modes whose canonical request uses an unsigned-payload token. On `STREAMING-UNSIGNED-PAYLOAD-TRAILER`, only `Host`, `X-Amz-Content-Sha256: STREAMING-UNSIGNED-PAYLOAD-TRAILER`, `X-Amz-Date`, `X-Amz-Decoded-Content-Length`, and `X-Amz-Trailer` are signed—neither the chunk bytes nor the trailing CRC/checksum value is covered by the SigV4 signature. Anyone who obtains a captured header block (from middlebox logs, debug traces, or cleartext HTTP traffic) can compute a fresh valid CRC trailer for **any** replacement payload of matching byte length and overwrite the object at any point in the future.

### Omitted SigV4 Condition Keys in `getConditionValuesWithTags` {#condition-gap}

In `cmd/bucket-policy.go`, `getConditionValuesWithTags` populated `s3:signatureversion` and `s3:authType` via a `switch getRequestAuthType(r)` block written before trailer streaming existed (`authTypeSigned`, `authTypePresigned`, `authTypeStreamingSigned`). Neither `authTypeStreamingSignedTrailer` nor authenticated `authTypeStreamingUnsignedTrailer` was added in [`76913a9fd`](https://github.com/pgsty/silo/commit/76913a9fd5c6e5c2dbd4e8c7faf56ed9e9e24091). Because modern AWS SDKs (Go v2, Java v2, Python `boto3`, JS v3) enable default `CRC32`/`CRC64NVME` trailing checksums on `PutObject` and `UploadPart`, their requests routinely arrive as `authTypeStreamingSignedTrailer` or `authTypeStreamingUnsignedTrailer`—evaluating with empty `s3:signatureversion` and `s3:authType` values.

---

## 2. Impact Scope {#impact}

| Surface / Configuration                                           | Concrete Impact                                                                                                                                                                                                                             |
| :---------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`PutObject`, `PutObjectPart`, `PutObjectExtract`**              | Captured authenticated `STREAMING-UNSIGNED-PAYLOAD-TRAILER` request headers remain replayable forever while the access key is active, allowing arbitrary same-length payload overwrites (unless blocked by Object Lock on the destination). |
| **Policies conditioned on `s3:signatureversion` / `s3:authType`** | Rules requiring `AWS4-HMAC-SHA256` / `REST-HEADER` fail to match trailer uploads when those condition values are empty.                                                                                                                     |
| **Anonymous public-bucket `aws-chunked` uploads**                 | Unaffected before and after the fix (no `Authorization` header is sent).                                                                                                                                                                    |
{.wide .expand}

---

## 3. Solution Design: Why It Is Necessary and Sufficient {#fix}

Commits [`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697) and [`296c9710b`](https://github.com/pgsty/silo/commit/296c9710b16467e53fd4d861bf0b01f35fe6e555) close these gaps at the protocol classification and streaming signature boundaries:

1. **Conditional skew enforcement in `setAuthMiddleware` (`cmd/auth-handler.go`):**
   When `aType == authTypeStreamingUnsignedTrailer` and `r.Header.Get(xhttp.Authorization) != ""`, the middleware applies `parseAmzDateHeader(r)` and the 15-minute skew check before invoking the handler or chunk reader. A missing date returns `400 AccessDenied`, a malformed date returns `400 MalformedDate`, and a timestamp outside the window returns `403 RequestTimeTooSkewed`. Without `Authorization`, the request remains anonymous and must still pass bucket policy authorization in `newUnsignedV4ChunkedReader`.
2. **Complete SigV4 condition population in `getConditionValuesWithTags` (`cmd/bucket-policy.go`):**
   - `authTypeStreamingSignedTrailer`: sets `s3:signatureversion = "AWS4-HMAC-SHA256"` and `s3:authType = "REST-HEADER"`.
   - `authTypeStreamingUnsignedTrailer` when `r.Header.Get(xhttp.Authorization) != ""`: sets `s3:signatureversion = "AWS4-HMAC-SHA256"` and `s3:authType = "REST-HEADER"`.
   - `authTypeStreamingUnsignedTrailer` without `Authorization`: leaves both condition values empty, so an anonymous request cannot match the SigV4 signature version or `REST-HEADER` authentication type.

### Sufficiency and Necessity {#sufficiency}

- **Necessary:** Enforcing `parseAmzDateHeader` unconditionally on all `authTypeStreamingUnsignedTrailer` requests (without checking `Authorization != ""`) would break unauthenticated `aws-chunked` uploads to buckets configured for anonymous public writes (`newUnsignedV4ChunkedReader` explicitly supports anonymous bucket-policy uploads, tested in `cmd/streaming-auth-boundary_test.go`). Conversely, gating on `Authorization != ""` covers **every** credentialed `STREAMING-UNSIGNED-PAYLOAD-TRAILER` upload because presigned query-string authentication with `STREAMING-UNSIGNED-PAYLOAD-TRAILER` is already forbidden (`CVE-2026-41145`).
- **Sufficient:** Enforcing the skew window in `setAuthMiddleware` protects every handler that accepts `authTypeStreamingUnsignedTrailer` (`PutObjectHandler`, `PutObjectPartHandler`, `PutObjectExtractHandler`, and any custom S3 route) from a single entry point before body bytes are read.

---

## 4. Trade-Offs, Caveats, and Operational Costs {#tradeoffs}

| Dimension                                         | Engineering Trade-Off & Residual Boundary                                                                                                                                                                                                                                                                                                                                        |
| :------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Client clock synchronization**                  | Authenticated clients using `STREAMING-UNSIGNED-PAYLOAD-TRAILER` whose system clocks drift by more than 15 minutes from server UTC are now rejected with `RequestTimeTooSkewed`, matching all other SigV4 modes and AWS S3.                                                                                                                                                      |
| **Policies using `s3:authType` allowlists**       | Authenticated signed-trailer and unsigned-trailer requests both use `REST-HEADER`. An allowlist already containing that value needs no trailer-specific additions. Use `s3:x-amz-content-sha256` to distinguish payload modes.                                                                                                                                                   |
| **Inherent 15-minute window over plaintext HTTP** | The unsigned-trailer body has no per-chunk cryptographic signatures, even within the valid time window. Use TLS. To reject this payload mode, add a `Deny` for `s3:PutObject` with `StringEquals` on `s3:x-amz-content-sha256` equal to `STREAMING-UNSIGNED-PAYLOAD-TRAILER`. This condition rejects this specific mode; it does not prohibit every other unsigned-payload mode. |
{.wide .expand}

---

## Upgrade and Policy Hardening Guidance {#remediation}

1. **Upgrade SILO Server** to **[SILO 20261112](/blog/release/silo-20261112/)** (`RELEASE.2026-11-12T00-00-00Z`) or later (commits [`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697) and [`296c9710b`](https://github.com/pgsty/silo/commit/296c9710b16467e53fd4d861bf0b01f35fe6e555)).
2. **Always terminate S3 traffic over TLS** so `Authorization` headers and `STREAMING-UNSIGNED-PAYLOAD-TRAILER` chunk streams cannot be captured or modified in transit, and ensure HTTP reverse proxies or debug loggers redact the `Authorization` header.
3. **Optional policy hardening (disabling unsigned-trailer payloads):** Add an IAM or bucket-policy `Deny` for `s3:PutObject` with `StringEquals: {"s3:x-amz-content-sha256": "STREAMING-UNSIGNED-PAYLOAD-TRAILER"}`. The mode token is a payload condition value; authenticated trailer requests have `s3:authType = "REST-HEADER"`. Verify the intended policy with your upload clients.

See the [Security Advisory Ledger](/about/security-advisories/#sn-2026-023), [`CVE-2026-41145`](/blog/security/cve-2026-41145/), [`CVE-2026-40344`](/blog/security/cve-2026-40344/), and [Signed Header Coverage Design (`SN-2026-011`)](/blog/design/signed-header-coverage/).

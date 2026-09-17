---
title: "Security Advisories"
linkTitle: "Advisories"
description: "The SILO advisory ledger: CVE and SN identifiers, fix commits, affected areas, release boundaries, and dependency security updates."
url: "/about/security-advisories/"
weight: 41
type: docs
icon: fa-solid fa-shield-halved
---

This ledger summarizes fork-specific security fixes and closely related
upgrade-impacting security notes in `pgsty/silo`. It is intentionally narrower
than a changelog and focuses on release-impacting security behavior. Each
advisory with its own investigation also has an article in the
[Security Chronicle](/blog/security/); this page is the stable index of
identifiers, fixes, and release boundaries.

Entries carry a CVE identifier where one exists. Where none does, they carry a
fork-local `SN-<year>-<sequence>` identifier so that a finding without a CVE can
still be referenced stably from release notes, commits and issues. An `SN-`
identifier is **not** a CVE and is not registered in any vulnerability
database; it is deliberately not written in CVE form so that scanners do not
mistake it for one. Upstream `minio/minio` is archived, so for findings in
inherited code there is no upstream maintainer to coordinate a CVE assignment
with. `SN-2026-001` is the streaming-flush regression in
`trackingResponseWriter`, which is a reliability defect rather than a security
one and is tracked in the release notes rather than here.

## Current release boundary {#boundary}

**Verified 2026-09-17.** The latest published Server is
[`RELEASE.2026-09-16T00-00-00Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-16T00-00-00Z).
It includes [SN-2026-011](#sn-2026-011), [SN-2026-012](#sn-2026-012),
[SN-2026-013](#sn-2026-013) and the embedded Console repair for
[SN-2026-014](#sn-2026-014); Server 20260903 lacks these repairs.
The standalone Console fix is in v2.4.1. Upgrade the component serving the
affected interface: updating mcli, pkg or a standalone Console does not patch
an installed Server. See the [component matrix](/compatibility/versions/)
and [complete release notes](/blog/release/silo-20260916/) for identities and upgrade requirements.

## Inherited upstream advisory baseline {#inherited}

The first Silo community release was cut from upstream history that already
contained the following security fix. Upstream and Silo links are both recorded
even when the fork preserves the same commit object and SHA; that identity is
the inheritance evidence, not a claim that Silo independently reimplemented the
patch.

| ID | Upstream remediation | Silo inheritance | Release note |
| :-- | :-- | :-- | :-- |
| [CVE-2025-62506](https://github.com/advisories/GHSA-jjjj-jwhf-8rgr) | [minio/minio#21642](https://github.com/minio/minio/pull/21642), merged as [`c1a49490`](https://github.com/minio/minio/commit/c1a49490c78e9c3ebcad86ba0662319138ace190) | The same commit object is present as [`pgsty/silo@c1a49490`](https://github.com/pgsty/silo/commit/c1a49490c78e9c3ebcad86ba0662319138ace190) | Resets `DenyOnly` while evaluating a restricted session policy so service or STS accounts cannot mint an unrestricted child service account. Upstream first fixed this in [`RELEASE.2025-10-15T17-29-55Z`](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z); every Silo community release, beginning with [`RELEASE.2025-12-03T12-00-00Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2025-12-03T12-00-00Z), contains it. Operators migrating from an older upstream build should upgrade and audit service accounts created by restricted service or STS identities. See the [chronicle article](/blog/security/20251015-cve-2025-62506/). |

## Advisories since `RELEASE.2026-03-21T00-00-00Z` {#advisories}

| ID | Fixed by | Affected area | Chronicle / release note |
| :-- | :-- | :-- | :-- |
| `CVE-2026-33322` | [`d24f449e0`](https://github.com/pgsty/silo/commit/d24f449e0) | OIDC STS (`AssumeRoleWithWebIdentity`, `AssumeRoleWithClientGrants`) | [Chronicle](/blog/security/20260415-cve-2026-33322/) |
| `CVE-2026-33419` | [`3b950f8fa`](https://github.com/pgsty/silo/commit/3b950f8fa) + follow-ups | LDAP STS authentication | [Chronicle](/blog/security/cve-2026-33419/) |
| `CVE-2026-34204` | [`56fa63bfd`](https://github.com/pgsty/silo/commit/56fa63bfd) | Replication metadata handling | [Chronicle](/blog/security/20260415-cve-2026-34204/) |
| `CVE-2026-39414` | [`3252d5b7f`](https://github.com/pgsty/silo/commit/3252d5b7f) | S3 Select oversized record handling | [Chronicle](/blog/security/cve-2026-39414/) |
| [CVE-2026-41145](https://github.com/advisories/GHSA-hv4r-mvr4-25vw) | [`f444b6f37`](https://github.com/pgsty/silo/commit/f444b6f37) | Unsigned-trailer PUT and multipart upload authentication | [Chronicle](/blog/security/20260416-cve-2026-41145/) |
| [CVE-2026-40344](https://github.com/advisories/GHSA-9c4q-hq6p-c237) | [`efb6e5b00`](https://github.com/pgsty/silo/commit/efb6e5b00) | Snowball auto-extract authentication | [Chronicle](/blog/security/20260416-cve-2026-40344/) |
| [CVE-2026-42600](https://github.com/advisories/GHSA-xh8f-g2qw-gcm7) | [`73ac52472`](https://github.com/pgsty/silo/commit/73ac52472) | Internode `ReadMultiple` storage-REST endpoint | [Chronicle](/blog/security/20260612-cve-2026-42600/) |
| [`SN-2026-002`](#sn-2026-002) | [`ca7baa670`](https://github.com/pgsty/silo/commit/ca7baa670) and follow-ups | Internode storage-REST and Grid RPC payloads | [Chronicle](/blog/security/20260802-internode-path-containment/) · [release note](/blog/release/silo-20260804/#sn-2026-002) |
| [`SN-2026-003`](#sn-2026-003) | [silo-pkg v3.11.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.11.0) and [`2f55347f7`](https://github.com/pgsty/silo/commit/2f55347f78352aed8e08866d370c9426c73362cf) | S3/IAM bucket-policy condition values | [release note](/blog/release/silo-20260804/#sn-2026-003) |
| [Not a vulnerability](#source-address-trust) | [`fe6dc4780`](https://github.com/pgsty/silo/commit/fe6dc4780) | Client source address (`aws:SourceIp`, audit `remotehost`, event `Host`) | [Chronicle](/blog/security/20260804-source-address-trust/) |
| [`SN-2026-004`](#sn-2026-004) | [silo-pkg v3.11.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.11.0) and [`97b7d2804`](https://github.com/pgsty/silo/commit/97b7d28040d109061c0a46a4c01bfc7800a97cc1) | IAM policy evaluation of bucket-level actions | [Chronicle](/blog/security/20260804-object-grant-bucket-reach/) · [release note](/blog/release/silo-20260804/#sn-2026-004) |
| [`SN-2026-005`](#sn-2026-005) | [silo-pkg v3.12.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.0) and [`eee05a17c`](https://github.com/pgsty/silo/commit/eee05a17c34a07cebb27220d12697be74c8bd617) | IAM named-policy and service-account policy writes | [release note](/blog/release/pkg-3.12.0/) |
| [`SN-2026-006`](#sn-2026-006) | [`b73581b05`](https://github.com/pgsty/silo/commit/b73581b05), [`c4fd97d0b`](https://github.com/pgsty/silo/commit/c4fd97d0b) ([#82](https://github.com/pgsty/silo/issues/82)) | SSE-C reads of zero-byte objects | [Chronicle](/blog/security/20260903-server-hardening/) |
| [`SN-2026-007`](#sn-2026-007) | [`474cd5801`](https://github.com/pgsty/silo/commit/474cd5801), [`74c97d005`](https://github.com/pgsty/silo/commit/74c97d005), [`21870fa2e`](https://github.com/pgsty/silo/commit/21870fa2e) ([#84](https://github.com/pgsty/silo/issues/84)) | `GetObjectAttributes` on SSE-C objects | [Chronicle](/blog/security/20260903-server-hardening/) |
| [`SN-2026-008`](#sn-2026-008) | [PR #101](https://github.com/pgsty/silo/pull/101) ([`938603458`](https://github.com/pgsty/silo/commit/938603458) through [`04b097fd9`](https://github.com/pgsty/silo/commit/04b097fd9)) | Internal replication request headers | [Chronicle](/blog/security/20260903-server-hardening/) |
| [`SN-2026-009`](#sn-2026-009) | [`58735ee38`](https://github.com/pgsty/silo/commit/58735ee38), [`229fe2b3c`](https://github.com/pgsty/silo/commit/229fe2b3c) ([PR #73](https://github.com/pgsty/silo/pull/73), [#85](https://github.com/pgsty/silo/pull/85)) | Admin `SetUserStatus` / `SetGroupStatus` | [Chronicle](/blog/security/20260903-server-hardening/) |
| [`SN-2026-010`](#sn-2026-010) | [PR #104](https://github.com/pgsty/silo/pull/104) ([`75a6734e4`](https://github.com/pgsty/silo/commit/75a6734e4) through [`d2d47a41f`](https://github.com/pgsty/silo/commit/d2d47a41f), [#58](https://github.com/pgsty/silo/issues/58)) | `DeleteObject`/`DeleteObjects` with explicit `versionId` | [Chronicle](/blog/security/20260903-server-hardening/) |
| [`SN-2026-011`](#sn-2026-011) | [`123325430`](https://github.com/pgsty/silo/commit/1233254309b15571f101b2b26d531951ceaeef1e) | SigV4 signed-header coverage; `x-amz-copy-source` dispatch | [Chronicle](/blog/security/20260913-signed-header-status/) |
| [`SN-2026-012`](#sn-2026-012) | [`c4b5e1cb4`](https://github.com/pgsty/silo/commit/c4b5e1cb4), [#177](https://github.com/pgsty/silo/pull/177) | Header-only presigned payload hash verification | [Chronicle](/blog/security/20260916-release-hardening/#sn-2026-012) |
| [`SN-2026-013`](#sn-2026-013) | [#191](https://github.com/pgsty/silo/pull/191), [#192](https://github.com/pgsty/silo/pull/192) | IAM revocation replay and recovery | [Design](/blog/design/iam-revocations/) · [Chronicle](/blog/security/20260916-release-hardening/#sn-2026-013) |
| [`SN-2026-014`](#sn-2026-014) | [Console #56](https://github.com/pgsty/silo-console/pull/56), [Server #209](https://github.com/pgsty/silo/pull/209) | Anonymous shared-download proxy scope | [Chronicle](/blog/security/20260916-release-hardening/#sn-2026-014) · [Console v2.4.1](/blog/release/console-2.4.1/) |

Upgrade and compatibility notes for each entry follow. Entries whose full
investigation is told in a chronicle article are summarized here; follow the
link for the threat model, rejected alternatives, and verification.

### CVE-2026-33322 — OIDC STS JWT algorithm confusion {#cve-2026-33322}

Remote exploitation: yes. Closes JWT algorithm confusion by removing
HMAC/shared-secret verification and requiring JWKS-backed verifier keys.
**Breaking change:** providers issuing `HS256`, `HS384`, or `HS512` tokens for
these STS flows must switch to JWKS-backed RSA or ECDSA signing before
upgrading. `PS256` and `EdDSA` are not currently supported.

### CVE-2026-33419 — LDAP STS username enumeration {#cve-2026-33419}

Remote exploitation: yes. Prevents username enumeration by unifying
unknown-user and bad-password responses (both now `400 InvalidParameterValue`)
and adds in-memory login throttling. The final June design limits by source IP
only; it removed the shared username bucket because attackers could use it to
lock out a specific account. Limits are per-node and in-memory; the source
address trust policy is configurable separately. See the [LDAP STS
chronicle](/blog/security/cve-2026-33419/) for the successive repairs.

### CVE-2026-34204 — replication metadata injection {#cve-2026-34204}

Remote exploitation: yes. Blocks untrusted `X-Minio-Replication-*` headers
from being smuggled into internal replication metadata and leaving objects
unreadable. Upgrade any server that accepts untrusted `PutObject` or
`CopyObject` requests, which in practice means almost any production server
that accepts writes.

### CVE-2026-39414 — S3 Select oversized records {#cve-2026-39414}

Remote exploitation: yes. Rejects oversized CSV and line-delimited JSON
records with `OverMaxRecordSize` instead of buffering them unchecked. The
April fix initially missed the SIMD JSON path; the June follow-up routes all
JSON Lines through the bounded `json.PReader`, closing that bypass. See the
[S3 Select chronicle](/blog/security/cve-2026-39414/).

### CVE-2026-41145 — unsigned-trailer authentication bypass {#cve-2026-41145}

Remote exploitation: yes. Closes the query-string authentication bypass in
unsigned-trailer streaming requests. Upgrade if clients can reach object write
endpoints using the `STREAMING-UNSIGNED-PAYLOAD-TRAILER` content-sha256 mode
together with query-string SigV4 credentials.

### CVE-2026-40344 — Snowball auto-extract authentication {#cve-2026-40344}

Remote exploitation: yes. Verifies request authentication before tar
extraction in Snowball unsigned-trailer flows. Upgrade if you use
`PutObjectExtract` or Snowball uploads.

### CVE-2026-42600 — internode `ReadMultiple` path traversal {#cve-2026-42600}

Remote exploitation: yes; cluster-root JWT required. Removes the unused
endpoint that allowed path traversal outside configured drive roots. Upgrade
distributed-erasure deployments. Single-node deployments do not register this
route.

### SN-2026-002 — internode payload containment {#sn-2026-002}

Remote exploitation: yes; cluster-root / internode JWT required. Completes
CVE-2026-42600: its fix removed one endpoint that exercised the gap; the gap
itself — request bodies and grid frames never reaching the validity
middleware, and no containment in the storage layer — remained across three
further protocol surfaces. Closes path traversal on both the volume and path
axes (including the peer-S3 bucket RPCs, which bypass the storage-REST wrapper
entirely), an unrecoverable divide-by-zero that killed a node per RPC frame,
metadata that reported truncated shards as intact, and three allocations sized
from caller-declared values. Upgrade distributed-erasure deployments;
single-node deployments register none of these routes. No S3 API behaviour
changes; object keys containing `.` or `..` path segments were already refused
at the S3 boundary.

### SN-2026-003 — policy condition value sources {#sn-2026-003}

Remote exploitation: yes (policy-dependent). Prevents raw request entries
that spell condition-key names from shadowing or synthesizing internal
condition values; confines `s3:signatureAge` to verified SigV4 presigned
requests; separates query-only list fields from header-backed `x-amz-*`
fields; and stops client request tags from impersonating stored existing-object
tags. The compatible query form remains for storage class and upload tagging
on handlers that consume it; an explicitly present header wins, including an
empty header. Use request-tag conditions only on operations that consume tags.
Header-only `x-amz-*` policy keys no longer accept query substitutes. See
[condition value sources and
precedence](/administration/identity-access-management/policy-based-access-control/#condition-value-sources).

### Client source address trust — opt-in hardening, not a vulnerability {#source-address-trust}

Fixed by `fe6dc4780`; no CVE assigned (the default matches upstream, and
upstream's own position is that IP-based restrictions are impractical without
reliable source-IP visibility). Adds an enforceable forwarded-header trust
boundary, `MINIO_API_TRUSTED_PROXIES`. Set to a list of addresses or CIDR
blocks, forwarded headers are believed only from those peers and forwarding
chains are read right-to-left past listed hops — which also stops the
client-supplied left-most entry that an appending proxy leaves in place. Set to
`none`, no forwarded header is believed at all. This is the guarantee
`_MINIO_API_XFF_HEADER=off` never provided. **No behaviour change for any
existing deployment**; the variable is opt-in and inert when unset. If you use
`IpAddress` or `NotIpAddress` conditions, note that they were not enforceable
before this change; the operator contract — including why the allowlist must
name proxies rather than subnets and why multi-node deployments must include
their own node addresses — is in the [chronicle
article](/blog/security/20260804-source-address-trust/) and the
[settings reference](/reference/minio-server/settings/core/#client-source-address-trust).

### SN-2026-004 — object-grant bucket reach {#sn-2026-004}

Remote exploitation: yes (policy-dependent). Withholds twelve sensitive
bucket-level writes from an object-only resource pattern
(`arn:aws:s3:::bucket/*`): `PutBucketPolicy`, `DeleteBucketPolicy`,
`PutBucketObjectLockConfiguration`, `PutBucketVersioning`,
`PutReplicationConfiguration`, `PutBucketLifecycle`, `DeleteBucket`,
`ForceDeleteBucket`, `PutBucketCors`, `DeleteBucketCors`, `PutBucketQOS`,
`PutInventoryConfiguration`. **This is an authorization tightening; read the
[chronicle article](/blog/security/20260804-object-grant-bucket-reach/) before
upgrading if you write your own bucket-scoped policies.** Add the bare bucket
ARN (`arn:aws:s3:::bucket`) alongside the wildcard form in any statement that
legitimately grants one of the twelve. Built-in canned policies are unaffected;
`Deny` statements and `NotResource` exclusions are untouched.
`MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` restores the historical behaviour in full. It is read during package initialization from the process environment; setting it only in `MINIO_CONFIG_ENV_FILE` is too late. See the [setting](/reference/minio-server/settings/core/#envvar.MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH).

### SN-2026-005 — bare ARN prefix rejection {#sn-2026-005}

No direct remote exploit; policy-dependent. Rejects S3, S3 Tables, and KMS ARN
namespace prefixes that name no resource, including their historical
`*arn:...` serialization, in both `Resource` and `NotResource`, when creating
named policies and when creating or updating service-account session policies.
Existing policies keep loading, matching, importing, and replicating with
unchanged runtime behavior, but a policy containing such a prefix cannot be
submitted unchanged; replace it with the intended concrete resource, or use an
explicit wildcard such as `arn:aws:s3:::*` only when all resources are
intended. A "bare ARN prefix" (`arn:aws:s3:::`) is distinct from the valid
"bare bucket ARN" of SN-2026-004 (`arn:aws:s3:::bucket`). IAM import,
site-replication receive paths, stored-policy loading, and STS inline policies
remain on the permissive compatibility path in this release. See the
[pkg v3.12.0 release note](/blog/release/pkg-3.12.0/).

### SN-2026-006 — SSE-C zero-byte reads {#sn-2026-006}

Remote exploitation: yes; requires read access to the object. Zero-byte SSE-C
objects never unsealed the customer-provided key, so a wrong key was accepted
with `200` instead of `403`, and a copy or new version could be created under a
key of the caller's choosing without knowing the current one. Wrong keys now
fail with `403 AccessDenied` as on AWS; correct keys behave as before and no
client change is needed. Inherited from upstream; every earlier release is
affected.

### SN-2026-007 — `GetObjectAttributes` on SSE-C objects {#sn-2026-007}

Remote exploitation: yes; requires read access to the object. Attributes of
SSE-C objects were returned without authenticating the customer key, and a bare
`X-Minio-Source-Replication-Request` header skipped the check entirely. A wrong
key returns `403`, a replication marker without the key returns `400`;
replication peers holding `s3:ReplicateObject` are unaffected. Inherited from
upstream.

### SN-2026-008 — internal replication headers {#sn-2026-008}

Remote exploitation: yes; any authenticated principal that can read or write
the object. Completes CVE-2026-34204: internal headers such as
`X-Minio-Source-Etag`, `X-Minio-Source-Mtime`,
`X-Minio-Source-Replication-Request`, the replication SSE key headers, and
`X-Amz-Bucket-Replication-Status` were still trusted on presence in most
handlers. Replication semantics now require the exact marker value together
with `s3:ReplicateObject` or `s3:ReplicateDelete`; other requests have these
headers removed after signature verification. Site replication service accounts
and bucket-replication targets that already hold the replication permissions
are unaffected. Inherited from upstream.

### SN-2026-009 — user/group status authorization {#sn-2026-009}

Remote exploitation: yes; authenticated admin API. Status changes were
authorized against `admin:EnableUser` / `admin:EnableGroup` regardless of the
requested status, so a principal allowed only to enable could also disable,
and vice versa. Enable and disable now require the action matching the target
status. Policies that grant only one of the pair lose the other operation;
`admin:*` and the built-in `consoleAdmin` policy are unaffected. Inherited from
upstream.

### SN-2026-010 — explicit version delete authorization {#sn-2026-010}

Remote exploitation: yes; authenticated S3 API. Explicit version deletes were
authorized as `s3:DeleteObject` with only a deny check on
`s3:DeleteObjectVersion`, diverging from AWS. Explicit version deletes now
require `s3:DeleteObjectVersion`. **Two policy effects:** principals granted
only `s3:DeleteObject` can no longer delete specific versions, and a policy
that relied on `Deny s3:DeleteObject` to block permanent deletes must also deny
`s3:DeleteObjectVersion`, because `Allow s3:*` now permits explicit version
deletes. Replication targets keep the `s3:ReplicateDelete` contract. Inherited
from upstream.

### SN-2026-011 — unsigned `x-amz-*` operation headers {#sn-2026-011}

A holder of a presigned or ordinary signed PUT can add an unsigned `x-amz-copy-source` without knowing the signing secret. On affected paths this changes a one-object write into `CopyObject` or `UploadPartCopy`, reading source data with the signer's authority. A readable destination can expose the copied bytes. Published Server 20260903 is affected; the original fix is `123325430`, followed by #177.

Ordinary SigV4 and presigned verification now reject unsigned `x-amz-*` headers with `400 AccessDenied`. `X-Amz-Content-Sha256` is the sole explicit header exception: its effective value is separately bound by the canonical request. #177 removed the internal `X-Amz-Signature-Age` header, constant and exemption; signature age comes from the signed date. Conforming ordinary signers keep working; custom clients must sign nonexempt headers before sending them. AWS uses a different HTTP status for this rejection, so this is not byte-for-byte response parity.

The streaming SigV4 seed verifier does not call this same coverage helper. Streaming auth is refused by the copy handler's ordinary authentication dispatch, but the change must not be described as universal header coverage for every streaming PUT path. See the [scope and residual boundary](/blog/design/signed-header-coverage/#scope). Reported by Oren Yomtov; a CVE was requested. Upgrade the Server, restrict signing grants to the required objects and review anonymously readable destinations. A client or standalone Console update does not repair it.

### SN-2026-012 — header-only presigned payload hash {#sn-2026-012}

A valid presigned request can bind a SHA-256 value supplied only through `X-Amz-Content-Sha256`, yet affected generic authenticated handlers did not verify the consumed body against it. A URL holder could change the body while retaining the valid signed request; `PutBucketPolicy` is a reproduced surface. This does not create permission the signer never had, but it defeats the intended signed-body restriction.

`c4b5e1cb4` makes generic body verification use the same effective payload hash as signature verification: query value first, header fallback. Tampering with a checksum-bound body is rejected with `XAmzContentSHA256Mismatch`; explicit `UNSIGNED-PAYLOAD` keeps its protocol meaning. This shipped in Server 20260916 and is absent from Server 20260903. Upgrade before depending on body-bound presigned administration; avoid distributing broad administrative presigned grants. See the [chronicle](/blog/security/20260916-release-hardening/#sn-2026-012).

### SN-2026-013 — durable IAM revocation {#sn-2026-013}

A revoked identity or grant could return when stale site state, delayed notifications or incomplete recovery reintroduced it. The attacker needs a previously valid credential and an affected replay/recovery scenario; this is not unauthenticated identity creation. #191/#192 preserve deletion revisions, parent revocation boundaries and original group-grant times, and reject old child credentials after same-name parent recreation.

The repair shipped in Server 20260916 and is absent from Server 20260903. **Coordinated upgrade is required for every site and every process sharing an IAM backend, including shared backends without site replication.** Back up complete persistent IAM state, not only a live-record export. Keep tombstones, reissue the required child credentials and reconcile revocations missing from older backups before reopening access. Ordinary group-member removal during an outage remains a separate limitation. See the [design](/blog/design/iam-revocations/) and [recovery runbook](/operations/replication/iam-upgrade/).

### SN-2026-014 — anonymous share-download proxy {#sn-2026-014}

The public Console download proxy could fetch non-object paths on its configured S3 origin, exposing endpoints such as public metrics that operators had isolated behind the Console network boundary. An anonymous caller could cross that boundary without a Console session. This is not a claim that the proxy bypassed S3 authentication or could read every private object.

Console #56 limits forwarding to object-content GETs at the configured origin, rejects system paths and query-selected non-download APIs before sending a request, and refuses all redirects. Ordinary public, presigned and versioned downloads remain supported; the existing shared-link format setting is not a global sharing-disable switch. Reported by Jiri Pejchal (@jiri-pejchal).

The standalone repair is published in **Console v2.4.1**. Server 20260916 embeds the repaired Console through #209; Server 20260903 still embeds an older Console. Upgrade the component that actually serves the UI; installing a standalone Console does not replace an embedded bundle. Until the serving Server has been upgraded, restrict access to the exposed Console proxy and review the configured origin's public endpoints. See the [chronicle](/blog/security/20260916-release-hardening/#sn-2026-014).

## Dependency security updates {#dependencies}

Rows list the absorbed fix and the commit or release that first carried it.
Reachability and deployment exposure still need to be judged per release: an
absorbed dependency fix is not a claim that the vulnerability was reachable in
Silo.

| ID / date | Fixed by | Summary |
| :-- | :-- | :-- |
| 2026-03-25 release | [`RELEASE.2026-03-25`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-03-25T00-00-00Z) | OTel SDK, Paho MQTT and `x/crypto` updates absorb `CVE-2026-24051`, `CVE-2025-10543` and `CVE-2025-58181`; shipped together with the LDAP TLS regression fix below. Not every dependency upgrade in that release was a reachable vulnerability. |
| `CVE-2026-34986` | [`68e0ba997`](https://github.com/pgsty/silo/commit/68e0ba997) | Upgrades `go-jose` to `v4.1.4`. |
| `CVE-2026-39883` | `1869bd30b`, `e4fa06394` | Updates OpenTelemetry dependencies. |
| Go 1.26.2 stdlib | [`db4c0fd5e`](https://github.com/pgsty/silo/commit/db4c0fd5e)  | `CVE-2026-32280` and `CVE-2026-32281` (`crypto/x509`), `CVE-2026-32283` (`crypto/tls`); toolchain/stdlib only, no unrelated dependency rolling. |
| Go 1.26.4 refresh | `df627ff89`, `3e61b1d3a` | `CVE-2026-32952` (Azure NTLM), `CVE-2026-41602` (Thrift), plus further NATS/Prometheus security fixes as the dependency-maintenance layer of the 06-18 release. |
| Upstream Go security fixes | [Go 1.26.5](https://go.dev/doc/devel/release#go1.26.5) | Bumps the required toolchain to Go 1.26.5, which includes security fixes to `crypto/tls` and `os`. |
| [GO-2026-6061](https://pkg.go.dev/vuln/GO-2026-6061) / [GHSA-hrxh-6v49-42gf](https://github.com/advisories/GHSA-hrxh-6v49-42gf) | `4dfc27ce3`: gRPC `v1.82.1` with `x/text` `v0.39.0` | gRPC xDS RBAC engine and HTTP/2 transport fixes ([GO-2026-5970](https://pkg.go.dev/vuln/GO-2026-5970) / `CVE-2026-56852`, an infinite loop on invalid input in `x/text`, landed in the same refresh). Existing MVS pins were kept; the security update was not used to roll unrelated dependencies. |
| [GO-2026-5841](https://pkg.go.dev/vuln/GO-2026-5841) | `c1aec0518`: `klauspost/compress` `v1.18.7` | `govulncheck` judged the affected dictionary symbols unreachable, but the known-affected direct dependency was still not carried; updated to the first fixed version. |
| Toolchain and dependency refresh | [Go 1.27.1](https://go.dev/doc/devel/release#go1.27.1) via [`43f4bb7ed`](https://github.com/pgsty/silo/commit/43f4bb7ed), [`edc8be6ed`](https://github.com/pgsty/silo/commit/edc8be6ed), [`4d6e1ea8e`](https://github.com/pgsty/silo/commit/4d6e1ea8e) | Moves the toolchain to Go 1.27 (1.27.1 as of the release) and refreshes the dependency stack (etcd client v3.7.1, `jwx` v3.0.13, `klauspost/compress` v1.19.2). The pre-release cleanup then returns to upstream `minio-go` (v7.3.1 pre-release) and retires the `silo-go` fork; `govulncheck` reports no reachable vulnerability on the release candidate. |
| [GO-2026-6354](https://pkg.go.dev/vuln/GO-2026-6354) / [GO-2026-6355](https://pkg.go.dev/vuln/GO-2026-6355) | `golang.org/x/crypto` `v0.56.0` ([`edf36bcbf`](https://github.com/pgsty/silo/commit/edf36bcbf)) | Updates `x/crypto/ssh` to the first fixed version for denial of service on deadlocked undecided and established channels. Reachable through the SFTP server (`startSFTPServer` → `sftp.Server.Listen` → `ssh.NewServerConn`); every earlier release that enables SFTP is affected. |
| [CVE-2026-84304](https://github.com/advisories/GHSA-vp52-pcj8-j9qc) | gRPC `v1.83.1` | Updates gRPC-Go to the first fixed version for unauthenticated heap exhaustion through highly fragmented HTTP/2 DATA frames. Silo pulls gRPC transitively rather than registering a gRPC server itself, but selects the fixed version for the complete module graph. |
| [GO-2026-5970](https://pkg.go.dev/vuln/GO-2026-5970) / `CVE-2026-56852` | `x/text` `v0.39.0` | Updates `x/text` to the first fixed version for an infinite loop on invalid input. |
| [CVE-2026-79921 / GHSA-6c5v-hqjr-5xxp](https://github.com/advisories/GHSA-6c5v-hqjr-5xxp) | `d63c92e39`: `amqp091-go` v1.14.0 (upstream first fixed v1.13.0) | A malicious AMQP broker can send oversized frames and exhaust client memory. Relevant when an AMQP notification target is configured; this is not an unauthenticated S3 request path. The update shipped in Server 20260916 and is absent from Server 20260903. |

## Operationally significant security-related fixes {#operational}

| Change | Fixed by | Summary |
| :-- | :-- | :-- |
| Replicated Object Lock updates ignored their timestamps | [`f4c1286c9`](https://github.com/pgsty/silo/commit/f4c1286c9), included in [Server 20260903](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z) | A replicated `CopyObject` rebuilt the metadata from the request before comparing replication timestamps, so the stored retention and legal-hold timestamps were never seen: any replica update was applied regardless of order, and the legal-hold timestamp was written under the retention key. A stale replica could therefore turn a newer legal hold off or shorten a newer retention. The stored state is now captured first, a replica update is applied only when its timestamp is newer, a stale one leaves the stored state in place, and each timestamp is kept under its own key. Inherited from upstream; builds preceding the fix are affected. |
| LDAP TLS regression | [`ce1c537eb`](https://github.com/pgsty/silo/commit/ce1c537eb1dd6c4efa1cf75cf5df0e2c489c947a), released in `RELEASE.2026-03-25` | Restores TLS configuration propagation for `ldaps://` `DialURL()` connections so `MINIO_IDENTITY_LDAP_TLS_SKIP_VERIFY` and custom root CAs work again. |
| Signed-field and policy-input alignment | [#177](https://github.com/pgsty/silo/pull/177), `87d8b5967` | Rejects ambiguous repeated copy-source values, derives signature age from signed input and aligns the effective payload-hash policy value. Distinct from the original header-coverage fix; shipped in Server 20260916, absent from Server 20260903. |
| Cross-pool conditional PUT | [#207](https://github.com/pgsty/silo/pull/207), `5e7d60308` | Evaluates write conditions against the current logical object under the shared pool lock; a stale pool copy must not authorize an overwrite. Shipped in Server 20260916, absent from Server 20260903; see [multi-pool consistency](/blog/design/multi-pool-object-consistency/). |

## Attribution of this ledger {#attribution}

This page is maintained from the ledger previously carried in the repository at
`docs/security/advisories.md`, updated through verified main `f99ed829b5eba`
(2026-09-16). Release status statements are calibrated against the
[component matrix](/compatibility/versions/); each fix's investigation, review,
and verification detail lives in the linked chronicle article or release note.

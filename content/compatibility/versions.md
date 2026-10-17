---
title: "Component Versions"
linkTitle: "Component Versions"
description: "Published SILO components, mcli 20261018, and pending Server release status."
url: "/compatibility/versions/"
weight: 5
type: docs
page_width: wide
icon: fa-solid fa-code-branch
---

> [!WARNING]
> **旧版分片列举设计已被覆盖 · Earlier multipart-listing designs superseded (2026-10-17)**
>
> **English:** The earlier #79 listing-mode and preflight/drain enablement design retained here is superseded by the [latest design decision (English)](https://silo.pgsty.com/blog/design/list-multipart-uploads/#decision-20261017). Dated instructions still describe their named releases. Unified persistent listing is merged into main but remains unreleased; existing binaries do not gain it from a documentation update. This notice concerns multipart listing only and does not replace other compatibility or IAM upgrade requirements.
>
> **中文：** 本页保留的 #79 分片列举旧模式及预检、排空启用建议，已被[最新设计决策（中文）](https://silo.pgsty.com/zh/blog/design/list-multipart-uploads/#decision-20261017)覆盖，请参考新版设计。旧说明仍适用于其明确标注的已发布版本；统一持久列举已合入主干、尚未发布，不能据此认定现有二进制已改变。本提示只针对分片列举，不替代其他兼容性或 IAM 升级要求。

**Public release state verified on 2026-10-17.** SILO releases its four components independently.
A merged dependency update does not change an existing binary or image.

## Published components {#published}

| Component | Latest published version | What it contains |
| --- | --- | --- |
| Server | [20260916](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-16T00-00-00Z) | Go 1.27.1; pkg v3.14.1; upstream SDK `32e1f32cb176`; mcli 20260916; embedded Console v2.4.1, source `1360e26d976d` |
| <span style="white-space:nowrap">Standalone<br>Console</span> | [v2.4.1](https://github.com/pgsty/silo-console/releases/tag/v2.4.1) | pkg v3.14.1; mcli 20260916; upstream SDK `32e1f32cb176`; restricted shared downloads, streaming ZIPs and signed artifacts |
| mcli | [20261018](https://github.com/pgsty/mc/releases/tag/RELEASE.2026-10-18T00-00-00Z) | Go 1.27.2; pkg v3.14.2; upstream SDK v7.4.1; package version `20261018000000.0.0`; public Docker amd64/arm64 images |
| Shared pkg | [v3.14.2](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.2) | Own module path `github.com/pgsty/silo-pkg/v3`; SDK v7.4.1; go-jose v4.1.6; LDAP v3.4.15; Go 1.26 library floor |

Release notes: [Server 20260916](/blog/release/silo-20260916/),
[Console v2.4.1](/blog/release/console-2.4.1/),
[mcli 20261018](/blog/release/mcli-20261018/), [pkg v3.14.2](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.2).
For embedded deployments, select Console and MC explicitly in the Server build.
Package-repository mirrors may lag GitHub; the [download page](/download/)
links directly to the published artifacts.

**Standalone Console image:** anonymous token requests for `docker.io/pgsty/silo-console` returned HTTP 401 on 2026-09-17; public pulls are not confirmed. v2.4.1 GitHub binaries, packages and source are published. This limitation does not affect Server embedding.

## Pending Server releases {#october-release}

Server **20261015 remains a Draft**. Earlier website statements that it was a public release are superseded. Its [Object Lock repairs and artifact checks](/blog/release/silo-20261015/) describe candidate acceptance; the fixes are absent from the current public Server 20260916. See the [security advisory](/blog/security/20260926-governance-retention-bypass/).

Server **20261018 has a signed [source tag](https://github.com/pgsty/silo/tree/RELEASE.2026-10-18T00-00-00Z) and a verified Draft**, with pkg v3.14.2, upstream SDK v7.4.1, mcli 20261018 and the Console v2.4.2 source tag. Console v2.4.2 standalone publication is still pending; the table above lists published components. Public Server release, image promotion and production deployment remain separate steps. Publishing mcli or Console does not repair an existing Server installation.

## September 16 dependency graph {#source}

[Console v2.4.1](/blog/release/console-2.4.1/) selects the released pkg and MC
sources below. These identities are verified through the public Go proxy and
checksum database.

- **Console:** `v0.0.0-20260916075814-1360e26d976d` →
  [`1360e26d976d`](https://github.com/pgsty/silo-console/commit/1360e26d976d82eda395b0b2e449df8c9d49f39c), tag `v2.4.1`.
- **pkg:** `v3.14.1` → `fa657ef431ae22e720df37e5144cf00f67102945`.
- **MC:** `v0.0.0-20260916070421-e952aa78f10a` →
  [`e952aa78f10a`](https://github.com/pgsty/mc/commit/e952aa78f10a2b77dd525a2b7e3143bcda0cd377), tag `RELEASE.2026-09-16T00-00-00Z`.
- **Upstream minio-go:** `v7.3.1-0.20260915093545-32e1f32cb176`.
- **JWX / strfmt / React Router:** v3.3.0 / v0.27.2 / v7.18.4.

Console's embedded frontend is rebuilt from this graph. Its Go dependency uses
the canonical pseudo-version because the historical module path has no `/v2`
suffix. Server embedders must copy both Console and MC replacements; see the
[Console integration notes](/compatibility/console/#source).

Review the [password-permission migration](/compatibility/password-permissions/)
before upgrading: `admin:ChangeMyPassword` and `admin:CreateUser` now express
separate operations. The [Server changelog](https://github.com/pgsty/silo/blob/main/CHANGELOG.md)
and source links below describe the storage, IAM and HTTP changes needed for
coordinated Server upgrades.

### Storage, IAM and HTTP repairs {#september-reliability}

The following changes shipped in Server 20260916 and are absent from Server
20260903. Use the linked PRs and source records to check each repair's scope.

| <span style="display:inline-block;min-width:10rem">Area</span> | <span style="white-space:nowrap">Merged PRs</span> | Operator-visible behavior |
| --- | --- | --- |
| Multi-pool storage | [#188](https://github.com/pgsty/silo/pull/188)<br>[#189](https://github.com/pgsty/silo/pull/189) | Ordinary single-object version DELETE reconciles copies across pools; reconciliation preserves tag state. The opt-in GET-frequency pool-tiering feature was removed. |
| Conditional multipart completion | [#190](https://github.com/pgsty/silo/pull/190) | Preconditions use the logical current object across all pools, preventing an older pool copy from accepting a stale ETag or rejecting the current one. |
| Multipart discovery and cancellation | [#198](https://github.com/pgsty/silo/pull/198) | Discover persistent uploads across pools and sets, continue after native marker uploads disappear, and require majority cancellation confirmations. Strict mode requires a coordinated writer upgrade and legacy drain; see the [upgrade contract](/blog/design/list-multipart-uploads/#implementation-20260916). |
| Ordinary conditional PUT | [#207](https://github.com/pgsty/silo/pull/207) | Public write conditions use the logical current object across all pools, including draining pools. Readability and destination-version changes are detailed [below](#conditional-put). |
| IAM revocations | [#191](https://github.com/pgsty/silo/pull/191)<br>[#192](https://github.com/pgsty/silo/pull/192) | Peer deletion notifications reload committed state. Durable deletion versions and retained revocation boundaries prevent stale site replay from restoring revoked identities or their older grants. |
| Replicated tags and delete markers | [#193](https://github.com/pgsty/silo/pull/193)<br>[#196](https://github.com/pgsty/silo/pull/196) | SSE-KMS copies preserve tag revision times; tag deletion advances its revision and resists delayed events. Delete-marker purges retain their identity and retry state through MRF recovery. |
| Delete-marker purges | [`eb4f5e5b3`](https://github.com/pgsty/silo/commit/eb4f5e5b3)<br>[`254b19ac0`](https://github.com/pgsty/silo/commit/254b19ac0)<br>[`358ab38fb`](https://github.com/pgsty/silo/commit/358ab38fb) | An exact-version purge never creates the marker on drives that lack it, a retried purge of a missing version needs a write-quorum majority of absent drives, healed markers keep their replication and purge metadata, and a queued marker creation is re-checked against the source under the replication lock before it is sent. Remaining gaps are listed [below](#pending) and in [#217](https://github.com/pgsty/silo/issues/217); see the [third round of the replication record](/blog/design/replication-reliability/#third-round). |
| Listing under drive disagreement | [`8d06424b1`](https://github.com/pgsty/silo/commit/8d06424b1) | A null object version that has listing quorum is kept when a newer minority of drives would otherwise hide it. Rolling restarts with concurrent overwrites can still omit readable keys from a successful LIST; see [below](#pending), [#218](https://github.com/pgsty/silo/issues/218) and the [design record](/blog/design/list-null-version-quorum/). |
| Pool migration tags | [`fced86303`](https://github.com/pgsty/silo/commit/fced86303) | Rebalance and decommission carry object tags and their revision fields to the destination pool for ordinary and multipart writes. Tags lost by earlier migrations are not recovered; see [multi-pool object consistency](/blog/design/multi-pool-object-consistency/#migration-tags). |
| Replica metadata | [#194](https://github.com/pgsty/silo/pull/194) | Restoring replication metadata no longer reintroduces the transport-only `aws-chunked` encoding into stored object metadata. |
| Request-header timeout | [#196](https://github.com/pgsty/silo/pull/196) | `--read-header-timeout` / `MINIO_READ_HEADER_TIMEOUT` reaches the HTTP server and imposes an absolute HTTP/1 header-reading deadline, even while bytes keep arriving. HTTP/1 bodies retain the existing rolling idle timeout. |

**Upgrade and compatibility requirements:**

- **IAM requires a coordinated upgrade of all participating servers.** Mixed
  old/new nodes sharing an IAM backend and rolling downgrade are unsupported.
  Back up complete IAM storage and required encryption material; a live admin
  export omits deletion history. Older credentials for a recreated parent may
  need reissuance. Pre-upgrade deletions whose history is already lost cannot be
  reconstructed automatically. Follow the [IAM upgrade and rollback guide](/operations/replication/iam-upgrade/).
- **Unavailable pools can now fail writes and deletes more consistently.**
  Conditional multipart completion fails if any pool's metadata is unreadable,
  even when GET/HEAD can use another pool. Ordinary version DELETE also fails
  on unreadable pools or cleanup errors; insufficient read quorum returns
  `503 SlowDownRead`. Retry after recovery. Successful deletion does not promise
  immediate removal from every drive while outbound delete replication is pending.
- **Access-frequency pool tiering was never in Server 20260903.** Only builds
  containing the experimental feature need its
  [configuration/XML migration](/compatibility/access-tiering-removal/).
  Ordinary lifecycle expiration, remote-tier transitions, rebalance and
  decommission remain available.
- Purge audit status is normalized from `COMPLETE` to `COMPLETED`. Malformed
  historical tag revisions can fail and retry; this repair does not reconstruct
  their history. A shorter header timeout also constrains TLS handshake reads;
  this is not a new total-duration limit for HTTP/1 uploads or downloads.
- Objects with recorded tag revisions take **one extra metadata COPY per
  object** during explicit resync or heal; when the destination is KMS-encrypted
  by bucket default, that copy rewrites the object data. Replication rules with
  tag filters still evaluate target eligibility against the post-deletion
  (empty) tagging state, and arbitrary site clock skew remains outside the
  repaired ordering guarantees. Both endpoints of a replication pair must run
  the repaired build for tombstones to be honored; an old peer still drops
  empty-value revisions. See [Replicated Tag Ordering](/blog/design/replicated-tag-ordering/).

The [R4–R8 integration record](https://github.com/pgsty/silo/blob/40220bd836cbd066ca424fa4dc5dbb90057fb55a/docs/investigations/r4-r8-integration/README.md)
contains source hashes, local tests and remaining acceptance limits. PR #196's
11 checks passed before merge. Those results establish source acceptance, not
a new release or production cluster rollout.

### Console shared downloads {#console-sharing}

[Console #56](https://github.com/pgsty/silo-console/pull/56) and
[Server #209](https://github.com/pgsty/silo/pull/209) resolve the anonymous proxy
boundary reported in [Console #52](https://github.com/pgsty/silo-console/issues/52).
The proxy only accepts object-content GETs at the configured S3 origin and
rejects redirects, system paths and query-selected non-download operations.
No sharing-disable environment variable was added. Normal public, presigned and
versioned downloads remain supported; see the [behavior and design tradeoffs](/reference/minio-server/settings/console/#object-sharing).

The fix is released in [Console v2.4.1](/blog/release/console-2.4.1/).
The exact release source passed the complete CI matrix, vulnerability checks
and release workflow. Real API and browser sharing tests passed in standalone
and embedded deployments; the downloaded standalone binary also passed the
sharing regression against a SILO fixture.

### Ordinary conditional PUT {#conditional-put}

The separate cross-pool conditional PUT defect in
[#199](https://github.com/pgsty/silo/issues/199) was reproduced on published
Server 20260903. [PR #207](https://github.com/pgsty/silo/pull/207) was merged as
[`9b4ae82a29cc`](https://github.com/pgsty/silo/commit/9b4ae82a29cc2290fb5be7b551ec3d8cf7acdd99)
after its head `4620be394b52` passed all eight CI checks on 2026-09-16.
**The repair shipped in Server 20260916.** Its behavior is:

- Ordinary multi-pool `If-Match` / `If-None-Match` conditions use the logical
  current object across all pools. Unreadable metadata can prevent acceptance
  even when GET still works from another pool; read-quorum failures return 503.
  Restore readability or heal before retrying.
- When a destination `versionId` is supplied, the public condition still
  compares the current object. The requested destination version is preserved;
  internal replication keeps its addressed-version checks. Unconditional PUT
  and single-pool conditions retain their existing behavior.
- A successful conditional overwrite does not retire stale copies in other
  pools, and upgrading cannot recover historical accepted overwrites. Existing
  modification-time/pool ordering remains in use; this adds no global clock
  ordering guarantee.

The multipart-completion fix in #190 neither introduced nor repaired this PUT
defect. Final packaged-candidate and rollout acceptance remain tracked in
[#203](https://github.com/pgsty/silo/issues/203).

### Work still pending {#pending}

- **Upgrade and historical-state readiness:** [#200](https://github.com/pgsty/silo/issues/200)
  tracks the [IAM upgrade/restore rehearsal](/operations/replication/iam-upgrade/);
  [#201](https://github.com/pgsty/silo/issues/201) tracks [historical replica inventory and repair validation](/operations/replication/replica-metadata-audit/).
  Source repairs do not automatically repair old state.
- **Release delivery:** [#202](https://github.com/pgsty/silo/issues/202)
  collects release notes and component identities; [#203](https://github.com/pgsty/silo/issues/203)
  separately validates final artifacts and multi-process behavior. Release-artifact acceptance and production rollout remain separate.
- **Multi-site delete-marker convergence:** the source-side re-check in
  `254b19ac0` does not cover creations already in flight or replayed from
  another site, and minority marker copies left by a crash after a
  majority-acknowledged purge have no proven persistent cleanup owner.
  [#217](https://github.com/pgsty/silo/issues/217) tracks the receiver-side
  design. The three-site evidence for the purge repairs came from a combined
  build, not from the final main; see the
  [design record](/blog/design/replication-reliability/#third-round-limits).
- **Listing during rolling restarts:** [#239](https://github.com/pgsty/silo/pull/239)
  carries the follow-up to [#218](https://github.com/pgsty/silo/issues/218): confirm
  eligible unresolved latest-object entries, distinguish deletion from read
  failure and preserve terminal errors through pagination. It adds no disk
  format, client parameter or migration switch. The [current design and
  acceptance limits](/blog/design/listing-recovery-lock-cost/) supersede the
  earlier investigation guidance. Until running a release that contains this
  repair, retain the warning against destination-deleting synchronization
  during rolling restarts. Source integration does not update installed binaries.
- **Pool migration tags:** `fced86303` has unit and race coverage; the
  post-repair eight-node rebalance/decommission acceptance was not completed.
  Tags dropped by earlier migrations must be audited, not assumed.
- **Multipart listing:** [#79](https://github.com/pgsty/silo/issues/79) remains
  open for capacity/release acceptance and the known delayed-creation-write
  boundary. PR #198 repairs durable discovery, global pagination and static
  cancellation confirmation; it does not add a creation fence or certify
  large-scale scanning. The temporary 10,000-upload trial missed the provisional
  five-second page target; see the [design record](/blog/design/list-multipart-uploads/#implementation-20260916).

## Dependency and release order {#order}

1. Verify the upstream SDK commit and required fixes. Keep the upstream
   `github.com/minio/minio-go/v7` path; the retired `silo-go` fork is not part of
   the maintained graph.
2. Validate and publish pkg under `github.com/pgsty/silo-pkg/v3`, including its
   migration notes. Resolve the tag through the Go proxy and checksum database.
3. Update MC to that pkg and SDK, validate it, then publish the calendar-tagged
   mcli release. Go consumers select its canonical pseudo-version.
4. Update Console's direct pkg requirement and explicit MC replacement, validate
   its embedded frontend and integration, and publish Console when a release is
   intended. An accepted immutable source commit can also be selected explicitly.
5. Update Server's direct pkg/SDK requirements and both PGSTY replacements,
   client archive hashes, image and Helm client pins. Validate the complete graph
   before a separate Server release, image publication and cluster rollout.

Go does not inherit a dependency module's `replace` directives. Server must
explicitly select both maintained Console and MC even when Console already
selects MC. Console and MC retain their historical MinIO module paths; pkg uses
its own path directly. Legacy transitive `minio/pkg/v3` from `colorjson`/`dperf`
is separate from the maintained policy implementation.

The Server 20261015 candidate uses Go **1.27.2**; the September stack used Go **1.27.1**.
pkg retains a Go **1.26** library floor and
was also race-tested with Go **1.26.8**. The Go x/* dependencies were refreshed.
The effective go-systemd version stays **v22.6.0** because v22.7.0 fails to compile
on NetBSD; Console's tablewriter **v0.0.5** replacement preserves its MC API.
These are documented compatibility pins, not missed automatic upgrades.

Other dependencies change for concrete CVE/bug fixes, not just newer major
versions. The September 13 Go scans found no reachable or imported vulnerable
package, but retained module-only **GO-2026-5932** in unused OpenPGP code. A clean
reachability result is not a claim that every selected module is advisory-free.

The supported integration target is the coordinated PGSTY stack. Compatibility
with unmodified upstream MinIO/MC and other S3 implementations is best effort.

## September 16 Server source review {#source-review}

Server 20260916 source [`2a4d51406b7e`](https://github.com/pgsty/silo/commit/2a4d51406b7ed87af5fe6fe0f801f3290f96eb3c) selects pkg v3.14.1, upstream minio-go `32e1f32cb176`, Console v2.4.1 source `1360e26d976d`, and MC `e952aa78f10a` (mcli 20260916). The published Server tag is `RELEASE.2026-09-16T00-00-00Z`, package version `20260916000000.0.0`.

- #213 retains **legacy as the multipart default**. Strict requires `MINIO_API_MULTIPART_LISTING` in the process environment and restart, with no shared dynamic key. Majority cancellation confirmation is strict-only. See [settings](/reference/minio-server/settings/core/#multipart-listing) and the [upgrade contract](/blog/design/list-multipart-uploads/#implementation-20260916).
- [Multi-pool consistency](/blog/design/multi-pool-object-consistency/), [conditional DELETE](/blog/design/conditional-delete/) and [Object Lock replication ordering](/blog/design/object-lock-replication-ordering/) distinguish logical current objects, addressed versions and persistence locks.
- [Federated CopyObject](/blog/design/federated-copy-object/) and [SSE-C replica integrity](/blog/design/ssec-replica-integrity/) describe logical-byte checksums, encryption and historical-object limits.
- [Durable IAM revocation](/blog/design/iam-revocations/) and [bucket configuration convergence](/blog/design/bucket-metadata-convergence/) document coordinated upgrades, deletion history and the default-off `MINIO_SITE_REPLICATION_METADATA_TOMBSTONES` switch.
- [Request-header timeouts](/blog/design/request-header-timeouts/) and [Go 1.27 TLS/OIDC](/blog/design/go127-tls-oidc-discovery/) explain their separate scopes.
- The [September security chronicle](/blog/security/20260916-release-hardening/) records SN-2026-012/013/014 and their distinct component delivery boundaries.

These later Server repairs are not in 20260903; original Object Lock fixes and other released prerequisites retain their explicitly identified earlier release boundaries.

Final storage repairs also include migration tag preservation in [`fced86303`](https://github.com/pgsty/silo/commit/fced8630365fd57d6116c595b65252bcd12e13be), null-version quorum in [`8d06424b1`](https://github.com/pgsty/silo/commit/8d06424b126b4ac640cd076a4585b66f2ec753a6), and exact-version purge, marker metadata and queued-creation fixes in `eb4f5e5b3` / `254b19ac0` / `358ab38fb`. Late creation/crash residue in [#217](https://github.com/pgsty/silo/issues/217) and restart-time listing omissions in [#218](https://github.com/pgsty/silo/issues/218) remain known limitations.

## October 15 source acceptance {#october-source}

**Included in the Server 20261015 draft; not shipped in the public Server 20260916.**
[PR #233](https://github.com/pgsty/silo/pull/233), merged as
[`d94b3b3c9251`](https://github.com/pgsty/silo/commit/d94b3b3c9251af5a9dbdb2d178e892c4de75204a),
clears absent fields when reusing legacy `xl.meta` headers and keeps scanner
updates separate from final caches. Storage formats, RPC fields and dependency
versions are unchanged. The [problem and repair record](/blog/design/stale-metadata-reuse/)
documents deterministic regression coverage, a two-process scanner check,
post-merge CI, and operator verification. The source repair is included in
[Server 20261015](/blog/release/silo-20261015/); draft artifact acceptance does not establish a public release or production rollout.

## Server fixes after 20261015 {#post-20261015}

The following fixes target the next Server release. They are not included in
`RELEASE.2026-10-15T00-00-00Z`; merging source does not update installed binaries
or container images.

- [PR #232](https://github.com/pgsty/silo/pull/232) distinguishes missing staged
  `xl.meta` at the final write commit from an incomplete client upload or a
  missing object. PUT and multipart completion report HTTP 503 `SlowDownWrite`
  for this commit failure. The storage RPC and healing paths preserve that
  classification. Client retries remain subject to SDK policy; the fix does
  not recover missing staging data or guarantee a successful retry.
- [PR #236](https://github.com/pgsty/silo/pull/236) parses the native multipart
  directory timestamp before trying the existing Base64 compatibility path.
  This avoids unnecessary local `xl.meta` reads, including plaintext UUIDs
  that also decode as Base64. Legacy or unrecognized directory names still
  fall back to metadata. Storage formats, S3 upload IDs and cleanup settings
  are unchanged: the default expiry is 24 hours and the default scan interval
  is 6 hours.
- [PR #243](https://github.com/pgsty/silo/pull/243), merged on October 17, makes
  persistent multipart listing the only public path and retires the migration
  switch. Confirmed readable historical uploads lacking both identity fields
  are omitted individually; invalid metadata and incomplete scan coverage
  remain errors. Default Abort availability is retained. Repeated scan cost,
  capacity limits and delayed creation after cancellation remain explicit
  boundaries; see the [decision record](/blog/design/list-multipart-uploads/#decision-20261017).

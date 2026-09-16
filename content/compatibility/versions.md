---
title: "Component Versions"
linkTitle: "Component Versions"
description: "Published SILO releases, source fixes verified on September 16, and coordinated upgrade requirements."
url: "/compatibility/versions/"
weight: 5
type: docs
page_width: wide
icon: fa-solid fa-code-branch
---

**Verified on 2026-09-16.** SILO releases its four components independently.
A merged dependency update does not change an existing binary or image.

## Published components {#published}

| Component | Latest published version | What it contains |
| --- | --- | --- |
| Server | <a href="https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z" style="white-space:nowrap">20260903</a> | pkg v3.13.2; upstream SDK `0e78d3f18efe`; mcli 20260903; embedded Console source `464a59d73ada` with v2.3.0 version identity |
| <span style="white-space:nowrap">Standalone<br>Console</span> | [v2.4.1](https://github.com/pgsty/silo-console/releases/tag/v2.4.1) | pkg v3.14.1; mcli 20260916; upstream SDK `32e1f32cb176`; restricted shared downloads, streaming ZIPs and signed artifacts |
| mcli | <a href="https://github.com/pgsty/mc/releases/tag/RELEASE.2026-09-16T00-00-00Z" style="white-space:nowrap">20260916</a> | pkg v3.14.1; upstream SDK `32e1f32cb176`; package version `20260916000000.0.0` |
| Shared pkg | [v3.14.1](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.1) | Own module path `github.com/pgsty/silo-pkg/v3`; CopyObject embedded-error handling; JWX v3.3.0 field-name escaping; upstream SDK `32e1f32cb176` |

Release notes: [Server 20260903](/blog/release/silo-20260903/),
[Console v2.4.1](/blog/release/console-2.4.1/),
[mcli 20260916](/blog/release/mcli-20260916/), [pkg v3.14.1](/blog/release/pkg-3.14.1/).
For embedded deployments, select Console and MC explicitly in the Server build.
Package-repository mirrors may lag GitHub; the [download page](/download/)
links directly to the published artifacts.

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

The following changes have merged into Server main. They remain absent from
the published Server 20260903; use the linked PRs and source records to identify
a build containing them.

| <span style="display:inline-block;min-width:10rem">Area</span> | <span style="white-space:nowrap">Merged PRs</span> | Operator-visible behavior |
| --- | --- | --- |
| Multi-pool storage | [#188](https://github.com/pgsty/silo/pull/188)<br>[#189](https://github.com/pgsty/silo/pull/189) | Ordinary single-object version DELETE reconciles copies across pools; reconciliation preserves tag state. The opt-in GET-frequency pool-tiering feature was removed. |
| Conditional multipart completion | [#190](https://github.com/pgsty/silo/pull/190) | Preconditions use the logical current object across all pools, preventing an older pool copy from accepting a stale ETag or rejecting the current one. |
| Multipart discovery and cancellation | [#198](https://github.com/pgsty/silo/pull/198) | Discover persistent uploads across pools and sets, continue after native marker uploads disappear, and require majority cancellation confirmations. Strict mode requires a coordinated writer upgrade and legacy drain; see the [upgrade contract](/blog/design/list-multipart-uploads/#implementation). |
| Ordinary conditional PUT | [#207](https://github.com/pgsty/silo/pull/207) | Public write conditions use the logical current object across all pools, including draining pools. Readability and destination-version changes are detailed [below](#conditional-put). |
| IAM revocations | [#191](https://github.com/pgsty/silo/pull/191)<br>[#192](https://github.com/pgsty/silo/pull/192) | Peer deletion notifications reload committed state. Durable deletion versions and retained revocation boundaries prevent stale site replay from restoring revoked identities or their older grants. |
| Replicated tags and delete markers | [#193](https://github.com/pgsty/silo/pull/193)<br>[#196](https://github.com/pgsty/silo/pull/196) | SSE-KMS copies preserve tag revision times; tag deletion advances its revision and resists delayed events. Delete-marker purges retain their identity and retry state through MRF recovery. |
| Delete-marker purges | [`eb4f5e5b3`](https://github.com/pgsty/silo/commit/eb4f5e5b3)<br>[`254b19ac0`](https://github.com/pgsty/silo/commit/254b19ac0)<br>[`358ab38fb`](https://github.com/pgsty/silo/commit/358ab38fb) | An exact-version purge never creates the marker on drives that lack it, a retried purge of a missing version needs a write-quorum majority of absent drives, healed markers keep their replication and purge metadata, and a queued marker creation is re-checked against the source under the replication lock before it is sent. Remaining gaps are listed [below](#pending) and in [#217](https://github.com/pgsty/silo/issues/217); see the [third round of the replication record](/blog/design/replication-reliability/#third-round). |
| Listing under drive disagreement | [`8d06424b1`](https://github.com/pgsty/silo/commit/8d06424b1) | A null object version that has listing quorum is kept when a newer minority of drives sorts first. Rolling restarts with concurrent overwrites can still omit readable keys from a successful LIST; see [below](#pending), [#218](https://github.com/pgsty/silo/issues/218) and the [design record](/blog/design/list-null-version-quorum/). |
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
**The repair is on main and remains unreleased.** Its behavior is:

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
  separately validates final artifacts and multi-process behavior. No new Server
  release is established by these tracking issues.
- **Multi-site delete-marker convergence:** the source-side re-check in
  `254b19ac0` does not cover creations already in flight or replayed from
  another site, and minority marker copies left by a crash after a
  majority-acknowledged purge have no proven persistent cleanup owner.
  [#217](https://github.com/pgsty/silo/issues/217) tracks the receiver-side
  design. The three-site evidence for the purge repairs came from a combined
  build, not from the final main; see the
  [design record](/blog/design/replication-reliability/#third-round-limits).
- **Listing during rolling restarts:** with `8d06424b1` included, a four-node
  rolling restart under concurrent overwrites returned 2,624 of 27,966
  successful LISTs with one to four readable keys missing; steady state
  returned 0 of 20,000. The internal cause is not bound;
  [#218](https://github.com/pgsty/silo/issues/218) tracks the diagnostic
  capture and contract decision. Do not run destination-deleting sync tools
  against listings taken during a rolling restart; see the
  [design record](/blog/design/list-null-version-quorum/#boundary).
- **Pool migration tags:** `fced86303` has unit and race coverage; the
  post-repair eight-node rebalance/decommission acceptance was not completed.
  Tags dropped by earlier migrations must be audited, not assumed.
- **Multipart listing:** [#79](https://github.com/pgsty/silo/issues/79) remains
  open for capacity/release acceptance and the known delayed-creation-write
  boundary. PR #198 repairs durable discovery, global pagination and static
  cancellation confirmation; it does not add a creation fence or certify
  large-scale scanning. The temporary 10,000-upload trial missed the provisional
  five-second page target; see the [design record](/blog/design/list-multipart-uploads/#implementation).

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

The main stack uses Go **1.27.1**; pkg retains a Go **1.26** library floor and
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

Pinned baseline `f99ed829b5eb` selects pkg v3.14.0, upstream minio-go `60bd07042d49`, Console source `56dfe455ac2f` and bundled mcli 20260913. This differs from standalone Console 2.4.1. Recheck the final Server tag before release; publishing another component does not update an existing Server.

- #213 retains **legacy as the multipart default**. Strict requires `MINIO_API_MULTIPART_LISTING` in the process environment and restart, with no shared dynamic key. Majority cancellation confirmation is strict-only. See [settings](/reference/minio-server/settings/core/#multipart-listing) and the [upgrade contract](/blog/design/list-multipart-uploads/#implementation).
- [Multi-pool consistency](/blog/design/multi-pool-object-consistency/), [conditional DELETE](/blog/design/conditional-delete/) and [Object Lock replication ordering](/blog/design/object-lock-replication-ordering/) distinguish logical current objects, addressed versions and persistence locks.
- [Federated CopyObject](/blog/design/federated-copy-object/) and [SSE-C replica integrity](/blog/design/ssec-replica-integrity/) describe logical-byte checksums, encryption and historical-object limits.
- [Durable IAM revocation](/blog/design/iam-revocations/) and [bucket configuration convergence](/blog/design/bucket-metadata-convergence/) document coordinated upgrades, deletion history and the default-off `MINIO_SITE_REPLICATION_METADATA_TOMBSTONES` switch.
- [Request-header timeouts](/blog/design/request-header-timeouts/) and [Go 1.27 TLS/OIDC](/blog/design/go127-tls-oidc-discovery/) explain their separate scopes.
- The [September security chronicle](/blog/security/20260916-release-hardening/) records SN-2026-012/013/014 and their distinct component delivery boundaries.

These later Server repairs are not in 20260903; original Object Lock fixes and other released prerequisites retain their explicitly identified earlier release boundaries.

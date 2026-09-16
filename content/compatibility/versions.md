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
| <span style="white-space:nowrap">Standalone<br>Console</span> | [v2.4.0](https://github.com/pgsty/silo-console/releases/tag/v2.4.0) | pkg v3.13.3; MC source `c8aa5d25a63a`; upstream SDK `0e78d3f18efe`; bounded object-browser pages |
| mcli | <a href="https://github.com/pgsty/mc/releases/tag/RELEASE.2026-09-16T00-00-00Z" style="white-space:nowrap">20260916</a> | pkg v3.14.1; upstream SDK `32e1f32cb176`; package version `20260916000000.0.0` |
| Shared pkg | [v3.14.1](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.1) | Own module path `github.com/pgsty/silo-pkg/v3`; CopyObject embedded-error handling; JWX v3.3.0 field-name escaping; upstream SDK `32e1f32cb176` |

Release notes: [Server 20260903](/blog/release/silo-20260903/),
[Console v2.4.0](/blog/release/console-2.4.0/),
[mcli 20260916](/blog/release/mcli-20260916/), [pkg v3.14.1](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.1).
The published Server image still bundles its original client and Console.
Installing a standalone update does not replace those embedded components.
Package-repository mirrors may lag GitHub; the [download page](/download/)
links directly to the published artifacts.

## Coordinated source on main {#source}

**September 16 client/library release:** mcli 20260916 is [`e952aa78f10a`](https://github.com/pgsty/mc/commit/e952aa78f10a2b77dd525a2b7e3143bcda0cd377), Go pseudo-version `v0.0.0-20260916070421-e952aa78f10a`; pkg v3.14.1 is `fa657ef431ae22e720df37e5144cf00f67102945`. Both select SDK `v7.3.1-0.20260915093545-32e1f32cb176` and JWX v3.3.0. The verified Server/Console integration sources below still select their earlier dependency graph; publishing the client does not advance those pins.

The September 13 refresh landed as [pkg #7](https://github.com/pgsty/silo-pkg/pull/7),
[MC #42](https://github.com/pgsty/mc/pull/42),
[Console #53](https://github.com/pgsty/silo-console/pull/53) and [#54](https://github.com/pgsty/silo-console/pull/54),
and [Server #181](https://github.com/pgsty/silo/pull/181).

- **pkg selected by Server/Console:** `v3.14.0` → `827f8109ff11bf6239a35d8d6d137cb5738539c3`.
- **MC selected by Server/Console:** `v0.0.0-20260913012246-4f609a4da3bb` → the published 20260913 tag.
- **Console selected by Server:** `v0.0.0-20260916034812-56dfe455ac2f`; accepted on main by merge [`60aa9492779a`](https://github.com/pgsty/silo-console/commit/60aa9492779a67d2f5131a892dea7aa0da5e133c) with the same tree.
- **Server Console integration:** [`2fabd436c0b1`](https://github.com/pgsty/silo/commit/2fabd436c0b18b6f31536889af27a376e718483c), merged through [#209](https://github.com/pgsty/silo/pull/209). The other September 13 component pins remain unchanged.
- **Verified Server main:** [`3c26a8b0b5bd`](https://github.com/pgsty/silo/commit/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca), including the repairs below.
- **Upstream minio-go:** `v7.3.1-0.20260910142817-60bd07042d49`.

**Server and Console changes after their latest tags remain unreleased.** This
includes the [password-permission split](/compatibility/password-permissions/),
Console streaming ZIP downloads and its revised image-promotion gate, and
Server's later storage, replication and signed-header fixes. Server main now
builds curl 8.22.0 and bundles mcli 20260913; existing Server images retain their
published contents. The [Server changelog](https://github.com/pgsty/silo/blob/main/CHANGELOG.md)
and [Console changelog](https://github.com/pgsty/silo-console/blob/main/CHANGELOG.md)
separate those changes from published releases.

The latest published Server is affected by [SN-2026-011](/blog/security/20260913-signed-header-status/).
Its fix is on main; upgrading only pkg, mcli or standalone Console does not patch
an installed Server. Source validation and vulnerability scans do not establish
that a fixed Server binary has been published.

### Storage, IAM and HTTP repairs {#september-reliability}

The following changes have merged into Server main. They remain absent from
the published Server 20260903; use the linked PRs and source records to identify
a build containing them.

| <span style="display:inline-block;min-width:10rem">Area</span> | <span style="white-space:nowrap">Merged PRs</span> | Operator-visible behavior |
| --- | --- | --- |
| Multi-pool storage | [#188](https://github.com/pgsty/silo/pull/188)<br>[#189](https://github.com/pgsty/silo/pull/189) | Ordinary single-object version DELETE reconciles copies across pools; reconciliation preserves tag state. The opt-in GET-frequency pool-tiering feature was removed. |
| Conditional multipart completion | [#190](https://github.com/pgsty/silo/pull/190) | Preconditions use the logical current object across all pools, preventing an older pool copy from accepting a stale ETag or rejecting the current one. |
| Multipart discovery and cancellation | [#198](https://github.com/pgsty/silo/pull/198) | Discover persistent uploads across pools and sets, continue after native marker uploads disappear, and require majority cancellation confirmations. Strict mode requires a coordinated writer upgrade and legacy drain; see the [upgrade contract](/blog/design/list-multipart-uploads/#implementation). |
| IAM revocations | [#191](https://github.com/pgsty/silo/pull/191)<br>[#192](https://github.com/pgsty/silo/pull/192) | Peer deletion notifications reload committed state. Durable deletion versions and retained revocation boundaries prevent stale site replay from restoring revoked identities or their older grants. |
| Replicated tags and delete markers | [#193](https://github.com/pgsty/silo/pull/193)<br>[#196](https://github.com/pgsty/silo/pull/196) | SSE-KMS copies preserve tag revision times; tag deletion advances its revision and resists delayed events. Delete-marker purges retain their identity and retry state through MRF recovery. |
| Replica metadata | [#194](https://github.com/pgsty/silo/pull/194) | Restoring replication metadata no longer reintroduces the transport-only `aws-chunked` encoding into stored object metadata. |
| Request-header timeout | [#196](https://github.com/pgsty/silo/pull/196) | `--read-header-timeout` / `MINIO_READ_HEADER_TIMEOUT` reaches the HTTP server and imposes an absolute HTTP/1 header-reading deadline, even while bytes keep arriving. HTTP/1 bodies retain the existing rolling idle timeout. |

**Upgrade and compatibility requirements:**

- **IAM requires a coordinated upgrade of all participating servers.** Mixed
  old/new nodes sharing an IAM backend and rolling downgrade are unsupported.
  Back up complete IAM storage and required encryption material; a live admin
  export omits deletion history. Older credentials for a recreated parent may
  need reissuance. Pre-upgrade deletions whose history is already lost cannot be
  reconstructed automatically. Follow the [IAM upgrade and rollback guide](https://github.com/pgsty/silo/blob/40220bd836cbd066ca424fa4dc5dbb90057fb55a/docs/site-replication/iam-revocations.md#protocol-and-supported-upgrade).
- **Unavailable pools can now fail writes and deletes more consistently.**
  Conditional multipart completion fails if any pool's metadata is unreadable,
  even when GET/HEAD can use another pool. Ordinary version DELETE also fails
  on unreadable pools or cleanup errors; insufficient read quorum returns
  `503 SlowDownRead`. Retry after recovery. Successful deletion does not promise
  immediate removal from every drive while outbound delete replication is pending.
- **Access-frequency pool tiering was never in Server 20260903.** Only builds
  containing the experimental feature need its [configuration/XML migration](https://github.com/pgsty/silo/blob/40220bd836cbd066ca424fa4dc5dbb90057fb55a/docs/bucket/lifecycle/access-tiering-removal.md).
  Ordinary lifecycle expiration, remote-tier transitions, rebalance and
  decommission remain available.
- Purge audit status is normalized from `COMPLETE` to `COMPLETED`. Malformed
  historical tag revisions can fail and retry; this repair does not reconstruct
  their history. A shorter header timeout also constrains TLS handshake reads;
  this is not a new total-duration limit for HTTP/1 uploads or downloads.

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

The final Console CI matrix and vulnerability checks passed before merge.
Server's formal module selection passed real API and browser sharing tests in
both standalone and embedded deployments, as well as its CI checks. These are
source acceptance results: Console v2.4.0 and Server 20260903 do not contain this
fix, and no new binary or image is published by merging either PR.

### Work still pending {#pending}

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

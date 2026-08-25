---
title: "Silo Console 2.2.0 Release Notes (Draft)"
linkTitle: "silo/console 2.2.0"
date: 2026-08-24
author: "Ruohang Feng"
description: "Draft notes for the proposed SILO Console 2.2.0 minor release: Go 1.27.0, the maintained silo-pkg fork, etcd client 3.7.1, conservative dependency maintenance, and correct indeterminate download progress."
tags: [Release, console]
weight: 1
draft: true
url: "/blog/release/console-2.2.0/"
aliases:
  - /releases/console-2.2.0/
---

> [!CAUTION]
> **Draft — not released.** The provisional release date is **2026-08-24** and the proposed version is **2.2.0**. There is no release commit, tag, binary, package, container image, checksum, signature, or public artifact for this candidate yet. Both date and scope may change before publication.

**Provisional date:** 2026-08-24 · **Candidate version:** `v2.2.0` · **Status:** draft

This candidate moves SILO Console onto Go 1.27, switches its shared-package dependency from upstream `minio/pkg` to the maintained [`pgsty/silo-pkg` 3.12.0 candidate](/blog/release/pkg-3.12.0/), adopts the stable etcd 3.7 client line, applies a deliberately small set of dependency patches, and includes the already committed download-progress correctness fix.

The proposed version is **2.2.0**, not 2.1.2. The user-facing download fix is patch-sized, but changing the shared policy/certificate implementation and crossing an etcd client minor boundary deserve a minor release with explicit compatibility notes.

## Download Progress Stays Honest {#download-progress}

The object browser no longer turns an unknown download size into a fabricated determinate percentage.

- A missing, invalid, or contradictory total remains **indeterminate** instead of being coerced into a misleading progress value.
- Zero-byte objects are normalized deliberately rather than falling through the unknown-total path.
- Abort and cancel transitions are terminal, so a late progress event cannot revive a completed cancellation.
- Unit and Chromium regression coverage exercise invalid totals, zero-byte objects, cancellation, and the visible progress state.

The fix is already committed as [`16960f7a`](https://github.com/pgsty/silo-console/commit/16960f7ab894ee8c1750ad9a6a93f984f5cd5077). The dependency work described below is still an uncommitted candidate.

## Toolchain and Go-maintained Modules {#go-toolchain}

The language, container-build, CI, tidy, and vulnerability-analysis baselines are aligned on Go 1.27:

| Component | Previous | Candidate |
|:--|:--|:--|
| `go` directive and build image | `1.26.5` | `1.27.0` |
| GitHub Actions matrix | `1.26.x` | `1.27.x` |
| tidy compatibility | `1.26` | `1.27` |

Go 1.27 is a supported compatibility release, but it changes the compiler, runtime, standard library, and default JSON implementation. The candidate is therefore built and tested under the final Go 1.27.0 toolchain rather than merely changing metadata.

The Go project-maintained modules selected by this graph are also refreshed:

| Module | Previous | Candidate |
|:--|:--|:--|
| `golang.org/x/crypto` | `v0.54.0` | `v0.55.0` |
| `golang.org/x/net` | `v0.57.0` | `v0.58.0` |
| `golang.org/x/text` | `v0.40.0` | `v0.41.0` |
| `golang.org/x/mod` | `v0.37.0` | `v0.40.0` |
| `golang.org/x/tools` | `v0.47.0` | `v0.49.0` |
| `golang.org/x/exp` | `2026-02-18` pseudo-version | `2026-08-20` pseudo-version |

`x/oauth2`, `x/sync`, `x/sys`, `x/term`, and `x/time` were already on the current selected versions and remain unchanged.

The legacy `x/exp/typeparams` submodule and `x/telemetry` also appear in the full graph, but only through tool or historical transitive requirements. `go mod tidy` does not retain them as root requirements, so this candidate does not manufacture unused pins merely to override those tool-only selections.

## Aligning with `silo-pkg` {#silo-pkg}

The old module graph required `github.com/minio/pkg/v3 v3.6.1`, which resolves to the upstream MinIO module. Merely changing the requirement version would still fetch upstream `minio/pkg`; it would **not** select the SILO fork. The intended final declarations explicitly select the sibling 3.12 candidate:

```go
require github.com/minio/pkg/v3 v3.12.0

replace github.com/minio/pkg/v3 => github.com/pgsty/silo-pkg/v3 v3.12.0
```

The `v3.12.0` tag and public proxy record do not exist yet, so the Console worktree temporarily pins the already-published fork at 3.11.0 and selects the 3.12 dependency floors at its root. A temporary modfile replaced that pin with the current local `silo-pkg` 3.12 tree for integration testing. Console cannot be tagged until `silo-pkg` 3.12.0 is published, the replace is updated to that real version, and the tests are rerun through the public module path.

This arrangement keeps every existing import path unchanged while ensuring the final binary is built against the maintained fork. The 3.12 candidate builds on the policy resource-boundary hardening, condition-key lookup repair, LDAP connection fixes, certificate-watcher cleanup, seeded-RNG repair, and duration round-trip fix documented in the [`silo-pkg` 3.11.0 release notes](/blog/release/pkg-3.11.0/), then adds the Go 1.27 / etcd 3.7 dependency baseline documented in its own [3.12.0 draft](/blog/release/pkg-3.12.0/).

Console directly consumes the fork's `certs`, `env`, `net`, `policy`, `console`, `trie`, `words`, `ellipses`, and `mimedb` packages. The replacement is therefore a real runtime dependency decision, not a documentation-only alignment.

## Why etcd 3.7.1 Instead of 3.6.14? {#etcd-3-7}

These two versions solve different problems:

| Line | Meaning |
|:--|:--|
| `3.6.14` | A patch on the existing 3.6 line. It is the smallest update that fixes GO-2026-6107 / CVE-2026-73500. |
| `3.7.1` | The current stable 3.7 minor line. It contains the same security fix plus the 3.7 client/API work and requires Go 1.26 or newer. |

etcd 3.7 is not a cosmetic version bump. It completes a substantial migration from legacy protobuf implementations to `google.golang.org/protobuf`, removes the old v2 client/server remnants, and makes `clientv3.New` non-blocking instead of honoring the deprecated `grpc.WithBlock` behavior. Consumers that embed the server, depend on internal packages, or rely on blocking client construction need a deliberate migration.

SILO Console does none of those things. Its dependency path reaches etcd through `silo-pkg/quick`, which accepts an already-created `*clientv3.Client` and uses the established v3 `Get` and `Put` calls. Neither Console nor `silo-pkg` creates an etcd client or embeds an etcd server. The three related Go modules are kept on exactly the same version, as etcd's module policy requires:

| Module | Previous | Candidate |
|:--|:--|:--|
| `go.etcd.io/etcd/api/v3` | `v3.6.8` | `v3.7.1` |
| `go.etcd.io/etcd/client/pkg/v3` | `v3.6.8` | `v3.7.1` |
| `go.etcd.io/etcd/client/v3` | `v3.6.8` | `v3.7.1` |

This upgrades the **compiled Go client libraries only**. It does not upgrade an operator's etcd servers, modify cluster data, enable 3.7-only server features, or change SILO's deployment topology. A separate etcd server upgrade from 3.6 to 3.7 must still follow the official one-minor-at-a-time procedure and begin from 3.6.11 or later.

## Conservative Third-party Maintenance {#third-party}

Third-party libraries are not upgraded wholesale. After inspecting the actual source diffs rather than trusting version numbers, the candidate keeps only one independent patch and the dependency changes required by the `silo-pkg` / etcd alignment:

| Module or family | Previous | Candidate | Reason |
|:--|:--|:--|:--|
| `github.com/cheggaaa/pb` | `v1.0.29` | `v1.0.30` | Same-line patch; aligned with the `silo-pkg` candidate |
| `github.com/lestrrat-go/jwx` | `v2.1.6` (`/v2`) | `v3.0.13` (`/v3`) | Required by `silo-pkg`; reviewed there as the maintained JWT line |
| `github.com/lestrrat-go/httprc` | `v1.0.6` | `v3.0.6` (`/v3`) | Coordinated JWX dependency; includes the reviewed refresh-loop fixes |
| `github.com/go-openapi/swag/conv` | `v0.25.5` | `v0.28.0` | Direct requirement of `silo-pkg`; `typeutils` moves with it |
| `github.com/grpc-ecosystem/grpc-gateway/v2` | `v2.28.0` | `v2.29.0` | Declared by etcd 3.7.1 |
| `go.yaml.in/yaml/v3` | `v3.0.4` | `v3.0.5` | Direct requirement of `silo-pkg` |

These associated changes are requirements of accepted first-party or security dependencies, not an independent sweep of Console libraries.

The first pass proposed `minio-go` 7.0.100 and the newest patches in each existing go-openapi minor line. Source review reversed that decision: `minio-go` 7.0.99 → 7.0.100 changes 19 files, including signing, endpoint, and cache behavior, while the go-openapi patches change 17–52 files per module and `spec` touches expander, loader, and SSRF-sensitive paths. With no forcing CVE, all remain at their original Console versions.

Other deliberately deferred updates include `pb/v3` 3.2, `klauspost/compress` 1.19, `minio-go` 7.3, `testify` 1.12, and newer go-openapi minor lines. No reachable vulnerability or required dependency relationship justifies them in this candidate.

The `pgsty/mc` fork was also reviewed. It currently publishes date-style application release tags rather than a directly consumable semantic Go module version. Switching Console's heavily used `github.com/minio/mc` library dependency would require a pseudo-version replacement and would mix application behavior changes into this dependency release, so that migration remains deferred.

## Security Review {#security}

- **etcd TLS-listener denial of service:** `go.etcd.io/etcd/client/pkg/v3` before 3.6.14 or 3.7.1 is affected by [GO-2026-6107 / CVE-2026-73500](https://pkg.go.dev/vuln/GO-2026-6107). Selecting 3.7.1 closes it while keeping all etcd modules aligned.
- **Go module verification:** `x/mod` 0.40.0 contains the fixes for [CVE-2026-56864](https://pkg.go.dev/vuln/GO-2026-6180) and [CVE-2026-56865](https://pkg.go.dev/vuln/GO-2026-6179).
- **Reachability result:** post-upgrade `govulncheck` reports zero vulnerable symbols reached by Console and zero vulnerable imported packages. The Swagger build tool is scanned separately with the same result.
- **OpenPGP advisory:** the scanner still reports the module-level [GO-2026-5932](https://pkg.go.dev/vuln/GO-2026-5932) notice because `x/crypto` contains the unmaintained `openpgp` package. Console does not import it, and the Go vulnerability database marks every version affected with no fixed release.

## Compatibility {#compatibility}

- No Console HTTP API, environment variable, command, binary name, systemd unit, configuration format, or embedded data layout is intentionally changed by the dependency work.
- The minimum **build toolchain** is now Go 1.27.0. The released binary remains self-contained and does not require Go on the target host.
- The etcd Go modules now require Go 1.26, which is below the Console's Go 1.27 build baseline.
- The `silo-pkg` fork tightens and repairs shared policy behavior. This is security-correct but is one reason to treat the release as a minor version and run authorization regression tests before tagging.
- The frontend package still reports 2.1.1 in the current candidate tree. It will be changed to 2.2.0 only in the final release commit, followed by a deterministic rebuild of the embedded assets.

## Verification Completed So Far {#verification}

The uncommitted dependency candidate has passed:

- `go mod tidy -diff`, `go mod verify`, `go vet ./...`, and full-package compile checks under Go 1.27.0;
- all Console tests that do not require external services, including the API suite with only the localhost-MinIO test excluded; the `integration`, `replication`, and SSO suites remain separate topology-dependent gates;
- static `linux/amd64` and `linux/arm64` builds with the production `kqueue,operator` tags;
- Swagger 2.0 specification validation and execution of the pinned Swagger tool;
- application and build-tool `govulncheck`, with zero reachable or imported-package vulnerabilities;
- the `silo-pkg` gate on the same etcd 3.7.1 line: golangci-lint with zero findings and the full `go test -race -tags kqueue ./...` suite.
- Console's `pkg`, `cmd/console`, and API tests plus a Linux/amd64 production-tag build using a temporary modfile that replaces `minio/pkg/v3` with the current local `silo-pkg` 3.12 candidate.

## Remaining Release Gates {#remaining-gates}

This draft is not evidence that v2.2.0 exists. Before publication:

1. publish and verify `silo-pkg` 3.12.0, update Console's replace from the staging 3.11.0 pin to the real 3.12.0 module version, and rerun the Go gates;
2. settle the final source scope and review every non-dependency change intended for 2.2.0;
3. run the full external MinIO and OpenLDAP/Dex SSO suites;
4. bump the frontend package version to 2.2.0 and regenerate the embedded assets from a clean tree;
5. run the complete frontend type, unit, Chromium, formatting, and production-build gates;
6. commit the focused changes, tag the exact verified tree, and build the release binaries, packages, images, checksums, signatures, and provenance metadata;
7. verify every public artifact before changing this page from `draft: true`.

## Related Commits {#related-commits}

- [`16960f7a`](https://github.com/pgsty/silo-console/commit/16960f7ab894ee8c1750ad9a6a93f984f5cd5077): fix: keep unknown downloads indeterminate
- Dependency and release commits: pending.

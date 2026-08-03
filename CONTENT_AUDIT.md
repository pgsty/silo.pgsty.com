# Silo Documentation Calibration Record

Last calibrated: 2026-08-03 (Asia/Shanghai)

This record separates source state, published releases, documentation changes, and rendered-site checks. It is also the review boundary for conservative `MinIO` to `Silo` branding changes.

## Evidence baseline

### Server source

- Repository: `/Users/vonng/pgsty/minio`
- Reviewed HEAD: `0b8dbdd66895` on `master`, 20 commits ahead of `origin/master`
- Latest public `pgsty/minio` release: `RELEASE.2026-06-18T00-00-00Z`
- The policy-condition hardening at `1a6d5b415`, storage-boundary checks added on 2026-08-02, and the merged notification-streaming fix at `b7f52ca43` are present in the reviewed source but are newer than the public release. Documentation must describe them as merged or source-level work, not as released behavior.
- The local `go.mod` and `go.sum` are modified to test `pgsty/silo-console`, and `.github/workflows/go.yml` is untracked. Those files are workspace state, not published-release evidence.
- The server still enables its inherited in-place updater unless `MINIO_UPDATE=off`. Its default release feed remains `dl.min.io`, and the release container carries the upstream signing key. Therefore Silo deployment examples set `MINIO_UPDATE=off`, and upgrades replace a pinned Silo package or image rather than invoking `mc admin update`.

### Client source

- Repository: `/Users/vonng/pgsty/mc`
- Reviewed HEAD: `65bdc60a4d14` on `build/harden-release-pipeline`, one commit ahead of `origin/master`
- The client worktree is clean. The local branch commit hardens release provenance, nFPM metadata, action pinning, and workflow checks while preserving the `mcli` package/archive name. It has not been merged to `origin/master` or published as a release, so it is source-level evidence only.
- Latest stable public client release: `RELEASE.2026-04-17T00-00-00Z`
- `RELEASE.2026-08-01T00-00-00Z` is a pre-release; `RELEASE.2026-08-03T00-00-00Z` is a draft. Neither replaces the stable version shown on the download page.
- `mc update` remains as a compatibility command but always returns exit status 1. It does not download or replace a binary.
- The release workflow builds standalone archives and Linux packages with the `mcli` binary name. Source builds and the client container retain `mc`; the server image also exposes the compatible `mc` command.
- `mc license` and `mc support` remain present and integrate with upstream MinIO SUBNET/commercial services. Their command names, protocol fields, MinIO wording, license links, and SUBNET links are contracts, not Silo branding.

### MinIO Operator

- Current deployment guidance is pinned to upstream MinIO Operator `v7.1.1`.
- The upstream `minio/operator` repository was archived and made read-only on 2026-03-20. Version `v7.1.1` is the final/latest upstream release, so these pages are a frozen compatibility snapshot, not an actively maintained Operator channel.
- Operator, `Tenant`, the `minio.min.io` API group, CRD fields, generated resource names, Operator images, and Operator environment variables retain their upstream names.
- The v7.1.1 Kustomize base defaults to `quay.io/minio/minio:RELEASE.2025-04-08T15-41-24Z`; Silo procedures explicitly override it with a published `pgsty/minio` image and set `MINIO_UPDATE=off`.
- The Tenant Chart reference and bundled values snapshot are synchronized to v7.1.1 defaults. Internal documentation links are routed to this site. The stale upstream `existingSecret` comment is corrected to the chart input actually used by its templates: `tenant.configSecret.name`.
- The archived Operator has no ongoing upstream compatibility or platform-support commitment. Silo documentation verifies only the pinned manifests and image override described here; users must validate the exact Kubernetes environment themselves.

## Branding boundary

For branding prose, preserve the source word's case: map `MINIO` to `SILO`, `MinIO` to `Silo`, and `minio` to `silo`. Apply this only when the text describes this project's product, server, deployment, console, availability, architecture, or operational recommendation.

Do not rename or rewrite these categories:

- Executables and commands such as `minio`, `minio server`, `mc`, and `mcli`.
- `MINIO_*` environment variables, configuration keys, API routes, HTTP headers, S3 fields, errors, metrics, and wire-format values.
- Go module/import paths, package names, repository names, upstream image names, generated Kubernetes resource names, and CRD/API identifiers.
- MinIO Operator, MinIO SDK names, MinIO SUBNET, KES product names, and other upstream proper nouns.
- Copyright, license, attribution, trademark, provenance, release identifiers, quoted upstream text, and historical article titles.
- Pages that explicitly describe migration from or interoperability with an upstream MinIO deployment.

When a phrase can be either product prose or a compatibility contract, leave it unchanged and add it to a later manual-review queue rather than guessing.

## Link policy and checks

- Site documentation links should be root-relative, language-correct internal routes whenever possible. Same-site absolute links must use `https://silo.pgsty.com`.
- Legacy MinIO server-documentation URLs under `min.io/docs`, `docs.min.io/minio`, and similar old routes have been removed from current documentation paths.
- The retired `docs.min.io/community/minio-kes/` deep links now collapse to one generic legacy page. They are replaced with the matching pages in the pinned `minio/kes-docs` source snapshot at `67cc5e56909035aad851f2d031a295a8ad9efe57`. KES itself is deprecated and archived; these are historical references, not a maintenance promise.
- SDK API links use upstream repositories or language-native API references instead of deleted legacy documentation pages.
- MinIO Operator links used by current procedures are pinned to the archived `v7.1.1` snapshot; historical migration pages may retain the version they document.
- `bin/check_internal_links.py` validates rendered internal routes, static assets, fragment identifiers, same-site absolute links, and links that accidentally target Hugo alias redirects. It intentionally does not make the build depend on third-party network availability.

## Verification completed for this calibration

- `go test ./cmd -run TestSelfUpdateDisabled -count=1` passed in the client repository.
- Focused server tests for policy-condition isolation, source IP/transport forgery resistance, object-lock spelling, malformed erasure metadata, bounded `ReadFile`, and zero shard size passed.
- `make check` passed: Go modules verified; Hugo built 590 English and 590 Chinese pages with warnings treated as fatal; 405,972 rendered internal references across 1,034 HTML files passed the internal route, asset, fragment, and canonical-target gate.
- The public release state and release asset names were checked through GitHub on 2026-08-03.
- This calibration pass did not create a commit or tag, publish a package, deploy the site, or mutate a remote release.

## Deliberately retained and follow-up queue

- The remaining front-matter titles containing `MinIO` belong to upstream Operator/CRD/SDK names, historical MinIO articles, or migration pages whose source or destination really is MinIO. They are not automatic replacement candidates.
- MinIO pricing and SUBNET links are retained where `mc license` or `mc support` documents the upstream commercial contract. KES links identify a deprecated, archived upstream dependency and its pinned historical documentation.
- Upstream `quay.io/minio/minio` values remain visible only in clearly labeled Operator Chart snapshots, historical Operator migration material, or prose that warns readers to override the upstream default.
- A stable client release newer than `RELEASE.2026-04-17T00-00-00Z` should trigger a new download-page and artifact audit. A server release newer than `RELEASE.2026-06-18T00-00-00Z` should trigger a source-versus-release reconciliation before newer fixes are described as shipped.
- The source tree still contains a large body of imported reference prose. Future passes should review one semantic area at a time, preserving identifiers and adding focused runtime or source evidence. A `silo_modified: false` marker means the page has not yet crossed this project's manual Silo calibration boundary; `silo_modified: true` means its substance changed beyond format conversion, not that every inherited sentence has been revalidated. Neither value proves that every `MinIO` token on the page is a branding error.

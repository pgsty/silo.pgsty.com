---
title: "MCLI Client Compatibility Notes"
linkTitle: "MC Client"
description: "Compatibility, behavior changes, installation, and the current pgsty/mc release"
url: "/compatibility/mcli/"
weight: 20
type: docs
icon: fa-solid fa-terminal
---

`mcli` is Silo's build of the MinIO Client (`mc`). This page records where the two are interchangeable and where they differ.

[`pgsty/mc`](https://github.com/pgsty/mc) forked from the upstream [`minio/mc`](https://github.com/minio/mc) at its final commit, [`77f82e18`](https://github.com/minio/mc/commit/77f82e18b5401a65958f1619df6ebb994634bd88) (2025-11-06). The upstream repository was archived in July 2026 without ever cutting a release that contains that commit — so every `mcli` release is strictly newer than any official `mc` binary ever published. Documented fork releases: [20260313], [20260321], [20260417], [20260804](/blog/release/mcli-20260804/), [20260806](/blog/release/mcli-20260806/), and [20260903](/blog/release/mcli-20260903/). The intermediate 20260901 artifact remains on GitHub, but the documentation compares the current release directly with 20260806.

> [!TIP]
> **Current release:** [`RELEASE.2026-09-03T07-13-05Z`](https://github.com/pgsty/mc/releases/tag/RELEASE.2026-09-03T07-13-05Z), package version `20260903071305.0.0`, built from [`a2ef95c0`](https://github.com/pgsty/mc/commit/a2ef95c035d9ae7cc01469a63926900f1786f9e2). It is available as Linux RPM/DEB/APK packages, six OS/architecture archives, and the multi-architecture `docker.io/pgsty/mc` image. See the [complete release notes](/blog/release/mcli-20260903/).

## Current release changes {#current-release}

The 20260903 client keeps the upstream command, configuration, protocol, and JSON contracts, with these deliberate additions and tightenings since 20260806:

- **Read-only checksum audit:** [`mc checksum verify`](/reference/minio-mc/mc-checksum-verify/#command-mc.checksum.verify) streams object data and compares stored `FULL_OBJECT` CRC32, CRC32C, CRC64NVME, SHA1, or SHA256 values. It supports one object, recursive prefixes, exact or all versions, JSON Lines manifests, dry runs, bounded workers, size/time filters, SSE-C, machine-readable output, private report files, and explicit failure policies. It never repairs or mutates an object.
- **Credential output is fail-closed:** `--debug`, `admin trace`, errors, redirects, trailers, JSON documents, SSE-C paths, custom headers, and registered runtime secrets are scrubbed before display. Support and cluster-export artifacts, including rotated copies, are created with mode `0600` on POSIX systems.
- **Correctness repairs:** JSON Prometheus metrics no longer panic; empty `pipe` input uses a regular zero-byte PUT; S3 Select responses are no longer closed twice after valid rows are printed; malformed app-level global flags fail instead of being ignored; and service-account policy clearing works again.
- **Strict writes, permissive reads:** named policy and service-account write paths reject empty or malformed policies, bare ARN namespaces, and mixed S3/admin action statements. Existing stored policies remain readable; an empty service-account policy still means “clear the inline policy.”
- **Dependency and toolchain floor:** builds require Go 1.27.1 and directly consume `github.com/pgsty/silo-pkg/v3` v3.13.2. `minio-go` is pinned to upstream master commit `0e78d3f18efe`; gRPC is 1.83.2 and `x/crypto` is 0.56.0. Darwin binaries require macOS 13 or newer.
- **Verifiable delivery:** the public release is immutable, contains 19 checksum-checked assets, and binds archives plus DEB/APK packages to the signed tag and exact source with Sigstore attestations. RPMs carry the PGSTY GPG signature. The release and `latest` container tags publish matching linux/amd64 and linux/arm64 manifests.

Two low-level compatibility changes are worth testing in specialized deployments: JWX 3.2 rejects non-compliant JWT `crit` processing more strictly, and updated Unicode width handling can slightly change table/progress alignment for Indic or ZWJ-heavy strings.

## Principles {#principles}

The fork follows one rule: **the shipped artifact and its channels are renamed; the tool you use is not.**

- **Renamed / replaced** — the artifact name on disk (`mcli`), the product identity in `--version` and `--help`, the distribution channels (GitHub `pgsty/mc`, the Pigsty repository, `docker.io/pgsty/mc`), and the signing keys. Not the command syntax, and — depending on how you install it — not even the name you type.
- **Unchanged** — every command, subcommand, and flag; S3 and admin API behavior, request signing, and protocol headers (`x-minio-*`); JSON output schemas; exit codes of normal operations; the configuration file format and alias semantics; `MC_*` environment variables (including `MC_HOST_<alias>`); the `.part.minio` resume suffix; and the Go module path `github.com/minio/mc`.
- **Severed** — every connection to MinIO-operated services: the release/update feed, the SUBNET support and licensing portal, telemetry, and the pre-seeded `play` demo alias. Affected commands remain in the CLI for script compatibility and fail with a stable error rather than disappearing.
- **Preserved** — upstream copyright and the AGPL-3.0 license. Runtime output credits both MinIO, Inc. and PGSTY.

A configuration written by upstream `mc` is readable by `mcli` unchanged, and vice versa. SILO releases test mcli against Silo; operation against upstream MinIO and other S3-compatible endpoints is retained on a best-effort basis and should be verified with the exact versions in use.

## What changed {#changed}

Ordered by how likely each change is to affect you, most likely first.

### 1. The name — what you type, and where the config lives {#naming}

For many users nothing changes here: the container image keeps `mc` as its entrypoint, and a binary installed under the name `mc` behaves identically to upstream. What changed is what we ship — archives and Linux packages install the binary as **`/usr/local/bin/mcli`** (package name `mcli`).

Neither name is hardcoded anywhere. Since 2016 the upstream client has derived its runtime identity from the name it is invoked as, and `mcli` is the exact rename upstream's own `CONFLICT.md` recommended ([issue #873](https://github.com/minio/mc/issues/873#issuecomment-267583013)) for the Midnight Commander clash — this fork merely promoted that suggestion to the official shipping name, with zero code changes. What that mechanism means in practice:

| Follows the invoked name                                                                  | Fixed, regardless of the name                                           |
|:------------------------------------------------------------------------------------------|:------------------------------------------------------------------------|
| Configuration directory: `~/.mc` vs `~/.mcli` (Windows: `%USERPROFILE%\mc\` vs `…\mcli\`) | Environment variables: always `MC_*` — there is no `MCLI_CONFIG_DIR`    |
| Program name shown in help and usage text                                                 | `config.json` format — identical and interchangeable in both directions |
| Shell-completion registration                                                             | All commands, flags, JSON output, exit codes                            |
| User-Agent application suffix (`mc/…` vs `mcli/…`)                                        | `--config-dir` and `MC_CONFIG_DIR` overrides                            |

The one real trap: **run `mcli` for the first time and your existing `mc` aliases are not there** — it starts from an empty `~/.mcli`. Either keep invoking it as `mc` (a symlink suffices — argv[0] is what counts), or copy the state once with `cp -a ~/.mc ~/.mcli`. For automation and configuration templates, set `MC_CONFIG_DIR` explicitly: the environment prefix does not follow the name, so one template serves both. Details in [Migration](#migration).

Get it from [GitHub Releases](https://github.com/pgsty/mc/releases) (SHA-256 `mcli_<version>_checksums.txt`), the [Pigsty repository](https://pigsty.io/docs/repo/infra/list/#object-storage) (RPMs GPG-signed, key fingerprint `9592A7BC7A682E7333376E09E7935D8DB9BD8B20`), or `docker.io/pgsty/mc`. Upstream's minisign key does not sign these artifacts, and `dl.min.io` is never contacted. Release tags (`RELEASE.YYYY-MM-DDTHH-MM-SSZ`) and package versions (`YYYYMMDDHHMMSS.0.0`) keep their upstream schemes.

### 2. `mcli update` always fails — on purpose {#self-update}

Self-update is removed. `mcli update` never contacts the network and never replaces its binary; it prints an explicit notice and **always exits `1`**. Upstream `mc update` exited `0` when already current, so **any cron job or script that calls it and treats a non-zero exit as failure will start failing** — drop the call and upgrade through your package manager or GitHub Releases instead. The per-invocation version probe against upstream release feeds is also gone, and `MC_UPDATE` / `MINIO_UPDATE` are no longer consulted.

(`mcli admin update ALIAS` — updating the *server* — still exists, but Silo servers reject in-place updates server-side.)

### 3. SUBNET, licensing, and telemetry commands {#subnet}

Everything that reached MinIO SUBNET is disabled at build time. Affected commands keep their names and flags, print a stable notice — *"MinIO SUBNET services (registration, licensing, uploads) are disabled in this Silo build of mc; diagnostics remain available locally."* — and exit `1`:

| Command                                      | Behavior now     | Use instead                                                    |
|:---------------------------------------------|:-----------------|:---------------------------------------------------------------|
| `mcli license register`                      | notice, exit `1` | —                                                              |
| `mcli license update ALIAS` (online renewal) | notice, exit `1` | `mcli license update ALIAS license.key` (offline, still works) |
| `mcli support upload`                        | notice, exit `1` | share files through your own channels                          |
| `mcli support proxy set`                     | notice, exit `1` | `proxy remove` still clears a legacy setting                   |
| `mcli support callhome enable`               | notice, exit `1` | `disable` / `status` still work                                |

The diagnostics themselves stay: `mcli support diag` / `perf` / `profile` / `inspect` always run in local (airgap) mode — results are written to local files, nothing is uploaded, and SUBNET registration is no longer a prerequisite. Two related hardening changes: `inspect` no longer falls back to encrypting output with an embedded MinIO public key (your archives stay decryptable by you), and since 20260804 `--debug` output redacts SUBNET credentials — if you ever shared debug logs from older builds, rotate the keys in them. `mcli license info` and `unregister` work locally.

### 4. The `play` demo alias is no longer pre-seeded {#aliases}

Fresh configurations seed `local`, `s3`, and `gcs` — not `play`. Tutorials and smoke scripts that assume the demo alias need it added explicitly: `mcli alias set play https://play.min.io <access-key> <secret-key>` restores the old behavior, since nothing blocks deliberate access to any S3 endpoint. Existing configuration files are never modified.

### 5. Output text carries the Silo identity {#identity}

`mcli --version` keeps its machine-readable first line and adds an identity line plus dual copyright; `--help` says "Silo client" and examples use `mysilo`. Command syntax is untouched — only scripts that grep for upstream identity strings (e.g. "MinIO Client") need adjusting.

### 6. For developers {#source}

The module path stays `github.com/minio/mc`, so imports compile unchanged — but `go install github.com/minio/mc@latest` installs the **archived upstream**, not this fork. Build from source (`git clone https://github.com/pgsty/mc && cd mc && make`) or consume it via a `replace` directive. Contributions need no CLA but require a DCO sign-off (`git commit -s`). Upstream being archived also means inherited defects are only ever fixed here — most notably [minio/mc#5139](https://github.com/minio/mc/issues/5139) (`mirror --remove --watch` on versioned buckets).

## Migration {#migration}

Moving from an official `mc` binary to `mcli`:

1. **Install `mcli`** from one of the fork's channels (see [§1](#naming) for verification): GitHub Releases archive, `yum install mcli` / `apt install mcli` from the Pigsty repository, or `docker pull pgsty/mc`.
2. **Decide what to call it** — this determines which configuration it reads:
   - *Keep the `mc` name (least friction)*: after confirming no upstream binary remains (`command -v mc`), install it as `mc` — e.g. `ln -s /usr/local/bin/mcli /usr/local/bin/mc`. Invoked as `mc`, it reads your existing `~/.mc` untouched; nothing else to migrate.
   - *Adopt the `mcli` name*: carry your state over once with `cp -a ~/.mc ~/.mcli`, or set `MC_CONFIG_DIR=~/.mc`. Both clients can also coexist side by side, each with its own directory.
3. **Clean up automation**:
   - remove `mc update` calls — they now always exit `1`;
   - remove `license register`, `support upload`, `support callhome enable`, and `support proxy set` — same stable failure;
   - `support diag` / `perf` / `profile` / `inspect` keep working and write local files; drop any step that expected a SUBNET upload;
   - review anything that greps `--version` output beyond the first line.
4. **Re-check `play` usage** in tutorials and smoke scripts ([§4](#aliases)).
5. **Verify**: `mcli --version`, `mcli alias ls`, then `mcli ls <alias>` and `mcli ping <alias>` against your servers.
6. **Rollback** stays trivial: the configuration format is identical in both directions, so keeping the old `mc` binary around lets you switch back at any time.

## See also {#see-also}

- [Silo vs. MinIO](/compatibility/server/) — how the `silo` server compares to `minio`

[20260313]: https://github.com/pgsty/mc/releases/tag/RELEASE.2026-03-13T08-57-32Z
[20260321]: https://github.com/pgsty/mc/releases/tag/RELEASE.2026-03-21T00-00-00Z
[20260417]: https://github.com/pgsty/mc/releases/tag/RELEASE.2026-04-17T00-00-00Z

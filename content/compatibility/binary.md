---
title: "Native Package Migration"
linkTitle: "Native Package"
description: "How the silo RPM/DEB packages differ from the minio packages: file layout, service account, takeover semantics, and caveats."
url: "/compatibility/binary/"
weight: 20
type: docs
icon: fa-solid fa-box
---

Silo publishes `silo` packages for RPM, DEB, and APK on `amd64`/`arm64` via [GitHub Releases](https://github.com/pgsty/silo/releases), with SHA-256 sums and build-provenance attestations. This page records what changes relative to a `minio` package installation: the file layout, the service account, and the caveats. General migration scope is in the [migration guide](/compatibility/migration/).

## Installing {#install}

Download the package that matches your platform from the release assets, then verify its checksum before installing:

```bash
SILO_TAG=RELEASE.2026-09-16T00-00-00Z
SILO_RPM=silo-20260916000000.0.0-1PGSTY.x86_64.rpm
SILO_URL="https://github.com/pgsty/silo/releases/download/$SILO_TAG"
curl -fLO "$SILO_URL/$SILO_RPM"
curl -fLO "$SILO_URL/$SILO_RPM.sha256sum"
sha256sum --check "$SILO_RPM.sha256sum" && \
  sudo dnf install "./$SILO_RPM"
```
This example selects the x86_64 RPM. For ARM64 use `.aarch64.rpm`; on Debian/Ubuntu select the `.deb` file and matching checksum from the download page.


If you use the Pigsty package repository, `dnf install silo` / `apt install silo` resolves the same artifacts (the repository may lag GitHub Releases). The package intentionally provides **no** `minio` alias or `Provides:` relationship — `minio` and `silo` are separate packages that coexist, and the takeover happens at the systemd level, not through package replacement (see [Takeover](#takeover)).

## File layout {#layout}

| MinIO installation | Silo package |
| :-- | :-- |
| `/usr/bin/minio` | `/usr/bin/silo` (also provides `silo healthcheck`) |
| `minio.service` | `/usr/lib/systemd/system/silo.service` |
| `/etc/default/minio` | Still read, first; `/etc/default/silo` overrides per variable (`noreplace`/conffile — upgrades never overwrite edits) |
| service account `minio-user` (upstream) / `minio` (Pigsty) | `silo:silo`, declared in `/usr/lib/sysusers.d/silo.conf`, created on install |
| — | `/usr/share/doc/silo/LICENSE`, `NOTICE` (AGPL-3.0-or-later) |

Two package properties:

- Installation never starts or enables the service; `postinstall` only creates the `silo` account and reloads systemd.
- The package installs alongside the `minio` package — no file conflicts, so the old package stays available for rollback.

## Service account {#user}

The unit defaults to `User=silo`, but existing data, TLS keys, and KMS credentials belong to the old MinIO user. Do not chown the data. Run Silo as the current owner via a drop-in:

```bash
ls -ld /path/to/your/data              # note the owner, e.g. minio-user
sudo mkdir -p /etc/systemd/system/silo.service.d
sudo tee /etc/systemd/system/silo.service.d/10-legacy-user.conf <<'EOF'
[Service]
User=minio-user
Group=minio-user
EOF
sudo systemctl daemon-reload
```

This also keeps TLS working: Silo resolves certificates from the runtime user's home (`~/.silo/certs`, falling back to the legacy `~/.minio/certs`), so the existing `public.crt`/`private.key`/`CAs/` are found without copying. Without the drop-in, a TLS deployment fails to start:

```text
FATAL Unable to start the server: HTTPS specified in endpoints,
      but no TLS certificate is found on the local machine
```

Adopting the `silo` account is an optional later change: move the certificates to a `silo`-readable path, set `--certs-dir` in `MINIO_OPTS`, and transfer data ownership outside the migration window.

## Takeover and rollback {#takeover}

The unit is a takeover unit:

```ini
[Unit]
After=network-online.target minio.service
Conflicts=minio.service

[Service]
Type=notify
EnvironmentFile=-/etc/default/minio
EnvironmentFile=-/etc/default/silo
ExecStart=/usr/bin/silo server $MINIO_OPTS $MINIO_VOLUMES
Restart=always
```

- `Conflicts=minio.service`: systemd never runs both units; starting one stops the other. This switches processes, but does not establish that state can safely be rolled back between versions.
- The `EnvironmentFile` chain means `MINIO_VOLUMES`, `MINIO_OPTS`, credentials, and KMS settings from `/etc/default/minio` apply unchanged.
- `Type=notify`: `systemctl start` returns success only after the server is actually ready.

Switch over:

```bash
sudo cp -a /etc/default/minio /etc/default/minio.migration-backup   # cheap insurance
sudo systemctl disable --now minio.service
sudo systemctl enable  --now silo.service
silo healthcheck --url https://127.0.0.1:9000 ready    # http:// without TLS
mc admin info <existing-alias>
```

Before rollback, validate the target version, complete recovery point and IAM/bucket-configuration state under [rollback scope](/compatibility/migration/#rollback). Retaining ownership, certificates and the old unit does not mean state needs no restoration; the following commands only illustrate service switching on one node:

```bash
sudo systemctl disable --now silo.service
sudo systemctl enable  --now minio.service
```

After validation completes and the rollback window closes, optionally mask the old unit so nothing but an explicit `systemctl unmask` can bring it back:

```bash
sudo systemctl mask minio.service
```

## Caveats {#caveats}

- **Coordinate the switch across all cluster nodes.** Prepare every node first (install packages and create drop-ins), stop all old processes, confirm they have exited, then start all new processes. Avoid old and new versions accessing storage together. See [migration notes](/compatibility/migration/#one-binary) for mixed versions and binary consistency; for shared IAM or site replication, coordinate every participant under the [IAM upgrade procedure](/operations/replication/iam-upgrade/). Rollback must also meet the applicable state-recovery requirements.
- **Non-packaged installations work the same way.** A `/usr/local/bin/minio` with a custom unit is taken over identically, as long as its configuration lives in `/etc/default/minio`.
- **Crash loops rate-limit.** A misconfigured start (for example, missing certificates) repeats under `Restart=always` until systemd's start limit trips (`Start request repeated too quickly`). Fix the cause, then `systemctl reset-failed silo && systemctl start silo`.
- **An old `minio.service` stop can hang.** Legacy units commonly set `TimeoutSec=infinity`. If graceful shutdown remains stuck after traffic is drained and the shutdown allowance expires, an operator can force it with `sudo systemctl kill --signal=SIGKILL minio.service`, then confirm the old process has exited before starting Silo. This interrupts any remaining requests; plain `systemctl kill` defaults to another `SIGTERM` and does not resolve a process that ignores it.
- **The environment chain can surprise you during the bridge period.** `/etc/default/minio` is still read while `/etc/default/silo` exists: deleting a variable from `/etc/default/silo` does not disable it — the old value from `/etc/default/minio` applies again. Remove the variable from both files, or comment it out in the file that still carries it.
- **Keep the rollback window.** Leave the `minio` package, unit, and binary installed until validation completes; a disabled unit costs nothing. Remove the old package afterwards if desired.
- **Rolling restarts after migration**: gate each with `silo healthcheck --maintenance cluster`; exit `0` means stopping this node keeps write quorum, HTTP `412` means it does not.

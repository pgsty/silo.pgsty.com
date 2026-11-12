---
title: "Security Policy"
linkTitle: "Security"
description: "How to report vulnerabilities in PGSTY SILO and where security advisories and fixes are published."
url: "/about/security/"
weight: 40
type: docs
icon: fa-solid fa-shield-halved
---

PGSTY SILO maintains active security tracking and patching for the S3-compatible object storage stack after upstream `minio/minio` entered archive mode. Production deployments should run **[Server 20261112](/blog/release/silo-20261112/)**, embedded and standalone **[Console v2.7.2](/blog/release/console-2.7.2/)**, **[mcli 20261112](/blog/release/mcli-20261112/)**, and **[silo-pkg v3.16.1](/blog/release/pkg-3.16.1/)**, all built with Go 1.27.4, alongside optional external **[KES 20261026](/blog/release/silo-20261026/#kes)** (Go 1.27.3).

Server 20261112 embeds Console v2.7.2 and delivers `SN-2026-020` through `SN-2026-025`: single-pool `DeleteObjects` containment, service-account inline-policy tri-state preservation, active-active tagging/read-proxy authorization and response-header redaction, `STREAMING-UNSIGNED-PAYLOAD-TRAILER` replay window and header validation, `s3:ExistingObjectTag/<key>` and version-action enforcement across attributes/copy/select/ZIP archive reads, strict IAM and bucket policy JSON decoding, and `null`-version and replica Object Lock hardening. It retains all earlier security repairs, including `SN-2026-018` through `SN-2026-019` from Server 20261109, `SN-2026-015` through `SN-2026-017` from Server 20261018, and `SN-2026-011` through `SN-2026-014` from Server 20260916. Review the [20261112 upgrade requirements](/blog/release/silo-20261112/#upgrade), [Advisory Ledger](/about/security-advisories/), and [Component Matrix](/compatibility/versions/) before upgrading.

Deploying standalone Console or `mcli` does not replace components embedded in an older Server binary; Server-side authorization, lifecycle, and Object Lock fixes require upgrading SILO Server.

## Reporting a Vulnerability {#reporting}

Report undisclosed vulnerabilities through a private channel rather than a public issue:

- **SILO Server, Console, `mcli`, `silo-pkg`, and `kes`**: Submit a private report via [GitHub Security Advisories on `pgsty/silo`](https://github.com/pgsty/silo/security/advisories/new). If GitHub private vulnerability reporting is unavailable, email [ron@pgsty.com](mailto:ron@pgsty.com) or [rh@vonng.com](mailto:rh@vonng.com).
- **Documentation (`silo.pgsty.com`)**: Open an issue on [`pgsty/silo.pgsty.com`](https://github.com/pgsty/silo.pgsty.com/issues), or use the private advisory channel above if the report discloses an exploitable weakness.

Include the affected component version, reproduction steps, and impact scope. SILO is maintained as an open-source project on a best-effort basis without commercial response-time SLAs.

## Upstream MinIO Vulnerabilities {#upstream}

Because SILO shares lineage with `minio/minio`, most vulnerabilities in inherited code affect both codebases. Report findings in inherited code directly to SILO; when a vulnerability affects other active distributions of the same lineage, we coordinate disclosure as appropriate.

## Where Fixes Are Published {#published}

- **[Advisory Ledger](/about/security-advisories/)**: The canonical index of all `CVE-*` and `SN-2026-*` identifiers, fix commits, affected versions, and dependency security updates.
- **[Security Advisories](/blog/security/)**: Technical advisories detailing root causes, exploit conditions, code fixes, and upgrade requirements.
- **[Release Notes](/blog/release/)**: Versioned release announcements for Server, Console, `mcli`, `silo-pkg`, and `kes`.

## Deployment Hardening {#hardening}

- [Security Checklist](/operations/checklists/security/) — production access control, network isolation, and key management.
- [Network Encryption (TLS)](/operations/network-encryption/) — certificate configuration for S3, Console, and internode traffic.

## See Also {#see-also}

- [Contributors](/about/contributors/)
- [License](/about/license/)
- [Attribution](/about/attribution/)

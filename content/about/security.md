---
title: "Security Policy"
linkTitle: "Security"
description: "How to report vulnerabilities in PGSTY SILO and where security advisories and fixes are published."
url: "/about/security/"
weight: 40
type: docs
icon: fa-solid fa-shield-halved
---

PGSTY SILO maintains active security tracking and patching for the S3-compatible object storage stack after upstream `minio/minio` entered archive mode. Current production deployments should run [Server 20261018](/blog/release/silo-20261018/) (which fixes Object Lock advisories `SN-2026-015` / `SN-2026-016` and IAM Admin boundary `SN-2026-017`, building on `SN-2026-011` through `SN-2026-014` from Server 20260916), [Console v2.5.0](/blog/release/silo-20261025/#console-250), and [mcli 20261025](/blog/release/mcli-20261025/); see the [October Security Note](/blog/security/20261018-release-hardening/), [Advisory Ledger](/about/security-advisories/), and [Component Matrix](/compatibility/versions/).

Standalone Console does not replace Server’s embedded Console. Policy Reset and immediate bucket-inventory freshness need the Server repairs already on main; Server 20261018 does not include them. See the [Console upgrade boundary](/blog/release/silo-20261025/#console-250).

## Reporting a Vulnerability {#reporting}

Report undisclosed vulnerabilities through a private channel rather than a public issue:

- **SILO Server, Console, `mcli`, and `silo-pkg`**: Submit a private report via [GitHub Security Advisories on `pgsty/silo`](https://github.com/pgsty/silo/security/advisories/new).
- **Documentation (`silo.pgsty.com`)**: Open an issue on [`pgsty/silo.pgsty.com`](https://github.com/pgsty/silo.pgsty.com/issues), or use the private advisory channel above if the report discloses an exploitable weakness.

Include the affected component version, reproduction steps, and impact scope. SILO is maintained as an open-source project on a best-effort basis without commercial response-time SLAs.

## Upstream MinIO Vulnerabilities {#upstream}

Because SILO shares lineage with `minio/minio`, most vulnerabilities in inherited code affect both codebases. Report findings in inherited code directly to SILO; when a vulnerability affects other active distributions of the same lineage, we coordinate disclosure as appropriate.

## Where Fixes Are Published {#published}

- **[Advisory Ledger](/about/security-advisories/)**: The canonical index of all `CVE-*` and `SN-2026-*` identifiers, fix commits, affected versions, and dependency security updates.
- **[Security Advisories](/blog/security/)**: Technical advisories detailing root causes, exploit conditions, code fixes, and upgrade requirements.
- **[Release Notes](/blog/release/)**: Versioned release announcements for Server, Console, `mcli`, and `silo-pkg`.

## Deployment Hardening {#hardening}

- [Security Checklist](/operations/checklists/security/) — production access control, network isolation, and key management.
- [Network Encryption (TLS)](/operations/network-encryption/) — certificate configuration for S3, Console, and internode traffic.

## See Also {#see-also}

- [License](/about/license/)
- [Attribution](/about/attribution/)

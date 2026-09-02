---
title: "Security Policy"
linkTitle: "Security"
description: "How to report a vulnerability in PGSTY SILO, and where fixed issues are published."
url: "/about/security/"
weight: 40
type: docs
icon: fa-solid fa-shield-halved
---

Security maintenance is the reason this fork exists. Upstream `minio/minio` is archived; Silo tracks CVEs against the codebase, backports or writes the fixes, and publishes what it found.

## Reporting a vulnerability {#reporting}

Report undisclosed high-severity vulnerabilities through a private channel, not in a public issue.

- **Silo server and `mcli` client** — preferably as a private report through [GitHub Security Advisories on `pgsty/silo`](https://github.com/pgsty/silo/security/advisories/new).
- **This documentation** — open an issue on [`pgsty/silo.pgsty.com`](https://github.com/pgsty/silo.pgsty.com/issues); if the content itself discloses a weakness, use a private channel instead.

Include the affected release, a description of the impact, and reproduction steps if you have them — this helps us confirm the issue faster.

We will do our best to respond within a reasonable time, but note that Silo is a community project: we promise no fix SLA and no guaranteed response time.

## Vulnerabilities in upstream MinIO {#upstream}

Silo is a fork, so the vast majority of findings apply to `minio/minio` as well. The upstream repository is archived and no longer accepts reports — precisely the gap this project fills. Report to Silo; where an issue affects other distributions of the same code, the project coordinates disclosure with them.

## Where fixes are published {#published}

- [Security Chronicle](/blog/security/) —
  one article per investigated CVE: the original threat model, the back-and-forth of the review, the rejected alternatives, the invariant finally settled on, the verifying evidence, and the compatibility cost.

- [Release Notes](/blog/release/) —
  the release each fix first shipped in and became publicly available.

## Hardening your own deployment {#hardening}

Reporting is one half; configuration is the other. See the [security checklist](/operations/checklists/security/) for deployment hardening, and [network encryption](/operations/network-encryption/) for TLS setup.

## See also {#see-also}

- [License](/about/license/) — the software is provided as-is, without warranty of any kind
- [Attribution](/about/attribution/) — copyright and derivation of this documentation

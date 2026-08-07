---
title: "The Silo Manifesto"
linkTitle: "Manifesto"
description: "Silo's commitments in eleven articles: what the project maintains, what it refuses to promise, and where to check both."
url: "/about/manifesto/"
aliases:
  - /about/manifest/
  - /manifesto/
weight: 5
type: docs
icon: fa-solid fa-scroll
minio_origin: false
silo_modified: false
---

Silo keeps an open-source, feature-complete, S3-compatible object store maintained and installable, with a build and release chain anyone can inspect. That is the whole scope.

This page is the project's public commitment, and it follows one rule: **every article below is either something we already do, with public evidence, or something we explicitly refuse to promise.** A promise we could not keep would be worse than no promise.


## Article 1 · Reason to exist, and an exit clause {#exit}

This project started when upstream wound down its community edition: the web console was cut back to a stub, prebuilt community binaries stopped, and the community repository was archived.
Silo keeps existing MinIO-compatible deployments running. [Pigsty](https://pigsty.io) runs it in production as its PostgreSQL backup storage, so our own operations depend on the artifacts we publish.

The fork is a means, not an identity. If upstream restores its community edition, we will narrow our scope and offer our fixes back.

> Background:
> - [MinIO is Dead](/blog/post/minio-is-dead/) (2025-12) — what upstream removed, and when.
> - [MinIO Is Dead. Which Next?](/blog/post/minio-alternative/) (2025-12) — the alternatives, evaluated.
> - [MinIO Is Dead, Long Live MinIO](/blog/post/minio-resurrect/) (2026-02) — the fork, announced.
> - [MinIO Fork, Promise Kept](/blog/post/minio-promise-kept/) (2026-04) — the first months of receipts.


## Article 2 · The compatibility contract {#compatibility}

The product and its trademark are renamed; the protocol and your data are not.

- The S3 API, `MINIO_*` environment variables, `minio_*` metrics, `x-minio-*` headers, `/minio/*` routes, and the on-disk format (including `.minio.sys`) are preserved, and held in place by a CI compatibility check.
- Every release documents its tested rollback target and path in the [release notes](/blog/release/).
- New capabilities do not touch the on-disk format. Any exception must be explicitly marked as **non-reversible** before you can enable it.
- The [migration guide](/compatibility/migration/), which includes how to leave Silo, and the per-component [compatibility audits](/compatibility/) are public and maintained.

## Article 3 · The license cannot change {#license}

Silo is [AGPLv3](/about/license/). There is no CLA and no copyright aggregation: contributions are accepted only with DCO sign-off, so copyright stays with each contributor.
That is not a verbal promise not to relicense. It means nobody here, ourselves included, holds enough copyright to relicense the project on everyone else's behalf.

Our reading of the AGPL boundary is a position, not legal advice: using Silo through its S3 API does not make your application a derivative work.
We will not use the license as a threat or a sales instrument.


## Article 4 · Change discipline {#changes}

Changes relative to the upstream baseline fall into four classes only: security fixes, defect fixes, restored community features, and optional additions.
Existing API semantics change only when a security fix demands it, and every such compatibility cost is recorded in the advisory that caused it.
Every divergence from upstream is listed in the code-verified [compatibility audit](/compatibility/server/).


## Article 5 · The never list {#never}

Silo will never:

- move an existing feature behind a paywall;
- put a registration or login wall in front of downloads;
- ship telemetry — the upstream phone-home paths (update checks, SUBNET, call-home) are removed outright, not merely disabled;
- require a CLA;
- change the license;
- use trademarks against normal use or descriptive mention.

This list is append-only: entries may be added, never removed.


## Article 6 · Security discipline {#security}

- Vulnerabilities are reported through a [private channel](/about/security/) and triaged reproducibly. Writeups are held until the fixed release ships.
- Every security fix ships with a [public advisory](/blog/security/), including its evidence and its compatibility cost.
- Dependencies are tracked for CVEs, with reachability analysis before any change.
- Every release ships SHA-256 checksums, SPDX SBOMs, Sigstore-signed manifests, and GitHub build provenance.

Severe, remotely exploitable issues are expedited on a best-effort basis, but we do not commit to a specific fix-time SLA.


## Article 7 · Release cadence {#releases}

Releases ship typically every one to two months, and at most a quarter apart. Security and defect fixes are batched into these releases. The history is [public](/blog/release/); judge the promise against it.

Version tags keep the `RELEASE.YYYY-MM-DDTHH-MM-SSZ` format, and each release documents its upstream baseline.
Deprecations get at least six months' notice and a migration path. The exception is a removal that security requires immediately; the removal and its justification are then published in the [security advisories](/blog/security/).


## Article 8 · Upstream relations {#upstream}

We renamed the project out of respect for upstream's trademarks. Upstream copyright, license, and third-party notices are preserved in full: [attribution](/about/attribution/) and [trademark](/about/trademark/).
If upstream resumes accepting contributions, applicable fixes will be offered back as appropriate.

## Article 9 · Continuity {#continuity}

- The repositories live under the [pgsty](https://github.com/pgsty) organization, not a personal account.
- The build is documented and provenance-attested: anyone can rebuild equivalent artifacts from source without us.
- If active maintenance stops for six months, we will say so publicly and archive the project rather than let it go quiet. Released artifacts and documentation stay up as long as we can keep them up.
- If an established open-source organization (a CNCF-style foundation, say) wanted to bring Silo under more formal governance, we would cooperate.

## Article 10 · The commercial boundary {#commercial}

Everything in the Silo repositories is complete and free of charge: the server, the client, the console, and the released artifacts. That does not change.


## Article 11 · Amendment discipline {#amendments}

Additions and strengthenings of this manifesto take effect immediately. Weakening or removing any article requires ninety days' public notice. Article 5 is append-only, always.

Where to check:

- [Security advisories](/blog/security/): every CVE investigated and fixed, one article per incident.
- [Release notes](/blog/release/): every release, with its baseline, rollback target, and acceptance record.
- [Compatibility audits](/compatibility/): where Silo matches MinIO, and where it deliberately differs.

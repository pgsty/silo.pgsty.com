---
title: "The Silo Manifesto"
linkTitle: "Manifesto"
description: "What Silo promises, what it deliberately refuses to promise, and the public evidence for both — the project's commitments in eleven articles."
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

Silo exists for one purpose: to keep a trustworthy, maintained, feature-complete community edition of S3-compatible object storage in existence, and to keep its software supply chain unbroken.

This page is the project's public commitment. It follows one rule throughout: **every article is either something we already practice with public evidence, or something we deliberately refuse to promise.** A commitment we could not keep would be worse than none.


## Article 1 · Reason to exist, and an exit clause {#exit}

This project was born when upstream wound down its community edition: the web console was stripped, prebuilt community binaries stopped, and the community repository was archived.
Silo provides continuity for existing MinIO-compatible deployments — [Pigsty](https://pigsty.io) runs it in production as its PostgreSQL backup storage, so our own operations depend on the same artifacts we publish.

The fork is a means, not an identity. If upstream restores its commitment to a community edition, we will welcome it, gladly narrow our scope, and offer our fixes back.

> Background:
> - [MinIO is Dead](/blog/post/minio-is-dead/) (2025-12) — what upstream removed, and when.
> - [MinIO Is Dead. Which Next?](/blog/post/minio-alternative/) (2025-12) — the alternatives, evaluated.
> - [MinIO Is Dead, Long Live MinIO](/blog/post/minio-resurrect/) (2026-02) — the fork, announced.
> - [MinIO Fork, Promise Kept](/blog/post/minio-promise-kept/) (2026-04) — the first months of receipts.


## Article 2 · The compatibility contract {#compatibility}

The product and its trademark are renamed; the protocol and your data are not.

- The S3 API, `MINIO_*` environment variables, `minio_*` metrics, `x-minio-*` headers, `/minio/*` routes, and the on-disk format (including `.minio.sys`) are preserved, and frozen by a CI compatibility guard.
- Every release documents its tested rollback target and path in the [release notes](/blog/release/).
- New capabilities do not touch the on-disk format. Any exception must be explicitly marked as **non-reversible** before you can enable it.
- The [migration guide](/compatibility/migration/) — including how to leave Silo — and the per-component [compatibility audits](/compatibility/) are public and maintained.

## Article 3 · The license is constant, structurally {#license}

Silo is [AGPLv3](/about/license/), forever. There is no CLA and no copyright aggregation: contributions are accepted only with DCO sign-off, so copyright stays with each contributor.
Not relicensing is not a verbal promise — we have made it structurally impossible.

Our reading of the AGPL boundary is itself a public commitment, stated as a position rather than legal advice:
using Silo through its S3 API does not make your application a derivative work. The license will never be used as a threat or a sales instrument.


## Article 4 · Change discipline {#changes}

Changes relative to the upstream baseline fall into four classes only: security fixes, defect fixes, restored community features, and optional additions.
Existing API semantics change only when a security fix demands it, and every such compatibility cost is recorded in the advisory that caused it.
The full divergence from upstream is maintained as a code-verified [compatibility audit](/compatibility/server/).


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

- Vulnerabilities are reported through a [private channel](/about/security/), triaged reproducibly, and disclosed in coordination — writeups are held until the fixed release ships.
- Every security fix is published with a public advisory in the [security chronicle](/blog/security/), including its evidence and its compatibility cost.
- Dependencies are tracked for CVEs, with reachability analysis before any change.
- Every release ships SHA-256 checksums, SPDX SBOMs, Sigstore-signed manifests, and GitHub build provenance.

Severe, remotely exploitable issues are expedited on a best-effort basis, but we do not commit to a specific fix-time SLA.


## Article 7 · Release rhythm {#releases}

Releases ship typically every one to two months, and at most a quarter apart. Security and defect fixes are batched into these releases. The history is [public](/blog/release/); judge the promise against it.

Version tags keep the `RELEASE.YYYY-MM-DDTHH-MM-SSZ` format, and each release documents its upstream baseline.
Deprecations get at least six months' notice with a migration path — except where security requires immediate removal, in which case the removal and its justification are published in the [security chronicle](/blog/security/).


## Article 8 · Upstream relations {#upstream}

We renamed the project out of respect for upstream's trademarks. Upstream copyright, license, and third-party notices are preserved in full: [attribution](/about/attribution/) and [trademark](/about/trademark/).
If upstream resumes accepting contributions, applicable fixes will be offered back as appropriate.

## Article 9 · Continuity {#continuity}

- The repositories live under the [pgsty](https://github.com/pgsty) organization, not a personal account.
- The build is documented and provenance-attested: anyone can rebuild equivalent artifacts from source without us.
- If active maintenance stops for six months, we will say so publicly and archive the project tidily — and make our best effort to keep released artifacts and documentation available.
- Should an established open-source organization — a CNCF-style foundation, for example — want to bring Silo under more formal governance, we would be glad to cooperate.

## Article 10 · The commercial boundary {#commercial}

Everything in the Silo repositories — the server, the client, the console, and the released artifacts — is complete and free of charge, now and in the future.


## Article 11 · Amendment discipline {#amendments}

Additions and strengthenings of this manifesto take effect immediately. Weakening or removing any article requires ninety days' public notice. Article 5 is append-only, always.

The ongoing evidence:

- [Security chronicle](/blog/security/): every investigated CVE and fix, one article per incident.
- [Release notes](/blog/release/): every release, with its baseline, rollback target, and acceptance record.
- [Compatibility audits](/compatibility/): where Silo matches MinIO, and where it deliberately differs.

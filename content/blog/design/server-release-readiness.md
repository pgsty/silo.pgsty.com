---
title: "SILO Server 20260903 Pre-release Review"
linkTitle: "Server 20260903 Review"
date: 2026-09-03
lastmod: 2026-10-18
author: "Ruohang Feng"
summary: >
  The pre-release engineering review of every server change after 20260806: confirmed defects, fixes, complexity tradeoffs, validation evidence, explicit deferrals, and release gates. Includes the #116 restart-and-readback verification method.
tags: [Design, Review, Security, Compatibility, Release]
weight: 8
draft: false
url: "/blog/design/server-release-readiness/"
---

This is the pre-release engineering review behind [SILO 20260903](/blog/release/silo-20260903/) (`RELEASE.2026-09-03T13-18-01Z` at `9b11dc9469e650815b775cb47b039610644f5da4`, reviewed candidate `6e112d1856d4f3655f30fc81ee47e9f43d50d8f3`, against baseline `RELEASE.2026-08-06T00-00-00Z` at `3be10fcc1a44f6620ded0bd303461f9d688cca23`). It records what the second-pass review found after the initial implementation pass, how the fixes were narrowed, and how the release gates were structured. Subsequent September and October releases are covered in [Replication Reliability](/blog/design/replication-reliability/), [Server 20260916](/blog/release/silo-20260916/), and [Server 20261018](/blog/release/silo-20261018/#delivery).

## Why the Second Review Was Necessary {#why-review}

The first implementation pass resolved most reported defects and passed the existing test suite, but passing existing tests did not prove that every security invariant held across all valid wire representations and edge states.

The second-pass review tested each change against seven questions:

- Can the same invariant be bypassed by a different valid wire representation?
- Does a pre-authentication fast path still perform I/O or acquire state?
- What happens when metadata exists but cannot be loaded?
- Do two individually correct read-modify-write paths share the same serialization boundary?
- Does request sanitization preserve all SigV4 streaming state?
- Does a validation record describe the final tree or an earlier commit?
- Is a complex mechanism protecting a reproduced failure, or only a hypothetical future?

That pass uncovered real defects after the first pass and tied every conclusion to a specific invariant and commit.

## Review Result by Area {#review-result}

| Area | Second-pass finding | Final resolution | Status |
| :-- | :-- | :-- | :-- |
| Bucket metadata | Independent config locks could lose updates to the shared `.metadata.bin` record ([#102](https://github.com/pgsty/silo/issues/102)) | One bounded `metadata.lock` surrounds every whole-record writer, migration, import, adoption, and healing path; changed-field replication avoids stale whole-record replacement | Closed in candidate |
| Bucket creation | `ForceCreate` and site adoption could replace existing config with defaults | Preserve existing records and update only creation/adoption state; add regression tests for clobbering | Closed in candidate |
| Object Lock | Comparing lock-document bytes with one canonical XML document missed valid configurations carrying a Default Retention rule | Parse Object Lock first, then derive the versioning invariant from the parsed enabled state; verify update, read-back, and disk reload | Closed in candidate |
| Pre-auth CORS | Arbitrary path segments could cause metadata reads and cache growth | CORS lookup reads resident metadata only and does no object-layer I/O | Closed in candidate |
| CORS startup | A nonresident name could fall back to global CORS before metadata initialization | Preserve an explicit fail-closed startup state | Closed in candidate |
| CORS load failure | Forgetting that a real bucket failed to load made it indistinguishable from a nonexistent bucket and exposed the global fallback to pre-signed requests | Maintain a bounded failed-bucket set, clear it on every successful load/remove/refresh path, and keep those buckets fail-closed | Closed in candidate |
| CORS recovery | A successful on-demand `GetConfig` reload did not initially clear the load-failure bit | One-line final fix `84e1580a4` plus targeted race coverage | Closed in candidate |
| Replication trust | Presence of client-controlled internal headers enabled privileged behavior in multiple handlers | Authenticate first; require an exact marker plus `s3:ReplicateObject` or `s3:ReplicateDelete`; carry a private context decision; sanitize untrusted headers afterward | Closed in candidate |
| Streaming uploads | The sanitized request clone did not initially share the original trailer map | Preserve the trailer map so late-arriving streaming checksums remain visible | Closed in candidate |
| Snowball | A request-wide trust bit could leak between extracted entries | Derive and isolate trust per entry; preserve request defaults across workers | Closed in candidate |
| SSE-C | Zero-byte reads and `GetObjectAttributes` could skip customer-key authentication | Require a successfully unsealed key, with a separate authorized-replica exception | Closed in candidate |
| Delete authorization | Explicit version deletes checked the ordinary delete action instead of requiring `s3:DeleteObjectVersion` | Align single and multi-delete authorization, keep replication deletes on `s3:ReplicateDelete`, and preserve auth/audit context | Closed in candidate |
| Admin authorization | User/group status changes always checked the enable action | Check the action that matches the target state | Closed in candidate |
| Checksums | Multipart and copy paths omitted fields, accepted invalid combinations, or computed over the wrong representation | Complete algorithm/type validation, server-side part calculation, federated propagation, AWS errors, and CopyObject transform ordering | Closed in candidate |
| Release evidence | Full acceptance initially described a tree that changed afterward | Record full acceptance at `ebac0ca73` and current-tree targeted gates separately | Closed as an evidence defect |

## The Invariants That Define the Candidate {#invariants}

### Trust Is Derived Once, After Authentication {#trust-invariant}

An internal-looking header is still client input. The request must first pass the existing authentication path in its original signed form. Only then can the handler combine:

1. an exact, single replication marker;
2. a non-anonymous authenticated identity;
3. `s3:ReplicateObject` or `s3:ReplicateDelete` on the addressed resource;
4. replica status where the narrower replica-only semantics require it.

The result lives in private request context. Header stripping is defense in depth for legacy consumers, not the source of authority.

This ordering matters because SigV4 may sign the headers. Sanitizing first would reject legitimate replication with `SignatureDoesNotMatch`. The sanitized clone also has to share the request trailer: trailers arrive after the initial header parse and carry streaming checksums.

The complete receiver-wide model is in [No I/O Before Auth, No Privilege From Headers](/blog/design/cors-replication-trust/).

### A Shared Record Has One Write Boundary {#metadata-invariant}

Policy, lifecycle, SSE, tags, quota, replication, Object Lock, versioning, and CORS are logical fields but physical members of one bucket record. A per-field mutex cannot protect a whole-record read-modify-write.

Rather than introducing a separate database or transaction layer, the fix serializes bucket-record updates under one bounded lock:

```text
acquire metadata.lock
  load or reuse current record
  mutate the requested field
  parse/normalize the complete record
  persist atomically
  publish the in-memory record
release metadata.lock
```

The lock does not cover object data I/O and is bounded to a bucket-metadata operation. Migration and healing participate because they also replace the whole record. Replication receivers merge only changed fields so an older remote snapshot cannot erase unrelated local state.

### Distinguishing CORS Load Failure from Absence {#cors-failure-invariant}

The CORS hot path must distinguish four states:

| State | Result |
| :-- | :-- |
| Metadata system not initialized | No CORS headers |
| Known real bucket whose metadata load failed | No CORS headers |
| Resident bucket with a bucket CORS document | Evaluate that document |
| No resident metadata and no known failure | Use the server-wide fallback |

The second row is why the failed-bucket set is required. A pre-signed URL is already authorized by its signature and may access a private object without bucket-policy evaluation. In that case the bucket CORS document is the browser-origin boundary. Losing the failure bit and using a permissive global fallback would weaken that boundary.

The set remains bounded by real bucket load attempts and is maintained through `noteLoadFailure` and `clearLoadFailure`. Successful load, removal, stale-bucket cleanup, refresh, reset, and concurrent load all have tests.

### Semantic Object Lock Normalization {#object-lock-invariant}

Any valid enabled Object Lock configuration implies versioning. XML whitespace, element order, and the presence of a Default Retention rule do not change that meaning. Normalization therefore follows XML parsing rather than a byte comparison against one canonical document.

The resulting versioning record is plain `Enabled`. A suspended state and an exclude-prefix extension are incompatible with the lock invariant and are removed on update, read-back, and reload.

## Complexity Audit {#complexity-audit}

The pre-release pass audited the diff for over-design, duplication, defensive code without a threat model, and stale compatibility machinery.

### Complexity Retained Because It Protects a Reproduced Failure {#retained}

- **One metadata lock:** a deterministic cross-type lost-update test reproduced data loss.
- **CORS tombstones:** site replication cannot distinguish deletion from "never observed" without them.
- **CORS load-failure state:** a pre-signed URL provides an authenticated, policy-independent counterexample.
- **Two replication trust levels:** ordinary replication and replica-ciphertext/SSE semantics do not use identical wire shapes.
- **Post-authentication sanitization:** sanitizing before SigV4 verification breaks legitimate signed requests.
- **Multi-pool/null-version edge-case tests:** single-pool happy paths do not exercise the state-selection failures they caught.

### Complexity Removed or Narrowed {#removed}

- CORS failure-set mutations were centralized in `noteLoadFailure` and `clearLoadFailure`.
- The replication import path applies changed fields rather than copying an entire possibly stale record.
- Obsolete encryption helpers, dead event-target functions, and abandoned handler branches were deleted.
- The compatibility guard stopped inventorying every exported source symbol and now protects the actual served routes and frozen wire/configuration surfaces.
- The old `wait_pipe` lint exemption was removed; `gomodguard_v2` replaced deprecated configuration.
- Dynamic timeout tests no longer call global `rand.Seed` from a parallel package.
- The server returned from the temporary `silo-go` fork to the reviewed upstream-compatible `minio-go` revision.

### Changes Deliberately Not Introduced {#not-introduced}

- no generic metadata transaction framework;
- no second CORS cache or unbounded negative cache;
- no new public "trusted replication" request header;
- no cross-repository release gate that makes the server depend on a later Console or documentation release;
- no partial conditional-delete contract in the release candidate;
- no broad rewrite of inherited site-replication registers without dedicated convergence tests.

## Deferrals and Why They Do Not All Have the Same Severity {#deferrals}

| Item | Classification | 20260903 release decision (and subsequent status) |
| :-- | :-- | :-- |
| Conditional delete [#10](https://github.com/pgsty/silo/issues/10) | Inherited missing S3 feature; affects callers that assume `If-Match` / per-object ETag is enforced | Documented for 0903; single-object conditional delete later shipped in 20260916 (#145), while batch ETag deletion remains open |
| Multi-site config deletion [#77](https://github.com/pgsty/silo/issues/77) | Inherited convergence defect for policy/SSE/tags/quota; CORS has its own fixed register | Documented deployment condition for 0903; later repaired in 20260916 |
| `ListMultipartUploads` [#79](https://github.com/pgsty/silo/issues/79) | Inherited listing-conformance gap | Known issue; not a data-integrity blocker for ordinary multipart workflows |
| Federated `CopyObject` [#99](https://github.com/pgsty/silo/issues/99), [#100](https://github.com/pgsty/silo/issues/100) | Legacy-backend checksum/inline-object gaps | Scoped to affected federated features in 0903; later repaired in 20260916 |
| ILM relocation PR #60 and broad SSE issue #61 | New capability requests | Outside the release safety boundary |

## Evidence {#evidence}

### Full Acceptance Tree {#full-acceptance}

The full local acceptance run targeted `ebac0ca73bbf251b070bb6df4d8005015841f901`:

- full `cmd` and `internal` suites;
- complete `cmd` race suite: 365.448 seconds, pass;
- lint: 0 issues;
- rebrand/compatibility and generated-file guards;
- `govulncheck` with no reachable vulnerability;
- six `make verify` deployment shapes: 174 PASS / 0 FAIL.

The first two `make verify` runs hit environment/setup issues while fetching `mcli`, not test failures. The passing run used the locally checksum-pinned `mcli`, retained the outbound proxy for GitHub downloads, bypassed it for localhost, and placed GNU userland tools first in `PATH`.

### Post-Acceptance Candidate {#post-acceptance}

The only code change after that full run was `84e1580a4`, which clears one CORS failure-state bit after a successful on-demand metadata reload. The candidate merge added no code; `6e112d185` changed only Helm release metadata and documentation. On the final candidate, the following checks passed:

- `git diff --check`;
- targeted CORS and Object Lock `go test -race`;
- rebrand guard;
- generated-file check;
- lint with 0 issues;
- Helm lint, default and optional renders, chart packaging, and the seven-resource legacy-upgrade identity guard.

## Go, No-Go, and Ownership of the Release Gates {#decision}

### Code Decision: GO {#code-go}

All confirmed code defects from both review rounds were resolved in the candidate. Each fix was verified at the layer that owns its invariant, and every retained mechanism corresponds to a reproduced failure case.

### Production Release Gates {#production-conditional-go}

Before publishing `RELEASE.2026-09-03T13-18-01Z`, the candidate cleared seven release gates:

1. candidate commits pushed and reviewed;
2. remote CI and Test Release passing on the pushed head;
3. the release tag pointing at the reviewed chart 7.0.2 / server 0903 / client 0903 release tree;
4. draft artifacts, checksums, SBOMs, attestations, and signed RPMs verified;
5. finalize and Docker release publishing both classic and distroless variants;
6. anonymous download and pull tests passing;
7. release notes updated from the tagged facts and documentation deployed.

### Deployment Considerations for 20260903 {#deployment-conditions}

Operators upgrading to 20260903 must account for three requirements:

- update every node in a distributed cluster within one coordinated maintenance window;
- update every member of a site-replication group before configuring bucket CORS;
- update IAM policies for `s3:DeleteObjectVersion` and user/group status-action separation.

## Restart and Readback Verification (2026-09-11, #116) {#restart-readback}

A follow-up acceptance test ([#116](https://github.com/pgsty/silo/issues/116), run on 2026-09-11) measured bounded restart and readback behavior across four dimensions:

- **Acknowledgement ledger.** Every acknowledged PUT writes to a unique versioned key, and the acknowledgement records the `VersionId`, byte count, and SHA-256 immediately. Readback fetches by exact `VersionId` and asserts all three, ensuring an early confirmation cannot be silently replaced by a later write.
- **Readback timing.** Periodic re-reads run at 15, 30, and 60 seconds after the data canary succeeds, across every peer, and the final check covers writes made both during a single-node outage and after its rejoin.
- **No retry masking.** Each canary carries a hard 60-second deadline covering setup, request, response-body read, and sleep, with SDK retries disabled so a recovery window cannot be masked by client-side retries.
- **Driver topology.** Four Linux/arm64 containers on one host with independent network identities, one drive each (EC 2+2), and `tmpfs` volumes kept mounted by a holder container through the full shutdown; nodes stop in parallel with a 10-second grace period, then start in parallel.

**Admin-endpoint readiness is not data readiness.** The [historical test record](https://github.com/pgsty/silo/blob/82948d63060839f6d18c9da8cfd03e8b6d95bc49/docs/investigations/release-readiness-20260911.md#linux-restartreadback-116) compared 0806, 0903, and the `main` repair build. The `main` build passed the admin readiness check 2.461 s after restart, then required another 14.489 s to complete the first data canary. During that startup window, `admin/health` does not reflect data-plane readiness; upgrade automation must verify actual data-plane operations rather than relying on a fixed sleep.

See the [current component/source matrix](/compatibility/versions/) for the status of all subsequent repairs.

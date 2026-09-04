---
title: "SILO Server 20260903 Pre-release Review"
linkTitle: "Server 20260903 Review"
date: 2026-09-03
author: "Ruohang Feng"
summary: >
  The final adversarial review of every server change after 20260806: confirmed defects, fixes, rejected simplifications, necessary complexity, validation evidence, explicit deferrals, and the distinction between code-level GO and production release.
tags: [Design, Review, Security, Compatibility, Release]
weight: 8
draft: false
url: "/blog/design/server-release-readiness/"
---

This is the durable pre-release engineering record behind [SILO 20260903](/blog/release/silo-20260903/). It explains why an earlier “all issues are solved” assessment was not accepted at face value, what the independent review found, how the fixes were narrowed, and which gates still remained at the review point. The linked release note records the later publication result.

> **Decision:** the source candidate at `6e112d1856d4f3655f30fc81ee47e9f43d50d8f3` is a **code-level GO for remote review**. Production release remains a **conditional GO** until remote CI, Test Release, tag and artifact verification, signing, container publication, and public pull checks complete.<br>
> **Baseline:** `RELEASE.2026-08-06T00-00-00Z` at `3be10fcc1a44f6620ded0bd303461f9d688cca23`.<br>
> **Scope:** SILO Server behavior and its embedded/pinned runtime components. Documentation, the standalone Console, mcli, package repositories, images, and the deployed site are separate deliverables.<br>
> **Publication closure:** the later final tree `9b11dc9469e650815b775cb47b039610644f5da4` was published as [`RELEASE.2026-09-03T13-18-01Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z) on 2026-09-04 after the remote, package, provenance, container, and public-download gates below completed. The conditional decision in this page remains the historical review criterion, not the current release state.

## Why the second review was necessary {#why-review}

The first implementation pass had strong test results and resolved most reported defects. Its conclusion was nevertheless too broad: it treated green tests and a clean worktree as proof that every security invariant had been closed.

An adversarial review asked different questions:

- Can the same invariant be bypassed by a different valid wire representation?
- Does a pre-authentication fast path still perform I/O or acquire state?
- What happens when metadata exists but cannot be loaded?
- Do two individually correct read-modify-write paths share the same serialization boundary?
- Does request sanitization preserve all SigV4 streaming state?
- Does a validation claim describe the final tree or an earlier one?
- Is a complex mechanism protecting a reproduced failure, or only a hypothetical future?

That pass found real defects after the initial “ready” claim. The correct response was not to distrust all prior work, but to narrow every assertion to an invariant and an observed tree.

## Review result by area {#review-result}

| Area | Adversarial finding | Final resolution | Status |
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

## The invariants that now define the candidate {#invariants}

### Trust is derived once, after authentication {#trust-invariant}

An internal-looking header is still client input. The request must first pass the existing authentication path in its original signed form. Only then can the handler combine:

1. an exact, single replication marker;
2. a non-anonymous authenticated identity;
3. `s3:ReplicateObject` or `s3:ReplicateDelete` on the addressed resource;
4. replica status where the narrower replica-only semantics require it.

The result lives in private request context. Header stripping is defense in depth for legacy consumers, not the source of authority.

This ordering matters because SigV4 may sign the headers. Sanitizing first would reject legitimate replication with `SignatureDoesNotMatch`. The sanitized clone also has to share the request trailer: trailers arrive after the initial header parse and carry streaming checksums.

The complete receiver-wide model is in [No I/O Before Auth, No Privilege From Headers](/blog/design/cors-replication-trust/).

### A shared record has one write boundary {#metadata-invariant}

Policy, lifecycle, SSE, tags, quota, replication, Object Lock, versioning, and CORS are logical fields but physical members of one bucket record. A per-field mutex cannot protect a whole-record read-modify-write.

The selected repair is deliberately smaller than a new database or transaction layer:

```text
acquire metadata.lock
  load or reuse current record
  mutate the requested field
  parse/normalize the complete record
  persist atomically
  publish the in-memory record
release metadata.lock
```

The lock does not cover object data I/O and is bounded to a bucket-metadata operation. Migration and healing must participate because they also replace the whole record. Replication receivers merge only changed fields so an older remote snapshot cannot erase unrelated local state.

### Failure is a state, not the same thing as absence {#cors-failure-invariant}

The CORS hot path must distinguish four states:

| State | Result |
| :-- | :-- |
| Metadata system not initialized | No CORS headers |
| Known real bucket whose metadata load failed | No CORS headers |
| Resident bucket with a bucket CORS document | Evaluate that document |
| No resident metadata and no known failure | Use the server-wide fallback |

The second row is why a failed-bucket set survives the simplification pass. A pre-signed URL is already authorized by its signature and may access a private object without bucket-policy evaluation. In that case the bucket CORS document is the browser-origin boundary. Losing the failure bit and using a permissive global fallback would weaken that boundary.

The set remains bounded by real bucket load attempts and is maintained through two helpers. Successful load, removal, stale-bucket cleanup, refresh, reset, and concurrent load all have tests.

### Object Lock is semantic, not textual {#object-lock-invariant}

Any valid enabled Object Lock configuration implies versioning. XML whitespace, element order, and the presence of a Default Retention rule do not change that meaning. Therefore normalization follows parsing, not a byte comparison against one canonical document.

The resulting versioning record is plain `Enabled`. A suspended state and an exclude-prefix extension are incompatible with the lock invariant and are removed on update, read-back, and reload.

## Complexity audit {#complexity-audit}

The pre-release pass explicitly looked for over-design, duplication, defensive programming without a threat model, and stale compatibility machinery.

### Complexity retained because it protects a reproduced failure {#retained}

- **One metadata lock:** retained because a deterministic cross-type lost-update test reproduced data loss.
- **CORS tombstones:** retained because site replication cannot distinguish deletion from “never observed” without them.
- **CORS load-failure state:** retained because a pre-signed URL provides an authenticated, policy-independent counterexample.
- **Two replication trust levels:** retained because ordinary replication and replica-ciphertext/SSE semantics do not use identical wire shapes.
- **Post-authentication sanitization:** retained because sanitizing before SigV4 verification breaks legitimate signed requests.
- **Adversarial multi-pool/null-version tests:** retained because single-pool happy paths do not exercise the state-selection failures they caught.

### Complexity removed or narrowed {#removed}

- CORS failure-set mutations were centralized in `noteLoadFailure` and `clearLoadFailure`.
- The replication import path now applies changed fields rather than copying an entire possibly stale record.
- Obsolete encryption helpers, dead event-target functions, and abandoned handler branches were deleted.
- The compatibility guard stopped inventorying every exported source symbol and now protects the actual served routes and frozen wire/configuration surfaces.
- The old `wait_pipe` lint exemption was removed; `gomodguard_v2` replaced deprecated configuration.
- Dynamic timeout tests no longer call global `rand.Seed` from a parallel package.
- The server returned from the temporary `silo-go` fork to the reviewed upstream-compatible `minio-go` revision.

### Changes deliberately not introduced {#not-introduced}

- no generic metadata transaction framework;
- no second CORS cache or unbounded negative cache;
- no new public “trusted replication” request header;
- no cross-repository release gate that makes the server depend on a later Console or documentation release;
- no partial conditional-delete contract in the release candidate;
- no broad rewrite of inherited site-replication registers without dedicated convergence tests.

## Deferrals and why they do not all have the same severity {#deferrals}

| Item | Classification | Release decision |
| :-- | :-- | :-- |
| Conditional delete [#10](https://github.com/pgsty/silo/issues/10) | Inherited missing S3 feature; dangerous only to callers that assume unsupported `If-Match` / per-object ETag is enforced | Document prominently; do not merge the incomplete PR or a single-only half contract |
| Multi-site config deletion [#77](https://github.com/pgsty/silo/issues/77) | Inherited convergence defect for policy/SSE/tags/quota; CORS has its own fixed register | Not a single-site blocker; deployment condition for users relying on those multi-site deletes |
| `ListMultipartUploads` [#79](https://github.com/pgsty/silo/issues/79) | Inherited listing-conformance gap | Known issue; not a data-integrity blocker for ordinary multipart workflows |
| Federated `CopyObject` [#99](https://github.com/pgsty/silo/issues/99), [#100](https://github.com/pgsty/silo/issues/100) | Legacy-backend checksum/inline-object gaps | Block use of the affected features, not the general server release |
| ILM relocation PR #60 and broad SSE issue #61 | New capability requests | Outside the release safety boundary |

“Inherited” does not mean harmless. It means the defect was not introduced by this change set and should be evaluated against the documented release contract. A deployment that depends on one of the affected paths inherits a deployment-specific stop condition even when the general release remains conditional GO.

## Evidence {#evidence}

### Full acceptance tree {#full-acceptance}

The full local acceptance corresponds to `ebac0ca73bbf251b070bb6df4d8005015841f901`:

- full `cmd` and `internal` suites;
- complete `cmd` race suite: 365.448 seconds, pass;
- lint: 0 issues;
- rebrand/compatibility and generated-file guards;
- `govulncheck` with no reachable vulnerability;
- six `make verify` deployment shapes: 174 PASS / 0 FAIL.

The first two `make verify` attempts encountered environment/setup failures while obtaining mcli, not test failures. The successful run used the locally checksum-pinned mcli, retained the outbound proxy for GitHub downloads, bypassed it for localhost, and placed GNU userland tools first in `PATH`. That distinction is part of the evidence rather than something to hide.

### Post-acceptance candidate {#post-acceptance}

The only code change after that full run is `84e1580a4`, which clears one CORS failure-state bit after a successful on-demand metadata reload. The candidate merge adds no code; `6e112d185` changes only Helm release metadata and documentation. On the final candidate, the following pass:

- `git diff --check`;
- targeted CORS and Object Lock `go test -race`;
- rebrand guard;
- generated-file check;
- lint with 0 issues.
- Helm lint, default and optional renders, chart packaging, and the seven-resource legacy-upgrade identity guard.

This evidence is proportional to a one-line state-transition fix, but the remote CI and release workflows must still run against the pushed tree.

## Go, no-go, and ownership of the remaining gates {#decision}

### Code decision: GO {#code-go}

No confirmed code defect from the two review rounds remains unresolved in the candidate. The fixes are covered at the layer where their invariants live, and the retained complexity corresponds to reproduced counterexamples.

### Production decision: conditional GO {#production-conditional-go}

The server must not be described as released until all of these are facts:

1. candidate commits are pushed and reviewed;
2. remote CI and Test Release pass on the pushed head;
3. the intended tag points at the reviewed chart 7.0.2/server 0903/client 0903 release tree;
4. Draft artifacts, checksums, SBOMs, attestations, and signed RPMs verify;
5. finalize and Docker release publish both classic and distroless variants;
6. anonymous download and pull tests pass;
7. release notes are updated from the tagged facts and the documentation site is deployed.

Any failure in steps 1–6 is a release blocker. A local green suite cannot substitute for them.

### Deployment-specific stop conditions {#deployment-conditions}

Operators should delay even a successfully published release when they cannot yet:

- update every node in a distributed cluster within one coordinated maintenance operation;
- update every member of a site-replication group before using bucket CORS;
- revise IAM policies for `s3:DeleteObjectVersion` and status-action separation;
- avoid or explicitly accept the known #10, #77, #79, #99, or #100 path their workload depends on.

The final conclusion at the review point was intentionally narrower than “everything is fixed”: **the reviewed candidate was ready to enter the release machinery, the remaining limitations were explicit, and production publication was gated by verifiable artifacts rather than confidence.** Those gates later completed for the release linked above; the deployment-specific conditions remain applicable.

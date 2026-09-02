---
title: "No I/O Before Auth, No Privilege From Headers"
linkTitle: "CORS & Replication Trust"
date: 2026-09-01
lastmod: 2026-09-02
author: "Ruohang Feng"
summary: >
  A pre-authentication CORS lookup turned arbitrary path segments into metadata I/O and cache entries, while a client-controlled replication marker acquired privileges across SSE-C reads, source timestamps, checksums, object lock, events, and deletes. This record defines SILO's resident-only CORS hot path, two-level replication trust model, post-signature sanitization boundary, wire-compatibility matrix, and release evidence.
tags: [Design, Security, CORS, Replication, SSE-C, Compatibility]
weight: 12
draft: false
url: "/blog/design/cors-replication-trust/"
---

This record describes the CORS hot-path and replication-request trust repair merged into SILO as [PR #101](https://github.com/pgsty/silo/pull/101) (`938603458` through `04b097fd9`).

> **Status on 2026-09-02:** PR #101 merged into `main` on 2026-09-01 with four follow-up commits: per-entry Snowball trust isolation (`ff44527a3`), request defaults preserved across Snowball workers (`ab3ae99ca`), and replication validity probes that verify the replication permissions (`c9ad74673`) under the rule prefix (`5db7be4ee`). The pre-release cleanup kept the resident-only lookup with its fail-closed startup and load-failure states, dropped only the internal-namespace special case, and made the header-stripped request clone share the original request trailer so streaming-checksum uploads keep working for untrusted requests. Tag, package, image, deployment, and production verification remain separate gates.<br>
> **Scope:** HTTP request interpretation before and inside the S3 handlers. No S3 wire field, object format, bucket metadata format, replication protocol, encryption format, or client command changes.<br>
> **Security properties:** pre-authentication CORS processing performs no object-layer I/O; a header never grants replication semantics by itself; SSE-C ciphertext paths and replica-only metadata require both authentication and the corresponding replication permission.

## Too Long; Didn't Read (TL;DR) {#tldr}

Two bugs looked unrelated:

1. an `Origin` header made the outermost CORS middleware treat the first URL segment as a bucket and synchronously load its metadata before authentication;
2. `X-Minio-Source-Replication-Request` made downstream code believe a request was internal replication merely because the header existed.

They shared the same design failure: **untrusted request shape was allowed to acquire expensive or privileged internal meaning before an authorization boundary**.

The repair establishes two invariants:

```text
before authentication:  parse cheaply; never load bucket metadata
after authentication:   derive one trust decision; downstream code consumes it
```

For CORS, the outer middleware now reads only metadata already resident in memory. For replication, handlers authenticate the original signed request first, authorize the appropriate replication action, and then attach a private trust decision to the request context. Untrusted internal headers are stripped only after signature verification. The context decision—not header removal—is the authority used by option builders, encryption paths, object lock, event generation, and metadata persistence.

## Failure A: pre-authentication CORS amplification {#cors-failure}

`corsHandler` wraps the complete server router. Any request carrying `Origin` reaches it before S3 authentication, request validity checks, and the normal API limiter.

The per-bucket CORS implementation originally called the normal bucket metadata getter:

```text
Origin-bearing request
  -> first URL segment becomes "bucket"
  -> GetCorsConfig
  -> GetConfig cache miss
  -> read .metadata.bin
  -> probe ten legacy config paths
  -> cache a default BucketMetadata record
```

When `.metadata.bin` did not exist, the loader intentionally searched legacy configuration files. With none found, it returned a valid empty metadata record rather than `NoSuchBucket`. The generic getter then inserted that record into `metadataMap`.

An unauthenticated client could therefore vary otherwise plausible names and obtain two effects per distinct value:

- repeated erasure/object metadata reads before the normal request limiter;
- growth of the in-memory bucket metadata map.

Name validation alone cannot repair this. An attacker can generate an effectively unbounded sequence of syntactically valid, nonexistent bucket names. Distributed deployments eventually prune stale map entries during the 15-minute metadata refresh; single-node deployments do not start that refresh loop, so their synthetic entries persist until restart.

## Failure B: a marker header became authority {#replication-failure}

SILO and its MinIO-compatible clients use internal headers to preserve source state during replication. The most important marker is:

```text
X-Minio-Source-Replication-Request: true
```

Before this repair, several paths treated header presence—or its raw string value—as proof that the request was a replication request. That affected more than metadata extraction:

- `GET` of an SSE-C object could set `NoDecryption` and return ciphertext without the customer key to a caller holding only ordinary read permission;
- source ETag and modification time could replace server-generated values;
- source tagging, retention, and legal-hold timestamps could enter last-writer-wins comparisons;
- a past object-lock retention date could be accepted through a raw marker check;
- delete-marker identity and modification time could be supplied by the caller;
- successful object events could be suppressed;
- multipart actual size and encrypted checksum metadata could be injected at completion;
- `X-Amz-Replication-Status` could be persisted from ordinary PUT, COPY, or POST-policy metadata extraction.

The earlier [CVE-2026-34204 repair](/blog/security/cve-2026-34204/) correctly stopped ordinary PUT and COPY from importing the replication SSE metadata that could make objects unreadable. It did not yet provide one authority shared by every reader of the marker, source fields, event state, object-lock exceptions, or multipart completion metadata.

## Selected design {#design}

### One exact marker, two trust levels {#trust-levels}

The marker is accepted only when it appears exactly once and its value is exactly lowercase `true`. Duplicate values, mixed case, and any other value are untrusted.

The handler then derives two related decisions:

| Decision | Requirements | Semantics it may enable |
| --- | --- | --- |
| `trusted` | original request authenticated; non-anonymous principal; exact marker; `s3:ReplicateObject` or `s3:ReplicateDelete` on the addressed resource | source ETag/MTime and source timestamps; actual size and encrypted checksum transfer; event and re-replication suppression; replication delete pool/version pinning |
| `replicaTrusted` | `trusted`, plus raw request status `REPLICA` or a multipart upload whose stored status is `REPLICA` | replica status persistence; replication SSE sealed-key import; SSE-C ciphertext/no-decryption path; replica-only object-lock behavior |

The split is required by the real wire protocol. Not every legitimate replication request repeats `X-Amz-Replication-Status: REPLICA`.

The receiver follows this matrix:

| Incoming shape | Result |
| --- | --- |
| no marker | ordinary S3 operation |
| marker without replication permission | internal fields ignored; operation continues with ordinary semantics |
| `REPLICA` without replication permission | `403 AccessDenied` |
| exact marker + replication permission, no `REPLICA` | `trusted` only |
| exact marker + replication permission + `REPLICA` | `trusted` and `replicaTrusted` |

The explicit `403` for an unauthorized `REPLICA` request prevents a claimed replica write from being silently downgraded into a new ordinary object that may be replicated again.

### Authenticate the original, then sanitize {#signature-boundary}

SigV4 signs request headers. Removing an internal header before authentication would change the canonical request and turn a valid signature into `SignatureDoesNotMatch`.

The ordering is therefore mandatory:

```text
original request
  -> existing signature/authentication path
  -> ordinary S3 action authorization
  -> replication action authorization
  -> derive trusted / replicaTrusted
  -> bind decision to request context
  -> clone and strip untrusted internal fields
  -> option parsing, encryption, object lock, storage, events
```

The audit logger retains the original request. The effective request clone retains public S3, SSE, checksum, object-lock, copy-source, proxy, and replication-validity headers. It strips only internal source/replication controls, including source ETag/MTime/delete-marker/timestamps, replication SSE state, actual object size, encrypted checksum transfer, and the request use of `X-Amz-Replication-Status`.

Header stripping is defense in depth. All privileged consumers use the private context decision or an explicit Boolean; they do not infer trust by looking at the clone.

### Replica status is not generic user metadata {#replica-status}

`X-Amz-Replication-Status` is an S3 response header that MinIO-compatible servers also use as an internal request control. It no longer belongs to the generic supported-request-metadata list.

Ordinary PUT, COPY, multipart initiation, Snowball/PAX extraction, and POST policy cannot persist it merely by submitting the field. The receiver sets `REPLICA` explicitly only in a `replicaTrusted` branch.

This closes a subtle POST-policy path: a form field could previously store `REPLICA`, causing the resulting object to evade normal replication scheduling even though the POST principal never held replication permission.

### Object lock receives an explicit decision {#object-lock}

The object-lock parser used to accept past retention dates when the raw marker header was present. That package now receives `allowPastRetainDate` explicitly from `replicaTrusted` state.

The surrounding handler also uses the same decision when deciding whether an existing compliance/legal-hold version may be overwritten by a replica. This removes an internal-header dependency from the reusable object-lock package.

## Actual replication wire matrix {#wire-matrix}

The design was checked against the silo-go v7.3.1 emitter selected by the server's `go.mod`, not inferred from comments or upstream documentation.

| Operation | Marker | `REPLICA` on this request | Receiver decision |
| --- | --- | --- | --- |
| regular replicated `PutObject` | yes | yes | `replicaTrusted` |
| replicated `NewMultipartUpload` | yes | yes | persist trusted multipart replica provenance |
| replicated `PutObjectPart` | yes | no | `trusted`; `replicaTrusted` only when stored MPU status is `REPLICA` |
| replicated `CompleteMultipartUpload` | yes | no | `trusted`; preserve source ETag/MTime, actual size, and encrypted checksum |
| CopyObject metadata replication | yes | yes | `replicaTrusted` |
| replicated `RemoveObject` | yes | yes | `replicaTrusted` with `s3:ReplicateDelete` |
| batch replication PUT/Complete | yes | no | `trusted`; target credentials must hold `s3:ReplicateObject` |
| proxy/readiness/validity probes | separate probe headers | no marker authority | probe behavior retained; those headers are never stripped by this repair |

Requiring `REPLICA` for every trusted operation would break PutPart, multipart completion, and batch replication. Trusting every marker would recreate the vulnerability. Stored multipart provenance bridges the two requirements for encrypted raw parts.

## CORS resident-only state machine {#cors-state-machine}

The outer CORS middleware must remain cheaper than the request it is about to route. It now calls a dedicated resident-only getter that takes one read lock and examines only in-memory state.

| Bucket metadata state | CORS result | Object-layer work |
| --- | --- | --- |
| resident, valid per-bucket CORS | apply per-bucket rule | none |
| resident, no CORS document | use global CORS fallback | none |
| resident, invalid stored CORS | fail closed; continue without CORS headers and log once | none |
| not resident while startup loading is still running | fail closed | none |
| not resident after startup: real bucket whose metadata failed to load | fail closed | none |
| not resident after startup: reserved, invalid, internal, or unknown name | global fallback | none |

The lookup consults the resident map and a bounded set of real buckets whose metadata failed to load at startup or during a refresh. That set is filled only from disk-derived bucket lists, never from a client path, and a successful load, `Set`, bucket removal, stale-bucket reconciliation, and subsystem reset clear it. Both non-resident states fail closed: a presigned URL is authenticated by its own signature, so the bucket's CORS document is the only origin boundary a browser enforces for it, and answering with the global policy would let a leaked URL be used from any origin. The internal `.minio.sys` namespace no longer has a special case; like any reserved or invalid name it is not a bucket, gets the global fallback, and is rejected downstream.

## Alternatives rejected {#alternatives}

| Alternative | Why it was rejected |
| --- | --- |
| Validate bucket names before the old CORS getter | valid nonexistent names still provide an unbounded attacker-controlled key space and still trigger pre-auth I/O |
| Call `GetBucketInfo` before loading CORS | replaces eleven metadata reads with at least one unthrottled backend operation per attacker name |
| Cache every negative result with a TTL | bounds duration, not attacker cardinality or the initial I/O amplification |
| Strip replication headers before authentication | breaks SigV4 canonical-request verification |
| Reject every request carrying an internal marker | turns formerly ignored extra headers into broad client failures and breaks legitimate marker-only replication calls |
| Require `REPLICA` on every trusted call | breaks replicated PutPart, CompleteMultipartUpload, and batch replication wire behavior |
| Let every handler re-check raw headers independently | recreates inconsistent trust rules and leaves future consumers easy to miss |
| Store a Boolean in `ObjectOptions` but leave events/object lock on headers | produces two authorities that can disagree; the original bug class remains |

## Implementation boundary {#implementation}

The selected change is intentionally layered:

1. a small request-trust module defines exact marker parsing, replication authorization, private context state, and the post-authentication effective request;
2. object option builders parse source fields only when their caller provides trusted state;
3. `DecryptObjectInfo`, event request parameters, multipart completion, delete options, and object lock consume the same decision;
4. handlers calculate trust immediately after their existing authentication path;
5. multipart part handling combines current-request trust with stored MPU replica provenance;
6. generic metadata extraction does not accept replica status;
7. CORS middleware uses a separate resident-only metadata accessor and never calls the load-on-miss getter.

No object-layer API needs to infer HTTP trust. Programmatic internal callers that construct `ObjectOptions{ReplicationRequest: true}` remain unchanged.

## Verification and adversarial review {#verification}

Regression coverage includes:

- hundreds of distinct valid missing bucket names, both actual and preflight CORS requests, with zero metadata reads and no map growth;
- Console, reserved, invalid, startup, internal namespace, and invalid stored CORS paths;
- least-privilege SSE-C GET, HEAD, and GetObjectAttributes callers with correct, missing, wrong-case, and unauthorized markers;
- marker-only batch-style PUT preserving source ETag/MTime only with `s3:ReplicateObject`;
- unauthorized `REPLICA` PUT and DELETE returning `403`;
- POST policy unable to forge replica status;
- object-lock past-date parsing with and without replica trust;
- marker-only CopyObject with SSE-C source headers copying plaintext rather than ciphertext;
- fake marker on an ordinary SSE-C MPU failing instead of storing raw bytes;
- a real in-process SSE-C multipart replication chain: encrypted source, raw ciphertext part, trusted replica initiation, marker-only PutPart and Complete, and exact plaintext recovery with the original key.

The final local tree passed focused and race tests, the complete `cmd` suite, object-lock tests, vet, build, and diff checks.

A separate black-box run started two TLS-enabled SILO instances built from the candidate and enabled real site replication. It verified:

- an SSE-C 4 KiB object;
- an SSE-C 12 MiB, three-part multipart object;
- an SSE-C CopyObject result;
- a replicated delete marker.

Source and target ETag, size, version ID, SSE-C key MD5, decrypted SHA-256, and delete-marker version ID matched; targets reported `REPLICA`.

Two Fable 5 review rounds first corrected the trust model for marker-only batch and multipart calls, then audited the implementation. A final independent Claude Code Opus 5 review reported **GO**, with no P0/P1 findings, and independently reran build, vet, race, object-lock, and full `cmd` tests.

## Compatibility and operations {#impact}

- **Ordinary clients:** no request change. Untrusted internal headers are ignored instead of acquiring internal semantics.
- **Unauthorized claimed replica writes:** requests carrying `X-Amz-Replication-Status: REPLICA` now return `403` where some multipart subpaths previously lacked a uniform check.
- **Batch replication:** destination credentials must include `s3:ReplicateObject`, as documented in the [batch replication requirements](/administration/batch-framework-job-replicate/). Without it, the receiver processes marker-only writes as ordinary writes and does not preserve source ETag/MTime.
- **SSE-C:** ordinary reads still require the customer key. Authorized replica reads may use the raw ciphertext path needed to preserve encrypted bytes.
- **Events:** only trusted replication suppresses replica creation/access events; a forged marker no longer silences them.
- **Object lock:** replica exceptions are permission-derived rather than header-derived.
- **Performance:** CORS removes pre-authentication backend work. Trusted writes add policy checks already required by the replication contract; no additional object pass is introduced.
- **Rolling upgrade:** wire and storage formats are unchanged. New receivers enforce the trust boundary; old receivers remain vulnerable to the old header semantics until upgraded. Per-bucket CORS behavior can therefore differ by node during the rolling window.
- **Rollback:** data written by the repaired version remains readable by the previous version, but rollback reopens both trust defects and restores pre-authentication metadata loads.

## Residual risks and follow-ups {#residual-risks}

- Emit a rate-limited diagnostic when a marker-bearing request lacks replication permission; the safe ordinary fallback is otherwise easy to misdiagnose as an ETag/MTime mismatch.
- Replication validity probes now verify the replication permissions the target credentials need and place the synthetic validation key under the rule prefix (`c9ad74673`, `5db7be4ee`).
- This review covers the named source/replication headers. Other future internal controls must still answer the same question: which authenticated decision allowed this client value to acquire internal meaning?

## Conclusion {#conclusion}

An internal-looking header is still client input. A bucket-shaped URL segment is still attacker input. The durable repair is to stop either one from becoming authority by accident:

> Before authentication, do no backend work. After authentication, derive trust once and pass the decision—not the claim—downstream.

That rule is broader than CORS or replication. It is the boundary future SILO handlers should preserve whenever inexpensive public request syntax meets expensive or privileged internal state.

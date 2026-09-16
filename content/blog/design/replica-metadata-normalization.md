---
title: "Replica Metadata Normalization: What a Trusted Copy May Not Re-Inject"
linkTitle: "Replica Metadata Normalization"
date: 2026-09-16
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  The decision record for PR #194 (fix 4fcdf37ce): trusted replication COPY
  re-extracted raw request metadata through the permissive path, so
  transport-only aws-chunked encodings and GHSA-redacted user metadata came
  back into stored objects. Covers the expected encoding mappings, the
  Snowball behavior change, why upgrading does not repair existing objects,
  and the status of the stored-metadata remediation proposal.
tags: [Design, Replication, S3, Review]
weight: 9
draft: false
url: "/blog/design/replica-metadata-normalization/"
---

This page records the repair of how a trusted replication receiver restores
metadata for a replica, merged into Server main as
[PR #194](https://github.com/pgsty/silo/pull/194) (fix
[`4fcdf37ce`](https://github.com/pgsty/silo/commit/4fcdf37ce), merged as
[`9f3037e941`](https://github.com/pgsty/silo/commit/9f3037e941a49ab4cd8a0eed7c0f01083fbe4bbe)).

> **As of 2026-09-16:** the fix is on verified main
> [`40220bd836cb`](https://github.com/pgsty/silo/commit/40220bd836cbd066ca424fa4dc5dbb90057fb55a). It is
> **not** in the published Server 20260903.<br>
> **Provenance:** the production logic follows PR #187 by Mikhail Khadarenka;
  the merged change keeps that authorship and narrows it to a
  review-validated boundary.<br>
> **Evidence class:** an HTTP-level baseline of 64 leaf cases (44 controls
  passing, 20 defect failures before the fix) against real single-drive and
  16-drive erasure backends, plus counterfactual replay of the same suite
  against the baseline helper. No customer incident is attributed.

## What went wrong {#problem}

The ordinary PUT path normalizes metadata: it strips the transport-only
`aws-chunked` token from `Content-Encoding`, and removes the
`X-Amz-Meta-X-Amz-Unencrypted-Content-Length/-Md5` user-metadata keys that a
GHSA mitigation deliberately deletes. The trusted replication receiver,
however, restored replica metadata by re-running the *same permissive
extractor* with replication allowed — replaying every supported header and all
user metadata from the original request. Concretely, on a trusted replica
write the server could store and later return via GET/HEAD:

- `Content-Encoding: aws-chunked` (a pure transport encoding that must never
  be stored, per the AWS SigV4 streaming rules), or the unsplit
  `aws-chunked,gzip` string instead of `gzip`;
- the two GHSA-redacted user-metadata keys — a partial rollback of that
  mitigation, limited to trusted replica writes;
- for Snowball entries without their own PAX header: the outer archive's
  content-type, cache-control, and user metadata.

The object bytes themselves were not necessarily damaged; the stored metadata
was wrong. The regression was introduced by
[`56fa63bfd`](https://github.com/pgsty/silo/commit/56fa63bfd)
(2026-04-15, the replication header trust boundary hardening, CVE-2026-34204)
— whose trust protection is correct and stays.

## The fix {#fix}

One file (`cmd/handler-utils.go`). The boolean dual-mode helper is deleted:

- the ordinary extractor unconditionally skips replication-only keys;
- a new replica extractor walks only the replication-to-internal header map
  and restores **only** the six replication-scoped fields: the SSE-C sealed
  key material, sealed algorithm, IV, and encrypted-multipart marker (the
  empty marker is honored by key presence), the actual object size, and the
  SSE-C checksum identity mapping;
- it never re-reads ordinary supported headers or user metadata.

Expected stored encodings after the fix:

| Requested encoding | Stored `Content-Encoding` |
| :-- | :-- |
| `aws-chunked` | none |
| `aws-chunked,gzip` | `gzip` |
| `gzip` | `gzip` |

`aws-chunked, gzip` (note the space) still stores ` gzip` with a leading
space, and `gzip, aws-chunked` stores the whole string. These are
**documented status quo**, asserted by tests as such — not claims of repair.

## Operator-visible changes {#behavior}

- Trusted replicas of Snowball entries **without a PAX header** no longer
  inherit the outer archive's ordinary metadata. The six replication-scoped
  fields still apply to authorized entries. This matches ordinary (non-trust)
  Snowball behavior, and no producer in the repository ships the
  auto-extract marker, so nothing in-tree depends on the old inheritance.
- The GHSA-redacted keys are no longer written back on replica restore —
  matching what every ordinary PUT already did.
- Authentication, permission gating, and replication trust semantics are
  unchanged; the ordinary extraction path is byte-for-byte equivalent.
- Rolling back the code reopens the injection path but does **not** repair
  already-stored metadata.

## Upgrade does not fix stored objects {#existing}

An upgrade stops new pollution; it does not scan or rewrite existing objects.
Two consequences matter:

- Objects whose *authoritative source* is still polluted will be judged
  inconsistent after the upgrade and re-selected for metadata replication on
  heal/resync — repeatedly. Fix the authoritative source first, then let the
  copies converge.
- Ordinary S3 self-COPY is not a general remediation API: it can create new
  versions or shift timestamps rather than rewriting one version's metadata
  in place.

### The stored-metadata remediation proposal — status {#remediation}

A design for a *future* operation exists: build an inventory (including
non-current versions, not just the latest), verify by comparing against the
trusted source version or an independent checksum — never by guessing from
the wrong response header, and never by re-decompressing gzip just because a
label says so — process the authoritative source's exact versions first,
then converge copies; keep immutable inventories and metadata backups; use
small validation batches with a rehearsed rollback. Where no supported path
exists for an object, stop and leave it — editing `xl.meta` directly is not a
supported operation.

Any selected procedure must preserve the required version identity and current
version relationship, Object Lock retention/legal hold, tags, replication
state, and encryption context. Check for concurrent changes before writing;
blocked or unverifiable versions stay untouched. A local clone must prove the
chosen operation and rollback before this proposal becomes an executable runbook.

> **This is a design proposal awaiting separate approval, not an executed
> procedure.** No production inventory scan, object write, version change, or
> deployment has been performed as part of it. Treat it as the shape of a
> future runbook, not as a validated one.

## Known limits {#limits}

- The POST-form upload path (`bucket-handlers.go`) calls the low-level
  extractor directly and never normalized encodings; that behavior is
  unchanged and flagged for a separate issue.
- Local verification ran with a test-only capacity accommodation (a full host
  disk); the merged-tree rerun in the R4–R8 integration record covers the
  unchanged-tree case.
- No two-site scheduler, restart, or network-failure acceptance is claimed.

## Verification {#verification}

Regression tests (`TestExtractReplicationMetadata*`,
`TestAPIReplicaContentEncoding`, `TestAPISnowballReplicaContentEncoding`,
plus race-included trust/SSE-C round-trips) cover the mapping table, the six
restored fields, and the ordinary path's equivalence; the counterfactual run
(unchanged tests against the baseline helper) reproduces the 20 defect
failures, demonstrating the tests bite. The upgrade summary lives in the
[component matrix](/compatibility/versions/#september-reliability); the
sibling tag-ordering repair is recorded in [Replicated Tag
Ordering](/blog/design/replicated-tag-ordering/).

---
title: "Audit Historical Replica State"
description: "Inventory stored Content-Encoding by exact version and prepare a bounded historical-state repair."
url: "/operations/replication/replica-metadata-audit/"
weight: 26
icon: fa-solid fa-magnifying-glass
---

Upgrading to the [September replication repairs](/compatibility/versions/#september-reliability)
prevents new errors. It does not rewrite old Content-Encoding, reconstruct lost
tags or establish that historical delete-marker purge work has converged.
[#201](https://github.com/pgsty/silo/issues/201) tracks inventory and recovery
readiness. No affected production installation has been identified by this review.

## Read-only version inventory {#inventory}

Start with stored `aws-chunked` Content-Encoding, the transport token addressed
by [#194](https://github.com/pgsty/silo/pull/194). Inventory **all versions** on
the authoritative site and replicas. Checking only current objects misses
historical versions; a normal COPY can preserve polluted source metadata.

Download and inspect the [read-only inventory script](/tools/replica-metadata-audit.py).
It uses Python 3 and boto3, calls only `ListObjectVersions` and exact-version
`HeadObject`, and emits JSON Lines. It does not read bodies, write objects, edit
storage files or collect credentials. Use an existing protected AWS profile
with `s3:ListBucketVersions` and `s3:GetObjectVersion` permissions on the chosen
scope. This profile is separate from an `mcli` alias. Allow any additional
read-only Object Lock permissions needed to inspect that deployment.

```bash
umask 077
python3 -m venv audit-venv
audit-venv/bin/python -m pip install boto3
audit-venv/bin/python -m pip freeze > audit-requirements.txt
audit-venv/bin/python replica-metadata-audit.py \
  --profile silo-readonly --endpoint-url https://silo.example.com \
  --site site-a --bucket example-bucket --prefix 'review-scope/' \
  > site-a-inventory.jsonl
```

Keep the script revision/checksum, client dependency versions, Server identity,
bucket configuration, chosen prefix and start/end time with the inventory.
Use an empty prefix to cover the entire bucket and repeat for every relevant
bucket/site. Each data version requires one HEAD, so begin with a bounded
prefix and size the scan to the deployment. Listings are not atomic snapshots;
pause relevant changes or compare repeated inventories before any later repair.

The final `summary` row must have `listing_complete: true`. Exit code `0` means
the scan completed without ambiguous rows, **not** that it found no affected
headers; `2` means ambiguous rows remain, and `1` means listing failed. An
interruption or any unexpected failure without a complete summary is incomplete.

| Classification | Meaning and next action |
| --- | --- |
| `confirmed-header` | HEAD returned a well-formed encoding list containing the exact `aws-chunked` token. The proposed header only removes that token. Raw bytes and a supported repair operation still need verification. |
| `ambiguous` | HEAD failed, LIST/HEAD identity or state changed, or encoding tokens are malformed, duplicated or noncanonical. Investigate; never turn a failed HEAD into an empty-header success. |
| `unaffected-header` | This successful exact-version HEAD did not contain the transport token. This says nothing about historical tags, purges, body integrity or another version. |
| `delete-marker` | A listed marker identity, retained for separate purge analysis. It has no object body to normalize. |

Matching is token-based: `gzip, aws-chunked` is a candidate; `my-aws-chunked`
is not the transport token. Mixed encoding retains the other tokens in order.
Case variants and duplicates require manual review. SSE-C versions without
the required key can fail HEAD and remain ambiguous; this tool accepts no
SSE-C keys. Use an approved key-aware read procedure for those records without
placing keys in reports or command history.

## Manifest and private evidence {#manifest}

The script records exact bucket/key/version, listing time/ETag/size, raw and
proposed Content-Encoding, metadata fingerprint and available replication,
encryption and Object Lock fields. User metadata values and KMS key identifiers
are omitted. Object names and version IDs may still be sensitive: retain the
full manifest privately and use stable replacements in shared reports.

```json
{"site":"site-a","bucket":"redacted-bucket","key":"redacted-key-001","version_id":"redacted-version-002","classification":"confirmed-header","content_encoding":"gzip, aws-chunked","proposed_content_encoding":"gzip"}
```

This is an example, not an observed production object. Before approving any
write, enrich the private record with the trusted source/version relationship,
full ordinary/user metadata, exact-version tags, retention/legal hold, SSE mode
and key availability, independent raw-byte checksum and replication state.
Absent fields are unknown until the relevant authorized read confirms them.
The fingerprint detects differences; it cannot restore omitted metadata.

Retrieve raw object bytes without automatic Content-Encoding decompression and
compare them with the trusted source version or an independent known checksum.
Preserve genuine gzip bytes; do not recompress. An ETag alone is not a universal
content checksum, especially for multipart or encrypted objects. If the source
is missing, polluted or otherwise untrustworthy, keep the object unresolved.

## Choose and rehearse a repair {#repair}

1. Establish the authoritative exact version first, then its replicas. In
   multi-way replication, compare every participating source. A still-polluted
   source can make later heal/resync select metadata replication again; this
   does not establish an uninterrupted retry loop.
2. Produce a per-version before/after change list. Remove only the verified
   transport token. Preserve raw bytes, genuine encodings, user metadata, tags,
   Object Lock and encryption requirements.
3. Rehearse the chosen supported operation on an isolated clone with the same
   versioning, Object Lock, SSE and replication configuration. Ordinary self-COPY
   may create a new version and change modification time or replication ordering;
   it is not a generic in-place metadata repair API. If a replacement version is
   required, explicitly document changed version identity and caller impact.
   If no supported safe operation exists, leave the record unresolved. Do not
   edit `xl.meta` or internal drive files.
   Verify the encryption configuration and key availability at each destination;
   an encrypted source alone does not establish encrypted replica storage.
   After any restart, use a designated write/read canary on every serving
   process, including replication targets, before COPY or rollback. Health
   checks and successful reads can precede usable write quorum.
4. Immediately before a write, recheck exact version, ETag, size, metadata
   fingerprint, timestamps, tags and lock state under the chosen write-coordination
   procedure. A read-then-write check alone does not eliminate races; metadata
   changes can leave ETag unchanged. Skip conflicts and re-inventory them.
5. On the clone, verify exact-version HEAD, unchanged raw-byte checksum, all
   retained metadata/locks and eventual replica convergence. Exercise restart,
   delayed old events and the specific rollback operation. A successful local
   COPY response alone is insufficient.
   Check exact version listings at every site and the source replication status
   as well as current-object reads. After rollback, the replacement version must
   be absent from every intended replica; a correct current object can coexist
   with a version still awaiting purge elsewhere.

Keep the immutable manifest, full private metadata backup and a tested rollback
for the selected operation. If it created a new version, rollback must account
for that version and which version is current. Another COPY is not proof of
rollback. Reverting the binary can reopen the original error path and does not
undo prior metadata writes.
If a write fails or its outcome is uncertain, stop and re-inventory the exact
versions before retrying. An automatic COPY retry can create another version;
repeating the request is not a substitute for reconciling its outcome.

## Tags and marker purge {#other-state}

- **Tag loss or resurrection:** compare exact-version tags and available
  revision/audit evidence across sites. An empty tag set can be intentional;
  absence cannot reconstruct a lost tag history. Use an authoritative manifest
  before planning a new tagging operation, which itself advances the revision.
- **Delete-marker purge:** record the expected version, bucket, key and
  modification time alongside purge/MRF status and replication errors. A
  retained marker may be intentional or awaiting outbound replication. A 405
  response alone does not prove that the expected marker was found or purged.
- **Historical IAM revocations:** use the separate [IAM recovery procedure](/operations/replication/iam-upgrade/).

## Validation scope {#validation}

On 2026-09-16 the tool was exercised with a read-only account against actual
Server 20260903 storage, a stopped-storage clone upgraded to build `70c7ec4a9fbf`
(runtime source baseline `40220bd836cb`), and that clone after restart. All three inventories agreed on
21 version/marker records: six confirmed headers, two ambiguous encodings,
twelve unaffected headers and one marker. Fixtures included a non-current
version, null version, unusual object keys, gzip bytes, and SSE-S3 with retention
and legal hold. Original bytes, tags and the verified lock state survived the
upgrade; the old encoding headers also remained, as expected.

A separate clone rehearsal corrected one unlocked current object's encoding
through an explicit replacement COPY. Raw gzip bytes and tags were preserved,
but COPY created a new version and left the original version's header unchanged.
Deleting only that new, unlocked version restored the original current version.
This demonstrates the version/rollback distinction, not a general in-place
repair. That initial setup used one Linux ARM64 process/drive and a static test
KMS key.

An additional rehearsal used three sites, each with two Server processes and
four drives. A stopped Server 20260903 backup was restored into the same
candidate build above, with explicit SSE-S3 bucket defaults and a static lab
KMS key. Two unlocked gzip objects received replacement versions while one
site was offline. After it returned, all six processes served the same new
version IDs, raw gzip bytes, metadata and tags; the source reported replication
`COMPLETED`. Later tag updates to the historical versions remained separate
from the replacement versions. An untouched control retained SSE-S3,
GOVERNANCE retention and legal hold throughout.

| Phase | Observed exact-version inventory at each site |
| --- | --- |
| Old storage and upgraded clone | Three affected original versions. |
| Replacement, offline-site catch-up and cold restart | Two corrected current versions plus the three affected original versions. |
| Delete only the two new unlocked versions, then cold restart | The three original versions remain; both replacement version IDs are absent. |

The completed run checked signed write/read canaries on every process before
both COPY and rollback. Earlier attempts are retained: health/read checks
passed while writes returned `SlowDownWrite`, and a rollback begun immediately
after restart still had replacement versions in peer listings after 180
seconds. That observation does not establish a permanent replication failure;
the longer recovery path for that attempt was not tested. The completed
procedure requires actual write readiness and exact-version convergence.

The multi-site lab ran in one isolated Linux ARM64 container with a shared
clock. It did not validate SSE-C, external KMS, rewriting locked versions,
every delayed-event ordering or a general in-place historical-version repair.
Detailed results and remaining limits are tracked in
[#201](https://github.com/pgsty/silo/issues/201).

The inventory tool is preparation, not a repair engine. Configuration-specific
Object Lock/SSE/replication checks remain tracked in
[#201](https://github.com/pgsty/silo/issues/201). Record any production inventory
and writes separately against a selected deployment and reviewed change list.

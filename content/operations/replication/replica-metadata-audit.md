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
4. Immediately before a write, recheck exact version, ETag, size, metadata
   fingerprint, timestamps, tags and lock state under the chosen write-coordination
   procedure. A read-then-write check alone does not eliminate races; metadata
   changes can leave ETag unchanged. Skip conflicts and re-inventory them.
5. On the clone, verify exact-version HEAD, unchanged raw-byte checksum, all
   retained metadata/locks and eventual replica convergence. Exercise restart,
   delayed old events and the specific rollback operation. A successful local
   COPY response alone is insufficient.

Keep the immutable manifest, full private metadata backup and a tested rollback
for the selected operation. If it created a new version, rollback must account
for that version and which version is current. Another COPY is not proof of
rollback. Reverting the binary can reopen the original error path and does not
undo prior metadata writes.

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

The inventory tool is preparation, not a repair engine. Clone remediation and
configuration-specific Object Lock/SSE/replication checks remain tracked in
[#201](https://github.com/pgsty/silo/issues/201). Record any production inventory
and writes separately against a selected deployment and reviewed change list.

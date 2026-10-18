---
title: "ListMultipartUploads: Default Scan Rollback and Future Design"
linkTitle: "ListMultipartUploads Compatibility"
date: 2026-08-30
lastmod: 2026-10-18
author: "Ruohang Feng"
summary: >
  Records the October 18 targeted rollback: withdraw default global scanning while retaining identity, safety and cleanup repairs; explains capacity limits, switch retirement, legacy tradeoffs, future indexing and related records.
tags: [Design, S3, Compatibility, Multipart]
weight: 35
draft: false
url: "/blog/design/list-multipart-uploads/"
---

> [!WARNING]
> **Release-status correction (2026-10-17):** SILO `RELEASE.2026-10-15T00-00-00Z` was returned to Draft and is not the current public release; the published Server remains 20260916. Historical statements below that 20261015 is published or downloadable are superseded, and its fixes must not be treated as delivered in a public release. 20261018 is being prepared as a tag and draft only. See the [component matrix](/compatibility/versions/) and [download page](/download/).

> [!WARNING]
> **分片列表最新决策 · Latest multipart-listing decision (2026-10-18)**
>
> **English:** The October 18 decision withdraws default persistent scanning, restores cache/exact-key listing, retains identity, safety and cleanup repairs, and does not restore the strict switch. See the [latest decision](https://silo.pgsty.com/blog/design/list-multipart-uploads/#decision-20261018). The rollback is implemented in [`4733e1423`](https://github.com/pgsty/silo/commit/4733e1423cfe703951f52ff9cbd286df2cf9d79d) and remains unreleased. Historical sections retain their named releases' contracts; installed binaries and unrelated upgrade requirements do not change.
>
> **中文：** 2026-10-18 决定定向撤回默认持久扫描，恢复缓存／精确 key 列表；保留身份、安全和清理修复，不恢复 strict 开关。参见[最新决策](https://silo.pgsty.com/zh/blog/design/list-multipart-uploads/#decision-20261018)。回退实现见 [`4733e1423`](https://github.com/pgsty/silo/commit/4733e1423cfe703951f52ff9cbd286df2cf9d79d)，尚未正式发布。旧章节保留对应版本的历史契约，不改变已安装二进制，也不替代其他主题的升级要求。

> **Source integration, 2026-10-17:** The unified-listing repair passed all eight PR checks and merged through [PR #243](https://github.com/pgsty/silo/pull/243) as [`7e9454456`](https://github.com/pgsty/silo/commit/7e9454456ee7065cd1d782fc4498338324a94894). Its default-scan choice is now superseded by the October 18 decision below; it is not included in [Server 20261015](/blog/release/silo-20261015/). Source acceptance does not change installed binaries or container images.

> **Publication update, 2026-09-17:** The September source repairs discussed here shipped in [Server 20260916](/blog/release/silo-20260916/). Its opt-in contract is preserved in the historical section; the unreleased follow-up is described next. Dated source-status and validation records below retain their original scope.


This is the problem, design, and decision record for [SILO issue #79](https://github.com/pgsty/silo/issues/79).

Reading guide: [candidate behavior](#implementation), the [October 18 rollback decision](#decision-20261018), and the [related-document inventory](#related-records). October 17, September and August sections remain historical records.

## Unreleased: restore legacy listing and defer durable enumeration {#implementation}

**October 18 decision: a targeted partial rollback.** Withdraw #243's mandatory persistent scan from public listing, retaining identity metadata, safety checks, default cancellation and cleanup repairs. Do not restore the `legacy`/`strict` runtime switch. This section describes rollback commit [`4733e1423`](https://github.com/pgsty/silo/commit/4733e1423cfe703951f52ff9cbd286df2cf9d79d), which remains unreleased. Documentation updates do not change installed Server 20260916 binaries or their existing contract.

Public `ListMultipartUploads` returns to the two older paths: an empty `prefix` reads the node-local cache; a nonempty `prefix` looks up an exact object key. Restarting or changing serving nodes can omit uploads. True prefix filtering, grouping and cache pagination remain incomplete: `prefix=trips/` does not enumerate `trips/a.mp4`, while `prefix=trips/a.mp4` can find uploads for that object. **These are retained defects, not completion of #79.**

Keep recognition of `MINIO_API_MULTIPART_LISTING` and a startup warning, but ignore its value. Tolerate the obsolete shared `api multipart_listing` key without rejecting startup, discarding other settings or automatically deleting user configuration. Add no replacement switch. **Existing strict users lose optional durable listing and strict cancellation; this upgrade is not behavior-preserving for them.** They must assess workflows that depend on complete discovery. Published older binaries retain their original strict behavior.

The signed `GET /minio/admin/v3/multipart-preflight` diagnostic retains `admin:StorageInfo` authorization and reports `mode: "legacy"` to describe public listing. `complete` and `ready` still describe diagnostic coverage and historical records; they do not gate startup, uploads or public listing. Run diagnostics on demand. They retain scan limits, are not a large-scale cleanup tool and should not be retried indefinitely on failure.

## October 18 decision: withdraw default scanning, retain independent repairs {#decision-20261018}

This decision supersedes the [October 17 choice of persistent listing by default](#decision-20261017). Its analysis and implementation record remain below as history, not the target behavior for this release.

### Restart never deleted the uploads

Upload metadata and parts were already on disk in older versions. Restarting discarded the in-memory inventory, not the uploads; an empty list never proved that storage had been reclaimed. The bucket/object identity fields make records identifiable. They do not turn previously temporary data into persistent data.

The newly introduced failure chain was different: records accumulate on disk; every listing scans the namespace again; a fixed directory-entry budget is exhausted; the request returns 503. Restart preserves those records, so the next request fails again. Other buckets, both directory levels and duplicate entries on each drive consume the same request budget. Reducing `max-uploads` does not reduce discovery work.

100,000 is an implementation budget for physical directory entries, not an S3 upload-count limit or a lifetime count of completed uploads. In one healthy 16-drive erasure set, with each incomplete upload using a distinct key and directories on every drive, 3,126 uploads require approximately `16 × (3,126 + 3,126) = 100,032` entries. Layout and replica differences change that boundary; it is not a universal cluster quota.

Resource protection is necessary. The mistake is making repeated global discovery with this scale boundary the only normal listing path. A passing test that expects `SlowDown` above the limit proves that protection works, not that the workload is supported.

### Implementation provenance and responsibility

Trace the three decisions separately rather than attributing later restrictions to the original contributor:

| Change | Verifiable source |
| --- | --- |
| Store upload identity, discover disk records and paginate globally | mr javad seydi's [original commit `4cbb074cc`](https://github.com/pgsty/silo/commit/4cbb074ccdd3d1fc2453e68f6a18d76abd16e253), incorporated through #198; it did not contain this 100,000-entry budget |
| 100,000 directory entries, two scan slots and a 30-second budget | Subsequent maintenance commit [`143f6970d`](https://github.com/pgsty/silo/commit/143f6970d8639843e19412fe2607bf3bad734bb1), bounding scan resource use |
| Make scanning the only public listing path | Subsequent maintenance commit [`4ed86dfe6`](https://github.com/pgsty/silo/commit/4ed86dfe62ed6e07016885552feebcb59f779631), merged through #243 |

The budget and default switch were subsequent project maintenance decisions, not an upload quota proposed by the original contributor. The integration mistake was making a protected but capacity-limited scanner the mandatory default while its capacity counterexample remained. Maintainers own that tradeoff; the original identity metadata and discovery work retain their value.

### Why a partial rollback

| Option | Benefit | Cost | Decision |
| --- | --- | --- | --- |
| Keep persistent scanning as default | Identified uploads survive restart discovery; uniform prefixes and pagination | Repeated full scans, cross-bucket effects and persistent failure above the budget | Reject |
| Revert all of #243 | Restore the previous default and opt-in strict contract | Restore the switch, two listing/cancellation modes and an option that still has the scan problem | Compatibility-first alternative if all existing strict behavior must survive |
| **Targeted partial rollback** | Remove the new default failure mechanism, retain independent repairs and fewer runtime modes | Retain old listing defects; retire optional strict capability; require a dedicated patch and acceptance | **Selected** |
| Revert all multipart work | Broad return to older code | Lose useful identity, safety and cleanup repairs; larger regression scope | Reject |
| Finish a persistent index before release | Potentially combine discovery, pagination and scalability | Introduce index consistency, recovery and migration work into a maintenance release | Separate follow-up |

Retain the existing bucket/object identity fields in `xl.meta` and their removal on completion, UploadID path validation, successful-abort cache and peer notification, native upload-time parsing and stale-upload cleanup repairs. Preserve current read-quorum validation and best-effort Abort; do not restore the strict branch or claim HTTP 204 confirms deletion of every physical copy. Delayed creation writes can still restore an upload; no persistent creation fence is added.

Retain the scanner and identity-conflict checks for explicit diagnostics. Preserve ordering and pagination tests as a foundation, not evidence that the legacy cache path supports those features. IAM, Object Lock and ordinary object-listing repairs retain their own acceptance boundaries.

### What accumulation can still break

The rollback cuts the chain from global persistent upload count to mandatory discovery and exhaustion of a fixed budget on every public request. Public listing and lower-level exact lookups do not acquire diagnostic scan slots or inherit its 100,000-entry budget, 30-second deadline or admission limit.

This is not unlimited-capacity support. The empty-prefix cache path still traverses, sorts and constructs responses; many active uploads increase CPU, memory and response size. Exact lookup still reads the chosen object's upload directory, so many uploads for one key can be expensive. Other buckets' in-memory records can still increase cache traversal work. Residual parts consume storage, and explicit diagnostics can still exceed their budget or compete with foreground I/O.

Stale cleanup walks disk directories directly rather than discovering records through the public API. The listing budget therefore does not inherently deadlock cleanup. Offline drives, deletion failures and scan time can still delay reclamation. Default 24-hour expiry and six-hour cleanup checks remain unchanged. Do not shorten upload lifetime to reduce listing work, or treat a restart as part-data cleanup.

The separately merged [empty upload-parent cleanup repair](https://github.com/pgsty/silo/commit/0f9199e0c3e768bb7699bd640ddad3d6b5d0628b) is also retained: each cleanup pass attempts to remove emptied hash parents without waiting another expiry period after child deletion refreshed their modification time. Active or unreadable uploads remain. This reduces leftover directories; it does not make full scans scale with page size.

This is an acceptable maintenance-release containment measure: withdraw the newly introduced default failure while documenting the old limitations. Workflows requiring complete inventories for recovery, auditing or bulk cancellation remain unsupported by this solution.

### The reasonable cost of ordering

Sorting is not the direct cause of the hard boundary: directory discovery can exhaust the budget before sorting starts. Removing ordering does not remove discovery I/O, and no CPU profile here establishes that sorting dominates runtime.

A reasonable target is for a page to pay mainly for that page and necessary index access, or to amortize discovery and sorting across a complete traversal. It should not rediscover other buckets and every replica for each page. Top-K selection can reduce memory without reducing full-discovery I/O; a higher budget merely moves the failure point.

Future work can evaluate bucket-scoped discovery, traversal reuse and bounded caches with explicit expiry, concurrent-update and continuation semantics. Large or frequent listings with cross-node and restart behavior require a bucket-scoped ordered persistent index, including its updates on create, complete, abort and cleanup, crash/late-write reconciliation, and rebuild behavior. A continuation token alone cannot turn hashed directories into a key-range index. Match these costs to the required workload rather than expanding the storage protocol during this release.

### Acceptance boundaries {#rollback-validation}

Test populated active caches, real on-disk inventories beyond the old budget, other buckets, many uploads for one key and actual storage reopening separately. HTTP 200 from an empty cache is not sufficient capacity evidence: record returned counts, storage calls, latency and allocation as well. Busy diagnostic slots or an unreadable multipart root must not redirect public requests into global scanning.

Known-ID part upload, completion, cancellation and background cleanup retain their regression requirements. Obsolete configuration must remain tolerated; startup warnings and diagnostic mode must match actual behavior. Evidence applies only to the tested source. Integration, artifact publication and deployment remain separate deliverables.

Local validation on October 18 passed public-entry isolation, known-ID operations after reopening, diagnostic identity/budget/cancellation regressions, relevant race tests, configuration compatibility, lint, generation and compatibility-identifier checks, and the server build. The isolation test returned 503 `SlowDownRead` and `SlowDown` before the change; afterward it returned 200 with no multipart-root scan. A separate four-directory server process verified the ignored strict setting and warning, an actual process restart, resumed upload, completion/readback and cancellation.

Running `BenchmarkMultipartPublicListingCapacity -benchtime=1x` explicitly at rollback commit `4733e1423cfe703951f52ff9cbd286df2cf9d79d` produced the following results using local directories on macOS arm64, without isolation from other local system load. Half of each distinct-key fixture belongs to another bucket. Fixture creation is excluded from request timing.

| Layout and real upload inventory | Request | Returned | Object-layer time | Multipart ListDir calls |
| --- | --- | --- | --- | --- |
| 4 drives, 10,000 distinct keys | Populated cache, max-uploads=1,000 | 5,000 | 1.298 ms | 0 |
| 16 drives, 3,126 distinct keys | Populated cache, max-uploads=1,000 | 1,563 | 0.623 ms | 0 |
| 16 drives, 10,000 uploads for one key | Populated cache, max-uploads=1,000 | 10,000 | 2.453 ms | 0 |
| Same inventory after clearing the cache | Exact key, max-uploads=1,000 | 1,000 | 18.416 ms | 1 |

The 16-drive/3,126 case first confirms that the retained scanner still exhausts its budget, then verifies public-path success. Cache responses exceeding the requested page size demonstrate the retained pagination defect; this is not a pagination repair. Empty-prefix requests after cache loss were also checked to return empty, without treating that as complete-inventory acceptance. The single-key lookup allocated about 11.4 MB, illustrating the legacy path's own scaling cost. These are single object-layer measurements excluding HTTP serialization and network work, not throughput, p95 latency or distributed-production guarantees. The process test uses test mode to permit temporary directories on the root filesystem, not independent physical drives.

### Related documentation {#related-records}

These are the site's articles and reference pages directly connected to this listing repair, maintained in both languages. Unrelated multipart checksum and Object Lock articles are outside this inventory.

| Document | Relationship |
| --- | --- |
| [This ListMultipartUploads record](#decision-20261018) | Main #79 record: August analysis, September contract, October 17 decision and this rollback |
| [SILO Server 20260903 release review](/blog/design/server-release-readiness/) | Classifies #79 as a known listing defect and separates code acceptance from publication |
| [Silo 20260903 release](/blog/release/silo-20260903/) | Records retained prefix and pagination limitations |
| [SILO 20260916 release notes](/blog/release/silo-20260916/) | Published legacy default, opt-in strict behavior and cancellation boundaries |
| [Multi-pool object consistency](/blog/design/multi-pool-object-consistency/) | Related reference distinguishing that repair from multipart listing |
| [LIST recovery and lock cost](/blog/design/listing-recovery-lock-cost/) | Related distinction: ordinary ListObjects recovery is separate from #79 and is not part of this rollback |
| [Compatibility overview](/compatibility/) | Index of listing and upgrade impacts |
| [Server compatibility](/compatibility/server/) | Behavior differences and admin interfaces |
| [Component versions](/compatibility/versions/) | Published versions and subsequent source status |
| [Core settings](/reference/minio-server/settings/core/#multipart-listing) | Retired environment switch, obsolete configuration and diagnostics |
| [S3 API compatibility](/reference/s3-api-compatibility/#differences-from-s3-apis-for-multipart-uploads) | Remaining public listing limitations |
| [IAM upgrade and recovery](/operations/replication/iam-upgrade/) | Historical reference to separate multipart preparation |
| [Contributors](/about/contributors/) | #79 reporter and original #198 contribution; later maintenance choices are separate |


## October 17 implementation: persistent listing (superseded) {#implementation-20261017}

> **Historical record:** The following describes #243 at the time. Its default behavior is superseded by the October 18 decision and is no longer the candidate target.

**This section describes the #79 follow-up candidate, not a published release.** It supersedes the mode-switch design below for builds containing this change. Server 20260916 keeps its documented `legacy`/`strict` behavior. The follow-up removes the switch and makes durable listing automatic, including on an existing cluster.

### What the client sees

`prefix` is an existing S3 string parameter, not a new boolean option. For example, `GET /photos?uploads&prefix=trips/` lists unfinished uploads whose object names start with `trips/`. `GET /photos?uploads&max-uploads=1` lists one entry and returns continuation markers when more entries exist. Both requests now discover the same on-disk records before filtering and pagination; neither depends on a node's upload cache or treats the prefix as an exact filename.

New uploads already store two internal identity fields in their existing `xl.meta`. No additional fields, metadata file, database, index or directory migration are introduced by this follow-up. Conceptually the existing metadata includes:

```json
{
  "x-minio-internal-multipart-v1-bucket": "photos",
  "x-minio-internal-multipart-v1-object": "trips/2026/video.mp4"
}
```

This is an illustration of the metadata map, not the binary `xl.meta` encoding. The map is written with the upload's existing metadata quorum, and completion removes the upload-only fields. Older map-based readers accept unknown entries; this follow-up changes neither the encoding nor the storage format. Reverting the listing change restores the older listing limitations rather than reconstructing missing identities.

### Historical uploads do not block new uploads

The rule depends on the record, not the cluster's installation date:

| Record found on disk | Listing behavior |
| --- | --- |
| Both identity fields are present, valid and match the hashed directory | Include the upload if it matches the requested bucket and prefix |
| Both fields are absent in readable metadata selected through the existing read quorum | Omit that historical upload and continue listing |
| Only one field is present, an identity is empty/invalid, readable copies contradict each other, the hash is inconsistent, or an identified record has an unsupported native upload ID | Return an error; do not disguise damage as historical data |
| Insufficient discovery coverage, unreadable metadata without quorum, timeout or budget exhaustion | Return an error; do not return a successful incomplete page |

An omitted historical upload can still receive parts, complete or abort using its known bucket, object key and upload ID. It is also omitted when a prefix happens to equal its entire key; the public API no longer takes the old exact-key shortcut. Existing stale-upload cleanup is unchanged. It is based on initiation age, not recent part activity, so do not shorten expiry just to clear the historical exception.

There is no backfill, forced drain or preflight gate. Upgrade all writers if every subsequently created upload must carry identity. During a rolling upgrade, an older writer can still create an unidentified upload, and an older serving endpoint can still return its old listing semantics. Restart a paginated traversal after changing serving versions. The documented omission of historical uploads is a compatibility exception: an empty result alone does not prove there is no old unfinished upload on disk.

### Retired configuration and diagnostic API

`MINIO_API_MULTIPART_LISTING` has no effect in this candidate, whatever its value; a startup warning explains that it is ignored. Remove it from deployment configuration when convenient. The obsolete shared `api multipart_listing` key remains tolerated without invalidating other API settings. No new environment variable replaces it. The historical targeted-reset procedure below remains relevant when reverting to a build that rejects that shared key.

The existing signed, read-only `GET /minio/admin/v3/multipart-preflight` endpoint still requires `admin:StorageInfo`. It now reports `mode: "persistent"`. `legacyUploads` counts observed historical records, `complete` says every drive was inspected without scan errors, and `ready` means a complete diagnosis found no historical records. **`ready=false` does not disable listing.** Unreadable or offline copies can still make the diagnosis incomplete; an incomplete count is not proof of absence.

### Cost and remaining boundaries

This follow-up adds no upload-path disk write, RPC, lock, tombstone or secondary index. The two identity fields were already persisted by the earlier implementation. The extra work is on listing: every page traverses multipart directories across pools and sets, reads candidate metadata, sorts and filters the result. Other buckets and skipped historical records still consume scan work. Setting a small page size limits the response, not the discovery work.

The existing limits remain: two concurrent scans per process, 16 identity workers and four full-metadata workers per scan, a 30-second context budget, and 100,000 aggregate returned directory entries. The entry count includes both directory levels and duplicate entries across drives. One upload per unique key on all 16 drives costs about 32 entries, so 10,000 such uploads exceed the budget and return `SlowDown` (503). Retrying without reducing that workload will not resolve a deterministic budget overflow. This candidate fixes listing semantics; it does not claim to solve large-scale enumeration performance. A durable index or a different bounded discovery strategy needs separate performance work and acceptance.

Cancellation keeps the previous **default** read-quorum check, best-effort deletion and first-matching-pool behavior. Retiring the listing switch also removes its optional strict cancellation branch. A caller previously relying on strict majority deletion acknowledgement must account for this change. HTTP 204 is not proof that every physical copy is gone. The delayed-create race remains separate: the default-path fault test demonstrates seven delayed writes plus one offline old copy restoring eight readable copies in a 16-drive/EC:8 set after cancellation. This candidate deliberately adds no creation fence.

Regression coverage includes mixed old/new HTTP pages, delimiter groups, old uploads continued and completed by known ID, invalid/partial identities, read failures, actual storage-layer reopen without an upload cache, multi-set/pool results, removed markers, scan admission and preserved default cancellation. The explicit `BenchmarkMultipartListingCapacity` fixture exercises 1,000 and 10,000 real on-disk uploads, including mixed old/new records and another bucket; its overflow case checks for an error rather than a partial successful response. These local checks do not certify distributed storage latency or foreground upload throughput in production.

## October 17 decision record: unified listing with a historical exception {#decision-20261017}

> **Historical record:** The following describes #243 at the time. Its default behavior is superseded by the October 18 decision and is no longer the candidate target.

**Status: selected design, local validation and PR CI complete; merged into main, unreleased.** This section describes implementation commit `4ed86dfe62ed6e07016885552feebcb59f779631`, accepted through [PR #243](https://github.com/pgsty/silo/pull/243) on October 17, 2026. The merge does not establish a published artifact or production rollout. Server 20260916 and Server 20261015 binaries still use the historical legacy/strict contract below.

### Decision and priorities {#decision-contract}

Use one public listing path: discover uploads from durable metadata, then apply S3 prefix filtering, delimiter grouping, ordering and pagination globally. Omit an individual historical upload only after read validation confirms that both bucket and object identity fields are absent. New-version writers continue using the existing identity fields. Upgrading an existing cluster enables this behavior without a migration switch, backfill or prerequisite drain of every upload.

The priorities are to give identifiable uploads reliable standard API results; preserve the existing upload write path and default cancellation availability; accept a limited exception for temporary historical uploads; and address scan scale and delayed writes separately. **“Minimal and sufficient” refers to this defined listing repair, not completion of every concern in issue #79.**

The old/new distinction follows each record's contents. “Old” means both identity fields are absent, not that the cluster was installed long ago. “New” means the writer persisted verifiable identity, not that a request has a recent date. An upgraded writer on a years-old cluster creates identifiable uploads. During a mixed-version rollout, older writers may still introduce records without identity, so upgrading one server cannot make every upload discoverable immediately.

The decision explicitly gives up a stronger guarantee: a successful response need not include every historical upload on disk. Omission does not delete a record, and clients that know its bucket, object key and upload ID can still operate on it. For new-format candidates, failed required validation remains an error rather than a partial successful page. Existing pool-lifecycle scope and scan limits still apply.

### Why strict existed, and why the switch can now go {#decision-background}

A multipart upload is a task: obtain an upload ID, send pieces of a file and finally confirm completion. `ListMultipartUploads` lists unfinished tasks. It does not list completed objects or the individual parts inside one task.

The previous shortcuts did not provide one authoritative inventory. A request without `prefix` read a node's in-memory cache, which could be incomplete after restart or endpoint changes. A request with `prefix` treated the entire string as one exact object name. Suppose bucket `photos` has three unfinished uploads: `trips/a.mp4`, `trips/b.mp4` and `trips/sub/c.mp4`:

| Example request | Expected result | Old shortcut's problem | Candidate behavior |
| --- | --- | --- | --- |
| `GET /photos?uploads&prefix=trips/` | All three uploads | Looks for the single object named `trips/`, potentially returning nothing | Returns the three matching uploads |
| `GET /photos?uploads&max-uploads=1` | One item and continuation markers | The cache path can return multiple items without working pagination | Returns one item and markers when more results remain |
| `GET /photos?uploads&prefix=trips/&delimiter=/` | Two direct children and group `trips/sub/` | Exact-object lookup cannot produce the prefix groups | Returns two `Upload` entries and one `CommonPrefixes` entry; a group consumes a page slot |
| Repeat those requests after restart | Readable uploads remain discoverable | The memory inventory disappears while uploads remain on disk | Reads persistent state without waiting for cache recovery |

`prefix` has always been a standard S3 string parameter; this work adds no `prefix=true` switch. A paginating client echoes `NextKeyMarker` and `NextUploadIdMarker` as `key-marker` and `upload-id-marker`, letting its SDK URL-encode them rather than inventing upload ID markers. Continuation works even if the marker's upload has completed or been canceled. Under concurrent creation or deletion, successive pages are not a snapshot of one instant.

[PR #198](https://github.com/pgsty/silo/pull/198) had already implemented persisted identity, disk discovery and global pagination, under the name `strict`. This was an algorithm with a stricter completeness policy, not a different S3 API. Because a historical record without identity cannot be assigned to a bucket, the original strict policy rejected the whole listing when it encountered one. A remnant from another bucket could therefore fail the current request.

[PR #213](https://github.com/pgsty/silo/pull/213) subsequently restored `legacy` as the default. A server environment variable let operators enable strict after preparation, while an ordinary upgrade retained the default Abort success threshold. The switch served a **migration and availability choice**; it was never a prerequisite for implementing S3's `prefix` parameter.

This decision changes the historical-record contract: individually omit confirmed unidentified uploads and preserve default Abort availability. That removes the main reason to keep a mode switch while waiting for old uploads to drain. Keeping it would leave the defective default path in place and require operators and tests to maintain two behaviors. Retire it without introducing a replacement migration variable.

### Alternatives and reasons {#decision-alternatives}

The names below distinguish this decision's alternatives. The numbered options in the archived August analysis belong to that earlier comparison.

| Alternative | Benefit | Cost or limitation | Decision |
| --- | --- | --- | --- |
| **One persistent scan; omit individually confirmed unidentified uploads** | An ordinary upgrade fixes prefix and pagination for identifiable uploads, without migration configuration or a second durable state store | Historical inventory is incomplete; each page amplifies reads and remains subject to scan limits | **Adopt.** Meets the requirement to accept a historical exception while making new writes discoverable |
| Keep `legacy` and `strict` modes | Operators can retain old behavior and choose when to switch | Default defects persist; configuration, troubleshooting and test combinations grow; strict still faces historical blockers | Reject. The per-record policy removes the original switching prerequisite |
| Make original strict the default and reject every historical record | Successful responses provide stronger historical completeness | One unidentified record can block all buckets, requiring drain or intervention; lost keys/IDs make this difficult | Reject. Temporary historical data becomes a deployment-wide listing obstacle |
| Backfill every historical identity | An authoritative mapping could restore the full inventory | Directory names contain a one-way bucket/key hash; caches and logs are not guaranteed complete and cannot reconstruct missing names | No general backfill. Targeted recovery with a reliable external mapping is separate work |
| Add a durable ordered index per bucket | Direct bucket/prefix/marker lookup can avoid repeated full discovery | Creation, completion and cancellation must maintain secondary state; atomicity, repair, rebuild and mixed-version behavior need definitions | Defer. Design and validate separately when supported scale exceeds the scanner |
| Repair only the cache, or add a custom `prefix=true` parameter | A small apparent change may help some single-node cases | Does not solve restart, cross-node discovery or persistent pagination; a custom parameter cannot repair standard SDK requests | Reject. It does not provide an authoritative durable inventory |

Combining an index and a cancellation fence with this repair could address more concerns, but it would change the creation/deletion storage protocol and turn a listing fix into a new lifecycle design. Reuse the existing scanner now and keep those follow-ups explicit. Merely increasing the directory-entry limit is not a capacity solution: per-page work, allocation and timeout pressure continue growing.

### Where identity lives, and the compatibility evidence {#decision-storage}

Persistent discovery initially sees directories, not user-visible filenames. The existing layout is schematically:

```text
.minio.sys/multipart/
└── <hash derived from bucket and object key>/
    └── <internal upload ID>/
        ├── xl.meta        ← existing binary metadata file
        └── ...            ← upload state and part-related files
```

The hash can verify that a bucket/key belongs in a directory, but cannot recover the original names. The upload ID does not contain the object key either. The two identity entries illustrated above retain the original bucket and complete object key in the existing internal metadata map inside `xl.meta`, persisted with the existing write. Completion removes these upload-only entries. **Both fields were already written before this follow-up, in both legacy and strict modes. This change does not add two more keys.**

The existing map is intended to hold extensible key/value metadata. This choice changes neither directory names, the binary format version nor mandatory fixed structure fields, and creates no JSON sidecar. A separate identity file would require another write and rules for “main metadata saved, identity file missing” or cancellation leaving one file behind, without a corresponding benefit here.

The compatibility conclusion has a concrete scope. The historical `xlMetaV2Object` and generated MessagePack codec from SILO's August 6 commit `3be10fcc1a44f6620ded0bd303461f9d688cca23` were inspected and extracted for a decode/re-encode check. Its internal `MetaSys` is a `map[string][]byte`; it accepts and preserves both entries without a whitelist of their names. It is not a fixed schema that rejects an unfamiliar map key. Current response-header handling also filters the internal reserved prefix.

This establishes that the tested historical codec does not reject these entries and preserves them when re-encoding. It **does not certify** every old server's recovery, healing and replication paths or every third-party offline parser. Reading the file does not give an older server the new listing behavior; older completion code may also retain internal entries it does not recognize. Release acceptance remains the coordinated PGSTY component stack, with upstream compatibility maintained on a best-effort basis.

### What can be omitted, and what must fail {#decision-read-policy}

“Skip anything whose identity cannot be found” would be too permissive. Corruption, failed reads or inconsistent copies can all look like missing identity. The implementation distinguishes the historical format from an unverified state.

1. Discover upload candidates in pools and sets participating in service, requiring sufficient directory coverage for each set. A pool groups storage resources; a set is a group of drives storing erasure-coded data together.
2. A valid identity on a source drive can exclude another bucket early. Otherwise read metadata using the existing rules and establish read quorum: enough valid copies for the storage layer to confirm that the record is readable.
3. For candidates requiring full reads, also compare identity across the valid copies already returned. The generic quorum selection does not compare these fields. If one copy lacks identity and another has it, or their values disagree, selecting the apparently old copy must not silently hide a new upload.
4. Omit only when both fields are **absent**. Present-but-empty fields, one missing field, invalid identity, a directory-hash mismatch or an identified record with an unsupported native upload ID remain metadata errors. Read or discovery failures remain failures too.
5. Collect identifiable uploads, deduplicate by bucket/key/upload ID, then apply ordering, filtering, grouping and page selection globally. Paginating each drive or pool before concatenation would break order and continuation markers.

The added identity comparison uses metadata already read, adding field lookups and comparisons rather than more disk reads. Because a valid source identity can exclude another bucket early, a normal listing is not a complete corruption audit of every copy in every bucket. Normal enumeration keeps the existing exclusion of suspended pools; preflight inspects them. This work does not redefine their lifecycle.

Read quorum and directory-discovery coverage have different thresholds. For example, metadata in a 16-drive/EC:8 set can be readable from eight copies while discovery requires nine successfully scanned drives, avoiding a false assertion that undiscovered directories do not exist. Refusing a successful response under insufficient coverage is one availability cost of this path compared with the old cache listing.

### Cost: little new write work, substantial listing work {#decision-cost}

The comparison baseline matters. Relative to the code that already contained strict, a new upload still writes the same `xl.meta`, with no extra disk write, RPC, lock, index or durable tombstone. Relative to older code without identity, the two entries add their field names, UTF-8 bucket/key values and encoding overhead to metadata copies. That cost belonged to the earlier implementation.

For deployments previously using default legacy behavior, the public list changes from a cache or single-key lookup to persistent discovery. Read cost increases substantially. A scan's work depends on stored uploads, not merely the number of items in its response.

| Operation | Work and cost |
| --- | --- |
| Initiate, upload parts and complete | No new identity-writing step or secondary state in this follow-up; completion still removes the existing upload identity entries |
| Discover a listing | Each page traverses two directory levels across relevant pools/sets; other buckets and omitted historical records also consume budget |
| Read identity | Usually read one source copy first; target-bucket or uncertain records then use the existing all-drive metadata read |
| Validate, order and paginate | Compare identities already read, retain target-bucket candidates and sort globally in about `O(M log M)` for M uploads entering the sort; discovery candidate sets also consume memory |
| Fetch another page or narrow `prefix` / `max-uploads` | Still rediscover and validate candidates; a narrower prefix or smaller page does not proportionally reduce preceding scan work |
| Preflight | Shares scan admission slots; an on-demand diagnostic, not a migration procedure required on every upload or startup |

For a healthy N-drive set with identical directory layouts, H distinct object-hash directories and U upload directories, discovery returns approximately `N × (H + U)` entries and makes `N × (1 + H)` `ListDir` calls. These are different metrics. A target-bucket or historical candidate usually needs one source read plus N full metadata reads; a valid other-bucket identity usually needs only one source read.

Thus a single page for 10,000 target-bucket uploads with distinct keys on four drives needs roughly 80,000 directory entries, 40,004 `ListDir` calls and 50,000 `ReadVersion` calls. These count storage-interface calls, not necessarily network RPCs or physical disk I/O. Local drives, caching and deployment topology affect the actual cost.

Existing protections remain: two admitted scans per process; 16 identity workers, four full-read workers, a 30-second context budget and 100,000 aggregate returned directory entries per scan. Already issued concurrent calls may finish later, and admission is retained until workers exit. These limits are not exact peak-memory or physical-I/O cutoff guarantees.

**100,000 entries does not mean 100,000 uploads.** On 16 drives with one object-hash directory per upload, about 3,125 uploads exhaust the entry budget; 10,000 require about 320,000 entries and return `SlowDown` (503). Uploads sharing a key share the upper directory cost; other pools and remnant directories change the count too. A smaller page or identical retry cannot resolve deterministic budget overflow.

An October 17 real-filesystem benchmark of the final candidate recorded the first 1,000-item page:

| 10,000 uploads on four drives | Time | `ListDir` calls | `ReadVersion` calls | Go cumulative allocated bytes |
| --- | --- | --- | --- | --- |
| All new-format records in the target bucket | About 2.40 s | 40,004 | 50,000 | 485,925,912 |
| 4,000 new target records, 1,000 unidentified old records, 5,000 new other-bucket records | About 2.42 s | 40,004 | 30,000 | 330,686,136 |

The environment was local macOS arm64, Apple M5 Max and Go 1.27.2, with one iteration per case and fixture creation excluded from timing. Other local validation could be running. Cumulative allocation is not peak resident memory; fewer interface calls did not directly yield a shorter elapsed time in these two observations. These are not distributed production throughput results and cannot be divided by the September Docker measurements to claim a speedup. Reproduce these two final-candidate cases in the server checkout with:

```bash
go test ./cmd -run '^$' \
  -bench '^BenchmarkMultipartListingCapacity$/^drives=4$/^uploads=10000$' \
  -benchtime=1x -benchmem -timeout=10m
```

This command belongs to the October 17 implementation described in this section. After the October 18 rollback, the retained scan benchmark is named `BenchmarkMultipartDiagnosticScanCapacity` and covers diagnostic scanning only. Public listing uses `BenchmarkMultipartPublicListingCapacity` above; the two are not evidence for the same request path.

### Why “reappears after cancellation” is separate {#decision-abort}

Listing and cancellation are related but distinct. A reliable list discovers uploads that still exist. Guaranteeing that no in-flight creation can restore an upload after successful cancellation requires creation and cancellation to share a durable ordering rule.

For example, creation has issued writes to several drives. Some calls time out while physical writes continue. Cancellation deletes records currently visible, then delayed writes reach disk and restore readable copies. The default-path fault test preserves a concrete counterexample: in a 16-drive/EC:8 set, nine drives finish creation and seven writes are delayed. One completed drive goes offline; cancellation reads and cleans the other eight. After the seven delayed writes complete and the offline drive returns, its old copy brings the total back to eight readable copies. This demonstrates renewed readability, not achievement of the nine-copy write quorum.

Increasing deletion acknowledgement alone cannot fence creation writes still in flight. A real fence might use a durable tombstone or generation marker so a late writer can learn that an upload ID was canceled. Its drive coverage, retention, offline-drive recovery and old-node behavior all need definitions. That adds persistent state and coordination to the creation/cancellation hot paths and requires separate design, fault testing and acceptance.

This repair retains the previous default read-quorum check, best-effort deletion and pool-order return behavior to avoid reducing ordinary deployments' cancellation availability. The optional strict majority-delete and remnant-retry branch retires with the switch. **Users who explicitly enabled old strict lose that stronger acknowledgement behavior**; it would be inaccurate to claim unchanged cancellation semantics for everyone. HTTP 204 can also acknowledge an already nonexistent upload and is not proof of physical drain.

### Changes and affected surfaces {#decision-changes}

| Surface | Change | Reason and consequence |
| --- | --- | --- |
| `cmd/erasure-server-pool.go`, `cmd/erasure-sets.go`, `cmd/erasure-multipart.go` | Route public listing through persistent discovery; remove mode branches and public exact-key/cache shortcuts; retain default Abort | Public entry points share one listing algorithm; an exact-looking prefix no longer retrieves an unidentified historical record as a special case |
| `cmd/erasure-multipart-listing.go` | Individually omit confirmed unidentified records, compare valid copies' identities, report diagnostic mode `persistent` | Historical records do not block new ones; damaged or conflicting identities still fail; preflight no longer enables or disables the feature |
| `internal/config/api/api.go`, `cmd/common-main.go` | Warn about the retired environment variable, tolerate obsolete shared configuration, remove mode selection | No replacement switch; operators can remove the old variable, other API settings survive, shared configuration is not automatically rewritten |
| Regressions and capacity benchmark | Cover mixed formats, HTTP parameters, restart, pagination, metadata failures, default cancellation and scan limits | Both promised behavior and known counterexamples remain checkable |

The internal exact-object helper remains necessary for placement when initiating uploads; removing its public-list use is not a reason to delete it. Cache maintenance and peer notifications also remain to limit mixed-version protocol changes. The public result no longer reads `mpCache`. Retaining this compatibility code is deliberate; subsequent cleanup need not be part of the functional repair.

The main affected surfaces are unfinished-upload discovery, cleanup tools and operational inventory. Standard SDKs need no new parameters. Callers must use the existing pagination protocol rather than assume a complete single response, and handle actual scan failures. This does not change completed-object listing/reads, upload data formats or authorization rules. An empty list still cannot establish that unidentified historical uploads have drained.

### What validation establishes, and what remains open {#decision-evidence}

| Completed check | Supported conclusion | Stronger conclusion it does not support |
| --- | --- | --- |
| Mixed-format HTTP lists, prefix, delimiter, global pagination, deleted markers, multiple sets/pools, known-ID continuation and completion of old uploads | Automated regression coverage for the defined listing and historical compatibility behavior | Snapshot consistency across concurrent pages |
| Storage-layer reopen and real-server process restart with boto3 and PGSTY mcli | New-format discovery does not depend on the process cache; standard client flows work | Certification of every historical or third-party client |
| Missing, damaged and conflicting identities; read quorum; directory coverage; admission; slot retention after cancellation | Unverified states fail rather than become partial successful pages; resource protections have regression coverage | No timeouts, exact peak-memory limits or unlimited capacity |
| Default Abort failure tests and the delayed-create counterexample | Default availability is retained and the known race remains observable | A repaired delayed-create race or physical drain guaranteed by 204 |
| Focused tests and race checks, repository tests with `kqueue,dev` tags (51 packages containing tests), `make verifiers` and build | The candidate passes local functional, race and project checks | Acceptance for every production topology, workload and long-term recovery scenario |
| Initial four-/sixteen-drive, 1,000-/10,000-upload capacity matrix; the two final cases above rerun after adding cross-copy validation | Real directory cost and overflow evidence, with reproducible final-case measurements | Every matrix case rerun on the final revision, or no production foreground-load impact |

These results come from local candidate validation. The document retains verifiable conclusions rather than publishing raw execution logs. Historical omission, capacity limits and late writes remain explicit boundaries even when the tests pass.

### Upgrade procedure and reasons to revisit {#decision-followup}

After a release includes this change, upgrade all serving and writing nodes through the normal process and restart paginated traversals. No historical-upload drain is required first. Remove the ineffective `MINIO_API_MULTIPART_LISTING` variable without setting a replacement. Use read-only preflight when historical inventory matters: `ready=false` indicates historical records or incomplete diagnosis, not a disabled new listing feature.

Old uploads with known identity can still continue, complete or be canceled; existing expiry cleanup remains available. Do not create a migration deadline by shortening expiry, because age is measured from initiation and active long uploads are affected too. Reverting the server restores that version's listing and switch behavior. If the target build rejects a previously persisted shared `api multipart_listing` key, follow the historical targeted-cleanup procedure rather than resetting the entire API configuration.

Revisit the decision under these conditions:

- The product must enumerate every historical upload without omission: obtain an authoritative identity-recovery source or establish actual drain; renaming a switch cannot deliver that guarantee.
- Supported scale exceeds the budget, or page latency/foreground-upload impact is unacceptable: define acceptance with drive counts, bucket distribution, active uploads, concurrent pagination and foreground load, then choose an index or another discovery structure.
- Successful cancellation must prevent any delayed creation from restoring an upload: design a separate creation/cancellation fence covering offline copies, recovery and mixed versions.
- Suspended-pool visibility must change, or full rollback to a particular old version is promised: add the corresponding pool-lifecycle or version-specific end-to-end compatibility acceptance.

Retain the defined scope: ordinary upgrades should gain reliable listing for identifiable uploads; historical omission and scan cost should be explicit; capacity and cancellation fencing remain separate unfinished work. Neither this decision nor the candidate commit establishes complete closure of issue #79.

## Historical: September 16 implementation and upgrade contract {#implementation-20260916}

> [!WARNING]
> **分片列表最新决策 · Latest multipart-listing decision (2026-10-18)**
>
> **English:** The October 18 decision withdraws default persistent scanning, restores cache/exact-key listing, retains identity, safety and cleanup repairs, and does not restore the strict switch. See the [latest decision](https://silo.pgsty.com/blog/design/list-multipart-uploads/#decision-20261018). The rollback is implemented in [`4733e1423`](https://github.com/pgsty/silo/commit/4733e1423cfe703951f52ff9cbd286df2cf9d79d) and remains unreleased. Historical sections retain their named releases' contracts; installed binaries and unrelated upgrade requirements do not change.
>
> **中文：** 2026-10-18 决定定向撤回默认持久扫描，恢复缓存／精确 key 列表；保留身份、安全和清理修复，不恢复 strict 开关。参见[最新决策](https://silo.pgsty.com/zh/blog/design/list-multipart-uploads/#decision-20261018)。回退实现见 [`4733e1423`](https://github.com/pgsty/silo/commit/4733e1423cfe703951f52ff9cbd286df2cf9d79d)，尚未正式发布。旧章节保留对应版本的历史契约，不改变已安装二进制，也不替代其他主题的升级要求。

[PR #198](https://github.com/pgsty/silo/pull/198) retains mr javad seydi's original metadata-and-scan contribution and adds maintainer fixes for disappearing markers, incomplete discovery, cancellation confirmation and upgrade diagnostics. The pre-release compatibility follow-up restores `legacy` as the default and makes strict mode an explicit process-environment opt-in. This section describes those source changes. **It is not included in Server 20260903, and does not establish production performance or deployment acceptance.** The August 30 analysis below remains a historical design record.

### Listing and cancellation

New uploads persist their bucket and object key in the existing `xl.meta`; completion removes these upload-only fields. Strict listing discovers durable uploads across pools and sets, verifies metadata with the existing read quorum, and applies prefix, delimiter, `CommonPrefixes` and a global page limit of at most 1,000. Restarting a node or choosing another endpoint does not depend on rebuilding its upload cache.

Ordering is `(key, initiation time from the native upload ID, encoded upload ID)`. A returned marker defines this boundary even after the corresponding upload is completed or canceled. This supports clients that echo the server's markers; it does not promise arbitrary lexical comparison of random upload IDs. There is no snapshot across pages under concurrent mutations. Without `key-marker`, `upload-id-marker` is ignored. With a key marker, invalid base64 retains the existing 404 response; a decodable but unsupported native ID returns 400. Unsupported persistent IDs are legacy records, never assigned a fabricated current initiation time.

Directory discovery requires `floor(N/2)+1` successful drive scans per set. For example, two available drives out of four are insufficient and return 503, even when metadata could still be read from two copies. A source-drive identity read may exclude another bucket only after validating its bucket/key hash; uncertain identities require a quorum read. Strict mode returns `MultipartListingNotReady` (503) for legacy records and `MultipartListingMetadataInvalid` (503) for invalid identities. It never silently switches the whole request to cache-based listing.

In default `legacy` mode, Abort retains the released read quorum, best-effort cleanup and pool-order return behavior, avoiding new 503 responses for previously successful cancellations. In `strict` mode it checks every relevant pool and requires `floor(N/2)+1` deletion acknowledgements per set. Remnants below read quorum can still be retried. When a majority was already absent but remnants were observed, those observed copies must be cleaned successfully; successful responses from empty drives cannot mask their deletion failures. Unknown pools or insufficient confirmations still return 503.

In both modes, an Abort with the wrong key or bucket cannot evict another valid upload's cache entry. The S3 HTTP layer retains its existing idempotent response: a nonexistent upload also returns 204; malformed input, authorization and quorum errors remain errors. **204 does not prove that every physical copy has been deleted.** Offline part data may still need later cleanup.

**Unresolved creation-write boundary:** these confirmations do not fence a physical creation write that continues after its caller receives a storage timeout. A fault-injection test reproduces a 16-drive/EC:8 case where seven delayed writes and seven offline old copies restore a writable upload after acknowledged cancellation. The test preserves this known limitation; its passing status is not a repair claim. A durable creation fence needs a separate storage-consistency design.

### Coordinated upgrade

**The default is `legacy`**, retaining the old exact-key/cache listing limitations. An ordinary upgrade does not require pausing production or draining uploads to enable the new listing. The mode is read only from the server process environment, `MINIO_API_MULTIPART_LISTING=legacy|strict`; no shared configuration key is added. An unset value selects `legacy`. An invalid value logs a diagnostic and falls back to `legacy` while preserving other API settings. Do not set this mode with `mcli admin config set`.

Only before opting into strict mode must operators upgrade **all writers**, stop introducing old-format uploads, finish or abort legacy uploads using known keys/IDs, run the read-only preflight below, and verify scan capacity against their workload. Once these checks pass, set `MINIO_API_MULTIPART_LISTING=strict` in every server's service environment and restart; check the effective mode at each endpoint. Restart paginated traversals after changing modes. Issue #79 remains open for the default listing limitations; this batch does not claim a complete repair.

If a development build already persisted `api multipart_listing`, back up configuration and record API values, upgrade all configuration writers to the patched version, prevent concurrent configuration writes, then remove only that historical key:

```bash
mcli admin config reset ALIAS api multipart_listing
mcli admin config get ALIAS api
```

The patched server ignores the historical key's mode value without automatically rewriting shared configuration or deleting history. The config get/export views omit retired keys, so their absence from those views alone does not prove deletion. Require a successful targeted reset, then verify preserved values after restart and during a controlled rollback check; do not reset the whole `api` subsystem. A development build can reintroduce the key on its next configuration write, and history containing that key should not be replayed directly. Existing API values can temporarily be pinned through their corresponding environment variables where needed, but that does not replace persistent cleanup. This procedure covers this API configuration change only; other rollback constraints require separate checks.

The read-only, SigV4-authenticated endpoint `GET /minio/admin/v3/multipart-preflight` requires `admin:StorageInfo`. For example, with credentials and an endpoint supplied by the operator:

```bash
curl --aws-sigv4 'aws:amz:us-east-1:s3' \
  --user "$SILO_ACCESS_KEY:$SILO_SECRET_KEY" \
  "$SILO_ENDPOINT/minio/admin/v3/multipart-preflight"
```

The report contains `mode`, `ready`, `complete`, `scannedEntries`, `legacyUploads`, and per-pool/set drive coverage, uncovered drive indexes and oldest legacy initiation time. It bypasses upload caches, inspects even suspended pools and detects minority legacy copies. `ready=true` requires every drive to be inspected, no unreadable candidate metadata and no observed legacy copies. It cannot attest that every writer has been upgraded or that no concurrent writer will introduce a legacy record. Offline drives, scan errors, timeouts and budget exhaustion prevent readiness; an incomplete count is not a zero count. Rerun after drives return and before enabling strict mode.

For uploads whose original key/ID has been lost, the existing stale-upload cleanup scans each server's local drives. Age is measured from creation, **not recent part activity**. Retain the existing cleanup policy, wait and verify actual drain; the default 24-hour expiry and 6-hour interval do not guarantee drain completion. Do not shorten expiry to accelerate an ordinary upgrade, since this can also remove active long-running uploads. Continue using default `legacy` mode if drain cannot be established. This batch changes neither cleanup policy nor the available deletion APIs.

The shared `maxUploadsList` cap changes from 10,000 to 1,000 in both modes; clients that assumed one response contained everything must paginate.

A legacy upload lacks bucket/key identity and cannot safely be excluded as belonging to another bucket, so it can block strict listing for any bucket. A valid new-format identity belonging to another bucket can be filtered earlier. This does not impose deployment-wide 503 responses on default legacy listing.

### Scan capacity and evidence limits

Each process admits two scans, with 16 identity workers and four full-metadata workers per scan. Directory reads pass a finite count with overflow detection. The aggregate budget is 100,000 returned directory entries, including repeated entries on different drives and hash directories; it is **not** a promise to list 100,000 unique uploads. Concurrent directory calls may already be in flight when the aggregate budget is exceeded. Overflow returns `SlowDown` (503), never a successful partial page. A 30-second context budget stops further scheduling; admission stays held until scan workers exit. This is neither a precise memory ceiling nor a guarantee that a canceled physical system call stops immediately.

As a budget illustration only, one upload per unique key on every drive of an N-drive set costs about `2 × N` entries across the two directory levels: `100000 / (2 × N)` uploads, or about 3,125 at N=16. Multiple uploads under one key share the hash-directory cost; other sets/pools, stale directories and timeouts also matter. This is not a universal upload-count limit.

Every page still rescans durable state: total enumeration cost grows with both stored candidates and page count. The tests cover missing markers, multi-pool coverage, partial-deletion retries, identity fallback, RPC directory bounds, cancellation admission and the known late-write counterexample. Temporary multi-node and maintained-client checks establish functional behavior for their recorded environment. Production-scale latency and foreground-load impact remain deployment-specific acceptance work; merging the source does not certify them.

A September 16 temporary Docker Desktop arm64 run used two nodes, four APFS-backed bind volumes and 11,000 uploads across two buckets, while other local validation was running. One 1,000-entry page for the 10,000-upload target bucket took 18.7 seconds; two concurrent requests returned retryable `SlowDownRead` responses after about 25–27 seconds. These observations do not meet the provisional five-second page target and are not an isolated SSD benchmark. Capacity and foreground-load acceptance remain open; the bounded scanner must not be advertised as a large-scale performance fix.

## Historical: August 30 analysis and proposal {#analysis-20260830}

> [!WARNING]
> **分片列表最新决策 · Latest multipart-listing decision (2026-10-18)**
>
> **English:** The October 18 decision withdraws default persistent scanning, restores cache/exact-key listing, retains identity, safety and cleanup repairs, and does not restore the strict switch. See the [latest decision](https://silo.pgsty.com/blog/design/list-multipart-uploads/#decision-20261018). The rollback is implemented in [`4733e1423`](https://github.com/pgsty/silo/commit/4733e1423cfe703951f52ff9cbd286df2cf9d79d) and remains unreleased. Historical sections retain their named releases' contracts; installed binaries and unrelated upgrade requirements do not change.
>
> **中文：** 2026-10-18 决定定向撤回默认持久扫描，恢复缓存／精确 key 列表；保留身份、安全和清理修复，不恢复 strict 开关。参见[最新决策](https://silo.pgsty.com/zh/blog/design/list-multipart-uploads/#decision-20261018)。回退实现见 [`4733e1423`](https://github.com/pgsty/silo/commit/4733e1423cfe703951f52ff9cbd286df2cf9d79d)，尚未正式发布。旧章节保留对应版本的历史契约，不改变已安装二进制，也不替代其他主题的升级要求。

> **Archived analysis (2026-08-30):** “current”, “recommended”, option numbers and gate language below refer to that review and proposal. For the unreleased candidate, use the [October 18 decision](#decision-20261018); for Server 20260916, use its [dated contract](#implementation-20260916). The old writer-upgrade/drain gate is not the candidate's prerequisite. Capability advertisement and the one-day drain estimate were proposals, not current guarantees.

### The problem in plain language {#plain-language}

Imagine that four large files are still being uploaded:

```text
tables/a/part-1
tables/a/part-2
tables/b/part-1
other/file
```

An S3 client asks, "show me every unfinished upload below `tables/`." AWS S3 returns the first three. SILO currently treats `tables/` as if it were the complete name of one object, looks for exactly that object, and returns an empty list.

If the client removes the prefix and asks for every unfinished upload in the bucket, SILO takes a different shortcut: it reads a process-local memory cache. That cache may contain all four uploads on the node that created them, but it does not survive a restart and is not authoritative across nodes. The upload data is still on disk; the list is wrong.

This is why the defect is more serious than one ignored query parameter. Cleanup tools can receive `200 OK`, conclude that no unfinished uploads exist, and report success while uploads remain on disk. The server is not losing committed objects, but it is giving callers a false view of unfinished work.

### Executive decision {#decision}

SILO should fix this behavior if it intends to keep advertising practical S3 compatibility.

The repair is justified because the current endpoint silently claims success, behaves differently after restart or node switching, and breaks standard prefix-based cleanup and pagination. The default 24-hour stale-upload collector limits storage accumulation on default configurations, but it does not make the API result truthful.

The repair is not a small change. Existing upload directories contain only a one-way hash of the bucket and object key, and the original key is not stored in their `xl.meta`. A correct implementation must begin persisting that identity for new uploads, discover candidates with erasure-aware quorum rules, apply S3 semantics globally across pools and sets, and handle legacy uploads during a rolling upgrade.

The recommended direction is therefore:

1. record the bucket and object key in the upload's existing quorum-written metadata;
2. build a bounded on-demand scan as the durable correctness path;
3. keep any cache only as a rebuildable optimization;
4. enable strict S3 behavior only after every writer has upgraded and all keyless legacy uploads have drained;
5. consider a durable secondary index only if measurements prove that scanning cannot meet a product-approved service-level objective.

### Sources and provenance {#sources}

The problem statement and proposed design are grounded in five kinds of evidence.

#### The S3 contract {#source-s3}

The [AWS ListMultipartUploads API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListMultipartUploads.html) defines the public contract for general-purpose buckets:

- `prefix` selects every upload whose key starts with that string;
- `delimiter` groups matching keys into `CommonPrefixes`;
- `max-uploads` limits a page, with 1,000 as the documented maximum;
- `key-marker` and `upload-id-marker` continue a truncated listing;
- `upload-id-marker` is ignored when `key-marker` is absent;
- results are ordered by object key, then by initiation time for uploads with the same key.

AWS documentation does not settle every implementation edge unambiguously. Equal timestamps, invalid or out-of-range `max-uploads`, URL encoding, marker boundaries, and the way `CommonPrefixes` consume a page should be captured once against AWS and stored as fixtures before implementation.

#### The reported defect {#source-issue}

[Issue #79](https://github.com/pgsty/silo/issues/79) supplied a self-contained signed reproducer against `pgsty/silo:latest` and compared SILO with AWS, RustFS, SeaweedFS, and Garage. Its four central observations reproduce:

| Request | Required behavior | Observed SILO behavior |
| --- | --- | --- |
| `prefix=t/` | return the three keys beginning with `t/` | returns no uploads |
| `max-uploads=1` | return one item and continuation markers | returns every cached upload |
| `key-marker=t/a_b/p2` | continue after that key | returns every cached upload |
| `prefix=t/&delimiter=/` | return grouped `CommonPrefixes` | returns neither uploads nor prefixes |

The issue correctly identifies a compatibility failure, but its statement that `max-uploads` is always ignored and `IsTruncated` is always false is broader than the implementation. Those claims hold on the empty-prefix cache path used by the reproducer; the exact-object path can honor `max-uploads` and `upload-id-marker` and can set `IsTruncated`.

#### The upstream design history {#source-upstream}

The behavior was inherited rather than invented by SILO:

- MinIO [PR #5248](https://github.com/minio/minio/pull/5248) deliberately removed prefix-based listing from the erasure backend in 2017 "to simplify" multipart support.
- MinIO [PR #20407](https://github.com/minio/minio/pull/20407) added the empty-prefix multipart cache in 2024, mainly for Alluxio tests.
- A 2025 report of the same exact-key behavior, [MinIO issue #20989](https://github.com/minio/minio/issues/20989), was closed as working as intended.
- SILO's current [S3 compatibility reference](/reference/s3-api-compatibility/#differences-from-s3-apis-for-multipart-uploads) already records the exact-object-name divergence, although it did not explain the cache, pagination, marker, delimiter, or restart limitations before this design record.

This history explains why the code looks deliberate. It does not make the endpoint compatible with the AWS contract.

#### Source review {#source-code}

The current source has two mutually exclusive listing paths:

```text
erasureServerPools.ListMultipartUploads
  prefix == ""  -> return entries from node-local mpCache
  prefix != ""  -> hash prefix as a complete object key
                    -> select one set
                    -> list one sha256(bucket/object) directory
```

The important locations are:

- [`cmd/erasure-server-pool.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/erasure-server-pool.go): empty-prefix `mpCache`, per-pool concatenation, and the internal exact-object lookup used by `NewMultipartUpload`;
- [`cmd/erasure-multipart.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/erasure-multipart.go): exact-object listing, upload directory construction, stale-upload cleanup, and the quorum write for a new upload's `xl.meta`;
- [`cmd/erasure-sets.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/erasure-sets.go): hashing a supplied object name to one erasure set;
- [`cmd/bucket-handlers.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/bucket-handlers.go): public request validation, including a `501 NotImplemented` guard when `key-marker` does not share the request prefix;
- [`cmd/object-api-multipart_test.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/object-api-multipart_test.go): a large expected-results table whose final assertion block checks only echoed scalar fields, not the returned uploads, prefixes, markers, or truncation state.

#### Independent reproduction and adversarial review {#source-review}

The issue scenario was independently reproduced against the reviewed SILO source with a single-node server and SigV4 requests. Additional probes established that:

- an exact object key can paginate its own uploads;
- `upload-id-marker` currently affects that exact-key path even without `key-marker`, contrary to AWS;
- `NextKeyMarker` remains empty on an exact-key truncated page;
- `max-uploads=0` behaves as unlimited in the current path;
- a plain server restart empties the bucket-wide view while exact-key lookup still finds the on-disk uploads.

A second adversarial architecture review challenged the storage, quorum, migration, suspended-pool, mixed-version, and performance assumptions. The corrections from that review are incorporated below; this record does not treat an AI review as a substitute for code tests or an AWS conformance capture.

### What the code actually does {#current-behavior}

#### Empty prefix: a volatile node-local view {#empty-prefix}

With no prefix, the pool layer returns every `MultipartInfo` for the bucket from `mpCache`, sorted only by initiation time. It does not apply `max-uploads`, `key-marker`, `upload-id-marker`, or `delimiter`, and it does not compute continuation markers or `IsTruncated`.

The cache is initialized empty at process startup. Creation populates only the node that handles the request. Completion and abort delete cache entries, including peer notifications in some paths, but creation has no equivalent durable cluster-wide population or startup rebuild. Consequently:

- a restart can change a non-empty listing into an empty one;
- two nodes can return different answers for the same bucket;
- a successful response is not evidence that the server has enumerated durable upload state.

#### Non-empty prefix: an exact object lookup {#nonempty-prefix}

With a non-empty prefix, the string is passed through object hashing as though it were a complete object name. One erasure set is selected, and listing reads the directory derived from `sha256(bucket/object)`.

This path can enumerate multiple upload IDs for that exact object. It sorts them by initiation time, applies its `upload-id-marker`, stops at `max-uploads`, and sets `IsTruncated`. It still does not implement lexical prefix matching, `CommonPrefixes`, general key-marker semantics, or `NextKeyMarker`.

#### Multiple pools make pagination less correct {#multiple-pools}

For a non-empty request on a multi-pool deployment, the pool layer invokes each active pool with the same maximum and concatenates the results. It does not perform a global ordered merge or recompute page boundaries and next markers. A request for `N` items can therefore collect up to `N` from each pool.

Suspended pools are skipped by listing and by the other public multipart verbs. In-progress uploads left on a suspended or decommissioning pool are therefore inaccessible, not merely unlisted. That is a related lifecycle defect, but listing alone must not advertise handles that `PutObjectPart`, `ListParts`, `CompleteMultipartUpload`, and `AbortMultipartUpload` cannot use. Pool drain or forced abort should be designed as a separate cross-verb change.

### Why current uploads cannot be backfilled {#no-backfill}

The multipart namespace is flat:

```text
.minio.sys/multipart/<sha256(bucket/object)>/<upload-id>/xl.meta
```

The hash is one-way. The original bucket and key are not encoded in the path. They are also not stored as a name field in the current multipart `xl.meta`; the supplied object name only influences the erasure distribution during `newFileInfo` construction.

Therefore an all-directory scan can discover that an upload exists, but it cannot determine which bucket or key it belongs to. The current node-local cache cannot repair this reliably because it is incomplete across nodes and disappears on restart.

This rules out a tempting "small" fix: scanning every existing `xl.meta` and applying prefix filters. New identity metadata or a durable index is required, and old keyless uploads need an explicit migration policy.

### Complexity assessment {#complexity}

The semantic algorithm is not the hardest part. The hard part is obtaining a complete, quorum-valid, globally ordered input set without turning a listing call into an uncontrolled cluster-wide metadata storm.

| Area | Complexity | Why |
| --- | --- | --- |
| Pure S3 filtering and pagination | Medium | Rules are finite, but marker and delimiter edge cases need captured AWS evidence. |
| Persisting bucket/key in new upload metadata | Medium | It reuses an existing quorum write, but completion, rollback, healing, and replication compatibility must be tested. |
| Candidate discovery | High | The namespace mixes every bucket and duplicates each upload across erasure drives. One-disk discovery can miss quorum-valid uploads. |
| Quorum and concurrent deletion | High | A scan must reject minority ghosts while tolerating abort, completion, GC rename-to-trash, and transient `ENOENT`. |
| Multi-pool global pagination | High | Results must be merged, sorted, truncated, and marked once across all accessible pools and sets. |
| Rolling migration | High | Old writers keep creating keyless uploads; old completers may preserve unknown internal metadata. |
| Performance and resource control | High | A bucket request may require inspecting every active upload in the cluster, not only that bucket. |

Overall, this is a high-complexity compatibility project with medium wire-compatibility risk and high implementation-correctness risk. It is not a destructive object-format migration: the recommended design adds internal metadata for new incomplete uploads and leaves the existing directory scheme in place.

### Compatibility and operational impact {#impact}

#### Wire behavior changes {#wire-impact}

A correct implementation deliberately changes observable results:

- `prefix=foo` will match `foo`, `foobar`, and `foo/...`, not only the exact key `foo`;
- bucket-wide results will be ordered by key and initiation time rather than only initiation time;
- `max-uploads` will actually limit a page;
- the default and maximum will move from SILO's current 10,000 constant toward the AWS limit of 1,000, subject to the captured edge-case contract;
- clients must follow `NextKeyMarker` and `NextUploadIdMarker` instead of assuming one response contains everything;
- delimiter requests will return `CommonPrefixes`;
- the current handler-side `501` for a marker outside the prefix will be replaced by the captured AWS semantics.

These are compatibility fixes, but they can break software that accidentally depends on SILO's old non-S3 behavior. In particular, a client that ignores pagination may see fewer entries after the repair. Strict behavior should therefore be introduced through an explicit release and rollout contract, not silently slipped into an unrelated patch.

#### Storage-format compatibility {#storage-impact}

The recommended write path adds the bucket and object key as reserved internal metadata inside the new upload's existing quorum-written `xl.meta`. It does not rename multipart directories or create a second transactional write.

Before `CompleteMultipartUpload` renames upload metadata into the completed object, the new upload-only fields must be removed alongside the multipart checksum fields that are already stripped there.

An old binary completing an upload created by a new binary will not know to remove the new internal keys. They would remain inert and hidden from S3 user metadata, but persist in the completed object's internal metadata. Rolling-upgrade tests must prove that unknown reserved keys do not disturb healing, replication, metadata comparison, or downgrade reads. The product must then choose between tolerating that residue and adding a scrubber; it must not assume the keys disappear.

#### Operational cost {#operational-impact}

Because all buckets share one flat hash namespace, an on-demand scan is `O(all active multipart uploads in the cluster)`, not `O(uploads in the requested bucket)`. Bounded parallelism, cancellation, memory limits, and failure behavior are part of correctness, not optional tuning.

Default SILO configuration expires stale multipart uploads after 24 hours and runs cleanup every 6 hours. Once the last old writer has been upgraded, the keyless population should normally drain within roughly 30 hours. Operators with a larger custom expiry have a longer migration window. A zero value is mapped back to the 24-hour default in the current code; no supported "disabled" expiry value was identified in this review.

The collector bounds default storage accumulation, but does not repair a false listing response. It also does not remove the need to test sustained legitimate multipart activity, failure modes, and custom expiry settings.

#### Severity {#severity}

The recommended classification is **P1 / high compatibility**, not P0:

- no committed object data loss was demonstrated;
- no security boundary is bypassed;
- unfinished uploads remain on disk until completed, aborted, or collected;
- default stale-upload cleanup bounds accumulation in the ordinary configuration.

It remains high rather than medium because the server returns fabricated success, the answer changes after restart or node switching, and cleanup or quiescence tooling can be misled into false confidence.

### Options considered {#options}

#### Option 0: leave the current behavior unchanged {#option-zero}

This has no engineering cost and preserves every accidental behavior. It also preserves false `200 OK` responses, node-local inconsistency, restart volatility, broken prefix cleanup, and an inaccurate impression of S3 support.

This option is acceptable only if SILO deliberately downgrades the public compatibility claim and treats the endpoint as unsupported. Even then, silently returning an incomplete success is inferior to explicit rejection.

**Decision: reject as a long-term position.**

#### Option 1: explicit documented divergence {#option-divergence}

Reject combinations that SILO cannot honor with a stable `NotImplemented`-class error and document the exact supported subset. This is operationally honest and much smaller than full compatibility.

It is still a breaking change: tools that currently receive an empty or unbounded `200 OK` may begin failing jobs. It also does not produce an S3-compatible endpoint. The error behavior and default release policy must be deliberate.

**Decision: acceptable short-term containment if full compatibility is declined or deferred; not a compatibility fix.**

#### Option 2: persist identity, scan durable state, optionally cache {#option-scan}

For each new upload, store the bucket and key in reserved internal metadata in the upload's existing `xl.meta`. For listing, discover upload directories across accessible pools and sets, validate candidates with erasure read quorum, then run one global S3 semantic layer. A cache may accelerate this path only if it can be rebuilt and reconciled from durable state.

This avoids a second write transaction and keeps the directory layout stable. Its principal cost is the cluster-wide scan.

**Decision: recommended, subject to a performance and failure-mode spike.**

#### Option 3: durable bucket-scoped ordered index {#option-index}

Maintain a secondary index ordered by bucket, key, and upload identity. Listing becomes scalable and naturally paginable, but create, complete, abort, healing, rollback, and reconciliation must keep two locations consistent across failures. The design resembles multipart index structures that upstream MinIO deliberately removed while simplifying this subsystem.

**Decision: no-go unless measurements show that Option 2 cannot meet the product-approved service-level objective.**

#### Rejected variant: repair only `mpCache` {#option-cache-only}

Filtering, sorting, paginating, broadcasting creates, or rebuilding the current cache would improve symptoms but would not by itself establish a durable quorum-valid source of truth. A cache-only patch risks producing a more convincing but still incorrect answer.

**Decision: reject. A cache can optimize a correct read path, never define it.**

### Recommended design {#recommended-design}

#### 1. Freeze the public contract first {#contract-first}

Create a recorded AWS fixture suite for general-purpose buckets covering:

- ordering across keys and multiple uploads of one key;
- equal initiation times and a deterministic total-order tie-break;
- prefix and exact-key overlap;
- key-marker with and without upload-id-marker;
- upload-id-marker without key-marker;
- delimiter, `CommonPrefixes`, and page accounting;
- `max-uploads` omitted, 0, 1, 1,000, and greater than 1,000;
- `encoding-type=url`;
- empty pages, final pages, and next-marker values.

The captured responses should become repository fixtures. CI should not depend on live AWS access.

#### 2. Persist recoverable identity in the existing write {#write-path}

At `NewMultipartUpload`, add reserved internal metadata for the canonical bucket and object key before the existing `writeAllMetadata` quorum write. The exact key names are an implementation detail, but they must be versioned, unambiguous, size-bounded by the existing object-key limits, and excluded from client-visible metadata.

At successful completion, delete those upload-only keys before copying `fi.Metadata` into the final object metadata and before `renameData`. Abort and stale cleanup already delete the entire upload directory and need no separate index operation.

#### 3. Separate discovery from validation {#read-path}

Candidate discovery and candidate validity are different questions.

For every accessible, non-suspended pool and set:

1. list candidate hash and upload directories from all online drives required by the configured list-quorum policy;
2. union and deduplicate those names;
3. read the candidate `xl.meta` through the normal erasure metadata machinery;
4. include the upload only when its metadata is quorum-valid and contains a valid bucket/key identity;
5. tolerate a candidate disappearing during abort, completion, or stale cleanup;
6. under strict list quorum, fail the request rather than return a partial `200 OK` when a required set cannot be evaluated.

Using the first healthy disk for discovery is insufficient: that disk may have been offline when a still-quorum-valid upload was created.

#### 4. Apply semantics once, globally {#semantic-layer}

Feed the validated candidates from all pools and sets into a pure semantic layer. The layer owns bucket filtering, prefix, delimiter grouping, ordering, markers, maximum-page accounting, URL encoding, `IsTruncated`, and next markers.

Pool-local limits and markers must not be applied before the global merge. The result should be deterministic under duplicate discovery and independent of which node handles the request.

#### 5. Preserve the internal exact-object operation {#exact-helper}

`erasureServerPools.NewMultipartUpload` currently calls `ListMultipartUploads(bucket, object, ...)` to keep another upload for the same object in the same pool. If the public function starts treating that argument as a lexical prefix, `foo` could match `foobar` and select the wrong pool.

Introduce a narrowly named internal helper such as `FindMultipartUploadPool` or `ListMultipartUploadsExact`. It should use the existing object hash path and must not share the public prefix semantics.

#### 6. Treat cache as an optimization {#cache}

The existing `mpCache` may be removed. If retained, it must satisfy all of the following:

- durable state remains authoritative;
- startup can rebuild it;
- create, complete, and abort updates are propagated consistently;
- reconciliation detects missed events and stale entries;
- a cold or divergent cache falls back to the quorum-valid scan;
- correctness tests pass with the cache disabled.

#### 7. Gate strict behavior through rolling migration {#migration}

Legacy upload records lack bucket/key identity and cannot be reconstructed reliably. Use two externally meaningful modes:

- **legacy mode**, the initial upgrade default: new writers persist identity; keyless uploads are counted and drained; the documented response policy for a mixed keyed/keyless population must be selected explicitly;
- **strict mode**: activation requires every writer node to advertise the new metadata capability and the observed keyless count to be zero. Discovering a keyless upload afterward is an error with anomaly telemetry, not a silent omission.

A short shadow comparison can help validate the new scanner, but a permanent third operating mode is unnecessary unless the spike finds a need. With default expiry, the expected legacy drain is about one day plus one cleanup interval after the last old writer stops.

There is one unresolved product choice in legacy mode:

| Policy | Advantage | Cost |
| --- | --- | --- |
| return the complete keyed subset with documented telemetry | keeps tools operating during the bounded drain | still returns an incomplete `200 OK` that ordinary clients cannot see is incomplete |
| fail listing while any keyless upload exists | never fabricates completeness | can block cleanup and existing jobs throughout the drain window |

This choice belongs in the ADR. Strict mode has no such ambiguity: it must fail loud if its precondition is violated.

#### 8. Keep suspended-pool lifecycle separate {#suspended-pools}

Listing should initially mirror the accessibility contract of the other multipart verbs and scan non-suspended pools. Adding suspended-pool entries to listing alone would expose uploads that cannot be extended, completed, or aborted.

Open a separate lifecycle design for in-progress uploads when a pool drains: either keep all multipart verbs available until the uploads finish, migrate them, or force-abort them under a documented policy. Do not hide that problem inside #79.

### Performance spike and decision rule {#spike}

Option 2 is preferred because it has one durable write location, but its scan cost must be measured rather than assumed.

Generate 1,000, 10,000, and 100,000 active uploads across a matrix of pools, sets, and drive counts. Measure:

- cold and warm p50/p95/p99 latency;
- total and per-drive `ListDir` operations;
- metadata-read and internode RPC counts;
- peak memory and allocation volume;
- cancellation latency;
- behavior with slow, offline, healing, and intermittently disappearing drives;
- simultaneous create, complete, abort, and stale cleanup;
- first-page and deep-page cost with selective and empty prefixes.

The acceptance threshold is a product decision and must be recorded before interpreting the result. A guessed one- or two-second target is not evidence. If the scan meets the approved target with bounded resource use, reject Option 3. If it does not, use the measurements to design the smallest durable index that solves the demonstrated bottleneck.

### Test and release gates {#gates}

#### Semantic and unit tests {#unit-tests}

- pure table tests generated from recorded AWS fixtures;
- ordering, marker, delimiter, encoding, truncation, and maximum-edge coverage;
- property tests ensuring pagination returns each logical upload exactly once;
- deterministic behavior with duplicate candidates and equal timestamps.

#### Object and handler tests {#handler-tests}

- strengthen the existing object-layer table to assert uploads, common prefixes, markers, and truncation;
- parse and validate handler XML bodies instead of checking only status codes;
- verify default and invalid `max-uploads` handling;
- test exact-helper pool selection independently of public prefix semantics.

#### Distributed and failure tests {#failure-tests}

- restart equivalence and node-switch equivalence;
- multiple sets and pools with a single global page boundary;
- candidate missing from one drive but present at quorum;
- minority ghost after partial abort;
- concurrent completion and GC rename-to-trash;
- unavailable set under every supported `list_quorum` policy;
- rolling upgrade, old-writer reintroduction, downgrade completion, and strict-mode gating;
- unknown internal metadata under healing and replication.

#### Delivery gates {#delivery-gates}

1. approve the ADR, including product mode and performance SLO;
2. commit the captured conformance fixtures;
3. complete and review the storage spike;
4. implement and pass focused, full, race, and failure QA;
5. update the S3 compatibility reference and operational guidance;
6. commit and merge the source change;
7. build and identify the release artifact or container image;
8. canary a rolling upgrade and observe keyless-drain telemetry;
9. enable strict mode only after its gates hold;
10. verify the live endpoint before closing #79.

Passing an earlier gate is not evidence that a later gate happened.

### Final recommendation: fix it, but do not rush it {#final-recommendation}

Leaving the current endpoint indefinitely is the wrong trade-off. This is not an obscure response-field mismatch: it affects discovery and cleanup of unfinished data, returns successful but false answers, and changes behavior across nodes and restarts. Those properties undermine the practical meaning of S3 compatibility.

At the same time, a direct implementation patch is also the wrong trade-off. The current disk layout cannot identify legacy uploads, a correct scan needs erasure-aware discovery and quorum, and wire-correct pagination changes observable client behavior.

The balanced decision is:

- **GO** for the ADR, AWS fixture capture, metadata-plus-scan prototype, and performance/failure spike;
- **GO conditionally** for Option 2 after the product SLO and legacy response policy are approved;
- **NO-GO** for a cache-only repair, an immediate durable secondary index, strict-by-default behavior in a patch release, or closing the issue before rolling-upgrade reachability is demonstrated;
- if implementation capacity is unavailable, **GO** for an explicit documented divergence and stable error behavior rather than continuing to fabricate successful listings.

This preserves compatibility discipline without pretending that a high-risk distributed listing change is a two-line bug fix.

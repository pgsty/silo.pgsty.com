---
title: "Bucket Replication"
url: "/administration/bucket-replication/"
weight: 160
icon: fa-solid fa-arrows-rotate
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/bucket-replication.rst
upstream_modified: true
---

**SILO 20261109 release changes:** [SILO 20261109](/blog/release/silo-20261109/) preserves target Object Lock retention and legal hold on replicated deletes (commit [`7e9ee6bef`](https://github.com/pgsty/silo/commit/7e9ee6bef)), stops replicating lifecycle-created delete markers and version purges to match AWS S3 semantics (commit [`1bd0b1b04`](https://github.com/pgsty/silo/commit/1bd0b1b04)), and prevents replication worker metrics from panicking when the replication pool is absent while retaining historical averages and peak counts (commit [`099b7ddf3`](https://github.com/pgsty/silo/commit/099b7ddf3)).

**20261026 release change:** Multipart replication now preserves the `FULL_OBJECT` checksum type for composite CRC algorithms (earlier versions omitted the header, causing the destination to initialize a `COMPOSITE` multipart upload and reject the full-object CRC at completion). This fix is in [Server 20261026](/blog/release/silo-20261026/#server-20261026); after upgrading the sending Server, verify pending/failed replicas and destination checksums.

<a id="bucket-replication"></a>
<a id="minio-bucket-replication"></a>

MinIO supports server-side and client-side replication of objects between source and destination buckets.

- **[Server-Side Bucket Replication](#minio-bucket-replication-serverside):** Configure per-bucket rules to synchronize objects automatically between deployments. The deployment where you configure the bucket replication rule acts as the “source” while the configured remote deployment acts as the “target”. SILO applies rules during object write operations (for example, `PUT`) and synchronizes new objects and object mutations, including new object versions and metadata updates. Server-side bucket replication requires an identical release on the source and remote target clusters.
- **Client-Side Bucket Replication:** Use [`mc mirror`](/reference/minio-mc/mc-mirror/#command-mc.mirror) to synchronize objects between buckets within the same S3-compatible cluster or between two independent S3-compatible clusters, including SILO-to-S3 configurations.

> [!NOTE]
> **Bucket vs Site Replication**
>
> Bucket Replication is distinct from and mutually exclusive with [site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview).
>
> - Bucket Replication synchronizes data at the bucket level, such as bucket prefix paths and objects.
>
>   You can configure bucket replication at any time, and the remote MinIO deployments may have pre-existing data on the replication target buckets.
> - Site Replication extends bucket replication to include [IAM](/administration/identity-access-management/#minio-authentication-and-identity-management), security tokens, access keys, and bucket-level configurations.
>
>   Site replication is typically configured when initially deploying the MinIO peer sites. Only one site can hold any bucket or objects at the time of initial configuration.

<a id="minio-bucket-replication-serverside"></a>

## Server-Side Bucket Replication {#server-side-bucket-replication}

MinIO server-side bucket replication is an automatic bucket-level configuration that synchronizes objects between a source and destination bucket. MinIO server-side replication *requires* the source and destination bucket be two separate MinIO clusters running the same MinIO Server version.

For each write operation to the bucket, MinIO checks all configured replication rules for the bucket and applies the matching rule with highest configured priority. MinIO synchronizes new objects *and* object mutations, such as new object versions or changes to object metadata. This includes metadata operations such as enabling or modifying object locking or retention settings.

MinIO server-side bucket replication is functionally similar to Amazon S3 replication while adding the following MinIO-only features:

- Source and destination bucket names can match, supporting site-to-site use cases such as Splunk or Veeam BC/DR.
- Simplified implementation than S3 bucket replication configuration, removing the need to configure settings like AccessControlTranslation, Metrics, and SourceSelectionCriteria.
- Active-Active (Two-Way) replication of objects between source and destination buckets.
- Multi-Site replication of objects between three or more MinIO deployments

<a id="minio-replication-behavior-resync"></a>

### Resynchronization (Disaster Recovery) {#resynchronization-disaster-recovery}

Resynchronization primarily supports recovery after partial or total loss of the data on a MinIO deployment using a healthy deployment in the replica configuration. Use the [`mc replicate resync`](/reference/minio-mc/mc-replicate-resync/#command-mc.replicate.resync) command completely resynchronize the remote target ([`mc admin bucket remote`](/reference/deprecated/mc-admin-bucket-remote/#command-mc.admin.bucket.remote)) using the specified source bucket.

The resynchronization process checks all objects in the source bucket against all configured replication rules that include [existing object replication](#minio-replication-behavior-existing-objects). For each object which matches a rule, the resynchronization process places the object into the replication [queue](#minio-replication-process) regardless of the object’s current [replication status](#minio-replication-process).

MinIO skips synchronizing those objects whose remote copy exactly match the source, including object metadata. MinIO otherwise does not prioritize or modify the queue with regards to the existing contents of the target.

[`mc replicate resync`](/reference/minio-mc/mc-replicate-resync/#command-mc.replicate.resync) operates at the bucket level and does *not* support prefix-level granularity. Initiating resynchronization on a large bucket may result in a significant increase in replication-related load and traffic. Use this command with caution and only when necessary.

For buckets with [object transition (Tiering)](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering) configured, replication resynchronization restores objects in a non-transitioned state with no associated transition metadata. Any data previously transitioned to the remote storage is therefore permanently disconnected from the remote MinIO deployment. For tiering configurations which specify an explicit human-readable prefix as part of the remote configuration, you can safely purge the transitioned data in that prefix to avoid costs associated to the “lost” data.

<a id="minio-replication-behavior-delete"></a>

### Replication of Delete Operations {#replication-of-delete-operations}

MinIO supports replicating [delete](/administration/object-management/object-delete/#minio-object-delete) operations, where MinIO synchronizes deleting specific object versions *and* new [delete markers](https://docs.aws.amazon.com/AmazonS3/latest/userguide/delete-marker-replication.html). Delete operation replication uses the same [replication process](#minio-replication-process) as all other replication operations.

MinIO requires explicitly enabling versioned deletes and delete marker replication . Use the [`mc replicate add --replicate`](/reference/minio-mc/mc-replicate-add/#mc.replicate.add.-replicate) field to specify both or either `delete` and `delete-marker` to enable versioned deletes and delete marker replication respectively. To enable both, specify both strings using a comma separator `delete,delete-marker`.

For delete marker replication, MinIO begins the replication process after a delete operation creates the delete marker. MinIO uses the `X-Minio-Replication-DeleteMarker-Status` metadata field for tracking delete marker replication status. In [active-active](/administration/bucket-replication/enable-server-side-two-way-bucket-replication/#minio-bucket-replication-serverside-twoway) replication configurations, MinIO may produce duplicate delete markers if both clusters concurrently create a delete marker for an object *or* if one or both clusters were down before the replication event synchronized.

For replicating the deletion of a specific object version, MinIO marks the object version as `PENDING` until replication completes. Once the remote target deletes that object version, MinIO deletes the object on the source. While this process ensures near-synchronized version deletion, it may result in listing operations returning the object version after the initial delete operation. MinIO uses the `X-Minio-Replication-Delete-Status` for tracking delete version replication status.

In [SILO 20261109](/blog/release/silo-20261109/), replicated deletes preserve the target's Object Lock legal hold and retention (commit [`7e9ee6bef`](https://github.com/pgsty/silo/commit/7e9ee6bef)). A source purge that bypassed `GOVERNANCE` retention does not grant a bypass on the target; if the target version still carries active retention or a legal hold, the target refuses the replicated purge and the source retries.

SILO replicates only explicit client-driven delete operations. Lifecycle-created delete markers and version purges from [lifecycle management expiration rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) are **not** replicated (commit [`1bd0b1b04`](https://github.com/pgsty/silo/commit/1bd0b1b04)), matching AWS S3 semantics. Configure expiration rules independently on source and target buckets—and identically across all buckets in [active-active](/administration/bucket-replication/enable-server-side-two-way-bucket-replication/#minio-bucket-replication-serverside-twoway) configurations—when replicas require consistent expiration.

> [!DETAILS]- MinIO Trims Empty Object Prefixes on Source and Remote Bucket
> If a delete operation removes the last object in a bucket prefix, MinIO recursively removes each empty part of the prefix up to the bucket root. MinIO only applies the recursive removal to prefixes created *implicitly* as part of object write operations - that is, the prefix was not created using an explicit directory creation command such as [`mc mb`](/reference/minio-mc/mc-mb/#command-mc.mb).
>
> If a replication rule enables replication delete operations, the replication process *also* applies the implicit prefix trimming behavior on the destination MinIO cluster.
>
> For example, consider a bucket `photos` with the following object prefixes:
>
> - `photos/2021/january/myphoto.jpg`
> - `photos/2021/february/myotherphoto.jpg`
> - `photos/NYE21/NewYears.jpg`
>
> `photos/NYE21` is the *only* prefix explicitly created using [`mc mb`](/reference/minio-mc/mc-mb/#command-mc.mb). All other prefixes were *implicitly* created as part of writing the object located at that prefix.
>
> - A command removes `myphoto.jpg`. MinIO automatically trims the empty `/january` prefix.
> - A command then removes the `myotherphoto.jpg`. MinIO automatically trims the `/february` prefix *and* the now-empty `/2021` prefix.
> - A command removes the `NewYears.jpg` object. MinIO leaves the `/NYE21` prefix in place since it was *explicitly* created.

<a id="minio-replication-behavior-existing-objects"></a>

### Replication of Existing Objects {#replication-of-existing-objects}

MinIO by default replicates existing objects in the source bucket to the configured remote, similar to [AWS: Replicating existing objects between S3 buckets](https://aws.amazon.com/blogs/storage/replicating-existing-objects-between-s3-buckets/) without the overhead of contacting technical support.

MinIO marks all objects or object prefixes that satisfy the replication rules as eligible for synchronization to the remote cluster and bucket. MinIO only excludes those objects without a version ID, such as those objects written before enabling versioning on the bucket.

You can disable existing object replication while configuring or modifying the bucket replication rule. You must specify *all* desired replication features during creation or modification:

- For new replication rules, exclude `"existing-objects"` from the list of replication features specified to [`mc replicate add --replicate`](/reference/minio-mc/mc-replicate-add/#mc.replicate.add.-replicate).
- For existing replication rules, remove `"existing-objects"` from the list of existing replication features using [`mc replicate update --replicate`](/reference/minio-mc/mc-replicate-update/#mc.replicate.update.-replicate). The new rule **replaces** the previous rule.

Disabling existing object replication does not remove any objects already replicated to the remote bucket.

### Synchronous vs Asynchronous Replication {#synchronous-vs-asynchronous-replication}

MinIO supports specifying either asynchronous (default) or synchronous replication for a given remote target.

With asynchronous replication, MinIO completes the originating `PUT` operation *before* placing the object into a [replication queue](#minio-replication-process). The originating client may therefore see a successful `PUT` operation *before* the object is replicated. While this may result in stale or missing objects on the remote, it mitigates the risk of slow write operations due to replication load.

With synchronous replication, MinIO attempts to replicate the object *prior* to completing the originating `PUT` operation. MinIO returns a successful `PUT` operation whether or not the replication attempt succeeds. This reduces the risk of slow write operations at a possible cost of stale or missing objects on the remote location.

You must explicitly enable synchronous replication when configuring the remote target using the [`mc admin bucket remote add`](/reference/deprecated/mc-admin-bucket-remote/#mc.admin.bucket.remote.add) command with the [`add`](/reference/deprecated/mc-admin-bucket-remote/#mc.admin.bucket.remote.add) flag.

### Replication Internals {#replication-internals}

This section documents internal replication behavior and is not critical to using or implementing replication. This documentation is provided strictly for learning and educational purposes.

<a id="minio-replication-process"></a>

#### Replication Process {#replication-process}

MinIO uses a replication queuing system with multiple concurrent replication workers operating on that queue. MinIO continuously works to replicate and remove objects from the queue while scanning for new unreplicated objects to add to the queue. In [SILO 20261109](/blog/release/silo-20261109/), replication worker metrics no longer panic when the replication worker pool is absent and continue to retain historical averages and peak counts (commit [`099b7ddf3`](https://github.com/pgsty/silo/commit/099b7ddf3)).

> [!NOTE]
> **Queue retry and requeue behavior**
>
> - **Retry limit (`RELEASE.2022-07-18T17-49-40Z`):** SILO queues failed replication operations and retries each operation up to three (3) times before dequeuing it. The scanner later picks up affected objects and requeues them for replication.
> - **Read-triggered requeue (`RELEASE.2022-08-11T04-37-28Z`):** Failed or pending replications requeue automatically during list, `GET`, or `HEAD` requests (for example, running [`mc stat`](/reference/minio-mc/mc-stat/#command-mc.stat), [`mc cat`](/reference/minio-mc/mc-cat/#command-mc.cat), or [`mc ls`](/reference/minio-mc/mc-ls/#command-mc.ls) after a remote target returns online).

MinIO sets the `X-Amz-Replication-Status` metadata field according to the replication state of the object:

| Replication State | Description                                                                                                                                                                                                                                                                                                                                          |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PENDING`         | The object has not yet replicated. SILO sets this state when the object matches a configured replication rule on the bucket, scans for `PENDING` objects not yet in the queue, and enqueues them as space is available. For multi-site replication, objects remain `PENDING` until replicated to *all* configured remotes for that bucket or prefix. |
| `COMPLETED`       | The object replicated to the remote cluster.                                                                                                                                                                                                                                                                                                         |
| `FAILED`          | The object failed to replicate to the remote cluster. SILO scans for `FAILED` objects not yet in the replication queue and enqueues them as space is available.                                                                                                                                                                                      |
| `REPLICA`         | The object is a replica received from a remote source.                                                                                                                                                                                                                                                                                               |
{.wide .expand}

The replication process generally has one of the following flows:

- `PENDING -> COMPLETED`
- `PENDING -> FAILED -> COMPLETED`

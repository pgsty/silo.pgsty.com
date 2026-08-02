---
title: "Bucket Versioning"
url: "/administration/object-management/object-versioning/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="bucket-versioning"></a>
<a id="minio-bucket-versioning"></a>

- [Versioning overview](https://youtu.be/XGOiwV6Cbuk?ref=docs)
- [Versioning lab](https://youtu.be/nFUI2N5zH34?ref=docs)

## Overview {#overview}

MinIO supports keeping multiple “versions” of an object in a single bucket.

When enabled, versioning allows MinIO to keep multiple iterations of the same object. Write operations which would normally overwrite an existing object instead result in the creation of a new versioned object. MinIO versioning protects from unintended overwrites and deletions while providing support for “undoing” a write operation. Bucket versioning is a prerequisite for configuring [object locking and retention rules](/administration/object-management/object-retention/#minio-object-locking).

For versioned buckets, a write operation results in a new version of that object with a unique version ID. MinIO marks the “latest” version of the object that clients retrieve by default. Clients can then explicitly choose to list, retrieve, or remove a specific object version.

Define [object expiration](/administration/object-management/create-lifecycle-management-expiration-rule/#minio-lifecycle-management-create-expiry-rule) rules to remove versions of objects no longer needed, such as by the number of versions or the date of versions.

### Read Operations on Versioned Objects {#read-operations-on-versioned-objects}

Review each of the four images in this series to see how MinIO retrieves objects in a versioned bucket. Use the arrows on either side of the images to navigate from one to the next.

{{< doc-carousel >}}
{{< doc-card title="Object with Single Version" image="/images/retention/minio-versioning-single-version.svg" alt="Object with single version" >}}
MinIO adds a unique version ID to each object as part of write operations.
{{< /doc-card >}}
{{< doc-card title="Object with Multiple Versions" image="/images/retention/minio-versioning-multiple-versions.svg" alt="Object with Multiple Versions" >}}
MinIO retains all versions of an object and marks the most recent version as the “latest”.
{{< /doc-card >}}
{{< doc-card title="Retrieving the Latest Object Version" image="/images/retention/minio-versioning-retrieve-latest-version.svg" alt="Object with Multiple Versions" >}}
A read operation request without a version ID returns the latest version of the object.
{{< /doc-card >}}
{{< doc-card title="Retrieving a Specific Object Version" image="/images/retention/minio-versioning-retrieve-single-version.svg" alt="Object with Multiple Versions" >}}
Include the version ID to retrieve a specific version of an object during a read operation.
{{< /doc-card >}}
{{< /doc-carousel >}}

{{% alert color="info" %}}
**Changed: MinIO**

Server RELEASE.2023-05-04T21-44-30Z

MinIO does not create versions for creation, mutation, or deletion of explicit directory objects (“prefixes”). Objects created within that explicit directory object retain normal versioning behavior.
{{% /alert %}}

MinIO implicitly determines prefixes from object paths. Explicit prefix creation typically only occurs with Spark and similar workloads which apply legacy POSIX/HDFS directory creation behavior within the S3 context.

### Versioning is Per-Namespace {#versioning-is-per-namespace}

MinIO uses the full namespace (the bucket and path to an object) for each object as part of determining object uniqueness. For example, all of the following namespaces are “unique” objects, where mutations of each object result in the creation of new object versions *at that namespace*:

```shell
databucket/object.blob
databucket/blobs/object.blob
blobbucket/object.blob
blobbucket/blobs/object.blob
```

While `object.blob` might be the same binary across all namespaces, MinIO only enforces versioning with a specific namespace and therefore considers each `object.blob` above as distinct and unique.

### Versioning and Storage Capacity {#versioning-and-storage-capacity}

MinIO does not perform incremental or differential-type versioning. For mutation-heavy workloads, this may result in substantial drive usage by older or aged object versions.

For example, consider a 1GB object containing log data. An application appends 100MB of data to the log and uploads to MinIO. MinIO would then contain both the 1GB and 1.1GB versions of the object. If the application repeated this process every day for 10 days, the bucket would eventually contain more than 14GB of data associated to a single object.

MinIO supports configuring configuring [object lifecycle management rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management) to automatically expire or transition aged object versions and free up storage capacity. For example, you can configure a rule to automatically expire object versions 90 days after they become non-current (i.e. no longer the “latest” version of that object). See [MinIO Object Expiration](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) for more information.

You can alternatively perform manual removal of object versions using the following commands:

- [`mc rm --versions`](/reference/minio-mc/mc-rm/#mc.rm.-versions) - Removes all versions of an object.
- **[`mc rm --versions --older-than`](/reference/minio-mc/mc-rm/#mc.rm.-older-than) -**

  > Removes all versions of an object older than the specified calendar date.

{{% alert color="info" %}}
**Added: RELEASE.2024-04-18T19-09-19Z**

MinIO emits a warning if the cumulative size of versions for any single object exceeds 1TiB.
{{% /alert %}}

<a id="minio-bucket-versioning-id"></a>

### Version ID Generation {#version-id-generation}

MinIO generates a unique and immutable identifier for each versioned object as part of write operations. Each object version ID consists of a 128-bit fixed-size <a id="index-0"></a>[**UUIDv4**](https://datatracker.ietf.org/doc/html/rfc4122.html#section-4.4). UUID generation is sufficiently random to ensure high likelihood of uniqueness for any environment, are computationally difficult to guess, and do not require centralized registration process and authority to guarantee uniqueness.

<img src="/images/retention/minio-versioning-multiple-versions.svg" alt="Object with Multiple Versions" style="max-width: (&#x27;600px&#x27;, &#x27;auto&#x27;);" />

MinIO does not support client-managed version ID allocation. All version ID generation is handled by the MinIO server process.

For objects created while versioning is disabled or suspended, MinIO uses a `null` version ID. You can access or remove these objects by specifying `null` as the version ID as part of S3 operations.

<a id="minio-bucket-versioning-delete"></a>

### Versioned Delete Operations {#versioned-delete-operations}

Performing a `DELETE` operation on a versioned object creates a 0-byte `DeleteMarker` as the latest version of that object. For objects where the latest version is a `DeleteMarker`, clients must specify versioning flags or identifiers to perform `GET/HEAD/LIST/DELETE` operations on a prior version of that object. The default server behavior omits `DeleteMarker` objects from consideration for unversioned operations.

MinIO can utilize [Lifecycle Management expiration rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) to automatically remove versioned objects permanently. Otherwise, use manual `DELETE` operations to permanently remove non-current versioned objects or `DeleteMarker` objects.

{{% alert color="info" %}}
**MinIO Implements Idempotent Delete Markers**

{{% alert color="info" %}}
**Changed: RELEASE.2022-08-22T23-53-06Z**

{{% /alert %}}

Standard S3 implementations can create multiple sequential delete markers for the same object when processing simple `DeleteObject` requests with no version identifier. See the S3 docs for details on [managing delete markers](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ManagingDelMarkers.html#RemDelMarker).

MinIO diverges from standard S3 implementation by avoiding this potential duplication of delete markers. When processing a `Delete` request with no version identifier, MinIO creates at most one Delete Marker for the specified object. MinIO **does not** share S3’s behavior in creating multiple sequential delete markers.
{{% /alert %}}

To permanently delete an object version, perform the `DELETE` operation and specify the version ID of the object to delete. Versioned delete operations are **irreversible**.

{{< doc-carousel >}}
{{< doc-card title="Deleting an Object" image="/images/retention/minio-versioning-delete-object.svg" alt="Deleting an Object" >}}
Performing a `DELETE` operation on a versioned object produces a `DeleteMarker` for that object.
{{< /doc-card >}}
{{< doc-card title="Reading a Deleted Object" image="/images/retention/minio-versioning-retrieve-deleted-object.svg" alt="Object with Multiple Versions" >}}
Clients by default retrieve the “latest” object version. MinIO returns a `404`-like response if the latest version is a `DeleteMarker`.
{{< /doc-card >}}
{{< doc-card title="Retrieve Previous Version of Deleted Object" image="/images/retention/minio-versioning-retrieve-version-before-delete.svg" alt="Retrieve Version of Deleted Object" >}}
Clients can retrieve any previous version of the object by specifying the version ID, even if the “Latest” version is a `DeleteMarker`.
{{< /doc-card >}}
{{< doc-card title="Delete a Specific Object Version" image="/images/retention/minio-versioning-delete-specific-version.svg" alt="Retrieve Version of Deleted Object" >}}
Clients can delete a specific object version by specifying the version ID as part of the `DELETE` operation. Deleting a specific version is **permanent** and does not result in the creation of a `DeleteMarker`.
{{< /doc-card >}}
{{< /doc-carousel >}}

The following [`mc`](/reference/minio-mc/#command-mc) commands operate on `DeleteMarkers` or versioned objects:

- Use [`mc ls --versions`](/reference/minio-mc/mc-ls/#mc.ls.-versions) to view all versions of an object, including delete markers.
- Use [`mc cp --version-id=UUID ...`](/reference/minio-mc/mc-cp/#mc.cp.-version-id) to retrieve the version of the “deleted” object with matching `UUID`.
- Use [`mc rm --version-id=UUID ...`](/reference/minio-mc/mc-rm/#mc.rm.-version-id) to delete the version of the object with matching `UUID`.
- Use [`mc rm --versions`](/reference/minio-mc/mc-rm/#mc.rm.-versions) to delete *all* versions of an object.

## Tutorials {#tutorials}

### Enable Bucket Versioning {#enable-bucket-versioning}

You can enable versioning using the MinIO Console, the MinIO [`mc`](/reference/minio-mc/#command-mc) CLI, or using an S3-compatible SDK.

Use the [`mc version enable`](/reference/minio-mc/mc-version-enable/#command-mc.version.enable) command to enable versioning on an existing bucket:

```shell
mc version enable ALIAS/BUCKET
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.
- Replace `BUCKET` with the [`target bucket`](/reference/minio-mc/mc-version-enable/#mc.version.enable.ALIAS) on which to enable versioning.

Objects created prior to enabling versioning have a `null` [version ID](#minio-bucket-versioning-id).

### Exclude a Prefix From Versioning {#exclude-a-prefix-from-versioning}

You can exclude certain [prefixes](/administration/concepts/#minio-admin-concepts-organize-objects) from versioning using the [MinIO Client](/reference/minio-mc/#minio-client). This is useful for Spark/Hadoop workloads or others that initially create objects with temporary prefixes.

{{% alert color="info" %}}
**Replication and Object Locking Require Versioning**

MinIO requires versioning to support [replication](/glossary/#term-replication). Objects in excluded prefixes do not replicate to any peer site or remote site.

MinIO does not support excluding prefixes from versioning on buckets with [object locking enabled](/administration/object-management/object-retention/#minio-object-locking).
{{% /alert %}}

- Use [`mc version enable`](/reference/minio-mc/mc-version-enable/#command-mc.version.enable) with the [`--excluded-prefixes`](/reference/minio-mc/mc-version-enable/#mc.version.enable.-excluded-prefixes) option:

  ```shell
  mc version enable --excluded-prefixes "prefix1, prefix2" ALIAS/BUCKET
  ```

  - Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.
  - Replace `BUCKET` with the name of the [bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingBucket.html) you want to exclude [prefixes](/administration/concepts/#minio-admin-concepts-organize-objects) for.

The list of [`--excluded-prefixes`](/reference/minio-mc/mc-version-enable/#mc.version.enable.-excluded-prefixes) prefixes match all objects containing the specified strings in their prefix or name, similar to a regular expression of the form `prefix*`. To match objects by prefix only, use `prefix/*`.

For example, the following command excludes any objects containing `_test` or `_temp` in their prefix or name from versioning:

> ```shell
> mc version enable --excluded-prefixes "_test, _temp" local/my-bucket
> ```

You can exclude up to 10 prefixes for each bucket. To add or remove prefixes, repeat the [`mc version enable`](/reference/minio-mc/mc-version-enable/#command-mc.version.enable) command with an updated list. The new list of prefixes replaces the previous one.

To view the currently excluded prefixes, use [`mc version info`](/reference/minio-mc/mc-version-info/#command-mc.version.info) with the `--json` option:

> ```shell
> mc version info ALIAS/BUCKET --json
> ```

The command output resembles the following, with the list of excluded prefixes in the `ExcludedPrefixes` property:

```shell
$ mc version info local/my-bucket --json
{
 "Op": "info",
 "status": "success",
 "url": "local/my-bucket",
 "versioning": {
  "status": "Enabled",
  "MFADelete": "",
  "ExcludedPrefixes": [
   "prefix1, prefix2"
  ]
 }
}
```

To disable prefix exclusion and resume versioning all prefixes, repeat the [`mc version enable`](/reference/minio-mc/mc-version-enable/#command-mc.version.enable) command without [`--excluded-prefixes`](/reference/minio-mc/mc-version-enable/#mc.version.enable.-excluded-prefixes):

> ```shell
> mc version enable ALIAS/BUCKET
> ```

### Exclude Folders from Versioning {#exclude-folders-from-versioning}

You can exclude folders from versioning using the [MinIO Client](/reference/minio-mc/#minio-client).

{{% alert color="info" %}}
**Replication and Object Locking Require Versioning**

MinIO requires versioning to support [replication](/glossary/#term-replication). Objects in excluded folders do not replicate to any peer site or remote site.

MinIO does not support excluding folders from versioning on buckets with [object locking enabled](/administration/object-management/object-retention/#minio-object-locking).
{{% /alert %}}

{{% alert color="info" %}}
**Object locking**

Buckets with [object locking enabled](/administration/object-management/object-retention/#minio-object-locking) require versioning and do not support excluding folders.
{{% /alert %}}

- Use [`mc version enable`](/reference/minio-mc/mc-version-enable/#command-mc.version.enable) with the [`--exclude-folders`](/reference/minio-mc/mc-version-enable/#mc.version.enable.-exclude-folders) option to exclude objects with names ending in `/` from versioning:

  ```shell
  mc version enable --exclude-folders ALIAS/BUCKET
  ```

  - Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.
  - Replace `BUCKET` with the [bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingBucket.html) you want to exclude [folders](/administration/concepts/#minio-admin-concepts-organize-objects) for.

To check whether folders are versioned for a bucket, use the [`mc version enable`](/reference/minio-mc/mc-version-enable/#command-mc.version.enable) command with the `--json` option. If the `ExcludeFolders` property is `true`, folders in that bucket are not versioned.

> ```shell
> mc version enable --excluded-prefixes ALIAS/BUCKET --json
> ```

The command output resembles the following:

```shell
$ mc version info local/my-bucket --json
{
 "Op": "info",
 "status": "success",
 "url": "local/my-bucket",
 "versioning": {
  "status": "Enabled",
  "MFADelete": "",
  "ExcludeFolders": true
 }
}
```

To disable folder exclusion and resume versioning all folders, repeat the [`mc version enable`](/reference/minio-mc/mc-version-enable/#command-mc.version.enable) command without [`--exclude-folders`](/reference/minio-mc/mc-version-enable/#mc.version.enable.-exclude-folders):

> ```shell
> mc version enable ALIAS/BUCKET
> ```

### Suspend Bucket Versioning {#suspend-bucket-versioning}

You can suspend bucket versioning at any time using he MinIO [`mc`](/reference/minio-mc/#command-mc) CLI or using an S3-compatible SDK.

Use the [`mc version suspend`](/reference/minio-mc/mc-version-suspend/#command-mc.version.suspend) command to enable versioning on an existing bucket:

```shell
mc version suspend ALIAS/BUCKET
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.
- Replace `BUCKET` with the [`target bucket`](/reference/minio-mc/mc-mb/#mc.mb.ALIAS) on which to disable versioning.

Objects created while versioning is suspended are assigned a `null` [version ID](#minio-bucket-versioning-id). Any mutations to an object while versioning is suspended result in overwriting that `null` versioned object. MinIO does not remove or otherwise alter existing versioned objects as part of suspending versioning. Clients can continue interacting with any existing object versions in the bucket.

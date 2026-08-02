---
title: "Object Deletion"
url: "/administration/object-management/object-delete/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="object-deletion"></a>
<a id="minio-object-delete"></a>

## Overview {#overview}

This page summarizes how a `DELETE` operation affects objects depending on the configuration of the bucket that contains the object.

Any combination of the following factors may impact how `DELETE` operations function:

- [Bucket versioning](/administration/object-management/object-versioning/#minio-bucket-versioning)
- [Object locking rules](/administration/object-management/object-retention/#minio-object-locking)
- [Object Lifecycle Management rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management)
- [Object tiering](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering)
- [Site](/operations/replication/multi-site-replication/#minio-site-replication-overview) or [bucket](/administration/bucket-replication/#minio-replication-behavior-delete) replication
- [Scanner](/operations/concepts/scanner/#minio-concepts-scanner)

## Permissions {#permissions}

MinIO uses a [policy based access control](/administration/identity-access-management/policy-based-access-control/#minio-policy) system for access management. The user or service account must provide the correct policy action and conditions to allow a `DELETE` for the bucket and object.

## Unversioned Objects {#unversioned-objects}

When performing a `DELETE` operation on an object in a bucket that does not have versioning enabled, the operation is straightforward. After verifying the user or service account has permission to perform the `DELETE` operation, MinIO permanently removes the object.

The user or service account requesting the delete action the action must have the [`s3:DeleteObject`](/administration/identity-access-management/policy-based-access-control/#policy-action.s3-DeleteObject) action permission for the bucket and object.

## Versioned Objects {#versioned-objects}

`DELETE` operations work differently when an object is versioned.

The user or service account must have the [`s3:DeleteObjectVersion`](/administration/identity-access-management/policy-based-access-control/#policy-action.s3-DeleteObjectVersion) action permission for the bucket and object.

### Delete operations on the current version {#delete-operations-on-the-current-version}

A `DELETE` operation on a versioned object that does not specify a version UUID results in the creation of a `DeleteMarker` placed as the `head` of the object.

In this scenario, MinIO does not actually remove the object or any of its versions from the disk. All existing versions of the object remain available to access by specifying the version’s UUID. When a `DeleteMarker` is the head for the object, MinIO does not serve the object for `GET` requests that do not specify a version ID. Instead, MinIO returns a `404`-like response.

You can find the UUID of object versions with [`mc ls --versions`](/reference/minio-mc/mc-ls/#mc.ls.-versions).

To remove the current version of the object from the drive, find the UUID of the version, and then use [`mc rm --version-id=UUID ...`](/reference/minio-mc/mc-rm/#mc.rm.-version-id) to delete the current version. In this scenario, the immediately preceding version of the object then becomes the current version of the object served for `GET` requests of the object with no UUID specified.

{{% alert color="danger" %}}
**Warning**

Specifying a `version-id` in a DELETE operation is irreversible. MinIO removes the specified version from the drive and **cannot** retrieve it.
{{% /alert %}}

### Delete operations on a prior version {#delete-operations-on-a-prior-version}

To delete prior versions of an object, specify the version’s UUID. You can retrieve the version UUID with [`mc ls --versions`](/reference/minio-mc/mc-ls/#mc.ls.-versions). When the `DELETE` request specifies a `version-id` and the user has the correct permissions to delete the object version`, MinIO permanently removes the specified version from the drive.

{{% alert color="danger" %}}
**Warning**

Specifying a `version-id` in a DELETE operation is irreversible. MinIO removes the specified version from the drive and **cannot** retrieve it.
{{% /alert %}}

### Delete all versions {#delete-all-versions}

Use [`mc rm --versions`](/reference/minio-mc/mc-rm/#mc.rm.-versions) to delete *all* versions of an object. This is irreversible.

## Lifecycle Management Expiration {#lifecycle-management-expiration}

You can define one or more [lifecycle management expiration rule(s)](/administration/object-management/create-lifecycle-management-expiration-rule/#minio-lifecycle-management-create-expiry-rule) to expire objects after a certain version number count or a certain period of time. When more versions exist than the rule specifies, or when a version is older than specified, MinIO permanently removes the object version from the drive.

These rules rely on the [scanner](/operations/concepts/scanner/#minio-concepts-scanner) to process the rule on the bucket. The scanner operates as a lower priority continuous process where `READ` and `WRITE` actions are preferred. Because of this, object versions that meet the requirements for expiration may not immediately be removed from MinIO.

See the [scanner](/operations/concepts/scanner/#minio-concepts-scanner) page for more details on how the scanner works and configuration options.

`DeleteMarkers` are their own objects. Lifecycle rules can remove `DeleteMarkers` that are the only remaining versions of their objects.

{{% alert color="info" %}}
**Changed: MinIO**

RELEASE.2024-05-01T01-11-10Z
{{% /alert %}}

With `JSON`, lifecycle rules can remove all versions of a deleted object after a specified number of days.

## Retained Objects {#retained-objects}

MinIO protects objects subject to a [locking rule](/administration/object-management/object-retention/#minio-object-locking) from being overwritten or deleted. These rules require that objects be retained until either the rule expires or is removed.

`DELETE` operations on locked objects without a specified version result in the creation of a *DeleteMarker* for the object. However, the object versions themselves are retained as required by the lock.

`DELETE` operations that specify an object version are subject to the retention rules. MinIO protects object versions subject to a lock from being overwritten or deleted until the lock expires or is removed.

## Replicated Objects {#replicated-objects}

Replication duplicates objects from one location to another. MinIO supports replication at the bucket level or the cluster (“site”) level.

Delete operations may or may not replicate, depending on the type of replication and how the replication is configured.

### Site Replication {#site-replication}

For clusters with [multi-site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview) enabled, MinIO replicates all `delete` operations performed on any cluster to each of the other clusters in the peer group.

Delete behavior on any single peer follows the same processes as any MinIO deployment.

### Bucket Replication {#bucket-replication}

With [bucket replication](/administration/bucket-replication/#minio-bucket-replication), MinIO supports replicating delete operations between a source bucket and a configured remote bucket. MinIO synchronizes deleting specific object versions *and* new [delete markers](https://docs.aws.amazon.com/AmazonS3/latest/userguide/delete-marker-replication.html). Delete operation replication uses the same [replication process](/administration/bucket-replication/#minio-replication-process) as all other replication operations.

MinIO requires *explicitly enabling* versioned deletes and delete marker replication. Use the [`mc replicate add --replicate`](/reference/minio-mc/mc-replicate-add/#mc.replicate.add.-replicate) field to specify either `delete` and `delete-marker` or both to enable versioned deletes and delete marker replication, respectively. To enable both, specify both strings using a comma separator: `delete,delete-marker`.

For delete marker replication, MinIO begins the replication process after a delete operation creates the delete marker. MinIO uses the `X-Minio-Replication-DeleteMarker-Status` metadata field for tracking delete marker replication status. In [active-active](/administration/bucket-replication/enable-server-side-two-way-bucket-replication/#minio-bucket-replication-serverside-twoway) replication configurations, MinIO may produce duplicate delete markers if both clusters concurrently create a delete marker for an object *or* if one or both clusters were down before the replication event synchronized.

For replicating the deletion of a specific object version, MinIO marks the object version as `PENDING` until replication completes. Once the remote target deletes that object version, MinIO deletes the object version on the source. While this process ensures near-synchronized version deletion, it may result in listing operations returning the object version after the initial delete operation. MinIO uses the `X-Minio-Replication-Delete-Status` for tracking delete version replication status.

MinIO only replicates explicit client-driven delete operations. MinIO does *not* replicate objects deleted by [lifecycle management expiration rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration). For [active-active](/administration/bucket-replication/enable-server-side-two-way-bucket-replication/#minio-bucket-replication-serverside-twoway) configurations, set the same expiration rules on *all* of of the replication buckets to ensure consistent application of object expiration.

{{% details title="MinIO Trims Empty Object Prefixes on Source and Remote Bucket" closed="true" %}}
If a delete operation removes the last object in a bucket prefix, MinIO recursively removes each empty part of the prefix up to the bucket root. MinIO only applies the recursive removal to prefixes created *implicitly* as part of object write operations. MinIO does not recursively remove prefixes created using an explicit directory creation command, such as [`mc mb`](/reference/minio-mc/mc-mb/#command-mc.mb).

If a replication rule enables replication delete operations, the replication process *also* applies the implicit prefix trimming behavior on the destination MinIO cluster.

For example, consider a bucket `photos` with the following object prefixes:

- `photos/2021/january/myphoto.jpg` // `2021/january/` created implicitly based on the object name
- `photos/2021/february/myotherphoto.jpg` // `2021/february/` created implicitly based on the object name
- `photos/NYE21/NewYears.jpg` // `NYE21/` explicitly created in the bucket

`photos/NYE21` is the *only* prefix explicitly created using [`mc mb`](/reference/minio-mc/mc-mb/#command-mc.mb). All other prefixes were *implicitly* created as part of writing the object located at that prefix.

- A command removes `myphoto.jpg`. MinIO automatically trims the empty `/january/` prefix.
- A command then removes the `myotherphoto.jpg`. MinIO automatically trims the `/february/` prefix *and* the now-empty `/2021` prefix.
- A command removes the `NewYears.jpg` object. MinIO leaves the `/NYE21/` prefix remains in place since it was *explicitly* created.
{{% /details %}}

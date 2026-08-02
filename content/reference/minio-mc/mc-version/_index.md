---
title: "mc version"
url: "/reference/minio-mc/mc-version/"
weight: 430
icon: fa-solid fa-code-branch
minio_origin: true
silo_modified: false
---

<a id="mc-version"></a>

<a id="command-mc.version"></a>

## Description {#description}

The [`mc version`](#command-mc.version) commands enable, disable, and retrieve the [versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) status for a MinIO bucket.

For more information about object versioning in MinIO, see [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning).

[`mc version`](#command-mc.version) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-version-enable/#command-mc.version.enable"><code>enable</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-version-enable/#command-mc.version.enable"><code>mc version enable</code></a> command enables versioning on the specified bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-version-info/#command-mc.version.info"><code>info</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-version-info/#command-mc.version.info"><code>mc version info</code></a> command returns the versioning status for the specified bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-version-suspend/#command-mc.version.suspend"><code>suspend</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-version-suspend/#command-mc.version.suspend"><code>mc version suspend</code></a> command disables versioning on the specified bucket.</p></td>
    </tr>
  </tbody>
</table>

## Behavior {#behavior}

### Object Locking Enables Bucket Versioning {#object-locking-enables-bucket-versioning}

While bucket versioning is disabled by default, configuring object locking on a bucket or an object in that bucket automatically enables versioning for the bucket. See [`mc retention`](/reference/minio-mc/mc-retention/#command-mc.retention) for more information on configuring object locking.

### Bucket Versioning with Existing Data {#bucket-versioning-with-existing-data}

Enabling bucket versioning on a bucket with existing data immediately creates a null value version ID for each unversioned object.

Disabling bucket versioning on a bucket with existing versioned data does *not* remove any versioned objects. Applications can continue to access versioned data after disabling bucket versioning. Use [`mc rm --versions ALIAS/BUCKET/OBJECT`](/reference/minio-mc/mc-rm/#mc.rm.-versions) to delete an object *and* all its versions.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

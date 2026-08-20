---
title: "mc quota clear"
url: "/reference/deprecated/mc-quota-clear/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/deprecated/mc-quota-clear.rst
upstream_modified: false
---

<a id="mc-quota-clear"></a>

<a id="command-mc.quota.clear"></a>

> [!NOTE]
> **Changed: RELEASE.2022-12-13T00-23-28Z**
>
> `mc quota clear` replaced `mc admin bucket quota --clear`.

> [!NOTE]
> **Changed: RELEASE.2024-07-31T15-58-33Z**
>
> `mc quota clear` is deprecated.

## Description {#description}

The [`mc quota clear`](#command-mc.quota.clear) command removes a configured storage quota for a bucket.

## Examples {#examples}

### Clear Configured Bucket Quota {#clear-configured-bucket-quota}

Use [`mc quota clear`](#command-mc.quota.clear) flag to remove the quota from a bucket.

```shell
mc quota clear TARGET/BUCKET
```

- Replace `TARGET` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment. Replace `BUCKET` with the name of the bucket on which to clear the quota.

## Syntax {#syntax}

[`mc quota clear`](#command-mc.quota.clear) has the following syntax:

```shell
mc quota clear TARGET [ARGUMENTS]
```

[`mc quota clear`](#command-mc.quota.clear) supports the following arguments:

#### `TARGET` {#mc.quota.clear.TARGET}

*mc-cmd*

*Required*

The full path to the bucket for which the command creates the quota. Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment as a prefix to the path. For example:

```shell
mc quota clear play/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

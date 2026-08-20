---
title: "mc quota info"
url: "/reference/deprecated/mc-quota-info/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/deprecated/mc-quota-info.rst
upstream_modified: false
---

<a id="mc-quota-info"></a>

<a id="command-mc.quota.info"></a>

> [!NOTE]
> **Changed: RELEASE.2022-12-13T00-23-28Z**
>
> `mc quota info` replaced `mc admin bucket quota`.

> [!NOTE]
> **Changed: RELEASE.2024-07-31T15-58-33Z**
>
> `mc quota info` is deprecated.

## Description {#description}

The [`mc quota info`](#command-mc.quota.info) command displays the currently configured quota for a bucket.

## Examples {#examples}

### Retrieve Bucket Quota Configuration {#retrieve-bucket-quota-configuration}

Use [`mc quota info`](#command-mc.quota.info) to retrieve the current quota configuration for a bucket:

```shell
mc quota info TARGET/BUCKET
```

Replace `TARGET` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment. Replace `BUCKET` with the name of the bucket on which to retrieve the quota.

## Syntax {#syntax}

[`mc quota info`](#command-mc.quota.info) has the following syntax:

```shell
mc quota info TARGET
```

[`mc quota info`](#command-mc.quota.info) supports the following arguments:

#### `TARGET` {#mc.quota.info.TARGET}

*mc-cmd*

*Required*

The full path to the bucket for which the command creates the quota. Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment as a prefix to the path. For example:

```shell
mc quota play/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

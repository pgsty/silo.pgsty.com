---
title: "mc admin bucket quota"
url: "/reference/deprecated/mc-admin-bucket-quota/"
weight: 110
minio_origin: true
silo_modified: false
---

<a id="mc-admin-bucket-quota"></a>

<a id="command-mc.admin.bucket.quota"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-13T00-23-28Z**

`mc admin bucket quota` replaced by:

- [`mc quota set`](/reference/deprecated/mc-quota-set/#command-mc.quota.set)
- [`mc quota info`](/reference/deprecated/mc-quota-info/#command-mc.quota.info)
- [`mc quota clear`](/reference/deprecated/mc-quota-clear/#command-mc.quota.clear)
{{% /alert %}}

## Description {#description}

The [`mc admin bucket quota`](#command-mc.admin.bucket.quota) command manages per-bucket storage quotas.

{{% alert color="info" %}}
**Use `mc admin` on MinIO Deployments Only**

MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.
{{% /alert %}}

<a id="mc-admin-bucket-quota-units"></a>

### Units of Measurement {#units-of-measurement}

The [`mc admin bucket quota --hard`](#mc.admin.bucket.quota.-hard) flag accepts the following case-insensitive suffixes to represent the unit of the specified size value:

| Suffix | Unit Size |
| --- | --- |
| `k` | KB (Kilobyte, 1000 Bytes) |
| `m` | MB (Megabyte, 1000 Kilobytes) |
| `g` | GB (Gigabyte, 1000 Megabytes) |
| `t` | TB (Terrabyte, 1000 Gigabytes) |
| `ki` | KiB (Kibibyte, 1024 Bites) |
| `mi` | MiB (Mebibyte, 1024 Kibibytes) |
| `gi` | GiB (Gibibyte, 1024 Mebibytes) |
| `ti` | TiB (Tebibyte, 1024 Gibibytes) |

Omitting the suffix defaults to `bytes`.

## Examples {#examples}

### Configure a Hard Quota on a Bucket {#configure-a-hard-quota-on-a-bucket}

Use [`mc admin bucket quota`](#command-mc.admin.bucket.quota) with the [`--hard`](#mc.admin.bucket.quota.-hard) flag to specify a hard quota on a bucket. Hard quotas prevent the bucket size from growing past the specified limit.

```shell
mc admin bucket quota TARGET/BUCKET --hard LIMIT
```

- Replace `TARGET` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment. Replace `BUCKET` with the name of the bucket on which to set the hard quota.
- Replace `LIMIT` with the maximum size to which the bucket can grow. For example, to set a hard limit of 10 Terrabytes, specify `10t`. See [Units of Measurement](#mc-admin-bucket-quota-units) for supported units.

### Retrieve Bucket Quota Configuration {#retrieve-bucket-quota-configuration}

Use [`mc admin bucket quota`](#command-mc.admin.bucket.quota) to retrieve the current quota configuration for a bucket:

```shell
mc admin bucket quota TARGET/BUCKET
```

Replace `TARGET` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment. Replace `BUCKET` with the name of the bucket on which to retrieve the quota.

### Clear Configured Bucket Quota {#clear-configured-bucket-quota}

Use [`mc admin bucket quota`](#command-mc.admin.bucket.quota) with the [`--clear`](#mc.admin.bucket.quota.-clear) flag to clear all quotas from a bucket.

```shell
mc admin bucket quota TARGET/BUCKET --clear
```

- Replace `TARGET` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment. Replace `BUCKET` with the name of the bucket on which to clear the quota.

## Syntax {#syntax}

[`mc admin bucket quota`](#command-mc.admin.bucket.quota) has the following syntax:

```shell
mc admin bucket quota TARGET [ARGUMENTS]
```

[`mc admin bucket quota`](#command-mc.admin.bucket.quota) supports the following arguments:

#### `TARGET` {#mc.admin.bucket.quota.TARGET}

*mc-cmd*

The full path to the bucket for which the command creates the quota. Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment as a prefix to the path. For example:

```shell
mc admin bucket quota play/mybucket
```

Omit all other arguments to return the current quota settings for the specified bucket.

#### `--hard` {#mc.admin.bucket.quota.-hard}

*mc-cmd*

Sets a maximum limit to the bucket storage size. The MinIO server rejects any incoming `PUT` request whose contents would exceed the bucket’s configured quota.

For example, a hard limit of `10GB` would prevent adding any additional objects if the bucket reaches `10GB` of size.

See [Units of Measurement](#mc-admin-bucket-quota-units) for supported unit sizes.

#### `--clear` {#mc.admin.bucket.quota.-clear}

*mc-cmd*

Clears all quotas configured for the bucket.

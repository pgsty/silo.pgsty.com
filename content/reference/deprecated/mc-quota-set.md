---
title: "mc quota set"
url: "/reference/deprecated/mc-quota-set/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="mc-quota-set"></a>

<a id="command-mc.quota.set"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-13T00-23-28Z**

`mc quota set` replaced `mc admin bucket quota --hard`.
{{% /alert %}}

{{% alert color="info" %}}
**Changed: RELEASE.2024-07-31T15-58-33Z**

`mc quota set` is deprecated.
{{% /alert %}}

## Description {#description}

The [`mc quota set`](#command-mc.quota.set) assigns a hard quota limit to a bucket beyond which MinIO does not allow writes.

### Units of Measurement {#units-of-measurement}

The [`mc quota set --size`](#mc.quota.set.-size) flag accepts the following **case-insensitive** suffixes to represent the unit of the specified size value:

| Suffix | Unit Size |
| --- | --- |
| `k` | KB (Kilobyte, 1000 Bytes) |
| `m` | MB (Megabyte, 1000 Kilobytes) |
| `g` | GB (Gigabyte, 1000 Megabytes) |
| `t` | TB (Terabyte, 1000 Gigabytes) |
| `ki` or `kib` | KiB (Kibibyte, 1024 Bites) |
| `mi` or `mib` | MiB (Mebibyte, 1024 Kibibytes) |
| `gi` or `gib` | GiB (Gibibyte, 1024 Mebibytes) |
| `ti` or `tib` | TiB (Tebibyte, 1024 Gibibytes) |

Omitting a suffix defaults to `bytes`.

## Examples {#examples}

### Configure a Hard Quota on a Bucket {#configure-a-hard-quota-on-a-bucket}

Use [`mc quota set`](#command-mc.quota.set) with the [`--size`](#mc.quota.set.-size) flag to specify a hard quota on a bucket. Hard quotas prevent the bucket size from growing past the specified limit.

```shell
mc quota set TARGET/BUCKET --size LIMIT
```

- Replace `TARGET` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment. Replace `BUCKET` with the name of the bucket on which to set the hard quota.
- Replace `LIMIT` with the maximum size to which the bucket can grow as an integer and, as desired, a suffix. For example, to set a hard limit of 10 Terabytes, specify `10t`.

## Syntax {#syntax}

[`mc quota set`](#command-mc.quota.set) has the following syntax:

```shell
mc quota set TARGET --size LIMIT
```

[`mc quota set`](#command-mc.quota.set) supports the following arguments:

#### `TARGET` {#mc.quota.set.TARGET}

*mc-cmd*

*Required*

The full path to the bucket for which the command creates the quota. Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment as a prefix to the path. For example:

```shell
mc quota set play/mybucket --size 10Gi
```

#### `--size` {#mc.quota.set.-size}

*mc-cmd*

*Required*

Sets a maximum limit to the bucket storage size. The MinIO server rejects any incoming `PUT` request whose contents would exceed the bucket’s configured quota.

For example, a hard limit of `10G` would prevent adding any additional objects if the bucket reaches 10 gigabytes of size.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

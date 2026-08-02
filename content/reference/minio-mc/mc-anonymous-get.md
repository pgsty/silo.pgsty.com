---
title: "mc anonymous get"
url: "/reference/minio-mc/mc-anonymous-get/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="mc-anonymous-get"></a>
<a id="minio-mc-policy-get"></a>

<a id="command-mc.anonymous.get"></a>

## Syntax {#syntax}

The [`mc anonymous get`](#command-mc.anonymous.get) command gets the anonymous (i.e. unauthenticated or public) access [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) for a bucket.

Buckets with anonymous policies allow clients to access the bucket contents and perform actions consistent with the specified policy without [authentication](/administration/identity-access-management/#minio-authentication-and-identity-management).

To get the [JSON policy](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-iam-policies) assigned to the bucket, use the [`mc anonymous get-json`](/reference/minio-mc/mc-anonymous-get-json/#command-mc.anonymous.get-json) command.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command retrieves the anonymous access policy for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc anonymous get myminio/mydata
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] policy get ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.anonymous.get.ALIAS}

*mc-cmd*

*Required* The full path to the bucket or bucket prefix for which the command retrieves the anonymous bucket policy.

Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO or other S3-compatible service *and* the full path to the bucket or bucket prefix. For example:

```shell
mc anonymous get public play/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Get Anonymous Policy for Bucket {#get-anonymous-policy-for-bucket}

Use [`mc anonymous get`](#command-mc.anonymous.get) to get the anonymous policy for a bucket:

```shell
mc anonymous get ALIAS/PATH
```

- Replace [`ALIAS`](#mc.anonymous.get.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.anonymous.get.ALIAS) with the destination bucket.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

---
title: "mc anonymous set-json"
url: "/reference/minio-mc/mc-anonymous-set-json/"
weight: 60
minio_origin: true
silo_modified: false
---

<a id="mc-anonymous-set-json"></a>
<a id="minio-mc-policy-set-json"></a>

<a id="command-mc.anonymous.set-json"></a>

## Syntax {#syntax}

The [`mc anonymous set-json`](#command-mc.anonymous.set-json) command sets anonymous (i.e. unauthenticated or public) access [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) for a bucket using using an IAM [JSON policy document](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-iam-policies).

Buckets with anonymous policies allow clients to access the bucket contents and perform actions consistent with the specified policy without [authentication](/administration/identity-access-management/#minio-authentication-and-identity-management).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command applies the JSON-formatted anonymous policy to the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc anonymous set-json ~/mydata-anonymous.json myminio/mydata
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] set-json POLICY ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `POLICY` {#mc.anonymous.set-json.POLICY}

*mc-cmd*

*Required* The path to the JSON-formatted policy to assign to the specified `ALIAS`.

##### `ALIAS` {#mc.anonymous.set-json.ALIAS}

*mc-cmd*

*Required* The full path to the bucket or bucket prefix to which the command applies the specified [`POLICY`](#mc.anonymous.set-json.POLICY).

Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO or other S3-compatible service *and* the full path to the bucket or bucket prefix. For example:

```shell
mc anonymous set-json public play/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Set Anonymous Policy for Bucket {#set-anonymous-policy-for-bucket}

Use [`mc anonymous set-json`](#command-mc.anonymous.set-json) to set the anonymous policy for a bucket:

```shell
mc anonymous set-json POLICY ALIAS/PATH
```

- Replace [`POLICY`](#mc.anonymous.set-json.POLICY) with a supported [`POLICY`](#mc.anonymous.set-json.POLICY).
- Replace [`ALIAS`](#mc.anonymous.set-json.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.anonymous.set-json.ALIAS) with the destination bucket.

### Remove Anonymous Policy for Bucket {#remove-anonymous-policy-for-bucket}

Use [`mc anonymous set`](/reference/minio-mc/mc-anonymous-set/#command-mc.anonymous.set) to clear the anonymous policy for a bucket:

```shell
mc anonymous set none ALIAS/PATH
```

- Replace [`ALIAS`](/reference/minio-mc/mc-anonymous-set/#mc.anonymous.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](/reference/minio-mc/mc-anonymous-set/#mc.anonymous.set.ALIAS) with the destination bucket.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

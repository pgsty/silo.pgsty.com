---
title: "mc anonymous set"
url: "/reference/minio-mc/mc-anonymous-set/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-anonymous-set"></a>
<a id="minio-mc-anonymous-set"></a>
<a id="minio-mc-policy-set"></a>

<a id="command-mc.anonymous.set"></a>

## Syntax {#syntax}

The [`mc anonymous set`](#command-mc.anonymous.set) command sets anonymous (i.e. unauthenticated or public) access [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) for a bucket.

Buckets with anonymous policies allow clients to access the bucket contents and perform actions consistent with the specified policy without [authentication](/administration/identity-access-management/#minio-authentication-and-identity-management).

To set anonymous bucket policies using an IAM [JSON policy](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-policy-language-overview.html), use the [`mc anonymous set-json`](/reference/minio-mc/mc-anonymous-set-json/#command-mc.anonymous.set-json) command.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command sets anonymous access policies for several buckets on the `myminio` MinIO deployment:

```shell
mc anonymous set upload myminio/uploads
mc anonymous set download myminio/downloads
mc anonymous set public myminio/public
```

Applications can perform the following operations without authentication:

- `PUT` objects to `myminio/uploads` and `myminio/public`.
- `GET` objects from `myminio/downloads` and `myminio/public`.
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] policy set PERMISSION ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `PERMISSION` {#mc.anonymous.set.PERMISSION}

*mc-cmd*

*Required* Name of the policy to assign to the specified `ALIAS`. Specify one of the following values:

- `none` - Disable anonymous access to the `ALIAS`.
- `download` - Enable download-only access to the `ALIAS`.
- `upload` - Enable upload-only access to the `ALIAS`.
- `public` - Enable download and upload access to the `ALIAS`.

##### `ALIAS` {#mc.anonymous.set.ALIAS}

*mc-cmd*

*Required* The full path to the bucket or bucket prefix to which the command applies the specified [`PERMISSION`](#mc.anonymous.set.PERMISSION).

Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO or other S3-compatible service *and* the full path to the bucket or bucket prefix. For example:

```shell
mc anonymous set public play/mybucket
```

Specify a bucket prefix to set the policy on only that prefix. For example, this command sets distinct anonymous bucket policies on the `mybucket/downloads` and `mybucket/uploads` prefixes:

```shell
mc anonymous set download play/mybucket/downloads
mc anonymous set upload play/mybucket/uploads
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Set Anonymous Policy for Bucket {#set-anonymous-policy-for-bucket}

Use [`mc anonymous set`](#command-mc.anonymous.set) to set the anonymous policy for a bucket:

```shell
mc anonymous set POLICY ALIAS/PATH
```

- Replace [`POLICY`](#mc.anonymous.set.PERMISSION) with a supported [`permission`](#mc.anonymous.set.PERMISSION).
- Replace [`ALIAS`](#mc.anonymous.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.anonymous.set.ALIAS) with the destination bucket.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

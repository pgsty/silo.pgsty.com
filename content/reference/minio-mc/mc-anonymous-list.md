---
title: "mc anonymous list"
url: "/reference/minio-mc/mc-anonymous-list/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="mc-anonymous-list"></a>
<a id="minio-mc-policy-list"></a>

<a id="command-mc.anonymous.list"></a>

## Syntax {#syntax}

The [`mc anonymous list`](#command-mc.anonymous.list) retrieves all anonymous (i.e. unauthenticated or public) access policies for a bucket.

Buckets with anonymous policies allow clients to access the bucket contents and perform actions consistent with the specified policy without [authentication](/administration/identity-access-management/#minio-authentication-and-identity-management).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command lists all anonymous access policies for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc anonymous list myminio/mydata
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.anonymous.list.ALIAS}

*mc-cmd*

*Required* The full path to the bucket or bucket prefix for which the command retrieves the anonymous bucket policies.

Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO or other S3-compatible service *and* the full path to the bucket or bucket prefix. For example:

```shell
mc anonymous list public play/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### List Anonymous Policies for Bucket {#list-anonymous-policies-for-bucket}

Use [`mc anonymous list`](#command-mc.anonymous.list) to list the anonymous policies for a bucket:

```shell
mc anonymous list ALIAS/PATH
```

- Replace [`ALIAS`](/reference/minio-mc/mc-anonymous-get/#mc.anonymous.get.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](/reference/minio-mc/mc-anonymous-get/#mc.anonymous.get.ALIAS) with the destination bucket.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

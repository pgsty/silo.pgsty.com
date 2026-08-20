---
title: "mc anonymous get-json"
url: "/reference/minio-mc/mc-anonymous-get-json/"
weight: 50
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-anonymous-get-json.rst
upstream_modified: false
---

<a id="mc-anonymous-get-json"></a>
<a id="minio-mc-policy-get-json"></a>

<a id="command-mc.anonymous.get-json"></a>

## Syntax {#syntax}

The [`mc anonymous get-json`](#command-mc.anonymous.get-json) command gets anonymous (i.e. unauthenticated or public) access [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) for a bucket.

Buckets with anonymous policies allow clients to access the bucket contents and perform actions consistent with the specified policy without [authentication](/administration/identity-access-management/#minio-authentication-and-identity-management).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command retrieves the JSON-formatted anonymous policy for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc anonymous get-json myminio/mydata
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] get-json ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.anonymous.get-json.ALIAS}

*mc-cmd*

*Required* The full path to the bucket or bucket prefix for which to get the anonymous bucket policy.

Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO or other S3-compatible service *and* the full path to the bucket or bucket prefix. For example:

```shell
mc anonymous get-json public play/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Get Anonymous Policy for Bucket {#get-anonymous-policy-for-bucket}

Use [`mc anonymous get-json`](#command-mc.anonymous.get-json) to get the anonymous policy for a bucket:

```shell
mc anonymous get-json ALIAS/PATH
```

- Replace [`ALIAS`](#mc.anonymous.get-json.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.anonymous.get-json.ALIAS) with the destination bucket.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

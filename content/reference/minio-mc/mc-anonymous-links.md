---
title: "mc anonymous links"
url: "/reference/minio-mc/mc-anonymous-links/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-anonymous-links.rst
upstream_modified: false
---

<a id="mc-anonymous-links"></a>
<a id="minio-mc-policy-links"></a>

<a id="command-mc.anonymous.links"></a>

## Syntax {#syntax}

The [`mc anonymous links`](#command-mc.anonymous.links) retrieves the HTTP URL for anonymous (i.e. unauthenticated or public) access to a bucket.

Buckets with anonymous policies allow clients to access the bucket contents and perform actions consistent with the specified policy without [authentication](/administration/identity-access-management/#minio-authentication-and-identity-management).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command retrieves HTTP URLs for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc anonymous links --recursive myminio/mydata
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] policy links   \
                 [--recursive]  \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.anonymous.links.ALIAS}

*mc-cmd*

*Required* The full path to the bucket or bucket prefix for which the command retrieves the anonymous bucket policies.

Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO or other S3-compatible service *and* the full path to the bucket or bucket prefix. For example:

```shell
mc anonymous links public [FLAGS] play/mybucket
```

##### `--recursive` {#mc.anonymous.links.-recursive}

*mc-cmd*

*Optional* Retrieve the HTTP links recursively.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### List Anonymous Policies for Bucket {#list-anonymous-policies-for-bucket}

Use [`mc anonymous links`](#command-mc.anonymous.links) to links the anonymous policies for a bucket:

```shell
mc anonymous links ALIAS/PATH
```

- Replace [`ALIAS`](/reference/minio-mc/mc-anonymous-get/#mc.anonymous.get.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](/reference/minio-mc/mc-anonymous-get/#mc.anonymous.get.ALIAS) with the destination bucket.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

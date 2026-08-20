---
title: "mc encrypt info"
url: "/reference/minio-mc/mc-encrypt-info/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-encrypt-info.rst
upstream_modified: false
---

<a id="mc-encrypt-info"></a>
<a id="minio-mc-encrypt-info"></a>

<a id="command-mc.encrypt.info"></a>

## Syntax {#syntax}

The [`mc encrypt info`](#command-mc.encrypt.info) command returns the current default encryption settings for a bucket.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command returns the default encryption setting for the `mydata` bucket on the `myminio` MinIO deployment.

```shell
mc encrypt info myminio/mydata
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] encrypt info ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.encrypt.info.ALIAS}

*mc-cmd*

The full path to the bucket on which to retrieve the default SSE mode. Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment as the prefix to the ALIAS path. For example:

```shell
mc encrypt info play/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Retrieve the Automatic Server-Side Encryption Settings for a Bucket {#retrieve-the-automatic-server-side-encryption-settings-for-a-bucket}

{{< tabs group="example-syntax" >}}
{{< tab label="Example" value="example" >}}
```shell
 mc encrypt info myminio/data
```
{{< /tab >}}
{{< tab label="Syntax" value="syntax" >}}
```shell
mc encrypt info ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment on which to configure automatic server-side bucket encryption.
{{< /tab >}}
{{< /tabs >}}

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

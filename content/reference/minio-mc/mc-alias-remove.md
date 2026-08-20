---
title: "mc alias remove"
url: "/reference/minio-mc/mc-alias-remove/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-alias-remove.rst
upstream_modified: false
---

<a id="mc-alias-remove"></a>
<a id="minio-mc-alias-remove"></a>

<a id="command-mc.alias.remove"></a>

## Syntax {#syntax}

The [`mc alias remove`](#command-mc.alias.remove) removes an existing alias from the local **`mc`** configuration.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command removes the `myminio` [alias](/reference/minio-mc/mc-alias-set/#alias) for a MinIO deployment from the host machine:

```shell
mc alias remove myminio
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The [`mc alias remove`](#command-mc.alias.remove) command has the following syntax:

```shell
mc [GLOBALFLAGS] alias remove ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.alias.remove.ALIAS}

*mc-cmd*

*Required* The alias to remove from the local **`mc`** configuration.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Remove an Alias from the `mc` Configuration {#remove-an-alias-from-the-mc-configuration}

Use [`mc alias remove`](#command-mc.alias.remove) to remove an existing alias from the **`mc`** configuration:

{{< tabs group="example-syntax" >}}
{{< tab label="Example" value="example" >}}
The following command removes the `myminio` alias.

```shell
mc alias remove myminio
```
{{< /tab >}}
{{< tab label="Syntax" value="syntax" >}}
```shell
mc alias remove ALIAS
```

Replace `ALIAS` with the name of the alias to remove.
{{< /tab >}}
{{< /tabs >}}

### Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

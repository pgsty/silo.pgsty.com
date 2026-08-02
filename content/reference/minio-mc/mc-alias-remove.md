---
title: "mc alias remove"
url: "/reference/minio-mc/mc-alias-remove/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="mc-alias-remove"></a>
<a id="minio-mc-alias-remove"></a>

<a id="command-mc.alias.remove"></a>

## Syntax {#syntax}

The [`mc alias remove`](#command-mc.alias.remove) removes an existing alias from the local **`mc`** configuration.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command removes the `myminio` [alias](/reference/minio-mc/mc-alias-set/#alias) for a MinIO deployment from the host machine:

```shell
mc alias remove myminio
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The [`mc alias remove`](#command-mc.alias.remove) command has the following syntax:

```shell
mc [GLOBALFLAGS] alias remove ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.alias.remove.ALIAS}

*mc-cmd*

*Required* The alias to remove from the local **`mc`** configuration.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Remove an Alias from the `mc` Configuration {#remove-an-alias-from-the-mc-configuration}

Use [`mc alias remove`](#command-mc.alias.remove) to remove an existing alias from the **`mc`** configuration:

{{< tabpane text=true persist=header >}}
{{% tab header="Example" %}}
The following command removes the `myminio` alias.

```shell
mc alias remove myminio
```
{{% /tab %}}
{{% tab header="Syntax" %}}
```shell
mc alias remove ALIAS
```

Replace `ALIAS` with the the name of the alias to remove.
{{% /tab %}}
{{< /tabpane >}}

### Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

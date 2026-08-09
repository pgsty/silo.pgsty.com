---
title: "mc alias list"
url: "/reference/minio-mc/mc-alias-list/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-alias-list"></a>
<a id="minio-mc-alias-list"></a>

<a id="command-mc.alias.list"></a>

## Syntax {#syntax}

The [`mc alias list`](#command-mc.alias.list) command lists all aliases in the local **`mc`** configuration.

The command output includes the configured access key and secret key associated to each alias.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command lists all [aliases](/reference/minio-mc/mc-alias-set/#alias) configured on the local host machine:

```shell
mc alias list
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The [`mc alias list`](#command-mc.alias.list) command has the following syntax:

```shell
mc [GLOBALFLAGS] alias list [ALIAS]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.alias.list.ALIAS}

*mc-cmd*

*Optional* The name of a specific alias to display.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### List All Configured Aliases {#list-all-configured-aliases}

{{< tabpane text=true persist=header >}}
{{% tab header="Example" %}}
The following [`mc alias list`](#command-mc.alias.list) command lists all configured aliases in the local **`mc`** configuration.

```shell
mc alias list
```

{{% /tab %}}
{{% tab header="Syntax" %}}

```shell
mc alias list
```

{{% /tab %}}
{{< /tabpane >}}

### List a Specific Alias {#list-a-specific-alias}

{{< tabpane text=true persist=header >}}
{{% tab header="Example" %}}
The following [`mc alias list`](#command-mc.alias.list) command lists the details of a specific alias in the local **`mc`** configuration.

```shell
mc alias list myminio
```

{{% /tab %}}
{{% tab header="Syntax" %}}

```shell
mc alias list ALIAS
```

- Replace `ALIAS` with the the name of the alias to return.
{{% /tab %}}
{{< /tabpane >}}

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

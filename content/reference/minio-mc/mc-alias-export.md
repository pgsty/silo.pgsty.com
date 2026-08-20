---
title: "mc alias export"
url: "/reference/minio-mc/mc-alias-export/"
weight: 50
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-alias-export.rst
upstream_modified: false
---

<a id="mc-alias-export"></a>
<a id="minio-mc-alias-export"></a>

<a id="command-mc.alias.export"></a>

> [!NOTE]
> **Added: mc.RELEASE.2023-11-15T22-45-58Z**

## Syntax {#syntax}

The [`mc alias export`](#command-mc.alias.export) command exports an alias configuration from the existing [configuration](/reference/minio-mc/#mc-configuration).

The command outputs the result to `STDOUT` where you can either capture the output as a file *or* perform further modifications to the output as necessary.

Use the [`mc alias import`](/reference/minio-mc/mc-alias-import/#command-mc.alias.import) command to import the resulting JSON configuration.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command exports an alias configuration from the existing host and outputs it to a file:

```shell
mc alias export play > play.json
```

The command outputs the file to Standard Out (`STDOUT`). You can alternatively pipe the output to a utility of your choice for further operations.
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The [`mc alias export`](#command-mc.alias.export) command has the following syntax:

```shell
mc [GLOBALFLAGS] alias export ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.alias.export.ALIAS}

*mc-cmd*

*Required*

The name of the alias to export.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### JSON Format {#json-format}

The command outputs a JSON object with the following schema:

```json
{
   "url" : "https://hostname:port",
   "accessKey": "<STRING>",
   "secretKey": "<STRING>",
   "api": "s3v4",
   "path": "auto"
}
```

You can use the [`mc alias import`](/reference/minio-mc/mc-alias-import/#command-mc.alias.import) to import the JSON document.

## Examples {#examples}

### Export and Transform an Alias {#export-and-transform-an-alias}

The following example exports the alias for the [play.min.io](https://play.min.io) sandbox. It then transforms the configuration using the [jq](https://jqlang.github.io/jq/) utility and creates a new alias from the modified configuration:

```shell
mc alias export play | jq '.accessKey = "minioadmin" | .secretKey = "minioadmin"' | mc alias import play-custom
```

### Back Up An Alias Configuration {#back-up-an-alias-configuration}

The following command exports an alias configuration to a JSON file. You can then back up that file using your preferred process.

```shell
mc alias export play > play-backup.json
```

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

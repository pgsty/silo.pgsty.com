---
title: "mc alias import"
url: "/reference/minio-mc/mc-alias-import/"
weight: 40
minio_origin: true
silo_modified: false
---

<a id="mc-alias-import"></a>
<a id="minio-mc-alias-import"></a>

<a id="command-mc.alias.import"></a>

## Syntax {#syntax}

The [`mc alias import`](#command-mc.alias.import) command imports an alias configuration from a JSON document.

You can use [`mc alias export`](/reference/minio-mc/mc-alias-export/#command-mc.alias.export) to create the necessary JSON for import.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command imports an alias configuration from a JSON document:

```shell
mc alias import newalias ./credentials.json
```

Use [`mc alias list newalias`](/reference/minio-mc/mc-alias-list/#command-mc.alias.list) to confirm the import succeeded.
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The [`mc alias import`](#command-mc.alias.import) command has the following syntax:

```shell
mc [GLOBALFLAGS] alias import ALIAS PATH|STDIN
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.alias.import.ALIAS}

*mc-cmd*

*Required*

The name of the alias to assign to the imported configuration.

##### `PATH` {#mc.alias.import.PATH}

*mc-cmd*

*Required*

The full path to the JSON object representing the alias configuration to import.

Mutually exclusive with the [`STDIN`](#mc.alias.import.STDIN) parameter.

##### `STDIN` {#mc.alias.import.STDIN}

*mc-cmd*

*Required*

Directs the command to use the Standard Input (STDIN) as the source of the JSON object for import.

Mutually exclusive with the [`PATH`](#mc.alias.import.PATH) parameter.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### JSON Format {#json-format}

The JSON object **must** have the following format:

```json
{
   "url" : "https://hostname:port",
   "accessKey": "<STRING>",
   "secretKey": "<STRING>",
   "api": "s3v4",
   "path": "auto"
}
```

You can use the [`mc alias export`](/reference/minio-mc/mc-alias-export/#command-mc.alias.export) command to export an existing alias from the local host configuration. Alternatively, you can manually extract the necessary JSOn fields from the [`mc`](/reference/minio-mc/#command-mc) [configuration file](/reference/minio-mc/#mc-configuration).

## Examples {#examples}

### Import an Alias Using Standard Input {#import-an-alias-using-standard-input}

The following example imports a custom alias for the [play.min.io](https://play.min.io) sandbox. You can modify this example to use user credentials you have already created or validated as existing on the sandbox:

```shell
echo '
{
 "url": "https://play.min.io",
 "accessKey": "minioadmin",
 "secretKey": "minioadmin",
 "api": "s3v4",
 "path": "auto"
}' | mc alias import play-minioadmin
```

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

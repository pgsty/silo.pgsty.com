---
title: "mc ilm import"
url: "/reference/deprecated/mc-ilm-import/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/deprecated/mc-ilm-import.rst
upstream_modified: false
---

<a id="mc-ilm-import"></a>
<a id="minio-mc-ilm-import"></a>

<a id="command-mc.ilm.import"></a>

> [!NOTE]
> **Changed: RELEASE.2022-12-24T15-21-38Z**
>
> `mc ilm import` replaced by [`mc ilm rule import`](/reference/minio-mc/mc-ilm-rule-import/#command-mc.ilm.rule.import).

## Syntax {#syntax}

The [`mc ilm import`](#command-mc.ilm.import) command imports an object lifecycle management configuration and applies it to a MinIO bucket.

The [`mc ilm import`](#command-mc.ilm.import) command imports from `STDIN` by default. You can input the contents from a `.json` file, such as one produced by [`mc ilm export`](/reference/deprecated/mc-ilm-export/#command-mc.ilm.export).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command imports the lifecycle management configuration from `mydata-lifecycle-config.json` and applies it to the `mydata` bucket on the `myminio` deployment:

```shell
mc ilm import myminio/mydata < mydata-lifecycle-config.json
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ilm import ALIAS < STDIN
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.ilm.import.ALIAS}

*mc-cmd*

*Required* The [alias](/reference/minio-mc/mc-alias-set/#alias) and full path to the bucket on the MinIO deployment into which to import object lifecycle management rules. For example:

```text
mc ilm import myminio/mydata < bucket-lifecycle.json
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Import the Bucket Lifecycle Management Configuration {#import-the-bucket-lifecycle-management-configuration}

{{< tabs group="example-syntax" >}}
{{< tab label="Example" value="example" >}}
The following command imports the bucket lifecycle management configuration from the `bucket-lifecycle.json` file:

```shell
mc ilm import myminio/mybucket < bucket-lifecycle.json
```
{{< /tab >}}
{{< tab label="Syntax" value="syntax" >}}
```shell
mc ilm import ALIAS < file.json
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment and the bucket into which to import object lifecycle management rules:

  `myminio/mydata`
- Replace `file.json` with the name of the file from which to import the lifecycle management rules.
{{< /tab >}}
{{< /tabs >}}

## Behavior {#behavior}

### Importing Configuration Overrides Existing Rules {#importing-configuration-overrides-existing-rules}

[`mc ilm import`](#command-mc.ilm.import) replaces the current bucket lifecycle management rules with those defined in the imported JSON configuration.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

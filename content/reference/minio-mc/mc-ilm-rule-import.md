---
title: "mc ilm rule import"
url: "/reference/minio-mc/mc-ilm-rule-import/"
weight: 40
minio_origin: true
silo_modified: false
---

<a id="mc-ilm-rule-import"></a>
<a id="minio-mc-ilm-rule-import"></a>

<a id="command-mc.ilm.rule.import"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

`mc ilm rule import` replaces `mc ilm import`.
{{% /alert %}}

## Syntax {#syntax}

The [`mc ilm rule import`](#command-mc.ilm.rule.import) command imports an object lifecycle management configuration and applies it to a MinIO bucket.

The [`mc ilm rule import`](#command-mc.ilm.rule.import) command imports from `STDIN` by default. You can input the contents from a `.json` file, such as one produced by [`mc ilm rule export`](/reference/minio-mc/mc-ilm-rule-export/#command-mc.ilm.rule.export).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command imports the lifecycle management configuration from `mydata-lifecycle-config.json` and applies it to the `mydata` bucket on the `myminio` deployment:

```shell
mc ilm rule import myminio/mydata < mydata-lifecycle-config.json
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ilm rule import ALIAS < STDIN
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.ilm.rule.import.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) and full path to the bucket on the MinIO deployment into which to import object lifecycle management rules. For example:

```text
mc ilm rule import myminio/mydata < bucket-lifecycle.json
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Import the Bucket Lifecycle Management Configuration {#import-the-bucket-lifecycle-management-configuration}

{{< tabpane text=true persist=header >}}
{{% tab header="Example" %}}
The following command imports the bucket lifecycle management configuration from the `bucket-lifecycle.json` file:

```shell
mc ilm rule import myminio/mybucket < bucket-lifecycle.json
```
{{% /tab %}}
{{% tab header="Syntax" %}}
```shell
mc ilm rule import ALIAS < file.json
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment and the bucket into which to import object lifecycle management rules:

  `myminio/mydata`
- Replace `file.json` with the name of the file from which to import the lifecycle management rules.
{{% /tab %}}
{{< /tabpane >}}

## Required Permissions {#required-permissions}

For permissions required to import rules, refer to the [required permissions](/reference/minio-mc/mc-ilm-rule/#minio-mc-ilm-rule-permissions) on the parent command.

## Behavior {#behavior}

### Importing Configuration Overrides Existing Rules {#importing-configuration-overrides-existing-rules}

[`mc ilm rule import`](#command-mc.ilm.rule.import) replaces the current bucket lifecycle management rules with those defined in the imported JSON configuration.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

---
title: "mc ilm rule export"
url: "/reference/minio-mc/mc-ilm-rule-export/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-ilm-rule-export.rst
upstream_modified: false
---

<a id="mc-ilm-rule-export"></a>
<a id="minio-mc-ilm-rule-export"></a>

<a id="command-mc.ilm.rule.export"></a>

> [!NOTE]
> **Changed: RELEASE.2022-12-24T15-21-38Z**
>
> `mc ilm rule export` replaces `mc ilm export`.

## Syntax {#syntax}

The [`mc ilm rule export`](#command-mc.ilm.rule.export) command exports the object lifecycle management configuration for a MinIO bucket.

The [`mc ilm rule export`](#command-mc.ilm.rule.export) command outputs to `STDOUT` by default. You can output the contents to a `.json` file for archival or ingestion using [`mc ilm rule import`](/reference/minio-mc/mc-ilm-rule-import/#command-mc.ilm.rule.import).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command exports the lifecycle management configuration of the `mydata` bucket on the `myminio` deployment to the `mydata-lifecycle-config.json` file:

```shell
mc ilm rule export myminio/mydata > mydata-lifecycle-config.json
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ilm rule export ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.ilm.rule.export.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) and full path to the bucket on the MinIO deployment for which to export object lifecycle management rules. For example:

```text
mc ilm rule export myminio/mydata > bucket-lifecycle.json
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Export the Bucket Lifecycle Management Configuration {#export-the-bucket-lifecycle-management-configuration}

{{< tabs group="example-syntax" >}}
{{< tab label="Example" value="example" >}}
The following command exports the bucket lifecycle management configuration to the `bucket-lifecycle.json` file:

```shell
mc ilm rule export myminio/mybucket > bucket-lifecycle.json
```
{{< /tab >}}
{{< tab label="Syntax" value="syntax" >}}
```shell
mc ilm rule export ALIAS > file.json
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment and the bucket for which to export object lifecycle management rules:

  `myminio/mydata`
- Replace `file.json` with the name of the file to which to export the lifecycle management rules.
{{< /tab >}}
{{< /tabs >}}

## Required Permissions {#required-permissions}

For permissions required to export a rule, refer to the [required permissions](/reference/minio-mc/mc-ilm-rule/#minio-mc-ilm-rule-permissions) on the parent command.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

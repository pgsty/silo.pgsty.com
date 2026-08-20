---
title: "mc replicate import"
url: "/reference/minio-mc/mc-replicate-import/"
weight: 90
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-replicate-import.rst
upstream_modified: false
---

<a id="mc-replicate-import"></a>
<a id="minio-mc-replicate-import"></a>

<a id="command-mc.replicate.import"></a>

## Syntax {#syntax}

The [`mc replicate import`](#command-mc.replicate.import) command imports JSON-formatted [replication rules](/administration/bucket-replication/#minio-bucket-replication-serverside) for a MinIO bucket from `STDIN`.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command imports the replication configuration for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc replicate import myminio/mydata < mydata-replication.json
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] import ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.replicate.import.ALIAS}

*mc-cmd*

*Required* the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment and full path to the bucket or bucket prefix for which to import the replication rules. For example:

```text
mc replicate import myminio/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Import Existing Replication Rules {#import-existing-replication-rules}

Use [`mc replicate import`](#command-mc.replicate.import) to import bucket replication rules:

```shell
mc replicate import ALIAS/PATH < bucket-replication-rules.json
```

- Replace [`ALIAS`](#mc.replicate.import.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`PATH`](#mc.replicate.import.ALIAS) with the path to the bucket or bucket prefix.

## Behavior {#behavior}

### Importing Configuration Overrides Existing Rules {#importing-configuration-overrides-existing-rules}

[`mc replicate import`](#command-mc.replicate.import) replaces the current bucket replication rules with those defined in the imported JSON configuration.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

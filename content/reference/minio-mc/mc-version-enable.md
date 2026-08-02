---
title: "mc version enable"
url: "/reference/minio-mc/mc-version-enable/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-version-enable"></a>
<a id="minio-mc-version-enable"></a>

<a id="command-mc.version.enable"></a>

## Syntax {#syntax}

The [`mc version enable`](#command-mc.version.enable) command enables versioning on the specified bucket.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command enables versioning for the `mybucket` bucket on the `myminio` MinIO deployment:

```shell
 mc version enable myminio/mybucket
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] version enable ALIAS                \
                                --exclude-folders    \
                                --excluded-prefixes
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.version.enable.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment and the full path to the bucket for which to enable versioning. For example:

```shell
mc version enable myminio/mybucket
```

##### `--exclude-folders` {#mc.version.enable.-exclude-folders}

*mc-cmd*

*Optional*

Disable versioning on all folders (objects whose name ends with `/`) in the specified bucket.

##### `--excluded-prefixes` {#mc.version.enable.-excluded-prefixes}

*mc-cmd*

*Optional*

Disable versioning on objects matching a list of prefixes, up to 10. The list of prefixes match all objects containing the specified strings in their prefix or name, similar to a regular expression of the form `prefix*`. To match objects by prefix only, use `prefix/*`.

For example, the following command excludes any objects containing `_test` or `_temp` in their prefix or name from versioning:

```shell
mc version enable --excluded-prefixes "_test, _temp" myminio/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Enable Bucket Versioning {#enable-bucket-versioning}

Use [`mc version enable`](#command-mc.version.enable) to enable versioning for a bucket:

```shell
mc version enable ALIAS/PATH
```

- Replace [`ALIAS`](#mc.version.enable.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.
- Replace [`PATH`](#mc.version.enable.ALIAS) with the bucket on which to enable versioning.

## Behavior {#behavior}

### Bucket Versioning with Existing Data {#bucket-versioning-with-existing-data}

Enabling bucket versioning on a bucket with existing data immediately creates a `NULL` value version ID for each unversioned object.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

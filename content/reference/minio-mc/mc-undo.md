---
title: "mc undo"
url: "/reference/minio-mc/mc-undo/"
weight: 410
minio_origin: true
silo_modified: false
---

<a id="mc-undo"></a>
<a id="minio-mc-undo"></a>

<a id="command-mc.undo"></a>

## Syntax {#syntax}

The [`mc undo`](#command-mc.undo) command reverses changes due to either a `PUT` or `DELETE` operation at a specified path.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command reverts the last three uploads and/or deletions of the `file.zip` object on the `myminio` deployment in the `data` bucket:

```shell
mc undo myminio/data/file.zip --last 3
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] undo                \
                 TARGET              \
                 [--action "type"]   \
                 [--force]           \
                 [--last "integer"]  \
                 [--recursive, r]    \
                 [--dry-run]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `TARGET` {#mc.undo.TARGET}

*mc-cmd*

*Required*

The full path to the object or prefix where the command should run. The path must include the [ALIAS](/reference/minio-mc/mc-alias-set/#minio-mc-alias), bucket, and prefix or object name.

##### `--action` {#mc.undo.-action}

*mc-cmd*

*Optional*

Undo the most recent change of the specified type. Accepted values are `DELETE` or `PUT`.

By default, [`mc undo`](#command-mc.undo) reverses both `DELETE` and `PUT` operations. Use [`--action`](#mc.undo.-action) to choose one or the other, but only for the most recent operation of the specified type.

The following command reverts the most recent `PUT` for the object `today.zip` in bucket `data`, reverting to the previous object version:

```shell
mc undo myminio/data/today.zip --action "PUT"
```

This example reverts the most recent `DELETE` for the prefix `archive`, recursively restoring it and any child objects:

```shell
mc undo myminio/data/archive --recursive --action "DELETE"
```

Mutually exclusive with [`--last`](#mc.undo.-last).

##### `--dry-run` {#mc.undo.-dry-run}

*mc-cmd*

*Optional*

Output the results of the command without actually performing the operations. Use this flag to test the outcome of running the command in a particular way.

##### `--force` {#mc.undo.-force}

*mc-cmd*

*Optional*

Force a recursive operation.

##### `--last` {#mc.undo.-last}

*mc-cmd*

*Optional*

Accepts an integer value specifying the number of `PUT` and/or `DELETE` changes to undo.

If not specified, the command reverses one (`1`) operation. Mutually exclusive with [`--action`](#mc.undo.-action).

##### `--recursive, r` {#mc.undo.-recursive}

*mc-cmd*

*Optional*

Performs the command in a recursive fashion. Use this flag to undo changes on a prefix, for example.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Undo the Last Three Uploads or Deletions on an Object {#undo-the-last-three-uploads-or-deletions-on-an-object}

The following command reverts the last three uploads and/or deletions of the `file.zip` object on the `myminio` deployment in the `data` bucket:

```shell
mc undo myminio/data/file.zip --last 3
```

### Undo the Last Upload or Deletion of any Object at a Prefix {#undo-the-last-upload-or-deletion-of-any-object-at-a-prefix}

Use [`mc undo`](#command-mc.undo) to reverse the most recent `PUT` or `DELETE` operation performed on the `myminio` alias in the `data` bucket under the `presentations/recordings/` [prefix](/glossary/#term-prefix):

```shell
mc undo myminio/data/presentations/recordings/ --recursive --force
```

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

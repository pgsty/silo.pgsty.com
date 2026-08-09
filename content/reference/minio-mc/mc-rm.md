---
title: "mc rm"
url: "/reference/minio-mc/mc-rm/"
weight: 340
minio_origin: true
silo_modified: false
---

<a id="mc-rm"></a>

<a id="command-mc.rm"></a>

## Syntax {#syntax}

The [`mc rm`](#command-mc.rm) command [removes objects](/administration/object-management/object-delete/#minio-object-delete) from a bucket on a MinIO deployment. To completely remove a bucket, use [`mc rb`](/reference/minio-mc/mc-rb/#command-mc.rb) instead.

You can also use [`mc rm`](#command-mc.rm) against the local filesystem to produce similar results to the `rm` commandline tool.

For more information on how MinIO performs `DELETE` actions on objects, see [Object Deletion](/administration/object-management/object-delete/#minio-object-delete).

{{% alert color="warning" %}}
**Important**

[`mc rm`](#command-mc.rm) supports removing multiple objects *or* files in a single command. Consider using the [`--dry-run`](#mc.rm.-dry-run) option to validate that the operation targets only the desired objects/files.
{{% /alert %}}

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command removes multiple objects from the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc rm --recursive myminio/mydata
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] rm  \
                 [--bypass]               \
                 [--dangerous]            \
                 [--dry-run]              \
                 [--force]*               \
                 [--incomplete]           \
                 [--newer-than "string"]  \
                 [--non-current]          \
                 [--older-than "string"]  \
                 [--recursive]            \
                 [--rewind "string"]      \
                 [--stdin]                \
                 [--version-id "string"]* \
                 [--versions]             \
                 ALIAS [ALIAS ...]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.

[`mc rm --force`](#mc.rm.-force) is required by multiple parameters. [`mc rm --version-id`](#mc.rm.-version-id) is mutually exclusive with multiple parameters. See the reference documentation for more information.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.rm.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment and the full path to the object to remove. For example:

```shell
mc rm play/mybucket/object.txt
```

You can specify multiple objects on the same or different MinIO deployments. For example:

```shell
mc rm play/mybucket/object.txt play/mybucket/otherobject.txt
```

If specifying the path to a bucket or bucket prefix, you **must** also specify the [`--recursive`](#mc.rm.-recursive) and [`--force`](#mc.rm.-force) arguments. For example:

```shell
mc rm --recursive --force play/mybucket/

mc rm --recursive --force play/mybucket/myprefix/
```

Consider first running the command with the [`--dry-run`](#mc.rm.-dry-run) flag to validate the scope of the recursive delete operation.

For removing a file from a local filesystem, specify the full path to that file:

```shell
mc rm ~/data/myoldobject.txt
```

##### `--bypass` {#mc.rm.-bypass}

*mc-cmd*

*Optional*

Allows removing an object held under [GOVERNANCE](/administration/object-management/object-retention/#minio-object-locking-governance) object locking.

##### `--dangerous` {#mc.rm.-dangerous}

*mc-cmd*

*Optional*

Allows running [`mc rm`](#command-mc.rm) when the [`ALIAS`](#mc.rm.ALIAS) specifies the root (all buckets) on the MinIO deployment.

When combined with [`--versions`](#mc.rm.-versions), this flag directs [`mc rm`](#command-mc.rm) to permanently remove all objects *and* versions from the `ALIAS` target.

Consider first running the command with the [`--dry-run`](#mc.rm.-dry-run) to validate the scope of the site-wide delete operation.

{{% alert color="danger" %}}
**Warning**

Running [`mc rm --dangerous`](#mc.rm.-dangerous) with the [`--versions`](#mc.rm.-versions) flag is irreversible. Exercise all possible due diligence in ensuring the command applies to only the desired `ALIAS` targets prior to execution.
{{% /alert %}}

##### `--dry-run` {#mc.rm.-dry-run}

*mc-cmd*

*Optional*

Outputs the results of a command without actually removing any files. Use this flag to test that your command configuration removes only the objects you wish to remove.

##### `--force` {#mc.rm.-force}

*mc-cmd*

*Optional*

Allows running [`mc rm`](#command-mc.rm) with any of the following arguments:

- [`--recursive`](#mc.rm.-recursive)
- [`--versions`](#mc.rm.-versions)
- [`--stdin`](#mc.rm.-stdin)

##### `--incomplete, I` {#mc.rm.-incomplete}

*mc-cmd*

*Optional*

Remove incomplete uploads for the specified object.

If any [`ALIAS`](#mc.rm.ALIAS) specifies a bucket, you **must** also specify [`--recursive`](#mc.rm.-recursive) and [`--force`](#mc.rm.-force).

##### `--newer-than` {#mc.rm.-newer-than}

*mc-cmd*

*Optional*

Remove object(s) newer than the specified number of days. Specify a string in `#d#hh#mm#ss` format. For example: `--newer-than 1d2hh3mm4ss`

Defaults to `0` (all objects).

##### `--non-current` {#mc.rm.-non-current}

*mc-cmd*

*Optional*

Removes all [non-current](/administration/object-management/object-versioning/#minio-bucket-versioning-delete) object versions from the specified [`ALIAS`](#mc.rm.ALIAS).

This option has no effect on buckets without [versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) enabled.

##### `--older-than` {#mc.rm.-older-than}

*mc-cmd*

*Optional*

Remove object(s) older than the specified time limit. Specify a string in `#d#h#m#s` format. For example: `--older-than 1d2h3m4s`.

Defaults to `0` (all objects).

##### `--recursive, r` {#mc.rm.-recursive}

*mc-cmd*

*Optional*

Recursively remove the contents of each [`ALIAS`](#mc.rm.ALIAS) bucket or bucket prefix.

If specifying [`--recursive`](#mc.rm.-recursive), you **must** also specify [`--force`](#mc.rm.-force).

For buckets with [versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) enabled, this option by default produces a delete marker for each removed object. Include the [`--versions`](#mc.rm.-versions) flag to recursively remove all objects *and* object versions from the bucket.

Consider first running the command with the [`--dry-run`](#mc.rm.-dry-run) flag to validate the scope of the recursive delete operation.

Mutually exclusive with [`mc rm --version-id`](#mc.rm.-version-id)

##### `--rewind` {#mc.rm.-rewind}

*mc-cmd*

*Optional*

Directs [`mc rm`](#command-mc.rm) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.rm.-rewind) requires that the specified [`ALIAS`](#mc.rm.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--stdin` {#mc.rm.-stdin}

*mc-cmd*

*Optional*

Read object names or buckets from `STDIN`.

##### `--versions` {#mc.rm.-versions}

*mc-cmd*

*Optional*

Directs [`mc rm`](#command-mc.rm) to operate on all object versions that exist in the bucket.

[`--versions`](#mc.rm.-versions) requires that the specified [`ALIAS`](#mc.rm.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Use [`--versions`](#mc.rm.-versions) and [`--rewind`](#mc.rm.-rewind) together to remove all object versions which existed at a specific point in time.

##### `--version-id, vid` {#mc.rm.-version-id}

*mc-cmd*

*Optional*

Directs [`mc rm`](#command-mc.rm) to operate only on the specified object version.

[`--version-id`](#mc.rm.-version-id) requires that the specified [`ALIAS`](#mc.rm.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Mutually exclusive with any of the following flags:

- [`--versions`](#mc.rm.-versions)
- [`--rewind`](#mc.rm.-rewind)
- [`--recursive`](#mc.rm.-recursive)

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Remove a Single Object {#remove-a-single-object}

```shell
mc rm ALIAS/PATH
```

- Replace [`ALIAS`](#mc.rm.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible service.
- Replace [`PATH`](#mc.rm.ALIAS) with the path to the object.

### Recursively Remove a Bucket’s Contents {#recursively-remove-a-bucket-s-contents}

Use [`mc rm`](#command-mc.rm) with the [`--recursive`](#mc.rm.-recursive) and [`--force`](#mc.rm.-force) options to recursively remove a bucket’s contents.

```shell
mc rm --recursive --force ALIAS/PATH
```

- Replace [`ALIAS`](#mc.rm.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible service.
- Replace [`PATH`](#mc.rm.ALIAS) with the path to the bucket.

This operation does *not* remove the bucket. Use [`mc rb`](/reference/minio-mc/mc-rb/#command-mc.rb) to remove the bucket along with all contents and associated configurations.

### Remove All Incomplete Upload Files for an Object {#remove-all-incomplete-upload-files-for-an-object}

Use [`mc rm`](#command-mc.rm) with the [`--incomplete`](#mc.rm.-incomplete) option to remove incomplete upload files for an object.

```shell
mc rm --incomplete --recursive --force ALIAS/PATH
```

- Replace [`ALIAS`](#mc.rm.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible service.
- Replace [`PATH`](#mc.rm.ALIAS) with the path to the object.

### Roll Object Back To Previous Version {#roll-object-back-to-previous-version}

Use [`mc rm`](#command-mc.rm) with [`--versions`](#mc.rm.-versions) and [`--newer-than`](#mc.rm.-newer-than) to remove all object versions newer than the specified duration of time. This effectively “rolls back” the object to its state at that time.

{{% alert color="warning" %}}
**Important**

Removing specific versions of an object is a *destructive* action. You cannot restore the deleted object versions.
{{% /alert %}}

```shell
mc rm ALIAS/PATH --versions --newer-than DURATION
```

- Replace [`ALIAS`](#mc.rm.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible service.
- Replace [`PATH`](#mc.rm.ALIAS) with the path to the object. For example, `/mybucket/myobject`.
- Replace [`DURATION`](#mc.rm.-newer-than) with the number of days in the past from the current host time from which the operation begins removing versions of the object. For example, to remove all versions of the object created in the last 30 days, specify `"30d"`.

## Behavior {#behavior}

### Deleting Bucket Contents {#deleting-bucket-contents}

Using [`mc rm`](#command-mc.rm) to remove all contents in a bucket does not delete the bucket itself. Any configurations associated to the bucket remain in place, such as [`default object lock settings`](/reference/minio-mc/mc-retention-set/#mc.retention.set.-default).

To completely remove a bucket, use [`mc rb`](/reference/minio-mc/mc-rb/#command-mc.rb) instead of [`mc rm`](#command-mc.rm).

### MinIO Trims Empty Prefixes on Object Removal {#minio-trims-empty-prefixes-on-object-removal}

[`mc rm`](#command-mc.rm) relies on the [`mc`](/reference/minio-mc/#command-mc) removal API for deleting objects. As part of removing the last object in a bucket prefix, [`mc`](/reference/minio-mc/#command-mc) also recursively removes each empty part of the prefix up to the bucket root. [`mc`](/reference/minio-mc/#command-mc) only applies the recursive removal to prefixes created *implicitly* as part of object write operations - that is, the prefix was not created using an explicit directory creation command such as [`mc mb`](/reference/minio-mc/mc-mb/#command-mc.mb).

For example, consider a bucket `photos` with the following object prefixes:

- `photos/2021/january/myphoto.jpg`
- `photos/2021/february/myotherphoto.jpg`
- `photos/NYE21/NewYears.jpg`

`photos/NYE21` is the *only* prefix explicitly created using [`mc mb`](/reference/minio-mc/mc-mb/#command-mc.mb). All other prefixes were *implicitly* created as part of writing the object located at that prefix.

If an [`mc`](/reference/minio-mc/#command-mc) command removes `myphoto.jpg`, the removal API automatically trims the empty `/january` prefix. If a subsequent [`mc`](/reference/minio-mc/#command-mc) command removes `myotherphoto.jpg`, the removal API automatically trims both the `/february` prefix *and* the now-empty `/2021` prefix. If an [`mc`](/reference/minio-mc/#command-mc) command removes `NewYears.jpg`, the `/NYE21` prefix remains in place since it was *explicitly* created.

If using [`mc rm`](#command-mc.rm) for operations on a filesystem, [`mc`](/reference/minio-mc/#command-mc) applies this same behavior by recursively trimming empty directory paths up to the root. However, the [`mc`](/reference/minio-mc/#command-mc) remove API cannot distinguish between an explicitly created directory path and an implicitly created one. If [`mc rm`](#command-mc.rm) deletes the last object at a filesystem path, [`mc`](/reference/minio-mc/#command-mc) recursively deletes all empty directories within that path up to the root as part of the removal operation.

### Delete Operations in Versioned Buckets {#delete-operations-in-versioned-buckets}

MinIO supports keeping multiple [versions](/administration/object-management/object-versioning/#minio-bucket-versioning) of an object in a single bucket. [Deleting](/administration/object-management/object-versioning/#minio-bucket-versioning-delete) an object in a versioned bucket results in a special `DeleteMarker` tombstone that marks an object as deleted while retaining all previous versions of that object.

- To remove a specific object version from a bucket, use [`mc rm --version-id`](#mc.rm.-version-id)
- To remove all versions of an object from a bucket, use [`mc rm --versions`](#mc.rm.-versions)
- To remove all non-current versions of an object from a bucket, use [`mc rm --non-current`](#mc.rm.-non-current)

{{% alert color="info" %}}
**Changed: mc**

RELEASE.2023-03-20T17-17-53Z

The output shows the modification time of versioned files. When used with `--dry-run`, this can help confirm that you selected the correct object(s) for removal.
{{% /alert %}}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

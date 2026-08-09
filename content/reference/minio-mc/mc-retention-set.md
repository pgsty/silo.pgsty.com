---
title: "mc retention set"
url: "/reference/minio-mc/mc-retention-set/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-retention-set"></a>
<a id="minio-bucket-locking"></a>

<a id="command-mc.retention.set"></a>

## Syntax {#syntax}

The [`mc retention set`](#command-mc.retention.set) command configures the [Write-Once Read-Many (WORM) locking](/administration/object-management/object-retention/#minio-object-locking) settings for an object or object(s) in a bucket. You can also set the default object lock settings for a bucket, where all objects without explicit object lock settings inherit the bucket default.

To lock an object under [legal hold](/administration/object-management/object-retention/#minio-object-locking-legalhold), use [`mc legalhold set`](/reference/minio-mc/mc-legalhold-set/#command-mc.legalhold.set).

[`mc retention set`](#command-mc.retention.set) *requires* that the specified bucket has object locking enabled. You can **only** enable object locking at bucket creation. See [`mc mb --with-lock`](/reference/minio-mc/mc-mb/#mc.mb.-with-lock) for documentation on creating buckets with object locking enabled.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command sets a default 30 day [GOVERNANCE](/administration/object-management/object-retention/#minio-object-locking-governance) object lock on the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc retention set --default GOVERNANCE "30d" myminio/mydata
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] retention set                         \
                 [--bypass]                            \
                 [--default]                           \
                 [--recursive]                         \
                 [--rewind "string"]                   \
                 [--versions]                          \
                 [--version-id "string"]*              \
                 MODE                                  \
                 "VALIDITY"                            \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.

[`mc retention set --version-id`](#mc.retention.set.-version-id) is mutually exclusive with multiple other parameters. See the reference documentation for more information.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `MODE` {#mc.retention.set.MODE}

*mc-cmd*

*Required*

Sets the locking mode for the [`ALIAS`](#mc.retention.set.ALIAS). Specify one of the following supported values:

- `governance`
- `compliance`

See the AWS S3 documentation on [Object Lock Overview](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-overview.html) for more information on the supported modes.

Requires specifying [`VALIDITY`](#mc.retention.set.VALIDITY).

##### `VALIDITY` {#mc.retention.set.VALIDITY}

*mc-cmd*

*Required*

The duration which objects remain in the specified [`MODE`](#mc.retention.set.MODE) after creation.

- **For days, specify a string formatted as `Nd`. For example,**

  > `30d` for 30 days after object creation.
- **For years, specify a string formatted as `Ny`. For example,**

  > `1y` for 1 year after object creation.

##### `ALIAS` {#mc.retention.set.ALIAS}

*mc-cmd*

*Required*

The full path to the object or objects for which to set object lock configuration. Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) for the MinIO or S3-compatible service and the full path to bucket. For example:

```shell
mc retention set play/mybucket/object.txt MODE VALIDITY
```

- If the `ALIAS` specifies a bucket or bucket prefix, include [`--recursive`](#mc.retention.set.-recursive) to apply the object lock settings to the bucket contents.
- [`mc retention set`](#command-mc.retention.set) by default applies to only the latest object version. Use [`--version-id`](#mc.retention.set.-version-id) or [`--versions`](#mc.retention.set.-versions) to apply the object lock settings to a specific version or to all versions of the object respectively.

##### `--bypass` {#mc.retention.set.-bypass}

*mc-cmd*

*Optional*

Allows a user with the `s3:BypassGovernanceRetention` permission to modify the object. Requires the `governance` retention [`MODE`](#mc.retention.set.MODE)

##### `--default` {#mc.retention.set.-default}

*mc-cmd*

*Optional*

Sets the default object lock settings for the bucket specified to [`ALIAS`](#mc.retention.set.ALIAS) using the [`MODE`](#mc.retention.set.MODE) and [`VALIDITY`](#mc.retention.set.VALIDITY). Any objects created in the bucket inherit the default object lock settings unless explicitly overriden using [`mc retention set`](#command-mc.retention.set).

If specifying [`--default`](#mc.retention.set.-default), [`mc retention set`](#command-mc.retention.set) ignores all other flags.

##### `--recursive, --r` {#mc.retention.set.-recursive}

*mc-cmd*

*Optional*

Recursively applies the object lock settings to all objects in the specified [`ALIAS`](#mc.retention.set.ALIAS) path.

Mutually exclusive with [`--version-id`](#mc.retention.set.-version-id).

##### `--rewind` {#mc.retention.set.-rewind}

*mc-cmd*

*Optional*

Directs [`mc retention set`](#command-mc.retention.set) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.retention.set.-rewind) requires that the specified [`ALIAS`](#mc.retention.set.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--version-id, --vid` {#mc.retention.set.-version-id}

*mc-cmd*

*Optional*

Directs [`mc retention set`](#command-mc.retention.set) to operate only on the specified object version.

[`--version-id`](#mc.retention.set.-version-id) requires that the specified [`ALIAS`](#mc.retention.set.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Mutually exclusive with any of the following flags:

- [`--versions`](#mc.retention.set.-versions)
- [`--rewind`](#mc.retention.set.-rewind)
- [`--recursive`](#mc.retention.set.-recursive)

##### `--versions` {#mc.retention.set.-versions}

*mc-cmd*

*Optional*

Directs [`mc retention set`](#command-mc.retention.set) to operate on all object versions that exist in the bucket.

[`--versions`](#mc.retention.set.-versions) requires that the specified [`ALIAS`](#mc.retention.set.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Use [`--versions`](#mc.retention.set.-versions) and [`--rewind`](#mc.retention.set.-rewind) together to apply the retention settings to all object versions that existed at a specific point-in-time.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Set Default Bucket Retention Settings {#set-default-bucket-retention-settings}

Use [`mc retention set`](#command-mc.retention.set) with the [`--recursive`](#mc.retention.set.-recursive) and [`--default`](#mc.retention.set.-default) to set the default bucket retention settings.

```shell
mc retention set  --recursive --default MODE DURATION ALIAS/PATH
```

- Replace [`MODE`](#mc.retention.set.MODE) with the retention mode to enable. MinIO supports the AWS S3 retention modes `governance` and `compliance`.
- Replace [`DURATION`](#mc.retention.set.VALIDITY) with the duration which the object lock should remain in effect. For example, to set a retention period of 30 days, specify `30d`.
- Replace [`ALIAS`](#mc.retention.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.retention.set.ALIAS) with the path to the bucket.

> The bucket *must* have object locking enabled to use this command. You can only enable object locking when creating a bucket. See [`mc mb --with-lock`](/reference/minio-mc/mc-mb/#mc.mb.-with-lock) for more information on creating buckets with object locking enabled.

### Set Object Lock Configuration for Versioned Object {#set-object-lock-configuration-for-versioned-object}

{{< tabpane text=true persist=header >}}
{{% tab header="Specific Version" %}}
Use [`mc retention set`](#command-mc.retention.set) with [`--version-id`](#mc.retention.set.-version-id) to apply the retention settings to a specific object version:

```shell
mc retention set --version-id VERSION MODE DURATION ALIAS/PATH
```

- Replace [`VERSION`](#mc.retention.set.-version-id) with the version of the object.
- Replace [`MODE`](#mc.retention.set.MODE) with the retention mode to enable. MinIO supports the AWS S3 retention modes `governance` and `compliance`.
- Replace [`DURATION`](#mc.retention.set.VALIDITY) with the duration which the object lock should remain in effect. For example, to set a retention period of 30 days, specify `30d`.
- Replace [`ALIAS`](#mc.retention.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.retention.set.ALIAS) with the path to the object.
{{% /tab %}}
{{% tab header="All Versions" %}}
Use [`mc retention set`](#command-mc.retention.set) with [`--versions`](#mc.retention.set.-versions) to apply the retention settings to a specific object version:

```shell
mc retention set --versions  MODE DURATION ALIAS/PATH
```

- Replace [`MODE`](#mc.retention.set.MODE) with the retention mode to enable. MinIO supports the AWS S3 retention modes `governance` and `compliance`.
- Replace [`DURATION`](#mc.retention.set.VALIDITY) with the duration which the object lock should remain in effect. For example, to set a retention period of 30 days, specify `30d`.
- Replace [`ALIAS`](#mc.retention.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.retention.set.ALIAS) with the path to the object.
{{% /tab %}}
{{< /tabpane >}}

> The bucket *must* have object locking enabled to use this command. You can only enable object locking when creating a bucket. See [`mc mb --with-lock`](/reference/minio-mc/mc-mb/#mc.mb.-with-lock) for more information on creating buckets with object locking enabled.

## Behavior {#behavior}

### Retention of Object Versions {#retention-of-object-versions}

For buckets with [`versioning enabled`](/reference/minio-mc/mc-version/#command-mc.version), [`mc retention set`](#command-mc.retention.set) by default operates on the *latest* version of the target object or object(s). [`mc retention set`](#command-mc.retention.set) includes specific options that when *explicitly* specified direct the command to operate on either a specific object version *or* all versions of an object:

{{< tabpane text=true persist=header >}}
{{% tab header="Specific Object Version" %}}
To direct [`mc retention set`](#command-mc.retention.set) to operate on a specific version of an object, include the `--version-id` argument:

- [`mc retention set --version-id`](#mc.retention.set.-version-id)
- [`mc retention set --version-id`](#mc.retention.set.-version-id)
- [`mc retention set --version-id`](#mc.retention.set.-version-id)
{{% /tab %}}
{{% tab header="All Object Versions" %}}
To direct [`mc retention set`](#command-mc.retention.set) to operate on *all* versions of an object, include the `--versions` argument:

- [`mc retention set --versions`](#mc.retention.set.-versions)
- [`mc retention set --versions`](#mc.retention.set.-versions)
- [`mc retention set --versions`](#mc.retention.set.-versions)
{{% /tab %}}
{{< /tabpane >}}

### Interaction with Legal Holds {#interaction-with-legal-holds}

Locking an object prevents any modification or deletion of that object, similar to the [`COMPLIANCE`](#mc.retention.set.MODE) object locking mode. Objects can have simultaneous retention-based locks *and* legal hold locks.

The legal hold lock *overrides* any retention locking, such that an object under legal hold remains locked *even if* the retention period expires. Setting, modifying, or clearing retention settings for an object under legal hold has no effect until the legal hold either expires or is explicitly disabled.

For more information on object legal holds, see [`mc legalhold`](/reference/minio-mc/mc-legalhold/#command-mc.legalhold).

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

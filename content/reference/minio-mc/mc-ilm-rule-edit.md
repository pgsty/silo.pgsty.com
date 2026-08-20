---
title: "mc ilm rule edit"
url: "/reference/minio-mc/mc-ilm-rule-edit/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-ilm-rule-edit.rst
upstream_modified: false
---

<a id="mc-ilm-rule-edit"></a>
<a id="minio-mc-ilm-rule-edit"></a>

<a id="command-mc.ilm.rule.edit"></a>

> [!NOTE]
> **Changed: RELEASE.2022-12-24T15-21-38Z**
>
> `mc ilm rule edit` replaces `mc ilm edit`.

## Syntax {#syntax}

The [`mc ilm rule edit`](#command-mc.ilm.rule.edit) command modifies an existing object lifecycle management rule on a MinIO bucket.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command modifies existing lifecycle management rules for the `mydata` bucket on the `myminio` deployment:

```shell
mc ilm rule edit --id "c79ntj94b0t6rukh6lr0" --expiry-days 90  myminio/mydata

mc ilm rule edit --id "c79nu2p4b0t6qko19rgg" --expired-object-delete-marker myminio/mydata

mc ilm rule edit --id "c79n19dn10dnab109fg1" --transition-days 30 --tier "COLDTIER"
```

The command modifies the specified rules as follows:

- Delete objects more than 90 days old.
- Delete `DeleteMarker` tombstones if that object has no other versions remaining.
- Transition objects more than 30 days old to the `COLDTIER` remote tier.
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ilm rule edit                                       \
                 --id "string"                                       \
                 [--prefix "string"]                                 \
                 [--enable]                                          \
                 [--disable]                                         \
                 [--expire-all-object-versions]                      \
                 [--expire-days "string"]                            \
                 [--expire-delete-marker]                            \
                 [--transition-days "string"]                        \
                 [--transition-tier "string"]                        \
                 [--noncurrent-expire-days "string"]                 \
                 [--noncurrent-expire-newer "string"]                \
                 [--noncurrent-transition-days "string"]             \
                 [--noncurrent-transition-tier "string"]             \
                 [--tags]                                            \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.ilm.rule.edit.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) and full path to the bucket on the MinIO deployment to which to modify the object lifecycle management rule. For example:

```text
mc ilm rule edit myminio/mydata
```

##### `--id` {#mc.ilm.rule.edit.-id}

*mc-cmd*

*Required*

The unique ID of the rule. Use [`mc ilm rule ls`](/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls) to list bucket rules and retrieve the `id` for the rule you want to modify.

##### `--disable` {#mc.ilm.rule.edit.-disable}

*mc-cmd*

*Optional*

Stop using the rule, but retain the rule for future use. Objects do not transition or expire when a rule is disabled.

##### `--enable` {#mc.ilm.rule.edit.-enable}

*mc-cmd*

*Optional*

Use a rule to transition or expire objects.

##### `--prefix` {#mc.ilm.rule.edit.-prefix}

*mc-cmd*

*Optional*

Restrict the management rule to a specific bucket prefix.

For example:

```text
mc ilm rule edit --prefix "meetingnotes/" myminio/mydata --expire-days "90"
```

The command modifies a rule that expires objects in the `mydata` bucket of the `myminio` ALIAS after 90 days for any object with the `meetingnotes/` prefix.

##### `--expire-all-object-versions` {#mc.ilm.rule.edit.-expire-all-object-versions}

*mc-cmd*

*Optional*

> [!NOTE]
> **Added: mc**
>
> RELEASE.2024-02-24T01-33-20Z

Expire all current **and** noncurrent versions of an object. Use with the [`--expire-days`](/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-expire-days) option to specify the number of days after which all versions of an object should be deleted by the scanner process.

After the [scanner](/operations/concepts/scanner/#minio-concepts-scanner) processes this command, no versions of the object remain on the deployment.

> [!NOTE]
> **Added: MinIO**
>
> RELEASE.2024-05-01T01-11-10Z

This flag *only* applies to objects that do **not** have a delete marker as the latest version.

##### `--expire-days` {#mc.ilm.rule.edit.-expire-days}

*mc-cmd*

*Optional*

The number of days to retain an object after being created. MinIO marks the object for deletion after the specified number of days pass.

Exercise caution when using this option, as its behavior can result in immediate expiration of uploaded objects. Any objects created *after* the specified expiration date are automatically eligible for expiration. Similarly, specifying a calendar date that is *prior* to the current system host datetime marks all objects covered by the rule for deletion. Consider immediately removing any ILM rule using this option once the specified calendar date has passed.

For versioned buckets, the expiry rule applies only to the *current* object version. Use the [`--noncurrent-expire-days`](#mc.ilm.rule.edit.-noncurrent-expire-days) option to apply expiration behavior to noncurrent object versions.

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

Mutually exclusive with the following options:

- [`--expire-delete-marker`](#mc.ilm.rule.edit.-expire-delete-marker)

##### `--expire-delete-marker` {#mc.ilm.rule.edit.-expire-delete-marker}

*mc-cmd*

*Optional*

Specify this option to direct MinIO to remove delete markers for objects with no remaining object versions. Specifically, the delete marker is the *only* remaining “version” of the given object.

This option is mutually exclusive with the following options:

- [`--tags`](#mc.ilm.rule.edit.-tags)
- [`--expire-days`](#mc.ilm.rule.edit.-expire-days)

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) and [Object Deletion](/administration/object-management/object-delete/#minio-object-delete) for more information.

##### `--noncurrent-expire-days` {#mc.ilm.rule.edit.-noncurrent-expire-days}

*mc-cmd*

*Optional*

The number of days to retain an object version after becoming *non-current* (i.e. a different version of that object is now the *HEAD*). MinIO marks noncurrent object versions for deletion after the specified number of days pass.

This option has the same behavior as the S3 `NoncurrentVersionExpiration` action.

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

##### `--noncurrent-expire-newer` {#mc.ilm.rule.edit.-noncurrent-expire-newer}

*mc-cmd*

*Optional*

The number of non-current versions of an object to retain before applying expiration. Older non-current versions beyond the specified number expire.

By default, MinIO does not retain any non-current versions when an expiration rule applies.

##### `--noncurrent-transition-days` {#mc.ilm.rule.edit.-noncurrent-transition-days}

*mc-cmd*

*Optional*

The number of days an object has been non-current (i.e. replaced by a newer version of that same object) after which MinIO marks the object version as eligible for transition. MinIO transitions the object to the configured remote storage tier specified to the [`--transition-tier`](#mc.ilm.rule.edit.-transition-tier) once the system host datetime passes that calendar date.

This option has no effect on non-versioned buckets. Requires specifying [`--noncurrent-transition-tier`](#mc.ilm.rule.edit.-noncurrent-transition-tier).

This option has the same behavior as the S3 `NoncurrentVersionTransition` action.

If the remote tier is another MinIO deployment, you can set the value to `0` to mark new objects as immediately eligible for transition to the remote tier.

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

##### `--noncurrent-transition-tier` {#mc.ilm.rule.edit.-noncurrent-transition-tier}

*mc-cmd*

*Optional*

The remote storage tier to which MinIO [transitions noncurrent objects versions](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering). Specify a remote storage tier created by [`mc ilm tier add`](/reference/minio-mc/mc-ilm-tier-add/#command-mc.ilm.tier.add).

MinIO does *not* automatically migrate objects from the previously specified remote tier to the new remote tier. MinIO continues to route requests for objects stored on the old remote tier.

##### `--tags` {#mc.ilm.rule.edit.-tags}

*mc-cmd*

*Optional*

One or more ampersand `&`-delimited key-value pairs describing the object tags to which to apply the lifecycle configuration rule.

This option is mutually exclusive with the following option:

- [`--expire-delete-marker`](#mc.ilm.rule.edit.-expire-delete-marker)

##### `--transition-days` {#mc.ilm.rule.edit.-transition-days}

*mc-cmd*

*Optional*

The number of calendar days from object creation after which MinIO marks an object as eligible for transition. MinIO transitions the object to the configured remote storage tier specified to the [`--transition-tier`](#mc.ilm.rule.edit.-transition-tier). Specify the number of days as an integer, e.g. `30` for 30 days. If the remote tier is another MinIO deployment, you can set the value to `0` to mark new objects as immediately eligible for transition to the remote tier.

For versioned buckets, the transition rule applies only to the *current* object version. Use the [`--noncurrent-transition-days`](#mc.ilm.rule.edit.-noncurrent-transition-days) option to apply transition behavior to noncurrent object versions.

Requires specifying [`--transition-tier`](#mc.ilm.rule.edit.-transition-tier).

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

##### `--transition-tier` {#mc.ilm.rule.edit.-transition-tier}

*mc-cmd*

*Optional*

The remote storage tier to which MinIO [transition objects](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering). Specify a remote storage tier created by [`mc ilm tier add`](/reference/minio-mc/mc-ilm-tier-add/#command-mc.ilm.tier.add).

Required if specifying [`--transition-days`](#mc.ilm.rule.edit.-transition-days).

MinIO does *not* automatically migrate objects from the previously specified remote tier to the new remote tier. MinIO continues to route requests for objects stored on the old remote tier.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Modify an Existing Lifecycle Management Rule {#modify-an-existing-lifecycle-management-rule}

Use [`mc ilm rule edit`](#command-mc.ilm.rule.edit) with [`--id`](#mc.ilm.rule.edit.-id) to modify an existing object expiration rule:

```shell
mc ilm rule edit ALIAS/PATH --id "RULEID" [FLAGS]
```

- Replace [`ALIAS`](#mc.ilm.rule.edit.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.ilm.rule.edit.ALIAS) with the path to the bucket on the S3-compatible host.
- Replace `RULEID` with the unique ID of the object lifecycle management rule. Use [`mc ilm rule ls`](/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls) to find the `RULEID`.
- Specify any additional flags to add or modify the lifecycle management rule. For example, specify [`--transition-days`](#mc.ilm.rule.edit.-transition-days) to override the existing transition days value for the rule.

### Disable a Lifecycle Management Rule {#disable-a-lifecycle-management-rule}

Use [`mc ilm rule edit`](#command-mc.ilm.rule.edit) with [`--disable`](#mc.ilm.rule.edit.-disable) to stop using an existing management rule.

```shell
mc ilm rule edit --id "RULEID" --disable myminio/mybucket
```

- Replace `RULEID` with the unique ID of the object lifecycle management rule. Use [`mc ilm rule ls`](/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls) to find the `RULEID`.
- Replace `myminio` with the ALIAS of the deployment where the rule exists.
- Replace `mybucket` with the bucket for the rule.

## Required Permissions {#required-permissions}

For permissions required to edit a rule, refer to the [required permissions](/reference/minio-mc/mc-ilm-rule/#minio-mc-ilm-rule-permissions) on the parent command.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

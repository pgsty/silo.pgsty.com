---
title: "mc ilm edit"
url: "/reference/deprecated/mc-ilm-edit/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="mc-ilm-edit"></a>
<a id="minio-mc-ilm-edit"></a>

<a id="command-mc.ilm.edit"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

`mc ilm edit` replaced by [`mc ilm rule edit`](/reference/minio-mc/mc-ilm-rule-edit/#command-mc.ilm.rule.edit).
{{% /alert %}}

## Syntax {#syntax}

The [`mc ilm edit`](#command-mc.ilm.edit) command modifies an existing object lifecycle management rule on a MinIO bucket.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command modifies existing lifecycle management rules for the `mydata` bucket on the `myminio` deployment:

```shell
mc ilm edit --id "c79ntj94b0t6rukh6lr0" --expiry-days 90  mydata/myminio

mc ilm edit --id "c79nu2p4b0t6qko19rgg" --expired-object-delete-marker mydata/myminio

mc ilm edit --id "c79n19dn10dnab109fg1" --transition-days 30 --tier "COLDTIER"
```

The command modifies the specified rules as follows:

- Delete objects more than 90 days old.
- Delete `DeleteMarker` tombstones if that object has no other versions remaining.
- Transition objects more than 30 days old to the `COLDTIER` remote tier.
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ilm edit \
                 --id "string"                                                                                        \
                 [--prefix "string"]                                                                                  \
                 [--enable]                                                                                           \
                 [--disable]                                                                                          \
                 [--expiry-days "string" | --expired-object-delete-marker]                                            \
                 [--transition-days "string"] --tier "string"                                                \
                 [--noncurrentversion-expiration-days "string"]                                                       \
                 [--noncurrentversion-transition-days "string" --noncurrentversion-tier "string"] \
                 [--tags]                                                                                             \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.ilm.edit.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) and full path to the bucket on the MinIO deployment to which to modify the object lifecycle management rule. For example:

```text
mc ilm edit myminio/mydata
```

##### `--id` {#mc.ilm.edit.-id}

*mc-cmd*

*Required*

The unique ID of the rule. Use [`mc ilm rule ls`](/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls) to list bucket rules and retrieve the `id` for the rule you want to modify.

##### `--disable` {#mc.ilm.edit.-disable}

*mc-cmd*

*Optional*

Stop using the rule, but retain the rule for future use. Objects do not transition or expire when a rule is disabled.

##### `--enable` {#mc.ilm.edit.-enable}

*mc-cmd*

*Optional*

Use a rule to transition or expire objects.

##### `--prefix` {#mc.ilm.edit.-prefix}

*mc-cmd*

*Optional*

Restrict the management rule to a specific bucket prefix.

For example:

```text
mc ilm edit --prefix "meetingnotes/" myminio/mydata/ --expiry-days "90"
```

The command modifies a rule that expires objects in the `mydata` bucket of the `myminio` ALIAS after 90 days for any object with the `meetingnotes/` prefix.

##### `--expiry-days` {#mc.ilm.edit.-expiry-days}

*mc-cmd*

*Optional*

The number of days to retain an object after being created. MinIO marks the object for deletion after the specified number of days pass.

Exercise caution when using this option, as its behavior can result in immediate expiration of uploaded objects. Any objects created *after* the specified expiration date are automatically eligible for expiration. Similarly, specifying a calendar date that is *prior* to the current system host datetime marks all objects covered by the rule for deletion. Consider immediately removing any ILM rule using this option once the specified calendar date has passed.

For versioned buckets, the expiry rule applies only to the *current* object version. Use the [`--noncurrentversion-expiration-days`](#mc.ilm.edit.-noncurrentversion-expiration-days) option to apply expiration behavior to noncurrent object versions.

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

Mutually exclusive with the following options:

- [`--expired-object-delete-marker`](#mc.ilm.edit.-expired-object-delete-marker)

See [Object Deletion](/administration/object-management/object-delete/#minio-object-delete) for more information.

##### `--expired-object-delete-marker` {#mc.ilm.edit.-expired-object-delete-marker}

*mc-cmd*

*Optional*

Specify this option to direct MinIO to remove delete markers for objects with no remaining object versions. Specifically, the delete marker is the *only* remaining “version” of the given object.

This option is mutually exclusive with the following option:

- [`--tags`](#mc.ilm.edit.-tags)
- [`--expiry-days`](#mc.ilm.edit.-expiry-days)

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) and [Object Deletion](/administration/object-management/object-delete/#minio-object-delete) for more information.

##### `--noncurrentversion-expiration-days` {#mc.ilm.edit.-noncurrentversion-expiration-days}

*mc-cmd*

*Optional*

The number of days to retain an object version after becoming *non-current* (i.e. a different version of that object is now the *HEAD*). MinIO marks noncurrent object versions for deletion after the specified number of days pass.

This option has the same behavior as the S3 `NoncurrentVersionExpiration` action.

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

##### `--noncurrentversion-transition-days` {#mc.ilm.edit.-noncurrentversion-transition-days}

*mc-cmd*

*Optional*

The number of days an object has been non-current (i.e. replaced by a newer version of that same object) after which MinIO marks the object version as eligible for transition. MinIO transitions the object to the configured remote storage tier specified to the [`--tier`](#mc.ilm.edit.-tier) once the system host datetime passes that calendar date.

This option has no effect on non-versioned buckets. Requires specifying [`--noncurrentversion-tier`](#mc.ilm.edit.-noncurrentversion-tier).

This option has the same behavior as the S3 `NoncurrentVersionTransition` action.

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

##### `--noncurrentversion-tier` {#mc.ilm.edit.-noncurrentversion-tier}

*mc-cmd*

*Optional*

The remote storage tier to which MinIO [transitions noncurrent objects versions](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering). Specify a remote storage tier created by [`mc admin tier`](/reference/deprecated/mc-admin-tier/#command-mc.admin.tier).

MinIO does *not* automatically migrate objects from the previously specified remote tier to the new remote tier. MinIO continues to route requests for objects stored on the old remote tier.

##### `--newer-noncurrentversions-expiration` {#mc.ilm.edit.-newer-noncurrentversions-expiration}

*mc-cmd*

*Optional*

The number of non-current versions of an object to retain before applying expiration. Older non-current versions beyond the specified number expire.

By default, MinIO does not retain any non-current versions when an expiration rule applies.

##### `--newer-noncurrentversions-transition` {#mc.ilm.edit.-newer-noncurrentversions-transition}

*mc-cmd*

*Optional*

The number of non-current versions of an object to keep on the current storage tier. Older non-current versions beyond the specified number transition to the specified tier.

By default, MinIO transitions all non-current versions when a transition rule applies.

##### `--tags` {#mc.ilm.edit.-tags}

*mc-cmd*

*Optional*

One or more ampersand `&`-delimited key-value pairs describing the object tags to which to apply the lifecycle configuration rule.

This option is mutually exclusive with the following option:

- [`--expired-object-delete-marker`](#mc.ilm.edit.-expired-object-delete-marker)

##### `--transition-days` {#mc.ilm.edit.-transition-days}

*mc-cmd*

*Optional*

The number of calendar days from object creation after which MinIO marks an object as eligible for transition. MinIO transitions the object to the configured remote storage tier specified to the [`--tier`](#mc.ilm.edit.-tier).

For versioned buckets, the transition rule applies only to the *current* object version. Use the [`--noncurrentversion-transition-days`](#mc.ilm.edit.-noncurrentversion-transition-days) option to apply transition behavior to noncurrent object versions.

Requires specifying [`--tier`](#mc.ilm.edit.-tier).

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

##### `--tier` {#mc.ilm.edit.-tier}

*mc-cmd*

*Optional*

The remote storage tier to which MinIO [transition objects](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering). Specify a remote storage tier created by [`mc admin tier`](/reference/deprecated/mc-admin-tier/#command-mc.admin.tier).

Required if specifying [`--transition-days`](#mc.ilm.edit.-transition-days).

MinIO does *not* automatically migrate objects from the previously specified remote tier to the new remote tier. MinIO continues to route requests for objects stored on the old remote tier.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Modify an Existing Lifecycle Management Rule {#modify-an-existing-lifecycle-management-rule}

Use [`mc ilm edit`](#command-mc.ilm.edit) with [`--id`](#mc.ilm.edit.-id) to modify an existing object expiration rule:

```shell
mc ilm edit ALIAS/PATH --id "RULEID" [FLAGS]
```

- Replace [`ALIAS`](#mc.ilm.edit.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.ilm.edit.ALIAS) with the path to the bucket on the S3-compatible host.
- Replace `RULEID` with the unique ID of the object lifecycle management rule. Use [`mc ilm rule ls`](/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls) to find the `RULEID`.
- Specify any additional flags to add or modify the lifecycle management rule. For example, specify [`--transition-days`](#mc.ilm.edit.-transition-days) to override the existing transition days value for the rule.

### Disable a Lifecycle Management Rule {#disable-a-lifecycle-management-rule}

Use [`mc ilm edit`](#command-mc.ilm.edit) with [`--disable`](#mc.ilm.edit.-disable) to stop using an existing management rule.

```shell
mc ilm edit --id "RULEID" --disable myminio/mybucket
```

- Replace `RULEID` with the unique ID of the object lifecycle management rule. Use [`mc ilm rule ls`](/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls) to find the `RULEID`.
- Replace `myminio` with the ALIAS of the deployment where the rule exists.
- Replace `mybucket` with the bucket for the rule.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

---
title: "mc ilm add"
url: "/reference/deprecated/mc-ilm-add/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-ilm-add"></a>
<a id="minio-mc-ilm-add"></a>

<a id="command-mc.ilm.add"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

`mc ilm add` replaced by [`mc ilm rule add`](/reference/minio-mc/mc-ilm-rule-add/#command-mc.ilm.rule.add).
{{% /alert %}}

## Syntax {#syntax}

The [`mc ilm add`](#command-mc.ilm.add) command adds an object lifecycle management rule to a bucket.

The command supports adding both [Transition (Tiering)](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering) and [Expiration](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) lifecycle management rules.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command adds new lifecycle management rules to the `mydata` bucket on the `myminio` deployment:

```shell
mc ilm add --expire-days 90 --noncurrent-expire-days 30 myminio/mydata

mc ilm add --expire-delete-marker myminio/mydata

mc ilm add --transition-days 30 --transition-tier "COLDTIER" myminio/mydata

mc ilm add --noncurrent-transition-days 7 --noncurrent-transition-tier "COLDTIER"
```

The configured rules have the following effect:

- Delete objects more than 90 days old
- Delete objects 30 days after they become non-current
- Delete `DeleteMarker` tombstones if that object has no other versions remaining.
- Transition objects more than 30 days old to the `COLDTIER` remote tier.
- Transition objects 7 days after they become non-current to the `COLDTIER` remote tier.
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ilm add                                    \
                 [--prefix string]                          \
                 [--tags string]                            \
                 --expire-days "integer"                    \
                 [--expire-delete-marker]                   \
                 [--transition-days "string"]               \
                 [--transition-tier "string"]               \
                 [--noncurrent-expire-days "integer"]       \
                 [--noncurrent-expire-newer "integer"]      \
                 [--noncurrent-transition-days "integer"]   \
                 [--noncurrent-transition-tier "string"]    \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.ilm.add.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) and bucket on the MinIO deployment to which to add the object lifecycle management rule.

For example:

```text
mc ilm add myminio/mydata
```

##### `--prefix` {#mc.ilm.add.-prefix}

*mc-cmd*

*Optional*

Restrict the management rule to a specific object prefix.

For example:

```text
mc ilm add --prefix "meetingnotes/" myminio/mydata/ --expire-days "90"
```

The command creates a rule that expires objects in the `mydata` bucket of the `myminio` ALIAS after 90 days for any object with the `meetingnotes/` prefix.

##### `--tags` {#mc.ilm.add.-tags}

*mc-cmd*

*Optional*

One or more ampersand `&`-delimited key-value pairs describing the object tags to use for filtering objects to which the lifecycle configuration rule applies.

This option is mutually exclusive with the following option:

- [`--expire-delete-marker`](#mc.ilm.add.-expire-delete-marker)

##### `--expire-days` {#mc.ilm.add.-expire-days}

*mc-cmd*

*Required*

The number of days to retain an object after being created. MinIO marks the object for deletion after the specified number of days pass. Specify the number of days as an integer, e.g. `30` for 30 days.

For versioned buckets, the expiry rule applies only to the *current* object version. Use the [`--noncurrent-expire-days`](#mc.ilm.add.-noncurrent-expire-days) option to apply expiration behavior to noncurrent object versions.

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

Mutually exclusive with the following options:

- [`--expire-delete-marker`](#mc.ilm.add.-expire-delete-marker)

For more complete documentation on object expiration, see [Object Expiration](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) and [Object Deletion](/administration/object-management/object-delete/#minio-object-delete).

##### `--expire-delete-marker` {#mc.ilm.add.-expire-delete-marker}

*mc-cmd*

*Optional*

Specify this option to direct MinIO to remove delete markers for objects with no remaining object versions. Specifically, the delete marker is the *only* remaining “version” of the given object.

This option is mutually exclusive with the following option:

- [`--tags`](#mc.ilm.add.-tags)
- [`--expire-days`](#mc.ilm.add.-expire-days)

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

For more complete documentation on object expiration, see [Object Expiration](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) and [Object Deletion](/administration/object-management/object-delete/#minio-object-delete).

##### `--transition-days` {#mc.ilm.add.-transition-days}

*mc-cmd*

*Optional*

The number of calendar days from object creation after which MinIO marks an object as eligible for transition. MinIO transitions the object to the configured remote tier specified to the [`--transition-tier`](#mc.ilm.add.-transition-tier). Specify the number of days as an integer, e.g. `30` for 30 days.

For versioned buckets, the transition rule applies only to the *current* object version. Use the [`--noncurrent-transition-days`](#mc.ilm.add.-noncurrent-transition-days) option to apply transition behavior to noncurrent object versions.

Requires specifying [`--transition-tier`](#mc.ilm.add.-transition-tier).

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

For more complete documentation on object transition, see [Object Transition (“Tiering”)](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering).

##### `--transition-tier` {#mc.ilm.add.-transition-tier}

*mc-cmd*

*Optional*

The remote tier to which MinIO [transition objects](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering). Specify an existing remote tier created by [`mc admin tier`](/reference/deprecated/mc-admin-tier/#command-mc.admin.tier).

Required if specifying [`--transition-days`](#mc.ilm.add.-transition-days).

##### `--noncurrent-expire-days` {#mc.ilm.add.-noncurrent-expire-days}

*mc-cmd*

*Optional*

The number of days to retain an object version after becoming *non-current* (i.e. a different version of that object is now the *HEAD*). MinIO marks noncurrent object versions for deletion after the specified number of days pass.

This option has the same behavior as the S3 `NoncurrentVersionExpiration` action.

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

##### `--noncurrent-transition-days` {#mc.ilm.add.-noncurrent-transition-days}

*mc-cmd*

*Optional*

The number of days an object has been non-current (i.e. replaced by a newer version of that same object) after which MinIO marks the object version as eligible for transition. MinIO transitions the object to the configured remote tier specified to the [`--transition-tier`](#mc.ilm.add.-transition-tier) once the system host datetime passes that calendar date.

This option has no effect on non-versioned buckets. Requires specifying [`--noncurrent-transition-tier`](#mc.ilm.add.-noncurrent-transition-tier).

This option has the same behavior as the S3 `NoncurrentVersionTransition` action.

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

##### `--noncurrent-transition-tier` {#mc.ilm.add.-noncurrent-transition-tier}

*mc-cmd*

*Optional*

The remote tier to which MinIO [transitions noncurrent objects versions](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering). Specify a remote tier created by [`mc admin tier`](/reference/deprecated/mc-admin-tier/#command-mc.admin.tier).

##### `--noncurrent-expire-newer` {#mc.ilm.add.-noncurrent-expire-newer}

*mc-cmd*

*Optional*

The maximum number of non-current object versions to retain, ordered from newest to oldest.

Use this flag to retain a certain number of past versions of a file in a first in, first out fashion. After retaining the maximum number of non-current versions, MinIO marks any remaining older non-current object versions as eligible for expiration.

The following table lists a number of object versions and their expiration eligibility based on `--noncurrent-expire-newer 3`:

<table>
  <tbody>
    <tr>
      <td><p>v5 (current version)</p></td>
      <td><p>Current version not affected by ILM rules.</p></td>
    </tr>
    <tr>
      <td><p>v4</p></td>
      <td><p>retained</p></td>
    </tr>
    <tr>
      <td><p>v3</p></td>
      <td><p>retained</p></td>
    </tr>
    <tr>
      <td><p>v2</p></td>
      <td><p>retained</p></td>
    </tr>
    <tr>
      <td><p>v1</p></td>
      <td><p>marked for expiry</p></td>
    </tr>
  </tbody>
</table>

MinIO retains the current version, v5. MinIO also retains the next `3` non-current versions, starting with the newest. This means MinIO marks `v4`, `v3`, and `v2` for the three non-current version to retain.

`v1` would be a fourth non-current version, which falls outside the limit of non-current versions to retain, so MinIO marks `v1` for expiration.

Updating the number for this flag only impacts the unmarked versions of objects. Any versions already marked for expiration do not change if you increase the number to retain.

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Expire All Bucket Contents After Number of Days {#expire-all-bucket-contents-after-number-of-days}

Use [`mc ilm add`](#command-mc.ilm.add) with [`--expire-days`](#mc.ilm.add.-expire-days) to mark bucket contents for expiration after a number of days pass from the object’s creation:

```shell
mc ilm add ALIAS/PATH --expire-days "DAYS"
```

- Replace [`ALIAS`](#mc.ilm.add.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.ilm.add.ALIAS) with the path to the bucket on the S3-compatible host.
- Replace [`DATE`](#mc.ilm.add.-expire-days) with the number of days after which to expire the object. For example, specify `30` to expire the object 30 days after creation.

### Transition Non-Current Object Versions at a Prefix to a Different Tier {#transition-non-current-object-versions-at-a-prefix-to-a-different-tier}

Use the [`mc ilm add`](#command-mc.ilm.add) with [`--prefix`](#mc.ilm.add.-prefix) and [`--transition-tier`](#mc.ilm.add.-transition-tier) to transition older non-current versions of an object to a different storage tier.

```shell
mc ilm add --prefix "doc/" --transition-days "90" --trasition-tier "MINIOTIER-1"                  \
       --noncurrent-transition-days "45" --noncurrent-transition-tier "MINIOTIER-2"  \
       myminio/mybucket/
```

This command looks at the contents with the `doc/` prefix in the `mybucket` bucket on the `myminio` deployment.

- Current objects in the prefix older than 90 days move to the `MINIOTIER-1` storage tier.
- Non-current objects in the prefix older than 45 days move to the `MINIOTIER-2` storage tier.
- Both `MINIOTIER-1` and `MINIOTIER-2` have already been created with [`mc admin tier add`](/reference/deprecated/mc-admin-tier/#mc.admin.tier.add).

### Expire All Objects at a Prefix, Retain Current Object Versions Longer Than Non-Current Object Versions {#expire-all-objects-at-a-prefix-retain-current-object-versions-longer-than-non-current-object-versions}

Use the [`mc ilm add`](#command-mc.ilm.add) command with [`--prefix`](#mc.ilm.add.-prefix), [`--expire-days`](#mc.ilm.add.-expire-days), and [`--noncurrent-expire-days`](#mc.ilm.add.-noncurrent-expire-days) to expire current and non-current versions of an object at different times.

```shell
mc ilm add --prefix "doc/" --expire-days "300" --noncurrent-expire-days "100" myminio/mybucket/
```

This command looks at the contents with the `doc/` prefix in the `mybucket` bucket on the `myminio` deployment.

- Current objects expire after 300 days.
- Non-current objects expire after 100 days.

## Behavior {#behavior}

### Lifecycle Management Object Scanner {#lifecycle-management-object-scanner}

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against the configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

### Expiry vs Transition {#expiry-vs-transition}

MinIO supports specifying both expiry and transition rules in the same bucket or bucket prefix. MinIO can execute an expiration rule on an object regardless of its transition status. Use [`mc ilm ls`](/reference/deprecated/mc-ilm-ls/#command-mc.ilm.ls) to review the currently configured object lifecycle management rules for any potential interactions between expiry and transition rules.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

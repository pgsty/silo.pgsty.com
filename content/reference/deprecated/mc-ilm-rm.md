---
title: "mc ilm rm"
url: "/reference/deprecated/mc-ilm-rm/"
weight: 60
minio_origin: true
silo_modified: false
---

<a id="mc-ilm-rm"></a>
<a id="minio-mc-ilm-rm"></a>

<a id="command-mc.ilm.remove"></a>

<a id="command-mc.ilm.rm"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

`mc ilm rm` replaced by [`mc ilm rule rm`](/reference/minio-mc/mc-ilm-rule-rm/#command-mc.ilm.rule.rm).
{{% /alert %}}

## Syntax {#syntax}

The [`mc ilm rm`](#command-mc.ilm.rm) command removes an object lifecycle management rule from a MinIO Bucket.

The [`mc ilm remove`](#command-mc.ilm.remove) command has equivalent functionality to [`mc ilm rm`](#command-mc.ilm.rm).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command removes a single lifecycle management rule from the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc ilm rm --id "bgrt1ghju" myminio/mydata
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ilm rm                          \
                 --id "string" | (--all --force) \
                 ALIAS                           \
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.ilm.rm.ALIAS}

*mc-cmd*

*Required* The [alias](/reference/minio-mc/mc-alias-set/#alias) and full path to the bucket on the MinIO deployment to which to remove the object lifecycle management rule. For example:

```text
mc ilm rm myminio/mydata
```

##### `all` {#mc.ilm.rm.all}

*mc-cmd*

*Required* Removes all rules in the bucket. Mutually exclusive with [`mc ilm rm id`](#mc.ilm.rm.id).

Mutually exclusive with [`mc ilm rm id`](#mc.ilm.rm.id)

Requires including [`force`](#mc.ilm.rm.force).

##### `force` {#mc.ilm.rm.force}

*mc-cmd*

Required if specifying [`all`](#mc.ilm.rm.all).

##### `id` {#mc.ilm.rm.id}

*mc-cmd*

*Required* The unique ID of the rule. Use [`mc ilm rule ls`](/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls) to list bucket rules and retrieve the `id` for the rule you want to remove.

Mutually exclusive with [`mc ilm rm all`](#mc.ilm.rm.all)

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Remove a Bucket Lifecycle Management Rule {#remove-a-bucket-lifecycle-management-rule}

Use [`mc ilm rm`](#command-mc.ilm.rm) to remove a bucket lifecycle management rule:

```shell
mc ilm rm --id "RULE" ALIAS/PATH
```

- Replace [`RULE`](#mc.ilm.rm.id) with the unique name of the lifecycle management rule.
- Replace [`ALIAS`](#mc.ilm.rm.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.ilm.rm.ALIAS) with the path to the bucket on the S3-compatible host.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

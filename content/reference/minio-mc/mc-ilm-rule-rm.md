---
title: "mc ilm rule rm"
url: "/reference/minio-mc/mc-ilm-rule-rm/"
weight: 60
minio_origin: true
silo_modified: false
---

<a id="mc-ilm-rule-rm"></a>
<a id="minio-mc-ilm-rule-rm"></a>

<a id="command-mc.ilm.rule.rm"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

`mc ilm rule rm` replaces `mc ilm rm`.
{{% /alert %}}

## Syntax {#syntax}

The [`mc ilm rule rm`](#command-mc.ilm.rule.rm) command removes an object lifecycle management rule from a MinIO Bucket.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command removes a single lifecycle management rule from the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc ilm rule rm --id "bgrt1ghju" myminio/mydata
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ilm rule rm                         \
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

##### `ALIAS` {#mc.ilm.rule.rm.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) and full path to the bucket on the MinIO deployment to which to remove the object lifecycle management rule. For example:

```text
mc ilm rule rm myminio/mydata
```

##### `--all` {#mc.ilm.rule.rm.-all}

*mc-cmd*

*Optional*

Removes all rules in the bucket. Requires including [`--force`](#mc.ilm.rule.rm.-force).

Mutually exclusive with [`--id`](#mc.ilm.rule.rm.-id).

##### `--force` {#mc.ilm.rule.rm.-force}

*mc-cmd*

*Optional*

Required if specifying [`--all`](#mc.ilm.rule.rm.-all).

##### `--id` {#mc.ilm.rule.rm.-id}

*mc-cmd*

*Optional*

The unique ID of the rule. Use [`mc ilm rule ls`](/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls) to list bucket rules and retrieve the `id` for the rule you want to remove.

Mutually exclusive with [`mc ilm rule rm --all`](#mc.ilm.rule.rm.-all)

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Remove a Bucket Lifecycle Management Rule {#remove-a-bucket-lifecycle-management-rule}

Use [`mc ilm rule rm`](#command-mc.ilm.rule.rm) to remove a bucket lifecycle management rule:

```shell
mc ilm rule rm --id "RULE" ALIAS/PATH
```

- Replace `RULE` with the unique identifier of the lifecycle management rule. Use [`mc ilm rule ls`](/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls) to find the ID to use.
- Replace [`ALIAS`](#mc.ilm.rule.rm.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace `PATH` with the path to the bucket on the S3-compatible host.

## Required Permissions {#required-permissions}

For permissions required to remove a rule, refer to the [required permissions](/reference/minio-mc/mc-ilm-rule/#minio-mc-ilm-rule-permissions) on the parent command.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

---
title: "mc ilm ls"
url: "/reference/deprecated/mc-ilm-ls/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="mc-ilm-ls"></a>
<a id="minio-mc-ilm-ls"></a>

<a id="command-mc.ilm.ls"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

`mc ilm ls` replaced by [`mc ilm rule ls`](/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls).
{{% /alert %}}

## Syntax {#syntax}

The [`mc ilm ls`](#command-mc.ilm.ls) command summrizes all configured object lifecycle management rules on a MinIO bucket in a tabular format.

The output of the command might resemble the following:

```shell
┌───────────────────────────────────────────────────────────────────────────────┐
│ Transition for latest version (Transition)                                    │
├────────┬─────────┬────────┬─────────────────────┬──────────────┬──────────────┤
│ ID     │ STATUS  │ PREFIX │ TAGS                │ DAYS TO TIER │ TIER         │
├────────┼─────────┼────────┼─────────────────────┼──────────────┼──────────────┤
│ rule-1 │ Enabled │ doc/   │ key1=val1&key2=val2 │            0 │ WARM-MINIO-1 │
└────────┴─────────┴────────┴─────────────────────┴──────────────┴──────────────┘
┌────────────────────────────────────────────────────────────────┐
│ Transition for older versions (NoncurrentVersionTransition)    │
├────────┬─────────┬────────┬──────┬──────────────┬──────────────┤
│ ID     │ STATUS  │ PREFIX │ TAGS │ DAYS TO TIER │ TIER         │
├────────┼─────────┼────────┼──────┼──────────────┼──────────────┤
│ rule-2 │ Enabled │ logs/  │ -    │           10 │ WARM-MINIO-1 │
└────────┴─────────┴────────┴──────┴──────────────┴──────────────┘
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Expiration for latest version (Expiration)                                             │
├────────┬─────────┬────────┬─────────────────────┬────────────────┬─────────────────────┤
│ ID     │ STATUS  │ PREFIX │ TAGS                │ DAYS TO EXPIRE │ EXPIRE DELETEMARKER │
├────────┼─────────┼────────┼─────────────────────┼────────────────┼─────────────────────┤
│ rule-1 │ Enabled │ doc/   │ key1=val1&key2=val2 │             30 │ false               │
└────────┴─────────┴────────┴─────────────────────┴────────────────┴─────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Expiration for older versions (NoncurrentVersionExpiration)                      │
├────────┬─────────┬────────┬─────────────────────┬────────────────┬───────────────┤
│ ID     │ STATUS  │ PREFIX │ TAGS                │ DAYS TO EXPIRE │ KEEP VERSIONS │
├────────┼─────────┼────────┼─────────────────────┼────────────────┼───────────────┤
│ rule-1 │ Enabled │ doc/   │ key1=val1&key2=val2 │             15 │             0 │
│ rule-2 │ Enabled │ logs/  │ -                   │              1 │             3 │
└────────┴─────────┴────────┴─────────────────────┴────────────────┴───────────────┘
```

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command lists all lifecycle management rules for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc ilm ls myminio/mydata
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The [`mc ilm ls`](#command-mc.ilm.ls) command has the following syntax:

```shell
mc [GLOBALFLAGS] ilm ls                        \
                 [--expiry | --transition]     \
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.ilm.ls.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) and full path to the bucket on the MinIO deployment for which to list the object lifecycle management rules. For example:

```text
mc ilm ls myminio/mydata
```

##### `--expiry` {#mc.ilm.ls.-expiry}

*mc-cmd*

*Optional*

[`mc ilm ls`](#command-mc.ilm.ls) returns only fields related to lifecycle rule expiration.

Mutually exclusive with [`--transition`](#mc.ilm.ls.-transition).

##### `--transition` {#mc.ilm.ls.-transition}

*mc-cmd*

*Optional*

[`mc ilm ls`](#command-mc.ilm.ls) returns only fields related to lifecycle rule transition.

Mutually exclusive with [`--expiry`](#mc.ilm.ls.-expiry).

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### List Bucket Lifecycle Management Rules {#list-bucket-lifecycle-management-rules}

Use [`mc ilm ls`](#command-mc.ilm.ls) to list a bucket’s lifecycle management rules:

```shell
mc ilm ls ALIAS/PATH
```

- Replace [`ALIAS`](#mc.ilm.ls.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.ilm.ls.ALIAS) with the path to the bucket on the S3-compatible host.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

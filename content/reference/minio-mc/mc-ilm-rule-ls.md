---
title: "mc ilm rule ls"
url: "/reference/minio-mc/mc-ilm-rule-ls/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="mc-ilm-rule-ls"></a>
<a id="minio-mc-ilm-rule-ls"></a>

<a id="command-mc.ilm.rule.list"></a>

<a id="command-mc.ilm.rule.ls"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

`mc ilm rule ls` replaces `mc ilm ls`.
{{% /alert %}}

{{% alert color="info" %}}
**Changed: RELEASE.2023-05-26T23-31-54Z**

`mc ilm rule ls --json` output includes the policy modification time in `updateAt`.
{{% /alert %}}

## Syntax {#syntax}

The [`mc ilm rule ls`](#command-mc.ilm.rule.ls) command summarizes all configured object lifecycle management rules on a MinIO bucket in a tabular format.

The [`mc ilm rule list`](#command-mc.ilm.rule.list) command has equivalent functionality to [`mc ilm rule ls`](#command-mc.ilm.rule.ls).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command lists all lifecycle management rules for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc ilm rule ls myminio/mydata
```

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

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The [`mc ilm rule ls`](#command-mc.ilm.rule.ls) command has the following syntax:

```shell
mc [GLOBALFLAGS] ilm rule ls     \
                 [--expiry]      \
                 [--transition]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.ilm.rule.ls.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) and full path to the bucket on the MinIO deployment for which to list the object lifecycle management rules. For example:

```text
mc ilm rule ls myminio/mydata
```

##### `--expiry` {#mc.ilm.rule.ls.-expiry}

*mc-cmd*

*Optional*

[`mc ilm rule ls`](#command-mc.ilm.rule.ls) returns only fields related to lifecycle rule expiration.

Mutually exclusive with [`--transition`](#mc.ilm.rule.ls.-transition).

##### `--transition` {#mc.ilm.rule.ls.-transition}

*mc-cmd*

*Optional*

[`mc ilm rule ls`](#command-mc.ilm.rule.ls) returns only fields related to lifecycle rule transition.

Mutually exclusive with [`--expiry`](#mc.ilm.rule.ls.-expiry).

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### List Bucket Lifecycle Management Rules {#list-bucket-lifecycle-management-rules}

Use [`mc ilm rule ls`](#command-mc.ilm.rule.ls) to list a bucket’s lifecycle management rules:

```shell
mc ilm rule ls ALIAS/PATH
```

- Replace [`ALIAS`](#mc.ilm.rule.ls.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace `PATH` with the path to the bucket on the S3-compatible host.

### Show Policy Modification Time {#show-policy-modification-time}

Use [`mc ilm rule ls`](#command-mc.ilm.rule.ls) with :option::*–json &lt;mc.–json&gt;* to show the time the policy for a bucket was last updated.

```shell
mc ilm rule ls ALIAS/PATH --json
```

- Replace [`ALIAS`](#mc.ilm.rule.ls.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace `PATH` with the path to the bucket on the S3-compatible host.

The `updateAt` property in the JSON output contains the date and time the policy was updated.

The output resembles the following:

```shell
{
 "status": "success",
 "target": "myminio/mybucket",
 "config": {
  "Rules": [
   {
    "Expiration": {
     "Days": 30
    },
    "ID": "ci1o2mg0sko6f1r3krv0",
    "Status": "Enabled"
   }
  ]
 },
 "updatedAt": "2023-06-09T19:45:30Z"
}
```

## Required Permissions {#required-permissions}

For permissions required to list rules, refer to the [required permissions](/reference/minio-mc/mc-ilm-rule/#minio-mc-ilm-rule-permissions) on the parent command.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

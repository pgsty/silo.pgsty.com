---
title: "mc admin policy info"
url: "/reference/minio-mc-admin/mc-admin-policy-info/"
weight: 50
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-policy-info.rst
upstream_modified: false
---

<a id="mc-admin-policy-info"></a>

<a id="command-mc.admin.policy.info"></a>

## Syntax {#syntax}

Returns the specified policy in JSON format if it exists on the target MinIO deployment.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command displays the contents of the `writeonly` policy on the [alias](/glossary/#term-alias) `myminio`.

```shell
 mc admin policy info myminio writeonly
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc admin policy info TARGET POLICYNAME
                     [--policy-file, -f <path>]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

The [`mc admin policy info`](#command-mc.admin.policy.info) command accepts the following arguments:

##### `TARGET` {#mc.admin.policy.info.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment from which to display the specified policy.

##### `POLICYNAME` {#mc.admin.policy.info.POLICYNAME}

*mc-cmd*

*Required*

The name of the policy whose details you want to display.

##### `--policy-file` {#mc.admin.policy.info.-policy-file}

*mc-cmd*

*Optional*

Specifly the path of a file to write the contents of the specified policy JSON. If the path already exists, the command overwrites the existing file with the contents of the specified file.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

Display the contents of the `writeonly` policy on the [alias](/glossary/#term-alias) `myminio`.

```shell
mc admin policy info myminio writeonly
```

Show information on a given policy and write the policy JSON content to /tmp/policy.json.

```shell
mc admin policy info myminio writeonly --policy-file /tmp/policy.json
```

### Output {#output}

The command returns output that resembles the following:

```json
{
   "Version": "2012-10-17",
   "Statement": [
      {
         "Effect": "Allow",
         "Action": [
            "s3:PutObject"
         ],
         "Resource": [
            "arn:aws:s3:::*"
         ]
      }
   ]
}
```

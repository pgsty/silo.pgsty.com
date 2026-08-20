---
title: "mc admin policy ls"
url: "/reference/minio-mc-admin/mc-admin-policy-list/"
weight: 60
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-policy-list.rst
upstream_modified: false
---

<a id="mc-admin-policy-ls"></a>

<a id="command-mc.admin.policy.ls"></a>

<a id="command-mc.admin.policy.list"></a>

## Syntax {#syntax}

Lists all policies on the target MinIO deployment.

The [`mc admin policy list`](#command-mc.admin.policy.list) command has equivalent functionality to [`mc admin policy ls`](#command-mc.admin.policy.ls).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command displays a list of the policies currently current on the [alias](/glossary/#term-alias) `play`.

```shell
mc admin policy ls play
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc admin policy ls TARGET
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

The [`mc admin policy ls`](#command-mc.admin.policy.ls) command accepts the following arguments:

##### `TARGET` {#mc.admin.policy.list.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment from which the command lists the available policies.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

List the policies that exist on the deployment at alias `myminio`.

```shell
mc admin policy ls myminio
```

### Output {#output}

The command returns output that resembles the following:

```shell
readwrite
writeonly
```

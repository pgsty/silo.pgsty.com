---
title: "mc admin policy rm"
url: "/reference/minio-mc-admin/mc-admin-policy-remove/"
weight: 70
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-policy-remove.rst
upstream_modified: true
---

<a id="mc-admin-policy-rm"></a>

<a id="command-mc.admin.policy.remove"></a>

<a id="command-mc.admin.policy.rm"></a>

## Syntax {#syntax}

Removes a custom IAM policy from a SILO deployment (rejected if the policy is still in use; unmodified built-in policies cannot be removed). In the [Server 20261026](/blog/release/silo-20261026/#server-20261026), removing an explicit built-in policy override immediately resets it to its native definition while retaining the deletion revision against stale overrides (see [Console policy management](/administration/console/security-and-access/#minio-console-admin-policies)).

The [`mc admin policy remove`](#command-mc.admin.policy.remove) command has equivalent functionality to [`mc admin policy rm`](#command-mc.admin.policy.rm).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command removes the policy names `project-readonly` from the `myminio` MinIO deployment:

```shell
mc admin policy rm myminio project-readonly
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc admin policy rm TARGET POLICYNAME
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

The [`mc admin policy rm`](#command-mc.admin.policy.rm) command accepts the following arguments:

##### `TARGET` {#mc.admin.policy.rm.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment from which to remove the policy.

##### `POLICYNAME` {#mc.admin.policy.rm.POLICYNAME}

*mc-cmd*

The name of the policy to remove.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

Remove a policy called `listbuckets`.

```shell
mc admin policy rm myminio listbuckets
```

---
title: "mc admin policy create"
url: "/reference/minio-mc-admin/mc-admin-policy-create/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-policy-create.rst
upstream_modified: false
---

<a id="mc-admin-policy-create"></a>

<a id="command-mc.admin.policy.create"></a>

## Syntax {#syntax}

Creates a new policy on the target MinIO deployment.

MinIO deployments include the following [built-in policies](/administration/identity-access-management/policy-based-access-control/#minio-policy-built-in) by default:

- [`readonly`](/administration/identity-access-management/policy-based-access-control/#userpolicy.readonly)
- [`readwrite`](/administration/identity-access-management/policy-based-access-control/#userpolicy.readwrite)
- [`diagnostics`](/administration/identity-access-management/policy-based-access-control/#userpolicy.diagnostics)
- [`writeonly`](/administration/identity-access-management/policy-based-access-control/#userpolicy.writeonly)

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
Consider the following JSON policy document saved at a file called `/tmp/listmybuckets.json`:

```javascript
{
   "Version": "2012-10-17",
   "Statement": [
      {
         "Effect": "Allow",
         "Action": [
            "s3:ListAllMyBuckets"
         ],
         "Resource": [
            "arn:aws:s3:::*"
         ]
      }
   ]
}
```

The following command creates a new policy called `listmybuckets` on the [alias](/glossary/#term-alias) `myminio` using the policy found at the file `/tmp/listmybuckets.json`.

```shell
mc admin policy create myminio listmybuckets /tmp/listmybuckets.json
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc admin policy create     \
                TARGET     \
                POLICYNAME \
                POLICYPATH
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

The [`mc admin policy create`](#command-mc.admin.policy.create) command accepts the following arguments:

##### `TARGET` {#mc.admin.policy.create.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment on which to add the new policy.

##### `POLICYNAME` {#mc.admin.policy.create.POLICYNAME}

*mc-cmd*

The name of the policy to add.

Specifying the name of an existing policy overwrites that policy on the [`TARGET`](#mc.admin.policy.create.TARGET) MinIO deployment.

##### `POLICYPATH` {#mc.admin.policy.create.POLICYPATH}

*mc-cmd*

The file path of the policy to add. The file *must* be a JSON-formatted file with [IAM-compatible syntax](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies.html) and no more than 2048 characters.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

Create a new policy called `writeonly` from the JSON file at `/tmp/writeonly.json` on the deployment at the alias `myminio`.

```shell
mc admin policy create myminio writeonly /tmp/writeonly.json
```

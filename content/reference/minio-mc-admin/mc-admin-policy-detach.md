---
title: "mc admin policy detach"
url: "/reference/minio-mc-admin/mc-admin-policy-detach/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="mc-admin-policy-detach"></a>

<a id="command-mc.admin.policy.detach"></a>

## Syntax {#syntax}

Remove one or more IAM policies from either a [MinIO-managed user or a group](/administration/identity-access-management/minio-user-management/#minio-users).

Exactly one [`--user`](#mc.admin.policy.detach.-user) or one [`--group`](#mc.admin.policy.detach.-group) is required.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command detaches the policy `readonly` from the user `james` on the deployment at alias `myminio`.

```shell
mc admin policy detach myminio readonly --user james
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc admin policy detach TARGET                         \
                       POLICY                         \
                       [POLICY...]                    \
                       [--user USER | --group GROUP]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

{{% alert color="warning" %}}
**Important**

This command is intended for managing policy associations for [MinIO-managed](/administration/identity-access-management/minio-user-management/#minio-users) users only.

For managing policies to OpenID-managed users, see [OpenID Connect Access Management](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid).

For detaching policies from Active Directory/LDAP users or groups, use [`mc idp ldap policy detach`](/reference/minio-mc/mc-idp-ldap-policy-detach/#command-mc.idp.ldap.policy.detach).
{{% /alert %}}

### Parameters {#parameters}

The [`mc admin policy detach`](#command-mc.admin.policy.detach) command accepts the following arguments:

##### `TARGET` {#mc.admin.policy.detach.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment with the user or group for which you want to detach one or more policies.

##### `POLICY` {#mc.admin.policy.detach.POLICY}

*mc-cmd*

*Required*

The name of the policy to detach from either the user or the group. You may detach multiple policies at once by separating each policy name with a space.

MinIO deployments include the following [built-in policies](/administration/identity-access-management/policy-based-access-control/#minio-policy-built-in) by default:

- [`readonly`](/administration/identity-access-management/policy-based-access-control/#userpolicy.readonly)
- [`readwrite`](/administration/identity-access-management/policy-based-access-control/#userpolicy.readwrite)
- [`diagnostics`](/administration/identity-access-management/policy-based-access-control/#userpolicy.diagnostics)
- [`writeonly`](/administration/identity-access-management/policy-based-access-control/#userpolicy.writeonly)

##### `--user` {#mc.admin.policy.detach.-user}

*mc-cmd*

*Optional*

The username of the identity you want to detach the policy or policies from. You may only list one user.

You must include either the `--user` flag or the `--group` flag. You may not use the `--user` flag at the same time as the `--group` flag.

##### `--group` {#mc.admin.policy.detach.-group}

*mc-cmd*

*Optional*

The name of the group identity you want to detach the policy or policies from. You may only list one group.

All users with membership in the group lose access to any permissions granted by the policies associated to the group, unless those are granted by other policies or groups the users belong to.

You must include either the `--group` flag or the `--user` flag. You may not use the `--group` flag at the same time as the `--user` flag.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

Detach the policy `readonly` from the user `james` on the deployment at alias `myminio`.

```shell
mc admin policy detach myminio readonly --user james
```

Detach the `audit-policy` and `acct-policy` policies from group `legal` on the deployment at alias `myminio`.

```shell
mc admin policy detach myminio audit-policy acct-policy --group legal
```

---
title: "mc admin policy attach"
url: "/reference/minio-mc-admin/mc-admin-policy-attach/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-policy-attach.rst
upstream_modified: false
---

<a id="mc-admin-policy-attach"></a>

<a id="command-mc.admin.policy.attach"></a>

## Syntax {#syntax}

Attaches one or more IAM policies to either a [MinIO-managed user or a group](/administration/identity-access-management/minio-user-management/#minio-users).

> [!NOTE]
> **Changed: RELEASE.2023-05-27T05-56-19Z**
>
> To successfully attach a policy, the referenced user or group must exist.

Exactly one [`--user`](#mc.admin.policy.attach.-user) or one [`--group`](#mc.admin.policy.attach.-group) is required.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command attaches the `readonly` policy to the user `james` on the deployment at [alias](/glossary/#term-alias) `myminio`.

```shell
mc admin policy attach myminio readonly --user james
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc admin policy attach                       \
                TARGET                       \
                POLICY                       \
                [POLICY...]                  \
                [--user USER | --group GROUP]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

> [!WARNING]
> **Important**
>
> This command is intended for managing policy associations for [MinIO-managed](/administration/identity-access-management/minio-user-management/#minio-users) users only.
>
> For attaching policies to OpenID-managed users, see [OpenID Connect Access Management](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid).
>
> For attaching policies to Active Directory/LDAP users or groups, use [`mc idp ldap policy attach`](/reference/minio-mc/mc-idp-ldap-policy-attach/#command-mc.idp.ldap.policy.attach).

### Parameters {#parameters}

The [`mc admin policy attach`](#command-mc.admin.policy.attach) command accepts the following arguments:

##### `TARGET` {#mc.admin.policy.attach.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment with the user or group for which you want to attach one or more policies.

##### `POLICY` {#mc.admin.policy.attach.POLICY}

*mc-cmd*

*Required*

The name of the policy to attach to either the user or the group.

You may attach multiple policies at once by separating each policy name with a space.

MinIO deployments include the following [built-in policies](/administration/identity-access-management/policy-based-access-control/#minio-policy-built-in) by default:

- [`readonly`](/administration/identity-access-management/policy-based-access-control/#userpolicy.readonly)
- [`readwrite`](/administration/identity-access-management/policy-based-access-control/#userpolicy.readwrite)
- [`diagnostics`](/administration/identity-access-management/policy-based-access-control/#userpolicy.diagnostics)
- [`writeonly`](/administration/identity-access-management/policy-based-access-control/#userpolicy.writeonly)

##### `--user` {#mc.admin.policy.attach.-user}

*mc-cmd*

*Optional*

The username of the identity you want to attach the policy or policies to. You may only list one user.

You must include either the `--user` flag or the `--group` flag. You may not use the `--user` flag at the same time as the `--group` flag.

##### `--group` {#mc.admin.policy.attach.-group}

*mc-cmd*

*Optional*

The name of the group identity you want to attach the policy or policies to. You may only list one group.

All users with membership in the group inherit the policies associated to the group.

You must include either the `--group` flag or the `--user` flag. You may not use the `--group` flag at the same time as the `--user` flag.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

Attach the `readonly` policy to user `james` on the deployment at alias `myminio`.

```shell
mc admin policy attach myminio readonly --user james
```

Attach the `audit-policy` and `acct-policy` policies to group `legal` on the deployment at alias `myminio`.

```shell
mc admin policy attach myminio audit-policy acct-policy --group legal
```

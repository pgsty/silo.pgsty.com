---
title: "mc admin idp ldap policy"
url: "/reference/deprecated/mc-admin-idp-ldap-policy/"
weight: 150
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/deprecated/mc-admin-idp-ldap-policy.rst
upstream_modified: false
---

<a id="mc-admin-idp-ldap-policy"></a>
<a id="minio-mc-admin-idp-ldap-policy"></a>

<a id="command-mc.admin.idp.ldap.policy"></a>

> [!NOTE]
> **Changed: RELEASE.2023-05-26T23-31-54Z**
>
> `mc admin idp ldap policy` and its subcommands replaced by [`mc idp ldap policy`](/reference/minio-mc/mc-idp-ldap-policy/#command-mc.idp.ldap.policy).

## Description {#description}

The [`mc admin idp ldap policy`](#command-mc.admin.idp.ldap.policy) command allows you to view the mapping relationships between policies and the associated groups or users.

The [`mc admin idp ldap policy`](#command-mc.admin.idp.ldap.policy) command has the following subcommands:

| Subcommand | Description |
| --- | --- |
| [`mc admin idp ldap policy attach`](#mc.admin.idp.ldap.policy.attach) | Attach a policy to an entity |
| [`mc admin idp ldap policy detach`](#mc.admin.idp.ldap.policy.detach) | Detach a policy from an entity |
| [`mc admin idp ldap policy entities`](#mc.admin.idp.ldap.policy.entities) | List policy entity mappings |

## Syntax {#syntax}

#### `attach` {#mc.admin.idp.ldap.policy.attach}

*mc-cmd*

Attach one or more polices to entity.

{{< tabs group="examples-syntax" >}}
{{< tab label="EXAMPLES" value="examples" >}}
The following example attaches two policies, `policy1` and `policy2`, to the `projectb` group on the `myminio` deployment.

```shell
 mc admin idp ldap policy attach myminio/                                               \
                                 policy1                                                \
                                 policy2                                                \
                                 --group='cn=projectb,ou=groups,ou=swengg,dc=min,dc=io'
```

The following example attaches the policy, `userpolicy`, to the user `bobfisher` on the `myminio` deployment.

```shell
 mc admin idp ldap policy attach myminio/                                               \
                                 mypolicy                                               \
                                 policy2                                                \
                                 --user='uid=bobfisher,ou=people,ou=hwengg,dc=min,dc=io'
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp ldap policy attach     \
                                POLICYNAME        \
                                [POLICY2] ...     \
                                ALIAS             \
                                [--user=`USER`]   \
                                [--group=`GROUP`]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for AD/LDAP integration.
- Replace `POLICYNAME` with the policy to attach to the entity. You may list multiple policies to attach to the entity.
- Use must use one of either the `--user` or `--group` flag. You may only use the flag once in the command. You cannot use both flags in the same command.
{{< /tab >}}
{{< /tabs >}}

#### `detach` {#mc.admin.idp.ldap.policy.detach}

*mc-cmd*

Detach one or more policies from an entity.

{{< tabs group="examples-syntax" >}}
{{< tab label="EXAMPLES" value="examples" >}}
The following example detaches two policies, `policy1` and `policy2`, from the `projectb` group on the `myminio` deployment.

```shell
 mc admin idp ldap policy detach myminio/                                               \
                                 policy1                                                \
                                 policy2                                                \
                                 --group='cn=projectb,ou=groups,ou=swengg,dc=min,dc=io'
```

The following example detaches the policy, `userpolicy`, from the user `bobfisher` on the `myminio` deployment.

```shell
 mc admin idp ldap policy detach myminio/                                               \
                                 mypolicy                                               \
                                 policy2                                                \
                                 --user='uid=bobfisher,ou=people,ou=hwengg,dc=min,dc=io'
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp ldap policy detach     \
                                POLICYNAME        \
                                [POLICY2] ...     \
                                ALIAS             \
                                [--user=`USER`]   \
                                [--group=`GROUP`]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for AD/LDAP integration.
- Replace `POLICYNAME` with the policy to detach from the entity. You may list multiple policies to detach from the entity.
- Use must use one of either the `--user` or `--group` flag. You may only use the flag once in the command. You cannot use both flags in the same command.
{{< /tab >}}
{{< /tabs >}}

#### `entities` {#mc.admin.idp.ldap.policy.entities}

*mc-cmd*

Display a list of mappings for a user, group, and/or policy.

{{< tabs group="examples-syntax" >}}
{{< tab label="EXAMPLES" value="examples" >}}
The following example lists all mappings for a specific policy, a set of groups, and a selection of users on the `myminio` deployment.

Specifically, it lists - Users mapped to the `finteam-policy` policy. - Policies assigned to the `uid=bobfisher,ou=people,ou=hwengg,dc=min,dc=io` user - Policies assigned to the `cn=projectb,ou=groups,ou=swengg,dc=min,dc=io` group

```shell
 mc admin idp ldap policy entities myminio/                                            \
                              --policy finteam-policy                                  \
                              --user 'uid=bobfisher,ou=people,ou=hwengg,dc=min,dc=io'  \
                              --group 'cn=projectb,ou=groups,ou=swengg,dc=min,dc=io'
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp ldap policy entities                \
                                ALIAS                          \
                                [--user `value`, -u `value`]   \
                                [--group `value`, -g `value`]  \
                                [--policy value]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for AD/LDAP integration.
- You may use each of the `--user`, `--group`, and/or `--policy` flags as many times as desired in the command.
- For each flag, the output lists the entities mapped to the specified policy, user, or group.
- Omit all flags to return a list of mappings for all policies.
{{< /tab >}}
{{< /tabs >}}

## Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

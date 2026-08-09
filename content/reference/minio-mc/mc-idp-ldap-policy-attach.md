---
title: "mc idp ldap policy attach"
url: "/reference/minio-mc/mc-idp-ldap-policy-attach/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-idp-ldap-policy-attach"></a>
<a id="minio-mc-idp-ldap-policy-attach"></a>

<a id="command-mc.idp.ldap.policy.attach"></a>

## Description {#description}

The [`mc idp ldap policy attach`](#command-mc.idp.ldap.policy.attach) command attaches one or more polices to an entity.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
> The following example attaches the policy `userpolicy` to the user `bobfisher` on the `myminio` deployment:

```shell
mc idp ldap policy attach myminio                                                  \
                          userpolicy                                               \
                          --user='uid=bobfisher,ou=people,ou=hwengg,dc=min,dc=io'
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap policy attach             \
                                 POLICYNAME         \
                                 [POLICY2] ...      \
                                 ALIAS              \
                                 [--user=`USER`]    \
                                 [--group=`GROUP`]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for AD/LDAP integration.
- Replace `POLICYNAME` with the policy to attach to the entity. You may list multiple policies to attach to the entity.
- Use must use one of either the `--user` or `--group` flag. You may only use the flag once in the command. You cannot use both flags in the same command.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.policy.attach.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment with the entity to which to attach a policy.

For example:

```text
mc idp ldap policy attach myminio                                                  \
                          userpolicy                                               \
                          --user='uid=bobfisher,ou=people,ou=hwengg,dc=min,dc=io'
```

### Example {#example}

The following example attaches two policies, `policy1` and `policy2`, to the `projectb` group on the `myminio` deployment:

```shell
mc idp ldap policy attach myminio                                                 \
                          policy1                                                 \
                          policy2                                                 \
                          --group='cn=projectb,ou=groups,ou=swengg,dc=min,dc=io'
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

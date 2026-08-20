---
title: "mc idp ldap policy detach"
url: "/reference/minio-mc/mc-idp-ldap-policy-detach/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-idp-ldap-policy-detach.rst
upstream_modified: false
---

<a id="mc-idp-ldap-policy-detach"></a>
<a id="minio-mc-idp-ldap-policy-detach"></a>

<a id="command-mc.idp.ldap.policy.detach"></a>

## Description {#description}

The [`mc idp ldap policy detach`](#command-mc.idp.ldap.policy.detach) command detaches one or more polices from an entity.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example detaches the policy `userpolicy` from the user `bobfisher` on the `myminio` deployment.

```shell
mc idp ldap policy detach myminio                                                  \
                          userpolicy                                               \
                          --user='uid=bobfisher,ou=people,ou=hwengg,dc=min,dc=io'
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap policy detach             \
                                 POLICYNAME         \
                                 [POLICY2] ...      \
                                 ALIAS              \
                                 [--user=`USER`]    \
                                 [--group=`GROUP`]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for AD/LDAP integration.
- Replace `POLICYNAME` with the policy to detach from the entity. You may list multiple policies to detach from the entity.
- Use must use one of either the `--user` or `--group` flag. You may only use the flag once in the command. You cannot use both flags in the same command.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.policy.detach.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment with the entity from which to detach a policy.

For example:

```text
mc idp ldap policy detach myminio                                                  \
                          userpolicy                                               \
                          --user='uid=bobfisher,ou=people,ou=hwengg,dc=min,dc=io'
```

### Example {#example}

The following example detaches two policies, `policy1` and `policy2`, from the `projectb` group on the `myminio` deployment:

```shell
mc idp ldap policy detach myminio                                                 \
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

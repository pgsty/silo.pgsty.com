---
title: "mc idp ldap policy entities"
url: "/reference/minio-mc/mc-idp-ldap-policy-entities/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="mc-idp-ldap-policy-entities"></a>
<a id="minio-mc-idp-ldap-policy-entities"></a>

<a id="command-mc.idp.ldap.policy.entities"></a>

## Description {#description}

The [`mc idp ldap policy entities`](#command-mc.idp.ldap.policy.entities) command displays a list of mappings for a user, group, and/or policy.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example lists all mappings for a specific policy, a set of groups, and a selection of users on the `myminio` deployment.

Specifically, it lists:

- Users mapped to the `finteam-policy` policy.
- Policies assigned to the `uid=bobfisher,ou=people,ou=hwengg,dc=min,dc=io` user.
- Policies assigned to the `cn=projectb,ou=groups,ou=swengg,dc=min,dc=io` group.

```shell
mc idp ldap policy entities myminio                                                  \
                            --policy finteam-policy                                  \
                            --user 'uid=bobfisher,ou=people,ou=hwengg,dc=min,dc=io'  \
                            --group 'cn=projectb,ou=groups,ou=swengg,dc=min,dc=io'
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap policy entities                       \
                                 ALIAS                          \
                                 [--group `value`, -g `value`]  \
                                 [--policy value]               \
                                 [--user `value`, -u `value`]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for AD/LDAP integration.
- You may use each of the `--user`, `--group`, and/or `--policy` flags as many times as desired in the command.
- For each flag, the output lists the entities mapped to the specified policy, user, or group.
- Omit all flags to return a list of mappings for all policies.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.policy.entities.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment for which to display the entity mappings.

For example:

```text
mc idp ldap policy entities myminio
```

##### `--group` {#mc.idp.ldap.policy.entities.-group}

*mc-cmd*

*Optional*

Returns a list of users and policies associated with the specified group. Repeat the flag to return a list for multiple groups.

##### `--policies` {#mc.idp.ldap.policy.entities.-policies}

*mc-cmd*

*Optional*

Returns a list of users and groups associated with the specified policy. Repeat the flag to return a list for multiple policies.

##### `--user` {#mc.idp.ldap.policy.entities.-user}

*mc-cmd*

*Optional*

Returns a list of groups to which the user belongs and the policies associated with each group. The output includes only groups assigned to policies.

Repeat the flag to return a list for multiple users.

### Example {#example}

The following example lists the entities mapped to each of two policies, `policy1` and `policy2` and entities mapped to the `projectb` group on the `myminio` deployment:

```shell
mc idp ldap policy entities myminio                                                 \
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

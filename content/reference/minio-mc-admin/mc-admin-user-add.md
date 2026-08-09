---
title: "mc admin user add"
url: "/reference/minio-mc-admin/mc-admin-user-add/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-admin-user-add"></a>
<a id="minio-mc-admin-user-add"></a>

<a id="command-mc.admin.user.add"></a>

## Syntax {#syntax}

The [`mc admin user add`](#command-mc.admin.user.add) command adds a new [MinIO user](/administration/identity-access-management/minio-identity-management/#minio-internal-idp) to the target MinIO deployment.

To manage external Identity Provider users, see [`OIDC`](/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid) or [`AD/LDAP`](/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command creates a new user `newuser` on the `myminio` MinIO deployment:

```shell
mc admin user add myminio newuser newusersecret
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user add        \
                            ALIAS      \
                            ACCESSKEY  \
                            SECRETKEY
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ACCESSKEY` {#mc.admin.user.add.ACCESSKEY}

*mc-cmd*

*Required*

The access key that uniquely identifies the new user, similar to a username.

##### `ALIAS` {#mc.admin.user.add.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment on which to create the new user.

##### `SECRETKEY` {#mc.admin.user.add.SECRETKEY}

*mc-cmd*

*Required*

The secret key for the new user. Consider the following guidance when creating a secret key:

- The key should be *unique*
- The key should be *long* (Greater than 12 characters)
- The key should be *complex* (A mixture of characters, numerals, and symbols)

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Create a New User {#create-a-new-user}

Use [`mc admin user add`](#command-mc.admin.user.add) to create a user on a MinIO deployment:

```shell
   mc admin user add ALIAS ACCESSKEY SECRETKEY
```

- Replace [`ALIAS`](#mc.admin.user.add.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`ACCESSKEY`](#mc.admin.user.add.ACCESSKEY) with the access key for the user.
- Replace [`SECRETKEY`](#mc.admin.user.add.SECRETKEY) with the secret key for the user. MinIO *does not* provide any method for retrieving the secret key once set.

Specify a unique, random, and long string for both the `ACCESSKEY` and `SECRETKEY`. Your organization may have specific internal or regulatory requirements around generating values for use with access or secret keys.

## Behavior {#behavior}

### New Users Have No Default Policies {#new-users-have-no-default-policies}

Newly created users have *no* policies by default and therefore cannot perform any operations on the MinIO deployment. To configure a user’s assigned policies, you can do either or both of the following:

- Use [`mc admin policy attach`](/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach) to associate one or more policies to the user.
- Use [`mc admin group add`](/reference/minio-mc-admin/mc-admin-group/#mc.admin.group.add) to associate the user to the group. Users inherit any policies assigned to the group.

For more information on MinIO users and groups, see [User Management](/administration/identity-access-management/minio-user-management/#minio-users) and [Group Management](/administration/identity-access-management/minio-group-management/#minio-groups). For more information on MinIO policies, see [MinIO Policy Based Access Control](/administration/identity-access-management/policy-based-access-control/#minio-policy).

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

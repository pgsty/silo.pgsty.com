---
title: "mc admin accesskey ls"
url: "/reference/minio-mc-admin/mc-admin-accesskey-list/"
weight: 60
minio_origin: true
silo_modified: false
---

<a id="mc-admin-accesskey-ls"></a>
<a id="minio-mc-admin-accesskey-list"></a>

<a id="command-mc.admin.accesskey.list"></a>

<a id="command-mc.admin.accesskey.ls"></a>

## Syntax {#syntax}

The [`mc admin accesskey ls`](#command-mc.admin.accesskey.ls) command lists users, access keys, or temporary [security token service](/developers/security-token-service/#minio-security-token-service) keys managed by the MinIO deployment.

The alias [`mc admin accesskey list`](#command-mc.admin.accesskey.list) has equivalent functionality to [`mc admin accesskey ls`](#command-mc.admin.accesskey.ls).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command lists all access keys associated to the user with username `admin1` on the deployment at alias `myminio`:

```shell
mc admin accesskey ls myminio admin1
```

The output resembles the following:

```shell
   Access Key        | Expiry
5XF3ZHNZK6FBDWH9JMLX | 2023-06-24 07:00:00 +0000 UTC
F4V2BBUZSWY7UG96ED70 | 2023-12-24 18:00:00 +0000 UTC
FZVSEZ8NM9JRBEQZ7B8Q | no-expiry
HOXGL8ON3RG0IKYCHCUD | no-expiry
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin accesskey ls             \
                                 ALIAS          \
                                 [USER]         \
                                 [--all]        \
                                 [--self]       \
                                 [--temp-only]  \
                                 [--users-only]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.accesskey.ls.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `USER` {#mc.admin.accesskey.ls.USER}

*mc-cmd*

*Optional*

The username of the user(s) to display access keys for. Separate multiple usernames with a space.

##### `--all` {#mc.admin.accesskey.ls.-all}

*mc-cmd*

*Optional*

List all users and any access keys or temporary STS keys associated with them. Requires admin privileges for the deployment.

This flag is mutually exclusive with the other flags available for this command.

##### `--svcacc-only` {#mc.admin.accesskey.ls.-svcacc-only}

*mc-cmd*

*Optional*

List temporary [Security Token Service (STS) keys](/developers/security-token-service/#minio-security-token-service) on the deployment.

This flag is mutually exclusive with the other flags available for this command.

##### `--self` {#mc.admin.accesskey.ls.-self}

*mc-cmd*

*Optional*

List access keys and STS keys for the currently authenticated user.

This flag is mutually exclusive with the other flags available for this command.

##### `--temp-only` {#mc.admin.accesskey.ls.-temp-only}

*mc-cmd*

*Optional*

List users with their access keys. This returns only users that have associated access keys.

This flag requires admin privileges for the user running the command.

This flag is mutually exclusive with the other flags available for this command.

##### `--users-only` {#mc.admin.accesskey.ls.-users-only}

*mc-cmd*

*Optional*

List the MinIO users managed by the deployment. Use in conjunction with the [`--all`](#mc.admin.accesskey.ls.-all) flag to list all users on the deployment.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### List all built-in users and associated access keys {#list-all-built-in-users-and-associated-access-keys}

The following command lists all users managed by the MinIO deployment at alias `myminio` and any associated access keys or temporary STS tokens.

```shell
mc admin accesskey list myminio/ --all
```

### Return a list of access keys for the current authenticated user {#return-a-list-of-access-keys-for-the-current-authenticated-user}

The following command lists the access keys or temporary STS tokens associated with the currently authenticated user for the `myminio` deployment.

```shell
mc admin accesskey list myminio/ --self
```

### List all users created and managed by the deployment {#list-all-users-created-and-managed-by-the-deployment}

The following command returns a list of all of the users on the current deployment. The list only includes MinIO IDP managed users, not users managed by a third party tool on a protocol like OpenID or Active Directory/LDAP.

```shell
mc admin accesskey ls myminio/ --all --users-only
```

### Return a list of access keys associated with the users `miniouser1` and `miniouser2` {#return-a-list-of-access-keys-associated-with-the-users-miniouser1-and-miniouser2}

The following command returns a list of access keys for two users on the `myminio` deployment.

```shell
mc admin accesskey ls myminio/ miniouser1 miniouser2
```

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

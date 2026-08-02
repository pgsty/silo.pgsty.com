---
title: "mc idp ldap accesskey ls"
url: "/reference/minio-mc/mc-idp-ldap-accesskey-ls/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="mc-idp-ldap-accesskey-ls"></a>
<a id="minio-mc-idp-ldap-accesskey-ls"></a>

<a id="command-mc.idp.ldap.accesskey.list"></a>

<a id="command-mc.idp.ldap.accesskey.ls"></a>

## Description {#description}

The [`mc idp ldap accesskey ls`](#command-mc.idp.ldap.accesskey.ls) displays a list of LDAP access key pairs.

[`mc idp ldap accesskey ls`](#command-mc.idp.ldap.accesskey.ls) is also known as [`mc idp ldap accesskey list`](#command-mc.idp.ldap.accesskey.list).

This command works against [access keys](/administration/identity-access-management/minio-user-management/#minio-id-access-keys) created by an AD/LDAP user after authenticating to MinIO.

Create AD/LDAP service accounts with the [`mc idp ldap accesskey create`](/reference/minio-mc/mc-idp-ldap-accesskey-create/#command-mc.idp.ldap.accesskey.create) command.

MinIO supports using [AssumeRoleWithLDAPIdentity](/developers/security-token-service/AssumeRoleWithLDAPIdentity/#minio-sts-assumerolewithldapidentity) to generate temporary access keys using the [Security Token Service](/developers/security-token-service/#minio-security-token-service).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
> The following example returns a list of access keys associated with the authenticated user on the `minio` [alias](/reference/minio-mc/mc-alias-set/#alias):

```shell
mc idp ldap accesskey ls minio/
```

If the authenticated user has the `admin:ListUsers` permission, the example command returns a list of all users and their associated access keys.
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap accesskey ls           \
                                 ALIAS           \
                                 [--all]         \
                                 [--self]        \
                                 [--svcacc-only] \
                                 [--temp-only]   \
                                 [--users-only]  \
                                 [DN] ...
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment configured for AD/LDAP integration.
- Replace `DN` with the string of a user’s [distinguished name](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ldap/distinguished-names). You may list multiple distinguished names by separating each with a space.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.accesskey.ls.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment configured for AD/LDAP.

For example:

```text
mc idp ldap accesskey ls minio
```

##### `--all` {#mc.idp.ldap.accesskey.ls.-all}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: mc**

RELEASE.2024-07-31T15-58-33Z
{{% /alert %}}

List all access keys for all LDAP users.

##### `--self` {#mc.idp.ldap.accesskey.ls.-self}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: mc**

RELEASE.2024-07-31T15-58-33Z
{{% /alert %}}

List access keys for the currently authenticated user.

##### `--svcacc-only` {#mc.idp.ldap.accesskey.ls.-svcacc-only}

*mc-cmd*

*Optional*

Output only service account access keys.

Mutually exclusive with [`--temp-only`](#mc.idp.ldap.accesskey.ls.-temp-only).

##### `--temp-only` {#mc.idp.ldap.accesskey.ls.-temp-only}

*mc-cmd*

*Optional*

Output only temporary access keys.

Mutually exclusive with [`--svcacc-only`](#mc.idp.ldap.accesskey.ls.-svcacc-only).

##### `--users-only` {#mc.idp.ldap.accesskey.ls.-users-only}

*mc-cmd*

*Optional*

Output only the user distinguished names.

### Examples {#examples}

#### List All Access Keys {#list-all-access-keys}

To return a list of all access keys, you must first authenticate as the `admin` user. Once authenticated, the following command returns all AD/LDAP access keys on the `minio` deployment.

```shell
mc idp ldap accesskey ls minio
```

{{% alert color="info" %}}
**Note**

If the user does not have the `admin:ListUsers` permission, the command returns a list of access keys for the authenticated user only.
{{% /alert %}}

#### List User Distinguished Names {#list-user-distinguished-names}

To return a list of DNs for a deployment, you must first authenticate as a user with the `admin:ListUsers` permission. Once authenticated, the following command outputs the AD/LDAP distinguished names on the `minio` deployment.

```shell
mc idp ldap accesskey ls minio --users-only
```

#### List Temporary Access Keys {#list-temporary-access-keys}

To return a list of all temporary access keys for a deployment, you must first authenticate as a user with the `admin:ListUsers` permission. Once authenticated, the following command outputs a list of distinguished names with their associated temporary access keys.

```shell
mc idp ldap accesskey ls minio --temp-only
```

#### List a User’s Access Keys {#list-a-user-s-access-keys}

The following command returns the AD/LDAP access keys for the user `bobfisher` on the `minio` deployment.

```shell
mc idp ldap accesskey list minio/ uid=bobfisher,dc=min,dc=io
```

#### List Access Keys for Multiple Users {#list-access-keys-for-multiple-users}

The following command returns the AD/LDAP access keys for the users `bobfisher` and `cody3` on the `minio` deployment.

```shell
mc idp ldap accesskey list minio/ uid=bobfisher,dc=min,dc=io uid=cody3,dc=min,dc=io
```

#### List Access Keys for Authenticated User {#list-access-keys-for-authenticated-user}

The following command returns the AD/LDAP access keys for the currently authenticated user on the `minio` deployment.

```shell
mc idp ldap accesskey list minio/
```

{{% alert color="info" %}}
**Note**

If the authenticated user has the `admin:ListUsers` permission, the command returns a list of all users and access keys on the deployment.
{{% /alert %}}

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

---
title: "mc admin accesskey create"
url: "/reference/minio-mc-admin/mc-admin-accesskey-create/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-accesskey-create.rst
upstream_modified: false
---

<a id="mc-admin-accesskey-create"></a>
<a id="minio-mc-admin-accesskey-create"></a>

<a id="command-mc.admin.accesskey.create"></a>

## Syntax {#syntax}

The [`mc admin accesskey create`](#command-mc.admin.accesskey.create) command adds a new access key and secret key pair for an existing MinIO user.

> [!NOTE]
> **Access keys for OpenID Connect or AD/LDAP users**
>
> This command is for access keys for users created directly on the MinIO deployment and not managed by a third party solution.
>
> To generate access keys for [Active Directory/LDAP users](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap), use [`mc idp ldap accesskey create`](/reference/minio-mc/mc-idp-ldap-accesskey-create/#command-mc.idp.ldap.accesskey.create).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command creates a new access key associated to an existing MinIO user:

```shell
mc admin accesskey create        \
   myminio/ myuser               \
   --access-key myuseraccesskey  \
   --secret-key myusersecretkey  \
   --policy /path/to/policy.json
```

The command returns the access key and secret key for the new account.
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin accesskey create                    \
                                 ALIAS                     \
                                 [USER]                    \
                                 [--access-key string]     \
                                 [--secret-key string]     \
                                 [--policy path]           \
                                 [--name string]           \
                                 [--description string]    \
                                 [--expiry-duration value] \
                                 [--expiry date]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.accesskey.create.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `USER` {#mc.admin.accesskey.create.USER}

*mc-cmd*

*Optional*

The username of the user to which MinIO adds the new access key. If not specified, MinIO generates an access key/secret key pair for the authenticated user.

##### `--access-key` {#mc.admin.accesskey.create.-access-key}

*mc-cmd*

*Optional*

A string to use as the access key for this account. Omit to let MinIO autogenerate a random 20 character value.

Access Key names *must* be unique across all users.

##### `--description` {#mc.admin.accesskey.create.-description}

*mc-cmd*

*Optional*

Add a description for the access key. For example, you might specify the reason the access key exists.

##### `--expiry` {#mc.admin.accesskey.create.-expiry}

*mc-cmd*

*Optional*

Set an expiration date for the access key. The date must be in the future. You may not set an expiration date that has already passed.

Allowed date and time formats:

- `2024-10-24`
- `2024-10-24T10:00`
- `2024-10-24T10:00:00`
- `2024-10-24T10:00:00Z`
- `2024-10-24T10:00:00-07:00`

Mutually exclusive with [`--expiry-duration`](#mc.admin.accesskey.create.-expiry-duration).

##### `--expiry-duration` {#mc.admin.accesskey.create.-expiry-duration}

*mc-cmd*

*Optional*

Length of time for which the accesskey remains valid. Valid time units are “ns”, “us” (or “µs”), “ms”, “s”, “m”, “h”.

The following expires the credentials after 30 days:

```text
--expiry-duration 720h
```

Mutually exclusive with [`--expiry`](#mc.admin.accesskey.create.-expiry).

##### `--name` {#mc.admin.accesskey.create.-name}

*mc-cmd*

*Optional*

Add a human-readable name for the access key.

##### `--policy` {#mc.admin.accesskey.create.-policy}

*mc-cmd*

*Optional*

The readable path to a [policy document](/administration/identity-access-management/policy-based-access-control/#minio-policy) to attach to the new access key, with a maximum size of 2048 characters. The attached policy cannot grant access to any action or resource not explicitly allowed by the parent user’s policy or group policies

##### `--secret-key` {#mc.admin.accesskey.create.-secret-key}

*mc-cmd*

*Optional*

The secret key to associate with the new account. Omit to let MinIO autogenerate a random 40-character value.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Create access key / secret key pair for the authenticated user {#create-access-key-secret-key-pair-for-the-authenticated-user}

The following command generates a new, random access key and secret key pair for the user currently logged in to MinIO deployment at the alias `myminio`. The access key and secret key have the same access policies as the authenticated user.

```shell
mc admin accesskey create myminio/
```

### Create a custom access key / secret key pair for the authenticated user {#create-a-custom-access-key-secret-key-pair-for-the-authenticated-user}

The following command creates a new access key and secret key pair for the user currently logged in to MinIO at the alias `myminio`. The access key and secret key have the same access policies as the authenticated user.

```shell
mc admin accesskey create myminio/ --access-key myaccesskey --secret-key mysecretkey
```

### Create an access key / secret key pair for another user with limited duration {#create-an-access-key-secret-key-pair-for-another-user-with-limited-duration}

The following command creates a new access key and secret key pair for a user, `miniouser` on the alias `myminio`. The access key and secret key have the same access policies as `miniouser`. The credentials remain valid for 24 hours after creation.

```shell
mc admin accesskey create myminio/ miniouser --expiry-duration 24h
```

### Create access key / secret key pair for the authenticated user that expires {#create-access-key-secret-key-pair-for-the-authenticated-user-that-expires}

The following command generates a new and random access key and random secret key pair for the user currently logged in to MinIO deployment at the alias `myminio`. The access key and secret key have the same access policies as the authenticated user. The credentials expire on the fifteenth day of January, 2025.

```shell
mc admin accesskey create myminio/ --expiry 2025-01-15
```

The date specified **must** be a future date. For valid datetime formats, see the [`--expiry`](#mc.admin.accesskey.create.-expiry) flag.

### Create access key / secret key pair for a different user with custom access {#create-access-key-secret-key-pair-for-a-different-user-with-custom-access}

The following command creates a new access key and secret key pair for the user, `miniouser` on the alias `myminio`. The access key and secret key have a more limited set of access than `miniouser`, as specified in the policy JSON file.

```shell
mc admin accesskey create myminio/ miniouser --policy /path/to/policy.json
```

The specified policy file **must not** grant access to anything to which `miniouser` does not already have access.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

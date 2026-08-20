---
title: "mc admin user accesskey edit"
url: "/reference/minio-mc-admin/mc-admin-accesskey-edit/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-accesskey-edit.rst
upstream_modified: false
---

<a id="mc-admin-user-accesskey-edit"></a>
<a id="minio-mc-admin-accesskey-edit"></a>

<a id="command-mc.admin.accesskey.edit"></a>

## Syntax {#syntax}

The [`mc admin accesskey edit`](#command-mc.admin.accesskey.edit) command modifies the configuration of an access key associated to the specified user.

The command requires that at least one attribute of the access key change. Otherwise, the command exits with an error message.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command applies a new policy and secret key to the `myuserserviceaccount` access key on the `myminio` deployment:

```shell
mc admin accesskey edit                                             \
                   myminio myuserserviceaccount                     \
                   --secret-key "myuserserviceaccountnewsecretkey"  \
                   --policy "/path/to/new/policy.json"
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin accesskey edit                      \
                                 ALIAS                     \
                                 ACCESSKEY                 \
                                 [--description string]    \
                                 [--expiry-duration value] \
                                 [--expiry value]          \
                                 [--name string]           \
                                 [--policy path]           \
                                 [--secret-key string]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.accesskey.edit.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `ACCESSKEY` {#mc.admin.accesskey.edit.ACCESSKEY}

*mc-cmd*

*Required*

The access key to modify.

##### `--description` {#mc.admin.accesskey.edit.-description}

*mc-cmd*

*Optional*

Add or modify a description for the access key. For example, you might specify the reason the access key exists.

##### `--expiry` {#mc.admin.accesskey.edit.-expiry}

*mc-cmd*

*Optional*

Set or modify an expiration date for the access key. The date must be in the future, you may not set an expiration date that has already passed.

Allowed date and time formats:

- `2023-06-24`
- `2023-06-24T10:00`
- `2023-06-24T10:00:00`
- `2023-06-24T10:00:00Z`
- `2023-06-24T10:00:00-07:00`

Mutually exclusive with [`--expiry-duration`](#mc.admin.accesskey.edit.-expiry-duration).

##### `--expiry-duration` {#mc.admin.accesskey.edit.-expiry-duration}

*mc-cmd*

*Optional*

Length of time for which the accesskey remains valid. Valid time units are “ns”, “us” (or “µs”), “ms”, “s”, “m”, “h”.

To expire the credentials after 30 days, use:

```text
--expiry-duration 720h
```

Mutually exclusive with [`--expiry`](#mc.admin.accesskey.edit.-expiry).

##### `--name` {#mc.admin.accesskey.edit.-name}

*mc-cmd*

*Optional*

Add or modify a human-readable name for the access key.

##### `--policy` {#mc.admin.accesskey.edit.-policy}

*mc-cmd*

*Optional*

The path to a [policy document](/administration/identity-access-management/policy-based-access-control/#minio-policy) to attach to the new access key, with a maximum size of 2048 characters. The attached policy cannot grant access to any action or resource not explicitly allowed by the parent user’s policies.

The new policy overwrites any previously attached policy.

##### `--secret-key` {#mc.admin.accesskey.edit.-secret-key}

*mc-cmd*

*Optional*

The secret key to associate with the new access key. Overwrites the previous secret key. Applications using the access keys *must* update to use the new credentials to continue performing operations.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Change the secret key for an access key {#change-the-secret-key-for-an-access-key}

The following command modifies the secret key for the access key `myuseraccesskey` on the `myminio` deployment.

```shell
mc admin accesskey edit myminio/ myuseraccesskey --secret-key 'new-secret-key-change-me'
```

### Change the expiration for an access key {#change-the-expiration-for-an-access-key}

The following command changes the expiration value for the access key `myuseraccesskey` on the `myminio` deployment.

```shell
mc admin accesskey edit myminio/ myuseraccesskey --expiry-duration 24h
```

The [`--expiry-duration`](#mc.admin.accesskey.edit.-expiry-duration) cannot be added if the access key already has a value set for [`--expiry`](#mc.admin.accesskey.edit.-expiry).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

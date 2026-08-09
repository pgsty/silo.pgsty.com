---
title: "mc idp ldap accesskey edit"
url: "/reference/minio-mc/mc-idp-ldap-accesskey-edit/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="mc-idp-ldap-accesskey-edit"></a>
<a id="minio-mc-idp-ldap-accesskey-edit"></a>

<a id="command-mc.idp.ldap.accesskey.edit"></a>

## Description {#description}

[`mc idp ldap accesskey edit`](#command-mc.idp.ldap.accesskey.edit) modifies the specified [access key](/administration/identity-access-management/minio-user-management/#minio-id-access-keys) on the local server.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
> The following example modifies the secret for the access key `mykey` on the `minio` deployment:

```shell
mc idp ldap accesskey edit myminio/ mykey --secret-key 'xxxxxxx'
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap accesskey rm                        \
                                 ALIAS                        \
                                 KEY                          \
                                 [--secret-key <string>]      \
                                 [--policy <string>]          \
                                 [--name <string>]            \
                                 [--description <string>]     \
                                 [--expiry-duration <string>] \
                                 [--expiry <string>]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment configured for AD/LDAP integration.
- Replace `KEY` with the access key to delete.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.accesskey.edit.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment configured for AD/LDAP.

For example:

```text
mc idp ldap accesskey ls minio
```

##### `KEY` {#mc.idp.ldap.accesskey.edit.KEY}

*mc-cmd*

*Required*

The configured access key to delete.

##### `--description` {#mc.idp.ldap.accesskey.edit.-description}

*mc-cmd*

*Optional*

Add a description for the service account. For example, you might specify the reason the access key exists.

##### `--expiry` {#mc.idp.ldap.accesskey.edit.-expiry}

*mc-cmd*

*Optional*

The date after which the access key expires. Enter the date in YYYY-MM-DD format.

For example, to expire the credentials after December 31, 2024, enter `2024-12-31`.

Mutually exclusive with [`--expiry-duration`](#mc.idp.ldap.accesskey.edit.-expiry-duration).

##### `--expiry-duration` {#mc.idp.ldap.accesskey.edit.-expiry-duration}

*mc-cmd*

*Optional*

Length of time the access key pair should remain valid for use in `#d#h#s` format.

For example, `7d`, `24h`, `5d12h30s` are valid strings.

Mutually exclusive with [`--expiry`](#mc.idp.ldap.accesskey.edit.-expiry).

##### `--name` {#mc.idp.ldap.accesskey.edit.-name}

*mc-cmd*

*Optional*

A human-readable name to use for the account.

##### `--policy` {#mc.idp.ldap.accesskey.edit.-policy}

*mc-cmd*

*Optional*

File path to the JSON-formatted policy to use for the account.

If not specified, the account uses the same policy as the authenticated user.

##### `--secret-key` {#mc.idp.ldap.accesskey.edit.-secret-key}

*mc-cmd*

*Optional*

A secret to use for the account.

### Example {#example}

#### Modify a secret for an access key {#modify-a-secret-for-an-access-key}

Modify the secret for the access key `mykey` on the `minio` deployment.

```shell
mc idp ldap accesskey edit myminio/ mykey --secret-key 'xxxxxxx'
```

#### Modify the expiration duration for an accesskey {#modify-the-expiration-duration-for-an-accesskey}

Modify the expiration duration for the access key `mykey` on the `minio` deployment.

```shell
mc idp ldap accesskey edit myminio/ mykey ---expiry-duration 24h
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

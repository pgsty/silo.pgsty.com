---
title: "mc idp ldap accesskey create"
url: "/reference/minio-mc/mc-idp-ldap-accesskey-create/"
weight: 9262
toc_hide: true
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-idp-ldap-accesskey-create.rst
upstream_modified: false
---

<a id="mc-idp-ldap-accesskey-create"></a>
<a id="minio-mc-idp-ldap-accesskey-create"></a>

<a id="command-mc.idp.ldap.accesskey.create"></a>

> [!NOTE]
> **Added: mc**
>
> RELEASE.2023-12-23T08-47-21Z

## Description {#description}

The [`mc idp ldap accesskey create`](#command-mc.idp.ldap.accesskey.create) allows you to add LDAP access key pairs.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
> The following example creates a new access key pair with the same policy as the authenticated user on the `minio` [alias](/reference/minio-mc/mc-alias-set/#alias):

```shell
mc idp ldap accesskey create minio/
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap accesskey create                   \
                                 ALIAS                       \
                                 [--access-key <value>]      \
                                 [--secret-key <value>]      \
                                 [--policy <value>]          \
                                 [--name <value>]            \
                                 [--description <value>]     \
                                 [--expiry <value>]          \
                                 [--expiry-duration <value>]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment configured for AD/LDAP integration.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.accesskey.create.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment configured for AD/LDAP.

For example:

```text
mc idp ldap accesskey create minio
```

##### `--access-key` {#mc.idp.ldap.accesskey.create.-access-key}

*mc-cmd*

*Optional*

An access key to use for the account. The access key cannot contain the characters `=` (equal sign) or `,` (comma).

Requires [`--secret-key`](#mc.idp.ldap.accesskey.create.-secret-key)

##### `--secret-key` {#mc.idp.ldap.accesskey.create.-secret-key}

*mc-cmd*

*Optional*

A secret to use for the account.

Requires [`--access-key`](#mc.idp.ldap.accesskey.create.-access-key)

##### `--policy` {#mc.idp.ldap.accesskey.create.-policy}

*mc-cmd*

*Optional*

File path to the JSON-formatted policy to use for the account.

If not specified, the account uses the same policy as the authenticated user.

##### `--name` {#mc.idp.ldap.accesskey.create.-name}

*mc-cmd*

*Optional*

A human-readable name to use for the account.

##### `--description` {#mc.idp.ldap.accesskey.create.-description}

*mc-cmd*

*Optional*

Add a description for the service account. For example, you might specify the reason the access key exists.

##### `--expiry-duration` {#mc.idp.ldap.accesskey.create.-expiry-duration}

*mc-cmd*

*Optional*

Length of time the access key pair should remain valid for use in `#d#h#s` format.

For example, `7d`, `24h`, `5d12h30s` are valid strings.

Mutually exclusive with [`--expiry`](#mc.idp.ldap.accesskey.create.-expiry).

##### `--expiry` {#mc.idp.ldap.accesskey.create.-expiry}

*mc-cmd*

*Optional*

The date after which the access key expires. Enter the date in YYYY-MM-DD format.

For example, to expire the credentials after December 31, 2024, enter `2024-12-31`.

Mutually exclusive with [`--expiry-duration`](#mc.idp.ldap.accesskey.create.-expiry-duration).

##### `--login` {#mc.idp.ldap.accesskey.create.-login}

*mc-cmd*

*Optional*

> [!CAUTION]
> **Deprecated: RELEASE.2024-04-18T16-45-29Z**
>
> Use [`mc idp ldap accesskey create-with-login`](/reference/minio-mc/mc-idp-ldap-accesskey-create-with-login/#command-mc.idp.ldap.accesskey.create-with-login) to access the functionality previously provided by this parameter.

Prompts the user to log in using the LDAP credentials to use to generate the access key. Specify the URL of the LDAP-configured MinIO Server to use for the login prompt.

Requires an interactive terminal.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

## Examples {#examples}

### Create a new access-key pair for the authenticated user {#create-a-new-access-key-pair-for-the-authenticated-user}

The following command creates a new access key pair to use with the currently authenticated user on the `minio` alias. The command outputs a randomly generated access key and secret key.

```shell
mc idp ldap accesskey create minio
```

### Create a new access-key pair with a custom access key and secret key {#create-a-new-access-key-pair-with-a-custom-access-key-and-secret-key}

The following command creates a new access key pair with both an access key and secret key that you specify for the user currently authenticated on the `minio` alias.

```shell
mc idp ldap accesskey create minio/ --access-key my-access-key-change-me --secret-key my-secret-key-change-me
```

### Create a new access-key pair that expires after 24 hours {#create-a-new-access-key-pair-that-expires-after-24-hours}

The following command creates a new access key pair to use with the currently authenticated user on the `minio` alias. The credentials expire after 24 hours.

The command outputs a randomly generated access key and secret key.

```shell
mc idp ldap accesskey create minio --expiry-duration 24h
```

### Create a new access-key and prompt to login as the user {#create-a-new-access-key-and-prompt-to-login-as-the-user}

The following command creates a new access key pair. The MinIO Client will first ask you to log in as the user the access key is for on the MinIO site configured for LDAP at `minio.example.com`.

The command outputs a randomly generated access key and secret key.

```shell
mc idp ldap accesskey create minio --login minio.example.com
```

### Create a new access-key pair that expires after a date {#create-a-new-access-key-pair-that-expires-after-a-date}

The following command creates a new access key pair to use with the currently authenticated user on the `minio` alias. The credentials expire after February 29, 2024.

The command outputs a randomly generated access key and secret key.

```shell
mc idp ldap accesskey create minio --expiry 2024-02-29
```

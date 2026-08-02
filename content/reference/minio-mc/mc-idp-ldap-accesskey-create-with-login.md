---
title: "mc idp ldap accesskey create-with-login"
url: "/reference/minio-mc/mc-idp-ldap-accesskey-create-with-login/"
weight: 160
minio_origin: true
silo_modified: false
---

<a id="mc-idp-ldap-accesskey-create-with-login"></a>
<a id="minio-mc-idp-ldap-accesskey-create-with-login"></a>

<a id="command-mc.idp.ldap.accesskey.create-with-login"></a>

{{% alert color="info" %}}
**Added: mc**

RELEASE.2024-04-18T16-45-29Z
{{% /alert %}}

## Description {#description}

The [`mc idp ldap accesskey create-with-login`](#command-mc.idp.ldap.accesskey.create-with-login) uses interactive terminal-based prompt to authenticate with the external AD/LDAP server and generate access keys for use with MinIO.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
> The following example prompts the user to provide their AD/LDAP credentials. It then generates a new access key pair using the policy or policies associated with that AD/LDAP user.

```shell
mc idp ldap accesskey create-with-login https://minio.example.net/
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap accesskey create-with-login        \
                                 URL                         \
                                 [--access-key <value>]      \
                                 [--secret-key <value>]      \
                                 [--policy <value>]          \
                                 [--name <value>]            \
                                 [--description <value>]     \
                                 [--expiry <value>]          \
                                 [--expiry-duration <value>]
```

- Replace `URL` with the <abbr title="Fully Qualified Domain Name">FQDN</abbr> of a MinIO deployment configured for AD/LDAP integration.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `URL` {#mc.idp.ldap.accesskey.create-with-login.URL}

*mc-cmd*

*Required*

The <abbr title="Fully Qualified Domain Name">FQDN</abbr> of a MinIO deployment configured for AD/LDAP integration.

For example:

```text
mc idp ldap accesskey create-with-login https://minio.example.net
```

##### `--access-key` {#mc.idp.ldap.accesskey.create-with-login.-access-key}

*mc-cmd*

*Optional*

The access key to use once successfully authenticated. Omit to let MinIO randomly generate a value.

The access key cannot contain the characters `=` (equal sign) or `,` (comma).

Requires [`--secret-key`](#mc.idp.ldap.accesskey.create-with-login.-secret-key)

##### `--secret-key` {#mc.idp.ldap.accesskey.create-with-login.-secret-key}

*mc-cmd*

*Optional*

A secret key to use once successfully authenticated. Omit to let MinIO randomly generate a value.

Requires [`--access-key`](#mc.idp.ldap.accesskey.create-with-login.-access-key)

##### `--policy` {#mc.idp.ldap.accesskey.create-with-login.-policy}

*mc-cmd*

*Optional*

File path to the JSON-formatted [policy](/administration/identity-access-management/policy-based-access-control/#minio-policy) to use for the account. This policy _cannot_ grant additional privileges beyond the privileges associated with the authenticated AD/LDAP user.

Omit to use the AD/LDAP user policies.

##### `--name` {#mc.idp.ldap.accesskey.create-with-login.-name}

*mc-cmd*

*Optional*

A human-readable name to use for the created access key.

##### `--description` {#mc.idp.ldap.accesskey.create-with-login.-description}

*mc-cmd*

*Optional*

Create a description for the service account. For example, you might specify the reason the access key exists.

##### `--expiry-duration` {#mc.idp.ldap.accesskey.create-with-login.-expiry-duration}

*mc-cmd*

*Optional*

Length of time the access key pair should remain valid for use in `#d#h#s` format.

For example, `7d`, `24h`, `5d12h30s` are valid strings.

Mutually exclusive with [`--expiry`](#mc.idp.ldap.accesskey.create-with-login.-expiry).

##### `--expiry` {#mc.idp.ldap.accesskey.create-with-login.-expiry}

*mc-cmd*

*Optional*

The date after which the access key expires. Enter the date in `YYYY-MM-DD` format.

For example, to expire the credentials after December 31, 2024, enter `2024-12-31`.

Mutually exclusive with [`--expiry-duration`](#mc.idp.ldap.accesskey.create-with-login.-expiry-duration).

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
mc idp ldap accesskey create-with-login https://minio.example.net
```

### Create a new access-key pair with a custom access key and secret key {#create-a-new-access-key-pair-with-a-custom-access-key-and-secret-key}

The following command creates a new access key pair with both an access key and secret key that you specify for the user currently authenticated on the `minio` alias.

```shell
mc idp ldap accesskey create-with-login https://minio.example.net/ --access-key my-access-key-change-me --secret-key my-secret-key-change-me
```

### Create a new access-key pair that expires after 24 hours {#create-a-new-access-key-pair-that-expires-after-24-hours}

The following command creates a new access key pair to use with the currently authenticated user on the `minio` alias. The credentials expire after 24 hours.

The command outputs a randomly generated access key and secret key.

```shell
mc idp ldap accesskey create-with-login https://minio.example.net --expiry-duration 24h
```

### Create a new access-key pair that expires after a date {#create-a-new-access-key-pair-that-expires-after-a-date}

The following command creates a new access key pair to use with the currently authenticated user on the `minio` alias. The credentials expire after February 28, 2025.

The command outputs a randomly generated access key and secret key.

```shell
mc idp ldap accesskey create-with-login https://minio.example.net --expiry 2025-02-28
```

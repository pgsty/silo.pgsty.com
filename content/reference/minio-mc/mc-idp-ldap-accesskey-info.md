---
title: "mc idp ldap accesskey info"
url: "/reference/minio-mc/mc-idp-ldap-accesskey-info/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-idp-ldap-accesskey-info.rst
upstream_modified: false
---

<a id="mc-idp-ldap-accesskey-info"></a>
<a id="minio-mc-idp-ldap-accesskey-info"></a>

<a id="command-mc.idp.ldap.accesskey.info"></a>

## Description {#description}

The [`mc idp ldap accesskey info`](#command-mc.idp.ldap.accesskey.info) outputs information about the specified access key(s).

This command works against [access keys](/administration/identity-access-management/minio-user-management/#minio-id-access-keys) created by an AD/LDAP user after authenticating to MinIO.

Create AD/LDAP service accounts with the [`mc idp ldap accesskey create`](/reference/minio-mc/mc-idp-ldap-accesskey-create/#command-mc.idp.ldap.accesskey.create) command.

MinIO supports using [AssumeRoleWithLDAPIdentity](/developers/security-token-service/AssumeRoleWithLDAPIdentity/#minio-sts-assumerolewithldapidentity) to generate temporary access keys using the [Security Token Service](/developers/security-token-service/#minio-security-token-service).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
> The following example outputs details for the access key `mykey` from the `minio` deployment:

```shell
mc idp ldap accesskey info minio/ mykey
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap accesskey info      \
                                    ALIAS     \
                                    KEY       \
                                    [KEY2] ...
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment configured for AD/LDAP integration.
- Replace `KEY` with the access key to delete. You can list more than one access key by separating each key with a space.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.accesskey.info.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment configured for AD/LDAP.

For example:

```text
mc idp ldap accesskey ls minio
```

##### `KEY` {#mc.idp.ldap.accesskey.info.KEY}

*mc-cmd*

*Required*

The configured access key to output information about.

You can list more than one access key by separating each key with a space.

### Example {#example}

Output information about the access keys `mykey` and `mykey2` from the `minio` deployment.

```shell
mc idp ldap accesskey info minio/ mykey mykey2
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

---
title: "mc idp ldap accesskey disable"
url: "/reference/minio-mc/mc-idp-ldap-accesskey-disable/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-idp-ldap-accesskey-disable"></a>
<a id="minio-mc-idp-ldap-accesskey-disable"></a>

<a id="command-mc.idp.ldap.accesskey.disable"></a>

## Description {#description}

[`mc idp ldap accesskey disable`](#command-mc.idp.ldap.accesskey.disable) disables the specified [access key](/administration/identity-access-management/minio-user-management/#minio-id-access-keys) on the MinIO deployment.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
> The following example disables the access key `mykey` on the `minio` deployment:

```shell
mc idp ldap accesskey disable minio mykey
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap accesskey disable  \
                                 ALIAS       \
                                 KEY
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment configured for AD/LDAP integration.
- Replace `KEY` with the access key to disable.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.accesskey.disable.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment configured for AD/LDAP.

For example:

```text
mc idp ldap accesskey disable minio
```

##### `KEY` {#mc.idp.ldap.accesskey.disable.KEY}

*mc-cmd*

*Required*

The configured access key to disable.

### Example {#example}

Disable the access key `mykey` from the `minio` deployment.

```shell
mc idp ldap accesskey disable minio/ mykey
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

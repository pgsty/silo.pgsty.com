---
title: "mc idp ldap enable"
url: "/reference/minio-mc/mc-idp-ldap-enable/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="mc-idp-ldap-enable"></a>
<a id="minio-mc-idp-ldap-enable"></a>

<a id="command-mc.idp.ldap.enable"></a>

## Description {#description}

The [`mc idp ldap enable`](#command-mc.idp.ldap.enable) command enables the currently configured AD/LDAP provider.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example enables the AD/LDAP configurations on the `myminio` deployment.

```shell
mc idp ldap enable   \
            myminio
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap enable  \
                          ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to enable the AD/LDAP integration.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.enable.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment for which to enable the AD/LDAP integration.

For example:

```text
mc idp ldap enable myminio
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

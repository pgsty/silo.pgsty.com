---
title: "mc idp ldap rm"
url: "/reference/minio-mc/mc-idp-ldap-rm/"
weight: 60
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-idp-ldap-rm.rst
upstream_modified: true
---

<a id="mc-idp-ldap-rm"></a>
<a id="minio-mc-idp-ldap-rm"></a>

<a id="command-mc.idp.ldap.rm"></a>

<a id="command-mc.idp.ldap.remove"></a>

## Description {#description}

The [`mc idp ldap rm`](#command-mc.idp.ldap.rm) command removes the existing configuration for an AD/LDAP provider.

[`mc idp ldap rm`](#command-mc.idp.ldap.rm) is also known as [`mc idp ldap remove`](#command-mc.idp.ldap.remove).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example removes the AD/LDAP provider settings for the `myminio` deployment.

```shell
mc idp ldap rm       \
            myminio
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap rm     \
                          ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to remove the AD/LDAP integration.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.remove.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment for which to remove the current AD/LDAP configuration.

For example:

```text
mc idp ldap rm myminio
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

SILO is the supported server for PGSTY mcli; compatibility with upstream MinIO and other S3 services is [best effort](/reference/minio-mc/#command-mc).

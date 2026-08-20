---
title: "mc idp ldap ls"
url: "/reference/minio-mc/mc-idp-ldap-ls/"
weight: 50
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-idp-ldap-ls.rst
upstream_modified: false
---

<a id="mc-idp-ldap-ls"></a>
<a id="minio-mc-idp-ldap-ls"></a>

<a id="command-mc.idp.ldap.ls"></a>

<a id="command-mc.idp.ldap.list"></a>

## Description {#description}

The [`mc idp ldap ls`](#command-mc.idp.ldap.ls) command lists the existing set of configurations for an AD/LDAP provider.

[`mc idp ldap ls`](#command-mc.idp.ldap.ls) is also known as [`mc idp ldap list`](#command-mc.idp.ldap.list).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example lists the AD/LDAP configuration settings for the `myminio` deployment.

```shell
mc idp ldap ls       \
            myminio
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap ls     \
                          ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to list the AD/LDAP integration.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.list.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment for which to output the current AD/LDAP configuration.

For example:

```text
mc idp ldap ls myminio
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

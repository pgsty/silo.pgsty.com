---
title: "mc idp ldap info"
url: "/reference/minio-mc/mc-idp-ldap-info/"
weight: 40
minio_origin: true
silo_modified: false
---

<a id="mc-idp-ldap-info"></a>
<a id="minio-mc-idp-ldap-info"></a>

<a id="command-mc.idp.ldap.info"></a>

## Description {#description}

The [`mc idp ldap info`](#command-mc.idp.ldap.info) command outputs the current configuration for an AD/LDAP provider on a specified MinIO deployment.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example outputs the AD/LDAP configuration settings on the `myminio` deployment.

```shell
mc idp ldap info     \
            myminio
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap info   \
                          ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to retrieve info on the AD/LDAP integration.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.info.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment for which to output the current AD/LDAP configuration.

For example:

```text
mc idp ldap info myminio
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

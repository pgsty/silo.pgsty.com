---
title: "mc admin user sts info"
url: "/reference/minio-mc-admin/mc-admin-user-sts-info/"
weight: 70
minio_origin: true
silo_modified: false
---

<a id="mc-admin-user-sts-info"></a>
<a id="minio-mc-admin-sts-info"></a>

<a id="command-mc.admin.user.sts.info"></a>

## Syntax {#syntax}

The [`mc admin user sts info`](#command-mc.admin.user.sts.info) command retrieves information on the specified STS credential, such as the parent [MinIO user](/administration/identity-access-management/minio-identity-management/#minio-internal-idp) who generated the credentials, associated policies, and expiration.

<abbr title="Security Token Service">STS</abbr> credentials provide temporary access to the MinIO deployment.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command retrieves information on the STS credentials with specified access key:

```shell
mc admin user sts info myminio/ "J123C4ZXEQN8RK6ND35I"
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user sts info          \
                                [--policy]    \
                                ALIAS         \
                                STSACCESSKEY
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.user.sts.info.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `STSACCESSKEY` {#mc.admin.user.sts.info.STSACCESSKEY}

*mc-cmd*

*Required*

The access key for the STS credentials.

##### `--policy` {#mc.admin.user.sts.info.-policy}

*mc-cmd*

*Optional*

Prints the policy attached to the specified STS credentials in JSON format.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

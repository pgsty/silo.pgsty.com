---
title: "mc admin kms key"
url: "/reference/minio-mc-admin/mc-admin-kms-key/"
weight: 90
minio_origin: true
silo_modified: false
---

<a id="mc-admin-kms-key"></a>

<a id="command-mc.admin.kms.key"></a>

## Description {#description}

The [`mc admin kms key`](#command-mc.admin.kms.key) command performs cryptographic key management operations through the MinIO Key Encryption Service (KES).

{{% alert color="info" %}}
**Use `mc admin` on MinIO Deployments Only**

MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.
{{% /alert %}}

## Syntax {#syntax}

#### `mc admin kms key create` {#mc.admin.kms.key.create}

*mc-cmd*

Creates a new master key on a Key Management System (KMS).

The command has the following syntax:

```shell
mc admin kms key create TARGET [KEY_NAME]
```

The command accepts the following arguments:

#### `TARGET` {#mc.admin.kms.key.create.TARGET}

*mc-cmd*

Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.

The `TARGET` deployment **must** include a configured MinIO Key Encryption Service (KES) server.

#### `KEY_NAME` {#mc.admin.kms.key.create.KEY_NAME}

*mc-cmd*

Specify the name of the new master key.

#### `mc admin kms key status` {#mc.admin.kms.key.status}

*mc-cmd*

Requests information on a Key Management System (KMS) master key.

The command has the following syntax:

```shell
mc admin kms key status TARGET [KEY_NAME]
```

The command accepts the following arguments:

#### `TARGET` {#mc.admin.kms.key.status.TARGET}

*mc-cmd*

Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.

The `TARGET` deployment **must** include a configured MinIO Key Encryption Service (KES) server.

#### `KEY_NAME` {#mc.admin.kms.key.status.KEY_NAME}

*mc-cmd*

Specify the name of a master key on the KMS.

Omit this argument to return the default master key on the [`TARGET`](#mc.admin.kms.key.status.TARGET) deployment.

#### `mc admin kms key list` {#mc.admin.kms.key.list}

*mc-cmd*

List all Key Management System (KMS) keys for a MinIO instance.

The command has the following syntax:

```shell
mc admin kms key list TARGET
```

The command accepts the following argument:

#### `TARGET` {#mc.admin.kms.key.list.TARGET}

*mc-cmd*

Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.

The `TARGET` deployment **must** include a configured MinIO Key Encryption Service (KES) server.

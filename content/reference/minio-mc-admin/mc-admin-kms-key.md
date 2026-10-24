---
title: "mc admin kms key"
url: "/reference/minio-mc-admin/mc-admin-kms-key/"
weight: 90
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-kms-key.rst
upstream_modified: true
---

<a id="mc-admin-kms-key"></a>

<a id="command-mc.admin.kms.key"></a>

## Description {#description}

The [`mc admin kms key`](#command-mc.admin.kms.key) command performs cryptographic key management operations through the MinIO Key Encryption Service (KES).

> [!NOTE]
> **Server compatibility**
>
> The supported server for [`mcli admin`](/reference/minio-mc-admin/#command-mc.admin) is SILO. Compatibility with unmodified upstream MinIO is best effort; general S3 compatibility alone does not provide these administrative APIs.

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

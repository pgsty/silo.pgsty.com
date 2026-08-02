---
title: "mc admin update"
url: "/reference/minio-mc-admin/mc-admin-update/"
weight: 180
minio_origin: true
silo_modified: false
---

<a id="mc-admin-update"></a>

<a id="command-mc.admin.update"></a>

## Description {#description}

The [`mc admin update`](#command-mc.admin.update) command updates all MinIO servers in the deployment. The command also supports using a private mirror server for environments where the deployment does not have public internet access.

After running the command, a prompt displays to confirm the update. Type `y` and `[ENTER]` to confirm and proceed with the update.

The user **must** have `write` permissions for the target location where the binary installs.

{{% alert color="info" %}}
**Use `mc admin` on MinIO Deployments Only**

MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.
{{% /alert %}}

## Considerations {#considerations}

### Updates are Non-Disruptive {#updates-are-non-disruptive}

[`mc admin update`](#command-mc.admin.update) updates the binary and restarts all MinIO servers in the deployment simultaneously. MinIO operations are atomic and strictly consistent and as such the restart process is non-disruptive to applications.

MinIO strongly recommends only performing simultaneous upgrade-and-restart procedures. Do not perform “rolling” (that is, one node at a time) upgrade procedures.

### Permissions {#permissions}

The user running the command **must** have `write` permissions to the target path where the MinIO Server binary installs.

## Examples {#examples}

Use [`mc admin update`](#command-mc.admin.update) to update each [`minio`](/reference/minio-server/#command-minio) server process in the MinIO deployment:

```shell
mc admin update ALIAS
```

Replace [`ALIAS`](#mc.admin.update.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

After running the command, answer yes to the prompt to confirm and process the update.

## Syntax {#syntax}

[`mc admin update`](#command-mc.admin.update) has the following syntax:

```shell
mc admin update ALIAS         \
                [MIRROR_URL]  \
                [--yes]
```

[`mc admin update`](#command-mc.admin.update) supports the following arguments:

#### `ALIAS` {#mc.admin.update.ALIAS}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment to update.

If the specified `ALIAS` corresponds to a distributed MinIO deployment, [`mc admin update`](#command-mc.admin.update) updates *all* MinIO servers in the deployment at the same time.

Use [`mc alias list`](/reference/minio-mc/mc-alias-list/#command-mc.alias.list) to review the configured aliases and their corresponding MinIO deployment endpoints.

#### `MIRROR_URL` {#mc.admin.update.MIRROR_URL}

*mc-cmd*

The mirror URL of the `minio` server binary to use for updating MinIO servers in the [`ALIAS`](#mc.admin.update.ALIAS) deployment.

#### `--yes, -y` {#mc.admin.update.-yes}

*mc-cmd*

*Optional*

Pass this flag to confirm the update and bypass the confirmation prompt.

## Behavior {#behavior}

### Binary Compression {#binary-compression}

{{% alert color="info" %}}
**Changed: RELEASE.2024-01-28T22-35-53Z**

[`mc admin update`](#command-mc.admin.update) compresses the binary before sending to all nodes in the deployment.
{{% /alert %}}

This feature does not apply to [systemctl managed deployments](/operations/deployments/baremetal/#minio-baremetal).

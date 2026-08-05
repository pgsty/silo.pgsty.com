---
title: "mc admin update"
url: "/reference/minio-mc-admin/mc-admin-update/"
weight: 180
minio_origin: true
silo_modified: true
---

<a id="mc-admin-update"></a>

<a id="command-mc.admin.update"></a>

## Description {#description}

The [`mc admin update`](#command-mc.admin.update) command invokes the MinIO-compatible server-side in-place update API. The client can pass an optional release mirror URL, and the server distributes the selected binary to all nodes.

After running the command, a prompt displays to confirm the update. Type `y` and `[ENTER]` to confirm and proceed with the update.

The user **must** have `write` permissions for the target location where the binary installs.

{{% alert color="danger" %}}
**Do not use the default update path on Silo**

As of 2026-08-05, the latest published Silo server (`RELEASE.2026-08-04T00-00-00Z`) still resolves an omitted `MIRROR_URL` through the upstream `dl.min.io` release feed and retains the upstream MinIO signing key. Running `mc admin update ALIAS` against an update-enabled Silo server can therefore replace Silo with an upstream MinIO binary.

Set `MINIO_UPDATE=off` on Silo servers and upgrade through [Download & Install](/download/#server), a trusted package repository, or a manually verified Silo artifact. This page retains the command contract for compatibility; it is not the recommended Silo upgrade procedure.
{{% /alert %}}

{{% alert color="info" %}}
**Use `mc admin` on Silo or compatible MinIO deployments only**

[`mc admin`](/reference/minio-mc-admin/#command-mc.admin) uses MinIO-specific administration APIs. General S3 API compatibility alone does not imply that another object store supports these commands.
{{% /alert %}}

## Considerations {#considerations}

### Coordinated Restart {#updates-are-non-disruptive}

[`mc admin update`](#command-mc.admin.update) updates the binary and restarts all servers in the deployment simultaneously. Applications should expect a temporary loss of availability and retry failed or interrupted requests; atomic object operations do not make a full-cluster restart invisible.

Use a coordinated upgrade-and-restart procedure. Do not perform a rolling (one node at a time) binary replacement unless the release documentation explicitly states that mixed versions are supported.

### Permissions {#permissions}

The user running the command **must** have `write` permissions to the target path where the MinIO Server binary installs.

## Examples {#examples}

The inherited default form below is shown only to identify the command contract. **Do not run it against Silo**, because omitting `MIRROR_URL` selects the upstream MinIO update feed:

```shell
mc admin update ALIAS
```

Replace [`ALIAS`](#mc.admin.update.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the target deployment.

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

The release-manifest URL used by the target server to locate the `minio` binary. Supplying a URL does not make an artifact trusted; verify the complete update and signature contract before using this compatibility path. Silo operators should prefer the documented package or manual upgrade procedure.

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

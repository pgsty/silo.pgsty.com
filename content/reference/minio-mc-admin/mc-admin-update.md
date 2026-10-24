---
title: "mc admin update"
url: "/reference/minio-mc-admin/mc-admin-update/"
weight: 180
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-update.rst
upstream_modified: true
---

<a id="mc-admin-update"></a>

<a id="command-mc.admin.update"></a>

## Description {#description}

`mcli admin update` invokes the retained server-side update API. **Current SILO permanently disables this API.** Neither `MINIO_UPDATE=on`, a mirror URL, nor `--yes` enables in-place updates. Install a verified package, binary, or container image using the [SILO upgrade procedure](/operations/deployments/baremetal-upgrade-minio-deployment/).

The client retains this command for other servers implementing the inherited API. Compatibility with unmodified upstream MinIO is best effort. Do not treat that retained client syntax as a SILO update mechanism.

> [!CAUTION]
> SILO releases from 20260804 or earlier still had an upstream updater. On those old servers, an omitted mirror URL could select the upstream MinIO feed and replace the server. Disable updates on those legacy deployments with `MINIO_UPDATE=off` and migrate through verified SILO artifacts.

## Considerations {#considerations}

### Coordinated Restart {#updates-are-non-disruptive}

Install the same release across the deployment and perform a coordinated restart through the service manager. Applications should retry requests interrupted during the restart. Do not assume mixed-version rolling upgrades are supported.

### Permissions {#permissions}

Package or manual binary replacement requires operating-system permission to replace the executable. Administrative API permission does not override SILO's disabled updater.

## Examples {#examples}

Use [Download & Install](/download/#server) to obtain a verified SILO artifact, then follow the [upgrade procedure](/operations/deployments/baremetal-upgrade-minio-deployment/). The syntax below is retained for reference, not as an executable SILO upgrade example.

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

On a server that implements the inherited updater, the request targets the whole deployment. Current SILO rejects the update.

Use [`mc alias list`](/reference/minio-mc/mc-alias-list/#command-mc.alias.list) to review the configured aliases and their corresponding MinIO deployment endpoints.

#### `MIRROR_URL` {#mc.admin.update.MIRROR_URL}

*mc-cmd*

The release-manifest URL used by the target server to locate the `minio` binary. Supplying a URL does not make an artifact trusted; verify the complete update and signature contract before using this compatibility path. Silo operators should prefer the documented package or manual upgrade procedure.

#### `--yes, -y` {#mc.admin.update.-yes}

*mc-cmd*

*Optional*

On a server with an enabled updater, bypass the client confirmation prompt. This flag does not enable updates on SILO.

## Behavior {#behavior}

### Binary Compression {#binary-compression}

The inherited update protocol can compress binaries for distribution between nodes. This does not apply to current SILO, which rejects in-place updates before replacing its binary.

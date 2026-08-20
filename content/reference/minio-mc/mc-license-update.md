---
title: "mc license update"
url: "/reference/minio-mc/mc-license-update/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-license-update.rst
upstream_modified: false
---

<a id="mc-license-update"></a>

<a id="command-mc.license.update"></a>

## Description {#description}

Use the [`mc license update`](#command-mc.license.update) command to replace a license key for a deployment.

For deployments registered for [MinIO SUBNET](https://min.io/pricing?jmp=docs), MinIO automatically checks for and updates the license every month.

## Examples {#examples}

### Update the License Key for a Deployment with Alias `minio1` {#update-the-license-key-for-a-deployment-with-alias-minio1}

```shell
mc license update minio1 license.key
```

## Syntax {#syntax}

The command has the following syntax:

```shell
mc [GLOBALFLAGS] license update                   \
                         ALIAS                    \
                         [LICENSE-FILE-WITH-PATH] \
                         [--airgap]
```

### Parameters {#parameters}

##### `ALIAS` {#mc.license.update.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

##### `LICENSE-FILE-WITH-PATH` {#mc.license.update.LICENSE-FILE-WITH-PATH}

*mc-cmd*

*Optional*

The path (relative to the current working directory) and file name of the key to use to update the deployment’s license.

To download the API key from SUBNET:

1. Log in to [MinIO SUBNET](https://min.io/pricing?jmp=docs)
2. Go to the **Deployments** tab
3. Select the **API Key** button near the top of the page on the right side of the account statistics information box
4. Select copy button to the right of the key field to copy the key value to your clipboard

##### `--airgap` {#mc.license.update.-airgap}

*mc-cmd*

*Optional*

Use in environments without network access to SUBNET (for example, airgapped, firewalled, or similar configuration).

If the deployment is airgapped, but the local device where you are using the [minio client](/reference/minio-mc/#minio-client) has network access, you do not need to use the `--airgap` flag.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

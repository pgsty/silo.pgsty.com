---
title: "mc license info"
url: "/reference/minio-mc/mc-license-info/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-license-info"></a>

<a id="command-mc.license.info"></a>

## Description {#description}

The [`mc license info`](#command-mc.license.info) command displays information about the MinIO deployment’s license status. Specifically, whether the deployment uses the AGPLv3 Open Source license of the [MinIO Commercial License](https://min.io/product/subnet?ref=docs).

You must register your deployment with MinIO [MinIO SUBNET](https://min.io/pricing?jmp=docs) to activate your commercial license.

For example, the command returns the following information for an unregistered deployment:

```shell
You are using GNU AFFERO GENERAL PUBLIC LICENSE Version 3 (https://www.gnu.org/licenses/agpl-3.0.txt)

If you are building proprietary applications, you may want to choose the commercial license
included as part of the Standard and Enterprise subscription plans. (https://min.io/signup?ref=mc)

Applications must otherwise comply with all the GNU AGPLv3 License & Trademark obligations.
```

Use [`mc license register`](/reference/minio-mc/mc-license-register/#command-mc.license.register) to associate your deployment with your SUBNET account. If you are not already signed up for SUBNET, see the [Registration](https://min.io/pricing?ref=docs) page.

## Examples {#examples}

### Display the Current License for a Deployment with Alias `minio1` {#display-the-current-license-for-a-deployment-with-alias-minio1}

```shell
mc license info minio1
```

If a deployment uses an expired MinIO Commercial License, the command outputs an error message.

## Syntax {#syntax}

The command has the following syntax:

```shell
mc [GLOBALFLAGS] license info       \
                         ALIAS      \
                         [--airgap]
```

### Parameters {#parameters}

##### `ALIAS` {#mc.license.info.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

##### `--airgap` {#mc.license.info.-airgap}

*mc-cmd*

*Optional*

Use in environments where the client machine running the [minio client](/reference/minio-mc/#minio-client) does not have network access to SUBNET (for example, airgapped, firewalled, or similar configuration) to display instructions for how to register the deployment with SUBNET.

If the deployment is airgapped, but the local device has network access, you do not need to use the `--airgap` flag.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

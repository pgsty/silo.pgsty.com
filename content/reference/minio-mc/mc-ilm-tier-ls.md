---
title: "mc ilm tier ls"
url: "/reference/minio-mc/mc-ilm-tier-ls/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-ilm-tier-ls.rst
upstream_modified: true
---

<a id="mc-ilm-tier-ls"></a>
<a id="minio-mc-ilm-tier-ls"></a>

<a id="command-mc.ilm.tier.list"></a>

<a id="command-mc.ilm.tier.ls"></a>

> [!NOTE]
> **Changed: RELEASE.2022-12-24T15-21-38Z**
>
> [`mc ilm tier ls`](#command-mc.ilm.tier.ls) replaces `mc admin tier ls`.

## Description {#description}

The [`mc ilm tier ls`](#command-mc.ilm.tier.ls) command shows the remote tiers configured on a deployment.

The [`mc ilm tier list`](#command-mc.ilm.tier.list) command has equivalent functionality to [`mc ilm tier ls`](#command-mc.ilm.tier.ls).

## Syntax {#syntax}

The command has the following syntax:

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example outputs a list of the existing remote tiers on the `myminio` deployment.

```shell
 mc ilm tier ls myminio
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc ilm tier ls TARGET TIER_NAME
```
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

The command accepts the following argument:

##### `TARGET` {#mc.ilm.tier.ls.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment on which the desired tier exists.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

### S3 Compatibility {#s3-compatibility}

SILO is the supported server for PGSTY mcli; compatibility with upstream MinIO and other S3 services is [best effort](/reference/minio-mc/#command-mc).

## Required Permissions {#required-permissions}

For permissions required for reviewing a tier, refer to the [required permissions](/reference/minio-mc/mc-ilm-tier/#minio-mc-ilm-tier-permissions) on the parent command.

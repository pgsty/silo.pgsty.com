---
title: "mc ilm tier check"
url: "/reference/minio-mc/mc-ilm-tier-check/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-ilm-tier-check.rst
upstream_modified: false
---

<a id="mc-ilm-tier-check"></a>
<a id="minio-mc-ilm-tier-check"></a>

<a id="command-mc.ilm.tier.check"></a>

## Description {#description}

The [`mc ilm tier check`](#command-mc.ilm.tier.check) command displays the configuration for remote tier on a deployment.

## Syntax {#syntax}

The command has the following syntax:

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example displays the configuration for an existing remote tier called `WARM-TIER` on the `myminio` deployment.

```shell
 mc ilm tier check myminio WARM-TIER
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc ilm tier add TARGET TIER_NAME
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

The command accepts the following arguments:

##### `TARGET` {#mc.ilm.tier.check.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment on which the desired tier exists.

##### `TIER_NAME` {#mc.ilm.tier.check.TIER_NAME}

*mc-cmd*

*Required*

The name of an existing remote tier to display.

You **must** specify the tier in all-caps, e.g. `WARM_TIER`.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Display the Configuration for an Existing Tier {#display-the-configuration-for-an-existing-tier}

The following example displays the configuration of the tier `WARM-TIER` on the `myminio` deployment.

```shell
mc ilm tier check myminio WARM-TIER
```

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

## Required Permissions {#required-permissions}

For permissions required to review a tier, refer to the [required permissions](/reference/minio-mc/mc-ilm-tier/#minio-mc-ilm-tier-permissions) on the parent command.

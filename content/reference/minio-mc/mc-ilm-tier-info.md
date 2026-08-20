---
title: "mc ilm tier info"
url: "/reference/minio-mc/mc-ilm-tier-info/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-ilm-tier-info.rst
upstream_modified: false
---

<a id="mc-ilm-tier-info"></a>
<a id="minio-mc-ilm-tier-info"></a>

<a id="command-mc.ilm.tier.info"></a>

## Description {#description}

The [`mc ilm tier info`](#command-mc.ilm.tier.info) command outputs statistics about a tier or all tiers for a deployment.

### Required Permissions {#required-permissions}

MinIO requires the following permissions scoped to the bucket or buckets for which you are creating lifecycle management rules.

- [`s3:PutLifecycleConfiguration`](/administration/identity-access-management/policy-based-access-control/#policy-action.s3-PutLifecycleConfiguration)
- [`s3:GetLifecycleConfiguration`](/administration/identity-access-management/policy-based-access-control/#policy-action.s3-GetLifecycleConfiguration)

MinIO also requires the following administrative permissions on the cluster in which you are creating remote tiers for object transition lifecycle management rules:

- [`admin:SetTier`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-SetTier)
- [`admin:ListTier`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-ListTier)

For example, the following policy provides permission for configuring object transition lifecycle management rules on any bucket in the cluster:.

```json
{
   "Version": "2012-10-17",
   "Statement": [
      {
            "Action": [
               "admin:SetTier",
               "admin:ListTier"
            ],
            "Effect": "Allow",
            "Sid": "EnableRemoteTierManagement"
      },
      {
            "Action": [
               "s3:PutLifecycleConfiguration",
               "s3:GetLifecycleConfiguration"
            ],
            "Resource": [
                        "arn:aws:s3:::*"
            ],
            "Effect": "Allow",
            "Sid": "EnableLifecycleManagementRules"
      }
   ]
}
```

## Syntax {#syntax}

The command has the following syntax:

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example outputs the configuration for an existing remote tier called `WARM-TIER` on the `myminio` deployment.

```shell
 mc ilm tier info myminio WARM-TIER
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc ilm tier info TARGET TIER_NAME
```
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

The command accepts the following arguments:

##### `TARGET` {#mc.ilm.tier.info.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment on which the desired tier exists.

##### `TIER_NAME` {#mc.ilm.tier.info.TIER_NAME}

*mc-cmd*

*Optional*

The name of an existing remote tier to display.

You **must** specify the tier in all-caps, e.g. `WARM_TIER`.

If not specified, MinIO lists statistics for all existing tiers on the deployment.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Display the Statistics for an Existing Tier {#display-the-statistics-for-an-existing-tier}

The following example displays the statistics of the tier `WARM-TIER` on the `myminio` deployment.

```shell
mc ilm tier info myminio WARM-TIER
```

### Display the Statistics for all Existing Tiers on a Deployment {#display-the-statistics-for-all-existing-tiers-on-a-deployment}

The following example displays the statistics of all existing tiers on the `myminio` deployment.

```shell
mc ilm tier info myminio
```

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

## Required Permissions {#id1}

For permissions required to review a tier, refer to the [required permissions](/reference/minio-mc/mc-ilm-tier/#minio-mc-ilm-tier-permissions) on the parent command.

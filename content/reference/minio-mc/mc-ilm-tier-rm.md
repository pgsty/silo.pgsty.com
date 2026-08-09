---
title: "mc ilm tier rm"
url: "/reference/minio-mc/mc-ilm-tier-rm/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="mc-ilm-tier-rm"></a>
<a id="minio-mc-ilm-tier-rm"></a>

<a id="command-mc.ilm.tier.remove"></a>

<a id="command-mc.ilm.tier.rm"></a>

## Description {#description}

The [`mc ilm tier rm`](#command-mc.ilm.tier.rm) command removes an remote tier that has not been used to transition any objects.

The [`mc ilm tier remove`](#command-mc.ilm.tier.remove) command has equivalent functionality to [`mc ilm tier rm`](#command-mc.ilm.tier.rm)

{{% alert color="info" %}}
**Note**

Once a tier has transitioned objects, it cannot be removed.
{{% /alert %}}

### Required Permissions {#required-permissions}

MinIO requires the following permissions scoped to to the bucket or buckets for which you are creating lifecycle management rules.

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

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example removes an existing remote tier called `WARM-TIER` on the `myminio` deployment. No objects have transitioned to the `WARM-TIER` tier.

```shell
 mc ilm tier rm myminio WARM-TIER
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc ilm tier info TARGET TIER_NAME
```

{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

The command accepts the following arguments:

##### `TARGET` {#mc.ilm.tier.rm.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment on which the desired tier exists.

##### `TIER_NAME` {#mc.ilm.tier.rm.TIER_NAME}

*mc-cmd*

*Required*

The name of an existing remote tier to remove.

You **must** specify the tier in all-caps, e.g. `WARM_TIER`.

No object can have transitioned to the tier.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

## Required Permissions {#id1}

For permissions required to remove a tier, refer to the [required permissions](/reference/minio-mc/mc-ilm-tier/#minio-mc-ilm-tier-permissions) on the parent command.

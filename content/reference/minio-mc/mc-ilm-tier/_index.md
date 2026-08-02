---
title: "mc ilm tier"
url: "/reference/minio-mc/mc-ilm-tier/"
weight: 30
icon: fa-solid fa-layer-group
minio_origin: true
silo_modified: false
---

<a id="mc-ilm-tier"></a>

<a id="command-mc.ilm.tier"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

[`mc ilm tier`](#command-mc.ilm.tier) replaces `mc admin tier`.
{{% /alert %}}

## Description {#description}

The [`mc ilm tier`](#command-mc.ilm.tier) command and its subcommands configure a remote supported S3-compatible service for MinIO [Lifecycle Management: Object Transition (“Tiering”)](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration).

After creating one or more tiers with this command, use [`mc ilm rule`](/reference/minio-mc/mc-ilm-rule/#command-mc.ilm.rule) and its subcommands to create the rules that move objects to other storage.

For more information, see the overview of [lifecycle management](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management).

## Subcommands {#subcommands}

[`mc ilm tier`](#command-mc.ilm.tier) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier-add/#command-mc.ilm.tier.add"><code>add</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-tier-add/#command-mc.ilm.tier.add"><code>mc ilm tier add</code></a> command creates a new remote storage tier to a supported storage services.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier-check/#command-mc.ilm.tier.check"><code>check</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-tier-check/#command-mc.ilm.tier.check"><code>mc ilm tier check</code></a> command displays the configuration for remote tier on a deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier-info/#command-mc.ilm.tier.info"><code>info</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-tier-info/#command-mc.ilm.tier.info"><code>mc ilm tier info</code></a> command outputs statistics about a tier or all tiers for a deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier-ls/#command-mc.ilm.tier.ls"><code>ls</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-tier-ls/#command-mc.ilm.tier.ls"><code>mc ilm tier ls</code></a> command shows the remote tiers configured on a deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier-rm/#command-mc.ilm.tier.rm"><code>rm</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-tier-rm/#command-mc.ilm.tier.rm"><code>mc ilm tier rm</code></a> command removes an remote tier that has not been used to transition any objects.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier-update/#command-mc.ilm.tier.update"><code>update</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-tier-update/#command-mc.ilm.tier.update"><code>mc ilm tier update</code></a> command modifies an existing configured remote tier.</p></td>
    </tr>
  </tbody>
</table>

<a id="minio-mc-ilm-tier-permissions"></a>

## Required Permissions {#required-permissions}

To create tiers for object transition, MinIO requires the following administrative permissions on the cluster:

- [`admin:SetTier`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-SetTier)
- [`admin:ListTier`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-ListTier)

For example, the following policy provides sufficient permissions for configuring object transition lifecycle management rules on any bucket in the cluster:

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

### Transition Permissions {#transition-permissions}

Object transition lifecycle management rules require additional permissions on the remote storage tier. Specifically, MinIO requires the remote tier credentials provide read, write, list, and delete permissions.

For example, if the remote storage tier implements AWS IAM policy-based access control, the following policy provides the necessary permissions for transitioning objects into and out of the remote tier:

```json
{
   "Version": "2012-10-17",
   "Statement": [
      {
            "Action": [
               "s3:ListBucket"
            ],
            "Effect": "Allow",
            "Resource": [
               "arn:aws:s3:::MyDestinationBucket"
            ],
            "Sid": ""
      },
      {
            "Action": [
               "s3:GetObject",
               "s3:PutObject",
               "s3:DeleteObject"
            ],
            "Effect": "Allow",
            "Resource": [
               "arn:aws:s3:::MyDestinationBucket/*"
            ],
            "Sid": ""
      }
   ]
}

```

Modify the `Resource` for the bucket into which MinIO tiers objects.

{{% alert color="info" %}}
**Avoid enabling versioning in the remote tier**

MinIO strongly recommends against enabling bucket versioning for remote tiers. If the remote tier bucket is versioned, each source object version is transitioned to a *unique object* in the remote tier.

If your environment requires versioning for the remote tier, you must also allow the `s3:DeleteObjectVersion` permission.
{{% /alert %}}

Defer to the documentation for the supported tiering targets for more complete information on configuring users and permissions to support MinIO tiering:

- [Amazon S3 Permissions](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazons3.html#amazons3-actions-as-permissions)
- [Google Cloud Storage Access Control](https://cloud.google.com/storage/docs/access-control)
- [Authorizing access to data in Azure storage](https://docs.microsoft.com/en-us/azure/storage/common/storage-auth?toc=/azure/storage/blobs/toc.json)

---
title: "mc ilm rule"
url: "/reference/minio-mc/mc-ilm-rule/"
weight: 20
icon: fa-solid fa-list-check
minio_origin: true
silo_modified: false
---

<a id="mc-ilm-rule"></a>

<a id="command-mc.ilm.rule"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

The following commands have moved to subcommands under [`mc ilm rule`](#command-mc.ilm.rule):

- [`mc ilm add`](/reference/deprecated/mc-ilm-add/#command-mc.ilm.add)
- [`mc ilm edit`](/reference/deprecated/mc-ilm-edit/#command-mc.ilm.edit)
- [`mc ilm export`](/reference/deprecated/mc-ilm-export/#command-mc.ilm.export)
- [`mc ilm import`](/reference/deprecated/mc-ilm-import/#command-mc.ilm.import)
- [`mc ilm ls`](/reference/deprecated/mc-ilm-ls/#command-mc.ilm.ls)
- [`mc ilm rm`](/reference/deprecated/mc-ilm-rm/#command-mc.ilm.rm)
{{% /alert %}}

## Description {#description}

The [`mc ilm rule`](#command-mc.ilm.rule) command and its subcommands configure the rules used to transition objects between storage tiers in MinIO’s Lifecycle Management.

Before creating rules with this command, use [`mc ilm tier`](/reference/minio-mc/mc-ilm-tier/#command-mc.ilm.tier) and its subcommands to create the tier or tiers of other object storage locations where objects move.

For more information, see the overview of [lifecycle management](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management).

## Subcommands {#subcommands}

[`mc ilm rule`](#command-mc.ilm.rule) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-rule-add/#command-mc.ilm.rule.add"><code>add</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-rule-add/#command-mc.ilm.rule.add"><code>mc ilm rule add</code></a> command adds an object lifecycle management rule to a bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-rule-edit/#command-mc.ilm.rule.edit"><code>edit</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-rule-edit/#command-mc.ilm.rule.edit"><code>mc ilm rule edit</code></a> command modifies an existing object lifecycle management
rule on a MinIO bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-rule-export/#command-mc.ilm.rule.export"><code>export</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-rule-export/#command-mc.ilm.rule.export"><code>mc ilm rule export</code></a> command exports the object lifecycle management configuration for a MinIO bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-rule-import/#command-mc.ilm.rule.import"><code>import</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-rule-import/#command-mc.ilm.rule.import"><code>mc ilm rule import</code></a> command imports an object lifecycle management
configuration and applies it to a MinIO bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls"><code>ls</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls"><code>mc ilm rule ls</code></a> command summarizes all configured object lifecycle management rules on a MinIO bucket in a tabular format.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-rule-rm/#command-mc.ilm.rule.rm"><code>rm</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-rule-rm/#command-mc.ilm.rule.rm"><code>mc ilm rule rm</code></a> command removes an object lifecycle management rule from a MinIO Bucket.</p></td>
    </tr>
  </tbody>
</table>

<a id="minio-mc-ilm-rule-permissions"></a>

## Permissions {#permissions}

MinIO requires the following permissions scoped to the bucket or buckets for which you create lifecycle management rules.

- [`s3:PutLifecycleConfiguration`](/administration/identity-access-management/policy-based-access-control/#policy-action.s3-PutLifecycleConfiguration)
- [`s3:GetLifecycleConfiguration`](/administration/identity-access-management/policy-based-access-control/#policy-action.s3-GetLifecycleConfiguration)

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

### Transition Permissions {#transition-permissions}

Object transition lifecycle management rules require additional permissions on the remote storage tier. Specifically, MinIO requires the remote tier credentials provide read, write, list, and delete permissions.

For example, if the remote storage tier implements AWS IAM policy-based access control, the following policy provides the necessary permission for transitioning objects into and out of the remote tier:

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

Defer to the documentation for the supported tiering targets for more complete information on configuring users and permissions to support MinIO tiering:

- [Amazon S3 Permissions](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazons3.html#amazons3-actions-as-permissions)
- [Google Cloud Storage Access Control](https://cloud.google.com/storage/docs/access-control)
- [Authorizing access to data in Azure storage](https://docs.microsoft.com/en-us/azure/storage/common/storage-auth?toc=/azure/storage/blobs/toc.json)

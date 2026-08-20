---
title: "Enable Two-Way Server-Side Bucket Replication"
url: "/administration/bucket-replication/enable-server-side-two-way-bucket-replication/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/bucket-replication/enable-server-side-two-way-bucket-replication.rst
upstream_modified: false
---

<a id="enable-two-way-server-side-bucket-replication"></a>
<a id="minio-bucket-replication-serverside-twoway"></a>

The procedure on this page creates a new bucket replication rule for two-way “active-active” synchronization of objects between MinIO buckets.

<img src="/images/replication/active-active-twoway-replication.svg" alt="Active-Active Replication synchronizes data between two remote clusters." style="max-width: 800px; height: auto;" />

- To configure replication between arbitrary S3-compatible services, use [`mc mirror`](/reference/minio-mc/mc-mirror/#command-mc.mirror).
- To configure one-way “active-passive” replication between MinIO clusters, see [Enable One-Way Server-Side Bucket Replication](/administration/bucket-replication/enable-server-side-one-way-bucket-replication/#minio-bucket-replication-serverside-oneway).
- To configure multi-site “active-active” replication between MinIO clusters, see [Enable Multi-Site Server-Side Bucket Replication](/administration/bucket-replication/enable-server-side-multi-site-bucket-replication/#minio-bucket-replication-serverside-multi).

This tutorial covers configuring Active-Active replication between two MinIO clusters. For a tutorial on multi-site replication between three or more MinIO clusters, see [Enable Multi-Site Server-Side Bucket Replication](/administration/bucket-replication/enable-server-side-multi-site-bucket-replication/#minio-bucket-replication-serverside-multi).

<a id="minio-bucket-replication-serverside-twoway-requirements"></a>

## Requirements {#requirements}

You must meet all of the basic requirements for bucket replication described in [Bucket Replication Requirements](/administration/bucket-replication/bucket-replication-requirements/#minio-bucket-replication-requirements).

In addition, to set up active-active bucket replication, you must meet the following additional requirements:

<a id="minio-bucket-replication-serverside-twoway-permissions"></a>

### Access to Both Clusters {#access-to-both-clusters}

You must have network access and login credentials with required permissions to both deployment to set up active-active bucket replication.

You can access the deployments by installing [`mc`](/reference/minio-mc/#command-mc) and using the command line. Use the [`mc alias set`](/reference/minio-mc/mc-alias-set/#command-mc.alias.set) command to create an alias for both MinIO deployments.

Alias creation requires specifying an access key for a user on the deployment. This user **must** have permission to create and manage users and policies on the deployment.

Specifically, ensure the user has *at minimum*:

- [`admin:CreateUser`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-CreateUser)
- [`admin:ListUsers`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-ListUsers)
- [`admin:GetUser`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-GetUser)
- [`admin:CreatePolicy`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-CreatePolicy)
- [`admin:GetPolicy`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-GetPolicy)
- [`admin:AttachUserOrGroupPolicy`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-AttachUserOrGroupPolicy)

## Considerations {#considerations}

> [!DETAILS]- Use Consistent Replication Settings
> MinIO supports customizing the replication configuration to enable or disable the following replication behaviors:
>
> - Replication of [delete operations](/administration/object-management/object-delete/#minio-object-delete)
> - Replication of delete markers
> - Replication of existing objects
> - Replication of metadata-only changes
>
> When configuring replication rules for a bucket, ensure that both MinIO deployments participating in active-active replication use the *same* replication behaviors to ensure consistent and predictable synchronization of objects.

> [!DETAILS]- Replication of Existing Objects
> MinIO supports automatically replicating existing objects in a bucket.
>
> MinIO requires explicitly enabling replication of existing objects using the [`mc replicate add --replicate`](/reference/minio-mc/mc-replicate-add/#mc.replicate.add.-replicate) or [`mc replicate update --replicate`](/reference/minio-mc/mc-replicate-update/#mc.replicate.update.-replicate) and including the `existing-objects` replication feature flag. This procedure includes the required flags for enabling replication of existing objects.

> [!DETAILS]- Replication of Delete Operations
> MinIO supports replicating delete operations onto the target bucket. Specifically, MinIO can replicate versioning [Delete Markers](https://docs.aws.amazon.com/AmazonS3/latest/userguide/versioning-workflows.html) and the deletion of specific versioned objects:
>
> - For delete operations on an object, MinIO replication also creates the delete marker on the target bucket.
> - For delete operations on versions of an object, MinIO replication also deletes those versions on the target bucket.
>
> MinIO requires explicitly enabling replication of delete operations using the [`mc replicate add --replicate`](/reference/minio-mc/mc-replicate-add/#mc.replicate.add.-replicate) or [`mc replicate update --replicate`](/reference/minio-mc/mc-replicate-update/#mc.replicate.update.-replicate). This procedure includes the required flags for enabling replication of delete operations and delete markers.
>
> MinIO does *not* replicate delete operations resulting from the application of [lifecycle management expiration rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration). Configure matching expiration rules on both the source and destination bucket to ensure consistent application of object expiration.
>
> See [Replication of Delete Operations](/administration/bucket-replication/#minio-replication-behavior-delete) and [Object Deletion](/administration/object-management/object-delete/#minio-object-delete) for more complete documentation.

> [!DETAILS]- Multi-Site Replication
> MinIO supports configuring multiple remote targets per bucket or bucket prefix. This enables configuring multi-site active-active replication between MinIO deployments.
>
> This procedure covers active-active replication between *two* MinIO sites. You can repeat this procedure for each “pair” of MinIO deployments in the replication mesh. For a dedicated tutorial, see [Enable Multi-Site Server-Side Bucket Replication](/administration/bucket-replication/enable-server-side-multi-site-bucket-replication/#minio-bucket-replication-serverside-multi).

## Procedure {#procedure}

- **[Configure Two-Way Bucket Replication Using the Command Line](#minio-bucket-replication-two-way-minio-cli-procedure)**

  > - [Create Replication Remote Targets](#minio-bucket-replication-two-way-minio-cli-create-remote-targets)
  > - [Create a New Bucket Replication Rule on Each Deployment](#minio-bucket-replication-two-way-minio-cli-create-replication-rules)
  > - [Validate the Replication Configuration](#minio-bucket-replication-two-way-minio-cli-verify-replication-config)

<a id="minio-bucket-replication-two-way-minio-cli-procedure"></a>

### Configure Two-Way Bucket Replication Using the Command Line `mc` {#configure-two-way-bucket-replication-using-the-command-line-mc}

This procedure creates two-way, active-active replication between two MinIO deployments.

This procedure assumes you have already defined an alias for each deployment as a user with the [necessary replication permissions](#minio-bucket-replication-serverside-twoway-permissions).

> [!NOTE]
> **Changed: RELEASE.2022-12-24T15-21-38Z**
>
> [`mc replicate add`](/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add) automatically creates the necessary replication targets, removing the need for using the deprecated `mc admin remote bucket add` command. This procedure only documents the procedure as of that release.

<a id="minio-bucket-replication-two-way-minio-cli-create-replication-rules"></a>
<a id="minio-bucket-replication-two-way-minio-cli-create-remote-targets"></a>

#### 1) Create a New Bucket Replication Rule on Each Deployment {#create-a-new-bucket-replication-rule-on-each-deployment}

Use the [`mc replicate add`](/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add) command to add a new replication rule to each MinIO deployment.

```shell
mc replicate add ALIAS/BUCKET \
   --remote-bucket 'https://USER:PASSWORD@HOSTNAME:PORT/BUCKET' \
   --replicate "delete,delete-marker,existing-objects"
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the origin MinIO deployment. The name *must* match the bucket specified when creating the remote target in the previous step.
- Replace `BUCKET` with the name of the bucket to replicate from on the origin deployment.
- Replace the `--remote-bucket` to specify the remote MinIO deployment and bucket to which the `ALIAS/BUCKET` replicates.

  The `USER:PASSWORD` must correspond to a user on the remote deployment with the [necessary replication permissions](#minio-bucket-replication-serverside-twoway-permissions).

  The `HOSTNAME:PORT` must resolve to a reachable MinIO instance on the remote deployment. The `BUCKET` must exist and otherwise meet all other [replication requirements](/administration/bucket-replication/bucket-replication-requirements/#minio-bucket-replication-requirements).
- The `--replicate "delete,delete-marker,existing-objects"` flag enables the following replication features:

  - [Replication of Deletes](/administration/bucket-replication/#minio-replication-behavior-delete)
  - [Replication of existing Objects](/administration/bucket-replication/#minio-replication-behavior-existing-objects)

  See [`mc replicate add --replicate`](/reference/minio-mc/mc-replicate-add/#mc.replicate.add.-replicate) for more complete documentation. Omit any field to disable replication of that component.

Specify any other supported optional arguments for [`mc replicate add`](/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add).

Repeat this step on the other MinIO deployment. Change the `ALIAS` and `--remote-bucket` values to correspond to the first deployment.

You should have two replication rules configured at the conclusion of this step - one created on each deployment that points to the bucket on the other deployment. Use the [`mc replicate ls`](/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls) command to verify the created replication rules.

<a id="minio-bucket-replication-two-way-minio-cli-verify-replication-config"></a>

#### 2) Validate the Replication Configuration {#validate-the-replication-configuration}

Use [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) to copy a new object to the replicated bucket on one of the deployments.

```shell
mc cp ~/foo.txt ALIAS/BUCKET
```

Use [`mc ls`](/reference/minio-mc/mc-ls/#command-mc.ls) to verify the object exists on the destination bucket:

```shell
mc ls ALIAS/BUCKET
```

Repeat this test by copying another object to the second deployment and verifying the object replicates to the first deployment.

Once both objects exist on both deployments, you have successfully set up two-way, active-active replication between MinIO buckets.

> [!NOTE]
> **See also**
>
> - Use the [`mc replicate update`](/reference/minio-mc/mc-replicate-update/#command-mc.replicate.update) command to modify an existing replication rule.
> - Use the [`mc replicate update`](/reference/minio-mc/mc-replicate-update/#command-mc.replicate.update) command with the [`--state "disable"`](/reference/minio-mc/mc-replicate-update/#mc.replicate.update.-state) flag to disable an existing replication rule.
> - Use the [`mc replicate rm`](/reference/minio-mc/mc-replicate-rm/#command-mc.replicate.rm) command to remove an existing replication rule.

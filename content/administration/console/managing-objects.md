---
title: "Managing Objects"
url: "/administration/console/managing-objects/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="managing-objects"></a>
<a id="minio-console-managing-objects"></a>

You can use the MinIO Console to perform several of the bucket and object management and interaction functions available in MinIO. Depending on the permissions and IAM policies for the authenticated user, you can:

- [Browse, upload, revert, manage, and interact with objects](#minio-console-object-browser).
- [Browse, create, and manage buckets](#minio-console-buckets).
- [Create or monitor remote tiers](#minio-console-tiers) for object transition rules.

<a id="minio-console-object-browser"></a>

## Object Browser {#object-browser}

The Object Browser lists the buckets and objects the authenticated user has access to on the deployment.

After logging in or navigating to the tab, the object browser displays a list of the user’s buckets, which the user can filter. Select a bucket to show a list of objects in the bucket.

Select a specific object to display summary information about the object such as name, size, tags, holds, and retention policies that apply. The console also shows the object’s metadata.

The user can perform actions on the bucket’s objects, depending on the policies and permissions that apply. Example actions the user may be able to perform include:

- Rewind to a previous version
- Create prefixes
- View deleted objects
- Upload objects
- Download objects
- Share
- Preview
- Manage legal holds
- Manage retention
- Manage tags
- Inspect
- Display versions
- [Delete](/administration/object-management/object-delete/#minio-object-delete)

{{% alert color="info" %}}
**Added: Console**

v0.24.0

View the status of uploading or downloading objects with the object manager button available on the top right corner of the Console. If you have not uploaded or downloaded any objects during the current session, the button does not appear.
{{% /alert %}}

{{% alert color="info" %}}
**Changed: Console**

v0.35.0

If you select multiple objects to download, MinIO creates a ZIP archive of those objects for downloading. You must unzip or uncompress this archive after downloading to access the files.
{{% /alert %}}

<a id="minio-console-admin-buckets"></a>
<a id="minio-console-buckets"></a>

## Buckets {#buckets}

The Console’s **Bucket** section displays all buckets to which the authenticated user has [access](/administration/identity-access-management/policy-based-access-control/#minio-policy). Use this section to create or manage these buckets, depending on your user’s access.

### Creating Buckets {#creating-buckets}

Select **Create Bucket** to create a new bucket on the deployment. MinIO validates bucket names. To see the rules for bucket names, select **View Bucket Naming Rules**.

MinIO does not limit the total number of buckets allowed on a deployment. However, MinIO recommends no more than 500,000 buckets per deployment as a general guideline.

While creating a bucket, you can enable [versioning](/administration/object-management/object-versioning/#minio-bucket-versioning), [object locking](/administration/object-management/object-retention/#minio-object-locking), bucket size (quota) limits, and [retention rules](/administration/object-management/object-retention/#minio-object-locking-retention-modes) (which require versioning).

{{% alert color="info" %}}
**Changed: Console**

v0.35.0

If you enable versioning, you can specify prefixes to exclude from versioning.
{{% /alert %}}

You **must** configure replication, locking, and versioning options at the time of bucket creation. You cannot change these settings for the bucket later.

### Managing Buckets {#managing-buckets}

Use the **Search** bar to filter for specific buckets. Select the row for the bucket to display summary information about the bucket.

Form the summary screen, select any of the available tabs to further manage the bucket.

{{% alert color="info" %}}
**Note**

Some management features may not be available if the authenticated user does not have the [required administrative permissions](/administration/identity-access-management/policy-based-access-control/#minio-policy-mc-admin-actions).
{{% /alert %}}

When managing a bucket, your access settings may allow you to view or change any of the following:

- The **Summary** section displays a summary of the bucket’s configuration.

  Use this section to view and modify the bucket’s access policy, encryption, quota, and tags.
- Configure alerts in the **Events** section to trigger [notification events](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) when a user uploads, accesses, or deletes matching objects.
- Copy objects to remote locations in the **Replication** section with [Server Side Bucket Replication Rules](/administration/bucket-replication/#minio-bucket-replication-serverside).
- Expire or transition objects in the bucket from the **Lifecycle** section by setting up [Object Lifecycle Management Rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management).
- Review security in the **Access** section by listing the [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) and [users](/administration/identity-access-management/minio-user-management/#minio-users) with access to that bucket.
- Properly secure unauthenticated access with the **Anonymous** section by managing rules for prefixes that unauthenticated users can use to read or write objects.

<a id="minio-console-tiers"></a>

## Tiers {#tiers}

The **Tiering** section provides an interface for adding and managing [remote tiers](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering) to support lifecycle management transition rules. MinIO tiering supports moving objects from the deployment to the remote storage, but does not support automatically restoring them to the deployment.

The tiering tab allows users with the appropriate permissions to:

- Review the status and summary information for all configured remote tiers.
- Create a tier for a new remote target to storage on another MinIO deployment, Google Cloud Storage, Amazon’s AWS S3, or Azure.
- Cycle the access credentials for any of the configured tiers with the tier’s <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-pencil" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M11.013 1.427a1.75 1.75 0 012.474 0l1.086 1.086a1.75 1.75 0 010 2.474l-8.61 8.61c-.21.21-.47.364-.756.445l-3.251.93a.75.75 0 01-.927-.928l.929-3.25a1.75 1.75 0 01.445-.758l8.61-8.61zm1.414 1.06a.25.25 0 00-.354 0L10.811 3.75l1.439 1.44 1.263-1.263a.25.25 0 000-.354l-1.086-1.086zM11.189 6.25L9.75 4.81l-6.286 6.287a.25.25 0 00-.064.108l-.558 1.953 1.953-.558a.249.249 0 00.108-.064l6.286-6.286z"></path></svg> icon.

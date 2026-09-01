---
title: "Access Management"
url: "/administration/identity-access-management/policy-based-access-control/"
weight: 50
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/identity-access-management/policy-based-access-control.rst
upstream_modified: true
---

<a id="access-management"></a>
<a id="minio-policy"></a>

## Overview {#overview}

MinIO uses Policy-Based Access Control (PBAC) to define the authorized actions and resources to which an authenticated user has access. Each policy describes one or more [actions](#minio-policy-actions) and [conditions](#minio-policy-conditions) that outline the permissions of a [user](/administration/identity-access-management/minio-user-management/#minio-users) or [group](/administration/identity-access-management/minio-group-management/#minio-groups) of users.

MinIO PBAC is built for compatibility with AWS IAM policy syntax, structure, and behavior. The MinIO documentation makes a best-effort to cover IAM-specific behavior and functionality. Consider deferring to the [IAM documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/) for more complete documentation on AWS IAM-specific topics.

The [`mc admin policy`](/reference/minio-mc-admin/mc-admin-policy/#command-mc.admin.policy) command supports creation and management of policies on the MinIO deployment. See the command reference for examples of usage.

## Tag-Based Policy Conditions {#tag-based-policy-conditions}

> [!NOTE]
> **Changed: RELEASE.2022-10-02T19-29-29Z**
>
> Policies can use conditions to limit a user’s access only to objects with a [specific tag](/administration/object-management/#minio-object-tagging).
>
> MinIO supports [tag-based conditions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/tagging-and-policies.html) for [selected actions](#minio-selected-conditional-actions). `s3:ExistingObjectTag/<key>` evaluates tags stored on the target object when that API path loads the object metadata before authorization. `s3:RequestObjectTag/<key>` and `s3:RequestObjectTagKeys` are client-supplied request values, not evidence of stored object state. `PutObject`, `CreateMultipartUpload`, and `PutObjectTagging` explicitly bind them to the tag input those handlers consume; other action paths retain the historical `X-Amz-Tagging` Header mapping for compatibility, so use request-tag conditions only where the API actually consumes tags.
>
> Bucket tags are separate from object tags. `PutBucketTagging` does not populate the `s3:RequestObjectTag*` condition keys from its XML body.

<a id="minio-policy-built-in"></a>

## Built-In Policies {#built-in-policies}

MinIO provides the following built-in policies for assigning to [users](/administration/identity-access-management/minio-user-management/#minio-users) or [groups](/administration/identity-access-management/minio-group-management/#minio-groups):

#### `consoleAdmin` {#userpolicy.consoleAdmin}

*userpolicy*

Grants complete access to all S3 and administrative API operations against all resources on the MinIO deployment. Equivalent to the following set of actions:

- [`s3:*`](#policy-action.s3)
- [`admin:*`](#policy-action.admin)

#### `readonly` {#userpolicy.readonly}

*userpolicy*

Grants read-only permissions on any object on the MinIO deployment. The GET action *must* apply to a specific object without requiring any listing. Equivalent to the following set of actions:

- [`s3:GetBucketLocation`](#policy-action.s3-GetBucketLocation)
- [`s3:GetObject`](#policy-action.s3-GetObject)

For example, this policy specifically supports GET operations on objects at a specific path (e.g. `GET play/mybucket/object.file`), such as:

- [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp)
- [`mc stat`](/reference/minio-mc/mc-stat/#command-mc.stat)
- [`mc head`](/reference/minio-mc/mc-head/#command-mc.head)
- [`mc cat`](/reference/minio-mc/mc-cat/#command-mc.cat)

The exclusion of listing permissions is intentional, as typical use cases do not intend for a “read-only” role to have complete discoverability (listing all buckets and objects) on the object storage resource.

#### `readwrite` {#userpolicy.readwrite}

*userpolicy*

Grants read and write permissions for all buckets and objects on the MinIO server. Equivalent to [`s3:*`](#policy-action.s3).

#### `diagnostics` {#userpolicy.diagnostics}

*userpolicy*

Grants permission to perform diagnostic actions on the MinIO deployment. Specifically includes the following actions:

- [`admin:ServerTrace`](#policy-action.admin-ServerTrace)
- [`admin:Profiling`](#policy-action.admin-Profiling)
- [`admin:ConsoleLog`](#policy-action.admin-ConsoleLog)
- [`admin:ServerInfo`](#policy-action.admin-ServerInfo)
- [`admin:TopLocksInfo`](#policy-action.admin-TopLocksInfo)
- [`admin:OBDInfo`](#policy-action.admin-OBDInfo)
- [`admin:BandwidthMonitor`](#policy-action.admin-BandwidthMonitor)
- [`admin:Prometheus`](#policy-action.admin-Prometheus)

#### `writeonly` {#userpolicy.writeonly}

*userpolicy*

Grants write-only permissions to any namespace (bucket and path to object) the MinIO deployment. The PUT action *must* apply to a specific object location without requiring any listing. Equivalent to the [`s3:PutObject`](#policy-action.s3-PutObject) action.

Use [`mc admin policy attach`](/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach) to associate a policy to a user or group on a MinIO deployment.

For example, consider the following table of users. Each user is assigned a [built-in policy](#minio-policy-built-in) or a supported [action](#minio-policy-actions). The table describes a subset of operations a client could perform if authenticated as that user:

<table>
  <thead>
    <tr>
      <th><p>User</p></th>
      <th><p>Policy</p></th>
      <th><p>Operations</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><code>Operations</code></p></td>
      <td><a href="#userpolicy.readwrite"><code>readwrite</code></a> on <code>finance</code> bucket<br /><a href="#userpolicy.readonly"><code>readonly</code></a> on <code>audit</code> bucket<br /></td>
      <td><code>PUT</code> and <code>GET</code> on <code>finance</code> bucket.<br /><code>GET</code> on <code>audit</code> bucket<br /></td>
    </tr>
    <tr>
      <td><p><code>Auditing</code></p></td>
      <td><a href="#userpolicy.readonly"><code>readonly</code></a> on <code>audit</code> bucket<br /></td>
      <td><p><code>GET</code> on <code>audit</code> bucket</p></td>
    </tr>
    <tr>
      <td><p><code>Admin</code></p></td>
      <td><p><a href="#policy-action.admin"><code>admin:*</code></a></p></td>
      <td><p>All <a href="/reference/minio-mc-admin/#command-mc.admin"><code>mc admin</code></a> commands.</p></td>
    </tr>
  </tbody>
</table>

Each user can access only those resources and operations which are *explicitly* granted by the built-in role. MinIO denies access to any other resource or action by default.

> [!NOTE]
> **`Deny` overrides `Allow`**
>
> MinIO follows the IAM policy evaluation rules where a `Deny` rule overrides `Allow` rule on the same action/resource. For example, if a user has an explicitly assigned policy with an `Allow` rule for an action/resource while one of its groups has an assigned policy with a `Deny` rule for that action/resource, MinIO would apply only the `Deny` rule.
>
> For more information on IAM policy evaluation logic, see the IAM documentation on [Determining Whether a Request is Allowed or Denied Within an Account](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html#policy-eval-denyallow).

<a id="minio-policy-document"></a>

## Policy Document Structure {#policy-document-structure}

MinIO policy documents use the same schema as [AWS IAM Policy](https://docs.aws.amazon.com/IAM/latest/UserGuide/access.html) documents.

The following sample document provides a template for creating custom policies for use with a MinIO deployment. For more complete documentation on IAM policy elements, see the [IAM JSON Policy Elements Reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html).

The maximum size for any single policy document is 20KiB. There is no limit to the number of policy documents that can be attached to a user or group.

```javascript
{
   "Version" : "2012-10-17",
   "Statement" : [
      {
         "Effect" : "Allow",
         "Action" : [ "s3:<ActionName>", ... ],
         "Resource" : "arn:aws:s3:::*",
         "Condition" : { ... }
      },
      {
         "Effect" : "Deny",
         "Action" : [ "s3:<ActionName>", ... ],
         "Resource" : "arn:aws:s3:::*",
         "Condition" : { ... }
      }
   ]
}
```

- For the `Statement.Action` array, specify one or more [supported S3 API operations](#minio-policy-actions).
- For the `Statement.Resource` key, specify the bucket or bucket prefix to which to restrict the policy. You can use `*` and `?` wildcard characters as per the [S3 Resource Spec](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-arn-format.html).

  The `*` wildcard may result in unintended application of a policy to multiple buckets or prefixes based on the [pattern match](/reference/minio-mc/#minio-wildcard-matching). For example, `arn:aws:s3:::data*` would match the buckets `data`, `data_private`, and `data_internal`. Specifying only `*` as the resource key applies the policy to all buckets and prefixes on the deployment.

  An object pattern and a bucket ARN are **not** interchangeable. See [Bucket and Object Resources](#bucket-and-object-resources).
- For the `Statement.Condition` key, you can specify one or more [supported Conditions](#minio-policy-conditions).

### Bucket and Object Resources {#bucket-and-object-resources}

A resource ARN either names a bucket or names objects within it, and the two forms authorize different operations:

- `arn:aws:s3:::mybucket` names **the bucket itself**, and authorizes bucket-level operations such as `ListBucket` or `PutBucketPolicy`.
- `arn:aws:s3:::mybucket/*` names **the objects in the bucket**, and authorizes object operations such as `GetObject` or `PutObject`.

Grant both when a principal needs both, which is the conventional form for a policy that manages a bucket and its contents:

```json
"Resource": ["arn:aws:s3:::mybucket", "arn:aws:s3:::mybucket/*"]
```

> [!WARNING]
> **Twelve bucket-level writes require the bucket ARN**
>
> An object-only pattern such as `arn:aws:s3:::mybucket/*` does **not** authorize the following actions, even when the statement grants `s3:*`:
>
> `PutBucketPolicy`, `DeleteBucketPolicy`, `PutBucketObjectLockConfiguration`, `PutBucketVersioning`, `PutReplicationConfiguration`, `PutLifecycleConfiguration`, `DeleteBucket`, `ForceDeleteBucket`, `PutBucketCors`, `DeleteBucketCors`, `PutBucketQOS`, `PutInventoryConfiguration`
>
> Each of these hands the caller something an object-scoped grant does not otherwise provide — access for other principals, defeat of a protection aimed at write-holders, activity that outlives the grant, or destruction of the bucket entity. Add the bare bucket ARN alongside the object pattern to grant them.
>
> Earlier releases authorized these through the object pattern as well, because a bucket-level request was matched against the string `mybucket/`, which `mybucket/*` also matches. That was an over-grant; see upstream [minio/minio#20449](https://github.com/minio/minio/issues/20449). Set [`MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH`](/reference/minio-server/settings/core/#envvar.MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH) to `on` to restore the previous behaviour while you adjust policies.

Everything else is unchanged. `ListBucket`, `GetBucketLocation`, the bucket configuration *reads*, and `CreateBucket` are still authorized through an object pattern, so listing and provisioning flows written that way keep working. `Deny` statements and `NotResource` exclusions match as they always did, so no restriction written against `mybucket/*` is weakened. The built-in `readwrite`, `readonly`, `writeonly` and `diagnostics` policies use `arn:aws:s3:::*` and are unaffected.

<a id="minio-policy-actions"></a>

## Supported S3 Policy Actions {#supported-s3-policy-actions}

MinIO policy documents support a subset of IAM [S3 Action keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/list_amazons3.html#amazons3-actions-as-permissions). This section also includes any [condition keys](#minio-policy-conditions) supported by a specific action beyond the common set of supported keys.

The following actions control access to common S3 operations. The remaining subsections document actions for more advanced S3 operations:

<a id="policy-action.s3:*"></a>

#### `s3:*` {#policy-action.s3}

*policy-action*

Selector for *all* MinIO S3 operations. Applying this action to a given resource allows the user to perform *any* S3 operation against that resource.

<a id="policy-action.s3:CreateBucket"></a>

#### `s3:CreateBucket` {#policy-action.s3-CreateBucket}

*policy-action*

Controls access to the [CreateBucket](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CreateBucket.html) S3 API operation.

<a id="policy-action.s3:DeleteBucket"></a>

#### `s3:DeleteBucket` {#policy-action.s3-DeleteBucket}

*policy-action*

Controls access to the [DeleteBucket](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucket.html) S3 API operation.

<a id="policy-action.s3:ForceDeleteBucket"></a>

#### `s3:ForceDeleteBucket` {#policy-action.s3-ForceDeleteBucket}

*policy-action*

Controls access to the [DeleteBucket](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucket.html) S3 API operation for operations with the `x-minio-force-delete` flag. Required for removing non-empty buckets.

<a id="policy-action.s3:GetBucketLocation"></a>

#### `s3:GetBucketLocation` {#policy-action.s3-GetBucketLocation}

*policy-action*

Controls access to the [GetBucketLocation](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketLocation.html) S3 API operation.

<a id="policy-action.s3:ListAllMyBuckets"></a>

#### `s3:ListAllMyBuckets` {#policy-action.s3-ListAllMyBuckets}

*policy-action*

Controls access to the [ListBuckets](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListBuckets.html) S3 API operation.

<a id="policy-action.s3:DeleteObject"></a>

#### `s3:DeleteObject` {#policy-action.s3-DeleteObject}

*policy-action*

Controls access to the [DeleteObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObject.html) S3 API operation.

This action authorizes a delete request that does not explicitly name a
version. On a versioned bucket, that request creates a delete marker. It does
not authorize `DELETE ?versionId=...` or a `DeleteObjects` entry containing
`VersionId`.

Supports the following additional [condition key](#minio-policy-conditions):

```shell
s3:versionid
```

<a id="policy-action.s3:GetObject"></a>

#### `s3:GetObject` {#policy-action.s3-GetObject}

*policy-action*

Controls access to the [GetObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html) S3 API operation.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:x-amz-server-side-encryption
s3:x-amz-server-side-encryption-customer-algorithm
s3:x-amz-server-side-encryption-aws-kms-key-id
s3:ExistingObjectTag/<key>
s3:versionid
```

<a id="policy-action.s3:GetObjectAttributes"></a>

#### `s3:GetObjectAttributes` {#policy-action.s3-GetObjectAttributes}

*policy-action*

Controls access to the [GetObjectAttributes](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectAttributes.html) S3 API operation.

The policy parser admits the following condition key for this action:

```shell
s3:ExistingObjectTag/<key>
```

The current handler authorizes before it loads object metadata, however, so that condition value is absent for this operation.

<a id="policy-action.s3:GetObjectVersionAttributes"></a>

#### `s3:GetObjectVersionAttributes` {#policy-action.s3-GetObjectVersionAttributes}

*policy-action*

Controls access to the [GetObjectAttributes](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectAttributes.html) S3 API operations on versioned objects.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:ExistingObjectTag/<key>
```

The version ID comes from the request query. The current handler authorizes before it loads object metadata, so `s3:ExistingObjectTag/<key>` is admitted by the policy parser but absent at evaluation time for this operation.

<a id="policy-action.s3:RestoreObject"></a>

#### `s3:RestoreObject` {#policy-action.s3-RestoreObject}

*policy-action*

Controls access to the [RestoreObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_RestoreObject.html) S3 API operation.

<a id="policy-action.s3:ListBucket"></a>

#### `s3:ListBucket` {#policy-action.s3-ListBucket}

*policy-action*

Controls access to the [ListObjectsV2](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html) S3 API operation.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:prefix
s3:delimiter
s3:max-keys
```

<a id="policy-action.s3:PutObject"></a>

#### `s3:PutObject` {#policy-action.s3-PutObject}

*policy-action*

Controls access to the [PutObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html) S3 API operation.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:x-amz-copy-source
s3:x-amz-server-side-encryption
s3:x-amz-server-side-encryption-customer-algorithm
s3:x-amz-server-side-encryption-aws-kms-key-id
s3:x-amz-metadata-directive
s3:x-amz-storage-class
s3:versionid
s3:object-lock-retain-until-date
s3:object-lock-mode
s3:object-lock-legal-hold
s3:RequestObjectTagKeys
s3:RequestObjectTag/<key>
```

<a id="policy-action.s3:PutObjectTagging"></a>

#### `s3:PutObjectTagging` {#policy-action.s3-PutObjectTagging}

*policy-action*

Controls access to the [PutObjectTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectTagging.html) S3 API operation.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:ExistingObjectTag/<key>
s3:RequestObjectTagKeys
s3:RequestObjectTag/<key>
```

<a id="policy-action.s3:GetObjectTagging"></a>

#### `s3:GetObjectTagging` {#policy-action.s3-GetObjectTagging}

*policy-action*

Controls access to the [GetObjectTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectTagging.html) S3 API operation.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:ExistingObjectTag/<key>
```

<a id="policy-action.s3:DeleteObjectTagging"></a>

#### `s3:DeleteObjectTagging` {#policy-action.s3-DeleteObjectTagging}

*policy-action*

Controls access to the [DeleteObjectTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObjectTagging.html) S3 API operation.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:ExistingObjectTag/<key>
```

### Bucket Configuration {#bucket-configuration}

<a id="policy-action.s3:GetBucketPolicy"></a>

##### `s3:GetBucketPolicy` {#policy-action.s3-GetBucketPolicy}

*policy-action*

Controls access to the [GetBucketPolicy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketPolicy.html) S3 API operation.

<a id="policy-action.s3:PutBucketPolicy"></a>

##### `s3:PutBucketPolicy` {#policy-action.s3-PutBucketPolicy}

*policy-action*

Controls access to the [PutBucketPolicy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketPolicy.html) S3 API operation.

<a id="policy-action.s3:DeleteBucketPolicy"></a>

##### `s3:DeleteBucketPolicy` {#policy-action.s3-DeleteBucketPolicy}

*policy-action*

Controls access to the [DeleteBucketPolicy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketPolicy.html) S3 API operation.

<a id="policy-action.s3:GetBucketTagging"></a>

##### `s3:GetBucketTagging` {#policy-action.s3-GetBucketTagging}

*policy-action*

Controls access to the [GetBucketTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketTagging.html) S3 API operation.

<a id="policy-action.s3:PutBucketTagging"></a>

##### `s3:PutBucketTagging` {#policy-action.s3-PutBucketTagging}

*policy-action*

Controls access to the [PutBucketTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketTagging.html) S3 API operation.

The policy parser retains the following condition keys for compatibility:

```shell
s3:RequestObjectTagKeys
s3:RequestObjectTag/<key>
```

The handler does **not** populate them from the bucket-tagging XML body. Only the historical, client-supplied `X-Amz-Tagging` Header fallback can populate them, and that Header does not constrain the bucket tags stored from the body. Do not use these keys to enforce the contents of a `PutBucketTagging` request.

<a id="policy-action.s3:GetBucketPolicyStatus"></a>

##### `s3:GetBucketPolicyStatus` {#policy-action.s3-GetBucketPolicyStatus}

*policy-action*

Controls access to the [GetBucketPolicyStatus](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketPolicyStatus.html) S3 API operation.

### Multipart Upload {#multipart-upload}

<a id="policy-action.s3:AbortMultipartUpload"></a>

##### `s3:AbortMultipartUpload` {#policy-action.s3-AbortMultipartUpload}

*policy-action*

Controls access to the [AbortMultipartUpload](https://docs.aws.amazon.com/AmazonS3/latest/API/API_AbortMultipartUpload.html) S3 API operation.

<a id="policy-action.s3:ListMultipartUploadParts"></a>

##### `s3:ListMultipartUploadParts` {#policy-action.s3-ListMultipartUploadParts}

*policy-action*

Controls access to the [ListParts](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListParts.html) S3 API operation.

<a id="policy-action.s3:ListBucketMultipartUploads"></a>

##### `s3:ListBucketMultipartUploads` {#policy-action.s3-ListBucketMultipartUploads}

*policy-action*

Controls access to the [ListMultipartUploads](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListMultipartUploads.html) S3 API operation.

### Versioning and Retention {#versioning-and-retention}

<a id="policy-action.s3:PutBucketVersioning"></a>

##### `s3:PutBucketVersioning` {#policy-action.s3-PutBucketVersioning}

*policy-action*

Controls access to the [PutBucketVersioning](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketVersioning.html) S3 API operation.

<a id="policy-action.s3:GetBucketVersioning"></a>

##### `s3:GetBucketVersioning` {#policy-action.s3-GetBucketVersioning}

*policy-action*

Controls access to the [GetBucketVersioning](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketVersioning.html) S3 API operation.

<a id="policy-action.s3:DeleteObjectVersion"></a>

##### `s3:DeleteObjectVersion` {#policy-action.s3-DeleteObjectVersion}

*policy-action*

Controls access to the [DeleteObjectVersion](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObjectVersion.html) S3 API operation.

This action authorizes deletion of an explicitly named UUID or the explicit
`null` version. In `DeleteObjects`, SILO evaluates this action independently for
each entry that contains `VersionId`.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
```

<a id="policy-action.s3:ListBucketVersions"></a>

##### `s3:ListBucketVersions` {#policy-action.s3-ListBucketVersions}

*policy-action*

Controls access to the [ListBucketVersions](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListBucketVersions.html) S3 API operation.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:prefix
s3:delimiter
s3:max-keys
```

<a id="policy-action.s3:PutObjectVersionTagging"></a>

##### `s3:PutObjectVersionTagging` {#policy-action.s3-PutObjectVersionTagging}

*policy-action*

Controls access to the [PutObjectVersionTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectVersionTagging.html) S3 API operation.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:ExistingObjectTag/<key>
s3:RequestObjectTagKeys
s3:RequestObjectTag/<key>
```

<a id="policy-action.s3:GetObjectVersionTagging"></a>

##### `s3:GetObjectVersionTagging` {#policy-action.s3-GetObjectVersionTagging}

*policy-action*

Controls access to the [GetObjectVersionTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectVersionTagging.html) S3 API operation.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:ExistingObjectTag/<key>
```

<a id="policy-action.s3:DeleteObjectVersionTagging"></a>

##### `s3:DeleteObjectVersionTagging` {#policy-action.s3-DeleteObjectVersionTagging}

*policy-action*

Controls access to the [DeleteObjectVersionTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObjectVersionTagging.html) S3 API operation.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:ExistingObjectTag/<key>
```

<a id="policy-action.s3:GetObjectVersion"></a>

##### `s3:GetObjectVersion` {#policy-action.s3-GetObjectVersion}

*policy-action*

Controls access to the [GetObjectVersion](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectVersion.html) S3 API operation.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:ExistingObjectTag/<key>
```

<a id="policy-action.s3:BypassGovernanceRetention"></a>

##### `s3:BypassGovernanceRetention` {#policy-action.s3-BypassGovernanceRetention}

*policy-action*

Controls access to the following S3 API operations on objects locked under [`GOVERNANCE`](/reference/minio-mc/mc-retention-set/#mc.retention.set.MODE) retention mode:

- `s3:PutObjectRetention`
- `s3:PutObject`
- `s3:DeleteObject`

See the S3 documentation on [s3:BypassGovernanceRetention](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-managing.html#object-lock-managing-bypass) for more information.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:object-lock-remaining-retention-days
s3:object-lock-retain-until-date
s3:object-lock-mode
s3:object-lock-legal-hold
s3:RequestObjectTagKeys
s3:RequestObjectTag/<key>
```

<a id="policy-action.s3:PutObjectRetention"></a>

##### `s3:PutObjectRetention` {#policy-action.s3-PutObjectRetention}

*policy-action*

Controls access to the [PutObjectRetention](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectRetention.html) S3 API operation.

Required for any `PutObject` operation that specifies [retention metadata](/administration/object-management/object-retention/#minio-object-locking).

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:x-amz-server-side-encryption
s3:x-amz-server-side-encryption-customer-algorithm
s3:x-amz-server-side-encryption-aws-kms-key-id
s3:object-lock-remaining-retention-days
s3:object-lock-retain-until-date
s3:object-lock-mode
s3:versionid
```

<a id="policy-action.s3:GetObjectRetention"></a>

##### `s3:GetObjectRetention` {#policy-action.s3-GetObjectRetention}

*policy-action*

Controls access to the [GetObjectRetention](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectRetention.html) S3 API operation.

Required for including [object locking metadata](/administration/object-management/object-retention/#minio-object-locking) as part of the response to a `GetObject` or `HeadObject` operation.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:x-amz-server-side-encryption
s3:x-amz-server-side-encryption-customer-algorithm
s3:x-amz-server-side-encryption-aws-kms-key-id
s3:versionid
```

<a id="policy-action.s3:GetObjectLegalHold"></a>

##### `s3:GetObjectLegalHold` {#policy-action.s3-GetObjectLegalHold}

*policy-action*

Controls access to the [GetObjectLegalHold](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectLegalHold.html) S3 API operation.

Required for including [object locking metadata](/administration/object-management/object-retention/#minio-object-locking) as part of the response to a `GetObject` or `HeadObject` operation.

<a id="policy-action.s3:PutObjectLegalHold"></a>

##### `s3:PutObjectLegalHold` {#policy-action.s3-PutObjectLegalHold}

*policy-action*

Controls access to the [PutObjectLegalHold](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectLegalHold.html) S3 API operation.

Required for any `PutObject` operation that specifies [legal hold metadata](/administration/object-management/object-retention/#minio-object-locking).

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:x-amz-server-side-encryption
s3:x-amz-server-side-encryption-customer-algorithm
s3:x-amz-server-side-encryption-aws-kms-key-id
s3:object-lock-legal-hold
s3:versionid
```

<a id="policy-action.s3:GetBucketObjectLockConfiguration"></a>

##### `s3:GetBucketObjectLockConfiguration` {#policy-action.s3-GetBucketObjectLockConfiguration}

*policy-action*

Controls access to the [GetObjectLockConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectLockConfiguration.html) S3 API operation.

<a id="policy-action.s3:PutBucketObjectLockConfiguration"></a>

##### `s3:PutBucketObjectLockConfiguration` {#policy-action.s3-PutBucketObjectLockConfiguration}

*policy-action*

Controls access to the [PutObjectLockConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectLockConfiguration.html) S3 API operation.

### Bucket Notifications {#bucket-notifications}

<a id="policy-action.s3:GetBucketNotification"></a>

##### `s3:GetBucketNotification` {#policy-action.s3-GetBucketNotification}

*policy-action*

Controls access to the [GetBucketNotification](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketNotification.html) S3 API operation.

<a id="policy-action.s3:PutBucketNotification"></a>

##### `s3:PutBucketNotification` {#policy-action.s3-PutBucketNotification}

*policy-action*

Controls access to the [PutBucketNotification](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketNotification.html) S3 API operation.

<a id="policy-action.s3:ListenNotification"></a>

##### `s3:ListenNotification` {#policy-action.s3-ListenNotification}

*policy-action*

MinIO Extension for controlling API operations related to MinIO Bucket Notifications.

This action is **not** intended for use with other S3-compatible services.

<a id="policy-action.s3:ListenBucketNotification"></a>

##### `s3:ListenBucketNotification` {#policy-action.s3-ListenBucketNotification}

*policy-action*

MinIO Extension for controlling API operations related to MinIO Bucket Notifications.

This action is **not** intended for use with other S3-compatible services.

### Object Lifecycle Management {#object-lifecycle-management}

<a id="policy-action.s3:PutLifecycleConfiguration"></a>

##### `s3:PutLifecycleConfiguration` {#policy-action.s3-PutLifecycleConfiguration}

*policy-action*

Controls access to the [PutLifecycleConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycleConfiguration.html) S3 API operation.

<a id="policy-action.s3:GetLifecycleConfiguration"></a>

##### `s3:GetLifecycleConfiguration` {#policy-action.s3-GetLifecycleConfiguration}

*policy-action*

Controls access to the [GetLifecycleConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketLifecycleConfiguration.html) S3 API operation.

### Object Encryption {#object-encryption}

<a id="policy-action.s3:PutEncryptionConfiguration"></a>

##### `s3:PutEncryptionConfiguration` {#policy-action.s3-PutEncryptionConfiguration}

*policy-action*

Controls access to the [PutEncryptionConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketEncryption.html) S3 API operation.

<a id="policy-action.s3:GetEncryptionConfiguration"></a>

##### `s3:GetEncryptionConfiguration` {#policy-action.s3-GetEncryptionConfiguration}

*policy-action*

Controls access to the [GetEncryptionConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketEncryption.html) S3 API operation.

### Bucket Replication {#bucket-replication}

<a id="policy-action.s3:GetReplicationConfiguration"></a>

##### `s3:GetReplicationConfiguration` {#policy-action.s3-GetReplicationConfiguration}

*policy-action*

Controls access to the [GetBucketReplication](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketReplication.html) S3 API operation.

<a id="policy-action.s3:PutReplicationConfiguration"></a>

##### `s3:PutReplicationConfiguration` {#policy-action.s3-PutReplicationConfiguration}

*policy-action*

Controls access to the [PutBucketReplication](https://docs.aws.amazon.com/AmazonS3/latest/API/PutBucketReplication.html) S3 API operation.

<a id="policy-action.s3:ReplicateObject"></a>

##### `s3:ReplicateObject` {#policy-action.s3-ReplicateObject}

*policy-action*

MinIO Extension for controlling API operations related to [Server-Side Bucket Replication](/administration/bucket-replication/#minio-bucket-replication-serverside).

Required for MinIO server-side replication.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:ExistingObjectTag/<key>
```

<a id="policy-action.s3:ReplicateDelete"></a>

##### `s3:ReplicateDelete` {#policy-action.s3-ReplicateDelete}

*policy-action*

MinIO Extension for controlling API operations related to [Server-Side Bucket Replication](/administration/bucket-replication/#minio-bucket-replication-serverside).

Required for synchronizing [delete operations](/administration/object-management/object-delete/#minio-object-delete) as part of MinIO server-side replication.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:ExistingObjectTag/<key>
```

<a id="policy-action.s3:ReplicateTags"></a>

##### `s3:ReplicateTags` {#policy-action.s3-ReplicateTags}

*policy-action*

MinIO Extension for controlling API operations related to [Server-Side Bucket Replication](/administration/bucket-replication/#minio-bucket-replication-serverside).

Required for MinIO server-side replication.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:ExistingObjectTag/<key>
```

<a id="policy-action.s3:GetObjectVersionForReplication"></a>

##### `s3:GetObjectVersionForReplication` {#policy-action.s3-GetObjectVersionForReplication}

*policy-action*

MinIO Extension for controlling API operations related to [Server-Side Bucket Replication](/administration/bucket-replication/#minio-bucket-replication-serverside).

Required for MinIO server-side replication.

Supports the following additional [condition keys](#minio-policy-conditions):

```shell
s3:versionid
s3:ExistingObjectTag/<key>
```

<a id="minio-selected-conditional-actions"></a>
<a id="minio-policy-conditions"></a>

## Supported S3 Policy Condition Keys {#supported-s3-policy-condition-keys}

MinIO policy documents support IAM [conditional statements](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition.html).

Each condition element consists of [operators](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition_operators.html) and condition keys. MinIO supports a subset of IAM condition keys. For complete information on any listed condition key, see the [IAM Condition Element Documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition.html)

MinIO supports the following condition keys for all supported [actions](#minio-policy-actions):

- `aws:Referer`
- `aws:SourceIp`
- `aws:UserAgent`
- `aws:SecureTransport`
- `aws:CurrentTime`
- `aws:EpochTime`
- `aws:PrincipalType`
- `aws:userid`
- `aws:username`
- `s3:x-amz-content-sha256`
- `s3:signatureAge`

> [!CAUTION]
> **Warning**
>
> The `aws:Referer`, `aws:SourceIp`, and `aws:UserAgent` keys may be spoofed and therefore pose a potential security risk. `aws:SourceIp` is only as trustworthy as the proxy boundary that supplies or overwrites forwarding headers. MinIO recommends only using these condition keys to *deny* access as a secondary security measure.
>
> **Never** use these three keys to grant access by themselves.

### Condition Value Sources and Precedence {#condition-value-sources}

> [!WARNING]
> **Unreleased server behavior (as of 2026-08-03)**
>
> The table below describes behavior after companion server change `1a6d5b415`. That change is present only on the local `pgsty/minio` branch: it is not on public `origin/master`, and the latest published server release (`RELEASE.2026-08-04T00-00-00Z`) does not contain it. Published builds retain the previous behavior. Verify the server release notes before relying on these precedence guarantees.

Silo constructs the condition-value map from semantic request sources instead of treating every header and query parameter as interchangeable. A raw header or query parameter whose name resembles an internal condition key cannot replace a value calculated by the server or create one that the server did not provide.

| Condition family | Source used for policy evaluation | Precedence and compatibility |
| :-- | :-- | :-- |
| Identity, time, transport, authentication, `s3:versionid`, `s3:LocationConstraint`, LDAP, and JWT values | Authenticated credentials and claims, the server clock and transport, or the API field parsed for that operation | Same-named raw headers and query parameters cannot add or replace these values. `aws:Referer` and `aws:UserAgent` remain client-controlled by definition; see the warning above for `aws:SourceIp`. |
| `s3:signatureAge` | Elapsed time calculated by the SigV4 presigned-request verifier | Available only for a verified SigV4 presigned request. A client-supplied `x-amz-signature-age` Header on any other request type is ignored. |
| `s3:prefix`, `s3:delimiter`, `s3:max-keys` | Query string only | A similarly named request header is ignored for these list conditions. |
| `s3:x-amz-content-sha256`, `s3:x-amz-copy-source`, `s3:x-amz-metadata-directive`, and server-side-encryption keys | Their corresponding HTTP headers only | Query-string substitutes do not satisfy these conditions. In particular, the `X-Amz-Content-Sha256` query value used while verifying a presigned request is not exposed as the policy condition value. |
| `s3:x-amz-storage-class` | `X-Amz-Storage-Class` header, with a compatible query-string fallback | Header presence wins even when the header value is empty. The query form remains available for compatibility with existing upload paths. |
| `s3:RequestObjectTag/<key>` and `s3:RequestObjectTagKeys` | The `X-Amz-Tagging` Header by default; an explicitly supplied effective tag set on tag-aware handlers | `PutObject` and `CreateMultipartUpload` accept the Header or their compatible query fallback, with Header presence winning. `PutObjectTagging` uses the parsed XML request body. Query tagging is ignored on unrelated operations. The historical Header fallback remains for compatibility on actions whose policy map admits these keys, so outside the three handlers above a request-tag condition does not by itself prove that the operation consumes or stores those tags. |
| `s3:ExistingObjectTag/<key>` | Tags loaded from the stored target object | Request headers and query parameters never provide existing-object tags. The value is available only on API paths that load those tags before authorization, including object GET/HEAD and object-tagging handlers. |
| Object-lock condition keys | Object-lock request headers or retention values calculated by the handler | Query-string fields with the same names are ignored. |

If an API path does not load or calculate a listed source, that condition key is absent. Its result then follows the semantics of the policy operator in use; do not assume that merely listing a key for an action causes the server to synthesize a value.

For additional keys supported by a specific S3 action, see the reference documentation for that action.

### MinIO Extended Condition Keys {#minio-extended-condition-keys}

MinIO extends the S3 standard condition keys with the following extended key:

`sts:DurationSeconds`

> > [!NOTE]
> > **Added: MinIO**
> >
> > SERVER RELEASE.2024-02-06T21-36-22Z
>
> Specify a time in seconds to limit the duration of *all* Security Token Service credentials generated by [AssumeRoleWithWebIdentity](/developers/security-token-service/AssumeRoleWithWebIdentity/#minio-sts-assumerolewithwebidentity).
>
> This value overrides the `DurationSeconds` field specified to the client.
>
> For example:
>
> ```json
> {
>    "Version": "2012-10-17",
>    "Statement": [
>       {
>             "Effect": "Allow",
>             "Action": [
>                "sts:AssumeRoleWithWebIdentity"
>             ],
>             "Condition": {
>                "NumericLessThanEquals": {
>                   "sts:DurationSeconds": "300"
>                }
>             }
>       }
>    ]
> }
> ```

<a id="minio-policy-mc-admin-actions"></a>

## `mc admin` Policy Action Keys {#mc-admin-policy-action-keys}

MinIO supports the following actions for use with defining policies for [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) operations. These actions are *only* valid for MinIO deployments and are *not* intended for use with other S3-compatible services:

<a id="policy-action.admin:*"></a>

#### `admin:*` {#policy-action.admin}

*policy-action*

Selector for all admin action keys.

<a id="policy-action.admin:Heal"></a>

#### `admin:Heal` {#policy-action.admin-Heal}

*policy-action*

Allows heal command

<a id="policy-action.admin:StorageInfo"></a>

#### `admin:StorageInfo` {#policy-action.admin-StorageInfo}

*policy-action*

Allows listing server info

<a id="policy-action.admin:DataUsageInfo"></a>

#### `admin:DataUsageInfo` {#policy-action.admin-DataUsageInfo}

*policy-action*

Allows listing data usage info

<a id="policy-action.admin:TopLocksInfo"></a>

#### `admin:TopLocksInfo` {#policy-action.admin-TopLocksInfo}

*policy-action*

Allows listing top locks

<a id="policy-action.admin:Profiling"></a>

#### `admin:Profiling` {#policy-action.admin-Profiling}

*policy-action*

Allows profiling

<a id="policy-action.admin:ServerTrace"></a>

#### `admin:ServerTrace` {#policy-action.admin-ServerTrace}

*policy-action*

Allows listing server trace

<a id="policy-action.admin:ConsoleLog"></a>

#### `admin:ConsoleLog` {#policy-action.admin-ConsoleLog}

*policy-action*

Allows listing console logs on terminal

<a id="policy-action.admin:KMSCreateKey"></a>

#### `admin:KMSCreateKey` {#policy-action.admin-KMSCreateKey}

*policy-action*

Allows creating a new KMS master key

While this option is still supported, [`kms:CreateKey`](#policy-action.kms-CreateKey) is preferred.

<a id="policy-action.admin:KMSKeyStatus"></a>

#### `admin:KMSKeyStatus` {#policy-action.admin-KMSKeyStatus}

*policy-action*

Allows getting KMS key status

While this option is still supported, [`kms:KeyStatus`](#policy-action.kms-KeyStatus) is preferred.

<a id="policy-action.admin:ServerInfo"></a>

#### `admin:ServerInfo` {#policy-action.admin-ServerInfo}

*policy-action*

Allows listing server info

<a id="policy-action.admin:OBDInfo"></a>

#### `admin:OBDInfo` {#policy-action.admin-OBDInfo}

*policy-action*

Allows obtaining cluster on-board diagnostics

<a id="policy-action.admin:ServerUpdate"></a>

#### `admin:ServerUpdate` {#policy-action.admin-ServerUpdate}

*policy-action*

Allows MinIO binary update

<a id="policy-action.admin:ServiceRestart"></a>

#### `admin:ServiceRestart` {#policy-action.admin-ServiceRestart}

*policy-action*

Allows restart of MinIO service.

<a id="policy-action.admin:ServiceStop"></a>

#### `admin:ServiceStop` {#policy-action.admin-ServiceStop}

*policy-action*

Allows stopping MinIO service.

<a id="policy-action.admin:ConfigUpdate"></a>

#### `admin:ConfigUpdate` {#policy-action.admin-ConfigUpdate}

*policy-action*

Allows MinIO config management

<a id="policy-action.admin:CreateUser"></a>

#### `admin:CreateUser` {#policy-action.admin-CreateUser}

*policy-action*

Allows creating MinIO user

<a id="policy-action.admin:DeleteUser"></a>

#### `admin:DeleteUser` {#policy-action.admin-DeleteUser}

*policy-action*

Allows deleting MinIO user

<a id="policy-action.admin:ListUsers"></a>

#### `admin:ListUsers` {#policy-action.admin-ListUsers}

*policy-action*

Allows list users permission

<a id="policy-action.admin:EnableUser"></a>

#### `admin:EnableUser` {#policy-action.admin-EnableUser}

*policy-action*

Allows changing a user's target status to `enabled`. This action does **not** authorize changing the target status to `disabled`.

<a id="policy-action.admin:DisableUser"></a>

#### `admin:DisableUser` {#policy-action.admin-DisableUser}

*policy-action*

Allows changing a user's target status to `disabled`. This action does **not** authorize changing the target status to `enabled`.

> [!IMPORTANT]
> SILO authorizes user-status changes by the requested target state: `enabled` requires `admin:EnableUser`, while `disabled` requires `admin:DisableUser`. Roles responsible for both transitions must explicitly receive both actions; the built-in `consoleAdmin` policy already does through `admin:*`. See [One Endpoint, Two Privileges](/blog/design/user-status-permissions/) for the permission matrix, least-privilege policy examples, compatibility guidance, and the design decision behind this strict separation.

<a id="policy-action.admin:GetUser"></a>

#### `admin:GetUser` {#policy-action.admin-GetUser}

*policy-action*

Allows GET permission on user info

<a id="policy-action.admin:AddUserToGroup"></a>

#### `admin:AddUserToGroup` {#policy-action.admin-AddUserToGroup}

*policy-action*

Allows adding user to group permission

<a id="policy-action.admin:RemoveUserFromGroup"></a>

#### `admin:RemoveUserFromGroup` {#policy-action.admin-RemoveUserFromGroup}

*policy-action*

Allows removing user to group permission

<a id="policy-action.admin:GetGroup"></a>

#### `admin:GetGroup` {#policy-action.admin-GetGroup}

*policy-action*

Allows getting group info

<a id="policy-action.admin:ListGroups"></a>

#### `admin:ListGroups` {#policy-action.admin-ListGroups}

*policy-action*

Allows list groups permission

<a id="policy-action.admin:EnableGroup"></a>

#### `admin:EnableGroup` {#policy-action.admin-EnableGroup}

*policy-action*

Allows changing a group's target status to `enabled`. It does not authorize disabling a group. See [User and Group Status Permissions](/blog/design/user-status-permissions/).

<a id="policy-action.admin:DisableGroup"></a>

#### `admin:DisableGroup` {#policy-action.admin-DisableGroup}

*policy-action*

Allows changing a group's target status to `disabled`. It does not authorize enabling a group. Grant both actions when a role manages the complete group lifecycle.

<a id="policy-action.admin:CreatePolicy"></a>

#### `admin:CreatePolicy` {#policy-action.admin-CreatePolicy}

*policy-action*

Allows create policy permission

<a id="policy-action.admin:DeletePolicy"></a>

#### `admin:DeletePolicy` {#policy-action.admin-DeletePolicy}

*policy-action*

Allows delete policy permission

<a id="policy-action.admin:GetPolicy"></a>

#### `admin:GetPolicy` {#policy-action.admin-GetPolicy}

*policy-action*

Allows get policy permission

<a id="policy-action.admin:AttachUserOrGroupPolicy"></a>

#### `admin:AttachUserOrGroupPolicy` {#policy-action.admin-AttachUserOrGroupPolicy}

*policy-action*

Allows attaching a policy to a user/group

<a id="policy-action.admin:ListUserPolicies"></a>

#### `admin:ListUserPolicies` {#policy-action.admin-ListUserPolicies}

*policy-action*

Allows listing user policies

<a id="policy-action.admin:CreateServiceAccount"></a>

#### `admin:CreateServiceAccount` {#policy-action.admin-CreateServiceAccount}

*policy-action*

Allows creating MinIO Access Key

<a id="policy-action.admin:UpdateServiceAccount"></a>

#### `admin:UpdateServiceAccount` {#policy-action.admin-UpdateServiceAccount}

*policy-action*

Allows updating MinIO Access Key

<a id="policy-action.admin:RemoveServiceAccount"></a>

#### `admin:RemoveServiceAccount` {#policy-action.admin-RemoveServiceAccount}

*policy-action*

Allows deleting MinIO Access Key

<a id="policy-action.admin:ListServiceAccounts"></a>

#### `admin:ListServiceAccounts` {#policy-action.admin-ListServiceAccounts}

*policy-action*

Allows listing MinIO Access Key

<a id="policy-action.admin:SetBucketQuota"></a>

#### `admin:SetBucketQuota` {#policy-action.admin-SetBucketQuota}

*policy-action*

Allows setting bucket quota

<a id="policy-action.admin:GetBucketQuota"></a>

#### `admin:GetBucketQuota` {#policy-action.admin-GetBucketQuota}

*policy-action*

Allows getting bucket quota

<a id="policy-action.admin:SetBucketTarget"></a>

#### `admin:SetBucketTarget` {#policy-action.admin-SetBucketTarget}

*policy-action*

Allows setting bucket target

<a id="policy-action.admin:GetBucketTarget"></a>

#### `admin:GetBucketTarget` {#policy-action.admin-GetBucketTarget}

*policy-action*

Allows getting bucket targets

<a id="policy-action.admin:SetTier"></a>

#### `admin:SetTier` {#policy-action.admin-SetTier}

*policy-action*

Allows creating and modifying remote storage tiers using the [`mc ilm tier`](/reference/minio-mc/mc-ilm-tier/#command-mc.ilm.tier) commands.

<a id="policy-action.admin:ListTier"></a>

#### `admin:ListTier` {#policy-action.admin-ListTier}

*policy-action*

Allows listing configured remote storage tiers using the [`mc ilm tier`](/reference/minio-mc/mc-ilm-tier/#command-mc.ilm.tier) commands.

<a id="policy-action.admin:BandwidthMonitor"></a>

#### `admin:BandwidthMonitor` {#policy-action.admin-BandwidthMonitor}

*policy-action*

Allows retrieving metrics related to current bandwidth consumption.

<a id="policy-action.admin:Prometheus"></a>

#### `admin:Prometheus` {#policy-action.admin-Prometheus}

*policy-action*

Allows access to MinIO [metrics](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts). Only required if MinIO requires authentication for scraping metrics.

<a id="policy-action.admin:ListBatchJobs"></a>

#### `admin:ListBatchJobs` {#policy-action.admin-ListBatchJobs}

*policy-action*

Allows access to list the active batch jobs.

<a id="policy-action.admin:DescribeBatchJob"></a>

#### `admin:DescribeBatchJob` {#policy-action.admin-DescribeBatchJob}

*policy-action*

Allows access to the see the definition details of a running batch job.

<a id="policy-action.admin:StartBatchJob"></a>

#### `admin:StartBatchJob` {#policy-action.admin-StartBatchJob}

*policy-action*

Allows user to begin a batch job run.

<a id="policy-action.admin:CancelBatchJob"></a>

#### `admin:CancelBatchJob` {#policy-action.admin-CancelBatchJob}

*policy-action*

Allows user to stop a batch job currently in process.

<a id="policy-action.admin:Rebalance"></a>

#### `admin:Rebalance` {#policy-action.admin-Rebalance}

*policy-action*

Allows access to start, query, or stop a rebalancing of objects across pools with varying free storage space.

## KMS policy action keys {#kms-policy-action-keys}

MinIO supports restricting key management service (KMS) actions by policy.

You can restrict KMS activities in a policy with any of the following KMS actions:

<a id="policy-action.kms:Status"></a>

#### `kms:Status` {#policy-action.kms-Status}

*policy-action*

Check the status of KMS.

<a id="policy-action.kms:Metrics"></a>

#### `kms:Metrics` {#policy-action.kms-Metrics}

*policy-action*

Obtain Prometheus-formatted metrics.

<a id="policy-action.kms:API"></a>

#### `kms:API` {#policy-action.kms-API}

*policy-action*

List supported API endpoints.

<a id="policy-action.kms:Version"></a>

#### `kms:Version` {#policy-action.kms-Version}

*policy-action*

Retrieve the KMS version.

<a id="policy-action.kms:CreateKey"></a>

#### `kms:CreateKey` {#policy-action.kms-CreateKey}

*policy-action*

Create a new KMS key.

<a id="policy-action.kms:ListKeys"></a>

#### `kms:ListKeys` {#policy-action.kms-ListKeys}

*policy-action*

Retrieve a list of existing KMS keys.

<a id="policy-action.kms:KeyStatus"></a>

#### `kms:KeyStatus` {#policy-action.kms-KeyStatus}

*policy-action*

Retrieve the status of a specified KMS key.

To select all of the available kms policy actions, use `kms:*`.

> [!NOTE]
> **Changed: RELEASE.2024-07-16T23-46-41Z**
>
> KMS actions can be restricted by resource or a resource prefix. The wildcard character `*` can be used to apply the KMS action policy to all resources that match the prefix.
>
> For example, the following policy document allows a user to list keys, create new keys, and check the status of keys for any resource that begins with `keys-abc-` or `myuser-`.
>
> ```shell
> {
>     "Version": "2012-10-17",
>     "Statement": [
>         {
>             "Effect": "Allow",
>             "Action": [
>                 "kms:CreateKey",
>                 "kms:KeyStatus",
>                 "kms:ListKeys"
>             ],
>             "Resource": [
>                 "arn:minio:kms:::keys-abc-*",
>                 "arn:minio:kms:::myuser-*"
>             ]
>         }
>     ]
> }
> ```

## `mc admin` Policy Condition Keys {#mc-admin-policy-condition-keys}

MinIO supports the following conditions for use with defining policies for [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) [actions](#minio-policy-mc-admin-actions).

- `aws:Referer`
- `aws:SourceIp`
- `aws:UserAgent`
- `aws:SecureTransport`
- `aws:CurrentTime`
- `aws:EpochTime`

For complete information on any listed condition key, see the [IAM Condition Element Documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition.html).

## Policy Variables {#policy-variables}

MinIO supports using policy variables for automatically substituting context from the authenticated user and/or the operation into the user’s assigned policy or policies. Use the `${POLICYVARIABLE}` format to specify the variable to the policy as part of the `Condition` or `Resource` definition. MinIO policy variables function similarly to [AWS IAM policy elements: Variables and tags](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_variables.html).

Each MinIO [identity provider](/administration/identity-access-management/#minio-authentication-and-identity-management) supports its own set of policy variables:

- [MinIO Policy Variables](#minio-policy-variables-internal)
- [OpenID Policy Variables](#minio-policy-variables-oidc)
- [Active Directory / LDAP Policy Variables](#minio-policy-variables-ad-ldap)

<a id="minio-policy-variables-internal"></a>

### MinIO Policy Variables {#minio-policy-variables}

The following table contains a list of recommended policy variables for use in authorizing [MinIO-managed users](/administration/identity-access-management/minio-identity-management/#minio-internal-idp):

| Variable | Description |
| --- | --- |
| [aws:referrer](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-referer) | The referrer in the HTTP header for the authenticated API call. |
| [aws:SourceIp](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-sourceip) | The source IP in the HTTP header for the authenticated API call. |
| [aws:username](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-username) | The name of the user associated with the authenticated API call. |

For example, the following policy uses variables to substitute the authenticated user’s username as part of the `Resource` field such that the user can only access those prefixes which match their username:

```json
{
"Version": "2012-10-17",
"Statement": [
      {
         "Action": ["s3:ListBucket"],
         "Effect": "Allow",
         "Resource": ["arn:aws:s3:::mybucket"],
         "Condition": {"StringLike": {"s3:prefix": ["${aws:username}/*"]}}
      },
      {
         "Action": [
         "s3:GetObject",
         "s3:PutObject"
         ],
         "Effect": "Allow",
         "Resource": ["arn:aws:s3:::mybucket/${aws:username}/*"]
      }
   ]
}
```

MinIO replaces the `${aws:username}` variable in the `Resource` field with the username. MinIO then evaluates the policy and grants or revokes access to the requested API and resource.

<a id="minio-policy-variables-oidc"></a>

### OpenID Policy Variables {#openid-policy-variables}

The following table contains a list of supported policy variables for use in authorizing [OIDC-managed users](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid).

Each variable corresponds to a claim returned as part of the authenticated user’s JWT token:

| Variable | Description |
| --- | --- |
| `jwt:sub` | Returns the `sub` claim for the user. |
| `jwt:iss` | Returns the Issuer Identifier claim from the ID token. |
| `jwt:aud` | Returns the Audience claim from the ID token. |
| `jwt:jti` | Returns the JWT ID claim from the client authentication information. |
| `jwt:upn` | Returns the User Principal Name claim from the client authentication information. |
| `jwt:name` | Returns the `name` claim for the user. |
| `jwt:groups` | Returns the `groups` claim for the user. |
| `jwt:given_name` | Returns the `given_name` claim for the user. |
| `jwt:family_name` | Returns the `family_name` claim for the user. |
| `jwt:middle_name` | Returns the `middle_name` claim for the user. |
| `jwt:nickname` | Returns the `nickname` claim for the user. |
| `jwt:preferred_username` | Returns the `preferred_username` claim for the user. |
| `jwt:profile` | Returns the `profile` claim for the user. |
| `jwt:picture` | Returns the `picture` claim for the user. |
| `jwt:website` | Returns the `website` claim for the user. |
| `jwt:email` | Returns the `email` claim for the user. |
| `jwt:gender` | Returns the `gender` claim for the user. |
| `jwt:birthdate` | Returns the `birthdate` claim for the user. |
| `jwt:phone_number` | Returns the `phone_number` claim for the user. |
| `jwt:address` | Returns the `address` claim for the user. |
| `jwt:scope` | Returns the `scope` claim for the user. |
| `jwt:client_id` | Returns the `client_id` claim for the user. |

See the [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html) document for more information on these scopes. Your OIDC provider of choice may have more specific documentation.

For example, the following policy uses variables to substitute the authenticated user’s `preferred_username` as part of the `Resource` field such that the user can only access those prefixes which match their username:

```json
{
"Version": "2012-10-17",
"Statement": [
      {
         "Action": ["s3:ListBucket"],
         "Effect": "Allow",
         "Resource": ["arn:aws:s3:::mybucket"],
         "Condition": {"StringLike": {"s3:prefix": ["${jwt:preferred_username}/*"]}}
      },
      {
         "Action": [
         "s3:GetObject",
         "s3:PutObject"
         ],
         "Effect": "Allow",
         "Resource": ["arn:aws:s3:::mybucket/${jwt:preferred_username}/*"]
      }
   ]
}
```

MinIO replaces the `${jwt:preferred_username}` variable in the `Resource` field with the value of the `preferred_username` in the JWT token. MinIO then evaluates the policy and grants or revokes access to the requested API and resource.

<a id="minio-policy-variables-ad-ldap"></a>

### Active Directory / LDAP Policy Variables {#active-directory-ldap-policy-variables}

The following table contains a list of supported policy variables for use in authorizing [AD/LDAP users](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap):

<table>
  <thead>
    <tr>
      <th><p>Variable</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><code>ldap:username</code></p></td>
      <td>The simple username (<code>name</code>) for the authenticated user.<p>This is distinct from the user’s DistinguishedName or CommonName.</p></td>
    </tr>
    <tr>
      <td><p><code>ldap:user</code></p></td>
      <td><p>The Distinguished Name used by the authenticated user.</p></td>
    </tr>
    <tr>
      <td><p><code>ldap:groups</code></p></td>
      <td><p>The Group Distinguished Name for the authenticated user.</p></td>
    </tr>
  </tbody>
</table>

For example, the following policy uses variables to substitute the authenticated user’s `name` as part of the `Resource` field such that the user can only access those prefixes which match their name:

```json
{
"Version": "2012-10-17",
"Statement": [
      {
         "Action": ["s3:ListBucket"],
         "Effect": "Allow",
         "Resource": ["arn:aws:s3:::mybucket"],
         "Condition": {"StringLike": {"s3:prefix": ["${ldap:username}/*"]}}
      },
      {
         "Action": [
         "s3:GetObject",
         "s3:PutObject"
         ],
         "Effect": "Allow",
         "Resource": ["arn:aws:s3:::mybucket/${ldap:username}/*"]
      }
   ]
}
```

MinIO replaces the `${ldap:username}` variable in the `Resource` field with the value of the authenticated user’s `name`. MinIO then evaluates the policy and grants or revokes access to the requested API and resource.

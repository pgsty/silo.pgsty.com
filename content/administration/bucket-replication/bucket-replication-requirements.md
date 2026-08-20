---
title: "Requirements to Set Up Bucket Replication"
url: "/administration/bucket-replication/bucket-replication-requirements/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/bucket-replication/bucket-replication-requirements.rst
upstream_modified: true
---

<a id="requirements-to-set-up-bucket-replication"></a>
<a id="minio-bucket-replication-requirements"></a>

Bucket replication uses rules to synchronize the contents of a bucket on one MinIO deployment to a bucket on a remote MinIO deployment.

Replication can be done in any of the following ways:

- [Active-Passive](/administration/bucket-replication/enable-server-side-one-way-bucket-replication/#minio-bucket-replication-serverside-oneway) Eligible objects replicate from the source bucket to the remote bucket. Any changes on the remote bucket do not replicate back.
- [Active-Active](/administration/bucket-replication/enable-server-side-two-way-bucket-replication/#minio-bucket-replication-serverside-twoway) Changes to eligible objects of either bucket replicate to the other bucket in a two-way direction.
- [Multi-Site Active-Active](/administration/bucket-replication/enable-server-side-multi-site-bucket-replication/#minio-bucket-replication-serverside-multi) Changes to eligible objects on any bucket set up for bucket replication replicate to all of the other buckets.

Ensure you meet the following prerequisites before you set up any of these replication configurations.

<a id="minio-bucket-replication-serverside-oneway-permissions"></a>

## Permissions Required for Setting Up Bucket Replication {#permissions-required-for-setting-up-bucket-replication}

Bucket replication requires specific permissions on the source and destination deployments to configure and enable replication rules.

{{< tabs group="replication-admin-replication-remote-user" >}}
{{< tab label="Replication Admin" value="replication-admin" >}}
The following policy provides permissions for configuring and enabling replication on a deployment.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "admin:SetBucketTarget",
                "admin:GetBucketTarget",
                "admin:ListBatchJobs",
                "admin:DescribeBatchJob",
                "admin:StartBatchJob",
                "admin:CancelBatchJob"
            ],
            "Effect": "Allow",
            "Sid": "EnableRemoteBucketConfiguration"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetReplicationConfiguration",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads",
                "s3:GetBucketLocation",
                "s3:GetBucketVersioning",
                "s3:GetObjectRetention",
                "s3:GetObjectLegalHold",
                "s3:PutReplicationConfiguration"
            ],
            "Resource": [
                "arn:aws:s3:::*"
            ],
            "Sid": "EnableReplicationRuleConfiguration"
        }
    ]
}

```

- The `"EnableRemoteBucketConfiguration"` statement grants permission for creating a remote target for supporting replication.
- The `"EnableReplicationRuleConfiguration"` statement grants permission for creating replication rules on a bucket. The `"arn:aws:s3:::*` resource applies the replication permissions to *any* bucket on the source deployment. You can restrict the user policy to specific buckets as-needed.

The following code creates a [MinIO-managed user](/administration/identity-access-management/minio-user-management/#minio-users) with the necessary policy. Replace the `TARGET` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment on which you are configuring replication:

```shell
wget -O - https://silo.pgsty.com/extra/examples/ReplicationAdminPolicy.json | \
mc admin policy create TARGET ReplicationAdminPolicy /dev/stdin
mc admin user add TARGET ReplicationAdmin LongRandomSecretKey
mc admin policy attach TARGET ReplicationAdminPolicy --user=ReplicationAdmin
```

MinIO deployments configured for [Active Directory/LDAP](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap) or [OpenID Connect](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid) user management should instead create a dedicated [access keys](/administration/identity-access-management/minio-user-management/#minio-idp-service-account) for bucket replication.
{{< /tab >}}
{{< tab label="Replication Remote User" value="replication-remote-user" >}}
The following policy provides permissions for enabling synchronization of replicated data *into* the deployment.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetReplicationConfiguration",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads",
                "s3:GetBucketLocation",
                "s3:GetBucketVersioning",
                "s3:GetBucketObjectLockConfiguration",
                "s3:GetEncryptionConfiguration"
            ],
            "Resource": [
                "arn:aws:s3:::*"
            ],
            "Sid": "EnableReplicationOnBucket"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetReplicationConfiguration",
                "s3:ReplicateTags",
                "s3:AbortMultipartUpload",
                "s3:GetObject",
                "s3:GetObjectVersion",
                "s3:GetObjectVersionTagging",
                "s3:PutObject",
                "s3:PutObjectRetention",
                "s3:PutBucketObjectLockConfiguration",
                "s3:PutObjectLegalHold",
                "s3:DeleteObject",
                "s3:ReplicateObject",
                "s3:ReplicateDelete"
            ],
            "Resource": [
                "arn:aws:s3:::*"
            ],
            "Sid": "EnableReplicatingDataIntoBucket"
        }
    ]
}
```

- The `"EnableReplicationOnBucket"` statement grants permission for a remote target to retrieve bucket-level configuration for supporting replication operations on *all* buckets in the MinIO deployment. To restrict the policy to specific buckets, specify those buckets as an element in the `Resource` array similar to `"arn:aws:s3:::bucketName"`.
- The `"EnableReplicatingDataIntoBucket"` statement grants permission for a remote target to synchronize data into *any* bucket in the MinIO deployment. To restrict the policy to specific buckets, specify those buckets as an element in the `Resource` array similar to `"arn:aws:s3:::bucketName/*"`.

The following code creates a [MinIO-managed user](/administration/identity-access-management/minio-user-management/#minio-users) with the necessary policy. Replace `TARGET` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment on which you are configuring replication:

```shell
wget -O - https://silo.pgsty.com/extra/examples/ReplicationRemoteUserPolicy.json | \
mc admin policy create TARGET ReplicationRemoteUserPolicy /dev/stdin
mc admin user add TARGET ReplicationRemoteUser LongRandomSecretKey
mc admin policy attach TARGET ReplicationRemoteUserPolicy --user=ReplicationRemoteUser
```

MinIO deployments configured for [Active Directory/LDAP](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap) or [OpenID Connect](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid) user management should instead create a dedicated [access keys](/administration/identity-access-management/minio-user-management/#minio-idp-service-account) for bucket replication.
{{< /tab >}}
{{< /tabs >}}

See [`mc admin user`](/reference/minio-mc-admin/mc-admin-user/#command-mc.admin.user), [`mc admin user svcacct`](/reference/minio-mc-admin/mc-admin-user-svcacct/#command-mc.admin.user.svcacct), and [`mc admin policy`](/reference/minio-mc-admin/mc-admin-policy/#command-mc.admin.policy) for more complete documentation on adding users, access keys, and policies to a MinIO deployment.

## Matching Object Encryption Settings for Bucket Replication {#matching-object-encryption-settings-for-bucket-replication}

MinIO supports replication of objects encrypted using [SSE-KMS](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms) and [SSE-S3](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3):

- For objects encrypted using SSE-KMS, MinIO *requires* that the target bucket support SSE-KMS encryption of objects using the *same key names* used to encrypt objects on the source bucket.
- For objects encrypted using [SSE-S3](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3), MinIO *requires* that the target bucket also support SSE-S3 encryption of objects regardless of key name.

As part of the replication process, MinIO *decrypts* the object on the source bucket and transmits the unencrypted object over the network. The destination MinIO deployment then re-encrypts the object using the encryption settings from the target. MinIO therefore *strongly recommends* [enabling TLS](/operations/network-encryption/#minio-tls) on both source and destination deployments to ensure the safety of objects during transmission.

MinIO does *not* support replicating client-side encrypted objects (SSE-C).

## Bucket Replication Requires MinIO Deployments {#bucket-replication-requires-minio-deployments}

MinIO server-side replication only works between MinIO deployments. Both the source and destination deployments *must* run MinIO Server with matching versions.

To configure replication between arbitrary S3-compatible services, use [`mc mirror`](/reference/minio-mc/mc-mirror/#command-mc.mirror).

## Replication Requires Versioning {#replication-requires-versioning}

MinIO relies on the immutability protections provided by [versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) to support replication and resynchronization.

Use [`mc version info`](/reference/minio-mc/mc-version-info/#command-mc.version.info) to validate the versioning status of both the source and remote buckets. Use the [`mc version enable`](/reference/minio-mc/mc-version-enable/#command-mc.version.enable) command to enable versioning as necessary.

If you exclude a prefix or folder from versioning within the source bucket, MinIO cannot replicate objects within that folder or prefix.

## Matching Object Locking State With Bucket Replication {#matching-object-locking-state-with-bucket-replication}

MinIO supports replicating objects held under [WORM Locking](/administration/object-management/object-retention/#minio-object-locking). Both replication buckets *must* have object locking enabled for MinIO to replicate the locked object. For active-active configuration, MinIO recommends using the *same* retention rules on both buckets to ensure consistent behavior across sites.

You must enable object locking during bucket creation as per S3 behavior. You can then configure object retention rules at any time. Configure the necessary rules on the unhealthy target bucket *prior* to beginning this procedure.

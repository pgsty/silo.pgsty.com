---
title: "Resynchronize Bucket from Remote Replica"
url: "/administration/bucket-replication/server-side-replication-resynchronize-remote/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="resynchronize-bucket-from-remote-replica"></a>
<a id="minio-bucket-replication-resynchronize"></a>

The procedure on this page resynchronizes the contents of a MinIO bucket using a healthy replication remote. Resynchronization supports recovery after partial or total loss of data on a MinIO deployment in a replica configuration.

For example, consider a MinIO active-active replication configuration similar to the following:

<img src="/images/replication/active-active-twoway-replication.svg" alt="Active-Active Replication synchronizes data between two remote deployments." style="max-width: 600px; height: auto;" />

Resynchronization allows using the healthy data on one of the participating MinIO deployments as the source for rebuilding the other deployment.

Resynchronization is a per-bucket process. You must repeat resynchronization for each bucket on the remote which suffered partial or total data loss.

{{% alert color="info" %}}
**Professional Support during BC/DR Operations**

[MinIO SUBNET](https://min.io/pricing?jmp=docs) users can [log in](https://subnet.min.io/) and create a new issue related to resynchronization. Coordination with MinIO Engineering via SUBNET can ensure successful resynchronization and restoration of normal operations, including performance testing and health diagnostics.

Community users can seek support on the [MinIO Community Slack](https://slack.min.io). Community Support is best-effort only and has no SLAs around responsiveness.
{{% /alert %}}

<a id="minio-bucket-replication-serverside-resynchronize-requirements"></a>

## Requirements {#requirements}

### MinIO Deployments Must Be Online {#minio-deployments-must-be-online}

Resynchronization requires both the source and target deployments be online and able to accept read and write operations. The source *must* have complete network connectivity to the remote.

The remote deployment may be “unhealthy” in that it has suffered partial or total data loss. Resynchronization addresses the data loss as long as both source and destination maintain connectivity.

### Resynchronization Requires Existing Replication Configuration {#resynchronization-requires-existing-replication-configuration}

Resynchronization requires the healthy source deployment have an existing replication configuration for the unhealthy target bucket. Additionally, resynchronization only applies to those replication rules created with the [existing object replication](/administration/bucket-replication/#minio-replication-behavior-existing-objects) option.

Use [`mc replicate ls`](/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls) to review the configured replication rules and targets for the healthy source bucket.

### Replication Requires Matching Object Encryption Settings {#replication-requires-matching-object-encryption-settings}

MinIO supports replication of objects encrypted using [SSE-KMS](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms) and [SSE-S3](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3):

- For objects encrypted using SSE-KMS, MinIO *requires* that the target bucket support SSE-KMS encryption of objects using the *same key names* used to encrypt objects on the source bucket.
- For objects encrypted using [SSE-S3](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3), MinIO *requires* that the target bucket also support SSE-S3 encryption of objects regardless of key name.

As part of the replication process, MinIO *decrypts* the object on the source bucket and transmits the unencrypted object over the network. The destination MinIO deployment then re-encrypts the object using the encryption settings from the target. MinIO therefore *strongly recommends* [enabling TLS](/operations/network-encryption/#minio-tls) on both source and destination deployments to ensure the safety of objects during transmission.

MinIO does *not* support replicating client-side encrypted objects (SSE-C).

### Replication Requires MinIO Deployments {#replication-requires-minio-deployments}

MinIO server-side replication only works between MinIO deployments. Both the source and destination deployments *must* run MinIO Server with matching versions.

To configure replication between arbitrary S3-compatible services, use [`mc mirror`](/reference/minio-mc/mc-mirror/#command-mc.mirror).

### Replication Requires Versioning {#replication-requires-versioning}

MinIO relies on the immutability protections provided by [versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) to support replication and resynchronization.

Use [`mc version info`](/reference/minio-mc/mc-version-info/#command-mc.version.info) to validate the versioning status of both the source and remote buckets. Use the [`mc version enable`](/reference/minio-mc/mc-version-enable/#command-mc.version.enable) command to enable versioning as necessary.

If you exclude a prefix or folder from versioning within the source bucket, MinIO cannot replicate objects within that folder or prefix.

### Replication Requires Matching Object Locking State {#replication-requires-matching-object-locking-state}

MinIO supports replicating objects held under [WORM Locking](/administration/object-management/object-retention/#minio-object-locking). Both replication buckets *must* have object locking enabled for MinIO to replicate the locked object. For active-active configuration, MinIO recommends using the *same* retention rules on both buckets to ensure consistent behavior across sites.

You must enable object locking during bucket creation as per S3 behavior. You can then configure object retention rules at any time. Configure the necessary rules on the unhealthy target bucket *prior* to beginning this procedure.

## Considerations {#considerations}

### Resynchronization Requires Time {#resynchronization-requires-time}

Resynchronization is a background processes that continually checks objects in the source MinIO bucket and copies them to the remote as-needed. The time required for replication to complete may vary depending on the number and size of objects, the throughput to the remote MinIO deployment, and the load on the source MinIO deployment. Total time for completion is generally not predictable due to these variables.

MinIO recommends configuring load balancers or proxies to direct traffic only to the healthy cluster until synchronization completes. The following commands can provide insight into the resynchronization status:

- [`mc replicate resync status`](/reference/minio-mc/mc-replicate-resync/#mc.replicate.resync.status) on the source to track the resynchronization progress.
- [`mc replicate status`](/reference/minio-mc/mc-replicate-status/#command-mc.replicate.status) on the source and remote to track normal replication data.
- Run `mc ls -r --versions ALIAS/BUCKET | wc -l` against both source and remote to validate the total number of objects and object versions on each.

## Resynchronize Objects after Data Loss {#resynchronize-objects-after-data-loss}

This procedure uses an existing [MinIO replication configuration](/administration/bucket-replication/#minio-bucket-replication-serverside) to restore missing data to one of the MinIO deployments participating in that configuration. Specifically, a healthy MinIO deployment (the `SOURCE`) synchronizes it’s existing data to the unhealthy MinIO deployment (the `TARGET`).

This procedure assumes an existing [alias](/reference/minio-mc/mc-alias-set/#alias) for the `SOURCE` that has the [necessary permissions](/administration/bucket-replication/enable-server-side-two-way-bucket-replication/#minio-bucket-replication-serverside-twoway-permissions) for configuring replication.

You can repeat this procedure for each bucket that requires resynchronization. You can have no more than one replication job running per bucket.

### 1) List the Configured Replication Targets on the Healthy Source {#list-the-configured-replication-targets-on-the-healthy-source}

Run the [`mc replicate ls`](/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls) command to list the configured remote targets on the healthy `SOURCE` deployment for the `BUCKET` that requires resynchronization.

```shell
mc replicate ls SOURCE/BUCKET --json
```

- Replace `SOURCE` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the source MinIO deployment.
- Replace `BUCKET` with the name of the bucket to use as the source for resynchronization.

The output resembles the following:

```shell
{
   "op": "",
   "status": "success",
   "url": "",
   "rule": {
      "ID": "cer1tuk9a3p5j68crk60",
      "Status": "Enabled",
      "Priority": 0,
      "DeleteMarkerReplication": {
         "Status": "Enabled"
      },
      "DeleteReplication": {
         "Status": "Enabled"
      },
      "Destination": {
         "Bucket": "arn:minio:replication::UUID:BUCKET"
      },
      "Filter": {
         "And": {},
         "Tag": {}
      },
      "SourceSelectionCriteria": {
         "ReplicaModifications": {
            "Status": "Enabled"
         }
      },
      "ExistingObjectReplication": {
         "Status": "Enabled"
      }
   }
}
```

Each document in the output represents one configured replication rule. The `Destination.Bucket` field specifies the ARN for a given rule on the bucket. Identify the correct ARN for the Bucket from which you want to resynchronize objects.

### 2) Start the Resynchronization Procedure {#start-the-resynchronization-procedure}

Run the [`mc replicate resync start`](/reference/minio-mc/mc-replicate-resync/#mc.replicate.resync.start) command to begin the resynchronization process:

```shell
mc replicate resync start --remote-bucket "arn:minio:replication::UUID:BUCKET" SOURCE/BUCKET
```

- Replace the `--remote-bucket` value with the ARN of the unhealthy `BUCKET` on the `TARGET` MinIO deployment.
- Replaced `SOURCE` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the source MinIO deployment.
- Replace the `BUCKET` with the name of the bucket on the healthy `SOURCE` MinIO deployment.

The command returns a resynchronization job ID indicating that the process has begun.

### 3) Monitor Resynchronization {#monitor-resynchronization}

Use the [`mc replicate resync status`](/reference/minio-mc/mc-replicate-resync/#mc.replicate.resync.status) command on the source deployment to track the received replication data:

```shell
mc replicate resync status ALIAS/BUCKET
```

The output resembles the following:

```shell
mc replicate resync status /data
Resync status summary:
● arn:minio:replication::6593d572-4dc3-4bb9-8d90-7f79cc612f01:data
   Status: Ongoing
   Replication Status | Size (Bytes)    | Count
   Replicated         | 2.3 GiB         | 18
   Failed             | 0 B             | 0
```

The **Status** updates to `Completed` once the resynchronization process completes.

### 4) Next Steps {#next-steps}

- If the `TARGET` bucket damage extends to replication rules, you must recreate those rules to match the previous replication configuration. See [Enable Two-Way Server-Side Bucket Replication](/administration/bucket-replication/enable-server-side-two-way-bucket-replication/#minio-bucket-replication-serverside-twoway) for additional guidance.
- Perform basic validation that all buckets in the replication configuration show similar results for commands such as [`mc ls`](/reference/minio-mc/mc-ls/#command-mc.ls) and [`mc stat`](/reference/minio-mc/mc-stat/#command-mc.stat).
- After restoring any replication rules and verifying replication between sites, you can configure the reverse proxy, load balancer, or other network control plane managing connections to resume sending traffic to the resynchronized deployment.

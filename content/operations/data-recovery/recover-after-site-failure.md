---
title: "Site Failure Recovery"
url: "/operations/data-recovery/recover-after-site-failure/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/data-recovery/recover-after-site-failure.rst
upstream_modified: false
---

<a id="site-failure-recovery"></a>
<a id="minio-restore-hardware-failure-site"></a>

MinIO can make the loss of an entire site, while significant, a relatively minor incident. Site recovery depends on the replication option you use for the site.

<table>
  <tbody>
    <tr>
      <td><p>Site Replication</p></td>
      <td><p>Total restoration of IAM configurations, bucket configurations, and data from the healthy peer site(s)</p></td>
    </tr>
    <tr>
      <td><p>Bucket Replication</p></td>
      <td><p>Data restoration of objects and metadata from a healthy remote location for each bucket configured for replication</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-mirror/#command-mc.mirror"><code>mc mirror</code></a></p></td>
      <td><p>Data restoration of objects only from a healthy remote location with no versioning</p></td>
    </tr>
  </tbody>
</table>

Site replication healing automatically adds IAM settings, buckets, bucket configurations, and objects from the existing site(s) to the new site with no further action required.

You cannot configure site replication if any bucket replication rules remain in place on other healthy sites. Bucket replication is mutually exclusive with site replication.

If you are switching from using bucket replication to using site replication, you must first remove all bucket replication rules from the healthy site prior to setting up site replication.

## Restore an Unhealthy Peer to Site Replication {#restore-an-unhealthy-peer-to-site-replication}

> [!WARNING]
> **Important**
>
> The [RELEASE.2023-01-02T09-40-09Z](https://github.com/minio/minio/releases/tag/RELEASE.2023-01-02T09-40-09Z) MinIO server release includes important fixes for removing a downed site in replication configurations containing three or more peer sites.
>
> For deployments configured for site replication, plan to [test and upgrade](/operations/deployments/baremetal-upgrade-minio-deployment/#minio-upgrade) all peer sites to the specified release. In the event of a site failure, you can update the remaining healthy sites to the specified version and use this procedure.

[Site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview) keeps two or more MinIO deployments in sync with IAM policies, buckets, bucket configurations, objects, and object metadata. If a peer site fails, such as due to a major disaster or long power outage, you can use the remaining healthy site(s) to restore the [replicable data](/operations/replication/multi-site-replication/#minio-site-replication-what-replicates).

The following procedure can restore data in scenarios where [site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview) was active prior to the site loss. This procedure assumes a *total loss* of one or more peer sites versus replication lag or delays due to latency or transient deployment downtime.

1. Remove the failed site from the MinIO site replication configuration using the [`mc admin replicate rm`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.rm) command with the `--force` option.

   The following command force-removes an unhealthy peer site from the replication configuration:

   ```shell
   mc admin replicate rm HEALTHY_PEER UNHEALTHY_PEER --force
   ```

   - Replace `HEALTHY_PEER` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of any healthy peer in the replication configuration
   - Replace `UNHEALTHY_PEER` with the alias of the unhealthy peer site

   All healthy peers in the site replication configuration update to remove the unhealthy peer automatically. You can use the [`mc admin replicate info`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.info) command to verify the new site replication configuration.
2. Deploy a new MinIO site following the [site replication requirements](/operations/replication/multi-site-replication/#minio-expand-site-replication).

   - Do not upload any data or otherwise configure the deployment beyond the stated requirements.
   - Validate that the new MinIO deployment functions normally and has bidirectional connectivity to the other peer sites.
   - Ensure the new site matches the server version on the existing peer sites

   > [!CAUTION]
   > **Warning**
   >
   > The [`mc admin replicate rm --force`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.rm.-force) command only operates on the online or healthy nodes in the site replication configuration. The removed offline MinIO deployment retains its original replication configuration, such that if the deployment resumes normal operations it would continue replication operations to its configured peer sites.
   >
   > If you plan to re-use the hardware for the site replication configuration, you **must** completely wipe the drives for the deployment before re-initializing MinIO and adding the site back to the replication configuration.
3. [Add the replacement peer site](/operations/replication/multi-site-replication/#minio-expand-site-replication) to the replication configuration.

   Use the [`mc admin replicate add`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.add) command to update the replication configuration with the new site:

   ```shell
   mc admin replicate add HEALTHY_PEER NEW_PEER
   ```

   - Replace `HEALTHY_PEER` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of any healthy peer in the replication configuration
   - Replace `NEW_PEER` with the alias of the new peer

   All healthy peers in the site replication configuration update for the new peer automatically. You can use the [`mc admin replicate info`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.info) command to verify the new site replication configuration.
4. Resynchronize the new peer with [`mc admin replicate resync`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.resync).

   ```shell
   mc admin replicate resync start HEALTHY_PEER NEW_PEER
   ```

   - Replace `HEALTHY_PEER` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of any healthy peer in the replication configuration
   - Replace `NEW_PEER` with the alias of the new peer
5. Validate the replication status.

   Use the following commands to track the replication status:

   - [`mc admin replicate status`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.status) - provides overall status and progress of replication
   - [`mc replicate status`](/reference/minio-mc/mc-replicate-status/#command-mc.replicate.status) - provides bucket-level and global replication status

## Active Bucket Replication Resynchronization {#active-bucket-replication-resynchronization}

For scenarios where [bucket replication](/administration/bucket-replication/#minio-bucket-replication) was in place prior to the failure, you can use [`mc replicate resync`](/reference/minio-mc/mc-replicate-resync/#command-mc.replicate.resync) to restore data to a new site. Create a new site to replace the failed deployment, then synchronize the data from an existing, healthy, bucket replication-enabled deployment to the new site.

1. Deploy a new MinIO site.
2. Set up IAM and users as needed.
3. On the site with data, create a new `remote target` using the [`mc admin bucket remote add`](/reference/deprecated/mc-admin-bucket-remote/#mc.admin.bucket.remote.add) command and record the ARN from the output.
4. From the site with the data, use the [`mc replicate resync start`](/reference/minio-mc/mc-replicate-resync/#mc.replicate.resync.start) command with the ARN from the previous command to rebuild the bucket on the new site.
5. Wait for re-synchronization to complete (use [`mc replicate resync status`](/reference/minio-mc/mc-replicate-resync/#mc.replicate.resync.status) to check).
6. Set up bucket replication rule(s) from the new MinIO site to the existing target bucket(s).
7. *(Optional)* Delete the bucket replication rules from the target deployment(s) to restore an active-passive replication scenario.

## Passive Bucket Replication Resynchronization {#passive-bucket-replication-resynchronization}

[Bucket replication](/administration/bucket-replication/#minio-bucket-replication) can directly restore the site contents by performing a replication from the target bucket(s) to a new MinIO site.

As a passive process, bucket replication may not perform as quickly as desired for a site recovery scenario.

Bucket replication relies on the standard replication [scanner](/operations/concepts/scanner/#minio-concepts-scanner) queue, which does not take priority over other processes. For recovery procedures with stricter SLA/SLO, use the active bucket replication process with [`mc replicate resync`](/reference/minio-mc/mc-replicate-resync/#command-mc.replicate.resync) command as described above.

Bucket replication rules copy the object, its version ID, versions, and other metadata to the target bucket. MinIO can restore the object with all of these attributes to a new MinIO site if bucket replication had already been in use prior to the site loss.

1. Deploy a new MinIO site.
2. Set up IAM and users as needed.
3. On the remaining target bucket deployment(s), create bucket replication rule(s) for each bucket to the new MinIO site.
4. Wait for replication to complete.
5. Set up bucket replication rule(s) from the new MinIO site to the existing target bucket(s).
6. *(Optional)* Delete the bucket replication rules from the target deployment(s) to restore an active-passive replication scenario.

   Do not delete the bucket replication rules from the deployments used to recover data if you prefer to keep an active-active replication between the buckets. In active-active replication, changes to the objects at either location affect the objects at the other location.

## Mirroring {#mirroring}

MinIO’s mirroring copies an object from any S3 compatible storage system.

Mirroring only copies the latest version of each object and does not include versioning metadata, regardless of the source. You cannot restore those attributes with this method.

Use [`mc mirror`](/reference/minio-mc/mc-mirror/#command-mc.mirror) in situations where you need to restore only the latest version of an object. Use bucket replication or site replication where those methods were already in use if you are copying from another MinIO deployment and wish to restore the object’s version history and version metadata.

1. Deploy a new MinIO site.
2. Set up IAM and users as needed.
3. Create buckets on the new site.
4. Use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) CLI command to copy the contents from the mirror location to the new MinIO site.

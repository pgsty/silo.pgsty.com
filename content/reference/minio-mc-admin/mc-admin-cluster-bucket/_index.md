---
title: "mc admin cluster bucket"
url: "/reference/minio-mc-admin/mc-admin-cluster-bucket/"
weight: 20
icon: fa-solid fa-boxes-stacked
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-cluster-bucket.rst
upstream_modified: false
---

<a id="mc-admin-cluster-bucket"></a>
<a id="minio-mc-admin-cluster-bucket"></a>

<a id="command-mc.admin.cluster.bucket"></a>

## Description {#description}

> [!NOTE]
> **Added: RELEASE.2022-06-17T02-52-50Z**

The [`mc admin cluster bucket`](#command-mc.admin.cluster.bucket) command and its subcommands provide tools for manually importing and exporting MinIO bucket metadata.

This metadata includes configurations related to features like [lifecycle management rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management). You can use this metadata as a snapshot of the bucket configuration for restoration later, such as part of <abbr title="Business Continuity / Disaster Recovery">BC/DR</abbr> or backup/restore operations.

You can use this command on individual buckets *or* on all buckets in a MinIO deployment. For automatic synchronization of all buckets in a deployment to a remote site, use [site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview).

The [`mc admin cluster bucket`](#command-mc.admin.cluster.bucket) command has the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-cluster-bucket-import/#command-mc.admin.cluster.bucket.import"><code>import</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-cluster-bucket-import/#command-mc.admin.cluster.bucket.import"><code>mc admin cluster bucket import</code></a> command imports bucket metadata as created by the <a href="/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export"><code>mc admin cluster bucket export</code></a> command.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export"><code>export</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export"><code>mc admin cluster bucket export</code></a> command exports bucket metadata for use with the <a href="/reference/minio-mc-admin/mc-admin-cluster-bucket-import/#command-mc.admin.cluster.bucket.import"><code>mc admin cluster bucket import</code></a> command.</p></td>
    </tr>
  </tbody>
</table>

---
title: "mc admin cluster iam"
url: "/reference/minio-mc-admin/mc-admin-cluster-iam/"
weight: 30
icon: fa-solid fa-users-gear
minio_origin: true
silo_modified: false
---

<a id="mc-admin-cluster-iam"></a>
<a id="minio-mc-admin-cluster-iam"></a>

<a id="command-mc.admin.cluster.iam"></a>

## Description {#description}

{{% alert color="info" %}}
**Added: RELEASE.2022-06-26T18-51-48Z**

{{% /alert %}}

The [`mc admin cluster iam`](#command-mc.admin.cluster.iam) command and its subcommands provide tools for manually importing and exporting MinIO [identity and access management (IAM)](/administration/identity-access-management/#minio-authentication-and-identity-management) metadata.

For automatic synchronization of all IAM configurations in a deployment to a remote site, use [site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview).

The [`mc admin cluster iam`](#command-mc.admin.cluster.iam) command has the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-cluster-iam-import/#command-mc.admin.cluster.iam.import"><code>import</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-cluster-iam-import/#command-mc.admin.cluster.iam.import"><code>mc admin cluster iam import</code></a> command imports <a href="/administration/identity-access-management/#minio-authentication-and-identity-management">IAM</a> metadata as created by the <a href="/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export"><code>mc admin cluster iam export</code></a> command.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export"><code>export</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export"><code>mc admin cluster iam export</code></a> command exports <a href="/administration/identity-access-management/#minio-authentication-and-identity-management">IAM</a> metadata for use with the <a href="/reference/minio-mc-admin/mc-admin-cluster-iam-import/#command-mc.admin.cluster.iam.import"><code>mc admin cluster iam import</code></a> command.</p></td>
    </tr>
  </tbody>
</table>

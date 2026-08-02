---
title: "mc replicate"
url: "/reference/minio-mc/mc-replicate/"
weight: 320
icon: fa-solid fa-copy
minio_origin: true
silo_modified: false
---

<a id="mc-replicate"></a>

<a id="command-mc.replicate"></a>

## Description {#description}

The [`mc replicate`](/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add) command configures and manages the [Server-Side Bucket Replication](/administration/bucket-replication/#minio-bucket-replication-serverside) for a MinIO deployment, including [active-active replication configurations](/administration/bucket-replication/enable-server-side-two-way-bucket-replication/#minio-bucket-replication-serverside-twoway) and [resynchronization](/administration/bucket-replication/#minio-replication-behavior-resync).

{{% alert color="info" %}}
**Note**

For multi-site replication, see [`mc admin replicate`](/reference/minio-mc-admin/mc-admin-replicate/#command-mc.admin.replicate).
{{% /alert %}}

## Subcommands {#subcommands}

[`mc replicate`](#command-mc.replicate) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add"><code>add</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add"><code>mc replicate add</code></a> command creates a new <a href="/administration/bucket-replication/#minio-bucket-replication-serverside">server-side replication</a> rule for a bucket on a MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-replicate-backlog/#command-mc.replicate.backlog"><code>backlog</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-replicate-backlog/#command-mc.replicate.backlog"><code>mc replicate backlog</code></a> shows a list of unreplicated new or deleted objects.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-replicate-export/#command-mc.replicate.export"><code>export</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-replicate-export/#command-mc.replicate.export"><code>mc replicate export</code></a> command exports the JSON-formatted
<a href="/administration/bucket-replication/#minio-bucket-replication-serverside">replication rules</a> for a
MinIO bucket to <code>STDOUT</code>.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-replicate-import/#command-mc.replicate.import"><code>import</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-replicate-import/#command-mc.replicate.import"><code>mc replicate import</code></a> command imports JSON-formatted
<a href="/administration/bucket-replication/#minio-bucket-replication-serverside">replication rules</a> for a
MinIO bucket from <code>STDIN</code>.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls"><code>ls</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls"><code>mc replicate ls</code></a> command lists all
<a href="/administration/bucket-replication/#minio-bucket-replication-serverside">replication rules</a> on a
MinIO bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-replicate-resync/#command-mc.replicate.resync"><code>resync</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-replicate-resync/#command-mc.replicate.resync"><code>mc replicate resync</code></a> command resynchronizes all objects in the
specified MinIO bucket to a remote <a href="/administration/bucket-replication/#minio-bucket-replication-serverside">replication</a> target.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-replicate-rm/#command-mc.replicate.rm"><code>rm</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-replicate-rm/#command-mc.replicate.rm"><code>mc replicate rm</code></a> command removes a
<a href="/administration/bucket-replication/#minio-bucket-replication-serverside">replication rule</a> from a
MinIO bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-replicate-status/#command-mc.replicate.status"><code>status</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-replicate-status/#command-mc.replicate.status"><code>mc replicate status</code></a> command displays the <a href="/administration/bucket-replication/#minio-bucket-replication-serverside">replication status</a> of a MinIO bucket.
The status also lists the remote target path or location.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-replicate-update/#command-mc.replicate.update"><code>update</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-replicate-update/#command-mc.replicate.update"><code>mc replicate update</code></a> command modifies an existing
<a href="/administration/bucket-replication/#minio-bucket-replication-serverside">bucket replication rule</a>.</p></td>
    </tr>
  </tbody>
</table>

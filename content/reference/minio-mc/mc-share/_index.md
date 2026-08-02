---
title: "mc share"
url: "/reference/minio-mc/mc-share/"
weight: 350
icon: fa-solid fa-share-nodes
minio_origin: true
silo_modified: false
---

<a id="mc-share"></a>

<a id="command-mc.share"></a>

## Description {#description}

Use the [`mc share`](#command-mc.share) commands to manage presigned URLs for downloading and uploading objects to a MinIO bucket.

## Subcommands {#subcommands}

[`mc share`](#command-mc.share) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-share-download/#command-mc.share.download"><code>download</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-share-download/#command-mc.share.download"><code>mc share download</code></a> command generates a temporary presigned URL with
integrated access credentials for downloading objects from a MinIO bucket. The
temporary URL expires after a configurable time limit.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-share-list/#command-mc.share.list"><code>list</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-share-list/#command-mc.share.ls"><code>mc share ls</code></a> command displays any unexpired presigned URLs generated
by <a href="/reference/minio-mc/mc-share-upload/#command-mc.share.upload"><code>mc share upload</code></a> or <a href="/reference/minio-mc/mc-share-download/#command-mc.share.download"><code>mc share download</code></a></p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-share-upload/#command-mc.share.upload"><code>upload</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-share-upload/#command-mc.share.upload"><code>mc share upload</code></a> command generates a temporary presigned URL with
integrated access credentials for uploading objects to a MinIO bucket. The
temporary URL expires after a configurable time limit.</p></td>
    </tr>
  </tbody>
</table>

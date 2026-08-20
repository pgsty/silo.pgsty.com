---
title: "mc ilm"
url: "/reference/minio-mc/mc-ilm/"
weight: 190
icon: fa-solid fa-clock-rotate-left
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-ilm.rst
upstream_modified: false
---

<a id="mc-ilm"></a>

<a id="command-mc.ilm"></a>

## Description {#description}

The [`mc ilm`](#command-mc.ilm) commands manage [object lifecycle management rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management) and tiering on a MinIO deployment.

Use these command to

- create tiers
- create [tiering](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering) rules
- manage [expiration](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) rules for objects on a bucket

## Subcommands {#subcommands}

[`mc ilm`](#command-mc.ilm) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-restore/#command-mc.ilm.restore"><code>restore</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-restore/#command-mc.ilm.restore"><code>mc ilm restore</code></a> command creates a temporary copy of an object archived
on a remote tier. The copy automatically expires after 1 day by default.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-rule/#command-mc.ilm.rule"><code>rule</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-rule/#command-mc.ilm.rule"><code>mc ilm rule</code></a> command and its subcommands configure the rules used to transition objects between storage tiers in MinIO’s Lifecycle Management.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier/#command-mc.ilm.tier"><code>tier</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm-tier/#command-mc.ilm.tier"><code>mc ilm tier</code></a> command and its subcommands configure a remote supported S3-compatible service for MinIO <a href="/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration">Lifecycle Management: Object Transition (“Tiering”)</a>.</p></td>
    </tr>
  </tbody>
</table>

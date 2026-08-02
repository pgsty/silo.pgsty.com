---
title: "mc retention"
url: "/reference/minio-mc/mc-retention/"
weight: 330
icon: fa-solid fa-hourglass-half
minio_origin: true
silo_modified: false
---

<a id="mc-retention"></a>

<a id="command-mc.retention"></a>

## Description {#description}

The [`mc retention`](#command-mc.retention) command configures the [Write-Once Read-Many (WORM) locking](/administration/object-management/object-retention/#minio-object-locking) settings for an object or object(s) in a bucket. You can also set the default object lock settings for a bucket, where all objects without explicit object lock settings inherit the bucket default.

## Subcommands {#subcommands}

[`mc retention`](#command-mc.retention) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-retention-clear/#command-mc.retention.clear"><code>clear</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-retention-clear/#command-mc.retention.clear"><code>mc retention clear</code></a> command removes the
<a href="/administration/object-management/object-retention/#minio-object-locking">Write-Once Read-Many (WORM) locking</a> settings for
an object or object(s) in a bucket. You can also remove the default object lock
settings for a bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-retention-info/#command-mc.retention.info"><code>info</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-retention-info/#command-mc.retention.info"><code>mc retention info</code></a> command configures the <a href="/administration/object-management/object-retention/#minio-object-locking">Write-Once Read-Many (WORM)
locking</a> settings for an object or object(s) in a bucket.
You can also set the default object lock settings for a bucket, where all
objects without explicit object lock settings inherit the bucket default.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-retention-set/#command-mc.retention.set"><code>set</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-retention-set/#command-mc.retention.set"><code>mc retention set</code></a> command configures the
<a href="/administration/object-management/object-retention/#minio-object-locking">Write-Once Read-Many (WORM) locking</a> settings for
an object or object(s) in a bucket. You can also set the default object lock
settings for a bucket, where all objects without explicit object lock settings
inherit the bucket default.</p></td>
    </tr>
  </tbody>
</table>

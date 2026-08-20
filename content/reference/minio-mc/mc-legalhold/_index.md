---
title: "mc legalhold"
url: "/reference/minio-mc/mc-legalhold/"
weight: 200
icon: fa-solid fa-gavel
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-legalhold.rst
upstream_modified: false
---

<a id="mc-legalhold"></a>

<a id="command-mc.legalhold"></a>

## Description {#description}

The [`mc legalhold`](#command-mc.legalhold) command sets, removes, or retrieves the [object legal hold (WORM)](/administration/object-management/object-retention/#minio-object-locking-legalhold) settings for object(s).

## Subcommands {#subcommands}

[`mc legalhold`](#command-mc.legalhold) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-legalhold-clear/#command-mc.legalhold.clear"><code>clear</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-legalhold-clear/#command-mc.legalhold.clear"><code>mc legalhold clear</code></a> command removes the current <a href="/administration/object-management/object-retention/#minio-object-locking-legalhold">legal hold</a> setting for an object or objects.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-legalhold-info/#command-mc.legalhold.info"><code>info</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-legalhold-info/#command-mc.legalhold.info"><code>mc legalhold info</code></a> command returns the current <a href="/administration/object-management/object-retention/#minio-object-locking-legalhold">legal hold</a> setting for an object or objects.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-legalhold-set/#command-mc.legalhold.set"><code>set</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-legalhold-set/#command-mc.legalhold.set"><code>mc legalhold set</code></a> command enables <a href="/administration/object-management/object-retention/#minio-object-locking-legalhold">legal hold</a> Write-Once Read-Many (WORM) object locking on
an object or objects.</p></td>
    </tr>
  </tbody>
</table>

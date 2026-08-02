---
title: "mc alias"
url: "/reference/minio-mc/mc-alias/"
weight: 20
icon: fa-solid fa-link
minio_origin: true
silo_modified: false
---

<a id="mc-alias"></a>

<a id="command-mc.alias"></a>

## Description {#description}

The [`mc alias`](#command-mc.alias) commands provide a convenient interface for managing the list of S3-compatible hosts that [`mc`](/reference/minio-mc/#command-mc) can connect to and run operations against.

{{% alert color="warning" %}}
**Important**

[`mc`](/reference/minio-mc/#command-mc) commands that operate on S3-compatible services *require* specifying an alias for that service.
{{% /alert %}}

## Subcommands {#subcommands}

[`mc alias`](#command-mc.alias) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-alias-list/#command-mc.alias.list"><code>list</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-alias-list/#command-mc.alias.list"><code>mc alias list</code></a> command lists all aliases in the local
<strong>mc</strong> configuration.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-alias-remove/#command-mc.alias.remove"><code>remove</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-alias-remove/#command-mc.alias.remove"><code>mc alias remove</code></a> removes an existing alias from the local
<strong>mc</strong> configuration.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-alias-set/#command-mc.alias.set"><code>set</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-alias-set/#command-mc.alias.set"><code>mc alias set</code></a> command adds or updates an alias to the local
<strong>mc</strong> configuration.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-alias-import/#command-mc.alias.import"><code>import</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-alias-import/#command-mc.alias.import"><code>mc alias import</code></a> command imports an alias configuration from a JSON document.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-alias-export/#command-mc.alias.export"><code>export</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-alias-export/#command-mc.alias.export"><code>mc alias export</code></a> command exports an alias configuration from the existing <a href="/reference/minio-mc/#mc-configuration">configuration</a>.</p></td>
    </tr>
  </tbody>
</table>

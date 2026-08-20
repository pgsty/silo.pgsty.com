---
title: "mc encrypt"
url: "/reference/minio-mc/mc-encrypt/"
weight: 90
icon: fa-solid fa-lock
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-encrypt.rst
upstream_modified: false
---

<a id="mc-encrypt"></a>

<a id="command-mc.encrypt"></a>

## Description {#description}

The [`mc encrypt`](#command-mc.encrypt) commands set, update, or disable the default bucket Server-Side Encryption (SSE) mode. MinIO automatically encrypts objects using the specified SSE mode.

## Subcommands {#subcommands}

[`mc encrypt`](#command-mc.encrypt) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-encrypt-clear/#command-mc.encrypt.clear"><code>clear</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-encrypt-clear/#command-mc.encrypt.clear"><code>mc encrypt clear</code></a> command removes the current default
encryption settings for a bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-encrypt-info/#command-mc.encrypt.info"><code>info</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-encrypt-info/#command-mc.encrypt.info"><code>mc encrypt info</code></a> command returns the current default
encryption settings for a bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-encrypt-set/#command-mc.encrypt.set"><code>set</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-encrypt-set/#command-mc.encrypt.set"><code>mc encrypt set</code></a> encrypt command sets or updates the default
bucket <a href="/administration/server-side-encryption/#minio-sse">Server-Side Encryption (SSE) mode</a>. MinIO automatically
encrypts objects written to that bucket using the specified SSE mode.</p></td>
    </tr>
  </tbody>
</table>

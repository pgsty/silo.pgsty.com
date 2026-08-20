---
title: "mc idp ldap policy"
url: "/reference/minio-mc/mc-idp-ldap-policy/"
weight: 170
icon: fa-solid fa-file-shield
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-idp-ldap-policy.rst
upstream_modified: false
---

<a id="mc-idp-ldap-policy"></a>
<a id="minio-mc-idp-ldap-policy"></a>

<a id="command-mc.idp.ldap.policy"></a>

> [!NOTE]
> **Added: RELEASE.2023-05-26T23-31-54Z**
>
> [`mc idp ldap policy`](#command-mc.idp.ldap.policy) and its subcommands replace `mc admin idp ldap policy`.

## Description {#description}

The [`mc idp ldap policy`](#command-mc.idp.ldap.policy) commands show the mapping relationships between policies and the associated groups or users.

The [`mc idp ldap policy`](#command-mc.idp.ldap.policy) commands are only supported against MinIO deployments.

The [`mc idp ldap policy`](#command-mc.idp.ldap.policy) command has the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-policy-attach/#command-mc.idp.ldap.policy.attach"><code>mc idp ldap policy attach</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-policy-attach/#command-mc.idp.ldap.policy.attach"><code>mc idp ldap policy attach</code></a> command attaches one or more polices to an entity.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-policy-detach/#command-mc.idp.ldap.policy.detach"><code>mc idp ldap policy detach</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-policy-detach/#command-mc.idp.ldap.policy.detach"><code>mc idp ldap policy detach</code></a> command detaches one or more polices from an entity.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-policy-entities/#command-mc.idp.ldap.policy.entities"><code>mc idp ldap policy entities</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-policy-entities/#command-mc.idp.ldap.policy.entities"><code>mc idp ldap policy entities</code></a> command displays a list of mappings for a user, group, and/or policy.</p></td>
    </tr>
  </tbody>
</table>

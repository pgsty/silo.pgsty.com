---
title: "mc idp ldap accesskey"
url: "/reference/minio-mc/mc-idp-ldap-accesskey/"
weight: 150
icon: fa-solid fa-key
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-idp-ldap-accesskey.rst
upstream_modified: false
---

<a id="mc-idp-ldap-accesskey"></a>
<a id="minio-mc-idp-ldap-accesskey"></a>

<a id="command-mc.idp.ldap.accesskey"></a>

> [!NOTE]
> **Added: RELEASE.2023-10-30T18-43-32Z**

## Description {#description}

The [`mc idp ldap accesskey`](#command-mc.idp.ldap.accesskey) commands allow you to list, delete, or display information about LDAP access key pairs.

The [`mc idp ldap accesskey`](#command-mc.idp.ldap.accesskey) commands are only supported against MinIO deployments.

This command works against [access keys](/administration/identity-access-management/minio-user-management/#minio-id-access-keys) created by an AD/LDAP user after authenticating to MinIO.

Create AD/LDAP service accounts with the [`mc idp ldap accesskey create`](/reference/minio-mc/mc-idp-ldap-accesskey-create/#command-mc.idp.ldap.accesskey.create) command.

MinIO supports using [AssumeRoleWithLDAPIdentity](/developers/security-token-service/AssumeRoleWithLDAPIdentity/#minio-sts-assumerolewithldapidentity) to generate temporary access keys using the [Security Token Service](/developers/security-token-service/#minio-security-token-service).

The [`mc idp ldap accesskey`](#command-mc.idp.ldap.accesskey) command has the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-accesskey-create/#command-mc.idp.ldap.accesskey.create"><code>mc idp ldap accesskey create</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-accesskey-create/#command-mc.idp.ldap.accesskey.create"><code>mc idp ldap accesskey create</code></a> allows you to add LDAP access key pairs.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-accesskey-disable/#command-mc.idp.ldap.accesskey.disable"><code>mc idp ldap accesskey disable</code></a></p></td>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-accesskey-disable/#command-mc.idp.ldap.accesskey.disable"><code>mc idp ldap accesskey disable</code></a> disables the specified <a href="/administration/identity-access-management/minio-user-management/#minio-id-access-keys">access key</a> on the MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-accesskey-edit/#command-mc.idp.ldap.accesskey.edit"><code>mc idp ldap accesskey edit</code></a></p></td>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-accesskey-edit/#command-mc.idp.ldap.accesskey.edit"><code>mc idp ldap accesskey edit</code></a> modifies the specified <a href="/administration/identity-access-management/minio-user-management/#minio-id-access-keys">access key</a> on the local server.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-accesskey-enable/#command-mc.idp.ldap.accesskey.enable"><code>mc idp ldap accesskey enable</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-accesskey-enable/#command-mc.idp.ldap.accesskey.enable"><code>mc idp ldap accesskey enable</code></a> enables the specified <a href="/administration/identity-access-management/minio-user-management/#minio-id-access-keys">access key</a> on the local server.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-accesskey-info/#command-mc.idp.ldap.accesskey.info"><code>mc idp ldap accesskey info</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-accesskey-info/#command-mc.idp.ldap.accesskey.info"><code>mc idp ldap accesskey info</code></a> outputs information about the specified access key(s).</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-accesskey-ls/#command-mc.idp.ldap.accesskey.ls"><code>mc idp ldap accesskey ls</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-accesskey-ls/#command-mc.idp.ldap.accesskey.ls"><code>mc idp ldap accesskey ls</code></a> displays a list of LDAP access key pairs.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-accesskey-rm/#command-mc.idp.ldap.accesskey.rm"><code>mc idp ldap accesskey rm</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-accesskey-rm/#command-mc.idp.ldap.accesskey.rm"><code>mc idp ldap accesskey rm</code></a> deletes the specified access key from the local server.</p></td>
    </tr>
  </tbody>
</table>

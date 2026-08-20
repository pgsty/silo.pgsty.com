---
title: "mc admin accesskey"
url: "/reference/minio-mc-admin/mc-admin-accesskey/"
weight: 10
icon: fa-solid fa-key
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-accesskey.rst
upstream_modified: false
---

<a id="mc-admin-accesskey"></a>
<a id="minio-mc-admin-accesskey"></a>

<a id="command-mc.admin.accesskey"></a>

> [!NOTE]
> **Added: MinIO**
>
> Client RELEASE.2024-10-08T09-37-26Z

These commands replace the MinIO IDP functionality of the [`mc admin user svcacct`](/reference/minio-mc-admin/mc-admin-user-svcacct/#command-mc.admin.user.svcacct) command and its subcommands.

## Description {#description}

The [`mc admin accesskey`](#command-mc.admin.accesskey) command and its subcommands create and manage [Access Keys](/administration/identity-access-management/minio-user-management/#minio-idp-service-account) for internally managed users on a MinIO deployment.

Each access key is linked to a [user identity](/administration/identity-access-management/#minio-authentication-and-identity-management) and inherits the [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) attached to its parent user *or* those groups in which the parent user has membership. Each access key also supports an optional inline policy which further restricts access to a subset of actions and resources available to the parent user.

[`mc admin user svcacct`](/reference/minio-mc-admin/mc-admin-user-svcacct/#command-mc.admin.user.svcacct) only supports creating access keys for [MinIO-managed](/administration/identity-access-management/minio-user-management/#minio-users) accounts.

To create access keys for [Active Directory/LDAP-managed](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap) accounts, use [`mc idp ldap accesskey`](/reference/minio-mc/mc-idp-ldap-accesskey/#command-mc.idp.ldap.accesskey) and its subcommands. To manage access keys for [OpenID Connect-managed users](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid), log into the [MinIO Console](/administration/minio-console/#minio-console) and generate the access keys through the UI.

[`mc admin accesskey`](#command-mc.admin.accesskey) command has the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-accesskey-create/#command-mc.admin.accesskey.create"><code>create</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-accesskey-create/#command-mc.admin.accesskey.create"><code>mc admin accesskey create</code></a> command adds a new access key and secret key pair for an existing MinIO user.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-accesskey-disable/#command-mc.admin.accesskey.disable"><code>disable</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-accesskey-disable/#command-mc.admin.accesskey.disable"><code>mc admin accesskey disable</code></a> command disables an existing access key for a MinIO IDP user.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-accesskey-edit/#command-mc.admin.accesskey.edit"><code>edit</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-accesskey-edit/#command-mc.admin.accesskey.edit"><code>mc admin accesskey edit</code></a> command modifies the configuration of an access key associated to the specified user.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-accesskey-enable/#command-mc.admin.accesskey.enable"><code>enable</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-accesskey-enable/#command-mc.admin.accesskey.enable"><code>mc admin accesskey enable</code></a> command enables an existing access key.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-accesskey-info/#command-mc.admin.accesskey.info"><code>info</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-accesskey-info/#command-mc.admin.accesskey.info"><code>mc admin accesskey info</code></a> command returns a description of the specified <a href="/administration/identity-access-management/minio-user-management/#minio-id-access-keys">access key(s)</a>.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-accesskey-list/#command-mc.admin.accesskey.ls"><code>ls</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-accesskey-list/#command-mc.admin.accesskey.ls"><code>mc admin accesskey ls</code></a> command lists users, access keys, or temporary <a href="/developers/security-token-service/#minio-security-token-service">security token service</a> keys managed by the MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-accesskey-remove/#command-mc.admin.accesskey.rm"><code>rm</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-accesskey-remove/#command-mc.admin.accesskey.rm"><code>mc admin accesskey rm</code></a> command removes an access key associated to a user on the deployment.</p></td>
    </tr>
  </tbody>
</table>

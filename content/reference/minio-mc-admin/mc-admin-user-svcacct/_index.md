---
title: "mc admin user svcacct"
url: "/reference/minio-mc-admin/mc-admin-user-svcacct/"
weight: 80
icon: fa-solid fa-user-tag
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-user-svcacct.rst
upstream_modified: false
---

<a id="mc-admin-user-svcacct"></a>
<a id="minio-mc-admin-user-svcacct"></a>

<a id="command-mc.admin.user.svcacct"></a>

> [!WARNING]
> **Important**
>
> These commands have been replaced and will be deprecated in a future MinIO Client release.
>
> As of MinIO Client RELEASE.2024-10-08T09-37-26Z, use the [`mc admin accesskey`](/reference/minio-mc-admin/mc-admin-accesskey/#command-mc.admin.accesskey) command and its subcommands for functions related to built-in MinIO IDP users and their access keys or STS tokens.
>
> For access keys for AD/LDAP users, use the [`mc idp ldap accesskey`](/reference/minio-mc/mc-idp-ldap-accesskey/#command-mc.idp.ldap.accesskey) command and its subcommands.

## Description {#description}

The [`mc admin user svcacct`](#command-mc.admin.user.svcacct) command and its subcommands create and manage [Access Keys](/administration/identity-access-management/minio-user-management/#minio-idp-service-account) on a MinIO deployment.

As of MinIO Client RELEASE.2024-10-08T09-37-26Z, these commands have been replaced by [`mc admin accesskey`](/reference/minio-mc-admin/mc-admin-accesskey/#command-mc.admin.accesskey) and [`mc idp ldap accesskey`](/reference/minio-mc/mc-idp-ldap-accesskey/#command-mc.idp.ldap.accesskey). This command and its subcommands will be deprecated in a future MinIO Client release.

Each access key is linked to a [user identity](/administration/identity-access-management/#minio-authentication-and-identity-management) and inherits the [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) attached to its parent user *or* those groups in which the parent user has membership. Each access key also supports an optional inline policy which further restricts access to a subset of actions and resources available to the parent user.

[`mc admin user svcacct`](#command-mc.admin.user.svcacct) only supports creating access keys for [MinIO-managed](/administration/identity-access-management/minio-user-management/#minio-users) and [Active Directory/LDAP-managed](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap) accounts.

To create access keys for [OpenID Connect-managed users](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid), log into the [MinIO Console](/administration/minio-console/#minio-console) and generate the access keys through the UI.

The [`mc admin user svcacct`](#command-mc.admin.user.svcacct) command has the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-svcacct-add/#command-mc.admin.user.svcacct.add"><code>add</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-svcacct-add/#command-mc.admin.user.svcacct.add"><code>mc admin user svcacct add</code></a> command adds a new access key to an existing MinIO or AD/LDAP user.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-svcacct-disable/#command-mc.admin.user.svcacct.disable"><code>disable</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-svcacct-disable/#command-mc.admin.user.svcacct.disable"><code>mc admin user svcacct disable</code></a> command disables an existing access key.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-svcacct-edit/#command-mc.admin.user.svcacct.edit"><code>edit</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-svcacct-edit/#command-mc.admin.user.svcacct.edit"><code>mc admin user svcacct edit</code></a> command modifies the configuration of an access key associated to the specified user.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-svcacct-enable/#command-mc.admin.user.svcacct.enable"><code>enable</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-svcacct-enable/#command-mc.admin.user.svcacct.enable"><code>mc admin user svcacct enable</code></a> command enables an existing access key.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-svcacct-info/#command-mc.admin.user.svcacct.info"><code>info</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-svcacct-info/#command-mc.admin.user.svcacct.info"><code>mc admin user svcacct info</code></a> command returns a description of the specified <a href="/administration/identity-access-management/minio-user-management/#minio-id-access-keys">access key</a>.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-svcacct-list/#command-mc.admin.user.svcacct.list"><code>list</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-svcacct-list/#command-mc.admin.user.svcacct.ls"><code>mc admin user svcacct ls</code></a> command lists all access keys associated to the specified user.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-svcacct-remove/#command-mc.admin.user.svcacct.rm"><code>rm</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-svcacct-remove/#command-mc.admin.user.svcacct.rm"><code>mc admin user svcacct rm</code></a> command removes an access key associated to a user on the deployment.</p></td>
    </tr>
  </tbody>
</table>

---
title: "mc admin user"
url: "/reference/minio-mc-admin/mc-admin-user/"
weight: 190
icon: fa-solid fa-users
minio_origin: true
silo_modified: false
---

<a id="mc-admin-user"></a>

<a id="command-mc.admin.user"></a>

## Description {#description}

The [`mc admin user`](#command-mc.admin.user) command and its subcommands manage [MinIO users](/administration/identity-access-management/minio-identity-management/#minio-internal-idp).

Clients *must* authenticate to the MinIO deployment with the access key and secret key associated to a user on the deployment. MinIO users constitute a key component in MinIO Identity and Access Management.

To manage users who authenticate using a 3rd party IDP, use the command for the appropriate provider:

- For AD/LDAP, use [`mc idp ldap`](/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap)
- For OpenID Connect (OIDC) compatible providers, use [`mc idp openid`](/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid)

{{% alert color="info" %}}
**Use `mc idp` commands on MinIO Deployments Only**

[`mc idp ldap`](/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap) and [`mc idp openid`](/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid) and their subcommands are only supported against MinIO deployments.
{{% /alert %}}

## Subcommands {#subcommands}

[`mc admin user`](#command-mc.admin.user) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-add/#command-mc.admin.user.add"><code>add</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-add/#command-mc.admin.user.add"><code>mc admin user add</code></a> command adds a new <a href="/administration/identity-access-management/minio-identity-management/#minio-internal-idp">MinIO user</a> to the target MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-disable/#command-mc.admin.user.disable"><code>disable</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-disable/#command-mc.admin.user.disable"><code>mc admin user disable</code></a> command disables a <a href="/administration/identity-access-management/minio-identity-management/#minio-internal-idp">MinIO user</a> on the target MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-enable/#command-mc.admin.user.enable"><code>enable</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-enable/#command-mc.admin.user.enable"><code>mc admin user enable</code></a> command enables a <a href="/administration/identity-access-management/minio-identity-management/#minio-internal-idp">MinIO user</a> on the target MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-info/#command-mc.admin.user.info"><code>info</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-info/#command-mc.admin.user.info"><code>mc admin user info</code></a> command returns detailed information of a <a href="/administration/identity-access-management/minio-identity-management/#minio-internal-idp">MinIO user</a> on the target MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-list/#command-mc.admin.user.ls"><code>ls</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-list/#command-mc.admin.user.ls"><code>mc admin user ls</code></a> command lists all <a href="/administration/identity-access-management/minio-identity-management/#minio-internal-idp">MinIO users</a> on the target MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-remove/#command-mc.admin.user.rm"><code>rm</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-remove/#command-mc.admin.user.rm"><code>mc admin user rm</code></a> command removes a <a href="/administration/identity-access-management/minio-identity-management/#minio-internal-idp">MinIO user</a> on the target MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-sts-info/#command-mc.admin.user.sts.info"><code>sts info</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-sts-info/#command-mc.admin.user.sts.info"><code>mc admin user sts info</code></a> command retrieves information on the specified STS credential, such as the parent <a href="/administration/identity-access-management/minio-identity-management/#minio-internal-idp">MinIO user</a> who generated the credentials, associated policies, and expiration.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user-svcacct/#command-mc.admin.user.svcacct"><code>svcacct</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user-svcacct/#command-mc.admin.user.svcacct"><code>mc admin user svcacct</code></a> command and its subcommands create and manage <a href="/administration/identity-access-management/minio-user-management/#minio-idp-service-account">Access Keys</a> on a MinIO deployment.</p><p>As of MinIO Client RELEASE.2024-10-08T09-37-26Z, these commands have been replaced by <a href="/reference/minio-mc-admin/mc-admin-accesskey/#command-mc.admin.accesskey"><code>mc admin accesskey</code></a> and <a href="/reference/minio-mc/mc-idp-ldap-accesskey/#command-mc.idp.ldap.accesskey"><code>mc idp ldap accesskey</code></a>.
This command and its subcommands will be deprecated in a future MinIO Client release.</p></td>
    </tr>
  </tbody>
</table>

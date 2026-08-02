---
title: "mc idp ldap"
url: "/reference/minio-mc/mc-idp-ldap/"
weight: 140
icon: fa-solid fa-address-book
minio_origin: true
silo_modified: false
---

<a id="mc-idp-ldap"></a>
<a id="minio-mc-idp-ldap"></a>

<a id="command-mc.idp.ldap"></a>

{{% alert color="info" %}}
**Added: RELEASE.2023-05-26T23-31-54Z**

[`mc idp ldap`](#command-mc.idp.ldap) and its subcommands replace `mc admin idp ldap`.
{{% /alert %}}

## Description {#description}

The [`mc idp ldap`](#command-mc.idp.ldap) commands allow you to manage configurations to 3rd party [Active Directory or LDAP Identity and Access Management (IAM) integrations](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap).

The [`mc idp ldap`](#command-mc.idp.ldap) commands are an alternative to using environment variables when [setting up an AD/LDAP connection](/operations/external-iam/configure-ad-ldap-external-identity-management/#minio-authenticate-using-ad-ldap-generic). They are only supported against MinIO deployments.

See [Active Directory / LDAP Access Management](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap) for a tutorial on using these commands.

{{% alert color="info" %}}
**Note**

MinIO [AD/LDAP environment variables](/reference/minio-server/settings/iam/ldap/#minio-server-envvar-external-identity-management-ad-ldap) override their corresponding configuration settings as modified or set by this command.
{{% /alert %}}

The [`mc idp ldap`](#command-mc.idp.ldap) command has the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-add/#command-mc.idp.ldap.add"><code>mc idp ldap add</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-add/#command-mc.idp.ldap.add"><code>mc idp ldap add</code></a> command creates an AD/LDAP IDP server configuration.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-disable/#command-mc.idp.ldap.disable"><code>mc idp ldap disable</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-disable/#command-mc.idp.ldap.disable"><code>mc idp ldap disable</code></a> command disables the currently configured AD/LDAP provider.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-enable/#command-mc.idp.ldap.enable"><code>mc idp ldap enable</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-enable/#command-mc.idp.ldap.enable"><code>mc idp ldap enable</code></a> command enables the currently configured AD/LDAP provider.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-info/#command-mc.idp.ldap.info"><code>mc idp ldap info</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-info/#command-mc.idp.ldap.info"><code>mc idp ldap info</code></a> command outputs the current configuration for an AD/LDAP provider on a specified MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-ls/#command-mc.idp.ldap.ls"><code>mc idp ldap ls</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-ls/#command-mc.idp.ldap.ls"><code>mc idp ldap ls</code></a> command lists the existing set of configurations for an AD/LDAP provider.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-policy/#command-mc.idp.ldap.policy"><code>mc idp ldap policy</code></a> subcommands</p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-policy/#command-mc.idp.ldap.policy"><code>mc idp ldap policy</code></a> commands show the mapping relationships between policies and the associated groups or users.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-rm/#command-mc.idp.ldap.rm"><code>mc idp ldap rm</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-rm/#command-mc.idp.ldap.rm"><code>mc idp ldap rm</code></a> command removes the existing configuration for an AD/LDAP provider.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-idp-ldap-update/#command-mc.idp.ldap.update"><code>mc idp ldap update</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-update/#command-mc.idp.ldap.update"><code>mc idp ldap update</code></a> command modifies an existing set of configurations for an AD/LDAP provider.</p></td>
    </tr>
  </tbody>
</table>

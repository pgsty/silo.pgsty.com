---
title: "mc admin policy"
url: "/reference/minio-mc-admin/mc-admin-policy/"
weight: 110
icon: fa-solid fa-file-shield
minio_origin: true
silo_modified: false
---

<a id="mc-admin-policy"></a>

<a id="command-mc.admin.policy"></a>

{{% alert color="info" %}}
**Changed: mc**

RELEASE.2023-03-20T17-17-53Z

The following commands are deprecated:

- `mc admin policy add` use [`mc admin policy create`](/reference/minio-mc-admin/mc-admin-policy-create/#command-mc.admin.policy.create) instead
- `mc admin policy set` use [`mc admin policy attach`](/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach) instead
- `mc admin policy unset` use [`mc admin policy detach`](/reference/minio-mc-admin/mc-admin-policy-detach/#command-mc.admin.policy.detach) instead
- `mc admin policy update` use [`attach`](/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach) or [`detach`](/reference/minio-mc-admin/mc-admin-policy-detach/#command-mc.admin.policy.detach) instead

The following command is added:

- [`mc admin policy entities`](/reference/minio-mc-admin/mc-admin-policy-entities/#command-mc.admin.policy.entities)
{{% /alert %}}

## Description {#description}

The [`mc admin policy`](#command-mc.admin.policy) commands manage policies for use with [MinIO Policy-Based Access Control](/administration/identity-access-management/policy-based-access-control/#minio-policy) (PBAC). MinIO PBAC uses IAM-compatible policy JSON documents to define rules for accessing resources on a MinIO server.

For complete documentation on MinIO PBAC, including policy document JSON structure and syntax, see [Access Management](/administration/identity-access-management/policy-based-access-control/#minio-policy). To manage policies for deployments that use LDAP authentication, see [`mc idp ldap policy`](/reference/minio-mc/mc-idp-ldap-policy/#command-mc.idp.ldap.policy).

## Subcommands {#subcommands}

[`mc admin policy`](#command-mc.admin.policy) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach"><code>attach</code></a></p></td>
      <td><p>Attaches one or more IAM policies to either a <a href="/administration/identity-access-management/minio-user-management/#minio-users">MinIO-managed user or a group</a>.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-policy-create/#command-mc.admin.policy.create"><code>create</code></a></p></td>
      <td><p>Creates a new policy on the target MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-policy-detach/#command-mc.admin.policy.detach"><code>detach</code></a></p></td>
      <td><p>Remove one or more IAM policies from either a <a href="/administration/identity-access-management/minio-user-management/#minio-users">MinIO-managed user or a group</a>.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-policy-entities/#command-mc.admin.policy.entities"><code>entities</code></a></p></td>
      <td><p>List the entities associated with a policy, user, or group on a target MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-policy-info/#command-mc.admin.policy.info"><code>info</code></a></p></td>
      <td><p>Returns the specified policy in JSON format if it exists on the target MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-policy-list/#command-mc.admin.policy.ls"><code>ls</code></a></p></td>
      <td><p>Lists all policies on the target MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-policy-remove/#command-mc.admin.policy.rm"><code>rm</code></a></p></td>
      <td><p>Removes an IAM policy from the target MinIO deployment.</p></td>
    </tr>
  </tbody>
</table>

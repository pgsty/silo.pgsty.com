---
title: "Group Management"
url: "/administration/identity-access-management/minio-group-management/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="group-management"></a>
<a id="minio-groups"></a>

## Overview {#overview}

A *group* is a collection of [users](/administration/identity-access-management/minio-user-management/#minio-users). Each group can have one or more assigned [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) that explicitly list the actions and resources to which group members are allowed or denied access.

For example, consider the following groups. Each group is assigned a [built-in policy](/administration/identity-access-management/policy-based-access-control/#minio-policy-built-in) or supported [policy action](/administration/identity-access-management/policy-based-access-control/#minio-policy-actions). Each group also has one or more assigned users. Each user’s total set of permissions consists of their explicitly assigned permission *and* the inherited permissions from each of their assigned groups. MinIO by default *denies* access to any resource or operation not explicitly allowed by a user’s assigned or inherited policies.

<table>
  <thead>
    <tr>
      <th><p>Group</p></th>
      <th><p>Policy</p></th>
      <th><p>Members</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><code>Operations</code></p></td>
      <td><a href="/administration/identity-access-management/policy-based-access-control/#userpolicy.readwrite"><code>readwrite</code></a> on <code>finance</code> bucket<br /><a href="/administration/identity-access-management/policy-based-access-control/#userpolicy.readonly"><code>readonly</code></a> on <code>audit</code> bucket<br /></td>
      <td><p><code>john.doe</code>, <code>jane.doe</code></p></td>
    </tr>
    <tr>
      <td><p><code>Auditing</code></p></td>
      <td><a href="/administration/identity-access-management/policy-based-access-control/#userpolicy.readonly"><code>readonly</code></a> on <code>audit</code> bucket<br /></td>
      <td><p><code>jen.doe</code>, <code>joe.doe</code></p></td>
    </tr>
    <tr>
      <td><p><code>Admin</code></p></td>
      <td><p><a href="/administration/identity-access-management/policy-based-access-control/#policy-action.admin"><code>admin:*</code></a></p></td>
      <td><p><code>greg.doe</code>, <code>jen.doe</code></p></td>
    </tr>
  </tbody>
</table>

Groups provide a simplified method for managing shared permissions among users with common access patterns and workloads. Client’s *cannot* authenticate to a MinIO deployment using a group as an identity.

The [`mc admin group`](/reference/minio-mc-admin/mc-admin-group/#command-mc.admin.group) command supports the creation and management of groups on the MinIO deployment. See the command reference for examples of usage.

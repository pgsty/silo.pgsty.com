---
title: "mc admin group"
url: "/reference/minio-mc-admin/mc-admin-group/"
weight: 60
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-group.rst
upstream_modified: false
---

<a id="mc-admin-group"></a>

<a id="command-mc.admin.group"></a>

## Description {#description}

The [`mc admin group`](#command-mc.admin.group) command manages groups on a MinIO deployment.

A [group](/administration/identity-access-management/minio-group-management/#minio-groups) is a collection of [users](/administration/identity-access-management/minio-user-management/#minio-users). Each group can have one or more assigned [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) that explicitly list the actions and resources to which group members are allowed or denied access. Groups provide a simplified method for managing shared permissions among users with common access patterns and workloads.

> [!NOTE]
> **Use `mc admin` on MinIO Deployments Only**
>
> MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.

### Groups and Policy-Based Access Control {#groups-and-policy-based-access-control}

MinIO uses Policy-Based Access Control (PBAC) to support *authorization* of users who have successfully *authenticated* to the deployment. Each policy includes rules that dictate the allowed or denied actions/resources on the deployment. You can assign one or more [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) to a group. Users with membership in the group inherit the group’s assigned policies. A user’s total set of permissions includes their explicitly assigned policies *and* any policies inherited via group membership.

Newly created groups have *no* policies by default. To configure a group’s assigned policies, use the [`mc admin policy attach`](/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach) command.

For more information on MinIO users and groups, see [User Management](/administration/identity-access-management/minio-user-management/#minio-users) and [Group Management](/administration/identity-access-management/minio-group-management/#minio-groups). For more information on MinIO policies, see [MinIO Policy Based Access Control](/administration/identity-access-management/policy-based-access-control/#minio-policy).

> [!NOTE]
> **`Deny` overrides `Allow`**
>
> MinIO follows the IAM standard where a `Deny` rule overrides `Allow` rule on the same action or resource. For example, if a user has an explicitly assigned policy with an `Allow` rule for an action/resource while one of its groups has an assigned policy with a `Deny` rule for that action/resource, MinIO would apply only the `Deny` rule.
>
> For more information on IAM policy evaluation logic, see the IAM documentation on [Determining Whether a Request is Allowed or Denied Within an Account](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html#policy-eval-denyallow).

## Examples {#examples}

### Create a New Group {#create-a-new-group}

Use [`mc admin group add`](#mc.admin.group.add) to create a new group to an S3-compatible host:

```shell
mc admin group add ALIAS GROUPNAME MEMBER [MEMBER...]
```

- Replace [`ALIAS`](#mc.admin.group.add.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`GROUPNAME`](#mc.admin.group.add.GROUPNAME) with the name of the group to create.
- Replace [`MEMBER`](#mc.admin.group.add.MEMBERS) with *at least* one [`user`](/reference/minio-mc-admin/mc-admin-user/#command-mc.admin.user) on the S3 host. Specify multiple members as a list: `MEMBER1 MEMBER2 MEMBER3`

### List Available Groups {#list-available-groups}

Use [`mc admin group ls`](#mc.admin.group.ls) to list list all groups on an S3-compatible host:

```shell
mc admin group ls ALIAS
```

- Replace [`ALIAS`](#mc.admin.group.ls.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.

### View Group Details {#view-group-details}

Use [`mc admin group info`](#mc.admin.group.info) to view detailed group information on an S3-compatible host:

```shell
mc admin group info ALIAS GROUPNAME
```

- Replace [`ALIAS`](#mc.admin.group.info.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`GROUPNAME`](#mc.admin.group.info.GROUPNAME) with the name of the group.

### Remove a Group {#remove-a-group}

Use [`mc admin group rm`](#mc.admin.group.rm) to remove a group from an S3-compatible host:

```shell
mc admin group rm ALIAS GROUPNAME
```

- Replace [`ALIAS`](#mc.admin.group.rm.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`GROUPNAME`](#mc.admin.group.rm.GROUPNAME) with the name of the group.

### Disable a Group {#disable-a-group}

Use [`mc admin group disable`](#mc.admin.group.disable) to disable a group on an S3-compatible host:

```shell
mc admin group disable ALIAS GROUPNAME
```

- Replace [`ALIAS`](#mc.admin.group.disable.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`GROUPNAME`](#mc.admin.group.disable.GROUPNAME) with the name of the group.

### Enable a Group {#enable-a-group}

Use [`mc admin group enable`](#mc.admin.group.enable) to enable a group on an S3-compatible host:

```shell
mc admin group enable ALIAS GROUPNAME
```

- Replace [`ALIAS`](#mc.admin.group.enable.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`GROUPNAME`](#mc.admin.group.enable.GROUPNAME) with the name of the group.

## Quick Reference {#quick-reference}

**[`mc admin group add TARGET GROUPNAME MEMBERS`](#mc.admin.group.add)**

> Adds a user to a group on the MinIO deployment. Creates the group if it does not exist.

**[`mc admin group info TARGET GROUPNAME`](#mc.admin.group.info)**

> Returns detailed information for a group on the MinIO deployment.

**[`mc admin group ls TARGET`](#mc.admin.group.ls)**

> Returns a list of all groups on the MinIO deployment.

**[`mc admin group rm TARGET GROUPNAME`](#mc.admin.group.rm)**

> Removes a group on the MinIO deployment.

**[`mc admin group enable TARGET GROUPNAME`](#mc.admin.group.enable)**

> Enables a group on the MinIO deployment. Users can only inherit [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) assigned to an enabled group.

**[`mc admin group disable TARGET GROUPNAME`](#mc.admin.group.disable)**

> Disables a group on the MinIO deployment. Users cannot inherit [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) assigned to a disabled group.

## Syntax {#syntax}

#### `mc admin group add` {#mc.admin.group.add}

*mc-cmd*

Adds an existing user to the group. The command creates the group if it does not exist. The command has the following syntax:

```shell
mc admin group add TARGET GROUPNAME MEMBERS
```

The command accepts the following arguments:

#### `TARGET` {#mc.admin.group.add.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment on which the command adds users to the new or existing group

#### `GROUPNAME` {#mc.admin.group.add.GROUPNAME}

*mc-cmd*

The name of the group. The command creates the group if it does not already exist. Use [`mc admin group ls`](#mc.admin.group.ls) to review the existing groups on a deployment.

A group name cannot contain the characters `=` (equal sign) or `,` (comma).

#### `MEMBERS` {#mc.admin.group.add.MEMBERS}

*mc-cmd*

The name of the user to add to the group.

The user *must* exist on the [`TARGET`](#mc.admin.group.add.TARGET) MinIO deployment. Use [`mc admin user ls`](/reference/minio-mc-admin/mc-admin-user-list/#command-mc.admin.user.ls) to review the available users on the deployment.

#### `mc admin group info` {#mc.admin.group.info}

*mc-cmd*

Returns details for the group on the target deployment, such as all [users](/administration/identity-access-management/minio-user-management/#minio-users) with membership in the group and the assigned [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy). The command has the following syntax:

```shell
mc admin group info TARGET GROUPNAME
```

The command accepts the following arguments:

#### `TARGET` {#mc.admin.group.info.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment from which to retrieve the group information.

#### `GROUPNAME` {#mc.admin.group.info.GROUPNAME}

*mc-cmd*

The name of the group.

#### `mc admin group ls, list` {#mc.admin.group.ls}

*mc-cmd*

List all groups on the target MinIO deployment. The command has the following syntax:

```shell
mc admin group ls TARGET
```

The command accepts the following arguments:

#### `TARGET` {#mc.admin.group.ls.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment from which to retrieve groups.

#### `mc admin group rm, remove` {#mc.admin.group.rm}

*mc-cmd*

Removes a group on the target MinIO deployment. Removing a group does *not* remove any users with membership in the group. Use [`mc admin user rm`](/reference/minio-mc-admin/mc-admin-user-remove/#command-mc.admin.user.rm) to remove users from a group.

The command has the following syntax:

```shell
mc admin group rm TARGET GROUPNAME
```

The command accepts the following arguments:

#### `TARGET` {#mc.admin.group.rm.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment on which to remove the group.

#### `GROUPNAME` {#mc.admin.group.rm.GROUPNAME}

*mc-cmd*

The name of the group to remove.

#### `mc admin group enable` {#mc.admin.group.enable}

*mc-cmd*

Enables the group on the target MinIO deployment. Users can only inherit [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) from an enabled group. Groups are enabled on creation by default. The command has the following syntax:

```shell
mc admin group enable TARGET GROUPNAME
```

The command accepts the following arguments:

#### `TARGET` {#mc.admin.group.enable.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment on which to enable the group.

#### `GROUPNAME` {#mc.admin.group.enable.GROUPNAME}

*mc-cmd*

The name of the group to enable.

#### `mc admin group disable` {#mc.admin.group.disable}

*mc-cmd*

Disables the group on the target MinIO deployment. Users cannot inherit [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) from a disabled group. The command has the following syntax:

```shell
mc admin group disable TARGET GROUPNAME
```

The command accepts the following arguments:

#### `TARGET` {#mc.admin.group.disable.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment on which to disable the group.

#### `GROUPNAME` {#mc.admin.group.disable.GROUPNAME}

*mc-cmd*

The name of the group to disable.

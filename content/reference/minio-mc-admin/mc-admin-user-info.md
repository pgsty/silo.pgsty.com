---
title: "mc admin user info"
url: "/reference/minio-mc-admin/mc-admin-user-info/"
weight: 40
minio_origin: true
silo_modified: false
---

<a id="mc-admin-user-info"></a>
<a id="minio-mc-admin-user-info"></a>

<a id="command-mc.admin.user.info"></a>

## Syntax {#syntax}

The [`mc admin user info`](#command-mc.admin.user.info) command returns detailed information of a [MinIO user](/administration/identity-access-management/minio-identity-management/#minio-internal-idp) on the target MinIO deployment.

To manage external Identity Provider users, see [`OIDC`](/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid) or [`AD/LDAP`](/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command returns details of user `myuser` on the `myminio` MinIO deployment:

```shell
mc admin user info myminio myuser
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user info      \
                            ALIAS     \
                            USERNAME
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.user.info.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment to retrieve user information from.

##### `USERNAME` {#mc.admin.user.info.USERNAME}

*mc-cmd*

The username to retrieve information for.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

{{% alert color="info" %}}
**Changed: RELEASE.2023-05-26T23-31-54Z**

`mc admin user info --json` output includes policies inherited from a user’s group memberships in `memberOf`.
{{% /alert %}}

## Examples {#examples}

### View User Details {#view-user-details}

Use [`mc admin user info`](#command-mc.admin.user.info) to view detailed user information for a user on a MinIO deployment:

```shell
mc admin user info ALIAS USERNAME
```

- Replace [`ALIAS`](#mc.admin.user.info.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`USERNAME`](#mc.admin.user.info.USERNAME) with the username of the user to display information for.

For the [MinIO internal IDentity Provider (IDP)](/administration/identity-access-management/minio-identity-management/#minio-internal-idp), the output resembles the following:

```shell
AccessKey: miniouser
Status: enabled
PolicyName:
MemberOf: []
Authentication: builtin (miniouser)
```

For a [third-party](/operations/external-iam/#minio-external-identity-management) identity service such as LDAP, the output resembles the following:

```shell
AccessKey: uid=dillon,ou=people,ou=swengg,dc=min,dc=io
Status:
PolicyName: consoleAdmin
MemberOf: []
Authentication: ldap/localhost:1389 (uid=dillon,ou=people,ou=swengg,dc=min,dc=io)
```

### View Policies from Group Membership {#view-policies-from-group-membership}

Use [`mc admin user info`](#command-mc.admin.user.info) with :option::*–json &lt;mc.–json&gt;* to view the policies inherited from a user’s [group memberships](/administration/identity-access-management/minio-group-management/#minio-groups):

```shell
mc admin user info ALIAS USERNAME --json
```

- Replace [`ALIAS`](#mc.admin.user.info.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`USERNAME`](#mc.admin.user.info.USERNAME) with the username of the user to display information for.

The `memberOf` property in the output contains a list of groups the user is a member of, with the policies attached to each group. The output resembles the following:

```shell
{
 "status": "success",
 "accessKey": "myuser",
 "userStatus": "enabled",
 "memberOf": [
  {
   "name": "testingGroup",
   "policies": [
    "testingGroupPolicy"
   ]
 "authentication": builtin (myuser)
  }
 ]
}
```

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

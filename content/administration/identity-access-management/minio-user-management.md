---
title: "User Management"
url: "/administration/identity-access-management/minio-user-management/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/identity-access-management/minio-user-management.rst
upstream_modified: false
---

<a id="user-management"></a>
<a id="minio-users"></a>

## Overview {#overview}

A MinIO user consists of a unique access key (username) and corresponding secret key (password). Clients must authenticate their identity by specifying both a valid access key (username) and the corresponding secret key (password) of an existing MinIO user.

Each user can have one or more assigned [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) that explicitly list the actions and resources to which that user has access. Users can also inherit policies from the [groups](/administration/identity-access-management/minio-group-management/#minio-groups) in which they have membership.

MinIO by default denies access to all actions or resources not explicitly allowed by a user’s assigned or inherited [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy). You must either explicitly assign a [policy](/administration/identity-access-management/policy-based-access-control/#minio-policy) describing the user’s authorized actions and resources *or* assign the user to [groups](/administration/identity-access-management/minio-group-management/#minio-groups) which have associated policies. See [Access Management](/administration/identity-access-management/#minio-access-management) for more information.

This page documents user management for the MinIO internal IDentity Provider (IDP). MinIO also external management of identities using either an OpenID Connect (OIDC) or Active Directory/LDAP IDentity Provider (IDP). For more information, see:

- [OpenID Connect Access Management](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid)
- [Active Directory / LDAP Access Management](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap)

Enabling external identity management disables the MinIO internal IDP, with the exception of creating [access keys](#minio-idp-service-account).

<a id="minio-id-access-keys"></a>
<a id="minio-idp-service-account"></a>

## Access Keys {#access-keys}

MinIO Access Keys (formerly “Service Accounts”) are child identities of an authenticated MinIO user, including [externally managed identities](/administration/identity-access-management/#minio-authentication-and-identity-management). Each access key inherits its privileges based on the [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) attached to it’s parent user *or* those groups in which the parent user has membership. Access keys also support an optional inline policy which further restricts access to a subset of actions and resources available to the parent user.

A MinIO user can generate any number of access keys. This allows application owners to generate arbitrary access keys for their applications without requiring action from the MinIO administrators. Since the generated access keys have the same or fewer permissions as the parents, administrators can focus on managing the top-level parent users without micro-managing generated access keys.

You can create access keys by using the [`mc admin user svcacct add`](/reference/minio-mc-admin/mc-admin-user-svcacct-add/#command-mc.admin.user.svcacct.add) command. Identities created by these methods do not expire until you remove the access key or the parent account.

You can also create [security token service](/developers/security-token-service/#minio-security-token-service) accounts programmatically with the `AssumeRole` STS API endpoint. STS tokens default to expire in 1 hour, but you set expiration for up to 7 days from creation.

> [!DETAILS]- Access Keys are for Programmatic Access
> Access Keys support programmatic access by applications. You cannot use an access key to log into the MinIO Console.

<a id="minio-users-root"></a>

## MinIO `root` User {#minio-root-user}

MinIO deployments have a `root` user with access to all actions and resources on the deployment, regardless of the configured [identity manager](/administration/identity-access-management/#minio-authentication-and-identity-management). When a [`minio`](/reference/minio-server/#command-minio) server first starts, it sets the `root` user credentials by checking the value of the following environment variables:

- [`MINIO_ROOT_USER`](/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_USER)
- [`MINIO_ROOT_PASSWORD`](/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_PASSWORD)

Rotating the root user credentials requires updating either or both variables for all MinIO servers in the deployment. Specify *long, unique, and random* strings for root credentials. Exercise all possible precautions in storing the access key and secret key, such that only known and trusted individuals who *require* superuser access to the deployment can retrieve the `root` credentials.

- MinIO *strongly discourages* using the `root` user for regular client access regardless of the environment (development, staging, or production).
- MinIO *strongly recommends* creating users such that each client has access to the minimal set of actions and resources required to perform their assigned workloads.

If these variables are unset, [`minio`](/reference/minio-server/#command-minio) defaults to `minioadmin` and `minioadmin` as the access key and secret key respectively. MinIO *strongly discourages* use of the default credentials regardless of deployment environment.

> [!DETAILS]- Deprecation of Legacy Root User Environment Variables
> MinIO [RELEASE.2021-04-22T15-44-28Z](https://github.com/minio/minio/releases/tag/RELEASE.2021-04-22T15-44-28Z) and later deprecates the following variables used for setting or updating root user credentials:
>
> - [`MINIO_ACCESS_KEY`](/reference/minio-server/settings/deprecated/#envvar.MINIO_ACCESS_KEY) to the new access key.
> - [`MINIO_SECRET_KEY`](/reference/minio-server/settings/deprecated/#envvar.MINIO_SECRET_KEY) to the new secret key.
> - [`MINIO_ACCESS_KEY_OLD`](/reference/minio-server/settings/deprecated/#envvar.MINIO_ACCESS_KEY_OLD) to the old access key.
> - [`MINIO_SECRET_KEY_OLD`](/reference/minio-server/settings/deprecated/#envvar.MINIO_SECRET_KEY_OLD) to the old secret key.

## User Management {#id1}

### Create a User {#create-a-user}

Use the [`mc admin user add`](/reference/minio-mc-admin/mc-admin-user-add/#command-mc.admin.user.add) command to create a new user on the MinIO deployment:

```shell
mc admin user add ALIAS ACCESSKEY SECRETKEY
```

- Replace [`ALIAS`](/reference/minio-mc-admin/mc-admin-user-add/#mc.admin.user.add.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`ACCESSKEY`](/reference/minio-mc-admin/mc-admin-user-add/#mc.admin.user.add.ACCESSKEY) with the access key for the user. MinIO allows retrieving the access key after user creation through the [`mc admin user info`](/reference/minio-mc-admin/mc-admin-user-info/#command-mc.admin.user.info) command.
- Replace [`SECRETKEY`](/reference/minio-mc-admin/mc-admin-user-add/#mc.admin.user.add.SECRETKEY) with the secret key for the user. MinIO *does not* provide any method for retrieving the secret key once set.

Specify a unique, random, and long string for both the `ACCESSKEY` and `SECRETKEY`. Your organization may have specific internal or regulatory requirements around generating values for use with access or secret keys.

After creating the user, use [`mc admin policy attach`](/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach) to associate a [MinIO Policy Based Access Control](/administration/identity-access-management/policy-based-access-control/#minio-policy) to the new user. The following command assigns the built-in [`readwrite`](/administration/identity-access-management/policy-based-access-control/#userpolicy.readwrite) policy:

```shell
mc admin policy attach ALIAS readwrite --user=USERNAME
```

Replace `USERNAME` with the `ACCESSKEY` created in the previous step.

### Delete a User {#delete-a-user}

Use the [`mc admin user rm`](/reference/minio-mc-admin/mc-admin-user-remove/#command-mc.admin.user.rm) command to remove a user on a MinIO deployment:

```shell
mc admin user rm ALIAS USERNAME
```

- Replace [`ALIAS`](/reference/minio-mc-admin/mc-admin-user-remove/#mc.admin.user.rm.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`USERNAME`](/reference/minio-mc-admin/mc-admin-user-remove/#mc.admin.user.rm.USERNAME) with the name of the user to remove.

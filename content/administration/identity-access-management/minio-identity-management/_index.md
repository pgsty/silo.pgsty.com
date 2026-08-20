---
title: "Silo Identity Management"
url: "/administration/identity-access-management/minio-identity-management/"
weight: 10
icon: fa-solid fa-user-shield
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/identity-access-management/minio-identity-management.rst
upstream_modified: true
---

<a id="minio-identity-management"></a>
<a id="minio-internal-idp"></a>

MinIO includes a built-in IDentity Provider (IDP) that provides core identity management functionality. The MinIO IDP supports creating an arbitrary number of long-lived users on the deployment for supporting client authentication.

Each user consists of a unique access key (username) and corresponding secret key (password). Clients must authenticate their identity by specifying both a valid access key (username) and the corresponding secret key (password) of an existing MinIO user.

Administrators use the [`mc admin user`](/reference/minio-mc-admin/mc-admin-user/#command-mc.admin.user) command to create and manage MinIO users.

MinIO also supports creating [access keys](/administration/identity-access-management/minio-user-management/#minio-idp-service-account). Access Keys are child identities of an authenticated parent user and inherit their permissions from the parent.

MinIO by default denies access to all actions or resources not explicitly allowed by a user’s assigned or inherited [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy). You must either explicitly assign a [policy](/administration/identity-access-management/policy-based-access-control/#minio-policy) describing the user’s authorized actions and resources *or* assign the user to [groups](/administration/identity-access-management/minio-group-management/#minio-groups) which have associated policies. See [Access Management](/administration/identity-access-management/#minio-access-management) for more information.

> [!NOTE]
> **External Identity Management**
>
> MinIO supports external management of identities using either an OpenID Connect (OIDC) or Active Directory/LDAP IDentity Provider (IDP). For more information, see:
>
> - [OpenID Connect Access Management](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid)
> - [Active Directory / LDAP Access Management](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap)
>
> AD/LDAP and OIDC configurations are mutually exclusive. Furthermore, enabling AD/LDAP external identity management disables the MinIO internal IDP, with the exception of creating [access keys](/administration/identity-access-management/minio-user-management/#minio-idp-service-account). You can configure multiple OIDC providers while maintaining MinIO-managed users.

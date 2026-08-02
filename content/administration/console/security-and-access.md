---
title: "Security and Access"
url: "/administration/console/security-and-access/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="security-and-access"></a>
<a id="minio-console-security-access"></a>

You can use the MinIO Console to perform several of the identity and access management functions available in MinIO, such as:

- Create child [access keys](#minio-console-user-access-keys) that inherit the parent’s permissions.
- View, manage, and create access [policies](#minio-console-admin-policies).
- Create and manage [user credentials](#minio-console-admin-identity) or groups with the built-in MinIO IDP, connect to one or more OIDC provider, or add an AD/LDAP provider for SSO.

<a id="minio-console-user-access-keys"></a>

## Access Keys {#access-keys}

The **Access Keys** or *Service Accounts* section displays all [Access Keys](/administration/identity-access-management/minio-user-management/#minio-id-access-keys) associated to the authenticated user. The summary list of access keys that already exist for a particular user includes the access key, expiration, status, name, and description.

Access Keys support providing applications authentication credentials which inherit permissions from the “parent” user.

For deployments using an external identity manager such as Active Directory or an OIDC-compatible provider, access keys provide a way for users to create long-lived credentials.

- You can select the access key row to view its custom policy, if one exists.

  > You can create or modify the policy from this screen. Access key policies cannot exceed the permissions granted to the parent user.
- You can create a new access key by selecting **Create access key**.

  > The Console auto-generates an access key and password. You can select the eye <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-eye" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M1.679 7.932c.412-.621 1.242-1.75 2.366-2.717C5.175 4.242 6.527 3.5 8 3.5c1.473 0 2.824.742 3.955 1.715 1.124.967 1.954 2.096 2.366 2.717a.119.119 0 010 .136c-.412.621-1.242 1.75-2.366 2.717C10.825 11.758 9.473 12.5 8 12.5c-1.473 0-2.824-.742-3.955-1.715C2.92 9.818 2.09 8.69 1.679 8.068a.119.119 0 010-.136zM8 2c-1.981 0-3.67.992-4.933 2.078C1.797 5.169.88 6.423.43 7.1a1.619 1.619 0 000 1.798c.45.678 1.367 1.932 2.637 3.024C4.329 13.008 6.019 14 8 14c1.981 0 3.67-.992 4.933-2.078 1.27-1.091 2.187-2.345 2.637-3.023a1.619 1.619 0 000-1.798c-.45-.678-1.367-1.932-2.637-3.023C11.671 2.992 9.981 2 8 2zm0 8a2 2 0 100-4 2 2 0 000 4z"></path></svg> icon on the password field to reveal the value. You can override these values as needed.
  >
  > You can set a custom policy for the access key that further restricts the permissions granted to users authenticating with that key. Select **Restrict beyond user policy** to open the policy editor and modify as necessary.
  >
  > Ensure you have saved the access key password to a secure location before selecting **Create** to create the access key. You cannot retrieve or reset the password value after creating the access key.
  >
  > To rotate credentials for an application, create a new access key and delete the old one once the application updates to using the new credentials.

<a id="minio-console-admin-policies"></a>

## Policies {#policies}

The **Policies** section displays all [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) on the MinIO deployment. The Policies section allows you to create, modify, or delete policies.

[Policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) define the authorized actions and resources to which an authenticated user has access. Each policy describes one or more actions a user, group of users, or access key can perform or conditions they must meet.

The policies are JSON formatted text files compatible with Amazon AWS Identity and Access Management policy syntax, structure, and behavior. Refer to [Policy Based Action Control](/administration/identity-access-management/policy-based-access-control/#minio-policy) for details on managing access in MinIO with policies.

This section or its contents may not be visible if the authenticated user does not have the [required administrative permissions](/administration/identity-access-management/policy-based-access-control/#minio-policy-mc-admin-actions).

- Select **+ Create Policy** to create a new MinIO Policy.
- Select the policy row to manage the policy details.

  The **Summary** view displays a summary of the policy.

  The **Users** view displays all users assigned to the policy.

  The **Groups** view displays all groups assigned to the policy.

  The **Raw Policy** view displays the raw JSON policy.

Use the **Users** and **Groups** views to assign a created policy to users and groups, respectively.

<a id="identity"></a>

## Identity {#minio-console-admin-identity}

The **Identity** section provides a management interface for [MinIO-Managed users](/administration/identity-access-management/minio-user-management/#minio-users).

The section contains the following subsections. Some subsections may not be visible if the authenticated user does not have the [required administrative permissions](/administration/identity-access-management/policy-based-access-control/#minio-policy-mc-admin-actions).

### Users {#users}

The **Users** section displays all MinIO-managed [users](/administration/identity-access-management/minio-user-management/#minio-users) on the deployment.

This section is not visible for deployments using an external identity manager such as Active Directory or an OIDC-compatible provider.

- Select **Create User** to create a new MinIO-managed user.

  You can assign [groups](/administration/identity-access-management/minio-group-management/#minio-groups) and [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) to the user during creation.
- Select a user’s row to view details for that user.

  You can view and modify the user’s assigned [groups](/administration/identity-access-management/minio-group-management/#minio-groups) and [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy).

  You can also view and manage any [Access Keys](/administration/identity-access-management/minio-user-management/#minio-idp-service-account) associated to the user.

### Groups {#groups}

The **Groups** section displays all [groups](/administration/identity-access-management/minio-group-management/#minio-groups) on the MinIO deployment.

This section is not visible for deployments using an external identity manager such as Active Directory or an OIDC-compatible provider.

- Select **Create Group** to create a new MinIO Group.

  You can assign new users to the group during creation.

  You can assign policies to the group after creation.
- Select the group row to open the details for that group.

  You can modify the group membership from the **Members** view.

  You can modify the group’s assigned policies from the **Policies** view.

  Changing a user’s group membership modifies the policies that user inherits. See [Access Management](/administration/identity-access-management/#minio-access-management) for more information.

### OpenID {#openid}

MinIO supports using an [OpenID Connect (OIDC) compatible IDentity Provider (IDP)](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid) for external management of user identities.

Examples of OpenID providers include:

- Okta
- KeyCloak
- Dex
- Google
- Facebook

Configuring an external IDP enables Single-Sign On workflows, where applications authenticate against the external IDP before accessing MinIO.

Use the the screens in this section to view, add, or edit OIDC configurations for the deployment. MinIO supports any number of active OIDC configurations.

<a id="minio-console-admin-identity-ldap"></a>

### LDAP {#ldap}

MinIO supports using an [Active Directory or LDAP (AD/LDAP)](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap) service for external management of user identities. Configuring an external IDentity Provider (IDP) enables Single-Sign On (SSO) workflows, where applications authenticate against the external IDP before accessing MinIO.

Use the the screens in this section to view, add, or edit an LDAP configuration for the deployment. MinIO only supports one active LDAP configuration.

MinIO queries the Active Directory / LDAP server to verify the client-specified credentials. MinIO also performs a group lookup on the AD/LDAP server if configured to do so.

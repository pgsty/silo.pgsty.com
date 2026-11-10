---
title: "Security and Access"
url: "/administration/console/security-and-access/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/console/security-and-access.rst
upstream_modified: true
---

> [!NOTE]
> **SILO 20261109 and Console v2.7.0 updates:**
> - **Console root login with LDAP ([#272](https://github.com/pgsty/silo/issues/272)):** The `root` user can sign in to the embedded Console when Active Directory / LDAP is enabled.
> - **Long-DN LDAP login on erasure sets ([#271](https://github.com/pgsty/silo/issues/271)):** LDAP users whose normalized DN exceeds the 255-byte single-component limit can sign in on multi-drive erasure-set deployments.
> - **Persisted IAM mutations and complete policy loads ([#316](https://github.com/pgsty/silo/issues/316), [#317](https://github.com/pgsty/silo/issues/317), [#321](https://github.com/pgsty/silo/issues/321)–[#323](https://github.com/pgsty/silo/issues/323)):** IAM user, group, policy, LDAP group refresh, and service-account edits apply directly to stored records, and IAM refuses incomplete policy loads while keeping cached authentication active during lazy reloads so stale nodes cannot restore old credentials or deleted identities.
> - **Arabic RTL field controls ([Console v2.7.0](/blog/release/console-2.7.0/)):** Password reveal buttons and field unit selectors stay beside input text instead of overlapping it in Arabic right-to-left layout.
> - **Earlier Console 2.5.1 / Server 20261026 updates:** Toggling group status preserves existing members, OIDC string-array group claims are parsed, session cookies retain `Secure` under HTTPS or a trusted TLS proxy, newly created access keys export clean UTF-8 JSON credentials, and built-in policy **Reset** requires [SILO 20261026](/blog/release/silo-20261026/#server-20261026) or later ([Console 2.5.1](/blog/release/console-2.5.1/)).

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

  You can create or modify the policy from this screen. Access key policies cannot exceed the permissions granted to the parent user.
- You can create a new access key by selecting **Create access key**.

  The Console auto-generates an access key and password. Select the password reveal icon on the password field to show the value, or override these values as needed.

  You can set a custom policy for the access key that further restricts the permissions granted to users authenticating with that key. Select **Restrict beyond user policy** to open the policy editor and modify as necessary.

  Ensure you have saved the access key password to a secure location before selecting **Create** to create the access key. You cannot retrieve or reset the password value after creating the access key.

  To rotate credentials for an application, create a new access key and delete the old one once the application updates to using the new credentials.

<a id="minio-console-admin-policies"></a>

## Policies {#policies}

Console v2.5.1 provides **Reset** for built-in policies and **Delete** for custom policies. **Reset** removes a stored built-in policy override and restores SILO's native definition. The [Server 20261026](/blog/release/silo-20261026/#server-20261026) makes the restored definition immediately readable and reloads committed state on peer/etcd notifications so delayed notifications cannot overwrite a later edit (in-use checks still apply).

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

Use the screens in this section to view, add, or edit OIDC configurations for the deployment. MinIO supports any number of active OIDC configurations.

<a id="minio-console-admin-identity-ldap"></a>

### LDAP {#ldap}

MinIO supports using an [Active Directory or LDAP (AD/LDAP)](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap) service for external management of user identities. Configuring an external IDentity Provider (IDP) enables Single-Sign On (SSO) workflows, where applications authenticate against the external IDP before accessing MinIO.

Use the screens in this section to view, add, or edit an LDAP configuration for the deployment. MinIO only supports one active LDAP configuration.

MinIO queries the Active Directory / LDAP server to verify the client-specified credentials. MinIO also performs a group lookup on the AD/LDAP server if configured to do so. Since [SILO 20261109](/blog/release/silo-20261109/), the `root` user can sign in to the embedded Console when LDAP is enabled ([#272](https://github.com/pgsty/silo/issues/272)), and group-authorized LDAP users with long normalized DNs (> 255-byte component) can log in on multi-drive erasure-set deployments ([#271](https://github.com/pgsty/silo/issues/271)).

---
title: "Identity and Access Management"
url: "/administration/identity-access-management/"
weight: 140
icon: fa-solid fa-users-gear
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/identity-access-management.rst
upstream_modified: false
---

<a id="minio-authentication-and-identity-management"></a>
<a id="identity-and-access-management"></a>

MinIO requires the client perform both authentication and authorization for each new operation.

**Authentication**

> The process of verifying the identity of a connecting client. MinIO requires clients authenticate using [AWS Signature Version 4 protocol](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) with support for the deprecated Signature Version 2 protocol. Specifically, clients must present a valid access key and secret key to access any S3 or MinIO administrative API, such as `PUT`, `GET`, and `DELETE` operations.

**Authorization**

> The process of restricting the actions and resources the authenticated client can perform on the deployment. MinIO uses Policy-Based Access Control (PBAC), where each policy describes one or more rules that outline the permissions of a user or group of users. MinIO supports S3-specific [actions](/administration/identity-access-management/policy-based-access-control/#minio-policy-actions) and [conditions](/administration/identity-access-management/policy-based-access-control/#minio-policy-conditions) when creating policies. By default, MinIO *denies* access to actions or resources not explicitly referenced in a user’s assigned or inherited policies.

## Identity Management {#identity-management}

MinIO supports both internal and external identity management:

| IDentity Provider (IDP) | Description |
| --- | --- |
| [MinIO Internal IDP](/administration/identity-access-management/minio-identity-management/#minio-internal-idp) | Provides built-in identity management functionality. |
| [OpenID](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid) | Supports managing identities through an OpenID Connect (OIDC) compatible service. |
| [MinIO Authentation Plugin](/administration/identity-access-management/pluggable-authentication/#minio-external-identity-management-plugin) | Supports a custom external identity manager using the MinIO Authentication Plugin extension. |
| [Active Directory / LDAP](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap) | Supports managing identities through an Active Directory or LDAP service. |
| [Access Management Plugin](/administration/identity-access-management/pluggable-authorization/#minio-external-access-management-plugin) | Supports a custom external access manager using the MinIO Access Management Plugin extension. |

Once authenticated, MinIO either allows or rejects the client request depending on whether or not the authenticated identity is *authorized* to perform the operation on the specified resource.

<a id="minio-access-management"></a>

## Access Management {#access-management}

MinIO uses Policy-Based Access Control (PBAC) to define the authorized actions and resources to which an authenticated user has access. Each policy describes one or more [actions](/administration/identity-access-management/policy-based-access-control/#minio-policy-actions) and [conditions](/administration/identity-access-management/policy-based-access-control/#minio-policy-conditions) that outline the permissions of a [user](/administration/identity-access-management/minio-user-management/#minio-users) or [group](/administration/identity-access-management/minio-group-management/#minio-groups) of users.

MinIO manages the creation and storage of policies. The process for assigning a policy to a user or group depends on the configured [IDentity Provider (IDP)](#minio-authentication-and-identity-management).

MinIO deployments using the [MinIO Internal IDP](/administration/identity-access-management/minio-identity-management/#minio-internal-idp) require explicitly associating a user to a policy or policies using the [`mc admin policy attach`](/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach) command. A user can also inherit the policies attached to the [groups](/administration/identity-access-management/minio-group-management/#minio-groups) in which they have membership.

By default, MinIO *denies* access to actions or resources not explicitly allowed by an attached or inherited policy. A user with no explicitly assigned or inherited policies cannot perform any S3 or MinIO administrative API operations.

For MinIO deployments using an External IDP, policy assignment depends on the choice of IDP:

<table>
  <tbody>
    <tr>
      <td><p><a href="/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid">OpenID Connect (OIDC)</a></p></td>
      <td><p>MinIO checks for a JSON Web Token (JWT) claim (<code>policy</code> by default)
containing the name of the policy or policies to attach to the
authenticated user. If the policies do not exist, the user cannot
perform any action on the MinIO deployment.</p><p>MinIO does not support assigning OIDC user identities to
<a href="/administration/identity-access-management/minio-group-management/#minio-groups">groups</a>. The IDP administrator must instead
assign all necessary policies to the user’s policy claim.</p><p>See <a href="/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid-access-control">Access Control for Externally Managed Identities</a> for
more information.</p></td>
    </tr>
    <tr>
      <td><p><a href="/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap">Active Directory / LDAP (AD/LDAP)</a></p></td>
      <td><p>MinIO checks for a policy whose name matches the Distinguished Name (DN)
of the authenticated AD/LDAP user.</p><p>MinIO also supports querying for the authenticated AD/LDAP user’s
group memberships. MinIO assigns any policy whose name matches the
DN for each returned group.</p><p>If no policies match either the user DN <em>or</em> any of the user’s group DNs,
the user cannot perform any action on the MinIO deployment.</p><p>See <a href="/operations/external-iam/#minio-external-identity-management-ad-ldap-access-control">Access Control for Externally Managed Identities</a> for more
information.</p></td>
    </tr>
  </tbody>
</table>

MinIO PBAC is built for compatibility with AWS IAM policy syntax, structure, and behavior. The MinIO documentation makes a best-effort to cover IAM-specific behavior and functionality. Consider deferring to the [IAM documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/) for more complete documentation on IAM, IAM policies, or IAM JSON syntax.

> [!NOTE]
> **`Deny` overrides `Allow`**
>
> MinIO follows AWS IAM policy evaluation rules where a `Deny` rule overrides `Allow` rule on the same action/resource. For example, if a user has an explicitly assigned policy with an `Allow` rule for an action/resource while one of its groups has an assigned policy with a `Deny` rule for that action/resource, MinIO would apply only the `Deny` rule.
>
> For more information on IAM policy evaluation logic, see the IAM documentation on [Determining Whether a Request is Allowed or Denied Within an Account](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html#policy-eval-denyallow).

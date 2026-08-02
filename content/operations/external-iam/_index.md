---
title: "External Identity Management"
url: "/operations/external-iam/"
weight: 50
icon: fa-solid fa-id-card
minio_origin: true
silo_modified: false
---

<a id="external-identity-management"></a>
<a id="minio-external-identity-management"></a>

MinIO supports multiple external identity managers through the following IDentity Providers (IDP):

- [OpenID Connect-Compatible](#minio-external-iam-oidc)
- [Active Directory / LDAP](#minio-external-iam-ad-ldap)

The following tutorials provide specific guidance for select IDP software:

- [Configure MinIO Authentication with KeyCloak](/operations/external-iam/configure-keycloak-identity-management/#minio-authenticate-using-keycloak)

Users can authenticate against MinIO using their externally managed credentials and the related [Security Token Service (STS)](/developers/security-token-service/#minio-security-token-service) API. Once authenticated, MinIO attempts to associate the user with one or more configured [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy). A user with no associated policies has no permissions on the MinIO deployment.

<a id="minio-external-iam-oidc"></a>

## OpenID Connect (OIDC) {#openid-connect-oidc}

MinIO supports using an OpenID Connect (OIDC) compatible IDentity Provider (IDP) such as Okta, KeyCloak, Dex, Google, or Facebook for external management of user identities. Configuring an external <abbr title="IDentity Provider">IDP</abbr> enables Single-Sign On workflows, where applications authenticate against the external <abbr title="IDentity Provider">IDP</abbr> before accessing MinIO.

MinIO uses [Policy Based Access Control (PBAC)](/administration/identity-access-management/#minio-access-management) to define the actions and resources to which an authenticated user has access. MinIO supports creating and managing [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) which an externally managed user can claim.

For identities managed by the external OpenID Connect (OIDC) compatible provider, MinIO uses a [JSON Web Token claim](https://datatracker.ietf.org/doc/html/rfc7519#section-4) to identify the [policy](/administration/identity-access-management/policy-based-access-control/#minio-policy) to assign to the authenticated user.

MinIO by default looks for a `policy` claim and reads a list of one or more policies to assign. MinIO attempts to match existing policies to those specified in the JWT claim. If none of the specified policies exist on the MinIO deployment, MinIO denies authorization for any and all operations issued by that user. For example, consider a claim with the following key-value assignment:

```shell
policy="readwrite_data,read_analytics,read_logs"
```

The specified policy claim directs MinIO to attach the policies with names matching `readwrite_data`, `read_analytics`, and `read_logs` to the authenticated user.

You can set a custom policy claim using the [`MINIO_IDENTITY_OPENID_CLAIM_NAME`](/reference/minio-server/settings/iam/openid/#envvar.MINIO_IDENTITY_OPENID_CLAIM_NAME) environment variable *or* by using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set the [`identity_openid claim_name`](/reference/minio-server/settings/iam/openid/#mc-conf.identity_openid.claim_name) setting.

See [OpenID Connect Access Management](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid-access-control) for more information on mapping MinIO policies to an OIDC-managed identity.

You can use a [JWT Debugging tool](https://jwt.io/) to decode the returned JWT token and validate that the user attributes include the specified claim. See [RFC 7519: JWT Claim](https://datatracker.ietf.org/doc/html/rfc7519#section-4) for more information on JWT claims. Defer to the documentation for your preferred OIDC provider for instructions on configuring user claims.

<a id="minio-external-iam-ad-ldap"></a>

## Active Directory / LDAP {#active-directory-ldap}

MinIO supports using an Active Directory or LDAP (AD/LDAP) service for external management of user identities. Configuring an external IDentity Provider (IDP) enables Single-Sign On (SSO) workflows, where applications authenticate against the external IDP before accessing MinIO.

<a id="minio-external-identity-management-ad-ldap-lookup-bind"></a>

### Querying the Active Directory / LDAP Service {#querying-the-active-directory-ldap-service}

MinIO queries the configured Active Directory / LDAP server to verify the credentials specified by the application and optionally return a list of groups in which the user has membership. This process, called Lookup-Bind mode, uses an AD/LDAP user with minimal permissions, only sufficient to authenticate with the AD/LDAP server for user and group lookups.

The following tabs provide a reference of the environment variables and configuration settings required for enabling Lookup-Bind mode.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
- [`MINIO_IDENTITY_LDAP_LOOKUP_BIND_DN`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_LOOKUP_BIND_DN)
- [`MINIO_IDENTITY_LDAP_LOOKUP_BIND_PASSWORD`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_LOOKUP_BIND_PASSWORD)
- [`MINIO_IDENTITY_LDAP_USER_DN_SEARCH_BASE_DN`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_USER_DN_SEARCH_BASE_DN)
- [`MINIO_IDENTITY_LDAP_USER_DN_SEARCH_FILTER`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_USER_DN_SEARCH_FILTER)

See the [Active Directory / LDAP Settings](/reference/minio-server/settings/iam/ldap/#minio-server-envvar-external-identity-management-ad-ldap) reference documentation for more information on these variables. The [Configure MinIO for Authentication using Active Directory / LDAP](/operations/external-iam/configure-ad-ldap-external-identity-management/#minio-authenticate-using-ad-ldap-generic) tutorial includes complete instructions on setting these values.
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
- [`identity_ldap lookup_bind_dn`](/reference/minio-server/settings/iam/ldap/#mc-conf.identity_ldap.lookup_bind_dn)
- [`identity_ldap lookup_bind_password`](/reference/minio-server/settings/iam/ldap/#mc-conf.identity_ldap.lookup_bind_password)
- [`identity_ldap user_dn_search_base_dn`](/reference/minio-server/settings/iam/ldap/#mc-conf.identity_ldap.user_dn_search_base_dn)
- [`identity_ldap user_dn_search_filter`](/reference/minio-server/settings/iam/ldap/#mc-conf.identity_ldap.user_dn_search_filter)

See the [`identity_ldap`](/reference/minio-server/settings/iam/ldap/#mc-conf.identity_ldap) reference documentation for more information on these settings. The [Configure MinIO for Authentication using Active Directory / LDAP](/operations/external-iam/configure-ad-ldap-external-identity-management/#minio-authenticate-using-ad-ldap-generic) tutorial includes complete instructions on setting these variables.
{{% /tab %}}
{{< /tabpane >}}

<a id="minio-external-identity-management-ad-ldap-access-control"></a>

### Access Control for AD/LDAP-Managed Identities {#access-control-for-ad-ldap-managed-identities}

MinIO uses [Policy Based Access Control (PBAC)](/administration/identity-access-management/#minio-access-management) to define the actions and resources to which an authenticated user has access. When using an Active Directory/LDAP server for identity management (authentication), MinIO maintains control over access (authorization) through PBAC.

When a user successfully authenticates to MinIO using their AD/LDAP credentials, MinIO searches for all [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) which are explicitly associated to that user’s Distinguished Name (DN). Specifically, the policy must be assigned to a user with a matching DN using the [`mc idp ldap policy attach`](/reference/minio-mc/mc-idp-ldap-policy-attach/#command-mc.idp.ldap.policy.attach) command.

MinIO also supports querying for the user’s AD/LDAP group membership. MinIO attempts to match existing policies to the DN for each of the user’s groups. The authenticated users complete set of permissions consists of its explicitly assigned and group-inherited policies. See [Group Lookup](#minio-external-identity-management-ad-ldap-access-control-group-lookup) for more information.

MinIO uses deny-by-default behavior where a user with no explicitly assigned or group-inherited policies cannot access any resource on the MinIO deployment.

MinIO provides [built-in policies](/administration/identity-access-management/policy-based-access-control/#minio-policy-built-in) for basic access control. You can create new policies using the [`mc admin policy create`](/reference/minio-mc-admin/mc-admin-policy-create/#command-mc.admin.policy.create) command.

<a id="minio-external-identity-management-ad-ldap-access-control-group-lookup"></a>

#### Group Lookup {#group-lookup}

MinIO supports querying the Active Directory / LDAP server for a list of groups in which the authenticated user has membership. MinIO attempts to match existing [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) to each group DN and assigns each matching policy to the authenticated user.

The following tabs provide a reference of the environment variables and configuration settings required for enabling group lookups:

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
- [`MINIO_IDENTITY_LDAP_GROUP_SEARCH_BASE_DN`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_GROUP_SEARCH_BASE_DN)
- [`MINIO_IDENTITY_LDAP_GROUP_SEARCH_FILTER`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_GROUP_SEARCH_FILTER)

See the [Active Directory / LDAP Settings](/reference/minio-server/settings/iam/ldap/#minio-server-envvar-external-identity-management-ad-ldap) reference documentation for more information on these variables. The [Configure MinIO for Authentication using Active Directory / LDAP](/operations/external-iam/configure-ad-ldap-external-identity-management/#minio-authenticate-using-ad-ldap-generic) tutorial includes complete instructions on setting these values.
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
- [`identity_ldap group_search_base_dn`](/reference/minio-server/settings/iam/ldap/#mc-conf.identity_ldap.group_search_base_dn)
- [`identity_ldap group_search_filter`](/reference/minio-server/settings/iam/ldap/#mc-conf.identity_ldap.group_search_filter)

See the [`identity_ldap`](/reference/minio-server/settings/iam/ldap/#mc-conf.identity_ldap) reference documentation for more information on these settings. The [Configure MinIO for Authentication using Active Directory / LDAP](/operations/external-iam/configure-ad-ldap-external-identity-management/#minio-authenticate-using-ad-ldap-generic) tutorial includes complete instructions on setting these variables.
{{% /tab %}}
{{< /tabpane >}}

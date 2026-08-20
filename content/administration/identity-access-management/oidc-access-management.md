---
title: "OpenID Connect Access Management"
url: "/administration/identity-access-management/oidc-access-management/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/identity-access-management/oidc-access-management.rst
upstream_modified: false
---

<a id="openid-connect-access-management"></a>
<a id="minio-external-identity-management-openid-access-control"></a>
<a id="minio-external-identity-management-openid"></a>

MinIO supports using an OpenID Connect (OIDC) compatible IDentity Provider (IDP) such as Okta, KeyCloak, Dex, Google, or Facebook for external management of user identities.

For identities managed by the external OpenID Connect (OIDC) compatible provider, MinIO can use either of two methods to assign policies to the authenticated user.

1. Use the [JSON Web Token claim](https://datatracker.ietf.org/doc/html/rfc7519#section-4) returned as part of the OIDC authentication flow to identify the [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) to assign to the authenticated user.
2. Use the `RoleArn` specified in the authorization request to assign the policies attached to the provider’s RolePolicy.

MinIO by default denies access to all actions or resources not explicitly allowed by a user’s assigned or inherited [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy). Users managed by an OIDC provider must specify the necessary policies as part of the JWT claim. If the user JWT claim has no matching MinIO policies, that user has no permissions to access any action or resource on the MinIO deployment.

The specific claim which MinIO looks for is configured as part of [deploying the cluster with OIDC identity management](/operations/external-iam/#minio-external-iam-oidc). This page focuses on creating MinIO policies to match the configured OIDC claims.

## Authentication and Authorization Flow {#authentication-and-authorization-flow}

MinIO supports two OIDC authentication and authorization flows:

1. The RolePolicy flow sets the assigned policies for an authenticated user in the MinIO configuration.

   MinIO recommends using the RolePolicy method for authenticating with an OpenID provider.
2. The JWT flow sets the assigned policies for an authenticated user as part of the OIDC configuration.

MinIO supports multiple OIDC provider configurations. However, you can configure only **one** JWT claim-based OIDC provider per deployment. All other providers must use RolePolicy.

### RolePolicy and RoleArn {#rolepolicy-and-rolearn}

With a RolePolicy, all clients which generate an STS credential using a given RoleArn receive the [policy or policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) associated to the RolePolicy configuration for that RoleArn.

You can use [OpenID Policy Variables](/administration/identity-access-management/policy-based-access-control/#minio-policy-variables-oidc) to create policies that programmatically manage what each individual user has access to.

The login flow for an application using <abbr title="OpenID Connect">OIDC</abbr> credentials with a RolePolicy claim flow is as follows:

1. Create an OIDC Configuration.
2. Record the RoleArn assigned to the configuration either at time of creation or at MinIO start. Use this RoleArn with the [AssumeRoleWithWebIdentity](/developers/security-token-service/AssumeRoleWithWebIdentity/#minio-sts-assumerolewithwebidentity) STS API.
3. Create a RolePolicy to use with the RoleArn. Use either the [`MINIO_IDENTITY_OPENID_ROLE_POLICY`](/reference/minio-server/settings/iam/openid/#envvar.MINIO_IDENTITY_OPENID_ROLE_POLICY) environment variable or the [`identity_openid role_policy`](/reference/minio-server/settings/iam/openid/#mc-conf.identity_openid.role_policy) configuration setting to define the list of policies to use for the provider
4. Users select the configured OIDC provider when logging in to MinIO.
5. Users complete authentication to the configured <abbr title="OpenID Connect">OIDC</abbr> provider and redirect back to MinIO.

   MinIO only supports the [OpenID Authorization Code Flow](https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth). Authentication using Implicit Flow is not supported.
6. MinIO verifies the `RoleArn` in the API call and checks for the [RolePolicy](#minio-external-identity-management-openid-access-control) to use. Any authentication request with the RoleArn receives the same policy access permissions.
7. MinIO returns temporary credentials in the STS API response in the form of an access key, secret key, and session token. The credentials have permissions matching those policies specified in the RolePolicy.
8. Applications use the temporary credentials returned by the STS endpoint to perform authenticated S3 operations on MinIO.

### JSON Web Token Claim {#json-web-token-claim}

Using JSON Web Tokens allows you to have individual assignment of policies. However, the use of web tokens also comes at the increased cost of managing multiple policies for separate claims.

The login flow for an application using <abbr title="OpenID Connect">OIDC</abbr> credentials with a JSON Web Token Claim flow is as follows:

1. Authenticate to the configured <abbr title="OpenID Connect">OIDC</abbr> provider and retrieve a [JSON Web Token (JWT)](https://jwt.io/introduction).

   MinIO only supports the [OpenID Authorization Code Flow](https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth). Authentication using Implicit Flow is not supported.
2. Specify the <abbr title="JSON Web Token">JWT</abbr> to the MinIO Security Token Service (STS) [AssumeRoleWithWebIdentity](/developers/security-token-service/AssumeRoleWithWebIdentity/#minio-sts-assumerolewithwebidentity) API endpoint.

   MinIO verifies the <abbr title="JSON Web Token">JWT</abbr> against the configured OIDC provider.

   If the JWT is valid, MinIO checks for a [claim](#minio-external-identity-management-openid-access-control) specifying a list of one or more [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) to assign to the authenticated user. MinIO defaults to checking the `policy` claim.
3. MinIO returns temporary credentials in the STS API response in the form of an access key, secret key, and session token. The credentials have permissions matching those policies specified in the JWT claim.
4. Applications use the temporary credentials returned by the STS endpoint to perform authenticated S3 operations on MinIO.

MinIO provides an example Go application [web-identity.go](https://github.com/minio/minio/blob/master/docs/sts/web-identity.go) that handles the full login flow.

#### Identifying the JWT Claim Value {#identifying-the-jwt-claim-value}

MinIO uses the JWT token returned as part of the OIDC authentication flow to identify the specific policies to assign to the authenticated user.

You can use a [JWT Debugging tool](https://jwt.io/) to decode the returned JWT token and validate that the user attributes include the required claims.

See [RFC 7519: JWT Claim](https://datatracker.ietf.org/doc/html/rfc7519#section-4) for more information on JWT claims.

Defer to the documentation for your preferred OIDC provider for instructions on configuring user claims.

## Creating Policies to Match Claims {#creating-policies-to-match-claims}

Use the [`mc admin policy`](/reference/minio-mc-admin/mc-admin-policy/#command-mc.admin.policy) command to create policies that match one or more claim values.

## OIDC Policy Variables {#oidc-policy-variables}

The following table contains a list of supported policy variables for use in authorizing [OIDC-managed users](#minio-external-identity-management-openid).

Each variable corresponds to a claim returned as part of the authenticated user’s JWT token:

| Variable | Description |
| --- | --- |
| `jwt:sub` | Returns the `sub` claim for the user. |
| `jwt:iss` | Returns the Issuer Identifier claim from the ID token. |
| `jwt:aud` | Returns the Audience claim from the ID token. |
| `jwt:jti` | Returns the JWT ID claim from the client authentication information. |
| `jwt:upn` | Returns the User Principal Name claim from the client authentication information. |
| `jwt:name` | Returns the `name` claim for the user. |
| `jwt:groups` | Returns the `groups` claim for the user. |
| `jwt:given_name` | Returns the `given_name` claim for the user. |
| `jwt:family_name` | Returns the `family_name` claim for the user. |
| `jwt:middle_name` | Returns the `middle_name` claim for the user. |
| `jwt:nickname` | Returns the `nickname` claim for the user. |
| `jwt:preferred_username` | Returns the `preferred_username` claim for the user. |
| `jwt:profile` | Returns the `profile` claim for the user. |
| `jwt:picture` | Returns the `picture` claim for the user. |
| `jwt:website` | Returns the `website` claim for the user. |
| `jwt:email` | Returns the `email` claim for the user. |
| `jwt:gender` | Returns the `gender` claim for the user. |
| `jwt:birthdate` | Returns the `birthdate` claim for the user. |
| `jwt:phone_number` | Returns the `phone_number` claim for the user. |
| `jwt:address` | Returns the `address` claim for the user. |
| `jwt:scope` | Returns the `scope` claim for the user. |
| `jwt:client_id` | Returns the `client_id` claim for the user. |

See the [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html) document for more information on these scopes. Your OIDC provider of choice may have more specific documentation.

For example, the following policy uses variables to substitute the authenticated user’s `preferred_username` as part of the `Resource` field such that the user can only access those prefixes which match their username:

```json
{
"Version": "2012-10-17",
"Statement": [
      {
         "Action": ["s3:ListBucket"],
         "Effect": "Allow",
         "Resource": ["arn:aws:s3:::mybucket"],
         "Condition": {"StringLike": {"s3:prefix": ["${jwt:preferred_username}/*"]}}
      },
      {
         "Action": [
         "s3:GetObject",
         "s3:PutObject"
         ],
         "Effect": "Allow",
         "Resource": ["arn:aws:s3:::mybucket/${jwt:preferred_username}/*"]
      }
   ]
}
```

MinIO replaces the `${jwt:preferred_username}` variable in the `Resource` field with the value of the `preferred_username` in the JWT token. MinIO then evaluates the policy and grants or revokes access to the requested API and resource.

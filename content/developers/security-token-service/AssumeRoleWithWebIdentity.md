---
title: "AssumeRoleWithWebIdentity"
url: "/developers/security-token-service/AssumeRoleWithWebIdentity/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/developers/security-token-service/AssumeRoleWithWebIdentity.rst
upstream_modified: false
---

<a id="assumerolewithwebidentity"></a>
<a id="minio-sts-assumerolewithwebidentity"></a>

The MinIO Security Token Service (STS) `AssumeRoleWithWebIdentity` API endpoint generates temporary access credentials using a JSON Web Token (JWT) returned from a [configured OpenID IDentity Provider (IDP)](/operations/external-iam/configure-openid-external-identity-management/#minio-external-identity-management-openid-configure). This page documents the MinIO server `AssumeRoleWithWebIdentity` endpoint. For instructions on implementing STS using an S3-compatible SDK, defer to the documentation for that SDK.

The MinIO STS `AssumeRoleWithWebIdentity` API endpoint is modeled after the AWS [AssumeRoleWithWebIdentity](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRoleWithWebIdentity.html) endpoint and shares certain request/response elements. This page documents the MinIO-specific syntax and links out to the AWS reference for all shared elements.

## Request Endpoint {#request-endpoint}

The `AssumeRoleWithWebIdentity` endpoint has the following form:

```shell
POST https://minio.example.net?Action=AssumeRoleWithWebIdentity[&ARGS]
```

The following example uses all supported arguments. Replace the `minio.example.net` hostname with the appropriate URL for your MinIO cluster:

```shell
POST https://minio.example.net?Action=AssumeRoleWithWebIdentity
&WebIdentityToken=TOKEN
&Version=2011-06-15
&DurationSeconds=86000
&Policy={}
```

<a id="minio-assumerolewithwebidentity-query-parameters"></a>

### Request Query Parameters {#request-query-parameters}

This endpoint supports the following query parameters:

<table>
  <thead>
    <tr>
      <th><p>Parameter</p></th>
      <th><p>Type</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><code>WebIdentityToken</code></p></td>
      <td><p>string</p></td>
      <td><p><em>Required</em></p><p>Specify the JSON Web Token (JWT) returned by the
<a href="/operations/external-iam/configure-openid-external-identity-management/#minio-external-identity-management-openid-configure">configured OpenID IDentity Provider</a>.</p></td>
    </tr>
    <tr>
      <td><p><code>Version</code></p></td>
      <td><p>string</p></td>
      <td><p><em>Required</em></p><p>Specify <code>2011-06-15</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>DurationSeconds</code></p></td>
      <td><p>integer</p></td>
      <td><p><em>Optional</em></p><p>Specify the number of seconds after which the temporary credentials
expire. Defaults to <code>3600</code>.</p><ul><li><p>The minimum value is <code>900</code> or 15 minutes.</p></li><li><p>The maximum value is <code>604800</code> or 7 days.</p></li></ul><p>If <code>DurationSeconds</code> is omitted, MinIO checks the JWT token for an
<code>exp</code> claim before using the default duration. See
<a href="https://datatracker.ietf.org/doc/html/rfc7519#section-4.1.4">RFC 7519 4.1.4: Expiration Time Claim</a>
for more information on JSON web token expiration.</p></td>
    </tr>
    <tr>
      <td><p><code>Policy</code></p></td>
      <td><p>string</p></td>
      <td><p><em>Optional</em></p><p>Specify the URL-encoded JSON-formatted <a href="/administration/identity-access-management/policy-based-access-control/#minio-policy">policy</a> to
use as an inline session policy.</p><ul><li><p>The minimum string length is <code>1</code>.</p></li><li><p>The maximum string length is <code>2048</code>.</p></li></ul><p>The resulting permissions for the temporary credentials are the
intersection between the policy specified as part of the <a href="/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid-access-control">JWT claim</a> and the specified inline
policy. Applications can only perform those operations for which they
are explicitly authorized.</p><p>The inline policy can specify a subset of permissions allowed by the
policy specified in the JWT claim. Applications can never assume
more privileges than those specified in the JWT claim policy.</p><p>Omit to use only the JWT claim policy.</p><p>See <a href="/administration/identity-access-management/#minio-access-management">Access Management</a> for more information on MinIO
authentication and authorization.</p></td>
    </tr>
    <tr>
      <td><p><code>RoleArn</code></p></td>
      <td><p>string</p></td>
      <td><p><em>Optional</em></p><p>The role Amazon Resource Number (ARN) to use for all user authentication requests.
If used, there must be a matching OIDC RolePolicy defined for the RoleArn’s provider by the <code>role_policy</code> configuration parameter or the <code>MINIO_IDENTITY_OPENID_ROLE_POLICY</code> environment variable.</p><p>When used, all valid authorization requests assume the same set of permissions provided by the RolePolicy.
You can use  <a href="/administration/identity-access-management/policy-based-access-control/#minio-policy-variables-oidc">OpenID Policy Variables</a> to create policies that programmatically manage what each individual user has access to.</p><p>If you do not supply a RoleArn, MinIO attempts to authorize through a JWT-based claim.</p></td>
    </tr>
  </tbody>
</table>

## Response Elements {#response-elements}

The XML response for this API endpoint is similar to the AWS [AssumeRoleWithWebIdentity response](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRoleWithWebIdentity.html#API_AssumeRoleWithWebIdentity_ResponseElements). Specifically, MinIO returns an `AssumeRoleWithWebIdentityResult` object, where the `AssumedRoleUser.Credentials` object contains the temporary credentials generated by MinIO:

- `AccessKeyId` - The access key applications use for authentication.
- `SecretKeyId` - The secret key applications use for authentication.
- `Expiration` - The <a id="index-0"></a>[**RFC3339**](https://datatracker.ietf.org/doc/html/rfc3339.html) date and time after which the credentials expire.
- `SessionToken` - The session token applications use for authentication. Some SDKs may require this field when using temporary credentials.

The following example is similar to the response returned by the MinIO STS `AssumeRoleWithWebIdentity` endpoint:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<AssumeRoleWithWebIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
<AssumeRoleWithWebIdentityResult>
   <AssumedRoleUser>
      <Arn/>
      <AssumeRoleId/>
   </AssumedRoleUser>
   <Credentials>
      <AccessKeyId>Y4RJU1RNFGK48LGO9I2S</AccessKeyId>
      <SecretAccessKey>sYLRKS1Z7hSjluf6gEbb9066hnx315wHTiACPAjg</SecretAccessKey>
      <Expiration>2019-08-08T20:26:12Z</Expiration>
      <SessionToken>eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3NLZXkiOiJZNFJKVTFSTkZHSzQ4TEdPOUkyUyIsImF1ZCI6IlBvRWdYUDZ1Vk80NUlzRU5SbmdEWGo1QXU1WWEiLCJhenAiOiJQb0VnWFA2dVZPNDVJc0VOUm5nRFhqNUF1NVlhIiwiZXhwIjoxNTQxODExMDcxLCJpYXQiOjE1NDE4MDc0NzEsImlzcyI6Imh0dHBzOi8vbG9jYWxob3N0Ojk0NDMvb2F1dGgyL3Rva2VuIiwianRpIjoiYTBiMjc2MjktZWUxYS00M2JmLTg3MzktZjMzNzRhNGNkYmMwIn0.ewHqKVFTaP-j_kgZrcOEKroNUjk10GEp8bqQjxBbYVovV0nHO985VnRESFbcT6XMDDKHZiWqN2vi_ETX_u3Q-w</SessionToken>
   </Credentials>
</AssumeRoleWithWebIdentityResult>
<ResponseMetadata/>
</AssumeRoleWithWebIdentityResponse>
```

## Error Elements {#error-elements}

The XML error response for this API endpoint is similar to the AWS [AssumeRoleWithWebIdentity response](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRoleWithWebIdentity.html#API_AssumeRoleWithWebIdentity_Errors).

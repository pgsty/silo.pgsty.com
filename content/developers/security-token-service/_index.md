---
title: "Security Token Service (STS)"
url: "/developers/security-token-service/"
weight: 200
icon: fa-solid fa-key
minio_origin: true
silo_modified: false
---

<a id="security-token-service-sts"></a>
<a id="minio-security-token-service"></a>

The MinIO Security Token Service (STS) APIs allow applications to generate temporary credentials for accessing the MinIO deployment.

The STS API is *required* for MinIO deployments configured to use external identity managers, as the API allows conversion of the external IDP credentials into AWS Signature v4-compatible credentials.

## STS API Endpoints {#sts-api-endpoints}

MinIO supports the following STS API endpoints:

| Endpoint | Supported IDP | Description |
| --- | --- | --- |
| [AssumeRoleWithWebIdentity](/developers/security-token-service/AssumeRoleWithWebIdentity/#minio-sts-assumerolewithwebidentity) | OpenID Connect | Generates an access key and secret key using the JWT token returned by the OIDC provider |
| [AssumeRoleWithLDAPIdentity](/developers/security-token-service/AssumeRoleWithLDAPIdentity/#minio-sts-assumerolewithldapidentity) | Active Directory / LDAP | Generates an access key and secret key using the AD/LDAP credentials specified to the API endpoint. |
| [AssumeRoleWithCustomToken](/developers/security-token-service/AssumeRoleWithCustomToken/#minio-sts-assumerolewithcustomtoken) | MinIO Identity Plugin | Generates a token for use with an external identity provider and the [MinIO Identity Plugin](/administration/identity-access-management/pluggable-authentication/#minio-external-identity-management-plugin). |

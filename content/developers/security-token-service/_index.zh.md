---
title: "Security Token Service (STS)"
url: "/zh/developers/security-token-service/"
weight: 200
icon: fa-solid fa-key
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/developers/security-token-service.rst
upstream_modified: true
---

<a id="security-token-service-sts"></a>
<a id="minio-security-token-service"></a>

MinIO Security Token Service (STS) APIs 允许应用程序生成用于访问 MinIO 部署的临时凭证。

对于配置为使用外部身份管理器的 MinIO 部署，STS API 是 *必需* 的，因为该 API 可将外部 IDP 凭证转换为兼容 AWS Signature v4 的凭证。

<a id="sts-api"></a>

## STS API 端点 {#sts-api-endpoints}

MinIO 支持以下 STS API 端点：

| 端点                                                                                                                                 | 支持的 IDP              | 说明                                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [AssumeRoleWithWebIdentity](/zh/developers/security-token-service/AssumeRoleWithWebIdentity/#minio-sts-assumerolewithwebidentity)    | OpenID Connect          | 使用 OIDC 提供方返回的 JWT token 生成 access key 和 secret key                                                                                                                                |
| [AssumeRoleWithLDAPIdentity](/zh/developers/security-token-service/AssumeRoleWithLDAPIdentity/#minio-sts-assumerolewithldapidentity) | Active Directory / LDAP | 使用为该 API 端点指定的 AD/LDAP 凭证生成 access key 和 secret key。                                                                                                                           |
| [AssumeRoleWithCustomToken](/zh/developers/security-token-service/AssumeRoleWithCustomToken/#minio-sts-assumerolewithcustomtoken)    | MinIO Identity Plugin   | 通过 [MinIO Identity Plugin](/zh/administration/identity-access-management/pluggable-authentication/#minio-external-identity-management-plugin) 将外部身份提供方的 token 交换为临时 S3 凭证。 |
{.wide .expand}

以上三个 API 均返回 access key、secret key 和 session token，调用 S3 SDK 时需同时传入这三项。各端点的会话有效期遵循其各自的契约；LDAP、OIDC 与外部身份插件并不共用同一个通用时长上限。

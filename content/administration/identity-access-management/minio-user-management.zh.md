---
title: "用户管理"
url: "/zh/administration/identity-access-management/minio-user-management/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/identity-access-management/minio-user-management.rst
upstream_modified: true
---

> [!NOTE]
> - **SILO 20261109 IAM 持久化与策略加载安全（[#316](https://github.com/pgsty/silo/issues/316)、[#317](https://github.com/pgsty/silo/issues/317)、[#321](https://github.com/pgsty/silo/issues/321)–[#323](https://github.com/pgsty/silo/issues/323)）：** [SILO 20261109](/zh/blog/release/silo-20261109/) 拒绝不完整的策略加载（不会发布残缺策略集），在惰性重载期间保持缓存认证可用，并将用户、用户组、策略及服务账户的变更直接应用于持久化记录，防止滞后节点恢复已轮换的旧凭据或复活已删除的身份。
> - **SILO 20261018 自助管理授权规则：** 自助查询与清理必须遵守显式 `Deny`、会话限制及授权插件决定；内置授权拒绝受限派生凭据创建或更新服务账户，并保护 `root` 派生凭据。普通用户保留既有自助权限，批量自查询别名统一解析至父身份。详见[管理授权契约](/zh/blog/design/iam-admin-authorization/)与 [SN-2026-017](/zh/blog/security/20261018-release-hardening/#sn-2026-017)。

<a id="user-management"></a>
<a id="minio-users"></a>

<a id="id3" data-td-print-local></a>

## 概述 {#overview}

MinIO 用户由唯一的访问密钥（用户名）及其对应的密钥（密码）组成。 客户端必须同时指定现有 MinIO 用户的有效访问密钥（用户名）及其对应的密钥（密码），才能完成身份认证。

每个用户都可以分配一个或多个 [策略](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)， 这些策略会显式列出该用户有权访问的操作和资源。 用户还可以从其所属的 [组](/zh/administration/identity-access-management/minio-group-management/#minio-groups) 继承策略。

默认情况下，MinIO 会拒绝访问任何未被用户已分配或继承的 [策略](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy) 显式允许的操作或资源。 你必须显式为用户分配一个描述其授权操作和资源的 [策略](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)，*或者* 将用户加入已关联策略的 [组](/zh/administration/identity-access-management/minio-group-management/#minio-groups)。更多信息请参见 [Access Management](/zh/administration/identity-access-management/#minio-access-management)。

本页介绍 MinIO 内部 IDentity Provider (IDP) 的用户管理。 MinIO 还支持使用 OpenID Connect (OIDC) 或 Active Directory/LDAP IDentity Provider (IDP) 对身份进行外部管理。 更多信息请参见：

- [OpenID Connect 访问管理](/zh/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid)
- [Active Directory / LDAP 访问管理](/zh/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap)

启用外部身份管理后，会禁用 MinIO 内部 IDP，但仍可创建 [访问密钥](#minio-idp-service-account)。

<a id="minio-id-access-keys"></a>
<a id="minio-idp-service-account"></a>
<a id="id4" data-td-print-local></a>

## 访问密钥 {#access-keys}

MinIO Access Keys（原称 “Service Accounts”）是已认证 MinIO 用户的子身份，其中也包括 [外部管理的身份](/zh/administration/identity-access-management/#minio-authentication-and-identity-management)。 每个访问密钥都会基于其父用户附加的 [策略](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)，*或者* 父用户所属组的策略来继承权限。 访问密钥还支持可选的内联策略，用于进一步将访问限制为父用户可用操作和资源的子集。

MinIO 用户可以生成任意数量的访问密钥。 这使应用所有者可以为其应用生成访问密钥，而无需 MinIO 管理员介入。 由于生成的访问密钥拥有与父用户相同或更少的权限，管理员可以专注于管理顶层父用户，而无需细致管理这些生成的访问密钥。

你可以使用 [`mc admin user svcacct add`](/zh/reference/minio-mc-admin/mc-admin-user-svcacct-add/#command-mc.admin.user.svcacct.add) 命令创建访问密钥。 通过这些方式创建的身份在你移除访问密钥或父账户之前不会过期。

你还可以通过 `AssumeRole` STS API 端点，以编程方式创建 [security token service](/zh/developers/security-token-service/#minio-security-token-service) 账户。对于 `AssumeRole`，默认有效期为 1 小时，显式指定的有效期范围为 15 分钟至 365 天，也可通过 `MINIO_STS_DURATION` 覆盖默认时长；其他 STS 端点遵循各自的时长规则。

> [!DETAILS]- 访问密钥用于编程访问
> 访问密钥支持应用程序进行编程访问。 你不能使用访问密钥登录 MinIO Console。

<a id="minio-users-root"></a>
<a id="minio-root" data-td-print-local></a>

## MinIO `root` 用户 {#minio-root-user}

每个 MinIO 部署都具有一个 `root` 用户，可访问该部署上的所有操作和资源，无论配置的是哪种 [身份管理器](/zh/administration/identity-access-management/#minio-authentication-and-identity-management)（包括在 [SILO 20261109](/zh/blog/release/silo-20261109/) 中启用 AD/LDAP 时登录内嵌 Console，[#272](https://github.com/pgsty/silo/issues/272)）。当 [`silo`](/zh/reference/minio-server/#command-minio) 服务器首次启动时，会通过检查以下环境变量的值来设置 `root` 用户凭证：

- [`MINIO_ROOT_USER`](/zh/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_USER)
- [`MINIO_ROOT_PASSWORD`](/zh/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_PASSWORD)

轮换 root 用户凭证时，需要为部署中的所有 MinIO 服务器更新其中一个或两个变量。 root 凭证应指定为 *长、唯一且随机* 的字符串。 存储访问密钥和密钥时应采取一切可能的防护措施，确保只有已知且受信任、并且 *确实需要* 该部署超级用户访问权限的人员才能获取 `root` 凭证。

- MinIO *强烈不建议* 在任何环境中（开发、预发或生产）使用 `root` 用户进行常规客户端访问。
- MinIO *强烈建议* 创建用户时，使每个客户端仅拥有执行其分配工作负载所需的最小操作和资源集合。

如果这些变量未设置，[`silo`](/zh/reference/minio-server/#command-minio) 默认分别使用 `minioadmin` 和 `minioadmin` 作为访问密钥和密钥。无论部署环境如何，MinIO 都 *强烈不建议* 使用默认凭证。

> [!DETAILS]- 旧版 Root 用户环境变量已弃用
> MinIO [RELEASE.2021-04-22T15-44-28Z](https://github.com/minio/minio/releases/tag/RELEASE.2021-04-22T15-44-28Z) 及后续版本已弃用以下用于设置或更新 root 用户凭证的变量：
>
> - [`MINIO_ACCESS_KEY`](/zh/reference/minio-server/settings/deprecated/#envvar.MINIO_ACCESS_KEY) 表示新的访问密钥。
> - [`MINIO_SECRET_KEY`](/zh/reference/minio-server/settings/deprecated/#envvar.MINIO_SECRET_KEY) 表示新的密钥。
> - [`MINIO_ACCESS_KEY_OLD`](/zh/reference/minio-server/settings/deprecated/#envvar.MINIO_ACCESS_KEY_OLD) 表示旧的访问密钥。
> - [`MINIO_SECRET_KEY_OLD`](/zh/reference/minio-server/settings/deprecated/#envvar.MINIO_SECRET_KEY_OLD) 表示旧的密钥。

<a id="id5" data-td-print-local></a>

## 用户管理 {#id1}

<a id="id6" data-td-print-local></a>

### 创建用户 {#create-a-user}

使用 [`mc admin user add`](/zh/reference/minio-mc-admin/mc-admin-user-add/#command-mc.admin.user.add) 命令在 MinIO 部署上创建新用户：

```shell
mc admin user add ALIAS ACCESSKEY SECRETKEY
```

- 将 [`ALIAS`](/zh/reference/minio-mc-admin/mc-admin-user-add/#mc.admin.user.add.ALIAS) 替换为 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。
- 将 [`ACCESSKEY`](/zh/reference/minio-mc-admin/mc-admin-user-add/#mc.admin.user.add.ACCESSKEY) 替换为用户的访问密钥。 MinIO 允许在用户创建后，通过 [`mc admin user info`](/zh/reference/minio-mc-admin/mc-admin-user-info/#command-mc.admin.user.info) 命令检索访问密钥。
- 将 [`SECRETKEY`](/zh/reference/minio-mc-admin/mc-admin-user-add/#mc.admin.user.add.SECRETKEY) 替换为用户的密钥。 MinIO *不提供* 在密钥设置后再进行检索的任何方法。

`ACCESSKEY` 和 `SECRETKEY` 都应指定为唯一、随机且足够长的字符串。 你的组织可能对生成用于访问密钥或密钥的值有特定的内部或监管要求。

创建用户后，使用 [`mc admin policy attach`](/zh/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach) 为新用户关联 [MinIO 基于策略的访问控制](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)。 以下命令分配内置的 [`readwrite`](/zh/administration/identity-access-management/policy-based-access-control/#userpolicy.readwrite) 策略：

```shell
mc admin policy attach ALIAS readwrite --user=USERNAME
```

将 `USERNAME` 替换为上一步创建的 `ACCESSKEY`。

<a id="id7" data-td-print-local></a>

### 删除用户 {#delete-a-user}

使用 [`mc admin user rm`](/zh/reference/minio-mc-admin/mc-admin-user-remove/#command-mc.admin.user.rm) 命令从 MinIO 部署中移除用户：

```shell
mc admin user rm ALIAS USERNAME
```

- 将 [`ALIAS`](/zh/reference/minio-mc-admin/mc-admin-user-remove/#mc.admin.user.rm.ALIAS) 替换为 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。
- 将 [`USERNAME`](/zh/reference/minio-mc-admin/mc-admin-user-remove/#mc.admin.user.rm.USERNAME) 替换为要移除的用户名。

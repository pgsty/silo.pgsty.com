---
title: "安全与访问"
url: "/zh/administration/console/security-and-access/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/console/security-and-access.rst
upstream_modified: true
---

> [!NOTE]
> **SILO 20261109 与 Console v2.7.0 更新：**
> - **启用 LDAP 时的 Console root 登录（[#272](https://github.com/pgsty/silo/issues/272)）：** 启用 Active Directory / LDAP 后，`root` 用户仍可登录内嵌 Console。
> - **多盘纠删集上的长 DN LDAP 登录（[#271](https://github.com/pgsty/silo/issues/271)）：** 规范化 DN 单段超过 255 字节的 LDAP 用户可在多盘纠删码集合部署上正常登录。
> - **持久化 IAM 变更与完整策略加载（[#316](https://github.com/pgsty/silo/issues/316)、[#317](https://github.com/pgsty/silo/issues/317)、[#321](https://github.com/pgsty/silo/issues/321)–[#323](https://github.com/pgsty/silo/issues/323)）：** IAM 用户、用户组、策略、LDAP 组成员刷新及服务账户修改直接作用于持久化记录，且 IAM 拒绝不完整的策略加载并在惰性重载期间保持缓存认证可用，防止过期节点恢复旧凭据或已删除身份。
> - **阿拉伯语 RTL 表单控件（[Console v2.7.0](/zh/blog/release/console-2.7.0/)）：** 阿拉伯语从右向左（RTL）界面下，密码显示按钮与字段单位选择器保持在输入文本旁，不再遮挡输入内容。
> - **此前 Console 2.5.1 / Server 20261026 更新：** 切换用户组启用/禁用状态时保留现有成员；支持解析 OIDC 字符串数组形式的组声明；配置 HTTPS 或可信 TLS 反向代理后会话 Cookie 自动带 `Secure` 属性；新建访问密钥导出标准 UTF-8 JSON 凭据文件；内置策略 **Reset** 需配合 [SILO 20261026](/zh/blog/release/silo-20261026/#server-20261026) 及更高版本使用（[Console 2.5.1](/zh/blog/release/console-2.5.1/)）。

<a id="security-and-access"></a>
<a id="minio-console-security-access"></a>
<a id="id1" data-td-print-local></a>

你可以使用 MinIO Console 执行 MinIO 提供的多种身份与访问管理功能，例如：

- 创建继承父级权限的子 [访问密钥](#minio-console-user-access-keys)。
- 查看、管理和创建访问 [策略](#minio-console-admin-policies)。
- 使用内置的 MinIO IDP 创建和管理 [用户凭证](#minio-console-admin-identity) 或组，连接一个或多个 OIDC provider，或添加 AD/LDAP provider 以实现 SSO。

<a id="id3" data-td-print-local></a>
<a id="minio-console-user-access-keys"></a>

## 访问密钥 {#access-keys}

**Access Keys** 或 *Service Accounts* 部分会显示与已认证用户关联的所有 [访问密钥](/zh/administration/identity-access-management/minio-user-management/#minio-id-access-keys)。 某个用户已有访问密钥的摘要列表包括访问密钥、过期时间、状态、名称和描述。

访问密钥可为应用程序提供认证凭证，并继承“父”用户的权限。

对于使用外部身份管理器（例如 Active Directory 或兼容 OIDC 的 provider）的部署，访问密钥为用户提供了一种创建长期有效凭证的方式。

- 你可以选择访问密钥所在行查看其自定义策略（如果存在）。

  你可以在此页面创建或修改策略。 访问密钥策略不能超过父用户被授予的权限。
- 你可以选择 **Create access key** 创建新的访问密钥。

  Console 会自动生成访问密钥和密码。你可以选择密码字段上的密码显示图标查看该值，也可以按需覆盖这些值。

  你可以为访问密钥设置自定义策略，进一步限制使用该密钥进行认证的用户所拥有的权限。 选择 **Restrict beyond user policy** 打开策略编辑器，并按需修改。

  在选择 **Create** 创建访问密钥之前，请确保你已将访问密钥密码保存到安全位置。 创建访问密钥后，你无法再次获取或重置该密码值。

  如需轮换应用程序凭证，请创建新的访问密钥，并在应用程序切换为使用新凭证后删除旧密钥。

<a id="id4" data-td-print-local></a>
<a id="minio-console-admin-policies"></a>

## 策略 {#policies}

Console v2.5.1 对内置策略提供 **Reset**（重置），对自定义策略提供 **Delete**（删除）。**Reset** 会移除管理员对内置策略的自定义覆盖并恢复 SILO 原生定义。[Server 20261026](/zh/blog/release/silo-20261026/#server-20261026)使恢复后的内置定义立即可读，并在收到对端/etcd 通知时重新加载已提交状态以防延迟通知抹去后续编辑（仍会执行策略在用检查）。

**Policies** 部分会显示 MinIO 部署上的所有 [策略](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)。 *Policies* 部分允许你创建、修改或删除策略。

[策略](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy) 定义了已认证用户可以访问的授权操作和资源。 每个策略描述用户、用户组或访问密钥可以执行的一项或多项操作，或其必须满足的条件。

这些策略是 JSON 格式的文本文件，并兼容 Amazon AWS Identity and Access Management 的策略语法、结构和行为。 有关在 MinIO 中使用策略管理访问的详细信息，请参阅 [Policy Based Action Control](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)。

如果已认证用户没有 [所需的管理权限](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy-mc-admin-actions)，则此部分或其中的内容可能不可见。

- 选择 **+ Create Policy** 创建新的 MinIO Policy。
- 选择策略所在行以管理该策略的详细信息。

  **Summary** 视图显示策略摘要。

  **Users** 视图显示所有分配了该策略的用户。

  **Groups** 视图显示所有分配了该策略的组。

  **Raw Policy** 视图显示原始 JSON 策略。

使用 **Users** 和 **Groups** 视图，可分别将已创建的策略分配给用户和组。

<a id="id5" data-td-print-local></a>
<a id="identity"></a>

## 身份 {#minio-console-admin-identity}

**Identity** 部分为 [MinIO 管理的用户](/zh/administration/identity-access-management/minio-user-management/#minio-users) 提供管理界面。

该部分包含以下子部分。 如果已认证用户没有 [所需的管理权限](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy-mc-admin-actions)，某些子部分可能不可见。

<a id="id6" data-td-print-local></a>

### 用户 {#users}

**Users** 部分显示部署中的所有 MinIO 管理 [用户](/zh/administration/identity-access-management/minio-user-management/#minio-users)。

对于使用外部身份管理器（例如 Active Directory 或兼容 OIDC 的 provider）的部署，此部分不可见。

- 选择 **Create User** 创建新的 MinIO 管理用户。

  你可以在创建时为该用户分配 [组](/zh/administration/identity-access-management/minio-group-management/#minio-groups) 和 [策略](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)。
- 选择某个用户所在行以查看该用户的详细信息。

  你可以查看并修改该用户已分配的 [组](/zh/administration/identity-access-management/minio-group-management/#minio-groups) 和 [策略](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)。

  你还可以查看和管理与该用户关联的所有 [访问密钥](/zh/administration/identity-access-management/minio-user-management/#minio-idp-service-account)。

<a id="id7" data-td-print-local></a>

### 组 {#groups}

**Groups** 部分显示 MinIO 部署上的所有 [组](/zh/administration/identity-access-management/minio-group-management/#minio-groups)。

对于使用外部身份管理器（例如 Active Directory 或兼容 OIDC 的 provider）的部署，此部分不可见。

- 选择 **Create Group** 创建新的 MinIO Group。

  你可以在创建时将新用户分配到该组。

  你可以在创建后为该组分配策略。
- 选择组所在行以打开该组的详细信息。

  你可以在 **Members** 视图中修改组成员。

  你可以在 **Policies** 视图中修改该组已分配的策略。

  更改用户的组成员关系会修改该用户继承的策略。更多信息请参阅 [Access Management](/zh/administration/identity-access-management/#minio-access-management)。

### OpenID {#openid}

MinIO 支持使用 [兼容 OpenID Connect (OIDC) 的身份提供者 (IDP)](/zh/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid) 对用户身份进行外部管理。

OpenID provider 的示例包括：

- Okta
- KeyCloak
- Dex
- Google
- Facebook

配置外部 IDP 后即可启用 Single-Sign On 工作流，应用程序会先针对外部 IDP 完成认证，然后再访问 MinIO。

使用本节中的界面可以查看、添加或编辑部署的 OIDC 配置。 MinIO 支持任意数量的活动 OIDC 配置。

<a id="minio-console-admin-identity-ldap"></a>

### LDAP {#ldap}

MinIO 支持使用 [Active Directory 或 LDAP (AD/LDAP)](/zh/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap) 服务对用户身份进行外部管理。 配置外部身份提供者 (IDP) 后即可启用 Single-Sign On (SSO) 工作流，应用程序会先针对外部 IDP 完成认证，然后再访问 MinIO。

使用本节中的界面可以查看、添加或编辑部署的 LDAP 配置。 MinIO 仅支持一个活动 LDAP 配置。

MinIO 会查询 Active Directory / LDAP 服务器，以验证客户端指定的凭证。 如果进行了相应配置，MinIO 还会在 AD/LDAP 服务器上执行组查找。自 [SILO 20261109](/zh/blog/release/silo-20261109/) 起，启用 LDAP 后 `root` 用户仍可登录内嵌 Console（[#272](https://github.com/pgsty/silo/issues/272)），且规范化 DN 单段超过 255 字节的组授权 LDAP 用户可在多盘纠删码集合部署上正常登录（[#271](https://github.com/pgsty/silo/issues/271)）。

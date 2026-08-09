---
title: "mc admin policy attach"
url: "/zh/reference/minio-mc-admin/mc-admin-policy-attach/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-admin-policy-attach"></a>

<a id="command-mc.admin.policy.attach"></a>

## 语法 {#id1}

将一个或多个 IAM 策略附加到 [MinIO 管理的用户或组](/zh/administration/identity-access-management/minio-user-management/#minio-users)。

{{% alert color="info" %}}
**变更: RELEASE.2023-05-27T05-56-19Z**

要成功附加策略，所引用的用户或组必须存在。
{{% /alert %}}

必须且只能指定 [`--user`](#mc.admin.policy.attach.-user) 或 [`--group`](#mc.admin.policy.attach.-group) 二者之一。

{{< tabpane text=true persist=header >}}
{{% tab header="示例" %}}
以下命令将 `readonly` 策略附加到 [alias](/zh/glossary/#term-alias) 为 `myminio` 的部署中的用户 `james`。

```shell
mc admin policy attach myminio readonly --user james
```

{{% /tab %}}
{{% tab header="语法" %}}
该命令使用以下语法：

```shell
mc admin policy attach                       \
                TARGET                       \
                POLICY                       \
                [POLICY...]                  \
                [--user USER | --group GROUP]
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{% /tab %}}
{{< /tabpane >}}

{{% alert color="warning" %}}
**重要**

此命令仅用于管理 [MinIO 管理](/zh/administration/identity-access-management/minio-user-management/#minio-users) 用户的策略关联。

如需为 OpenID 管理的用户附加策略，请参见 [OpenID Connect 访问管理](/zh/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid)。

如需为 Active Directory/LDAP 用户或组附加策略，请使用 [`mc idp ldap policy attach`](/zh/reference/minio-mc/mc-idp-ldap-policy-attach/#command-mc.idp.ldap.policy.attach)。
{{% /alert %}}

### 参数 {#id2}

[`mc admin policy attach`](#command-mc.admin.policy.attach) 命令接受以下参数：

##### `TARGET` {#mc.admin.policy.attach.TARGET}

*mc-cmd*

*Required*

已配置 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)，该部署中包含要附加一个或多个策略的用户或组。

##### `POLICY` {#mc.admin.policy.attach.POLICY}

*mc-cmd*

*Required*

要附加到用户或组的策略名称。

你可以通过空格分隔每个策略名称，一次附加多个策略。

MinIO 部署默认包含以下 [内置策略](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy-built-in)：

- [`readonly`](/zh/administration/identity-access-management/policy-based-access-control/#userpolicy.readonly)
- [`readwrite`](/zh/administration/identity-access-management/policy-based-access-control/#userpolicy.readwrite)
- [`diagnostics`](/zh/administration/identity-access-management/policy-based-access-control/#userpolicy.diagnostics)
- [`writeonly`](/zh/administration/identity-access-management/policy-based-access-control/#userpolicy.writeonly)

##### `--user` {#mc.admin.policy.attach.-user}

*mc-cmd*

*Optional*

要附加一个或多个策略的用户身份名称。 只能指定一个用户。

你必须包含 `--user` 或 `--group` 标志之一。 `--user` 标志不能与 `--group` 标志同时使用。

##### `--group` {#mc.admin.policy.attach.-group}

*mc-cmd*

*Optional*

要附加一个或多个策略的组身份名称。 只能指定一个组。

属于该组的所有用户都会继承与该组关联的策略。

你必须包含 `--group` 或 `--user` 标志之一。 `--group` 标志不能与 `--user` 标志同时使用。

### 全局标志 {#id3}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

## 示例 {#id4}

将 `readonly` 策略附加到 alias 为 `myminio` 的部署中的用户 `james`。

```shell
mc admin policy attach myminio readonly --user james
```

将 `audit-policy` 和 `acct-policy` 策略附加到 alias 为 `myminio` 的部署中的组 `legal`。

```shell
mc admin policy attach myminio audit-policy acct-policy --group legal
```

---
title: "mc admin user ls"
url: "/zh/reference/minio-mc-admin/mc-admin-user-list/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="mc-admin-user-ls"></a>
<a id="minio-mc-admin-user-list"></a>

<a id="command-mc.admin.user.list"></a>

<a id="command-mc.admin.user.ls"></a>

## 语法 {#id1}

[`mc admin user ls`](#command-mc.admin.user.ls) 命令会列出目标 MinIO 部署上的所有 [MinIO 用户](/zh/administration/identity-access-management/minio-identity-management/#minio-internal-idp)。

[`mc admin user list`](#command-mc.admin.user.list) 命令与 [`mc admin user ls`](#command-mc.admin.user.ls) 功能等效。

[`mc admin user ls`](#command-mc.admin.user.ls) *不会* 返回与用户关联的 access key 或 secret key。 使用 [`mc admin user info`](/zh/reference/minio-mc-admin/mc-admin-user-info/#command-mc.admin.user.info) 可获取用户详细信息，包括用户的 access key。

要管理外部 Identity Provider 用户，请参阅 [`OIDC`](/zh/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid) 或 [`AD/LDAP`](/zh/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap)。

{{< tabpane text=true persist=header >}}
{{% tab header="示例" %}}
以下命令会列出 `myminio` MinIO 部署上的所有用户：

```shell
mc admin user ls myminio
```

{{% /tab %}}
{{% tab header="语法" %}}
该命令具有以下语法：

```shell
mc [GLOBALFLAGS] admin user list   \
                            ALIAS
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{% /tab %}}
{{< /tabpane >}}

### 参数 {#id2}

##### `ALIAS` {#mc.admin.user.ls.ALIAS}

*mc-cmd*

*Required*

已配置 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)，命令将从该部署中列出用户。

### 全局参数 {#id3}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

## 示例 {#id4}

### 列出可用用户 {#id5}

使用 [`mc admin user ls`](#command-mc.admin.user.ls) 列出 MinIO 部署上的所有用户：

```shell
mc admin user ls ALIAS
```

- 将 [`ALIAS`](#mc.admin.user.ls.ALIAS) 替换为该 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。

输出类似如下：

```shell
enabled    devadmin              readwrite
enabled    devtest               readonly
enabled    newuser
```

## 行为 {#id6}

### S3 兼容性 {#s3}

**`mc`** 命令行工具以兼容 AWS S3 API 为目标构建，并针对 MinIO 和 AWS S3 进行了测试，以验证预期的功能与行为。

对于其他 S3 兼容服务，MinIO 不提供任何保证，因为这些服务的 S3 API 实现未知， 因此不在支持范围内。虽然 **`mc`** 命令 *可能* 仍能按文档说明工作，但此类 用法需要你自行承担风险。

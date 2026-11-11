---
title: "mc admin user svcacct edit"
url: "/zh/reference/minio-mc-admin/mc-admin-user-svcacct-edit/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-user-svcacct-edit.rst
upstream_modified: true
---

<a id="mc-admin-user-svcacct-edit"></a>
<a id="minio-mc-admin-svcacct-edit"></a>

<a id="command-mc.admin.user.svcacct.edit"></a>

> [!WARNING]
> **重要**
>
> 此命令已被替代，并将在未来的 MinIO 客户端 发布版本中弃用。
>
> 从 MinIO客户端版本RELEASE.2024-10-08T09-37-26Z 起，请使用 [`mc admin accesskey edit`](/zh/reference/minio-mc-admin/mc-admin-accesskey-edit/#command-mc.admin.accesskey.edit) 命令修改内置 MinIO IDP 用户的访问密钥。
>
> 如需修改 AD/LDAP 用户的访问密钥，请使用 [`mc idp ldap accesskey edit`](/zh/reference/minio-mc/mc-idp-ldap-accesskey-edit/#command-mc.idp.ldap.accesskey.edit) 命令。

## 语法 {#id2}

[`mc admin user svcacct edit`](#command-mc.admin.user.svcacct.edit) 命令用于修改与指定用户关联的访问密钥配置。

{{< tabs group="tab1-tab2" >}}
{{< tab label="示例" value="tab1" >}}
以下命令为 `myminio` 部署上的 `myuserserviceaccount` 访问密钥应用新的策略和密钥：

```shell
mc admin user svcacct edit                                             \
                      --secret-key "myuserserviceaccountnewsecretkey"  \
                      --policy "/path/to/new/policy.json"              \
                      myminio myuserserviceaccount
```
{{< /tab >}}
{{< tab label="语法" value="tab2" >}}
该命令的语法如下：

```shell
mc [GLOBALFLAGS] admin user svcacct edit            \
                                    [--secret-key]  \
                                    [--policy]      \
                                    ALIAS           \
                                    SERVICEACCOUNT
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{< /tab >}}
{{< /tabs >}}

### 参数 {#id3}

##### `ALIAS` {#mc.admin.user.svcacct.edit.ALIAS}

*mc-cmd*

*Required*

MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。

##### `SERVICEACCOUNT` {#mc.admin.user.svcacct.edit.SERVICEACCOUNT}

*mc-cmd*

*Required*

要修改的服务账户。

##### `--description` {#mc.admin.user.svcacct.edit.-description}

*mc-cmd*

*Optional*

> [!NOTE]
> **新增: RELEASE.2023-05-18T16-59-00Z**

为服务账户添加描述。 例如，可以说明该服务账户存在的原因。

##### `--expiry` {#mc.admin.user.svcacct.edit.-expiry}

*mc-cmd*

*Optional*

> [!NOTE]
> **新增: RELEASE.2023-05-30T22-41-38Z**

为服务账户设置过期日期。 日期必须在未来，不能设置已经过去的过期日期。

允许的日期和时间格式：

- `2023-06-24`
- `2023-06-24T10:00`
- `2023-06-24T10:00:00`
- `2023-06-24T10:00:00Z`
- `2023-06-24T10:00:00-07:00`

##### `--name` {#mc.admin.user.svcacct.edit.-name}

*mc-cmd*

*Optional*

> [!NOTE]
> **新增: RELEASE.2023-05-18T16-59-00Z**

为服务账户添加一个便于识别的名称。

##### `--policy` {#mc.admin.user.svcacct.edit.-policy}

*mc-cmd*

*Optional*

要附加到新访问密钥的 [policy document](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy) 路径，最大长度为 2048 个字符。 附加的策略不能授予父用户策略未明确允许的任何操作或资源访问权限。

新策略会覆盖此前已附加的任何策略。省略 `--policy` 会保留现有的内联策略；若需移除已附加的内联策略并恢复为继承父用户策略，请传入包含空策略文档（`{}` 或 `{"Version":"2012-10-17","Statement":[]}`）的文件。

##### `--secret-key` {#mc.admin.user.svcacct.edit.-secret-key}

*mc-cmd*

*Optional*

与新访问密钥关联的密钥。 会覆盖此前的密钥。 使用这些访问密钥的应用程序 *必须* 更新为新凭证，才能继续执行操作。

### 全局参数 {#id4}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

## 行为 {#id5}

### S3 兼容性 {#s3}

PGSTY mcli 受支持的服务端为 SILO；与上游 MinIO 及其他 S3 服务的兼容按[尽最大努力](/zh/reference/minio-mc/#command-mc)原则提供。

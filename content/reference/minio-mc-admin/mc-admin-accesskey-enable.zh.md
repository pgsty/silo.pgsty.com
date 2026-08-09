---
title: "mc admin accesskey enable"
url: "/zh/reference/minio-mc-admin/mc-admin-accesskey-enable/"
weight: 40
minio_origin: true
silo_modified: false
---

<a id="mc-admin-accesskey-enable"></a>
<a id="minio-mc-admin-accesskey-enable"></a>

<a id="command-mc.admin.accesskey.enable"></a>

## 语法 {#id2}

[`mc admin accesskey enable`](#command-mc.admin.accesskey.enable) 命令用于启用现有访问密钥。

{{< tabpane text=true persist=header >}}
{{% tab header="示例" %}}
以下命令启用指定的访问密钥：

```shell
mc admin accesskey enable myminio myuserserviceaccount
```

{{% /tab %}}
{{% tab header="语法" %}}
该命令具有以下语法：

```shell
mc [GLOBALFLAGS] admin accesskey enable          \
                                 ALIAS           \
                                 SERVICEACCOUNT
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{% /tab %}}
{{< /tabpane >}}

### 参数 {#id3}

##### `ALIAS` {#mc.admin.accesskey.enable.ALIAS}

*mc-cmd*

*Required*

MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。

##### `SERVICEACCOUNT` {#mc.admin.accesskey.enable.SERVICEACCOUNT}

*mc-cmd*

*Required*

要启用的访问密钥。

### 全局标志 {#id4}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

## 行为 {#id5}

### S3 兼容性 {#s3}

**`mc`** 命令行工具以兼容 AWS S3 API 为目标构建，并针对 MinIO 和 AWS S3 进行了测试，以验证预期的功能与行为。

对于其他 S3 兼容服务，MinIO 不提供任何保证，因为这些服务的 S3 API 实现未知， 因此不在支持范围内。虽然 **`mc`** 命令 *可能* 仍能按文档说明工作，但此类 用法需要你自行承担风险。

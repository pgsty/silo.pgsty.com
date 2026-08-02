---
title: "mc admin accesskey rm"
url: "/zh/reference/minio-mc-admin/mc-admin-accesskey-remove/"
weight: 70
minio_origin: true
silo_modified: false
---

<a id="mc-admin-accesskey-rm"></a>
<a id="minio-mc-admin-accesskey-remove"></a>

<a id="command-mc.admin.accesskey.remove"></a>

<a id="command-mc.admin.accesskey.rm"></a>

## 语法 {#id2}

[`mc admin accesskey rm`](#command-mc.admin.accesskey.rm) 命令用于删除部署中与某个用户关联的访问密钥。

[`mc admin accesskey remove`](#command-mc.admin.accesskey.remove) 命令与 [`mc admin accesskey rm`](#command-mc.admin.accesskey.rm) 的功能等效。

{{% alert color="danger" %}}
**警告**

删除后，应用程序将无法再使用该访问密钥进行身份验证。
{{% /alert %}}

{{< tabpane text=true persist=header >}}
{{% tab header="示例" %}}
以下命令会删除指定的访问密钥：

```shell
mc admin accesskey rm myminio myuserserviceaccount
```
{{% /tab %}}
{{% tab header="语法" %}}
命令语法如下：

```shell
mc [GLOBALFLAGS] admin accesskey rm                \
                                 ALIAS             \
                                 ACCESSKEYTOREMOVE
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{% /tab %}}
{{< /tabpane >}}

### 参数 {#id3}

##### `ALIAS` {#mc.admin.accesskey.rm.ALIAS}

*mc-cmd*

*Required*

MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。

##### `ACCESSKEYTOREMOVE` {#mc.admin.accesskey.rm.ACCESSKEYTOREMOVE}

*mc-cmd*

*Required*

要删除的访问密钥。

### 全局标志 {#id4}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

## 行为 {#id5}

### S3 兼容性 {#s3}

**`mc`** 命令行工具以兼容 AWS S3 API 为目标构建，并针对 MinIO 和 AWS S3 进行了测试，以验证预期的功能与行为。

对于其他 S3 兼容服务，MinIO 不提供任何保证，因为这些服务的 S3 API 实现未知， 因此不在支持范围内。虽然 **`mc`** 命令 *可能* 仍能按文档说明工作，但此类 用法需要你自行承担风险。

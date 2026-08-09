---
title: "mc alias list"
url: "/zh/reference/minio-mc/mc-alias-list/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-alias-list"></a>
<a id="minio-mc-alias-list"></a>

<a id="command-mc.alias.list"></a>

## 语法 {#id2}

[`mc alias list`](#command-mc.alias.list) 命令列出本地 **`mc`** 配置中的所有别名。

该命令输出包含每个别名关联的 access key 和 secret key 配置。

{{< tabpane text=true persist=header >}}
{{% tab header="示例" %}}
以下命令列出本地主机上配置的所有 [aliases](/zh/reference/minio-mc/mc-alias-set/#alias)：

```shell
mc alias list
```

{{% /tab %}}
{{% tab header="语法" %}}
[`mc alias list`](#command-mc.alias.list) 命令语法如下：

```shell
mc [GLOBALFLAGS] alias list [ALIAS]
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{% /tab %}}
{{< /tabpane >}}

### 参数 {#id3}

##### `ALIAS` {#mc.alias.list.ALIAS}

*mc-cmd*

*可选* 要显示的特定别名名称。

### 全局标志 {#id4}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

## 示例 {#id5}

### 列出所有已配置别名 {#id6}

{{< tabpane text=true persist=header >}}
{{% tab header="示例" %}}
以下 [`mc alias list`](#command-mc.alias.list) 命令列出本地 **`mc`** 配置中所有已配置的别名。

```shell
mc alias list
```

{{% /tab %}}
{{% tab header="语法" %}}

```shell
mc alias list
```

{{% /tab %}}
{{< /tabpane >}}

### 列出特定别名 {#id7}

{{< tabpane text=true persist=header >}}
{{% tab header="示例" %}}
以下 [`mc alias list`](#command-mc.alias.list) 命令列出本地 **`mc`** 配置中特定别名的详细信息。

```shell
mc alias list myminio
```

{{% /tab %}}
{{% tab header="语法" %}}

```shell
mc alias list ALIAS
```

- 将 `ALIAS` 替换为要返回的别名名称。
{{% /tab %}}
{{< /tabpane >}}

## 行为 {#id8}

### S3 兼容性 {#s3}

**`mc`** 命令行工具以兼容 AWS S3 API 为目标构建，并针对 MinIO 和 AWS S3 进行了测试，以验证预期的功能与行为。

对于其他 S3 兼容服务，MinIO 不提供任何保证，因为这些服务的 S3 API 实现未知， 因此不在支持范围内。虽然 **`mc`** 命令 *可能* 仍能按文档说明工作，但此类 用法需要你自行承担风险。

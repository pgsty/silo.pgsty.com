---
title: "mc update"
url: "/zh/reference/minio-mc/mc-update/"
weight: 420
minio_origin: true
silo_modified: false
---

<a id="mc-update"></a>

<a id="command-mc.update"></a>

## 语法 {#id2}

[`mc update`](#command-mc.update) 命令会自动将 **`mc`** 二进制更新到最新稳定版本。

运行此命令等同于手动下载最新稳定版二进制文件，并使用该文件替换主机上 现有的 `mc` 安装。

{{< tabpane text=true persist=header >}}
{{% tab header="示例" %}}
以下命令会更新本地主机上的 **`mc`** 二进制文件：

```shell
mc update
```
{{% /tab %}}
{{% tab header="语法" %}}
该命令的语法如下：

```shell
mc [GLOBALFLAGS] update
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{% /tab %}}
{{< /tabpane >}}

更新 **`minio`** 服务器二进制后，请使用 [`mc update`](#command-mc.update)， 以确保行为一致性和兼容性。

### 全局参数 {#id3}

##### `--json` {#mc.update.-json}

*mc-cmd*

*Optional*

启用 [JSON lines](http://jsonlines.org/)<a id="json-lines"></a> 格式的控制台输出。

例如：

```shell
mc --json COMMAND
```

---
title: "mc admin policy rm"
url: "/zh/reference/minio-mc-admin/mc-admin-policy-remove/"
weight: 70
minio_origin: true
silo_modified: false
---

<a id="mc-admin-policy-rm"></a>

<a id="command-mc.admin.policy.remove"></a>

<a id="command-mc.admin.policy.rm"></a>

## 语法 {#id1}

从目标 MinIO 部署中移除 IAM 策略。

[`mc admin policy remove`](#command-mc.admin.policy.remove) 命令与 [`mc admin policy rm`](#command-mc.admin.policy.rm) 具有等效功能。

{{< tabpane text=true persist=header >}}
{{% tab header="示例" %}}
以下命令从 `myminio` MinIO 部署中移除名为 `writeonly` 的策略：

```shell
mc admin policy rm myminio writeonly
```
{{% /tab %}}
{{% tab header="语法" %}}
该命令的语法如下：

```shell
mc admin policy rm TARGET POLICYNAME
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{% /tab %}}
{{< /tabpane >}}

### 参数 {#id2}

[`mc admin policy rm`](#command-mc.admin.policy.rm) 命令接受以下参数：

##### `TARGET` {#mc.admin.policy.rm.TARGET}

*mc-cmd*

要移除策略的已配置 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。

##### `POLICYNAME` {#mc.admin.policy.rm.POLICYNAME}

*mc-cmd*

要移除的策略名称。

### 全局标志 {#id3}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

## 示例 {#id4}

移除名为 `listbuckets` 的策略。

```shell
mc admin policy rm myminio listbuckets
```

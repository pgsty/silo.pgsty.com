---
title: "mc ilm restore"
url: "/zh/reference/minio-mc/mc-ilm-restore/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-ilm-restore.rst
upstream_modified: true
---

<a id="mc-ilm-restore"></a>
<a id="minio-mc-ilm-restore"></a>

<a id="command-mc.ilm.restore"></a>

## 语法 {#syntax}

[`mc ilm restore`](#command-mc.ilm.restore) 命令会为归档在远程层上的对象创建一份本地临时副本。默认情况下，该临时副本会在 1 天后过期。

使用此命令可让应用程序从 SILO 部署的本地存储读取已迁移对象。已迁移的数据保留在远程层上，而本地临时副本会在恢复有效期届满前响应该版本的读取请求。

> [!NOTE]
> **新增: mc**
>
> RELEASE.2023-04-12T02-21-51Z
>
> 使用 [`mc stat`](/zh/reference/minio-mc/mc-stat/#command-mc.stat) 可显示已恢复对象是从本地临时副本读取还是从远程层读取。 当前正在从远程层恢复的对象会显示状态 `Ongoing : true`。

{{< tabs group="tab1-tab2" >}}
{{< tab label="示例" value="tab1" >}}
以下命令将远程层上一个已转储对象的副本恢复到 `myminio` MinIO 部署：

```shell
mc ilm restore myminio/mybucket/object.txt
```
{{< /tab >}}
{{< tab label="语法" value="tab2" >}}
该命令的语法如下：

```shell
mc [GLOBALFLAGS] ilm restore         \
                 [--days "int" ]     \
                 [--recursive]       \
                 [--vid "string"]    \
                 [--versions]        \
                 [--enc-c "string"]  \
                 ALIAS
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{< /tab >}}
{{< /tabs >}}

### 参数 {#parameters}

##### `ALIAS` {#mc.ilm.restore.ALIAS}

*mc-cmd*

*Required*

要恢复的归档对象对应的 MinIO [alias](/zh/reference/minio-mc/mc-alias-set/#alias)、存储桶和路径。

```shell
mc ilm restore myminio/mybucket/object.txt
```

##### `--days` {#mc.ilm.restore.-days}

*mc-cmd*

*Optional*

MinIO 使已恢复归档对象副本过期前的天数。

##### `--enc-c` {#mc.ilm.restore.-enc-c}

*mc-cmd*

*Optional*

使用客户端管理的密钥，通过服务端 [SSE-C 加密](/zh/administration/server-side-encryption/#minio-sse) 对对象进行加密或解密。

该参数接受格式为 `KEY=VALUE` 的键值对：

| 组成部分 | 说明                                                                                                                                                              |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `KEY`    | 对象的完整路径，格式为 `alias/bucket/path/object.ext`。仅指定顶层路径即可对该路径下的所有操作使用同一个加密密钥。                                                 |
| `VALUE`  | 用于 SSE-C 加密的 32 字节 RawBase64 编码密钥或 64 字节十六进制编码密钥。Raw Base64 编码**拒绝**带 `=` 填充的密钥；请去掉填充或使用支持 RAW 格式的 Base64 编码器。 |
{.wide .expand}

例如：

```shell
# RawBase64-Encoded string "mybucket32byteencryptionkeyssec"
--enc-c "myminio/mybucket/prefix/object.obj=bXlidWNrZXQzMmJ5dGVlbmNyeXB0aW9ua2V5c3NlYwo"
```

你可以通过重复该参数来指定多个加密密钥。

也可以指定某个前缀路径，对该路径下所有匹配对象应用加密：

```shell
--enc-c "myminio/mybucket/prefix/=bXlidWNrZXQzMmJ5dGVlbmNyeXB0aW9ua2V5c3NlYwo"
```

> [!NOTE]
> **说明**
>
> MinIO 强烈不建议在生产负载中使用 SSE-C 加密。 请改用 `--enc-kms` 参数启用 SSE-KMS，或使用 `--enc-s3` 参数启用 SSE-S3。

##### `--recursive, r` {#mc.ilm.restore.-recursive}

*mc-cmd*

*Optional*

恢复指定前缀下的所有对象。

##### `--versions` {#mc.ilm.restore.-versions}

*mc-cmd*

*Optional*

恢复远程层上该对象的所有版本。

##### `--version-id, vid` {#mc.ilm.restore.-version-id}

*mc-cmd*

*Optional*

恢复远程层上该对象的指定版本。

### 全局参数 {#global-flags}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

## 示例 {#examples}

### 恢复归档对象 {#restore-an-archived-object}

以下命令恢复一个已归档到远程层的对象：

```shell
mc ilm restore myminio/mybucket/object.txt
```

### 恢复指定版本的归档对象 {#restore-a-specific-archived-object-version}

以下命令恢复一个已归档到远程层的指定对象版本：

```shell
mc ilm restore --vid "VERSIONID" myminio/mybucket/object.txt
```

### 恢复存储桶前缀下的所有归档对象 {#restore-all-archived-objects-at-a-bucket-prefix}

以下命令恢复远程层上指定前缀下归档的所有对象：

```shell
mc ilm restore --recursive myminio/mybucket/data/
```

## 行为 {#behavior}

### 已恢复对象自动过期 {#restored-objects-expire-automatically}

SILO 会在指定天数后自动使已恢复的本地副本过期（默认：1 天）。在 [SILO 20261109](/zh/blog/release/silo-20261109/) 中，已恢复副本到期时仅清理本地临时缓存，同时保留对象版本及其远程层数据（[#281](https://github.com/pgsty/silo/issues/281)）。

<a id="restored-objects-become-head"></a>

### 两阶段原地版本恢复 {#two-phase-restore}

自 [SILO 20261109](/zh/blog/release/silo-20261109/) 起，原生恢复（`POST ?restore`，提交 [`86dc6ee2e`](https://github.com/pgsty/silo/commit/86dc6ee2e)）分两个阶段运行，设计细节见[两阶段原生恢复](/zh/blog/design/native-restore-two-phase/)：

- **原地恢复指定版本：** SILO 原地恢复请求指定的精确版本，不会改变版本顺序，也不会创建新的 `HEAD` 版本；多池部署下的恢复不再挂起或长期停留在进行中状态（[#289](https://github.com/pgsty/silo/issues/289)）。
- **两阶段加锁：** 第一阶段在对象写锁之外下载并暂存远程层数据，使同一对象键上的并发 `GET`、`HEAD` 和 `PUT` 请求无需等待下载结束；第二阶段短暂获取对象锁，核验恢复尝试所有权与版本元数据后再发布恢复副本（[#284](https://github.com/pgsty/silo/issues/284)）。
- **快速失败清理：** 若恢复失败或被取消，服务端会立即返回，先在 `100 ms` 内尝试清理恢复标记，再转为有界后台重试，而不再同步等待对象锁长达一分钟。
- **滚动升级门控：** 在混合版本滚动升级期间，只要任一对等节点运行旧版本或不可达，已升级节点就会对 `POST ?restore` 返回 `503 Service Unavailable`。请在全部节点运行 `SILO 20261109` 前暂停发起新的恢复请求。

### S3 兼容性 {#s3-compatibility}

SILO 是 PGSTY mcli 正式支持的服务端；与上游 MinIO 及其他 S3 服务的兼容性为[尽最大努力](/zh/reference/minio-mc/#command-mc)。

---
title: "mc admin update"
url: "/zh/reference/minio-mc-admin/mc-admin-update/"
weight: 180
minio_origin: true
silo_modified: false
---

<a id="mc-admin-update"></a>

<a id="command-mc.admin.update"></a>

## 描述 {#id2}

[`mc admin update`](#command-mc.admin.update) 命令会更新部署中的所有 MinIO 服务器。 该命令还支持使用私有镜像服务器，适用于部署环境无法访问公网的场景。

运行该命令后，会显示确认更新的提示。 输入 `y` 并按 `[ENTER]`，即可确认并继续更新。

用户**必须**对二进制安装目标位置具有 `write` 权限。

{{% alert color="info" %}}
**仅在 MinIO 部署上使用 `mc admin`**

MinIO 不支持将 [`mc admin`](/zh/reference/minio-mc-admin/#command-mc.admin) 命令用于其他 S3 兼容服务， 无论这些服务声称与 MinIO 部署具有何种兼容性。
{{% /alert %}}

## 注意事项 {#id3}

### 更新无中断 {#id4}

[`mc admin update`](#command-mc.admin.update) 会更新二进制，并同时重启部署中的所有 MinIO 服务器。 MinIO 操作具备原子性和严格一致性，因此该重启过程不会中断应用。

MinIO 强烈建议仅执行同时升级并重启的流程。 请勿执行“滚动”（即一次一个节点）升级流程。

### 权限 {#id5}

执行该命令的用户**必须**对 MinIO 服务端二进制安装目标路径具有 `write` 权限。

## 示例 {#id6}

使用 [`mc admin update`](#command-mc.admin.update) 更新 MinIO 部署中的每个 [`minio`](/zh/reference/minio-server/#command-minio) 服务器进程：

```shell
mc admin update ALIAS
```

将 [`ALIAS`](#mc.admin.update.ALIAS) 替换为该 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。

运行该命令后，在提示中输入 yes 以确认并执行更新。

## 语法 {#id7}

[`mc admin update`](#command-mc.admin.update) 语法如下：

```shell
mc admin update ALIAS         \
                [MIRROR_URL]  \
                [--yes]
```

[`mc admin update`](#command-mc.admin.update) 支持以下参数：

#### `ALIAS` {#mc.admin.update.ALIAS}

*mc-cmd*

要更新的 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。

如果指定的 `ALIAS` 对应的是分布式 MinIO 部署，[`mc admin update`](#command-mc.admin.update) 会同时更新该部署中的*所有* MinIO 服务器。

使用 [`mc alias list`](/zh/reference/minio-mc/mc-alias-list/#command-mc.alias.list) 查看已配置的别名及其对应的 MinIO 部署端点。

#### `MIRROR_URL` {#mc.admin.update.MIRROR_URL}

*mc-cmd*

`minio` server 二进制的镜像 URL，用于更新 [`ALIAS`](#mc.admin.update.ALIAS) 部署中的 MinIO 服务器。

#### `--yes, -y` {#mc.admin.update.-yes}

*mc-cmd*

*Optional*

传入此标志以确认更新，并跳过确认提示。

## 行为 {#id8}

### 二进制压缩 {#id9}

{{% alert color="info" %}}
**变更: RELEASE.2024-01-28T22-35-53Z**

[`mc admin update`](#command-mc.admin.update) 会先压缩二进制，再发送到部署中的所有节点。
{{% /alert %}}

此功能不适用于 [systemctl managed deployments](/zh/operations/deployments/baremetal/#minio-baremetal)。

---
title: "升级 MinIO 部署"
url: "/zh/operations/deployments/baremetal-upgrade-minio-deployment/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="minio"></a>
<a id="minio-upgrade"></a>

{{% alert color="warning" %}}
**重要**

对于早于 [RELEASE.2024-03-30T09-41-56Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-03-30T09-41-56Z) 且启用了 [AD/LDAP](/zh/reference/minio-server/settings/iam/ldap/#minio-ldap-config-settings) 的部署，在开始本步骤前，你 **必须** 先完整阅读 [RELEASE.2024-04-18T19-09-19Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-04-18T19-09-19Z) 的发布说明。 你必须将该发布说明中记录的额外步骤纳入升级过程。
{{% /alert %}}

MinIO 使用先更新后重启的方法将部署升级到较新版本：

1. 使用较新版本更新 MinIO 二进制文件。
2. 使用 [`mc admin service restart`](/zh/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) 重启部署。

该流程无需停机，也不会中断正在进行的操作。

本页介绍对 `systemctl` 管理的 MinIO 部署和用户自管 MinIO 部署使用 先更新后重启方法进行升级的方式。 使用 Ansible、Terraform 或其他管理工具的部署， 可以将此处流程作为在现有自动化框架中实施升级的参考。

## 前提条件 {#id2}

### 先备份集群设置 {#id3}

在开始执行此流程之前，使用 [`mc admin cluster bucket export`](/zh/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) 和 [`mc admin cluster iam export`](/zh/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) 命令对存储桶元数据和 IAM 配置进行快照。 如有需要，你可以使用这些快照恢复 [bucket](/zh/reference/minio-mc-admin/mc-admin-cluster-bucket-import/#minio-mc-admin-cluster-bucket-import) 和 [IAM](/zh/reference/minio-mc-admin/mc-admin-cluster-iam-import/#minio-mc-admin-cluster-iam-import) 设置， 以便从用户或流程错误中恢复。

### 检查发行说明 {#id4}

MinIO 发布 [Release Notes](https://github.com/minio/minio/releases) 供你参考， 以识别每个版本所引入的变更。 请查看当前 MinIO 版本与目标较新版本之间各版本对应的发行说明， 以完整了解所有变更。

尤其要注意任何 *不* 向后兼容的版本。 你无法轻易从这类版本回退。

### 在应用到生产环境前先测试升级 {#id5}

MinIO 在每个版本发布时都会使用测试和验证套件。 但任何测试套件都无法覆盖你生产环境中硬件、软件和工作负载的所有特定组合。

在将任何 MinIO 升级应用到生产部署或其他包含关键数据的环境之前， 你都应先在较低环境（Dev/QA/Staging）中完成验证。 如果不先在较低环境中验证就直接更新生产环境，风险由你自行承担。

对于明显落后于最新稳定版（6 个月以上）的 MinIO 部署， 建议在升级过程中使用 [MinIO SUBNET](https://min.io/pricing?jmp=docs) 获取额外支持和指导。

## 注意事项 {#id6}

### 升级不会中断业务 {#id7}

MinIO 的先更新后重启流程 *不* 需要停机或安排维护窗口。 MinIO 重启速度很快，并行重启所有服务端进程通常只需几秒。 MinIO 操作具备原子性且严格一致，因此使用 MinIO 或 S3 SDK 的应用 可以依赖内置的 [transparent retry](https://docs.aws.amazon.com/general/latest/gr/api-retries.html)， 无需额外的客户端逻辑。 这可确保升级不会中断正在进行的操作。

<a id="minio-upgrade-systemctl"></a>

## 升级由 `systemctl` 管理的 MinIO 部署 {#systemctl-minio}

使用以下步骤升级由 `systemctl` 管理 MinIO 服务进程的部署， 例如通过 MinIO [DEB/RPM packages](/zh/operations/deployments/baremetal/#deploy-minio-distributed-baremetal) 创建的部署。

本流程假定你已在所有 MinIO 节点上设置 [`MINIO_CONFIG_ENV_FILE`](/zh/reference/minio-server/settings/core/#envvar.MINIO_CONFIG_ENV_FILE) 变量。

1. 在每个节点上更新 MinIO 二进制文件

   以下选项卡给出了在 64 位 Linux 操作系统上通过 RPM、DEB 或二进制方式更新 MinIO 的示例：

   {{< tabpane text=true persist=header >}}
   {{% tab header="RPM (RHEL)" %}}
   使用以下命令下载最新稳定版 MinIO RPM 并更新现有安装。

   ```shell
   wget RPMURL -O minio.rpm
   sudo dnf update minio.rpm
   ```
   {{% /tab %}}
   {{% tab header="DEB (Debian/Ubuntu)" %}}
   使用以下命令下载最新稳定版 MinIO DEB 并升级现有安装：

   ```shell
   wget DEBURL -O minio.deb
   sudo dpkg -i minio.deb
   ```
   {{% /tab %}}
   {{% tab header="Binary" %}}
   使用以下命令下载最新稳定版 MinIO 二进制文件， 并覆盖现有二进制文件：

   ```shell
   wget https://dl.min.io/server/minio/release/linux-amd64/minio
   chmod +x minio
   sudo mv -f ./minio /usr/local/bin/minio
   ```

   将 `/usr/local/bin` 替换为现有 MinIO 二进制文件所在位置。 如果尚不确定该路径，请运行 `which minio` 进行确认。
   {{% /tab %}}
   {{< /tabpane >}}

   在每个节点上运行 `minio --version`， 确认你已将所有二进制文件成功升级到相同版本。 除非所有节点都使用相同的 MinIO 二进制版本，否则 **不要** 继续。
2. 重启部署

   运行 [`mc admin service restart`](/zh/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) 命令， 同时重启部署中的所有 MinIO 服务进程。

   ```shell
   mc admin service restart ALIAS
   ```

   将 `ALIAS` 替换为要重启的 MinIO 部署的 [别名](/zh/reference/minio-mc/mc-alias-set/#alias)。

   S3 兼容 SDK 和应用应自动重试操作， 因此重启过程通常 *不会中断* 正在进行的操作。
3. 验证升级

   使用 [`mc admin info`](/zh/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info) 命令检查所有 MinIO 服务器是否在线、运行正常， 且显示已安装的 MinIO 版本。
4. 更新 MinIO Client

   你应升级 [`mc`](/zh/reference/minio-mc/#command-mc) 二进制文件，使其与 MinIO server 版本一致或尽量接近。 你可以使用 [`mc update`](/zh/reference/minio-mc/mc-update/#command-mc.update) 命令将该二进制文件更新到最新稳定版本：

   ```shell
   mc update
   ```

<a id="id8"></a>

## 升级非系统管理的 MinIO 部署 {#minio-upgrade-mc-admin-update}

使用以下步骤升级不由系统（`systemd`、`systemctl`）管理 MinIO 服务进程的部署， 例如由用户、自动化脚本或其他进程管理工具管理的部署。 该流程仅适用于运行 MinIO 进程的用户对 MinIO 二进制文件路径具有写权限的系统。 对于使用 `systemctl` 管理的部署，请参阅 [升级由 systemctl 管理的 MinIO 部署](#minio-upgrade-systemctl)。

### 使用 `mc admin update` 更新 {#mc-admin-update}

[`mc admin update`](/zh/reference/minio-mc-admin/mc-admin-update/#command-mc.admin.update) 命令会先更新目标 MinIO 部署中的所有 MinIO server 二进制文件， 然后同时重启所有节点。 重启过程通常会在几秒内完成，且 *不会中断* 正在进行的操作。

以下命令会将具有指定 [别名](/zh/reference/minio-mc/mc-alias-set/#alias) 的 MinIO 部署 更新到最新稳定版本：

```shell
mc admin update ALIAS
```

运行 `mc admin update` 命令的用户 **必须** 对二进制文件安装位置具有 `write` 权限。

你可以指定一个解析到特定 MinIO server 二进制版本的 URL。 气隙或与互联网隔离的部署可以利用此功能， 从内部可访问的服务器执行更新：

```shell
mc admin update ALIAS https://minio-mirror.example.com/minio.sha256sum
```

你应升级 [`mc`](/zh/reference/minio-mc/#command-mc) 二进制文件，使其与 MinIO server 版本一致或尽量接近。 你可以使用 [`mc update`](/zh/reference/minio-mc/mc-update/#command-mc.update) 命令将该二进制文件更新到最新稳定版本：

```shell
mc update
```

### 通过手动替换二进制文件更新 {#id9}

你可以在部署中的每个主机节点上下载并手动替换 `minio` server 二进制文件。 然后必须同时重启所有节点，例如使用 [`mc admin service restart`](/zh/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart)。

例如，以下命令会下载适用于 Linux 的最新稳定版 MinIO 二进制文件， 并将其复制到 `/usr/local/bin`。 该命令会覆盖该路径上现有的 `minio` 二进制文件。

```shell
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x ./minio
sudo mv -f ./minio /usr/local/bin/minio
```

在你替换完部署中所有 MinIO 主机上的二进制文件后， 必须同时重启所有节点。

你应升级 [`mc`](/zh/reference/minio-mc/#command-mc) 二进制文件，使其与 MinIO server 版本一致或尽量接近。 你可以使用 [`mc update`](/zh/reference/minio-mc/mc-update/#command-mc.update) 命令将该二进制文件更新到最新稳定版本：

```shell
mc update
```

---
title: "对象自动过期"
url: "/zh/administration/object-management/create-lifecycle-management-expiration-rule/"
weight: 50
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/object-management/create-lifecycle-management-expiration-rule.rst
upstream_modified: true
---

<a id="automatic-object-expiration"></a>
<a id="minio-lifecycle-management-create-expiry-rule"></a>

本页中的每个过程都会创建一条新的对象生命周期管理规则，用于让 MinIO 存储桶中的对象过期。该过程适用于在特定时间段或日历日期之后删除“旧”对象 等场景。

## 要求 {#requirements}

### 安装并配置 `mc` {#install-and-configure-mc}

该过程使用 [`mc`](/zh/reference/minio-mc/#command-mc) 对 MinIO 集群执行操作。请在一台可同时通过网络访问源集群 和目标集群的机器上安装 [`mc`](/zh/reference/minio-mc/#command-mc)。有关下载和安装 `mc` 的说明，请参阅 `mc` [快速安装](/zh/reference/minio-mc/#mc-install)。

使用 [`mc alias set`](/zh/reference/minio-mc/mc-alias-set/#command-mc.alias.set) 命令为源 MinIO 集群和目标 S3 兼容服务创建别名。 创建别名时，需要为源集群和目标集群上的用户指定访问密钥。指定的用户必须具备 配置和应用过期操作所需的 [权限](#minio-lifecycle-management-create-expiry-rule-permissions)。

<a id="minio-lifecycle-management-create-expiry-rule-permissions"></a>

### 所需权限 {#required-permissions}

MinIO 要求对创建生命周期管理规则的存储桶或多个存储桶授予以下权限。

- [`s3:PutLifecycleConfiguration`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.s3-PutLifecycleConfiguration)
- [`s3:GetLifecycleConfiguration`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.s3-GetLifecycleConfiguration)

如果要在某个集群上为对象转换生命周期管理规则创建远程层，MinIO 还要求在该 集群上具备以下管理权限：

- [`admin:SetTier`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.admin-SetTier)
- [`admin:ListTier`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.admin-ListTier)

例如，以下策略授予了在该集群任意存储桶上配置对象转换生命周期管理规则的 权限：

```json
{
   "Version": "2012-10-17",
   "Statement": [
      {
            "Action": [
               "admin:SetTier",
               "admin:ListTier"
            ],
            "Effect": "Allow",
            "Sid": "EnableRemoteTierManagement"
      },
      {
            "Action": [
               "s3:PutLifecycleConfiguration",
               "s3:GetLifecycleConfiguration"
            ],
            "Resource": [
                        "arn:aws:s3:::*"
            ],
            "Effect": "Allow",
            "Sid": "EnableLifecycleManagementRules"
      }
   ]
}
```

## 按天数使对象过期 {#expire-objects-after-number-of-days}

使用带有 [`--expire-days`](/zh/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-expire-days) 的 [`mc ilm rule add`](/zh/reference/minio-mc/mc-ilm-rule-add/#command-mc.ilm.rule.add)， 可在对象创建若干天后使存储桶内容过期：

```shell
mc ilm rule add ALIAS/PATH --expire-days "DAYS"
```

- 将 [`ALIAS`](/zh/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.ALIAS) 替换为 S3 兼容主机的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。
- 将 [`PATH`](/zh/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.ALIAS) 替换为 S3 兼容主机上该存储桶的 路径。
- 将 [`DAYS`](/zh/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-expire-days) 替换为对象过期前的天数。 例如，指定 `30` 表示对象会在创建 30 天后过期。

## 使已版本控制的对象过期 {#expire-versioned-objects}

使用 [`mc ilm rule add`](/zh/reference/minio-mc/mc-ilm-rule-add/#command-mc.ilm.rule.add) 使非当前对象版本和对象删除标记过期：

- 若要让非当前对象版本在指定天数后过期，请包含 [`--noncurrent-expire-days`](/zh/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-noncurrent-expire-days)。
- 若要让没有剩余版本的对象的删除标记过期，请包含 [`--expire-delete-marker`](/zh/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-expire-delete-marker)。

```shell
mc ilm rule add ALIAS/PATH \
   --noncurrent-expire-days NONCURRENT_DAYS \
   --expire-delete-marker
```

- 若要让对象的所有版本过期，请将 [`--expire-all-object-versions`](/zh/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-expire-all-object-versions) 与 [`--expire-days`](/zh/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-expire-days) 一同指定。此过期规则仅适用于最新或当前版本不是 `DeleteMarker` 的对象。

  ```shell
  mc ilm rule add ALIAS/PATH \
     --expire-days "DAYS" \
     --expire-all-object-versions
  ```

- 将 [`ALIAS`](/zh/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.ALIAS) 替换为 S3 兼容主机的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。
- 将 [`PATH`](/zh/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.ALIAS) 替换为 S3 兼容主机上该存储桶的 路径。
- 将 [`NONCURRENT_DAYS`](/zh/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-noncurrent-expire-days) 替换为非当前对象版本过期前的 天数。例如，指定 `30d` 表示某个版本在成为非当前版本至少 30 天后过期。

## 过期行为说明 {#expiration-behavior}

自 [SILO 20261109](/zh/blog/release/silo-20261109/) 起，生命周期过期执行以下行为（详见[对象生命周期管理](/zh/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration)）：

- **多池法定人数复核：** 过期判定会在对象锁内跨所有存储池评估，并要求取得权威法定人数后才移除版本（[#278](https://github.com/pgsty/silo/issues/278)）。请升级全部服务节点以使所有存储池执行相同检查。
- **精确键整键删除与仅含删除标记规则：** `ExpiredObjectAllVersions` 与 `DelMarkerExpiration` 仅作用于已过期的精确对象键，不会波及前缀下的子键，且拒绝包含已分层版本或受 Object Lock 保护版本的对象键（[#297](https://github.com/pgsty/silo/issues/297)）。唯一动作为 `DelMarkerExpiration` 的规则可正常执行（[#268](https://github.com/pgsty/silo/issues/268)）。
- **恢复副本与远程层保留：** 已恢复副本到期时仅清理本地临时缓存，同时保留对象版本及其远程层数据（[#281](https://github.com/pgsty/silo/issues/281)）。SILO 在普通版本历史中排除分层 free-version 标记（[#263](https://github.com/pgsty/silo/issues/263)），且只要其他存储池仍引用某份远程层对象，就会保留该远程数据（[#306](https://github.com/pgsty/silo/issues/306)、[#308](https://github.com/pgsty/silo/issues/308)）。
- **生命周期删除不复制：** 生命周期规则创建的删除标记与版本清除不会通过存储桶复制或站点复制传播（提交 [`1bd0b1b04`](https://github.com/pgsty/silo/commit/1bd0b1b04)），行为与 AWS S3 一致。如有需要，请在源存储桶和目标存储桶上分别配置过期规则。

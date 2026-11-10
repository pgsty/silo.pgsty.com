---
title: "Silo 对象锁定"
url: "/zh/administration/object-management/object-retention/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/object-management/object-retention.rst
upstream_modified: true
---

<a id="minio-object-retention"></a>
<a id="minio-object-locking"></a>

- [Object locking and retention overview](https://youtu.be/Hk9Z-sltUu8?ref=docs)
- [Object locking and retention lab](https://youtu.be/thNus-DL1u4?ref=docs)

## 概述 {#overview}

**SILO 20261109 更新：** [SILO 20261109](/zh/blog/release/silo-20261109/) 在批量删除、多池版本、目录 `null` 版本、复制清除、生命周期整键删除规则以及批处理作业中统一执行 Object Lock 检查；请升级所有服务节点，使每个池和站点执行一致的锁定规则。此前，[SILO 20261018](/zh/blog/release/silo-20261018/#security) 修复了保留期授权与受保护版本覆盖问题（SN-2026-015/016，Server 20260916 仍受影响）：每次保留期更新均要求 `s3:PutObjectRetention`，削弱生效中的 `GOVERNANCE` 保留期还要求携带 `x-amz-bypass-governance-retention: true` 请求头及 `s3:BypassGovernanceRetention` 权限。单独升级客户端或 Console 不会修补 Server，升级也不会恢复此前已被覆盖的数据或保留期。受影响路径与缓解措施见[安全公告](/zh/blog/security/20260926-governance-retention-bypass/)。

MinIO 对象锁定（“对象保留”）通过强制执行一次写入、多次读取（WORM）不可变性，防止 [已启用版本控制的对象](/zh/administration/object-management/object-versioning/#minio-bucket-versioning) 被删除。MinIO 同时支持 [基于时长的对象保留](#minio-object-locking-retention-modes) 和 [无限期 legal hold 保留](#minio-object-locking-legalhold)。

历史上游 MinIO 的对象锁定曾获 [Cohasset Associates](https://min.io/cohasset?ref-docs) 针对 SEC 17a-4(f)、FINRA 4511(c) 和 CFTC 1.31(c)-(d) 的第三方合规评估。该评估仅适用于受评的历史上游 MinIO 版本，尚未针对 PGSTY SILO 进行独立重新认证。

{{< cards >}}
{{< card title="未启用锁定的存储桶" image="/images/retention/minio-versioning-delete-object.svg" image_alt="删除对象" >}}
MinIO 版本控制会保留对象变更的完整历史。 但应用仍可显式删除特定对象版本。
{{< /card >}}
{{< card title="启用锁定的存储桶" image="/images/retention/minio-object-locking.svg" image_alt="锁定 30 天的对象" >}}
对存储桶中的对象应用默认 30 天的 WORM 锁，可确保所有对象版本在最短保留期内受到保护。
{{< /card >}}
{{< card title="锁定存储桶中的删除操作" image="/images/retention/minio-object-locking-delete.svg" image_alt="锁定存储桶中的删除操作" >}}
[删除操作](/zh/administration/object-management/object-delete/#minio-object-delete) 在 [已启用版本控制的存储桶](/zh/administration/object-management/object-versioning/#minio-bucket-versioning-delete) 中遵循常规行为，即 MinIO 会为对象创建 `DeleteMarker`。不过，对象中非 Delete Marker 的版本仍受保留规则约束，可防止任何针对特定版本的删除或覆盖尝试。
{{< /card >}}
{{< card title="锁定存储桶中的版本删除操作" image="/images/retention/minio-object-locking-delete-version.svg" image_alt="锁定存储桶中的版本删除操作" >}}
对于受 WORM 锁定保护的特定对象版本，MinIO 会阻止任何 [删除](/zh/administration/object-management/object-delete/#minio-object-delete) 尝试。客户端最早只能在锁过期后删除该版本。
{{< /card >}}
{{< /cards >}}

MinIO 对象锁定在功能和 API 层面与 AWS S3 [兼容](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)。 本页概述了 MinIO 中对象锁定/保留的实现概念。更多信息请参见 AWS S3 文档 [How S3 Object Lock works](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)。

按照 [S3 的行为](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-overview.html#object-lock-bucket-config)， 只能在创建存储桶时启用对象锁定。对于创建时未启用锁定的存储桶，之后无法再启用对象锁定。启用后，你可以在任意时刻配置对象保留规则。对象锁定依赖 [版本控制](/zh/administration/object-management/object-versioning/#minio-bucket-versioning)，并会隐式启用该特性。

<a id="minio-bucket-locking-interactions-versioning"></a>

### 与版本控制的交互 {#interaction-with-versioning}

受 WORM 锁定保护的对象在锁过期或被显式解除之前均不可变更。锁定以对象版本为粒度，每个版本都独立保持不可变。

如果应用对受锁定对象执行未指定版本的删除操作，该操作会生成一个 [Delete Marker](/zh/administration/object-management/object-versioning/#minio-bucket-versioning-delete)。 任何显式删除受 WORM 锁定对象的尝试都会报错失败。Delete Marker *不* 受 WORM 锁定保护。 更多信息请参见 S3 文档 [Managing delete markers and object lifecycles](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-managing.html#object-lock-managing-lifecycle)。

例如，考虑以下默认启用了 [GOVERNANCE 模式](#minio-object-locking-governance) 锁定的存储桶：

```shell
$ mc ls --versions play/locking-guide

  [DATETIME]    29B 62429eb1-9cb7-4dc5-b507-9cc23d0cc691 v3 PUT data.csv
  [DATETIME]    32B 78b3105a-02a1-4763-8054-e66add087710 v2 PUT data.csv
  [DATETIME]    23B c6b581ca-2883-41e2-9905-0a1867b535b8 v1 PUT data.csv
```

由于对象锁定设置，对 `data.csv` 的 *特定版本* 执行删除会失败：

```shell
$ mc rm --version-id 62429eb1-9cb7-4dc5-b507-9cc23d0cc691 play/data.csv

  Removing `play/locking-guide/data.csv` (versionId=62429eb1-9cb7-4dc5-b507-9cc23d0cc691).
  mc: <ERROR> Failed to remove `play/locking-guide/data.csv`.
      Object, 'data.csv (Version ID=62429eb1-9cb7-4dc5-b507-9cc23d0cc691)' is
      WORM protected and cannot be overwritten
```

对 `data.csv` 执行未指定版本的删除会成功，并为对象创建一个新的 `DeleteMarker`：

```shell
$ mc rm play/locking-guide/data.csv

  [DATETIME]     0B acce329f-ad32-46d9-8649-5fe8bf4ec6e0 v4 DEL data.csv
  [DATETIME]    29B 62429eb1-9cb7-4dc5-b507-9cc23d0cc691 v3 PUT data.csv
  [DATETIME]    32B 78b3105a-02a1-4763-8054-e66add087710 v2 PUT data.csv
  [DATETIME]    23B c6b581ca-2883-41e2-9905-0a1867b535b8 v1 PUT data.csv
```

### 与生命周期管理的交互 {#interaction-with-lifecycle-management}

对于受过期规则覆盖的对象，MinIO [对象过期](/zh/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) 会遵循所有生效中的对象锁定和保留设置。

- 对于仅作用于 *当前* 对象版本的过期规则， MinIO 会为受锁定对象创建一个 Delete Marker。
- 对于作用于 *非当前对象版本* 的过期规则， MinIO 只能在保留期结束 *之后*，或保留已被显式解除时（例如 legal hold）对非当前版本执行过期。

例如，考虑以下默认启用了 [GOVERNANCE 模式](#minio-object-locking-governance) 且保留期为 45 天的存储桶：

```shell
$ mc ls --versions play/locking-guide

  [7D]    29B 62429eb1-9cb7-4dc5-b507-9cc23d0cc691 v3 PUT data.csv
  [30D]    32B 78b3105a-02a1-4763-8054-e66add087710 v2 PUT data.csv
  [60D]    23B c6b581ca-2883-41e2-9905-0a1867b535b8 v1 PUT data.csv
```

为超过 7 天的 *当前* 对象创建过期规则时，会为该对象生成一个 Delete Marker：

```shell
$ mc ls --versions play/locking-guide

  [0D]     0B acce329f-ad32-46d9-8649-5fe8bf4ec6e0 v4 DEL data.csv
  [7D]    29B 62429eb1-9cb7-4dc5-b507-9cc23d0cc691 v3 PUT data.csv
  [30D]    32B 78b3105a-02a1-4763-8054-e66add087710 v2 PUT data.csv
  [60D]    23B c6b581ca-2883-41e2-9905-0a1867b535b8 v1 PUT data.csv
```

不过，对于超过 7 天的 *非当前* 对象，过期规则只有在已配置的 WORM 锁过期 *之后* 才会生效。由于该存储桶设置了 45 天的 `GOVERNANCE` 保留，因此只有 `data.csv` 的 `v1` 版本已解锁，因而可被删除。

在 [SILO 20261109](/zh/blog/release/silo-20261109/) 中，生命周期整键删除动作（`ExpiredObjectAllVersions` 与 `DelMarkerExpiration`，[#297](https://github.com/pgsty/silo/issues/297)）以及批处理 `expire` 和 `keyrotate` 作业（[#310](https://github.com/pgsty/silo/issues/310)）同样会保留受 Object Lock 保护的版本，而不会绕过生效中的保留期或 legal hold。

### 与批量删除和复制的交互 {#interaction-with-bulk-deletion-and-replication}

自 [SILO 20261109](/zh/blog/release/silo-20261109/) 起，批量删除与复制执行以下 Object Lock 保护机制：

- **持变更锁串行核验物理版本清除（`DeleteObjects`）：** S3 `DeleteObjects` 在执行物理版本移除时，会使用与保留期和 legal hold 更新相同的变更锁逐项串行核验，并合并所有存储池的保护状态（提交 [`6ef3a52fc`](https://github.com/pgsty/silo/commit/6ef3a52fc)）。因此在启用 Object Lock 的存储桶中，大批量物理版本清除耗时更长；创建删除标记以及普通存储桶仍保持并发批量路径。
- **目录 `null` 版本保护：** 批量删除在移除目录对象的 `null` 版本前，会检查该目录对象的 Object Lock 保留期与 legal hold 状态（提交 [`aa2d79daf`](https://github.com/pgsty/silo/commit/aa2d79daf)）。
- **复制删除保留目标端锁保护：** 存储桶复制与站点复制在执行复制删除时保留目标端的 legal hold 与保留期（提交 [`7e9ee6bef`](https://github.com/pgsty/silo/commit/7e9ee6bef)）。源端绕过 `GOVERNANCE` 保留期执行的物理清除不会赋予目标端绕过权限；只要目标端副本仍受有效保护，目标端就会拒绝清除并由源端重试。

## 教程 {#tutorials}

### 创建启用对象锁定的存储桶 {#create-bucket-with-object-locking-enabled}

按照 S3 的行为，必须在创建存储桶时启用对象锁定。 你可以使用 MinIO [`mc`](/zh/reference/minio-mc/#command-mc) CLI 或 S3 兼容 SDK 创建启用了对象锁定的存储桶。

使用带有 [`--with-lock`](/zh/reference/minio-mc/mc-mb/#mc.mb.-with-lock) 选项的 [`mc mb`](/zh/reference/minio-mc/mc-mb/#command-mc.mb) 命令创建启用了对象锁定的存储桶：

```shell
mc mb --with-lock ALIAS/BUCKET
```

- 将 `ALIAS` 替换为已配置 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。
- 将 `BUCKET` 替换为要创建的存储桶 [`名称`](/zh/reference/minio-mc/mc-mb/#mc.mb.ALIAS)。

### 配置存储桶默认对象保留 {#configure-bucket-default-object-retention}

你可以使用 MinIO [`mc`](/zh/reference/minio-mc/#command-mc) CLI 或 S3 兼容 SDK 配置对象锁定规则（“对象保留”）。

MinIO 同时支持设置存储桶默认保留规则和按对象设置保留规则。 以下示例演示的是存储桶默认保留。对于按对象设置保留，请参见所选 SDK 中相应 `PUT` 操作的文档。

使用带有 [`--recursive`](/zh/reference/minio-mc/mc-retention-set/#mc.retention.set.-recursive) 和 [`--default`](/zh/reference/minio-mc/mc-retention-set/#mc.retention.set.-default) 选项的 [`mc retention set`](/zh/reference/minio-mc/mc-retention-set/#command-mc.retention.set) 命令，为存储桶设置默认保留模式：

```shell
mc retention set --recursive --default MODE DURATION ALIAS/BUCKET
```

- 将 [`MODE`](/zh/reference/minio-mc/mc-retention-set/#mc.retention.set.MODE) 替换为 [COMPLIANCE](#minio-object-locking-compliance) 或 [GOVERNANCE](#minio-object-locking-governance)。
- 将 [`DURATION`](/zh/reference/minio-mc/mc-retention-set/#mc.retention.set.VALIDITY) 替换为对象锁定持续生效的时长。
- 将 [`ALIAS`](/zh/reference/minio-mc/mc-retention-set/#mc.retention.set.ALIAS) 替换为已配置 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。
- 将 [`BUCKET`](/zh/reference/minio-mc/mc-retention-set/#mc.retention.set.ALIAS) 替换为要设置默认保留规则的存储桶名称。

### 启用 Legal Hold 保留 {#enable-legal-hold-retention}

你可以使用 MinIO [`mc`](/zh/reference/minio-mc/#command-mc) CLI 或 S3 兼容 SDK，为对象启用或禁用无限期 legal hold 保留。

你可以对已经处于 [COMPLIANCE](#minio-object-locking-compliance) 或 [GOVERNANCE](#minio-object-locking-governance) 锁定下的对象设置 legal hold。 即使保留锁过期，对象在 legal hold 生效期间仍会保持 WORM 锁定。 你或其他拥有必要权限的用户必须显式解除 legal hold，才能移除 WORM 锁。

使用 **mc legalhold set** 命令切换对象的 legal hold 状态。

```shell
mc legalhold set ALIAS/PATH
```

- 将 [`ALIAS`](/zh/reference/minio-mc/mc-legalhold-set/#mc.legalhold.set.ALIAS) 替换为已配置 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。
- 将 [`PATH`](/zh/reference/minio-mc/mc-legalhold-set/#mc.legalhold.set.ALIAS) 替换为要启用 legal hold 的对象路径。

<a id="minio-object-locking-retention-modes"></a>

## 对象保留模式 {#object-retention-modes}

MinIO 实现了以下 [S3 对象锁定模式](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-overview.html)：

| 模式                                                | 说明                                                                                                                                                                                                                                                                                                                     |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [GOVERNANCE 模式](#minio-object-locking-governance) | 阻止非特权用户修改或变更对象及其锁定设置。在存储桶或对象上拥有 [`s3:BypassGovernanceRetention`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.s3-BypassGovernanceRetention) 权限的用户携带绕过请求头时，可以修改对象或其锁定设置。配置的保留时长到期后，SILO 会自动解除该锁。 |
| [COMPLIANCE 模式](#minio-object-locking-compliance) | 阻止任何修改或变更对象及其锁定设置的操作。在保留期届满前，包括 [root](/zh/administration/identity-access-management/minio-user-management/#minio-users-root) 用户在内的任何用户都无法修改对象或缩短保留期。配置的保留时长到期后，SILO 会自动解除该锁。                                                                   |
{.wide .expand}

<a id="minio-object-locking-governance"></a>

### GOVERNANCE 模式 {#governance-mode}

处于 `GOVERNANCE` 锁定下的对象可防止非特权用户执行写操作。

`GOVERNANCE` 锁定对象提供受管控的不可变性。拥有 [`s3:BypassGovernanceRetention`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.s3-BypassGovernanceRetention) 操作权限的用户可以修改被锁定对象、调整保留时长，或完全解除该锁。绕过 `GOVERNANCE` 保留还要求在请求中设置 `x-amz-bypass-governance-retention:true` header。

MinIO 的 `GOVERNANCE` 锁在功能上与 [S3 GOVERNANCE 模式](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html#object-lock-retention-modes) 完全一致。

<a id="minio-object-locking-compliance"></a>

### COMPLIANCE 模式 {#compliance-mode}

处于 `COMPLIANCE` 锁定下的对象可防止 *所有* 用户执行写操作，包括 [MinIO root](/zh/administration/identity-access-management/minio-user-management/#minio-users-root) 用户。

`COMPLIANCE` 锁定对象提供完全不可变性。 在配置的保留时长结束之前，无法更改或移除该锁。

MinIO 的 `COMPLIANCE` 锁在功能上与 [S3 COMPLIANCE 模式](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html#object-lock-retention-modes) 完全一致。

<a id="minio-object-locking-legalhold"></a>

## Legal Hold {#legal-hold}

处于 legal hold 状态下的对象可防止 *所有* 用户执行写操作，包括 [MinIO root](/zh/administration/identity-access-management/minio-user-management/#minio-users-root) 用户。

legal hold 为无限期，并对锁定对象强制执行完全不可变性。 只有拥有 [`s3:PutObjectLegalHold`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.s3-PutObjectLegalHold) 权限的特权用户才能设置或解除 legal hold。

legal hold 在对象级别生效。 如果你为一组对象启用 legal hold，例如某个存储桶中的现有内容，则该存储桶后续新创建的对象不会受到影响。

legal hold 与 [GOVERNANCE 模式](#minio-object-locking-governance) 和 [COMPLIANCE 模式](#minio-object-locking-compliance) 保留设置是互补关系。 同时受 legal hold 和 `GOVERNANCE/COMPLIANCE` 保留规则保护的对象，会持续保持 WORM 锁定，直到 legal hold 被解除 *且* 规则到期。

对于 `GOVERNANCE` 锁定对象，即使用户拥有绕过保留的必要权限，legal hold 仍会阻止其修改该对象。

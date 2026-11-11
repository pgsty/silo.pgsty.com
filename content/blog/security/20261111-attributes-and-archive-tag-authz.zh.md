---
title: "SN-2026-024：GetObjectAttributes 与只读 ZIP 归档扩展（x-minio-extract）标签策略及读取权限绕过"
linkTitle: "SN-2026-024 · 对象属性与归档鉴权"
date: 2026-11-11
author: "冯若航"
description: "GetObjectAttributes 与 S3 ZIP 在线读取扩展（x-minio-extract: true）在读取持久化对象标签前即完成策略鉴权，且归档内部目录列举仅校验 s3:ListBucket 而未校验 s3:GetObject，同时在只读请求中向对象元数据写回索引。"
tags: [安全, S3, Authorization, Tagging, Archive, SILO]
weight: 1
draft: false
url: "/zh/blog/security/20261111-attributes-and-archive-tag-authz/"
---

**发布状态：** 主干已修复（[`f746d0707`](https://github.com/pgsty/silo/commit/f746d07076faaf9be1479aadfaf904a4793fa8c0)），将随 [`20261109`](/zh/blog/release/silo-20261109/) 之后的下一版 Server 发布\
**安全编号：** `SN-2026-024`（[安全公告台账](/zh/about/security-advisories/#sn-2026-024)，[#342](https://github.com/pgsty/silo/issues/342)）\
**严重程度：** 高危（High）\
**影响范围：** **SILO Server**（`RELEASE.2026-11-09T00-00-00Z` 及更早版本）与自 `2021-06-10`（[`ba5fb2365`](https://github.com/pgsty/silo/commit/ba5fb2365cc9797fcf4952041e9cfb035b8277f8)）和 `2024-01-05`（[`9b8ba97f9`](https://github.com/pgsty/silo/commit/9b8ba97f9fc0a39ea6632443a102bd42f8067da3)）以来的上游原版 MinIO\
**不受影响组件：** `silo-console`、`mcli`、`silo-pkg` 与 `kes`

在 SILO 的标准 `GetObject` 与 `HeadObject` 处理链路中，服务端先完成调用方身份认证，读取目标对象版本的 `ObjectInfo`，再将 `objInfo.UserTags` 传入策略引擎校验 `s3:GetObject`（或 `s3:GetObjectVersion`），从而确保基于对象已有标签条件（`s3:ExistingObjectTag/<key>`）的 IAM 规则准确生效。继承自上游 MinIO 的两类读取接口绕过了这一步“读取元数据后的标签复核”：`GetObjectAttributes`（`GET /<bucket>/<key>?attributes`）以及 `.zip` 归档在线读取扩展（携带 `x-minio-extract: true` 的 `GET`、`HEAD` 与 `ListObjectsV2`）。此外，归档内部成员列举仅凭桶级 `s3:ListBucket` 权限即可解析 `.zip` 中央目录而无需 `s3:GetObject`，且读取未预建索引的 `.zip` 对象时会在只读动词中调用 `PutObjectMetadata` 改写磁盘元数据。

## 摘要 {#summary}

- **问题本质：**
  1. **`GetObjectAttributes` 绕过 `s3:ExistingObjectTag` 条件策略：** `getObjectAttributesHandler`（`cmd/object-handlers.go`）在调用 `objectAPI.GetObjectInfo` **之前**执行 `checkRequestAuthType`（内部传入空标签 `""`），读取到 `objInfo.UserTags` 后从未重新评估 `s3:GetObjectAttributes` 与 `s3:GetObject`（或带版本号的对应动作）。受 `s3:ExistingObjectTag/*` 显式 `Deny` 限制的调用方仍可获得 `200 OK` 并读取对象校验和、分片布局与大小，而依赖标签匹配才授予 `Allow` 的调用方则被误拒为 `403 AccessDenied`。
  2. **ZIP 成员 `GET` / `HEAD` 绕过标签 `Deny` 读取明文（`x-minio-extract: true`）：** `getObjectInArchiveFileHandler` 与 `headObjectInArchiveFileHandler`（`cmd/s3-zip-handlers.go`）同样在读取 `.zip` 对象标签前按空标签鉴权。被策略明确禁止访问带敏感标签（如 `classification=secret`）对象的调用方，虽然直接请求 `GET /bucket/archive.zip` 会收到 `403`，但只需附带 `x-minio-extract: true` 请求 `GET /bucket/archive.zip/secret.txt`，即可绕过标签拦截直接提取归档内的任意明文文件。
  3. **ZIP 成员 `ListObjectsV2` 绕过 `s3:GetObject` 泄露归档内部结构：** `listObjectsV2InArchive`（携带 `x-minio-extract: true` 请求 `GET /bucket?list-type=2&prefix=archive.zip/`）直接复用了外层桶级 `s3:ListBucket` 鉴权结果，未检查调用方是否对 `archive.zip` 拥有 `s3:GetObject` 权限。即使策略显式配置了 `Deny s3:GetObject`，仅持有列桶权限的账号仍可读取 `.zip` 数据流并枚举包内全部文件名、未压缩字节大小与时间戳。
  4. **只读请求附带隐式元数据写入：** 当被读取的 `.zip` 对象在上传时未预建归档索引时，`readObjectZIPInfo` 会在 `GET`、`HEAD` 与 `ListObjectsV2` 请求中后台调用 `PutObjectMetadata` 将生成的索引写回 `xl.meta`，违反了只读 HTTP 动词不修改持久化元数据的边界。
- **上游溯源：** `.zip` 在线提取扩展由上游 MinIO 于 `2021-06-10` 在提交 [`ba5fb2365`](https://github.com/pgsty/silo/commit/ba5fb2365cc9797fcf4952041e9cfb035b8277f8)（[minio/minio#12267](https://github.com/minio/minio/pull/12267)）中引入；`GetObjectAttributes` 由上游于 `2024-01-05` 在提交 [`9b8ba97f9`](https://github.com/pgsty/silo/commit/9b8ba97f9fc0a39ea6632443a102bd42f8067da3)（[minio/minio#18732](https://github.com/minio/minio/pull/18732)）中引入。
- **修复方式：** 提交 [`f746d0707`](https://github.com/pgsty/silo/commit/f746d07076faaf9be1479aadfaf904a4793fa8c0) 将两类路径统一拆分为前置身份认证与读取元数据后的真实标签鉴权：对 `GetObjectAttributes` 的双动作及 `.zip` 归档的 `GET`、`HEAD`、`ListObjectsV2` 全量绑定目标版本的真实 `UserTags`，强制要求归档列举具备针对 `.zip` 对象的 `s3:GetObject` 权限，并将读取路径上的归档索引构建改为纯内存无副作用操作。

---

## 一、上游溯源与根因分析 {#provenance}

### 为什么前置调用 `checkRequestAuthType` 会漏掉对象标签条件 {#pre-lookup}

在 `cmd/auth-handler.go` 中，`checkRequestAuthType` 将身份认证（`authenticateRequest`）与基于空标签的策略求值（`authorizeRequestWithExistingTags(..., "")`）打包为一步，适用于桶级操作或尚未存在目标对象的新建写入操作。而所有读取存量对象且需支持 `s3:ExistingObjectTag/<key>` 的接口（如标准 `GetObject` 与 `HeadObject`）都必须拆为两步：

1. 访问存储前先调用 `authenticateRequest` 完成验签；
2. 读取 `ObjectInfo`（或注入 `opts.CheckPrecondFn` 回调）后，将磁盘持久化的 `objInfo.UserTags` 传入 `authorizeRequestWithExistingTags`。

上游在实现 [`ba5fb2365`](https://github.com/pgsty/silo/commit/ba5fb2365cc9797fcf4952041e9cfb035b8277f8)（`cmd/s3-zip-handlers.go`）与 [`9b8ba97f9`](https://github.com/pgsty/silo/commit/9b8ba97f9fc0a39ea6632443a102bd42f8067da3)（`getObjectAttributesHandler`）时，均只保留了前置的 `checkRequestAuthType` 而遗漏了读取 `ObjectInfo` 后的标签鉴权：

- 在 **`GetObjectAttributes`** 中，按 AWS S3 规范调用方须同时具备 `s3:GetObjectAttributes` 与 `s3:GetObject`（带 `?versionId=` 时为 `s3:GetObjectVersionAttributes` 与 `s3:GetObjectVersion`）。前置按空标签求值导致针对任一动作的标签 `Deny` 失效、标签 `Allow` 被误拒。
- 在 **`.zip` 成员 `GET` / `HEAD`（`x-minio-extract: true`）** 中，只要桶内敏感数据以 `.zip` 归档存放并依靠对象标签做多租户或密级隔离，攻击者无需读取整包，直接请求归档内成员路径即可绕过标签 `Deny` 下载明文内容。

### 桶列举权限与对象内容读取权限的越界混淆 {#list-boundary}

当客户端发送 `GET /bucket?list-type=2&prefix=archive.zip/` 并携带 `x-minio-extract: true` 时，`listObjectsV2Handler`（`cmd/bucket-listobjects-handlers.go`）在校验完桶级 `s3:ListBucket` 后即转入 `listObjectsV2InArchive`。与普通命名空间前缀列举不同，`listObjectsV2InArchive` 需要调用 `getFilesListFromZIPObject`（底层执行 `GetObjectNInfo`）打开并解析 `archive.zip` 的对象数据字节。仅凭桶级 `s3:ListBucket` 即允许解析 `.zip` 内部目录，突破了“列举桶内对象键”与“读取对象内部载荷”之间的权限边界。

---

## 二、影响范围 {#impact}

| 受影响接口 / 能力                                 | 安全与行为影响                                                                                                                       |
| :------------------------------------------------ | :----------------------------------------------------------------------------------------------------------------------------------- |
| **`GetObjectAttributes`（`?attributes`）**        | 绕过基于 `s3:ExistingObjectTag/*` 的 `Deny` 规则（泄露校验和、ETag、分片数与字节大小）；基于标签匹配的 `Allow` 规则被误拒（`403`）。 |
| **ZIP 成员 `GET` / `HEAD`（`x-minio-extract`）**  | 完全绕过基于 `s3:ExistingObjectTag/*` 的 `Deny` 规则读取 `.zip` 包内任意文件明文；基于标签匹配的 `Allow` 规则被误拒。                |
| **ZIP 成员 `ListObjectsV2`（`x-minio-extract`）** | 仅持有 `s3:ListBucket` 的主体即使被显式 `Deny s3:GetObject`，仍可读取任意 `.zip` 包内的完整文件清单与未压缩大小。                    |
| **读取未预建索引的 `.zip` 对象**                  | `GET`、`HEAD`、`LIST` 在读取过程中调用 `PutObjectMetadata` 改写对象持久化元数据。                                                    |
{.wide .expand}

---

## 三、修复方案：设计思考与充分必要性 {#fix}

提交 [`f746d0707`](https://github.com/pgsty/silo/commit/f746d07076faaf9be1479aadfaf904a4793fa8c0) 将上述全部读取路径对齐至存储后标签鉴权与只读无副作用不变量：

1. **`GetObjectAttributes` 双动作真实标签鉴权（`cmd/object-handlers.go`）：**
   - 根据是否指定 `opts.VersionID` 选定 `[s3:GetObjectAttributes, s3:GetObject]` 或对应 `*Version*` 双动作，前置执行 `authenticateRequest`；
   - 读取 `objInfo` 后，对两个动作逐一执行 `authorizeRequestWithExistingTags(..., objInfo.UserTags)`（读取报错时通过 `authorizeRequestWithUnreadTags` 判断权限），同时保留缺失对象的 `s3:ListBucket` 掩码语义，并确保已授权调用方在遇到底层磁盘读仲裁不足时收到真实的 `503 SlowDownRead` 而非误报 `403`。
2. **ZIP `GET`、`HEAD` 与 `ListObjectsV2` 闭环鉴权（`cmd/s3-zip-handlers.go`、`cmd/bucket-listobjects-handlers.go`）：**
   - 将鉴权目标 `ReqInfo.ObjectName` 精确绑定为外层归档键名 `zipPath`（标签与对象级策略均挂载在 `.zip` 对象自身上）；
   - 在初次 `GetObjectInfo` 与后续 `GetObjectNInfo` 范围读取的 `opts.CheckPrecondFn` 回调中均执行 `authorizeRequestWithExistingTags(ctx, r, policy.GetObjectAction, oi.UserTags)`，消除元数据读取与分块解压之间的并发标签变更窗口；
   - 在 `listObjectsV2InArchive` 中强制校验调用方对 `zipPath` 的 `s3:GetObject` 权限（含真实标签条件），未获授权时返回 `PrefixAccessDenied`（`403 AccessDenied`）。
3. **剥离只读路径上的元数据写回（`cmd/s3-zip-handlers.go`）：**
   - `readObjectZIPInfo` 改为纯内存构建并返回序列化索引，绝不调用 `PutObjectMetadata`；持久化写回函数 `updateObjectMetadataWithZipInfo` 仅保留给显式携带 `x-minio-extract: true` 的上传写路径调用。

### 为什么该设计既必要又充分 {#sufficiency}

- **必要性：** 在 `.zip` 提取路径上，服务端先读一次 `GetObjectInfo` 定位成员偏移量，随后再发起一次 `GetObjectNInfo` 读取压缩数据段；若不在 `opts.CheckPrecondFn` 内二次校验所打开版本的 `UserTags`，并发打标仍可能产生竞态窗口。同时，只有彻底移除读取时的 `PutObjectMetadata`，才能保证只读请求不污染 `xl.meta`、不触发意外的元数据复制，也不会在只读或对象锁场景下产生隐式写冲突。
- **充分性：** 所有涉及对象属性与 `.zip` 归档读取的入口（`getObjectAttributesHandler`、`getObjectInArchiveFileHandler`、`headObjectInArchiveFileHandler`、`listObjectsV2InArchive`）均已纳入同一套基于真实标签的鉴权模型，并由 `cmd/object-attributes-archive-tags_test.go` 与 `cmd/object-attributes-read-error_test.go` 完整覆盖正反向条件策略与存储异常场景。

---

## 四、利弊权衡、潜在代价与边界 {#tradeoffs}

| 权衡维度                                     | 收益与代价说明                                                                                                                                                                                                                                                                                                                                                 |
| :------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **未预建索引 `.zip` 对象的重复读取开销**     | 修复前，普通上传的 `.zip` 在首次被 `x-minio-extract: true` 读取时会把目录索引写回 `xl.meta` 供后续复用；修复后只读请求不再改写磁盘元数据，未预建索引的 `.zip` 每次按归档方式读取时会从末尾中央目录在内存中构建索引。对超大 `.zip` 有高频在线提取需求的业务，可在上传（`PutObject` / `CompleteMultipartUpload`）时显式附带 `x-minio-extract: true` 持久化索引。 |
| **归档内部列举必须具备 `s3:GetObject` 权限** | 此前仅被授予 `s3:ListBucket`（而无权读取 `.zip` 对象内容）的账号将无法再通过 `x-minio-extract: true` 枚举 `.zip` 内部成员列表（返回 `403 AccessDenied`）。确需在线浏览包内目录的角色需补充对相应 `.zip` 前缀的 `s3:GetObject` 授权。                                                                                                                           |
{.wide .expand}

---

## 升级指引与缓解建议 {#remediation}

1. **升级 SILO Server** 至包含提交 [`f746d0707`](https://github.com/pgsty/silo/commit/f746d07076faaf9be1479aadfaf904a4793fa8c0) 的 `20261109` 后续发布版本。
2. **升级前网关层临时缓解：** 若未升级集群依赖 `s3:ExistingObjectTag/*` 的 `Deny` 规则保护敏感对象（尤其是 `.zip` 归档包），可在升级完成前于反向代理层拦截携带 `x-minio-extract` 请求头或 `?attributes` 查询参数的外部请求。
3. **核对归档浏览角色的 IAM 策略：** 若业务应用使用了 `x-minio-extract: true` 配合 `ListObjectsV2` 在线展示 `.zip` 内部目录，升级前请确认该角色除 `s3:ListBucket` 外已同时具备目标 `.zip` 对象的 `s3:GetObject` 权限。

更多信息请参阅[安全公告台账](/zh/about/security-advisories/#sn-2026-024)、[Server 候选兼容性说明](/zh/compatibility/server/#candidate-after-20261109)以及关联公告 [SN-2026-022（双活复制标签代理鉴权）](/zh/blog/security/20261111-tagging-replication-proxy-auth/)。

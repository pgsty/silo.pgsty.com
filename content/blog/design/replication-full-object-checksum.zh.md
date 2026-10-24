---
title: "FULL_OBJECT 校验和复制：在初始化上传时保留类型"
linkTitle: "FULL_OBJECT 复制"
date: 2026-10-24
lastmod: 2026-10-24
author: "冯若航"
summary: >
  PR #255 为分片 CRC 对象的复制恢复 FULL_OBJECT 校验和类型。本文记录 BadDigest 故障链路、上游回归来源、三行条件为何同时修复 CopyObject 复制，以及验证与升级要点。
tags: [Design, Replication, S3, Checksum]
weight: 8
draft: false
url: "/zh/blog/design/replication-full-object-checksum/"
---

[Issue #254](https://github.com/pgsty/silo/issues/254) 报告了一类复制故障：使用 `FULL_OBJECT` CRC32 或 CRC32C 校验和的分片上传对象在源端可正常上传和读取，但复制到目标端并在最后调用 `CompleteMultipartUpload` 时会因 `400 BadDigest` 失败。Denis Babchuk（`@botdeniska`）提交的 [PR #255](https://github.com/pgsty/silo/pull/255) 补回了出站复制请求遗漏的校验和类型头。

该补丁于 2026 年 10 月 24 日以 [`6d890fc86`](https://github.com/pgsty/silo/commit/6d890fc860c732cc0bd1925124c733362f803d2e) 直接合入主干并关闭 #254，共修改 **5 行生产代码（含 2 行注释）** 并新增 257 行回归测试。

## 故障现象 {#problem}

当分片上传对象的校验和类型记录为 `FULL_OBJECT`、算法为 CRC32 或 CRC32C 时，启用桶复制或站点复制会出现以下现象：

- 原始分片上传在源端成功完成，源端版本可正常读取。
- 复制发送端将所有分片传往目标端后，目标端在 `CompleteMultipartUpload` 阶段返回 `400 BadDigest`。
- 源端对象复制状态停留在 `FAILED`，目标端无法生成该版本的完整副本。
- 后续每次复制重试（包括对 `FAILED` 版本执行 `HeadObject` 触发的重入队）都会重新传输全部分片字节，并在完成阶段再次因同一错误失败。

分片 CRC64NVME 对象不受影响，因为接收端默认将 CRC64NVME 解释为 `FULL_OBJECT`；普通单次 `PUT` 与分片 `COMPOSITE` 上传也正常。此外，对受影响的分片 `FULL_OBJECT` 对象执行服务端 `CopyObject` 后再复制，会触发[下文](#copy)所述的另一条故障路径。

## 根因：仅转发算法无法区分校验和类型 {#root-cause}

对于分片 CRC32 和 CRC32C，同一算法支持两种截然不同的对象级校验和计算方式。设 `P1 ... Pn` 为各分片的字节内容，`||` 表示字节拼接：

| 类型 | 对象校验和的计算方式 |
| :-- | :-- |
| `FULL_OBJECT` | 对完整拼接内容 `P1 || ... || Pn` 计算 CRC，编码为 Base64 |
| `COMPOSITE` | 拼接各分片 CRC 的**原始摘要字节**，再对其计算 CRC、编码为 Base64，并在输出时附加 `-n` 分片数后缀 |

即便分片上传只有一个分片，这两种方式算出的摘要也通常不同。仅转发算法名称与摘要值，不足以还原校验和语义。

[复制发送端代码](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/cmd/bucket-replication.go#L843)中的完整故障链路如下：

1. `putReplicationOpts()` 调用 `getCRCMeta()` 构造对象校验和请求头。旧实现保留了摘要值和 `x-amz-checksum-algorithm`，但丢弃了 `x-amz-checksum-type`。
2. `replicateObjectWithMultipart()` 将这些选项传给目标端的 `NewMultipartUpload`。当算法为 CRC32 或 CRC32C 且未指定类型时，目标端默认将该分片上传初始化并持久化为 `COMPOSITE`。
3. 发送端传完各分片后，再次通过 `getCRCMeta()` 构造完成阶段的对象级校验和头，其中携带的摘要仍是源端的整对象（`FULL_OBJECT`）CRC。
4. 目标端的[`CompleteMultipartUpload` 校验逻辑](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/cmd/erasure-multipart.go#L1378)读取初始化时持久化的 `COMPOSITE` 类型，将收到的整对象 CRC 与“分片 CRC 的复合 CRC”进行比对，因摘要不匹配返回 `BadDigest`。

| 阶段 | 修复前 | 修复后 |
| :-- | :-- | :-- |
| 源端校验和元数据 | CRC32/CRC32C + `FULL_OBJECT` | 不变 |
| 目标端初始化请求头 | 仅含算法，缺失类型 | 算法 + `FULL_OBJECT` |
| 目标端持久化的上传类型 | `COMPOSITE` | `FULL_OBJECT` |
| 完成请求的校验和 | 源端整对象 CRC | 源端整对象 CRC + 显式 `FULL_OBJECT` 类型 |
| 目标端校验结果 | `400 BadDigest` | 校验通过，完成复制 |

核心不变量：**复制必须在初始化与完成两个阶段同时保留校验和的算法、摘要值与类型解释方式**，使目标端按与源端一致的规则执行完整性校验。

## 历史演进与上游回归来源 {#history}

上游 MinIO 于 2025 年 8 月 22 日在 PR #21535 中合入提交 [`4ea6f3b06`](https://github.com/minio/minio/commit/4ea6f3b06b5dc18bf967d1c13b97f33cc8bcdd87)，从 `getCRCMeta()` 中删掉了校验和类型转发。在那之前，`getCRCMeta()` 会无条件转发所有校验和的类型；但直接回退到无条件转发又会破坏普通单次 `PUT` 的 SHA 校验和复制（见[下文](#guard)）。

此前 SILO 针对分片完成阶段做过三项相关修复，均处于不同链路环节：

| 此前修复 | 解决的问题 | 为何未覆盖本次复制故障 |
| :-- | :-- | :-- |
| [`c8590413f`](https://github.com/pgsty/silo/commit/c8590413fd321a315f3779cd9b2a6f1cb72064da)（#31） | 允许 `FULL_OBJECT` 完成请求省略逐分片校验和并完成整对象校验 | 前提是接收端在初始化时已知该上传为 `FULL_OBJECT` |
| [`7e079ff05`](https://github.com/pgsty/silo/commit/7e079ff05c842afabb73c4572885cfb74604df17) | 校验完成请求显式携带的类型是否与初始化类型一致 | 复制发送端在初始化和完成两个阶段均未发送类型 |
| [CompleteMultipartUpload 响应补齐 ChecksumType](/zh/blog/design/complete-multipart-checksum-type/) | 向客户端 SDK 的完成响应返回 `ChecksumType` | 仅作用于上传完成后的响应编码，不影响复制发送端构造的出站请求头 |

## 最小修复实现 {#implementation}

在 [`getCRCMeta()`](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/cmd/bucket-replication.go#L4242) 复制已识别的校验和摘要与算法之后，新增三行判断：

```go
if isMP && cktype.CanMerge() && cs[xhttp.AmzChecksumType] == xhttp.AmzChecksumTypeFullObject {
    meta[xhttp.AmzChecksumType] = xhttp.AmzChecksumTypeFullObject
}
```

三个条件分别约束了精确的转发范围：

- `isMP`：解码自**已落盘校验和的分片元数据标记**（不要求当前对象的 ETag 一定是带 `-n` 的分片格式）。
- `cktype.CanMerge()`：复用既有算法能力判断，仅匹配支持将分片 CRC 合并为整对象 CRC 的算法（CRC32、CRC32C 与 CRC64NVME）。
- `cs[xhttp.AmzChecksumType] == xhttp.AmzChecksumTypeFullObject`：仅当源端持久化类型确为 `FULL_OBJECT` 时才转发，绝不改动 `COMPOSITE` 对象。

由于分片复制的初始化阶段（`NewMultipartUpload`）与完成阶段（`CompleteMultipartUpload`）共用 `getCRCMeta()`，这一处修改同时补齐了两个阶段的请求头。逐分片上传请求读取的是不含对象级类型的分片校验和映射，其请求头保持不变；CRC64NVME 则显式携带与其默认行为一致的 `FULL_OBJECT`。

### 为什么不能转发所有已存类型？ {#guard}

普通单次 `PUT` 上传的 SHA1 或 SHA256 对象，在内部存储和读取元数据中同样会标记为 `FULL_OBJECT`。但在 S3 请求侧，[`getContentChecksum()` 解析器](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/internal/hash/checksum.go#L766)会拒绝为不可合并算法（如 SHA1、SHA256）显式指定 `x-amz-checksum-type: FULL_OBJECT`。

若无条件转发所有已存类型，单次 `PUT` 的 SHA1/SHA256 对象在复制时反而会被接收端拒绝。通过 `isMP && cktype.CanMerge()` 收窄条件后，分片 CRC 请求得以恢复，同时普通单次 `PUT` 与 `COMPOSITE` 上传的既有请求头完全不受影响。

### CopyObject 自动恢复单次 PUT 复制路径 {#copy}

对分片 `FULL_OBJECT` 对象执行服务端 `CopyObject` 后，生成的新对象不再带有 `-n` 分片 ETag（`!objInfo.isMultipart()`），但其底层校验和元数据仍保留分片 `FULL_OBJECT` 标记。由于 `FULL_OBJECT` 摘要本身就是完整对象字节的 CRC，通过单次 `PutObject` 传输到目标端后依然完全有效。

[`putReplicationOpts()` 中原本就包含](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/cmd/bucket-replication.go#L879)针对该场景的路由分支：

```go
if !objInfo.isMultipart() && cs[xhttp.AmzChecksumType] == xhttp.AmzChecksumTypeFullObject {
    isMP = false
}
```

修复前，由于 `getCRCMeta()` 丢掉了 `x-amz-checksum-type`，上述条件永远为假，导致 `CopyObject` 生成的对象被错误路由到单分片 Multipart 复制路径并同样触发 `BadDigest`。在 `getCRCMeta()` 补回类型后，这段既有路由逻辑自动生效：此类对象直接通过单次 `PutObject` 完成复制，无需额外编写 Copy 专用分支或重算校验和。

## 备选方案取舍 {#alternatives}

| 备选方案 | 结论与原因 |
| :-- | :-- |
| 恢复上游变更前的无条件类型转发 | 不采纳：显式携带 `FULL_OBJECT` 的 SHA1/SHA256 请求会被 `getContentChecksum()` 拒绝 |
| 仅在 `CompleteMultipartUpload` 阶段补类型 | 不采纳：目标端在初始化时已持久化为 `COMPOSITE`，完成阶段传入不匹配的类型同样会被拒绝 |
| 将所有 CRC32/CRC32C 分片上传默认改为 `FULL_OBJECT` | 不采纳：破坏合法的 S3 默认 `COMPOSITE` 语义 |
| 忽略对象级校验和或跳过 `BadDigest` 检查 | 不采纳：牺牲复制过程的数据完整性验证 |
| 在发送端重新计算 `COMPOSITE` 摘要以迎合目标端 | 不采纳：篡改了源端对象的校验和类型与摘要值，且引入额外计算开销 |
| 单独编写 `CopyObject` 复制分支或排除 CRC64NVME | 不需要：`putReplicationOpts()` 既有路由分支与 `CanMerge()` 已自然覆盖 |
| 调整复制重试预算、队列或 resync 调度 | 无效：不修复请求头缺失，重试多少次都会发送相同的错误请求 |

## 验证与实机验收 {#validation}

在合入前的基线 [`aafe4f888`](https://github.com/pgsty/silo/commit/aafe4f8886a060ec698400043bee2f60e22140fd) 上运行新增回归测试：`FULL_OBJECT` CRC32/CRC32C 复制稳定复现 `BadDigest`，`CopyObject` 用例在路径选择断言处失败（`got true, want false`）；应用补丁后全部通过。

[入库的单元测试与集成测试](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/cmd/bucket-replication-checksum_test.go)包含 8 个请求头表驱动用例（含逐分片请求头检查）和 8 个双版本桶 API 集成用例，验证复制路径选择与两端校验和元数据一致性。

独立实机验收启动**两个单盘 SILO 服务端实例**，通过 `mcli` 配置站点复制，实测 12 个端到端用例：

| 用例类别 | 算法或变体 | 数量 |
| :-- | :-- | --: |
| 单次 `PUT` | SHA256、SHA1、CRC32 | 3 |
| 分片 `COMPOSITE` | CRC32、CRC32C、SHA256 | 3 |
| 分片 `FULL_OBJECT` | CRC32、CRC32C | 2 |
| 默认 `FULL_OBJECT` 的分片上传 | CRC64NVME | 1 |
| 对分片 `FULL_OBJECT` 对象执行 `CopyObject` | CRC32、CRC32C | 2 |
| 仅含 1 个分片的 `FULL_OBJECT` 上传 | CRC32 | 1 |

全部 12 个用例均达到源端 `COMPLETED`、目标端 `REPLICA`；独立计算的校验和摘要与类型、版本 ID、ETag、对象大小及目标端下载字节均与源端完全一致。

可复现测试命令：

```bash
go test ./cmd -count=1 -v \
  -run '^(TestGetCRCMetaChecksumType|TestReplicateObjectChecksumTypes)$'
go test ./cmd ./internal/hash -count=1 -timeout 10m \
  -run 'Replicat|Checksum|CRC|Multipart'
MINIO_API_REQUESTS_MAX=10000 CGO_ENABLED=0 \
  go test -tags kqueue,dev ./... -count=1 -timeout 30m
```

PR 检查（[Go CI](https://github.com/pgsty/silo/actions/runs/39974825425)、[DCO](https://github.com/pgsty/silo/actions/runs/39974825340)、[VulnCheck](https://github.com/pgsty/silo/actions/runs/39974825530)）与合并提交检查（[Go CI](https://github.com/pgsty/silo/actions/runs/40082832251)、[VulnCheck](https://github.com/pgsty/silo/actions/runs/40082832247)）全部通过。

## 升级与运维要点 {#operations}

- **升级复制源端**：该修复作用于复制发送端构造的请求头。仅升级目标端无法补回被源端丢弃的 `x-amz-checksum-type`；在双向（active-active）复制拓扑中，两端站点均作为发送端，需同时升级。贡献者在 [PR #255](https://github.com/pgsty/silo/pull/255) 中的混合版本测试验证了已修复源端可向未修复 SILO 目标端正常复制，而未修复源端向已修复目标端复制仍会失败。
- **覆盖路径**：桶复制、站点复制与批量复制（[`batchReplicationOpts()`](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/cmd/batch-handlers.go#L1593)）均通过 `putReplicationOpts()` 构造请求头，因此统一获得修复。SSE-C 加密对象继续通过 `X-Minio-Replication-Ssec-Crc` 传递加密校验和元数据。
- **存量 `FAILED` 版本恢复与回滚**：本次修改不涉及配置项、磁盘元数据格式或 API 变更。此前因该问题停留在 `FAILED` 状态的对象版本在源端保有完整的校验和元数据，升级源端后，触发复制重试或 resync 即可完成同步；回滚旧版本不会影响已落盘的目标端副本。

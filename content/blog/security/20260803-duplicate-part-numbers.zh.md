---
title: "CompleteMultipartUpload 重复分片号漏洞分析与修复"
linkTitle: "重复分片号修复"
date: 2026-08-03
author: "[冯若航](https://vonng.com) ([`@Vonng`](https://github.com/Vonng))"
description: "解析 CompleteMultipartUpload 为何会接受升序中的重复分片号、sort.SliceIsSorted 为何漏掉 [1, 1]，以及 Server 20260804 的修复方案。"
url: "/zh/blog/security/duplicate-part-numbers/"
tags: ["S3", "Multipart Upload", "Correctness", "SILO"]
---

在 S3 API 的 `CompleteMultipartUpload` 请求中，协议要求完成清单 XML 中的分片号（`PartNumber`）必须严格递增。直到 Server `20260725` 为止，SILO 一直使用 `sort.SliceIsSorted` 配合严格小于号 `<` 来校验这一不变量——但这套写法实际上校验的是“非递减序”，会放行 `[1, 1]` 这类包含相邻重复分片号的列表，导致同一个底层分片在最终对象中被重复拼接。[Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z)（[`pgsty/silo#49`](https://github.com/pgsty/silo/issues/49)）将其替换为显式的相邻元素比较（`Parts[i-1].PartNumber >= Parts[i].PartNumber`），并顺带修复了突变测试中发现的 `ReadParts` 空切片 panic（`2602177ef`）。

## 结论先行 {#summary}

1. **缺陷真实存在且边界清晰**：`CompleteMultipartUpload` 使用 `sort.SliceIsSorted` 配合 `<` 比较器，实际验证的是非递减序（`a[0] <= a[1] <= ...`）而非严格递增序（`a[0] < a[1] < ...`）。传入 `[1, 1]` 这类重复分片号会返回成功，并在最终对象中将对应分片重复拼接。
2. **属于数据完整性缺陷，而非 CVE 安全漏洞**：触发该行为的前提是调用方已经拥有目标对象的 `s3:PutObject` 权限，并持有正在进行的分段上传的合法 `uploadId`。它不跨越租户、桶或凭据边界。
3. **修复收敛在 HTTP Handler 边界**：`cmd/object-handlers.go` 对满足 `Parts[i-1].PartNumber >= Parts[i].PartNumber` 的输入直接返回 `InvalidPartOrder`（HTTP 400）。跳号分片（如 `[1, 3]`、`[5, 9]`、`[3]`）继续保持合法。

---

## 为什么 `sort.SliceIsSorted` 会放行重复分片号 {#the-defect}

在 `cmd/object-handlers.go` 中，`CompleteMultipartUploadHandler` 原本通过以下代码校验解析后的 `<CompleteMultipartUpload>` 分片列表：

```go
if !sort.SliceIsSorted(complMultipartUpload.Parts, func(i, j int) bool {
    return complMultipartUpload.Parts[i].PartNumber < complMultipartUpload.Parts[j].PartNumber
}) {
    writeErrorResponse(ctx, w, errorCodes.ToAPIErr(ErrInvalidPartOrder), r.URL)
    return
}
```

在 Go 标准库中，`sort.SliceIsSorted` 会将下标 `i` 从 `n-1` 递减遍历到 `1`，并调用 `less(i, i-1)`；只有当 `less(i, i-1)` 返回 `true`（即后一个元素严格小于前一个元素）时，才会判定切片无序。当两个相邻元素的分片号相等（`Parts[i].PartNumber == Parts[i-1].PartNumber`）时，`Parts[i].PartNumber < Parts[i-1].PartNumber` 的结果为 `false`，因此 `SliceIsSorted` 会认为 `[1, 1]` 已经有序。

将 `sort.SliceIsSorted` 替换为显式的相邻元素检查即可消除该盲区：

```go
for i := 1; i < len(complMultipartUpload.Parts); i++ {
    if complMultipartUpload.Parts[i-1].PartNumber >= complMultipartUpload.Parts[i].PartNumber {
        writeErrorResponse(ctx, w, errorCodes.ToAPIErr(ErrInvalidPartOrder), r.URL)
        return
    }
}
```

---

## 两次重构为何都保留了这一缺陷 {#archaeology}

通过 `git log -S` 追溯该处理函数的演进历史可以看到，这一“非递减”判断在九年间的两次代码整理中被原样保留了下来：

| 时间 | PR / 提交 | 变更内容 | 为何 `[1, 1]` 未被发现 |
|---|---|---|---|
| 2016-08 | [`minio/minio#2490`](https://github.com/minio/minio/pull/2490) | 引入 `sort.IsSorted(completedParts(complMultipartUpload.Parts))`，其 `Less(i, j)` 定义为 `a[i].PartNumber < a[j].PartNumber`。 | `sort.IsSorted` 仅检查后一项是否小于前一项。 |
| 2017-11 | [`minio/minio#5170`](https://github.com/minio/minio/pull/5170) | 移除具名类型 `completedParts`，改用 `sort.SliceIsSorted` 与相同的 `<` 闭包。 | 属于比较器逻辑不变的机械重构。 |
| 2023-04 | [`minio/minio#17066`](https://github.com/minio/minio/pull/17066) | 将 `ErrInvalidPartOrder` 校验前移到 `CompleteMultipartUploadHandler` 入口（进入对象层之前）。 | 原样移动了校验代码块，未补充重复分片号用例。 |

现有的单元测试与 mint 测试在验证 `ErrInvalidPartOrder` 时均只构造了 `[2, 1]` 这类逆序输入，从未覆盖 `[1, 1]` 这类相邻重复输入。

---

## 实际影响与复现表现 {#impact}

在修复前，只需上传一个 5 MiB 的分片（`partNumber=1`），并在完成上传时提交两条同样引用 `PartNumber=1` 及其 ETag 的 `<Part>` 记录，即可复现如下行为：

| 步骤 | 请求 | 修复前结果 | 修复后结果 |
|---|---|---|---|
| 1 | `UploadPart(partNumber=1)`（5 MiB） | `200 OK`，返回 `ETag: "e1"` | `200 OK`，返回 `ETag: "e1"` |
| 2 | 使用 `[(1, "e1"), (1, "e1")]` 调用 `CompleteMultipartUpload` | `200 OK`，`ETag: "...-2"` | `400 Bad Request`（`InvalidPartOrder`） |
| 3 | `HeadObject` / `GetObject` | `Content-Length: 10485760`（分片 1 被重复拼接两次） | 对象未创建，分段上传保持打开状态 |
| 4 | 改用 `[(1, "e1")]` 重试 `CompleteMultipartUpload` | `404 NoSuchUpload`（上传状态已被消费并清理） | `200 OK`，`Content-Length: 5242880` |

由于 `CompleteMultipartUpload` 一旦成功就会消费并清理该 `uploadId` 的暂存状态，如果客户端因重试逻辑缺陷（例如重试 `UploadPart` 后直接向内存切片 `append` 而未按分片号去重）在完成清单中混入了重复分片，服务端不仅会静默生成一个长度错误的损坏对象，而且客户端也无法再对该 `uploadId` 重新发起正确的 `CompleteMultipartUpload`，只能重传所有分片。

---

## 为什么不分配 CVE {#not-a-cve}

我们评估了恶意调用方能否利用重复分片号制造存储空间放大攻击：

1. **无直接物理落盘放大**：在纠删码存储层，`CompleteMultipartUpload` 只是在 `xl.meta` 的分片元数据数组中记录条目并指向磁盘上已有的 `part.1` 数据文件，不会在完成阶段按条目复制底层数据块。虽然读取该对象会流式读取两次 `part.1`，且后续后台修复（healing）或复制会按逻辑大小物化数据，但拥有写权限的调用方本就可以通过正常上传两个分片或调用 `UploadPartCopy` 达到同样的效果。
2. **仅限调用方自身权限范围**：调用 `CompleteMultipartUpload` 必须具备目标对象的写权限并知晓 `uploadId`，未认证用户或只读凭据无法触发该路径。

因此，我们将该问题归类为数据正确性与 S3 协议合规性缺陷（`#49`），而非安全公告（`SN-2026-*`）。

---

## Handler 层与对象层的职责边界 {#boundary}

排查过程中，我们同步检查了 `erasureObjects.CompleteMultipartUpload`（`cmd/erasure-multipart.go`）是否包含分片顺序校验。答案是没有：对象层直接遍历 `for i, part := range parts` 并与该 `uploadID` 的分片元数据逐项比对。

我们最终选择将严格递增校验保留在 `CompleteMultipartUploadHandler`（`cmd/object-handlers.go`），而不是在每个 `ObjectLayer` 实现中重复植入，原因有两点：

1. **单一不可信入口**：由客户端控制的完成清单只会从 `CompleteMultipartUploadHandler` 进入。系统内部调用方（如 `batch-replicate`、`restore`、`decommission`、`rebalance` 等）均直接基于已持久化的 `ObjectInfo.Parts` 或按 `1..n` 顺序循环构造分片列表。
2. **在获取命名空间锁之前快速失败**：在 HTTP Handler 层直接拒绝畸形 XML，可以避免无谓地获取对象命名空间锁或读取磁盘上的上传元数据。

---

## 保持稀疏分片号的合法性 {#no-extra-constraints}

S3 规范只要求 `CompleteMultipartUpload` 中的分片号严格递增（`1 <= PartNumber <= 10,000`），**并不要求**分片号连续，也**不要求**必须从 `1` 开始。客户端上传分片 `1`、`2`、`3` 后仅用 `[1, 3]` 完成上传，或者直接用 `[5, 9]`、`[3]` 完成上传，均属于合法的 S3 用法。

为确保修复不会误伤合法客户端，我们在回归测试中显式固定了以下用例：
- `[1, 3]`（跳号间隙，合法通过）；
- `[3]`（不从 `1` 开始的单分片，合法通过）；
- `[1, 1]` 与 `[1, 2, 2, 3]`（相邻重复，返回 `ErrInvalidPartOrder`）；
- `[1, 3, 2]` 与 `[2, 1]`（递减顺序，返回 `ErrInvalidPartOrder`）；
- `[1, 2, 1]`（非相邻重复，返回 `ErrInvalidPartOrder`）。

---

## 越界且重复分片号的错误码优先级 {#error-code}

一个值得记录的边界情形是：当输入**同时**违反分片号范围（`PartNumber < 1`）和严格递增要求时，例如 `[0, 0]` 或 `[-1, -1]`，应当返回哪个错误码？

由于 `CompleteMultipartUploadHandler` 先在入口校验分片顺序，随后才进入对象层逐个查找分片（并在分片不存在或越界时返回 `ErrInvalidPart`），修复前 `[0, 0]` 会通过 `sort.SliceIsSorted` 并在对象层返回 `InvalidPart`（HTTP 400）。改为严格递增校验后，`[0, 0]` 与 `[-1, -1]` 会在 Handler 入口直接被拦截并返回 `InvalidPartOrder`（HTTP 400）。这两个错误码均对应 HTTP `400 Bad Request` 且均不可重试；单个越界分片（如 `[0]` 或 `[-1]`）则依然会进入分片查找流程并返回 `InvalidPart`。

---

## 突变测试与一条误导性注释 {#mutations}

在验证 `cmd/object-handlers-multipart_test.go` 的单元测试时，我们对 Handler 做了两项手工突变实验（Mutation Testing）：

1. **植入“必须从分片 1 开始”的限制（要求 `Parts[0].PartNumber == 1`）**：立即被稀疏分片回归测试（`[3]` 与 `[5, 9]`）捕获。
2. **删掉 `len(complMultipartUpload.Parts) == 0` 空列表守卫**：起初我们在测试注释中写道“如果删掉该守卫，空分片完成请求将会成功”。然而实际运行该突变后发现，空 `Parts` 切片穿过 Handler 进入对象层后，会在 `errgroup` 协程调用的 `ReadParts`（`cmd/storage-rest-client.go`）中因为直接访问 `partNumbers[0]` 而触发数组越界 panic。

这次突变实验带来了两个直接收获：我们修正了测试文件中原本凭推理想象出来的误导性注释，并在提交 `2602177ef`（同样随 [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) 发布）中加固了 `ReadParts`，使其在收到空 `partNumbers` 切片时直接安全返回，消除了该处隐患。

---

## 明确不做项与后续边界 {#declined}

- **不提供存量对象自动改写工具**：在 `20260804` 之前由重复分片清单拼接出的对象，其 `xl.meta` 元数据与逻辑大小自洽；盲目对存量对象做自动截断或去重，反而可能破坏业务侧有意拼接相同数据块的合法对象。
- **不在对象层重复植入顺序校验**：如[职责边界](#boundary)所述，内部调用方均从已验证元数据构造分片列表，而突变测试暴露的 `ReadParts` 空切片边界已在 `2602177ef` 中闭环。

## 审查记录 {#review}

三轮独立审查依次验证了 Handler 递增谓词、错误码优先级（`InvalidPartOrder` 与 `InvalidPart`）、稀疏分片号兼容性（`[3]` 与 `[5, 9]`）以及 `ReadParts` 空切片守卫（`2602177ef`）。

## 总结 {#closing}

随 [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z)（`5df7b5466` 与 `2602177ef`）发布后，`CompleteMultipartUploadHandler` 严格校验分片号单调递增（`PartNumber[i-1] < PartNumber[i]`），同时 `ReadParts` 对空分片切片执行安全早退保护。

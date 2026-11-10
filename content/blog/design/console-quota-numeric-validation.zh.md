---
title: "Console 的桶配额：列表显示与数值校验"
linkTitle: "Console 配额校验"
date: 2026-11-04
lastmod: 2026-11-10
author: "PGSTY SILO 维护团队"
summary: >
  解释为什么在 Web Console 里设置的配额在桶列表中显示为短横线，为什么创建桶的表单会把 1000 Ei 变成 1 字节配额、又拒绝 0.5 Gi，两个缺陷分别出现在哪些发布中，以及为什么共用一个配额读取规则和一套换算与边界检查，是最小而完整的修复。
tags: [Design, Console, Quota, Retention]
weight: 10
draft: false
url: "/zh/blog/design/console-quota-numeric-validation/"
---

本文覆盖 [silo-console#72](https://github.com/pgsty/silo-console/issues/72)（在 Web Console 中设置的配额在桶列表里显示为短横线）和 [silo-console#73](https://github.com/pgsty/silo-console/issues/73)（创建桶表单的数值校验）。评估基于修复之前的 Console 源码 [3d264aea9](https://github.com/pgsty/silo-console/commit/3d264aea9b67aa40baf706f3e13c8d4145671ea1)，以及修复提交 [a85665814](https://github.com/pgsty/silo-console/commit/a85665814ff74d8a9d0cbd42a51f518c79c9a227) 至 [5a34232e7](https://github.com/pgsty/silo-console/commit/5a34232e72162274d621c57342c75c06fc35befd)。

**状态：** [PR #74](https://github.com/pgsty/silo-console/pull/74)（[`3d1dd56eb`](https://github.com/pgsty/silo-console/commit/3d1dd56ebaacf219191ed92d351a27bddd653838)，2026-11-04）已随独立版 [Console 2.6.0](/zh/blog/release/console-2.6.0/)（[`f8ab14669`](https://github.com/pgsty/silo-console/commit/f8ab146695fd1df74e4b84128a286d552921bf00)）发布。PR `#74` 及全部数值后续修复（[#75](https://github.com/pgsty/silo-console/issues/75) [`2b18ff854`](https://github.com/pgsty/silo-console/commit/2b18ff854f81b08080094f0f3231f6b249c64d49)、[#76](https://github.com/pgsty/silo-console/issues/76) [`4da296098`](https://github.com/pgsty/silo-console/commit/4da296098) 与 [PR #79](https://github.com/pgsty/silo-console/pull/79)）已随独立版 [Console 2.7.0](/zh/blog/release/console-2.7.0/)（[`4e91ae506e70`](https://github.com/pgsty/silo-console/commit/4e91ae506e706ccdecb512b1d8b5ab4d9871d505)）发布，并内嵌于 [SILO Server 20261109](/zh/blog/release/silo-20261109/)（`d998292387cc`）。

## 简短结论 {#tldr}

两份报告都属实，且都不影响已存储的数据或配额的执行。

- **#72 是显示缺陷。** 自 Console 开始写入新的 `Size` 字段（2025-09-16）起，在 Web Console 中设置的配额以 `size` 存储，旧的 `quota` 字段为零。桶列表处理程序和列表界面只读 `quota`，所以什么都不显示。服务器对配额的执行是正确的。
- **#73 是输入校验缺陷，其中有一种情形会影响写入。** `parseInt(getBytes(...))` 会把 868 Ei 及以上的任何数量变成 1 字节配额；服务器接受并执行它，该桶随后拒绝所有非空写入。其余情形是误拒绝或缺少检查：`0.5 Gi` 被拒绝，切换单位不会重新校验，保留期有效值既不检查是否为整数，也没有限制在 32 位范围内。

两个缺陷都不是 SILO 引入的。#72 来自 SILO 所派生的社区 Console 分支：它的配额写入端在 2025-09-16 改变了，列表读取端没有跟着改。#73 是 2020 至 2022 年间 minio/console 的原有代码。SILO 在下文列出的所有内嵌 Console 的发布中都带着这两个缺陷，而且 Console v2.5.0 的列表改版保留了过时的读取方式。

修复很小：桶列表与 Summary 使用同一个配额读取函数，创建与编辑表单共用同一套换算与边界检查。

## 定性 {#assessment}

| 方面       | 评估                                                                                                                                                                       |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 性质       | #72：Console 写入端的表示方式改变，留下了一个没改的读取端。#73：早于派生点的输入校验问题。两者都是继承而来，不是 SILO 的回归。                                             |
| 受影响组件 | 仅 Web Console：`api/user_buckets.go`、桶列表界面，以及创建桶和编辑配额的表单。服务器、`madmin-go` 和 `mcli` 没有缺陷。                                                    |
| #72 影响   | 仅显示。配额已被正确存储和执行，Summary 与 `mcli` 显示正确。列表显示短横线（Console v2.5.x）或不显示配额（v2.0.0 至 v2.4.2）。                                             |
| #73 影响   | 一种影响写入的情形：868 Ei 及以上会变成 1 字节硬配额，阻止任何非空对象的写入。8 Ei 至 867 Ei 超出有符号 64 位范围，会被 API 拒绝。其余情形是误拒绝或缺少检查。             |
| 严重度     | #72 低。#73 低到中：触发损害需要刻意输入至少 868 Ei，但后果是桶悄悄拒绝写入。无数据丢失，无安全影响。                                                                      |
| 受影响发布 | 见[行为的来源](#history)。#72：社区 v1.9.0 至 SILO Console v2.5.1；SILO Server 20260314 至 20261026。#73：截至 v2.5.1 的 Console 发布及截至 20261026 的 SILO Server 发布。 |
| 发布紧迫度 | 已随独立版 Console 2.6.0、Console 2.7.0 发布，并内嵌于 SILO Server 20261109。不是数据安全的阻断项。                                                                        |
| 剩余工作量 | 已完成；独立版 Console 2.6.0/2.7.0 与内嵌更新的 SILO Server 20261109 均已正式发布。                                                                                        |
{.wide .expand}

## 何时发生 {#trigger}

**#72。** 创建一个桶，用 `mcli quota set` 设置配额，它写入旧的 `quota` 字段，列表可以显示。在 Console 中打开该桶，修改配额并保存。Console 写入 `size`，服务器存储的配置中 `quota` 为零。此时管理 API 对 110 GiB 配额返回 `size=118111600640, quota=0`。Summary 页面优先使用 `size`，显示 110 GiB；列表读取 `quota`，显示短横线。在创建表单中设置的配额同样如此。

**#73。** 打开启用配额的创建桶表单。

1. 输入 `1000` 并选择 `Ei`。表单把它换算成字符串 `1.152921504606847e+21`，`parseInt` 在 `e` 处停止并返回 `1`，请求携带 `amount: 1`。
2. 输入 `0.5` 并选择 `Gi`。`parseInt("0.5")` 为 `0`，所以表单把字段标记为无效，尽管输入模式允许两位小数。
3. 输入 `1000` 和 `Gi`，然后把单位改为 `Ei`。切换单位不会重新校验，先前的有效状态保留，无需再次输入就能走到情形 1。
4. 启用保留期并输入 `1.5` 或 `3000000000`。输入通过 `valueAsNumber` 读取，唯一的检查是 `NaN` 或小于 1，而 API 模型是有符号 32 位整数。

已有桶的配额编辑器使用同样的 `parseInt(getBytes(...))` 换算；保留期编辑器同样缺少整数与上界检查。

## 根因 {#root-cause}

**#72。** 在修复之前的源码中，桶列表响应由 `getAccountBuckets`（`api/user_buckets.go` 第 409 至 414 行）构造，它复制 `bucket.Details.Quota.Quota`，忽略 `Size`。列表界面随后只渲染 `details.quota.quota`：v2.5.x 中是 `BucketsTable.tsx` 第 387 至 390 行，更早的版本是 `BucketListItem.tsx` 第 144 行。而单个桶的配额处理函数 `getBucketQuota`（`api/user_bucket_quota.go` 第 118 至 125 行）已经优先使用正的 `Size`，否则回退到 `Quota`。对同一份配置，两个读取方使用了两套规则。

服务器没有改变表示方式。它按客户端写入的内容存储和返回配置，执行时先看 `Size` 再看 `Quota`（`cmd/bucket-quota.go` 中的 `getBucketQuotaSize`；上游 MinIO 的最后一个 master 也是同样的优先顺序）。`madmin-go` 的结构自 2023 年 8 月起就把 `Quota` 标为已弃用，并带有 `Size`。`mcli quota set` 仍然写旧的 `Quota` 字段，所以命令行设置的配额在列表中显示正常。

**#73。** 创建表单有四个相互独立的缺口：

- `addBucketThunks.ts` 第 80 行发送 `parseInt(getBytes(quotaSize, quotaUnit, true))`。`getBytes` 把数字转成字符串返回，而 JavaScript 对 1e21 及以上的数字使用指数形式。
- `addBucketsSlice.ts` 第 122 行在 `parseInt(state.quotaSize) === 0` 时拒绝该字段。下一行的输入模式后来放宽到允许两位小数，`parseInt` 检查却保留了下来。
- `setQuotaUnit`（第 133 行）只保存单位，不触及 `invalidFields`。
- `setRetentionValidity`（第 170 至 183 行）和 `SetRetentionConfig.tsx`（第 87 行）只检查 `NaN` 和 `< 1`。

在服务器端，配额请求接受任何非负数量并存为 `Size`。存储的大小为 1 时，`enforceQuotaHard` 会拒绝所有一字节及以上的写入（`uint64(size) >= quotaSize`，`cmd/bucket-quota.go`）。

## 行为的来源 {#history}

溯源依据 Console 的提交历史。上游项目 `minio/console` 如今已无法公开访问。SILO Console 所派生的社区延续项目 [georgmangold/console](https://github.com/georgmangold/console) 仍然可以访问。`pgsty/silo-console` 的 `main` 派生自它的提交 [feff71e48](https://github.com/pgsty/silo-console/commit/feff71e48e39547834399a84a9460edb4fb50563)（2026-04-16），这就是派生点。下列提交都在 `pgsty/silo-console` 的 `main` 上；PR 编号指提交原本所在的仓库。派生点之前的 Console 发布标签中，只能取得社区的 v1.7.7 及之后的标签，所以更早的提交不给出 minio/console 的首个发布标签。

### #72：写入端改变后被遗留的读取端 {#reader-left-behind}

| 要素                                                                  | 提交                                                                                                                                                                                                                                                         | 来源                          | 日期       | 首个发布                                  |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------- | ---------- | ----------------------------------------- |
| 列表处理程序只复制 `Quota`                                            | [64e38ca8d](https://github.com/pgsty/silo-console/commit/64e38ca8d3) “List buckets re-design”（minio/console #1058），`api/user_buckets.go`                                                                                                                  | 上游                          | 2021-09-20 | 标签无法取得；此后每个发布都有            |
| 列表界面只读 `details.quota.quota`                                    | [10539929e](https://github.com/pgsty/silo-console/commit/10539929e1) “Added quota metric to buckets list & objects list”（minio/console #1595），`BucketListItem.tsx`                                                                                        | 上游                          | 2022-02-16 | 标签无法取得；此后每个发布都有            |
| **Console 写入端改为 `Size`；Summary 读取端同步更新，列表读取端没有** | [6c54a55d5](https://github.com/pgsty/silo-console/commit/6c54a55d5285986eeeb4df00544f1aaa8c8db05d) “use Quota Size field instead of the deprecated Quota field”（[georgmangold/console#28](https://github.com/georgmangold/console/pull/28)，Georg Mangold） | 派生点之前的社区 Console 分支 | 2025-09-16 | georgmangold/console v1.9.0（2025-11-16） |
| 列表改为表格；配额列沿用过时的读取方式，为零时显示短横线              | [2611a4d11](https://github.com/pgsty/silo-console/commit/2611a4d11a9e22282847bfa5b8b239a84b4b5d77) “modernize buckets, object browser, safe previews, and task center”（Feng Ruohang）                                                                       | SILO                          | 2026-10-25 | Console v2.5.0（2026-10-25）              |
{.wide .expand}

缺陷需要倒数第二行：2025-09-16 之前 Console 写的是旧字段，列表能读到。[6c54a55d5](https://github.com/pgsty/silo-console/commit/6c54a55d5285986eeeb4df00544f1aaa8c8db05d) 就是表示方式的改变，它只更新了两个读取端中的一个。这不是服务器或 `madmin-go` 的改动：`madmin-go` 自 2023 年 8 月起就同时带有两个字段，服务器对它们的存储与执行也没有因此改变。SILO 没有引入这个缺陷。

**SILO 改了什么。** 从派生点到修复之间，没有 SILO 提交改动列表处理程序或配额写入端。SILO 的 Web 改版（[23ae6e8e6](https://github.com/pgsty/silo-console/commit/23ae6e8e6)，Console v2.0.0）和 [2611a4d11](https://github.com/pgsty/silo-console/commit/2611a4d11a9e22282847bfa5b8b239a84b4b5d77) 的列表重建重写了列表界面，并沿用了旧的读取方式。v2.0.0 至 v2.4.2 的列表只是不显示配额；v2.5.0 和 v2.5.1 的新表格列显示短横线，读起来像“没有配额”，使缺陷明显到被人报告。这个改动放大了可见症状，没有改变原因。

**包含该缺陷的 Console 发布。** 写入端的改变和过时的读取端同时存在于 georgmangold/console v1.9.0 与 v1.9.1，以及 SILO 的每个 Console 标签，v2.0.0 至 v2.5.1。SILO 的首个 Console 标签是 v2.0.0（2026-08-04）。写旧字段的 Console 发布，直到 minio/console v1.7.6 和社区 v1.8.1，都没有这个缺陷。

**各 SILO Server 发布内嵌的 Console 状态**（取自 Server `go.mod` 中 `replace github.com/minio/console` 一行）：

| Server 发布                                      | 内嵌的 Console                      | 是否有缺陷           |
| ------------------------------------------------ | ----------------------------------- | -------------------- |
| 20251203、20260214                               | minio/console v1.7.x，写旧字段      | 否                   |
| 20260314、20260321、20260325、20260417、20260618 | georgmangold/console v1.9.1         | 是（列表不显示配额） |
| 20260804、20260806                               | SILO Console v2.0.0、v2.1.x         | 是（不显示）         |
| 20260903                                         | Console v2.3.0 与 v2.4.0 之间的构建 | 是（不显示）         |
| 20260916、20261015                               | Console v2.4.1                      | 是（不显示）         |
| 20261018                                         | Console v2.4.2                      | 是（不显示）         |
| 20261025、20261026                               | Console v2.5.0、v2.5.1              | 是（短横线）         |
| 20261109                                         | Console v2.7.0                      | 否                   |
{.wide .expand}

[SILO Server 20261109](/zh/blog/release/silo-20261109/)（`d998292387cc`）内嵌 [Console 2.7.0](/zh/blog/release/console-2.7.0/)（[`4e91ae506e70`](https://github.com/pgsty/silo-console/commit/4e91ae506e706ccdecb512b1d8b5ab4d9871d505)），在内嵌界面中一并修复了这两个缺陷（取代了此前 `main` 分支 [`e24831f53`](https://github.com/pgsty/silo/commit/e24831f53) 中的 `v2.6.0` 中间升级）。Server 标签 20260304、20260323 和 20260330 内嵌的是写入端改变之前的 Console 构建，不受影响。

### #73：minio/console 的原有代码 {#original-code}

| 要素                                                                              | 提交                                                                                                                                         | 来源 | 日期       | 说明                                                                                 |
| --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---------- | ------------------------------------------------------------------------------------ |
| 创建请求中的 `parseInt(getBytes(...))`                                            | [28eb8784a](https://github.com/pgsty/silo-console/commit/28eb8784a) “Set Bucket Quota on Creation”（minio/console #308）                     | 上游 | 2020-10-01 | `getBytes` 返回 `Number.toString(10)`；从 1e21 起出现指数形式                        |
| 字段检查 `parseInt(quotaSize) === 0`、切换单位不重新校验、保留期 `NaN`/`< 1` 检查 | [41e1b4a5d](https://github.com/pgsty/silo-console/commit/41e1b4a5d) “Add Bucket slice refactor to reduce re-renders”（minio/console #2087）  | 上游 | 2022-06-03 | 把表单逻辑移入 `addBucketsSlice.ts`；这些检查此前已存在于 `AddBucket.tsx`            |
| 输入模式加入小数，`parseInt` 检查保留                                             | [7ecc1022b](https://github.com/pgsty/silo-console/commit/7ecc1022b) “Added decimal support to bucket quota selectors”（minio/console #2126） | 上游 | 2022-06-15 | 使 `0.5` 通过输入模式、却被 `parseInt` 检查拒绝；上游 “Release v0.19.0” 提交紧随其后 |
{.wide .expand}

这些都在社区分支和 `feff71e48` 中。修复之前触及相同文件的 SILO 提交（[23ae6e8e6](https://github.com/pgsty/silo-console/commit/23ae6e8e6)、[14b1c2de2](https://github.com/pgsty/silo-console/commit/14b1c2de2)、[2611a4d11](https://github.com/pgsty/silo-console/commit/2611a4d11a9e22282847bfa5b8b239a84b4b5d77)）改的是链接目标、翻译和命令预览，没有改动校验或换算。SILO 既没有引入也没有放大 #73。它存在于每个 Console 发布，因而存在于每个内嵌 Console 的 SILO Server 发布。

仅凭推理、未执行：`main` 一线的历史。2020 至 2022 年这些提交对应的 minio/console 首个发布标签无法取得，所以只给出提交主题和日期。

## 方案选项 {#options}

### 选项 1：列表和详情共用一个配额读取函数 {#option-1}

把“先 `Size` 后 `Quota`”的规则放进一个函数，列表处理程序和 `getBucketQuota` 都调用它。两个读取方始终一致，API 模式不变。

### 选项 2：让写入端同时发送两个字段 {#option-2}

同时写 `Quota` 和 `Size` 能让旧读取端重新工作，但会为一个使用方重新引入已弃用字段，而其他工具写入的配额仍会让列表出错。否决。

### 选项 3：让界面也读取 `size` {#option-3}

列表响应模型只有 `quota`。让浏览器再读一个字段，会把规则复制到第三处。否决。

### 选项 4：用一个函数校验数量，到处使用 {#option-4}

一个函数把文本数量和单位换算成字节数，并拒绝 `1` 到 `2^63 - 1` 之外的值。创建表单、配额编辑器和 thunk 都调用它，切换单位时重新校验。保留期增加整数和 `1..2147483647` 的检查。

### 选项 5：交给服务器拒绝 {#option-5}

服务器接受任何非负的 `Size`，包括 1。这个错误值本身是合法配置，服务器无法区分它与有意设置。不能只靠它，保留作为负数的后备防线。

## 建议的修复 {#fix}

选项 1 加选项 4，在分支的六个提交中（都在 PR #74 内）：

1. [a85665814](https://github.com/pgsty/silo-console/commit/a85665814ff74d8a9d0cbd42a51f518c79c9a227) 提取 `bucketQuotaSize`，并同时用于列表处理程序和 `getBucketQuota`：正的 `Size` 优先，否则用 `Quota`。处理程序的 JSON 测试覆盖现代、旧式、冲突、空、零和 nil 值。配额写入与模式不变。
2. [35cf4aae7](https://github.com/pgsty/silo-console/commit/35cf4aae7f7cea46e99c95400894b0dc21c664f0) 让配额编辑器保留精确的字节值，未变化时跳过保存，换算前先校验，并在 API 端拒绝负数。
3. [fb2c9e71c](https://github.com/pgsty/silo-console/commit/fb2c9e71c) 完整解析字节值并限制显示单位，大数字在显示时不再出现指数形式。
4. [d878dbf88](https://github.com/pgsty/silo-console/commit/d878dbf88) 新增 `addBucketValidation.ts`，包含 `getQuotaBytes` 和 `isValidQuota`。数量必须符合两位小数的模式，换算为大于零且小于 `2^63` 的有限整数，切换单位时重新校验。创建 thunk 在发送前再检查一次。
5. [9fb0b0627](https://github.com/pgsty/silo-console/commit/9fb0b0627) 与 [5a34232e7](https://github.com/pgsty/silo-console/commit/5a34232e72162274d621c57342c75c06fc35befd) 要求保留期有效值在创建表单、其 thunk 和保留期编辑器中都是 1 到 2147483647 的整数。前者还让 API 拒绝小于等于零的保留期有效值。
{.steps}

分支上还有两个无关的显示提交（API 请求图表与 syscall 速率标签），不属于这两个问题。

**PR #74 之后的后续修复（已随 Console 2.6.0、Console 2.7.0 与 SILO Server 20261109 发布）。** 它们在 PR #74 分支之外继续收敛同一处代码：

- [2b18ff854](https://github.com/pgsty/silo-console/commit/2b18ff854f81b08080094f0f3231f6b249c64d49)（#75）用整数运算缩放小数配额，并拒绝浏览器写入 8 PiB 及以上的值，因此不会再发送不精确的值。
- [4da296098](https://github.com/pgsty/silo-console/commit/4da296098)（#76）把其余 `calculateBytes` 与显示路径改用同一个有界解析器。
- [9107a8281](https://github.com/pgsty/silo-console/commit/9107a8281)（#77、#78，经 [PR #79](https://github.com/pgsty/silo-console/pull/79) 合入）在创建桶之前校验配额和保留期。此前 `makeBucket` 容忍配额调用失败并返回成功，所以桶可能在没有所请求配额的情况下被创建。

## 为什么充分且必要 {#sufficiency}

**对 #72 充分。** 列表处理程序和单桶处理程序现在调用同一个函数，所以两个字段的任何组合下它们都一致，包括 `mcli` 写入的旧式配额和 Console 写入的新式配额。界面读取处理程序返回的 `quota` 值，无需改动。

**对 #73 充分。** 所有把文本变成配额数量的路径现在都经过同一个有界换算：`0.5 Gi` 变成 536870912，868 Ei 及以上在变成 1 之前就被拒绝，切换单位会重新校验。保留期检查封住了两个表单中小数和超范围的情形。thunk 检查防止过期的表单状态。

**必要。** 没有共用的读取函数，列表响应的任何新使用方都会重犯同样的错误。没有在换算前校验，对数字字符串使用 `parseInt` 对任何大值都不安全。

**刻意不包含。** 以下内容不在本记录的修复之内：

- 任意 64 位精度：在 PR #74 分支上，小数数量经由 JavaScript 数字换算，所以 `7 Ei` 这样的值会以 8070450532247929000 发送，而不是 8070450532247928832。该项由 [silo-console#75](https://github.com/pgsty/silo-console/issues/75) 跟踪，并在 Console 2.6.0/2.7.0（[2b18ff854](https://github.com/pgsty/silo-console/commit/2b18ff854f81b08080094f0f3231f6b249c64d49)）中通过拒绝浏览器写入 8 PiB 及以上配额解决；
- 其余的 `calculateBytes` 用法，由 [silo-console#76](https://github.com/pgsty/silo-console/issues/76) 跟踪，并在 Console 2.6.0/2.7.0（[4da296098](https://github.com/pgsty/silo-console/commit/4da296098)）中收敛；
- 三个复制带宽表单，换算模式相同，在 PR #74 中由单独的提交（[facbf3bab](https://github.com/pgsty/silo-console/commit/facbf3bab)）修复；
- 服务器：配额的存储、执行和管理 API 都不改。

## 成本与兼容性 {#cost}

- 不改 API 模式、服务器或 `madmin-go`。列表响应保留字段名 `quota`，只是它携带的值现在是有效配额。
- 服务器上已有的配额，无论旧式还是新式，都不变。旧式配额照旧显示；原先被隐藏的新式配额现在显示。
- 以前被接受、现在被拒绝的输入是 868 Ei 及以上的数量（原本等于 1 字节）以及非整数或超范围的保留期。以前被拒绝、现在被接受的是小于一的小数，如 `0.5 Gi`。
- 已经用 1 字节配额创建的桶保持原样，见[剩余限制](#limits)。
- 回滚到旧版 Console 即恢复旧行为，无需迁移。

## 剩余限制 {#limits}

- **已被设成 1 字节配额的桶仍然被阻止写入。** 用 `mcli quota info ALIAS/BUCKET` 查找（大小为 1 字节即是迹象），然后设置期望的配额，或用 `mcli quota clear ALIAS/BUCKET` 清除。
- **旧版 Server 发布仍保留内嵌缺陷。** 独立版 [Console 2.6.0](/zh/blog/release/console-2.6.0/)、[Console 2.7.0](/zh/blog/release/console-2.7.0/)（`4e91ae506e70`）以及 [SILO Server 20261109](/zh/blog/release/silo-20261109/)（`d998292387cc`）已包含全部修复；`20260314` 至 `20261026` 的 SILO Server 发布内嵌的 Console 界面仍有这两个缺陷。
- **大配额仍用 `mcli`。** 在 Console `2.6.0` 与 `2.7.0`（以及内嵌于 `SILO Server 20261109` 的界面）中，浏览器拒绝写入 8 PiB（`2^53` 字节）及以上的配额，因为 JSON 数字只在此范围内是精确的（[#75](https://github.com/pgsty/silo-console/issues/75)，由 [2b18ff854](https://github.com/pgsty/silo-console/commit/2b18ff854f81b08080094f0f3231f6b249c64d49) 关闭）。最初的 PR #74 分支顶端曾通过 JavaScript 数字允许到 `2^63`。
- **窄屏。** 现有的响应式布局在 1200 px 以下隐藏桶列表的配额列；Summary 仍显示配额。

## 验证 {#verification}

在 Console 仓库中，对修复分支顶端 [5a34232e7](https://github.com/pgsty/silo-console/commit/5a34232e72162274d621c57342c75c06fc35befd) 实际执行：

- **Playwright unit 项目。** `e2e/bucket-quota.unit.ts`、`e2e/bucket-retention.unit.ts`、`e2e/add-bucket-numeric.unit.ts` 和 `e2e/size-format.unit.ts`：49 个测试全部通过。覆盖 `1000 Ei` 与 `8 Ei` 被拒绝、`0.5 Gi` 写成 536870912 字节、切换单位会重新校验、未变化的配额不写入，以及保留期边界。
- **Go 测试。** `go test -mod=readonly ./api -run 'Quota|Retention|AccountBuckets|ListBuckets'` 通过（现代、旧式、冲突、空、零和 nil 配额的列表与详情响应）。
- **换算缺陷本身。** 对修复前公式的一个小脚本给出：`1000 Ei` 为 `"1.152921504606847e+21"`，其 `parseInt` 为 `1`；`867 Ei` 是 `999582944494136300000`，`868 Ei` 是指数形式，所以 1 字节的情形从 868 Ei 开始。`parseInt("0.5") === 0` 为真。
- **合并后的结果（来自报告，此处未重跑）。** issue 讨论报告合并后的改动在真实的 SILO、`mcli` 与 Console 环境中验证过（用 `mcli` 设置 100 GiB，在 Console 中改为 110 GiB，列表、详情与 `mcli` 一致为 118111600640 字节；创建时的 0.5 GiB 配额恰好存为 536870912 字节）。

仅凭代码推理、此处未执行：

- 服务器对 1 字节 `Size` 的执行（`cmd/bucket-quota.go`）；
- API 对 8 Ei 至 867 Ei 的超范围数量的拒绝，以及 32 位模型对小数或超范围保留期的拒绝；
- `SILO Server 20261109` 之前各 Server 发布内嵌受影响 Console 构建的范围，依据 `go.mod` 历史；
- 派生点之前的历史，依据提交主题和日期。

## 参考 {#references}

- Issue：[silo-console#72](https://github.com/pgsty/silo-console/issues/72)、[silo-console#73](https://github.com/pgsty/silo-console/issues/73)
- 修复：[PR #74](https://github.com/pgsty/silo-console/pull/74)，合并提交 [3d1dd56eb](https://github.com/pgsty/silo-console/commit/3d1dd56ebaacf219191ed92d351a27bddd653838)
- 写入端改动：[georgmangold/console#28](https://github.com/georgmangold/console/pull/28)
- 后续修复（已随 Console 2.6.0、Console 2.7.0 与 SILO Server 20261109 发布）：[silo-console#75](https://github.com/pgsty/silo-console/issues/75)（64 位精度，[2b18ff854](https://github.com/pgsty/silo-console/commit/2b18ff854f81b08080094f0f3231f6b249c64d49)）、[silo-console#76](https://github.com/pgsty/silo-console/issues/76)（`calculateBytes`，[4da296098](https://github.com/pgsty/silo-console/commit/4da296098)）、[PR #79](https://github.com/pgsty/silo-console/pull/79)（创建时校验）
- 发布页面：[SILO 20261109](/zh/blog/release/silo-20261109/)、[Console 2.7.0](/zh/blog/release/console-2.7.0/)、[Console 2.6.0](/zh/blog/release/console-2.6.0/)、[Console 2.5.1](/zh/blog/release/console-2.5.1/)、[SILO 20261026](/zh/blog/release/silo-20261026/)

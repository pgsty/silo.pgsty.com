---
title: "条件 DELETE：一个条件对应一个逻辑对象"
linkTitle: "条件 DELETE"
date: 2026-08-26
lastmod: 2026-09-16
author: "冯若航"
summary: >
  单对象 If-Match DELETE 在外层跨池共享锁内针对选中的逻辑版本只执行一次条件判断。批量 DeleteObjects 的 ETag、额外 GetObject 授权与递归前缀条件保护不在本契约范围内。
tags: [设计, S3, 兼容性, DELETE]
weight: 10
draft: false
url: "/zh/blog/design/conditional-delete/"
---

单对象条件删除（`DeleteObject` 上的 `If-Match`）由 [PR #145](https://github.com/pgsty/silo/pull/145) 引入，随后 [PR #178](https://github.com/pgsty/silo/pull/178) 修复了多池串行化与跨池清理。这两项改动均已随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布。

八月围绕 [PR #12](https://github.com/pgsty/silo/pull/12) 的早期方案曾设想更宽的范围——包括批量 `DeleteObjects` 拒绝保护、额外的 `s3:GetObject` 读取授权检查，以及“仅比较当前版本”规则——但实际合入的实现并未采纳这些扩展。本文记录 [`f99ed829b`](https://github.com/pgsty/silo/tree/f99ed829b5eba549160725f035156c9e020b6a07) 中已交付的契约，并阐述为什么前置条件判断必须位于单池存储层之上。

## 已实现的契约 {#tldr}

| 请求 | 已交付行为 |
| --- | --- |
| 单个 `DeleteObject`，非空 `If-Match: <ETag>` | 在外层删除锁内比较客户端可见 ETag；不匹配时先返回 `412 PreconditionFailed`，不执行任何删除 |
| `If-Match: *` | 要求选中的对象表示存在且不是删除标记（Delete Marker） |
| 显式 `versionId` | 比较**所指定的版本**，而非无关的当前版本 |
| 未携带 `If-Match` 或请求头值为空 | 不安装条件回调，按普通删除处理 |
| 批量 `DeleteObjects` 的逐项 `<ETag>` | `ObjectToDelete` 结构体无 ETag 字段，该 XML 元素**不提供删除保护** |
| 内部递归 `x-minio-force-delete` | 前缀删除先于单对象条件路径返回，不能用作条件删除 |

条件判断不会额外增加 `s3:GetObject` 授权检查。普通删除授权仍然生效，包括显式版本对应的 `s3:DeleteObjectVersion`、Object Lock 保护检查，以及独立的可信复制路径。

## 为什么条件判断属于跨池协调层 {#problem}

在多存储池部署中，不同存储池可能保留同一对象在不同时期的副本。请求前置条件针对的是本次操作选中的单一逻辑对象。如果让每个存储池独立判断条件并直接修改磁盘状态，就可能先在一个池中删掉副本，随后在另一个池中返回 `412 PreconditionFailed`；或者删掉最新副本后，反而让旧池中的陈旧副本重新暴露为当前版本。

因此，多池协调层（`erasureServerPools.DeleteObject`）会先获取共享命名空间写锁，收集各池状态，对选中的逻辑表示只执行一次条件判断，随后清空向下传递的回调函数，并跨池协调删除清理。并发写入与元数据更新共用同一把外层命名空间锁。

### 早期设计中的反例 {#two-pool-counterexamples}

假设存储池 1 保留旧副本（ETag 为 `A`），存储池 2 保留当前最新副本（ETag 为 `B`）：

- **`If-Match: A`（返回 `412` 却发生部分删除）：** 若逐池独立判断，存储池 1 会先匹配并删除副本 `A`，随后在存储池 2 因与 `B` 不匹配而返回 `412 PreconditionFailed`，导致被拒绝的请求依然修改了底层存储。
- **`If-Match: B`（成功删除后旧副本复活）：** 若逐池独立判断，存储池 2 删除了最新副本 `B`，而存储池 1 因不匹配或跳过而保留了旧副本 `A`，导致陈旧数据重新成为客户端可见的当前对象。

此外，在逐池并发工作协程中直接调用 HTTP 条件回调，还可能引发对同一个 `http.ResponseWriter` 的并发写入竞争。在跨池协调层集中消费一次请求条件，能够同时消除这两类隐患。

### 失败边界 {#degraded-pool-limitation}

跨池协调路径在判断条件前会先读取各池状态，并向上报告读仲裁失败，而不会把不可达的存储池误判为空池。不过，物理清理失败仍可能发生在部分底层修改之后：单次请求失败并不等价于分布式多池回滚事务。存储层报错后，调用方仍需通过重试与状态核对来确认最终结果；详见[多池对象一致性](/zh/blog/design/multi-pool-object-consistency/)。

## 选择与判断 {#selected-fix}

### 只判断一次 {#evaluate-once}

`erasureServerPools.DeleteObject` 持有外层命名空间锁。多池部署调用 `deleteObjectReconciled`；单池部署先读取选中表示，并在删除标记快捷返回分支之前调用 `CheckPrecondFn`。下层存储引擎不再针对每份物理副本重复解释条件。

### 通配符与删除标记 {#wildcard}

`DELETE` 专用前置条件辅助函数将 `If-Match: *` 解释为“目标必须存在有效的非删除标记对象表示”；删除标记不能满足 `*`。缺失对象键或缺失指定版本会进入常规的未找到路径，不会被伪造成空 ETag 匹配。

### 授权 {#permission}

处理器依据实际生效的目标版本检查删除权限（`s3:DeleteObject` 或 `s3:DeleteObjectVersion`），**不会**在 `If-Match` 携带具体 ETag 时额外要求 `s3:GetObject` 权限。

### SSE-C ETag {#encrypted-etag}

条件删除直接比较元数据中已保存的客户端可见 ETag 投影，不会读取或解密对象数据载荷。SSE-C 读取密钥认证与对象删除属于相互独立的契约。

### 显式版本 {#current-version}

当请求提供显式 `versionId` 时，系统会选中该特定版本执行 ETag 比对与删除。因此，即使当前最新版本拥有不同的 ETag，只要所指定的历史版本 ETag 匹配，该历史版本仍可被正常删除。这与早期方案中“只允许比较当前版本”的设想不同。

### 尚未支持的边界 {#fail-closed-edges}

空 `If-Match` 请求头不会安装条件。内部递归前缀删除扩展（`x-minio-force-delete`）会绕过单对象条件路径。`ObjectToDelete` 不会解析批量 `DeleteObjects` XML 中的 `<ETag>` 元素，也没有整请求级别的 `NotImplemented` 拒绝保护。需要“比较后删除”语义的调用方必须使用带非空 `If-Match` 请求头的单对象 `DeleteObject` 接口。

## 被拒绝的替代方案与范围边界 {#rejected}

- **仅修改底层共享 ETag 比较函数：** 改动字符串比较辅助函数无法解决多池胜出版本选择，也无法阻止在条件检查前先修改其他池的数据。
- **逐池执行回调后再汇总错误：** 当某个池已经物理删除了副本后，即使外层汇总返回 `412` 也无法撤销已发生的删除。
- **引入新的分布式事务框架：** 在既有外层命名空间锁内消费一次条件回调已足以满足单对象 `DeleteObject`；批量条件删除与 IAM 策略键跨越了其他接口边界，应作为独立工作推进。

## 源码证据 {#tests}

核心实现位于 [`cmd/object-handlers.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-handlers.go)、[`cmd/erasure-server-pool.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool.go) 与 [`cmd/api-datatypes.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/api-datatypes.go)，回归测试覆盖了 ETag 不匹配、通配符与删除标记、显式 `versionId`、读仲裁失败以及多池状态协调。

## 后续工作 {#follow-up}

### 批量条件删除 {#delete-objects}

在 `DeleteObjects` 中支持逐项 `<ETag>` 条件需要解析该 XML 字段、在对应外层锁内逐一判断每个逻辑对象、兼容 `Quiet` 模式，并在逐项响应结果中报告条件失败。在此之前，批量请求中的 `<ETag>` 会被忽略，切勿将其用作并发控制手段。

### 策略强制键 {#policy-key}

IAM 策略包目前尚未定义 `s3:if-match` 条件键。支持通过策略强制要求客户端提供 `If-Match` 需要先在 `silo-pkg` 中新增该条件键、在服务端处理器中填充请求条件上下文，并补充策略评估测试。

## 设计权衡 {#tradeoff}

单对象条件 `DELETE` 直接复用了既有的多池对象选择与外层命名空间锁边界，无需引入新的事务层。完整的批量条件删除与 IAM 策略条件键涉及更多 API 与外部包边界，仍作为独立特性管理。核心不变量非常明确：当受支持的单对象 `If-Match` 条件不成立时，必须在任何存储池删除数据之前，针对选中的逻辑表示一次性完成判定。

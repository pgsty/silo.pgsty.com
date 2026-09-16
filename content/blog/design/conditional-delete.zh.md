---
title: "条件 DELETE：一个条件对应一个逻辑对象"
linkTitle: "条件 DELETE"
date: 2026-08-26
lastmod: 2026-09-16
author: "冯若航"
summary: >
  main 已实现单对象 If-Match DELETE，按指定版本判断，并使用跨池共享锁。早期方案中的批量 ETag 拒绝、额外 GetObject 授权以及畸形或递归请求保护尚未实现。本文区分已合并的行为与原始提案。
tags: [Design, S3, Compatibility, DELETE]
weight: 10
draft: false
url: "/zh/blog/design/conditional-delete/"
---

**2026-09-16 状态：**[#145](https://github.com/pgsty/silo/pull/145) 引入单对象条件删除，随后 [#178](https://github.com/pgsty/silo/pull/178) 修复多池串行化与清理。这两批修改均不在已发布的 Server 20260903 中。依赖该行为前请核对[组件矩阵](/compatibility/versions/)。

围绕 [PR #12](https://github.com/pgsty/silo/pull/12) 的八月方案比实际合并代码范围更大。其中批量拒绝、额外读取授权和只比较当前版本等规则，**并不是已实现的保证**。本文以维护主线 [`f99ed829b`](https://github.com/pgsty/silo/tree/f99ed829b5eba549160725f035156c9e020b6a07) 为依据。

## 已实现的契约 {#tldr}

| 请求 | 当前 main 的行为 |
| --- | --- |
| 单个 `DeleteObject`，非空 `If-Match: <ETag>` | 在删除锁内比较客户端可见 ETag；不匹配时先返回 412，不执行删除 |
| `If-Match: *` | 要求选中的表示存在且不是删除标记 |
| 显式 `versionId` | 比较**指定版本**，不是另一个当前版本 |
| 没有 `If-Match` 或头值为空 | 不安装条件回调，按普通删除处理 |
| 批量 `DeleteObjects` 的逐项 `<ETag>` | 请求模型没有 ETag 字段，这个 XML 字段**不提供删除保护** |
| 内部递归 `x-minio-force-delete` | 前缀删除先于对象条件路径返回，不能用作条件删除 |

条件判断不会额外增加 `s3:GetObject` 授权检查。普通删除授权仍然生效，包括显式版本对应的 `s3:DeleteObjectVersion`、Object Lock 检查，以及单独的可信复制路径。

## 为什么条件属于跨池协调层 {#problem}

<a id="silent-downgrade"></a><a id="good-direction"></a><a id="atomicity-boundary"></a>

不同池可能保留同一对象的不同时期副本。请求条件针对本次操作选择的逻辑对象。如果每个池独立判断并修改，就可能先删掉一个副本、再从另一个池返回 412；也可能删掉最新副本后让旧副本重新可见。

因此，多池路径先持有共享命名空间写锁，收集相关状态，只判断一次条件，再清除向下传递的回调并跨池协调删除。并发写入和元数据更新也必须使用同一锁边界。这是后续多池修复的目标，并不表示所有物理磁盘能原子更新。

### 早期设计中的反例 {#two-pool-counterexamples}

<a id="partial-delete-on-412"></a><a id="stale-copy-after-success"></a>

假设一个池保存旧 ETag A，另一个池保存当前 ETag B：

- `If-Match: A` 不能先删 A，再因 B 不匹配而失败。
- `If-Match: B` 不能只删 B，留下 A 重新成为可见对象。

逐池 HTTP 回调还可能并发写同一个响应对象。应在协调层消费请求条件。

### 失败边界 {#degraded-pool-limitation}

协调路径在判断条件前读取各池状态，并报告失败，不把未知池视为空池。清理失败仍可能发生在部分物理修改之后：请求失败不等于分布式回滚。存储出错后仍需重试并核对实际状态，详见[多池一致性](/blog/design/multi-pool-object-consistency/)。

## 选择与判断 {#selected-fix}

### 只判断一次 {#evaluate-once}

`erasureServerPools.DeleteObject` 持有外层锁。多池使用 `deleteObjectReconciled`；单池读取选中表示，在删除标记快捷返回前调用 `CheckPrecondFn`。下层不再针对每份副本解释条件。

### 通配符与删除标记 {#wildcard}

<a id="delete-marker"></a>

DELETE 专用辅助函数把 `*` 解释为表示存在，删除标记不能满足该条件。缺失对象或指定版本走相应的未找到路径，不会被伪造成空 ETag 匹配。

### 授权 {#permission}

处理器按有效版本选择删除动作。它**没有**实现原提案针对具体 ETag 要求的额外 `s3:GetObject` 检查。原提案的权限矩阵不能作为已实现 AWS 兼容性的证明。

### SSE-C ETag {#encrypted-etag}

条件删除比较既有的客户端可见 ETag 投影，不读取或解密对象载荷。SSE-C 读取密钥认证与删除对象是不同契约。

### 显式版本 {#current-version}

显式 `versionId` 选择被比较和删除的版本。因此，即使当前版本拥有另一个 ETag，只要历史 ETag 匹配，仍可删除那个历史版本。这与早期方案的“只比较当前版本”不同。

### 尚未支持的边界 {#fail-closed-edges}

空 `If-Match` 不安装条件。递归前缀删除扩展绕过对象条件。`ObjectToDelete` 不识别批量 XML ETag，也不存在整请求 `NotImplemented` 拒绝保护。需要比较后删除的调用方必须使用支持的单对象路径和非空条件，并确认所选发布版本包含实现。

## 替代方案与范围 {#rejected}

<a id="reject-comparator"></a><a id="reject-per-pool"></a><a id="reject-framework"></a><a id="reject-scope-expansion"></a>

修改共享 ETag 比较器无法解决池选择和修改顺序。逐池回调后汇总错误也无法撤销已经发生的删除。在既有命名空间锁内消费一个回调不需要新事务框架，但批量执行与策略强制仍需单独实现。

## 证据与发布边界 {#tests}

<a id="adversarial-review"></a><a id="merge-gates"></a>

源码依据为[处理器](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-handlers.go)、[池协调层](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool.go)和[批量请求模型](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/api-datatypes.go)。相关覆盖包括 ETag 不匹配、通配符与删除标记、显式版本、仲裁失败和多池。早期针对另一份实现的本地审阅与测试结论，不能证明这些缺失保护已经存在。合并、发布和实际部署仍是不同事实。

## 后续工作 {#follow-up}

### 批量条件 {#delete-objects}

逐项 ETag 支持需要解析字段，在正确锁内判断每个逻辑对象，保留 quiet 模式，并在逐项响应中报告条件失败。目前批量 ETag 会被忽略，不能作为并发保护。

### 策略强制 {#policy-key}

维护的策略包尚未定义 `s3:if-match`。支持它需要修改并发布包、正确填充请求条件、更新 Server 依赖并验证授权。执行 `If-Match` 本身不等于能用策略强制客户端提供条件。

## 设计成本 {#tradeoff}

<a id="conclusion"></a>

单对象执行复用既有的对象选择和锁边界。完整批量条件与策略强制涉及更多接口，仍是独立工作。有效不变量应限定为：支持的单对象条件为假时，必须在删除前针对选中的逻辑表示判断一次。

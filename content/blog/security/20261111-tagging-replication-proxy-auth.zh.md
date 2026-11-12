---
title: "SN-2026-022：双活复制标签代理（Tagging Proxy）未认证删除与远端标签策略绕过"
linkTitle: "SN-2026-022 · 标签复制代理鉴权"
date: 2026-11-11
author: "冯若航"
description: "双活（Active-Active）复制场景下，DeleteObjectTagging 在认证调用方之前即向远端复制站点发起代理删除，且 GetObjectTagging、PutObjectTagging 与 DeleteObjectTagging 在本地缺副本时未读取并校验远端副本标签，可绕过基于 s3:ExistingObjectTag 的 IAM 限制策略。"
tags: [安全, S3, Replication, Tagging, IAM, SILO]
weight: 1
draft: false
url: "/zh/blog/security/20261111-tagging-replication-proxy-auth/"
---

**发布状态：** 已随 **[SILO 20261112](/zh/blog/release/silo-20261112/)** 发布（[`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697)、[`67a90dfef`](https://github.com/pgsty/silo/commit/67a90dfef458d3e5228e849711118bc162abed30)、[`293ab78b4`](https://github.com/pgsty/silo/commit/293ab78b4cc505c3ab8170a4b2b4b29c04ad74f9)；配套的代理 `GET`/`HEAD` 标签条件鉴权及 `x-amz-tagging-count` / `X-Amz-Object-Lock-*` 响应头裁剪见 [`c39605d4f`](https://github.com/pgsty/silo/commit/c39605d4f8a384096685ee3ea3a97802d9c8071c) 与 [`ea37a7e8b`](https://github.com/pgsty/silo/commit/ea37a7e8b05fddb32c8578c3e959d956dee3e2b0)）\
**安全编号：** `SN-2026-022`（[安全公告台账](/zh/about/security-advisories/#sn-2026-022)，[#337](https://github.com/pgsty/silo/issues/337)）\
**严重程度：** 严重（Critical）\
**影响范围：** **SILO Server**（`RELEASE.2026-11-09T00-00-00Z` 及更早版本）与自 `2024-01-12`（[`b2b26d9c9`](https://github.com/pgsty/silo/commit/b2b26d9c958a82fbd9f7e0dc70fc2133838576d0)）以来的上游原版 MinIO\
**不受影响组件：** `silo-console`、`mcli`、`silo-pkg` 与 `kes`

在启用双活（Active-Active）桶复制或站点复制的拓扑中，某个对象版本可能已写入远端复制对端，但尚未同步至当前接收客户端请求的本地集群。为保持跨站标签读写透明一致，`GetObjectTaggingHandler`、`PutObjectTaggingHandler` 与 `DeleteObjectTaggingHandler`（`cmd/object-handlers.go`）在本地未找到目标对象时，会通过 `proxyTaggingToRepTarget`（`cmd/bucket-replication.go`）使用服务端持有的高权限复制目标凭据向对端站点代理请求。

继承自上游 MinIO 的这一代理实现存在两处安全缺陷：`DeleteObjectTaggingHandler` 在执行调用方身份认证与权限检查**之前**就查询本地对象并向远端发起代理删除；同时三个标签接口在代理本地缺失对象时均未读取远端副本上的既有标签，导致基于 `s3:ExistingObjectTag/<key>` 的 IAM 策略条件失效。

## 摘要 {#summary}

- **问题本质：**
  1. **未认证远端标签抹除与私有桶对象探测：** `DeleteObjectTaggingHandler` 将 `getObjectInfo` 与 `proxyTaggingToRepTarget` 放在了 `checkRequestAuthType` 之前。当目标对象仅存在于双活对端站点时，**完全未携带任何签名的匿名请求** `DELETE /<bucket>/<key>?tagging` 会驱动服务端使用内部复制凭据直接清空远端对象标签并返回 `204 No Content`；即便未配置复制，匿名请求也可在无 `s3:ListBucket` 权限的私有桶上通过 `404 NoSuchKey` 与 `403 AccessDenied` 的响应差异探测任意对象是否存在。
  2. **跨站点 `s3:ExistingObjectTag` 条件策略绕过：** 当对象在本地不存在时，`GetObjectTagging`、`PutObjectTagging` 与 `DeleteObjectTagging` 仅按空标签集（`""`）评估本地 IAM 策略便直接向双活对端转发操作——既使受 `s3:ExistingObjectTag/*` 显式 `Deny` 约束（例如禁止修改带 `classification=restricted` 标签对象）的调用方可通过访问缺副本站点绕过拦截，也使依赖标签匹配才授予 `Allow` 的合法请求被误判为 `403 AccessDenied`。
- **上游溯源：** 两处问题均由上游 MinIO 于 `2024-01-12` 合入的提交 [`b2b26d9c9`](https://github.com/pgsty/silo/commit/b2b26d9c958a82fbd9f7e0dc70fc2133838576d0)（[minio/minio#18649](https://github.com/minio/minio/pull/18649)，*"support proxying of tagging requests in replication"*）引入，影响 2024 年 1 月之后的所有上游 MinIO 版本及 SILO Server `20261109` 与更早版本。
- **修复方式：** 提交 [`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697)、[`67a90dfef`](https://github.com/pgsty/silo/commit/67a90dfef458d3e5228e849711118bc162abed30) 与 [`293ab78b4`](https://github.com/pgsty/silo/commit/293ab78b4cc505c3ab8170a4b2b4b29c04ad74f9) 在入口处无条件执行调用方认证，以 `authorizeRequestWithUnreadTags` 拦截无权限调用方的跨站探测，在返回或修改前读取并逐一校验**所有已存在双活副本**的实际标签，同时容忍复制延迟导致的单目标缺失并对不可读目标执行 Fail-Closed 拒绝。

---

## 一、上游溯源与根因分析 {#provenance}

### `DeleteObjectTaggingHandler` 中的认证前代理执行 {#unauth-delete}

在 `PutObjectTaggingHandler` 与 `GetObjectTaggingHandler` 中，上游代码先执行认证再访问存储层；但在 `DeleteObjectTaggingHandler` 中，上游提交 [`b2b26d9c9`](https://github.com/pgsty/silo/commit/b2b26d9c958a82fbd9f7e0dc70fc2133838576d0) 将本地元数据读取与双活代理逻辑直接插入到了 `checkRequestAuthType` 之前：

```go
// 继承自上游的 DeleteObjectTaggingHandler 执行顺序（cmd/object-handlers.go）
oi, err := getObjectInfo(ctx, bucket, object, opts)
if err != nil {
    if (isErrObjectNotFound(err) || isErrVersionNotFound(err)) &&
        proxyTaggingToRepTarget(ctx, w, r, bucket, object, tags, opts) {
        writeSuccessNoContent(w)
        return
    }
    writeErrorResponse(ctx, w, toAPIError(ctx, err), r.URL)
    return
}
// 仅当对象在本地存在时，才会走到下方的身份认证与 IAM 鉴权！
if s3Error := checkRequestAuthType(ctx, r, deleteObjectTaggingAction(...), bucket, object); s3Error != ErrNone {
    ...
}
```

这一顺序直接造成两重后果：

1. **匿名清空远端副本标签：** 只要请求命中的站点本地尚未存有 `(bucket, object)`（返回 `ObjectNotFound` 或 `VersionNotFound`），且匹配的复制规则选中了允许代理并持有对象的目标，`proxyTaggingToRepTarget` 就会用服务端预先配置的复制凭据调用 `clnt.RemoveObjectTagging`，在未验证来访请求任何签名的情况下抹除对端站点上的对象标签并返回 `204 No Content`。
2. **私有桶键名存在性泄露：** 即使在未开启复制的普通私有桶上，匿名请求对不存在的键返回 `404 NoSuchKey`，对本地已存在的键则进入 `checkRequestAuthType` 返回 `403 AccessDenied`，从而无需 `s3:ListBucket` 即可枚举桶内对象路径。

### 跨站点代理缺失 `s3:ExistingObjectTag` 条件评估 {#blind-proxy}

S3 与 SILO 支持通过 `s3:ExistingObjectTag/<key>` 条件键在对象标签上实施基于属性的访问控制（ABAC）：

- `GetObjectTagging` / `GetObjectVersionTagging`
- `PutObjectTagging` / `PutObjectVersionTagging`（需同时校验证书已有标签 `s3:ExistingObjectTag/<key>` 与请求新标签 `s3:RequestObjectTag/<key>`）
- `DeleteObjectTagging` / `DeleteObjectVersionTagging`

当对象存在于本地时，处理器会从 `xl.meta` 读出 `oi.UserTags` 并调用 `authorizeRequestWithExistingTags`。但当对象在本地缺失时，`b2b26d9c9` 在未查询远端标签的前提下仅用空标签 `""` 做了一次本地检查便向对端发起代理：

- 若策略通过 `Deny` 禁止调用方修改带有 `s3:ExistingObjectTag/tier == "prod"` 的对象，调用方只要将请求发往尚未同步到该对象的双活站点，本地就会按空标签放行，并由高权限复制账号代为覆盖或删除对端标签。
- 反之，若策略仅在 `s3:ExistingObjectTag/team == "analytics"` 时授予 `Allow`，客户端请求一旦落到缺副本站点就会被误拒为 `403 AccessDenied`。
- 在**三个及以上站点的多目标双活拓扑**中，不同远端目标上的标签可能处于异步传播中间态。若只校验第一个响应的对端，或在完成全部存活副本鉴权前就开始下发写操作，仍会破坏跨副本标签策略的一致性边界。

---

## 二、影响范围 {#impact}

| 部署形态                     | 实际受影响面                                                                                                                                                                                              |
| :--------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **双活桶复制或站点复制集群** | 匿名请求可删除本站点缺失但对端存在的对象标签（`DELETE ?tagging`）；已认证受限主体可在 `GET`/`PUT`/`DELETE ?tagging` 上绕过针对 `s3:ExistingObjectTag` 的 `Deny` 规则，而基于标签的 `Allow` 规则会被误拒。 |
| **单向或异步复制**           | `replicateSync=false` 本身不会禁用代理；是否选中目标取决于匹配的复制规则和代理目标状态。不能把单向或异步模式当作免受影响的边界。                                                                          |
| **未启用复制的独立集群**     | 未认证或无权限调用方可通过 `DELETE ?tagging` 探测私有桶内对象是否存在（无 `s3:ListBucket` 时仍返回 `404` 而非 `403`）；本地已有对象的标签鉴权不受影响。                                                   |
{.wide .expand}

---

## 三、修复方案：设计思考与充分必要性 {#fix}

提交 [`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697)、[`67a90dfef`](https://github.com/pgsty/silo/commit/67a90dfef458d3e5228e849711118bc162abed30) 与 [`293ab78b4`](https://github.com/pgsty/silo/commit/293ab78b4cc505c3ab8170a4b2b4b29c04ad74f9) 将 `GetObjectTagging`、`PutObjectTagging` 与 `DeleteObjectTagging` 统一收敛到同一套两阶段鉴权代理模型：

1. **无条件前置身份认证：** 三个处理器均在访问本地对象层或复制目标前先调用 `authenticateRequest`，彻底封堵匿名流量进入后续链路（除非桶策略显式允许匿名访问）。
2. **跨站探测前置门禁（`authorizeRequestWithUnreadTags`）：** 当本地返回 `ObjectNotFound` / `VersionNotFound` 时，服务端不会对任意已登录用户无条件发起跨站 RPC，而是先通过 `authorizeRequestWithUnreadTags` 判定“该调用方是否存在至少一种标签组合使其可能获准执行本操作”。若调用方根本没有任何匹配的 `Allow` 语句（或命中了与标签无关的 `Deny`），本地直接拒绝并按 `s3:ListBucket` 权限决定返回 `404` 还是 `403`；若本地存储发生可重试故障（如 `503 SlowDownRead`），已获授权调用方将收到真实存储错误而非误报 `AccessDenied`。
3. **对入选目标进行两阶段读取与鉴权（`readTaggingProxyTargets`）：**
   - **第一阶段（读取并授权每份入选的现存副本）：** `getProxyTargets` 按匹配的复制规则选择目标；`readTaggingProxyTargets` 先跳过无客户端、已标记离线或禁用代理的目标，再发起 `GetObjectTagging`。下列错误处理针对实际入选目标：
     - 若某个对端因复制延迟返回 `NoSuchKey` 或 `NoSuchVersion`，跳过该缺失目标继续检查其余对端；若所有对端均不存在该对象，则按标准缺失对象规则返回 `404` 或 `403`。
     - 若**任一**对端返回网络超时、认证失败或 `5xx` 存储错误，立即 **Fail-Closed 终止**请求，绝不在无法确认远端是否存在受保护标签的情况下放行读写。
     - 对每一个实际持有该对象版本的对端，使用其真实标签调用 `authorizeRequestWithExistingTags`（`PutObjectTagging` 同时校验请求携带的新标签 `RequestObjectTag`）。只要任一存活副本未通过策略评估，整次请求即返回 `403 AccessDenied`。
   - **第二阶段（仅向已核验目标下发变更）：** `PutObjectTagging` 与 `DeleteObjectTagging` 只复用第一阶段已完成鉴权的客户端句柄。至少一个实际尝试的写入成功时返回成功；所有实际写入都失败才返回错误。被跳过的目标不能算作成功，写入也不是跨目标原子事务。

### 为什么该设计既必要又充分 {#sufficiency}

- **必要性：** 对抗测试（`cmd/tagging-proxy-authz_test.go`）逐项验证了缺少任一环节的后果：
  - 若缺少前置认证与 `authorizeRequestWithUnreadTags` 门禁，无权限账号仍可触发跨站扇出读取或探测键名；
  - 若只抽检单个远端目标，在多站点标签尚未收敛时会漏掉另一站点上的 `Deny` 标签；反之若机械要求“所有远端站点都必须持有副本”，正常的异步复制延迟就会导致双活标签操作大面积报 `404`；
  - 若对读取失败的远端目标降级放行（Fail-Open），故障窗口内就会绕过基于标签的显式 `Deny` 隔离。
- **充分性：** `GET`、`PUT`、`DELETE` 三条标签路径共用 `readTaggingProxyTargets`（`cmd/bucket-replication.go`），在单目标与多目标双活拓扑下统一保证了身份认证、`ExistingObjectTag` / `RequestObjectTag` 条件求值、`s3:ListBucket` 错误掩码以及远端故障原子拦截。

---

## 四、利弊权衡、潜在代价与边界 {#tradeoffs}

| 权衡维度                                    | 收益与代价说明                                                                                                                                                                         |
| :------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **本地缺副本时的额外远端 `GET` 往返**       | 本地已有对象不需要这些代理读取。当对象在本地缺失时，代理会先读取每个符合筛选条件的入选目标的标签，再返回或修改远端标签。                                                               |
| **对端站点故障时的 Fail-Closed 可用性取舍** | 入选目标的标签读取失败时，代理请求会在变更前终止。筛选时已标记离线或禁用代理的目标会被跳过，因此并不保证检查每个已配置对端。                                                           |
| **跨广域网无分布式锁的并发窗口**            | 双活 S3 复制不在广域网站点间持有分布式互斥锁。第一阶段校验的是紧邻写入前的远端标签快照；跨站点同时并发修改同一对象标签时，最终状态仍按既有的复制标签时间戳（`TaggingTimestamp`）收敛。 |
{.wide .expand}

---

## 升级指引与缓解建议 {#remediation}

1. **全站点协同升级 SILO Server：** 请将双活复制拓扑中的所有节点升级至 **[SILO 20261112](/zh/blog/release/silo-20261112/)**（`RELEASE.2026-11-12T00-00-00Z`）或更高版本（包含 [`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697)、[`67a90dfef`](https://github.com/pgsty/silo/commit/67a90dfef458d3e5228e849711118bc162abed30) 与 [`293ab78b4`](https://github.com/pgsty/silo/commit/293ab78b4cc505c3ab8170a4b2b4b29c04ad74f9)）。任意未升级的站点若暴露在客户端流量下，仍可能使用其复制凭据代发未认证的 `DELETE ?tagging`。
2. **升级前网关层临时缓解：** 若短期内无法完成升级且 S3 端口面向不可信网络开放，可在反向代理或负载均衡层拦截同时不含 `Authorization` 请求头与 `X-Amz-Signature` 查询参数的 `DELETE ...?tagging` 请求。
3. **升级后审计：** 在双活复制桶上依赖对象标签实施权限隔离（`s3:ExistingObjectTag/*`）的集群，建议升级后核查审计日志中是否存在异常的 `DeleteObjectTagging` / `PutObjectTagging` 记录并比对各站点标签一致性。

更多信息请参阅[安全公告台账](/zh/about/security-advisories/#sn-2026-022)、[Server 兼容性说明](/zh/compatibility/server/#candidate-after-20261109)以及关联公告 [SN-2026-024（`GetObjectAttributes` 与 ZIP 归档标签鉴权）](/zh/blog/security/20261111-attributes-and-archive-tag-authz/)。

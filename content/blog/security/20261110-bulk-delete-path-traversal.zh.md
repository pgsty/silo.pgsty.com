---
title: "SN-2026-020：单存储池批量删除（DeleteObjects）跨桶路径穿越"
linkTitle: "SN-2026-020 · 批量删除跨桶穿越"
date: 2026-11-10
author: "冯若航"
description: "单存储池部署下，S3 DeleteObjects 检出含 '..' 的非法对象名并记录 ObjectNameInvalid 后仍将条目下发至本地磁盘，并在磁盘操作完成后将错误清零，导致跨桶版本删除、COMPLIANCE 对象锁绕过及 .minio.sys 元数据删除标记写入。"
tags: [安全, S3, Path Containment, Object Lock, WORM, SILO]
weight: 1
draft: false
url: "/zh/blog/security/20261110-bulk-delete-path-traversal/"
---

**发布状态：** 主干已修复（[`a18293d0c`](https://github.com/pgsty/silo/commit/a18293d0c309b93fe9c69f45ed8f44fe558fe01d)），将随 [`20261109`](/zh/blog/release/silo-20261109/) 之后的 Server 热修版本发布\
**安全编号：** `SN-2026-020`（[安全公告台账](/zh/about/security-advisories/#sn-2026-020)）\
**严重程度：** 严重（Critical）\
**影响范围：** 单存储池（Single-Pool）部署的 **SILO Server**（`RELEASE.2026-11-09T00-00-00Z` 及更早版本）与上游原版 MinIO；多存储池（`2` 个及以上存储池）部署自 SILO `20261026` 起不受影响\
**不受影响组件：** `silo-console`、`mcli`、`silo-pkg` 与 `kes`

在单存储池部署中，`(*erasureServerPools).DeleteObjects`（`cmd/erasure-server-pool.go`）在收到 S3 批量删除请求（`POST /<bucket>?delete`）后，会调用 `checkDelObjArgs` 校验每个对象名并将 `ObjectNameInvalid` 写入 `derrs[i]`，但后续的单池执行分支并未跳过报错条目，仍将完整切片下发至磁盘，并在本地磁盘回报目标存在且处理完成时将 `derrs[i]` 重置为 `nil`。由于本地 `xlStorage` 通过 `pathJoin` 将对象名直接拼接到请求桶目录下，含 `..` 路径段的对象名可越出当前请求桶，访问其他业务桶或 `.minio.sys` 系统卷。

## 摘要 {#summary}

- **漏洞根因：** `checkDelObjArgs` 在入口处已将 `../B/secret` 标记为 `ObjectNameInvalid`（写入 `derrs[i]`），但单节点批量加锁路径与分布式单池按集加锁路径（`deleteObjectsInSets`）均未过滤 `derrs[i] != nil` 的条目，结果合并循环又在磁盘操作成功时执行 `derrs[i] = nil` 清除了该错误。
- **影响范围：** 在未开启对象锁的桶 `A` 上持有 `s3:DeleteObjectVersion` 的调用方，可通过传入 `../B/secret` 与 `versionId` 物理删除其他桶 `B` 中的指定版本，绕过桶 `B` 的 `COMPLIANCE` 合规保留期与法务保留（Legal Hold）；若桶 `A` 开启了版本控制，仅持有 `s3:DeleteObject` 的调用方无需提供版本号即可在桶 `B` 的对象或 `.minio.sys/buckets/B/.metadata.bin` 上写入删除标记。
- **历史溯源：** 该控制流继承自上游 MinIO 2020 年的单池批量删除分支（[`bdd094bc3`](https://github.com/pgsty/silo/commit/bdd094bc3)）与 2025 年初的多池派发重写（[`079d64c80`](https://github.com/pgsty/silo/commit/079d64c80)）。SILO 在 `Server 20261026`（[`3c82748e1`](https://github.com/pgsty/silo/commit/3c82748e1)）重构多存储池删除一致性时已在 `!z.SinglePool()` 分支中加入 `if derrs[i] != nil { continue }`，因此多存储池部署不受影响。
- **修复方式：** 提交 [`a18293d0c`](https://github.com/pgsty/silo/commit/a18293d0c309b93fe9c69f45ed8f44fe558fe01d) 在 `checkDelObjArgs` 校验循环后立即分流：校验失败的条目保留错误并直接返回，不再进入命名空间加锁、元数据查询或磁盘调用；全合法请求不进入新分支。

---

## 一、问题的发现 {#discovery}

2026 年 10 月 31 日，Denis Babchuk（[`@botdeniska`](https://github.com/botdeniska)）通过 GitHub 私密漏洞报告指出：`DeleteMultipleObjectsHandler`（`cmd/bucket-handlers.go`）仅根据请求桶在节点内存中的 `hasLockEnabled` 缓存决定是否执行对象锁保留期与法务保留检查，而未在存储写锁内逐版本校验目标状态。为此，[SILO Server 20261109](/zh/blog/release/silo-20261109/#authorization) 合入了 [PR #330](https://github.com/pgsty/silo/pull/330)（[`6ef3a52fc`](https://github.com/pgsty/silo/commit/6ef3a52fc)），使开启对象锁的桶在批量物理删除版本时复用持有变更锁的单对象删除路径。

在对 `6ef3a52fc` 与私密安全报告队列开展后续核验时，我们进一步检查了跨桶边界场景：当 URL 中的请求桶 `A`（`POST /A?delete`）未开启对象锁，而 XML 请求体中的 `<Object><Key>` 包含 `../B/secret` 指向已开启 `COMPLIANCE` 对象锁的桶 `B` 时，系统如何处理。在 `Server 20261026` 与 `Server 20261109` 上的实测确认单存储池部署会执行该跨桶删除；进一步排查同时确认了仅凭 `s3:DeleteObject` 跨桶写入删除标记、向 `.minio.sys` 元数据写入删除标记，以及同批次重复归一化别名导致的批量锁自死锁。感谢 [`@botdeniska`](https://github.com/botdeniska) 此前提交的 `DeleteObjects` 对象锁报告促成了本次关联审计。

---

## 二、溯源与根因 {#provenance}

### 请求路由与处理器鉴权流程 {#request-flow}

对于单对象 S3 接口（`GET /A/key`、`PUT /A/key`、`DELETE /A/key`），对象名位于 HTTP 请求 URL 路径中，URL 规范化与通用 HTTP 中间件会在进入业务处理器前拦截包含 `..` 的路径。

S3 `DeleteObjects`（`POST /A?delete`）则通过 XML 请求体传递最多 1,000 个 `<Key>` 条目：

1. **URL 中间件不解析 XML 请求体：** 请求 URL 中仅包含桶名 `A`，对象名从请求体反序列化得到。
2. **IAM 鉴权按请求桶 `A` 评估：** `DeleteMultipleObjectsHandler` 构造资源标识 `arn:aws:s3:::A/../B/secret` 并校验 `s3:DeleteObject` 或 `s3:DeleteObjectVersion`。任何授予 `arn:aws:s3:::A/*` 删除权限的策略均会匹配通过。
3. **桶级对象锁预检仅读取请求桶 `A`：** 处理器调用 `globalBucketObjectLockSys.Get(bucket)` 检查桶 `A` 是否开启 Object Lock（`hasLockEnabled`）。当桶 `A` 未开启对象锁时，请求不会进入 `6ef3a52fc` 的单对象锁内检查分支，而是直接调用 `erasureServerPools.DeleteObjects`。

### 单存储池路径上的错误丢弃与覆盖 {#discarded-check}

在 `(*erasureServerPools).DeleteObjects`（`cmd/erasure-server-pool.go`）入口处，代码已对每个对象名执行目录对象编码与合法性校验：

```go
for i := range derrs {
    objects[i].ObjectName = encodeDirObject(objects[i].ObjectName)
    ...
    derrs[i] = checkDelObjArgs(ctx, bucket, objects[i].ObjectName)
    objSets.Add(objects[i].ObjectName)
}
```

对于 `../B/secret`，`checkDelObjArgs`（内部调用 `hasBadPathComponent`）会返回 `ObjectNameInvalid` 并写入 `derrs[i]`。但在单存储池部署中，后续三步逻辑使该检查失效：

1. **未过滤报错条目：** 单节点批量加锁分支与分布式单池按纠删集加锁分支（`deleteObjectsInSets`）均未检查 `derrs[i] != nil`，直接将完整 `objects` 切片下发至存储池。
2. **本地磁盘路径拼接越界：** 在本地磁盘（`xlStorage`）上，各存储桶与 `.minio.sys` 均为磁盘根目录下的同级子目录（`/data/A`、`/data/B`、`/data/.minio.sys`）。`xlStorage.deleteVersions` 调用 `pathJoin(volumeDir, path)` 时，`path.Clean` 将 `/data/A` 与 `../B/secret` 合并为 `/data/B/secret`，进而物理删除目标版本或改写其 `xl.meta`。
3. **结果合并阶段清空初始错误：** 当存储池返回执行结果后，`erasureServerPools.DeleteObjects` 的合并循环按如下规则处理：

```go
if dErrsByPool[pool][j] == nil && dObjectsByPool[pool][j].found {
    // A fast exit when the object is found and removed
    dobjects[i] = dObjectsByPool[pool][j]
    derrs[i] = nil
    break
}
```

只要目标路径在磁盘上存在且本地磁盘未发生 I/O 错误（`found == true` 且 `err == nil`），`derrs[i] = nil` 就会覆盖入口处记录的 `ObjectNameInvalid`，并在 HTTP `200 OK` 响应中将该条目标记为 `<Deleted>`。在 `deleteObjectsInSets` 路径上，各纠删集返回的 `nil` 错误同样会直接覆盖 `derrs[idx]`。

### 上游 Git 演进记录 {#upstream-history}

追溯 `cmd/xl-zones.go`、`cmd/erasure-server-sets.go` 与 `cmd/erasure-server-pool.go` 的提交历史，该问题完整继承自上游 `minio/minio`：

| 时间    | 提交记录                                                                       | 来源仓库                 | 变更内容                                                                                                              |
| :------ | :----------------------------------------------------------------------------- | :----------------------- | :-------------------------------------------------------------------------------------------------------------------- |
| 2020-02 | [`ab7d3cd50`](https://github.com/pgsty/silo/commit/ab7d3cd50)（`minio#8974`）  | 上游 MinIO               | 将逐对象加锁循环（原含 `if derrs[i] != nil { continue }`）改为整批加锁，并将未过滤的 `objects` 切片直接传给底层 zone  |
| 2020-11 | [`bdd094bc3`](https://github.com/pgsty/silo/commit/bdd094bc3)（`minio#10994`） | 上游 MinIO               | 新增单池快捷分支 `if z.SingleZone() { return z.serverSets[0].DeleteObjects(...) }`，在单存储池下直接丢弃 `derrs`      |
| 2025-01 | [`079d64c80`](https://github.com/pgsty/silo/commit/079d64c80)（`minio#20821`） | 上游 MinIO               | 统一向所有存储池并发下发，并在合并循环中对 `found && err == nil` 的条目执行 `derrs[i] = nil`                          |
| 2026-10 | [`3c82748e1`](https://github.com/pgsty/silo/commit/3c82748e1)                  | PGSTY SILO（`20261026`） | 在 `!z.SinglePool()` 多存储池分支中加入 `if derrs[i] != nil { continue }`，使 `2+` 存储池集群免疫，单池路径仍保持原状 |
{.wide .expand}

---

## 三、触发条件 {#triggers}

触发该漏洞需同时满足以下三项条件：

1. **单存储池拓扑（Single-Pool）：** 服务端运行于单个存储池模式（`z.SinglePool() == true`），包括单机单盘、单机多盘纠删码及单存储池多节点分布式集群。运行 `Server 20261026` 及更高版本的多存储池（`2` 个及以上存储池）集群已在 `!z.SinglePool()` 分支中跳过非法条目，不受影响。
2. **至少在一个桶上拥有删除权限：** 调用方持有的凭据（或预签名 `POST /<bucket>?delete` 请求）在任意桶 `A` 上具备 `s3:DeleteObject` 或 `s3:DeleteObjectVersion` 权限。
3. **XML 请求体包含 `..` 路径段：** 提交的 `DeleteObjects` XML 请求体中存在经 `encodeDirObject` 处理后仍含 `..` 路径段的 `<Key>`（如 `../B/secret` 或 `a/../../.minio.sys/buckets/B/.metadata.bin`）。

---

## 四、影响范围 {#impact}

在单机单盘与单机 16 盘纠删码实例上，使用仅被授予 `arn:aws:s3:::A/*` 删除权限的测试账号实测确认了以下四类行为：

| 请求桶 `A` 状态                      | 桶 `A` 上的权限                        | XML 请求条目                                                                          | 实测结果                                                                                                                                                                        |
| :----------------------------------- | :------------------------------------- | :------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 未开启对象锁（无论是否开启版本控制） | `s3:DeleteObjectVersion`               | `<Key>../B/secret</Key>` + `<VersionId>v1</VersionId>`（桶 `B` 开启 `COMPLIANCE` 锁） | 桶 `B` 中处于有效 `COMPLIANCE` 保留期内的版本 `v1` 被从磁盘物理删除                                                                                                             |
| 已开启版本控制                       | 仅 `s3:DeleteObject`（无 `VersionId`） | `<Key>../B/doc</Key>`（不带 `<VersionId>`）                                           | 桶 `B` 的对象被追加写入删除标记，后续不带版本号的 `GET`/`HEAD` 返回 `404 Object not found`                                                                                      |
| 已开启版本控制                       | 仅 `s3:DeleteObject`（无 `VersionId`） | `<Key>../.minio.sys/buckets/B/.metadata.bin</Key>`                                    | `.minio.sys` 中桶 `B` 的元数据对象被写入删除标记（IAM 记录与集群配置同样存储在 `.minio.sys` 下）                                                                                |
| 未开启版本控制                       | `s3:DeleteObject`                      | `<Key>../B/small</Key>`（单版本内联小对象）                                           | 响应返回 `Deleted`，但 `xlStorage.deleteFile` 的 `strings.HasPrefix` 基路径检查提前返回，未实际删除 `xl.meta`（除非桶 `B` 名称以桶 `A` 为字符串前缀，或对象包含独立 `dataDir`） |
{.wide .expand}

### 补充技术说明 {#amplifiers}

1. **写入删除标记无需 `s3:DeleteObjectVersion` 或目标 `versionId`：** `DeleteMultipleObjectsHandler` 根据请求桶 `A` 的版本控制状态设置 `opts.Versioned`。只要桶 `A` 开启了版本控制且请求未指定 `<VersionId>`，`xlStorage.deleteVersions` 就会通过 `WriteAll` 向目标路径的 `xl.meta` 追加删除标记，不经过 `deleteFile`。
2. **单节点与分布式单存储池集群的差异：**
   - **单节点部署：** 所有磁盘均为本地 `xlStorage` 实例，不经过节点间 RPC 守卫，单次请求即可达到写入仲裁并立即生效。
   - **分布式单存储池集群：** 远端节点磁盘由 `guardedStorage`（[`SN-2026-002`](/zh/blog/security/internode-path-containment/)，`cmd/storage-rest-server-guard.go`）包装，会在内部 RPC 层拒绝含 `..` 的路径，因此单次请求在远端盘上无法达到写入仲裁；**但接收 HTTP 请求的节点自身的本地磁盘未经过 RPC 包装，仍会执行删除或写入标记**。若攻击者将同一请求逐个发往集群各节点，当本地受损分片数超过纠删码校验盘数时，目标对象同样会不可恢复。
3. **跨桶占锁与同批次别名自死锁：** `NewNSLock` 在获取命名空间锁前会先规范化路径，因此 `../B/secret` 实际锁定的是桶 `B` 中的目标对象。若同一请求中包含两个指向同一目标的不同穿越别名（如 `../B/secret` 与 `x/../../B/secret`），单节点按序逐个加锁的批量锁会在持有第一把写锁的情况下等待同一对象的第二把写锁，导致请求自身死锁并持续占用目标对象写锁直至 `globalOperationTimeout` 超时。

---

## 五、修复方案及其充分性与必要性 {#fix}

提交 [`a18293d0c`](https://github.com/pgsty/silo/commit/a18293d0c309b93fe9c69f45ed8f44fe558fe01d) 在 `(*erasureServerPools).DeleteObjects`（`cmd/erasure-server-pool.go`）的 `checkDelObjArgs` 循环之后立即分流校验失败的条目（共新增 22 行）：

```go
if slices.ContainsFunc(derrs, func(err error) bool { return err != nil }) {
    valid, at := make([]ObjectToDelete, 0, len(objects)), make([]int, 0, len(objects))
    for i, obj := range objects {
        if derrs[i] == nil {
            valid, at = append(valid, obj), append(at, i)
        }
    }
    if len(valid) > 0 {
        deleted, errs := z.DeleteObjects(ctx, bucket, valid, opts)
        for j, i := range at {
            dobjects[i], derrs[i] = deleted[j], errs[j]
        }
    }
    return dobjects, derrs
}
```

### 为什么该修改既必要又充分 {#sufficient}

1. **在加锁与下盘前统一收口：** 分流点紧跟在 `checkDelObjArgs` 之后，位于 `deleteObjectsInSets`、`multiDeleteLock.GetLock`、元数据查询与存储池并发派发之前，一处覆盖单节点批量锁、分布式单池按集锁与多存储池三种拓扑，以及 S3 批量删除和生命周期过期等全部调用方。
2. **消除跨桶加锁与自死锁：** 未通过 `checkDelObjArgs` 的条目在调用 `NewNSLock` 前即返回，无法锁定其他桶的对象，也不会因同批次重复别名触发自死锁。
3. **复用既有路径校验谓词：** `checkDelObjArgs` 使用的 `hasBadPathComponent` 与单对象 `DELETE`、`PUT`、`GET`、HTTP 查询参数守卫及 `SN-2026-002` 远端盘守卫完全一致。通过该检查的对象名不含 `.` 或 `..` 路径段，经 `pathJoin`（`path.Clean`）处理后只会落在 `<drive>/<bucket>/` 目录内部。代码审查同时核对了生命周期、Batch 批处理、复制、自愈与 `deleteObjectsReconciled` 等全部删除路径，确认不存在其他绕过 `check*Args` 将客户端名称直接传入磁盘删除接口的路径。
4. **递归有界且保持响应下标对齐：** `encodeDirObject` 具有幂等性，且筛选出的 `valid` 切片已全部通过 `checkDelObjArgs`，因此递归调用 `z.DeleteObjects` 不会再次进入错误分支；同批次的合法条目（含 `dir/` 目录对象）按原路径删除，并通过 `at` 索引切片映射回原始位置。

---

## 六、设计取舍与边界说明 {#tradeoffs}

| 方案                                                                    | 收益                                                          | 代价与风险                                                                                                                            | 结论                           |
| :---------------------------------------------------------------------- | :------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------ | :----------------------------- |
| **在 `erasureServerPools.DeleteObjects` 校验后立即分流（`a18293d0c`）** | 22 行代码覆盖全部拓扑、加锁路径与调用方；全合法请求无额外分配 | 单存储池下非法对象名的返回由 `Deleted` 变为 `XMinioInvalidObjectName`                                                                 | **采纳**                       |
| **在 `DeleteMultipleObjectsHandler` 中前置调用 `checkObjectArgs`**      | 在 HTTP 处理器层提前拦截非法名称                              | 对象层拒绝后处理器不会对失败项触发复制、事件或分层清理；且 **`checkObjectArgs` 拒绝尾斜杠，会导致合法的 `dir/` 目录批量删除回归失败** | **否决**                       |
| **在本次热修中同步为本地 `xlStorage` 增加路径包含守卫**                 | 提供贴近文件系统的底层纵深防御                                | 仅修补两个删除方法在 `StorageAPI` 中不对称；全量包装本地调用涉及纠删码读写热路径，回归测试面较大                                      | **作为独立加固项排入常规版本** |
{.wide .expand}

### 边界细节与行为变化 {#nuances}

- **目录对象（`dir/` 与 `../`）的处理：** `encodeDirObject` 在 `checkDelObjArgs` 之前将尾斜杠编码为 `__XLDIR__`（`dir/` 编码为 `dir__XLDIR__`，`../` 编码为 `..__XLDIR__`）。编码后的 `..__XLDIR__` 不含 `..` 路径段，仅作为请求桶内的字面目录对象名处理，不会向上级目录穿越；合法的 `dir/` 批量删除保持不变。
- **正常请求零额外开销：** 当批次内对象名全部合法时，`slices.ContainsFunc` 仅遍历一次全 `nil` 的 `derrs` 切片，不触发切片分配或递归调用。
- **Windows 路径规范化边界（`.. .`）：** 审查中评估了 Windows 下 `.. .`（两个句点、一个空格与一个句点）通过 `hasBadPathComponent` 后是否会被 Win32 规范化裁剪为 `..`。根据微软《File path formats on Windows systems》规范，Win32 先求值 `.` 与 `..` 段，随后才裁剪中间段末尾的单个句点（中间段不裁剪末尾空格），且裁剪后不会二次求值 `..`，因此 `.. .` 作为中间段会保留为 `.. `（桶内普通目录名）。由于 `hasBadPathComponent` 为全站 S3 API 共用且 CI 运行于 Linux，Windows 真机核验作为独立事项跟进，不阻塞本次热修。
- **可观测的接口行为变化：** 单存储池部署下，批量删除中经目录编码后仍未通过 `checkDelObjArgs` 的条目（如含 `.` 或 `..` 路径段、Windows 反斜杠、NUL 字节或非法 UTF-8）不再返回 `<Deleted>`，而是逐条返回 `<Error><Code>XMinioInvalidObjectName</Code></Error>`，与单对象 `DELETE` 及多存储池部署一致。

---

## 升级指引与临时缓解措施 {#remediation}

1. **升级 SILO Server：** 单存储池部署请升级至包含提交 [`a18293d0c`](https://github.com/pgsty/silo/commit/a18293d0c309b93fe9c69f45ed8f44fe558fe01d) 的 `20261109` 后续热修版本（或基于 `a18293d0c` 及之后的 `main` 源码构建）。单独升级 `silo-console` 或 `mcli` 无法修复服务端问题。
2. **升级前临时缓解：** 未修复的单存储池服务端无配置项可关闭该代码路径。完成升级前，请在单存储池集群上收回不可信或半可信多租户主体的 `s3:DeleteObject` 与 `s3:DeleteObjectVersion` 权限（或将不可信租户隔离至独立实例）。运行 [SILO Server 20261026](/zh/blog/release/silo-20261026/) 或 [20261109](/zh/blog/release/silo-20261109/) 的多存储池（`2` 个及以上存储池）集群不受影响。
3. **升级后核查：** 若未修复的单存储池集群此前曾向半可信主体授予开启版本控制桶的删除权限，建议升级后通过 `mcli ls --versions` 检查业务桶，并核查磁盘上 `.minio.sys/buckets/<bucket>/.metadata.bin` 是否存在异常删除标记。

更多信息请参阅[安全公告台账](/zh/about/security-advisories/#sn-2026-020)、[SN-2026-002 内部节点路径包含审计](/zh/blog/security/internode-path-containment/)与[组件版本矩阵](/zh/compatibility/versions/)。

---
title: "SILO Server 20260903 发布前复审"
linkTitle: "Server 20260903 复审"
date: 2026-09-03
author: "冯若航"
summary: >
  对 20260806 之后全部服务端变更的最终对抗性复审：已确认缺陷、修复、否决的简化、必要复杂度、验证证据、明确延期，以及代码 GO 与生产发布之间的区别。
tags: [Design, Review, Security, Compatibility, Release]
weight: 8
draft: false
url: "/zh/blog/design/server-release-readiness/"
---

这是 [SILO 20260903](/zh/blog/release/silo-20260903/) 背后的发布前长期工程记录：为什么不能直接接受早期“所有问题都已解决”的结论，独立复审发现了什么，修复如何收窄，以及复审时距离生产发布还差哪些门禁。链接的发布说明记录了之后的正式交付结果。

> **结论：** `6e112d1856d4f3655f30fc81ee47e9f43d50d8f3` 源码候选在**代码层面可以 GO 到远端复审**；生产发布仍是**有条件 GO**，必须等待远端 CI、Test Release、tag 与构件校验、签名、容器发布及公开 pull 验证完成。<br>
> **基线：** `RELEASE.2026-08-06T00-00-00Z`，提交 `3be10fcc1a44f6620ded0bd303461f9d688cca23`。<br>
> **范围：** SILO Server 行为及其内嵌/锁定的运行时组件。文档、独立 Console、mcli、软件仓库、镜像与线上站点是彼此独立的交付物。<br>
> **发布闭环：** 后续最终源码树 `9b11dc9469e650815b775cb47b039610644f5da4` 在完成下列远端、软件包、provenance、容器与公开下载门禁后，于 2026-09-04 以 [`RELEASE.2026-09-03T13-18-01Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z) 正式发布。本页的有条件结论保留为当时的复审标准，不代表当前仍未发布。

## 为什么需要第二轮审查 {#why-review}

第一轮实现有很强的测试结果，也解决了大多数报告缺陷。但“已经全部就绪”的结论仍然过宽：它把绿灯测试与干净工作树当成了所有安全不变量均已闭合的证明。

对抗性复审换了一组问题：

- 同一不变量能否被另一种合法 wire representation 绕过？
- 预鉴权 fast path 是否仍会做 I/O 或获得状态？
- metadata 存在但加载失败时会怎样？
- 两条各自正确的 read-modify-write path 是否共享同一 serialization boundary？
- request sanitization 是否保留了全部 SigV4 streaming state？
- 验证声明说的是最终树，还是此前某棵树？
- 一个复杂机制是在保护已复现故障，还是只保护假想未来？

这轮审查在第一次“ready”之后继续找到了真实缺陷。正确做法不是推翻全部既有工作，而是把每个结论收窄到具体不变量与具体源码树。

## 分领域复审结果 {#review-result}

| 领域 | 对抗性发现 | 最终解决方案 | 状态 |
| :-- | :-- | :-- | :-- |
| 桶元数据 | 独立配置锁会丢失共享 `.metadata.bin` 记录中的更新（[#102](https://github.com/pgsty/silo/issues/102)） | 一个有界 `metadata.lock` 包围所有整记录 writer、migration、import、adoption、healing；复制只应用变化字段，避免陈旧整记录替换 | 候选已关闭 |
| 桶创建 | `ForceCreate` 与站点 adoption 可能用默认值覆盖既有配置 | 保留既有记录，只更新 creation/adoption 状态；增加 clobber regression test | 候选已关闭 |
| Object Lock | 将 lock 文档字节与一个 canonical XML 比较，会漏掉带 Default Retention rule 的合法配置 | 先 parse Object Lock，再从解析后的 enabled 状态推导 versioning 不变量；验证更新、读回、磁盘重载 | 候选已关闭 |
| 预鉴权 CORS | 任意 path segment 会触发 metadata read 与 cache growth | CORS lookup 只读 resident metadata，不进行 object-layer I/O | 候选已关闭 |
| CORS 启动期 | metadata 尚未初始化时，非驻留名字可能回落全局 CORS | 保留显式 fail-closed startup state | 候选已关闭 |
| CORS 加载失败 | 忘记一个真实桶曾加载失败，会让它与不存在的桶无法区分，使预签名请求落到全局 fallback | 维护有界 failed-bucket set；成功加载、删除、refresh 等路径清除；这些桶保持 fail-closed | 候选已关闭 |
| CORS 恢复 | 按需 `GetConfig` 成功重载最初没有清除 load-failure bit | 最后一行修复 `84e1580a4`，加定向 race 覆盖 | 候选已关闭 |
| 复制信任 | 多个 handler 把客户端可控内部 header 的存在当作特权 | 先鉴权；要求精确 marker 与 `s3:ReplicateObject` / `s3:ReplicateDelete`；用私有 context decision；之后再清洗 | 候选已关闭 |
| Streaming upload | 清洗后的 request clone 起初没有共享原 trailer map | 保留 trailer map，使迟到的 streaming checksum 可见 | 候选已关闭 |
| Snowball | request-wide trust bit 可能在解压 entry 间泄漏 | 每个 entry 独立推导 trust，并在 worker 间保留请求默认值 | 候选已关闭 |
| SSE-C | 零字节读取与 `GetObjectAttributes` 可跳过客户密钥认证 | 要求成功解封 key；真正授权的 replica 走独立例外 | 候选已关闭 |
| 删除授权 | 显式版本删除检查普通 delete action，而不是要求 `s3:DeleteObjectVersion` | 对齐单删与批删授权；复制删除保留 `s3:ReplicateDelete`；保留 auth/audit context | 候选已关闭 |
| 管理授权 | 用户/组状态变更始终检查 enable action | 检查与目标状态匹配的 action | 候选已关闭 |
| Checksum | Multipart/copy 路径漏字段、接受非法组合，或在错误 representation 上计算 | 补齐算法/类型校验、服务端 part 计算、联邦传递、AWS 错误、CopyObject transform 顺序 | 候选已关闭 |
| 发布证据 | 完整验收最初描述的是之后仍发生变化的树 | 分别记录 `ebac0ca73` 的完整验收与当前树的定向门禁 | 证据缺陷已关闭 |

## 定义候选的四条不变量 {#invariants}

### 信任只在鉴权后推导一次 {#trust-invariant}

看起来像内部字段的 header 仍然是客户端输入。请求必须保持原始签名形态，先通过现有 authentication path；随后 handler 才能组合：

1. 唯一且精确的 replication marker；
2. 非匿名、已认证身份；
3. 对目标 resource 的 `s3:ReplicateObject` 或 `s3:ReplicateDelete`；
4. 在更窄的 replica-only 语义中所需的 replica status。

结果存入私有 request context。header stripping 是给旧 consumer 的纵深防御，不是 authority 来源。

顺序很重要，因为 SigV4 可能签了这些 header。鉴权前清洗会让合法复制返回 `SignatureDoesNotMatch`。sanitized clone 还必须共享 request trailer：trailer 在初始 header parse 之后到达，承载 streaming checksum。

完整接收端模型见 [鉴权前不做 I/O，Header 不产生权限](/zh/blog/design/cors-replication-trust/)。

### 共享记录只有一个写边界 {#metadata-invariant}

Policy、lifecycle、SSE、tags、quota、replication、Object Lock、versioning、CORS 是逻辑字段，却是同一 bucket record 的物理成员。每字段 mutex 无法保护整记录 read-modify-write。

选定修复比引入数据库或通用 transaction layer 更小：

```text
acquire metadata.lock
  load or reuse current record
  mutate the requested field
  parse/normalize the complete record
  persist atomically
  publish the in-memory record
release metadata.lock
```

锁不覆盖对象数据 I/O，只限于一次 bucket-metadata 操作。Migration 与 healing 同样参与，因为它们也会替换整条记录。Replication receiver 只 merge 变化字段，避免远端旧 snapshot 擦除无关本地状态。

### 失败是一种状态，不等于不存在 {#cors-failure-invariant}

CORS hot path 必须区分四种状态：

| 状态 | 结果 |
| :-- | :-- |
| Metadata system 尚未初始化 | 不返回 CORS header |
| 已知真实桶，但 metadata load 失败 | 不返回 CORS header |
| Resident bucket 且有桶级 CORS 文档 | 评估该文档 |
| 无 resident metadata，也没有已知失败 | 使用服务端全局 fallback |

第二行解释了为什么 failed-bucket set 在简化审查后仍然保留。预签名 URL 已经通过自身签名获得授权，无需 bucket-policy evaluation；此时 bucket CORS 文档就是 browser-origin boundary。丢掉失败 bit 并使用宽松全局 fallback，会削弱该边界。

集合只由真实 bucket load attempt 产生，因此有界；生命周期通过两个 helper 维护。成功 load、remove、stale-bucket cleanup、refresh、reset、concurrent load 都有测试。

### Object Lock 看语义，不看文本 {#object-lock-invariant}

任何解析有效且 enabled 的 Object Lock 配置都意味着 versioning。XML whitespace、element order 与 Default Retention rule 不改变语义。因此 normalization 必须发生在 parse 之后，而不是将 bytes 与某一个 canonical document 比较。

最终 versioning record 是纯 `Enabled`；suspended state 与 exclude-prefix 扩展和 lock 不变量冲突，会在 update、read-back、reload 时移除。

## 复杂度审计 {#complexity-audit}

发布前审查专门查找 over-design、重复、没有 threat model 的过度防御，以及陈旧兼容 machinery。

### 因保护已复现故障而保留 {#retained}

- **一把 metadata lock：** deterministic cross-type lost-update 测试已经复现数据丢失。
- **CORS tombstone：** 没有 tombstone，站点复制无法区分删除与“从未观察到”。
- **CORS load-failure state：** 预签名 URL 给出了已认证且不经 policy 的具体反例。
- **两级 replication trust：** 普通 replication 与 replica ciphertext/SSE 语义并不使用完全相同的 wire shape。
- **鉴权后清洗：** SigV4 之前清洗会破坏合法签名请求。
- **多池/null-version 对抗测试：** 单池 happy path 无法覆盖它们抓到的状态选择故障。

### 删除或收窄的复杂度 {#removed}

- CORS failure-set mutation 收口到 `noteLoadFailure` 与 `clearLoadFailure`。
- Replication import 只应用变化字段，不复制陈旧的完整记录。
- 删除过期 encryption helper、死 event-target function 与废弃 handler branch。
- Compatibility guard 不再枚举每个 exported source symbol，只保护真实 served route 与冻结的 wire/config surface。
- 删除旧 `wait_pipe` lint exemption；用 `gomodguard_v2` 替代弃用配置。
- Dynamic timeout 测试不再从 parallel package 调用全局 `rand.Seed`。
- 服务端从临时 `silo-go` 分叉回到已审查的上游兼容 `minio-go` revision。

### 刻意没有引入 {#not-introduced}

- 没有通用 metadata transaction framework；
- 没有第二套 CORS cache 或无界 negative cache；
- 没有新增公开“trusted replication”请求 header；
- 没有让服务端发布依赖未来 Console 或文档发布的跨仓库 gate；
- 没有把半套 conditional-delete contract 塞进候选；
- 没有在缺少专用 convergence test 时重写全部继承的 site-replication register。

## 延期事项，以及为什么严重度不同 {#deferrals}

| 事项 | 分类 | 发布决定 |
| :-- | :-- | :-- |
| 条件删除 [#10](https://github.com/pgsty/silo/issues/10) | 继承的 S3 缺失功能；只对假定服务器会执行未支持 `If-Match` / per-object ETag 的调用方危险 | 显著记录；不合并不完整 PR，也不发布只有单对象的一半合同 |
| 多站点配置删除 [#77](https://github.com/pgsty/silo/issues/77) | policy/SSE/tags/quota 的继承收敛缺陷；CORS 使用独立已修 register | 不是单站点 blocker；依赖这些多站点删除的用户需要附加部署条件 |
| `ListMultipartUploads` [#79](https://github.com/pgsty/silo/issues/79) | 继承的 listing conformance gap | 已知问题；不是普通 multipart workflow 的数据完整性 blocker |
| 联邦 `CopyObject` [#99](https://github.com/pgsty/silo/issues/99)、[#100](https://github.com/pgsty/silo/issues/100) | 旧后端 checksum/inline-object 缺口 | 阻塞受影响 feature 的使用，不阻塞通用 server 发布 |
| ILM relocation PR #60 与 broad SSE issue #61 | 新能力请求 | 不属于本版本安全边界 |

“继承”不等于无害，而是说明缺陷不是本变更集引入，应按公开 release contract 评估。若某个部署依赖受影响路径，即使通用版本仍是 conditional GO，该部署也有自己的 stop condition。

## 证据 {#evidence}

### 完整验收树 {#full-acceptance}

完整本地验收对应 `ebac0ca73bbf251b070bb6df4d8005015841f901`：

- 完整 `cmd` 与 `internal` 套件；
- 完整 `cmd` race：365.448 秒，通过；
- lint：0 issue；
- rebrand/compatibility 与 generated-file guard；
- `govulncheck` 无 reachable vulnerability；
- 六种 `make verify` 部署形态：174 PASS / 0 FAIL。

前两次 `make verify` 在获取 mcli 时遇到环境/准备失败，并非测试失败。成功运行使用本地 checksum-pinned mcli，保留到 GitHub 的 outbound proxy，对 localhost 绕过代理，并把 GNU userland tool 放在 `PATH` 前部。这个区别属于证据，不应隐藏。

### 验收后的候选 {#post-acceptance}

完整运行之后唯一代码修改是 `84e1580a4`：metadata 按需重载成功后清除一个 CORS failure-state bit。候选 merge 不改代码；`6e112d185` 只修改 Helm 发布元数据与文档。在最终候选上以下门禁通过：

- `git diff --check`；
- CORS 与 Object Lock 定向 `go test -race`；
- rebrand guard；
- generated-file check；
- lint 0 issue。
- Helm lint、默认与可选 render、chart package，以及七资源旧版升级身份守卫。

证据强度与一行状态迁移修复相称，但推送后的树仍必须运行远端 CI 与 release workflow。

## Go、No-Go 与剩余门禁归属 {#decision}

### 代码结论：GO {#code-go}

两轮复审确认的代码缺陷在候选中均已解决。修复落在对应不变量所在层；保留的复杂度都有已复现反例支撑。

### 生产结论：有条件 GO {#production-conditional-go}

以下全部成为事实前，不能把服务端称为“已发布”：

1. 候选提交推送并完成 review；
2. 远端 CI 与 Test Release 在 pushed head 通过；
3. 预定 tag 指向已审查的 chart 7.0.2、Server 0903、Client 0903 release tree；
4. Draft artifact、checksum、SBOM、attestation、签名 RPM 全部通过校验；
5. finalize 与 Docker release 发布 classic、distroless 两种镜像；
6. 匿名下载与 pull 测试通过；
7. 发布说明用 tagged fact 更新，文档站部署完成。

第 1～6 项任一失败都是 release blocker；本地绿灯无法替代它们。

### 部署特定停止条件 {#deployment-conditions}

即使版本成功发布，以下条件无法满足的运维方也应延后升级：

- 无法在同一维护操作中更新分布式集群全部节点；
- 无法在使用桶级 CORS 前更新站点复制组全部成员；
- 无法调整 `s3:DeleteObjectVersion` 与 status-action separation 相关 IAM 策略；
- 业务依赖 #10、#77、#79、#99 或 #100 路径，却不能显式接受对应已知限制。

复审时的最终结论有意比“所有问题都已修好”更窄：**经审候选已经可以进入发布机器；剩余限制全部显式；生产发布由可验证构件把关，而不是由信心把关。** 上述门禁后来已为链接的正式版本闭环；部署特定条件仍然有效。

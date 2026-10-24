---
title: "副本元数据归一化：可信复制不得重新注入什么"
linkTitle: "副本元数据归一化"
date: 2026-09-16
lastmod: 2026-09-16
author: "冯若航"
summary: >
  PR #194（修复 4fcdf37ce）的决策记录：可信复制 COPY 经由宽松路径重新提取原始请求元数据，使仅传输用的 aws-chunked 编码与 GHSA 脱敏的用户元数据回流到已存储对象中。涵盖期望的编码映射、Snowball 行为变化、为何升级不会修复存量对象，以及存量元数据修复提案的状态。
tags: [设计, 复制, S3, 评审]
weight: 9
draft: false
url: "/zh/blog/design/replica-metadata-normalization/"
---

随 [SILO Server 20260916](/zh/blog/release/silo-20260916/)（`40220bd836cbd066ca424fa4dc5dbb90057fb55a`）发布的 [PR #194](https://github.com/pgsty/silo/pull/194)（修复提交 [`4fcdf37ce`](https://github.com/pgsty/silo/commit/4fcdf37ce)，合并提交 [`9f3037e941`](https://github.com/pgsty/silo/commit/9f3037e941a49ab4cd8a0eed7c0f01083fbe4bbe)，采纳并保留 Mikhail Khadarenka 在 [PR #187](https://github.com/pgsty/silo/pull/187) 中的实现），修复了可信复制接收端在恢复副本内部元数据时重新调用宽松请求头提取器、导致仅用于传输的 `aws-chunked` `Content-Encoding` 标记与 GHSA 已脱敏的用户元数据重新回流至落盘对象中的回归缺陷。

## 问题根因 {#problem}

普通 S3 `PUT` 路径在落盘前会对请求元数据执行归一化处理：从 `Content-Encoding` 中剥离仅用于流式传输分帧的 `aws-chunked` 标记，并删除 [GHSA-76wf-9vgp-pj7w](https://github.com/google/security-research/security/advisories/GHSA-76wf-9vgp-pj7w) 缓解措施要求剔除的 `X-Amz-Meta-X-Amz-Unencrypted-Content-Length` 与 `X-Amz-Meta-X-Amz-Unencrypted-Content-Md5` 用户元数据键。

然而，当可信复制接收端为副本写入恢复内部复制元数据时，却以开启“允许复制（`allowReplication`）”标志的方式重新运行了**同一个通用宽松提取器**——把原始 HTTP 请求中的全部标准请求头与所有 `X-Amz-Meta-*` 用户元数据重新覆盖回已归一化的元数据映射表中。结果在可信副本写入路径上，服务端可能落盘并在后续 `GET`/`HEAD` 响应中返回：

- `Content-Encoding: aws-chunked`（按 AWS SigV4 流式传输规范绝不能作为对象元数据持久化的纯传输编码），或未经拆分的 `aws-chunked,gzip` 整串（正确落盘值应为 `gzip`）；
- 上述两个在普通写入中已被 GHSA 缓解措施剔除的 `X-Amz-Meta-X-Amz-Unencrypted-Content-*` 用户元数据键；
- 对于未携带独立 PAX 头的 Snowball 归档条目：意外继承外层归档请求的 `Content-Type`、`Cache-Control`、`Expires` 与用户元数据。

底层对象数据字节本身并未受损，但持久化的 `xl.meta` 元数据被污染。该回归由 [`56fa63bfd`](https://github.com/pgsty/silo/commit/56fa63bfd)（2026-04-15，针对 [CVE-2026-34204](/zh/blog/security/cve-2026-34204/) 的复制请求头信任边界加固）引入——该提交的认证与信任边界保护本身完全正确并予以保留。

## 修复方案 {#fix}

提交 [`4fcdf37ce`](https://github.com/pgsty/silo/commit/4fcdf37ce) 仅修改 `cmd/handler-utils.go`，删除了布尔双模式辅助函数，将普通请求头提取与副本内部字段恢复彻底拆离：

- 普通提取器无条件跳过所有复制专用内部键；
- 新增专用副本提取器（`extractReplicationMetadata`），仅遍历复制头到内部头的映射表，且**仅**恢复 6 个复制域专用字段：
  1. SSE-C 密封密钥材料（`x-minio-internal-server-side-encryption-ssec-key`），
  2. SSE-C 密封算法（`x-minio-internal-server-side-encryption-ssec-seal-algorithm`），
  3. SSE-C 初始向量 IV（`x-minio-internal-server-side-encryption-ssec-iv`），
  4. 加密多段上传标记（`x-minio-internal-encrypted-multipart`，空值标记按键存在性生效），
  5. 实际逻辑对象大小（`x-minio-internal-actual-size`），
  6. SSE-C 校验和恒等映射；
- 副本提取器绝不重新读取标准受支持请求头（如 `Content-Encoding`、`Content-Type` 等）或 `X-Amz-Meta-*` 用户元数据。

修复后各请求编码对应的落盘结果如下：

| 请求 `Content-Encoding` | 落盘存储的 `Content-Encoding` |
| :-- | :-- |
| `aws-chunked` | *（无）* |
| `aws-chunked,gzip` | `gzip` |
| `gzip` | `gzip` |

注：`aws-chunked, gzip`（逗号后带空格）仍存储带前导空格的 ` gzip`，`gzip, aws-chunked` 仍存储整串；这两者属于普通 `PUT` 路径既有的解析现状，由测试按现状固定断言。

## 运维可见变化 {#behavior}

- **可信 Snowball 归档条目：** 可信 Snowball 条目不再继承外层归档请求的普通元数据。当条目不含 PAX 记录时，不再继承外层 `Content-Type`、`Cache-Control`、`Expires` 与用户元数据；当含有 PAX 记录时，也不再继承条目自身未声明的外层字段。条目自身的 `minio.metadata.*` 依然生效，6 个复制域专用字段仍作用于已授权条目，归档的存储类型（Storage Class）仍正常继承。（仓库内置批量生产端调用 `PutObjectsSnowball` 时虽发送自动解压标记，但外层请求并不标记为可信副本，因此未受该继承路径影响。）
- **GHSA 脱敏键：** 在副本元数据恢复时不再写回两个未加密长度/MD5 元数据键，与普通 `PUT` 行为完全一致。
- **不变边界：** 身份认证、权限门禁与复制信任语义保持不变；普通 `PUT` 提取路径逐字节等价。

## 为什么升级服务端不会自动修复存量污染对象 {#existing}

升级至 [SILO Server 20260916](/zh/blog/release/silo-20260916/) 会立即阻断新写入对象的元数据污染，但不会后台扫描或改写磁盘上的存量对象。运维中需注意两点影响：

1. **权威源端仍被污染时的反复同步：** 若**权威源对象**仍带有被污染的元数据（例如来自早期的双向复制回流），在与已归一化的目标副本比对时会持续检测到元数据差异，导致在自愈（heal）或重新同步（resync）中反复触发元数据复制。务必先修复权威源端的对象版本，再让下游副本收敛。
2. **普通 S3 自 `COPY` 的局限性：** 普通 S3 向自身发起 `CopyObject` 并非通用的存量修复 API，因为它在版本化桶中会生成新版本或更新时间戳，而不会原地改写指定历史 `versionId` 的元数据。

[只读副本元数据审计手册](/zh/operations/replication/replica-metadata-audit/)提供了可执行的存量清单扫描工具与分类规则，用于在改动前盘点受影响的对象版本。

### 存量元数据修复方案设计原则 {#remediation}

针对审计手册识别出的历史受污染对象，制定修复流程时应遵循以下安全边界：

- 构建包含所有非当前历史版本的完整清单（不能仅扫描最新版本）；
- 通过比对可信源版本或独立校验和来核验真实内容编码——绝不凭被污染的响应头猜测，也绝不因为头部写有 `gzip` 就盲目执行解压重传；
- 优先处理权威源端的精确版本，再让副本自动收敛；保留不可变清单与元数据备份，在小批量验证并演练回滚后再推广；
- 修复操作必须保持版本 ID 与当前版本关系、Object Lock 保留期与法务锁定、对象标签、复制状态及加密上下文不变；对缺乏受支持修复路径的对象保持原状，严禁直接手动编辑磁盘上的 `xl.meta` 文件。

## 已知范围边界 {#limits}

- 浏览器 `POST` 表单上传路径（`cmd/bucket-handlers.go`）直接调用底层提取器，原本即未对 `aws-chunked` 执行编码归一化；该路径不属于复制接收端，作为独立跟进项记录。

## 验证 {#verification}

回归测试（`TestExtractReplicationMetadata*`、`TestAPIReplicaContentEncoding`、`TestAPISnowballReplicaContentEncoding` 以及开启 `-race` 的复制信任与 SSE-C 往返测试）在真实单盘与 16 盘纠删码后端上覆盖了映射表、6 个复制恢复字段与普通路径等价性（共 64 个 HTTP 叶级用例：44 个对照通过，20 个缺陷用例在修复前失败、修复后通过，外加 16 个辅助函数单元测试）。

升级摘要见[组件版本矩阵](/zh/compatibility/versions/#september-reliability)；姊妹修复见[复制标签排序](/zh/blog/design/replicated-tag-ordering/)。相关设计记录：[复制标签排序](/zh/blog/design/replicated-tag-ordering/) · [副本元数据归一化](/zh/blog/design/replica-metadata-normalization/) · [请求头超时防护](/zh/blog/design/request-header-timeouts/) · [副本元数据审计手册](/zh/operations/replication/replica-metadata-audit/)。

---
title: "SILO 下一版本：发布前加固说明"
linkTitle: "SILO 下一版加固"
date: 2026-08-29
lastmod: 2026-08-29
author: "冯若航"
description: "SILO 20260806 后续版本的兼容性、完整性、站点复制、客户端与发布管线草案。"
tags: [发布, 草稿, 兼容性, Checksum, S3]
weight: 9
draft: true
url: "/zh/blog/release/silo-next-hardening/"
---

> **草稿——目前没有对应的 release tag、软件包或镜像。** 本页记录
> `RELEASE.2026-08-06T00-00-00Z` 后续版本在发布前验证的代码与兼容边界。
> 只有源码 PR、远端 CI 与最终候选验收完成后，才会填写最终版本、提交与产物摘要。

## 完整性与加密修复 {#integrity}

- null version 的 metadata-only `CopyObject` 现在按对象层实际写入的字节记录压缩
  metadata。压缩两个方向与 SSE-C 换钥均有覆盖；原故障既可能报
  `s2: corrupt input`，也可能静默返回被截短的对象。
- 零字节 SSE-C 读取虽然不会创建 decryptor，仍会验证调用方提供的客户密钥。
  GET、CopyObject 与 UploadPartCopy 现在与非空对象一样对错误密钥返回 403，
  同时保持内部无解密、replication、restore、range 与 precondition 顺序。
- `GetObjectAttributes` 在返回明文对象大小或已完成分段布局前会解封 SSE-C 密钥；
  零字节与非空对象的正确、错误、缺失密钥均有测试。
- CopyObject 重新加密时使用目标密钥解密 checksum metadata；显式 multipart
  checksum type 也不能再缺少对应值而被接受。

## Checksum 兼容边界 {#checksum}

SILO 实现 CRC32、CRC32C、CRC64NVME、SHA1 与 SHA256。请求声明 MD5、SHA512、
XXHASH64、XXHASH3、XXHASH128 或未知的 `x-amz-checksum-*` 值/trailer 时，
现在明确返回 400 `InvalidArgument`，不再返回 200 却静默丢弃完整性断言。
该规则覆盖 PutObject、CreateMultipartUpload、UploadPart、CopyObject 与
UploadPartCopy。

CRC64NVME 只允许整对象 checksum；CRC64NVME + `COMPOSITE` 会被拒绝，
不再静默规范化。跨厂商复制若携带未支持算法，将显式失败，必须改用支持算法重试。
详见 [checksum 校验设计](/zh/blog/design/checksum-verify/)。

## CORS 与桶 metadata {#cors-metadata}

- per-bucket CORS 的复制、tombstone、严格 XML/wire 校验、status、heal 与恢复
  已合并，并由两篇 CORS 设计文档记录。
- 没有 `Origin` 的请求会完全跳过 per-bucket CORS metadata。Admin、Console、
  health 与普通非浏览器流量不再在鉴权前重复执行失败的 metadata 读取。
  运行故障与非法文档仍 fail-closed；不存在或未配置 CORS 的桶继续走全局 CORS。
- 旧开发版本接受的非法 CORS 可通过合法 `PUT ?cors` 或 `DELETE ?cors` 修复；
  修复前不要修改该桶的其他 metadata。

## 站点复制与 Object Lock {#site-replication}

- live、initial-sync 与 heal 事件统一在 `ObjectLockConfig` 字段携带 Object Lock XML；
  新 receiver 保留对旧 `Tags` 字段的滚动升级兼容。
- 接管同名既有桶时保留完整 Object Lock retention 与已启用的自定义 versioning
  规则（含 excluded prefixes）。缺失配置会初始化；Suspended 或非法 versioning
  会被明确启用。
- 每站点 totals 按该站点自己的有效 payload 统计，不再使用累计计数。Bucket policy
  与 quota 统计得到补齐；非法字段输出有界诊断，且不会吞掉同站点的其他桶统计。
  升级后，统计数可能下降或移动到真正持有配置的站点，这是修正后的结果。
  Status 中的 `Has*` 现在表示“存在且有效”；空 quota 按未配置处理，而不是已复制配置。

Policy、Tags、SSE、Quota、Versioning、Object Lock 的完整 source-time/tombstone
收敛仍需 peer capability 设计后分阶段交付。本版本不得宣称所有继承 metadata
类型在任意延迟事件与混合版本下都能完全收敛。

## MCLI 与镜像边界 {#mcli}

客户端源码拆为四个独立审查单元：

- 只读 `mcli checksum verify`，含可靠的非 TTY JSON Lines，以及明确的
  quiet/report/退出码语义；
- policy 写入命令严格校验，同时继续宽容读取历史策略；
- 空 `mcli pipe` 改用普通 PUT，其 ETag 从单段 multipart 形式变为标准空对象 MD5；
- 同 tag 可幂等重试的 Release workflow。

只有新的不可移动 MCLI release 真实存在，且 `Dockerfile.goreleaser` 钉住其
amd64/arm64 资产真实摘要后，Server 镜像才可以承诺内置 checksum audit 命令。
`mc` 兼容别名保持不变。

## 安全与鉴权兼容性 {#authorization}

- Group enable/disable 按目标状态选择鉴权动作；只有 enable 权限的主体不能再
  disable group，反之亦然。
- 新版 MCLI 的 policy 写入拒绝未知字段、裸 ARN、Resource/NotResource 冲突、
  空 Statement，以及 named policy 缺失 Version；既有 stored/session policy
  仍按历史兼容规则读取。
- config environment file 能保留 named target 与更广的合法环境变量名。
  `silo-pkg` 只把精确 `env://` / `env+tls://` 视为远程引用，`envreview`
  等普通值保持字面含义。

## 发布管线 {#release-pipeline}

MCLI 与 Server release job 都按解析后的 tag 串行化、验证 tag→HEAD、拒绝 published
或重复状态，并只整体替换一个尚未 finalize 的 Draft。Server build lane 检测到
finalize lane 的 GPG provenance marker 后会拒绝替换，重试不会把已签名 RPM 的
SBOM/attestation 悄悄退回未签名字节版本。

发布前仍必须完成受控 Draft/retry 验收：只剩一个 Draft、每个资产只有一份、
finalized Draft 拒绝重建、published release 不可覆盖。Tag 不可移动，也绝不改写。

## 明确延期 {#deferred}

- 所有继承 site-replication metadata 类型的 source-time/tombstone 完整收敛，
  等待混合版本 capability channel；
- `ListMultipartUploads` 的 prefix/delimiter/pagination 支持，该问题需要重构
  哈希 multipart 索引与内存缓存；
- 五种新 checksum 算法的持久化支持，该工作需要单独的磁盘格式与滚动升级设计。

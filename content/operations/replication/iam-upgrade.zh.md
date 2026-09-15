---
title: "IAM 升级与恢复"
description: "协调 IAM 撤销机制升级，保留完整删除历史，并演练备份恢复。"
url: "/zh/operations/replication/iam-upgrade/"
weight: 25
icon: fa-solid fa-user-shield
---

[Server #191](https://github.com/pgsty/silo/pull/191) 与
[#192](https://github.com/pgsty/silo/pull/192) 持久化删除修订及父身份撤销边界，防止延迟的站点事件恢复已撤销身份和旧授权。
所有参与服务器必须协调升级，包括没有配置站点复制、但共享 IAM 后端的节点。不支持共享后端的新旧节点混用，也不支持滚动降级。

**发布状态：** 修复已进入[九月源码基线](/zh/compatibility/versions/#september-reliability)，尚未进入 Server 20260903。
本页为包含这些修复的构建准备操作流程。新旧版本、对象存储与 etcd 后端的恢复演练仍由
[#200](https://github.com/pgsty/silo/issues/200) 跟踪；文档发布不代表生产升级已经通过演练。

## 准备维护窗口 {#prepare}

列出所有节点、站点、共享 IAM 后端、离线节点和备份。记录原版本与候选版本的 Server SHA、二进制校验值或镜像摘要、
部署配置、root 凭据来源、外部身份提供方设置及 KMS 依赖。按[组件版本表](/zh/compatibility/versions/)选择维护组件组合；
升级独立 Console 不会替换 Server 内嵌的 Console。

使用已安全配置的 `mcli` 别名。以下命令只读取状态，应逐站点执行并私下保存输出，使用实际别名替换 `site-a`。
共享验收材料中不得包含凭据，也不要开启 HTTP 调试日志。

```bash
umask 077
mkdir -p iam-upgrade-evidence
mcli --version > iam-upgrade-evidence/client.txt
mcli --json admin info site-a > iam-upgrade-evidence/site-a-info.jsonl
mcli --json admin replicate status site-a > iam-upgrade-evidence/site-a-replication.jsonl
mcli ready site-a
```

复制状态命令适用于已配置站点复制的部署。就绪检查本身不能证明 IAM 正确。
逐节点检查时钟同步，例如在由 chrony 管理的 Linux 主机执行 `chronyc tracking`，并检查 IAM 加载和复制错误。
升级前先解决时钟漂移：修订排序使用时间戳，受信节点发来的未来时间戳删除可能使后续较旧更新被拒绝，直到使用更新的修订。

暂停 IAM 管理、凭据签发及相关自动化。隔离状态不明的离线节点，防止旧二进制自动重启，为协调停机排空应用流量。
准备已撤销身份、曾重建的父身份及需重新签发凭据的清单。用户记录缺失不能帮助系统重建已经丢失的删除历史。

**停止条件：** 任何参与节点、后端、备份、必要密钥、未知离线节点或回滚流程尚未核实。
不要为了查看旧快照内容，就把它接回正在运行的复制集群。

## 保存完整恢复点 {#backup}

最终备份前，停止共享各后端的所有 SILO 进程。systemd 部署使用实际服务单元，并逐节点确认已停止；
由 Operator 管理的部署应使用经过演练的维护流程，阻止控制器自动重启旧 Pod。

```bash
SILO_UNIT='silo.service' # 替换为实际安装的服务单元名
sudo systemctl stop "$SILO_UNIT"
systemctl is-active "$SILO_UNIT" # 预期 inactive；此时非零退出码正常
```

| 后端 | 必须保存的恢复材料 | 继续前的核验 |
| --- | --- | --- |
| 对象存储 | 一致、可恢复的完整 IAM 存储，包含修订、删除记录和父身份撤销边界。使用经过演练的完整存储快照或备份流程，保留所需 pool、set、磁盘映射。 | 在拓扑匹配的隔离克隆中恢复并确认 IAM 加载正常。仅复制可见用户目录或一块纠删码磁盘不够。 |
| etcd | 完整 etcd 快照、成员和拓扑配置、证书与认证材料，以及 SILO 的 endpoint、prefix 和加密配置。 | 校验快照，按对应 etcd 版本的流程恢复到隔离集群。不要覆盖承载其他工作负载的共享 etcd。 |
| 两者共同要求 | 精确二进制或镜像、部署配置、root 密钥引用、KMS/密钥恢复材料，以及备份后的撤销和变更记录。 | 独立验证所需密钥可用，不依赖即将替换的集群。机密材料与评审日志分开保管。 |

etcd 示例使用部署已有的 TLS 认证配置，以及适配该版本的 `etcdctl`/`etcdutl`，参阅 [etcd 恢复指南](https://etcd.io/docs/v3.6/op-guide/recovery/)。这里只执行备份和校验，不恢复运行中的集群：

```bash
etcdctl --endpoints="$ETCD_ENDPOINT" snapshot save iam-upgrade-evidence/etcd.db
etcdutl snapshot status iam-upgrade-evidence/etcd.db --write-out=json
```

在线 `mcli admin cluster iam export` 导出可用的活跃记录，但遗漏删除历史，**不能**作为此次升级的恢复点。
快照校验值只证明文件身份，不能证明恢复与撤销检查有效。分别记录备份时间、范围、校验值及克隆恢复成功的证据。

## 升级与核验 {#upgrade}

1. 替换每个共享后端上**所有已停止节点**的二进制或镜像，只启动已升级节点。
   保持旧节点和未知节点隔离，完成所有站点的协调升级后，才能依赖新的撤销保证。
2. 重新执行 `mcli --json admin info site-a`、`mcli ready site-a` 和
   `mcli --json admin replicate status site-a`，确认每个进程实际版本、IAM 加载及站点通信正常。
3. 检查 IAM 修订数量、修复失败和最近成功修复时间等指标。错误计数没有增加，不能单独证明凭据已撤销。
   后台修复定期执行，其间隔不是收敛时间承诺。
4. 在每个站点，使用专用验证别名读取同一个已存在对象。旧撤销凭据必须被授权检查拒绝；刻意重新签发且具备所需权限的凭据必须成功。
   超时、5xx 或对象不存在均不能视为有效验证。记录错误码、站点和凭据标签，不记录密钥。

   ```bash
   mcli --json stat --no-list revoked-canary/upgrade-canary/probe
   mcli --json stat --no-list reissued-canary/upgrade-canary/probe
   ```

5. 为重建的父身份重新签发服务账户和 STS 凭据。旧凭据缺少父身份撤销后要求的签名边界；
   没有保留撤销历史的父身份维持既有凭据行为。只授予当前明确需要的权限。
6. 对仍持有旧记录的站点显式调和升级前已知的删除。使用已确认的状态重建陈旧离线节点，再接回集群。
   节点重启、复制追平后，重复凭据检查。

管理员覆盖内置策略后再删除该覆盖，会留下持久化删除记录；重新加载不会再自动创建该策略。
如果需要恢复，应显式执行策略创建。离线期间对旧式组成员关系的普通删除，仍不在父身份持久化删除保证的覆盖范围内。

只有版本身份、后端恢复、IAM 加载、复制和两类凭据检查都通过后，才恢复访问。
如果陈旧凭据仍能成功，保持相关站点隔离并调查；反复重启直到健康检查变绿不能解决授权问题。

## 回滚与恢复 {#rollback}

先停止并隔离受影响站点，记录选定恢复点之后的所有 IAM 变更和撤销。
将完整且兼容的后端恢复到隔离环境，配套恢复配置、密钥和二进制；不要让旧软件直接启动在已被新版修改的后端上。

较旧备份可能恢复备份后已撤销的凭据。重新开放恢复后的系统之前，重放撤销清单，或轮换受影响身份的密钥。
如果变更记录不完整，在受影响范围调和完毕前保持隔离。不要删除墓碑、截断修订历史或只导入活跃记录来使旧版启动。

## 必须保留的演练记录 {#rehearsal}

对**每一种**支持的后端，使用隔离的新旧版本、多进程站点，记录精确二进制身份和实际备份、恢复命令。
覆盖节点断连期间删除、旧事件延迟重放、同名身份有意重建与凭据重签；重启、完整恢复后重复验证，
并测试回滚到删除发生之前的恢复点。调和后，旧凭据应保持拒绝，预期的新凭据应可用。

[#192](https://github.com/pgsty/silo/pull/192) 中的源码回归证据支持协议实现；本演练补充部署拓扑、备份完整性、重启与操作恢复证据。
将脱敏观察结果关联到 [#200](https://github.com/pgsty/silo/issues/200)，最终制品验收和真实生产升级分别记录。

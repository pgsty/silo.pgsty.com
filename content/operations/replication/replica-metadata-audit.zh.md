---
title: "历史复制状态检查"
description: "逐版本检查历史 Content-Encoding，准备范围明确、可验证的存量修复。"
url: "/zh/operations/replication/replica-metadata-audit/"
weight: 26
icon: fa-solid fa-magnifying-glass
---

升级到包含[九月复制修复](/zh/compatibility/versions/#september-reliability)的版本可以防止新错误，
但不会改写旧 Content-Encoding、重建丢失的标签，也不能证明历史删除标记清除任务已经收敛。
[#201](https://github.com/pgsty/silo/issues/201) 跟踪存量检查与恢复准备；此次评审尚未确认任何受影响的生产部署。

## 逐版本只读清单 {#inventory}

优先检查 [#194](https://github.com/pgsty/silo/pull/194) 涉及的、被存入 Content-Encoding 的传输 token `aws-chunked`。
权威站点和副本站点都应检查**所有版本**。只检查当前对象会漏掉历史版本，普通 COPY 也可能保留来源的错误元数据。

下载并检查[只读清单脚本](/tools/replica-metadata-audit.py)。它使用 Python 3 与 boto3，
只调用 `ListObjectVersions` 和精确版本的 `HeadObject`，输出 JSON Lines。
它不读取正文、不写对象、不编辑存储文件，也不收集凭据。
使用安全配置的 AWS profile，为目标范围授予 `s3:ListBucketVersions` 与 `s3:GetObjectVersion` 只读权限；
该 profile 与 `mcli` 别名独立。需要检查 Object Lock 的部署还应配置相应只读权限。

下载脚本及其[SHA-256 文件](/tools/replica-metadata-audit.py.sha256)，先验证再执行。此版本摘要为 `ccc9d035809b2b41157b4a3f1d35a21108ae4b3af2836e99416a1d2eec1efef2`。

```bash
curl --fail --location --output replica-metadata-audit.py https://silo.pgsty.com/tools/replica-metadata-audit.py
curl --fail --location --output replica-metadata-audit.py.sha256 https://silo.pgsty.com/tools/replica-metadata-audit.py.sha256
shasum -a 256 --check replica-metadata-audit.py.sha256
```

```bash
umask 077
python3 -m venv audit-venv
audit-venv/bin/python -m pip install boto3
audit-venv/bin/python -m pip freeze > audit-requirements.txt
audit-venv/bin/python replica-metadata-audit.py \
  --profile silo-readonly --endpoint-url https://silo.example.com \
  --site site-a --bucket example-bucket --prefix 'review-scope/' \
  > site-a-inventory.jsonl
```

随清单保存脚本修订或校验值、客户端依赖版本、Server 身份、桶配置、所选前缀和起止时间。
空前缀覆盖整个桶；对每个相关桶和站点分别执行。每个数据版本需要一次 HEAD，应先从小范围前缀开始，根据部署负载安排扫描。
列表不是原子快照，任何后续修复前应暂停相关变更，或比较重复清单。

最后一条 `summary` 必须包含 `listing_complete: true`。退出码 `0` 表示扫描完成且没有待核查记录，
**不表示没有发现错误头部**；`2` 表示存在待核查记录，`1` 表示列表失败。
中断或其他异常导致没有完整 summary 时，该清单均不完整。

| 分类 | 含义与后续动作 |
| --- | --- |
| `confirmed-header` | HEAD 返回格式正常且包含精确 `aws-chunked` token 的编码列表。建议值仅移除此 token，仍须核验原始字节和受支持的修复操作。 |
| `ambiguous` | HEAD 失败、LIST/HEAD 身份或状态变化，或编码 token 格式异常、重复、拼写不规范。人工核查，不能把 HEAD 失败当成空头部成功。 |
| `unaffected-header` | 本次成功的精确版本 HEAD 不含该传输 token。不代表历史标签、清除任务、正文完整性或其他版本正常。 |
| `delete-marker` | 列表中的删除标记身份，留待独立清除分析；没有需要规范化的正文。 |

检查按 token 匹配：`gzip, aws-chunked` 是候选，`my-aws-chunked` 不是该传输 token。
混合编码保留其他 token 的顺序，大小写变体及重复 token 留给人工核查。
缺少密钥的 SSE-C 版本可能 HEAD 失败，并保持待核查；本工具不接受 SSE-C 密钥。
这些记录应使用批准的、支持密钥的只读流程检查，密钥不能写入报告或命令历史。

## 清单与私密证据 {#manifest}

脚本保存精确 bucket/key/version、列表时间/ETag/大小、原始及建议 Content-Encoding、元数据指纹，以及可读的复制、加密和 Object Lock 字段。
不导出用户元数据值和 KMS 密钥标识。对象名和版本 ID 仍可能敏感，完整清单私下保管，共享报告使用稳定的替代标识。

```json
{"site":"site-a","bucket":"redacted-bucket","key":"redacted-key-001","version_id":"redacted-version-002","classification":"confirmed-header","content_encoding":"gzip, aws-chunked","proposed_content_encoding":"gzip"}
```

这是格式示例，并非已发现的生产对象。批准任何写入前，补齐私密记录中的可信来源和版本关系、完整普通/用户元数据、
精确版本标签、保留期/法律保留、SSE 模式和密钥可用性、独立原始字节校验值及复制状态。
缺失字段应视为未知，直到获得相应的授权读取结果。指纹可以检测差异，但不能用于恢复被省略的元数据。

读取原始字节时禁用客户端 Content-Encoding 自动解压，与可信来源版本或独立的已知校验值比较。
真正的 gzip 字节应原样保留，不重新压缩。ETag 不是通用内容校验值，尤其对于分片或加密对象。
来源缺失、受污染或无法信任时，该对象继续保持未解决。

## 选择并演练修复 {#repair}

1. 先确定权威精确版本，再确认副本。多向复制须比较所有参与来源。
   仍受污染的来源可能使后续 heal/resync 再次选择元数据复制；这不等于已经证明存在持续重试热循环。
2. 形成逐版本的前后变更清单，只移除已确认的传输 token，保留原始字节、实际编码、用户元数据、标签、Object Lock 和加密要求。
3. 在版本控制、Object Lock、SSE 和复制配置相同的隔离克隆中演练所选受支持操作。
   普通自 COPY 可能创建新版本、改变修改时间和复制排序，不能当作通用的原地元数据修复 API。
   必须创建替代版本时，明确版本身份变化和调用方影响。没有受支持的安全操作时，保持未解决，不编辑 `xl.meta` 或内部磁盘文件。
   逐一核实目标站点的加密配置和密钥可用性；来源已加密，不能单独证明副本也以加密方式存储。
   每次重启后，在所有服务进程及复制目标上使用指定的写入/读取探针，再执行 COPY 或回退。
   健康检查和读取成功时，写入法定人数仍可能尚未就绪。
4. 真正写入前，在选定的写入协调流程中重新核对精确版本、ETag、大小、元数据指纹、时间戳、标签和锁状态。
   先读后写本身不能消除竞争，元数据改变也可能保持 ETag 不变。冲突项跳过并重新检查。
5. 在克隆中核对精确版本 HEAD、原始字节校验值不变、所有保留元数据/锁及副本最终收敛，
   并演练重启、旧事件延迟到达和具体回滚操作。本地 COPY 返回成功并不足够。
   除当前对象读取外，还要检查每个站点的精确版本列表和来源复制状态。
   回退后，所有预期副本都应不再列出替代版本；当前对象正确时，其他站点仍可能有待清除版本。

保留不可变清单、完整私密元数据备份及所选操作经过测试的回滚步骤。
如果操作产生了新版本，回滚必须考虑该版本及当前版本关系；再 COPY 一次不能证明回滚。
回退二进制可能重新打开原来的错误入口，也不会自动撤销先前的元数据写入。
写入失败或结果不确定时，先停止并重新检查精确版本，再决定是否重试。
自动重试 COPY 可能再创建一个版本，重复请求不能代替确认前一次操作的实际结果。

## 标签与删除标记清除 {#other-state}

- **标签丢失或复活：** 比较各站点精确版本的标签及可用的修订、审计证据。空标签可能是有意删除，不能根据缺失重建历史。
  计划新标签操作前需要权威清单；新的标签操作本身会推进修订。
- **删除标记清除：** 将预期版本、桶、键、修改时间与 purge/MRF 状态、复制错误一并记录。
  保留的标记可能符合预期，或正在等待出站复制；仅凭 405 响应不能证明找到了预期标记，也不能证明已清除。
- **历史 IAM 撤销：** 使用独立的 [IAM 恢复流程](/zh/operations/replication/iam-upgrade/)。

## 验证范围 {#validation}

2026-09-16 使用只读账户，对真实 Server 20260903 存储、停机快照升级到构建 `70c7ec4a9fbf`（运行时源码基线 `40220bd836cb`）的克隆，以及重启后的克隆执行检查。
三次清单均为 21 条版本或标记记录：6 条确认存在传输编码、2 条编码待核查、12 条头部不受影响、1 条删除标记。
夹具覆盖非当前版本、null version、特殊对象键、gzip 原始字节，以及带保留期和法律保留的 SSE-S3 对象。
升级保留了原始字节、标签和已核实的锁状态；旧编码头也如预期保留，未被自动修复。

另一次克隆演练通过明确替换元数据的 COPY 修正了一个未锁定当前对象的编码，保留原始 gzip 字节和标签，
但产生了新版本，原版本的错误头部仍然存在。仅删除该新建、未锁定版本后，原当前版本恢复。
该结果证明版本及回滚的区别，并非通用原地修复。最初的环境为 Linux ARM64 单进程、单盘与静态测试 KMS 密钥。

后续演练使用三个站点，每站点两个 Server 进程、四块盘。将 Server 20260903 的停机备份恢复到上述候选构建，
明确配置各站点的 SSE-S3 桶默认加密，使用静态实验 KMS 密钥。
一个站点离线期间，为两个未锁定 gzip 对象创建纠正后的替代版本；该站点返回后，
六个进程的新版 ID、原始 gzip 字节、元数据和标签一致，来源报告复制状态 `COMPLETED`。
随后对历史版本的标签更新没有改变替代版本的标签。
未参与改写的对照对象始终保留 SSE-S3、GOVERNANCE 保留期和法律保留。

| 阶段 | 每个站点观察到的精确版本清单 |
| --- | --- |
| 旧版存储与升级后的克隆 | 三个原版本的头部均受影响。 |
| 创建替代版本、离线站点追赶及冷重启 | 两个已纠正的当前版本，加上三个原有受影响版本。 |
| 仅删除两个新建未锁版本，再冷重启 | 三个原版本保留，两个替代版本 ID 均不再出现。 |

通过的演练在 COPY 和回退之前，均对每个进程执行了实际签名写入/读取探针。
早期失败记录仍保留：健康检查和读取成功时，写入曾返回 `SlowDownWrite`；
在重启后立即发起回退的一次尝试中，180 秒后仍能在副本站点列表中看到替代版本。
该观察不能证明复制永久失败，那次尝试的更长恢复路径未测试。
通过的流程要求实际写就绪，并逐版本确认收敛。

多站点实验运行于同一个隔离 Linux ARM64 容器，共享时钟。
尚未验证 SSE-C、外部 KMS、改写锁定版本、所有延迟事件排列或通用的历史版本原地修复。
详细结果和剩余限制由 [#201](https://github.com/pgsty/silo/issues/201) 跟踪。

清单工具用于准备，不执行修复。具体 Object Lock/SSE/复制配置的验证仍由
[#201](https://github.com/pgsty/silo/issues/201) 跟踪。生产清单扫描与写入应针对选定部署和经评审的变更清单分别记录。

对 `confirmed-header` 行，`proposed_content_encoding: null` 表示移除整个 Content-Encoding 字段，不是写入空字符串。其它分类的 null 不代表修复建议。设计背景见[副本元数据规范化](/blog/design/replica-metadata-normalization/)。

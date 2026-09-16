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
4. 真正写入前，在选定的写入协调流程中重新核对精确版本、ETag、大小、元数据指纹、时间戳、标签和锁状态。
   先读后写本身不能消除竞争，元数据改变也可能保持 ETag 不变。冲突项跳过并重新检查。
5. 在克隆中核对精确版本 HEAD、原始字节校验值不变、所有保留元数据/锁及副本最终收敛，
   并演练重启、旧事件延迟到达和具体回滚操作。本地 COPY 返回成功并不足够。

保留不可变清单、完整私密元数据备份及所选操作经过测试的回滚步骤。
如果操作产生了新版本，回滚必须考虑该版本及当前版本关系；再 COPY 一次不能证明回滚。
回退二进制可能重新打开原来的错误入口，也不会自动撤销先前的元数据写入。

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
该结果证明版本及回滚的区别，并非通用原地修复。环境为 Linux ARM64 单进程、单盘与静态测试 KMS 密钥；
尚未验证多站点收敛、SSE-C、外部 KMS 或改写锁定版本。详细结果和剩余检查由 [#201](https://github.com/pgsty/silo/issues/201) 跟踪。

清单工具用于准备，不执行修复。克隆修复和具体 Object Lock/SSE/复制配置的验证仍由
[#201](https://github.com/pgsty/silo/issues/201) 跟踪。生产清单扫描与写入应针对选定部署和经评审的变更清单分别记录。

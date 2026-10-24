---
title: "mc checksum verify"
url: "/zh/reference/minio-mc/mc-checksum-verify/"
weight: 14
upstream_modified: true
upstream_link: ""
---

<a id="command-mc.checksum.verify"></a>

[`mc checksum verify`](#command-mc.checksum.verify) 将 S3 端点保存的附加校验和，与该端点返回的逻辑对象字节重新独立计算出的校验和进行比较。

这是 [mcli 20260903](/zh/blog/release/mcli-20260903/) 新增的**只读审计命令**，只使用 S3 LIST、HEAD 与 GET；它绝不修复 metadata、改写对象，也不会武断地判断是哪条历史写入路径造成了 mismatch。

命令支持 `FULL_OBJECT` 类型的 CRC32、CRC32C、CRC64NVME、SHA1 与 SHA256。`COMPOSITE` 校验和报告为不支持；缺少 `x-amz-checksum-type` 时报告 `UNKNOWN_CHECKSUM_TYPE`。

本文写作 `mc`；如果安装的可执行文件名是 `mcli`，请直接替换命令名。

## 语法 {#syntax}

```shell
mc checksum verify [FLAGS] ALIAS/BUCKET/OBJECT
mc checksum verify --recursive [FLAGS] ALIAS/BUCKET[/PREFIX]
mc checksum verify --manifest FILE [FLAGS] ALIAS
```

按对象或递归前缀选择目标，并按需指定版本；`--manifest` 是独立的选择模式：

- 对象路径核验单个对象；
- `--recursive` 核验桶或前缀下的对象；
- `--version-id` 核验一个精确版本；
- `--versions` 将对象或递归扫描选中的所有版本纳入核验；
- `--manifest` 从 JSON Lines 文件读取精确的 bucket、key 与可选 version 身份。

对于未版本化对象和 `null` 版本，命令使用 `If-Match` 读取，并在读取完成后再次 HEAD。若对象发生变化，报告 `UNKNOWN_OBJECT_CHANGED`。

递归扫描忽略目录标记（以 `/` 结尾的对象键），不为其生成记录或增加 `objects` 计数。需要检查目录标记时，在 manifest 中显式列出。

查询单个对象的所有历史版本时，客户端会枚举同名前缀，再筛选精确键名。若已知 VersionID，使用 manifest 可减少枚举开销。

## 结果与退出码契约 {#results}

每个候选对象都会产生一个稳定状态：

| 状态 | 含义 |
| :-- | :-- |
| `MATCH` | 所有支持的存储校验和都等于独立计算值。 |
| `MISMATCH` | 至少一个存储校验和与返回的逻辑对象字节不同。 |
| `NO_CHECKSUM` | 端点未返回附加校验和；不会下载 body。 |
| `WOULD_VERIFY` | dry run 找到一个受支持的 full-object 校验和。 |
| `UNKNOWN_*` | 命令无法给出可靠判断，例如对象变化或读取失败。 |
| `SKIPPED_*` | 请求的过滤器有意排除了该候选对象。 |

正常完成返回 `0`；命令错误或选定的审计失败返回 `1`。默认 `--fail-on any` 会在 mismatch、`UNKNOWN_*`，以及被 `--max-size` 跳过对象时失败。

`--fail-on` 接受：

- `mismatch` —— 只在校验和不匹配时失败；
- `unknown` —— 只在出现 `UNKNOWN_*` 结果时失败；
- `no-checksum` —— 包含 `any` 的失败条件，并在缺少校验和或核验对象数为零时失败；
- `any` —— 默认值，也会把大小上限导致的不完整审计视为失败；
- `none` —— 报告发现，但不把它们转换成审计失败。

`--dry-run` 不执行 `--fail-on` 判定。默认策略允许只有 `NO_CHECKSUM` 的运行成功退出；要求实际完成校验时，使用 `no-checksum` 或检查 `verified`。

最终汇总包含 `objects`、`verified`、各状态计数与 `incomplete`。`verified` 等于 `MATCH + MISMATCH`；自动化需要证明至少真正重算过一个校验和时，应检查这个字段。

## 重要参数 {#flags}

| 参数 | 用途 |
| :-- | :-- |
| `--recursive`, `-r` | 扫描桶或前缀下的全部对象。 |
| `--versions` | 纳入所有对象版本。 |
| `--version-id`, `--vid` | 选择一个精确版本。 |
| `--manifest FILE` | 从 JSON Lines 读取候选；不能与扫描、版本、时间选择参数混用。 |
| `--dry-run` | 对候选执行 LIST 与 HEAD，但不下载对象 body。 |
| `--max-workers N` | 限制并发读取数；默认 `4`，范围 `1` 至 `64`。 |
| `--max-size SIZE` | 跳过大于 `10GiB` 等指定值的对象；空值或 `0` 表示不限。 |
| `--older-than`, `--newer-than` | 使用 `7d10h31s` 等相对时长或受支持的绝对时间进行过滤。 |
| `--enc-c KEY` | 提供一个或多个 SSE-C 前缀到密钥映射，使用原始 Base64 或十六进制格式。 |
| `--report FILE` | 把对象记录与汇总写入新的 JSON Lines 文件；POSIX 系统上以 `0600` 创建。 |
| `--json` | stdout 不是终端时输出紧凑 JSON Lines。 |

全局 `--limit-download` 可限制下载速度。对象正文以流式方式校验，不完整缓冲或写入磁盘。时间过滤仍需 HEAD，以对象当前返回的元数据为准。

仅显式 `--quiet`、`-q` 或 `MC_QUIET=true` 抑制 stdout 上的对象记录与汇总；重定向到文件或管道不会隐藏结果。`--report` 独立于 stdout，始终写入 JSON Lines。详见[输出契约](/zh/blog/design/checksum-verify/#output-contract)。

## Manifest 格式 {#manifest}

每个非空行标识一个候选对象。`bucket` 与 `key` 必填，`versionId` 可选：

```json
{"bucket":"archive","key":"2025/report.json","versionId":"optional"}
```

alias 只在命令行提供一次。Manifest 只接受候选对象身份，不是结果文件或断点文件，也不包含校验和或加密密钥。

## 示例 {#examples}

核验一个对象：

```shell
mc checksum verify mysilo/archive/report.json
```

递归核验前先估算读取成本：

```shell
mc checksum verify --recursive --dry-run mysilo/archive/2025/
```

以四个 worker 核验全部历史版本，并要求每个选中对象都携带校验和：

```shell
mc checksum verify --recursive --versions --max-workers 4 \
  --fail-on no-checksum mysilo/archive/2025/
```

从外部清单核验候选对象，并保留私有权限的 JSON Lines 报告：

```shell
mc checksum verify --manifest candidates.jsonl \
  --report results.jsonl mysilo
```

> [!NOTE]
> `MISMATCH` 只证明核验时端点返回的 checksum 与同一时刻返回的逻辑字节不同；它不识别历史原因，也不能代替外部事实源。如果服务端自身的 bitrot 保护在返回对象字节之前拒绝损坏分片，结果是 `UNKNOWN_READ_ERROR`，绝不会是 `MATCH`。

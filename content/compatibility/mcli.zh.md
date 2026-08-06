---
title: "MCLI 客户端兼容性注记"
linkTitle: "客户端 MC"
description: "pgsty/mc 与上游 minio/mc 的差异"
url: "/zh/compatibility/mcli/"
weight: 20
type: docs
icon: fa-solid fa-terminal
minio_origin: false
silo_modified: false
---

`mcli` 是 Silo 构建的 MinIO 客户端（`mc`）。本页记录二者在哪些地方可以互换使用，在哪些地方存在差异。

[`pgsty/mc`](https://github.com/pgsty/mc) 从上游项目 [`minio/mc`](https://github.com/minio/mc) 的最终提交 [`77f82e18`](https://github.com/minio/mc/commit/77f82e18b5401a65958f1619df6ebb994634bd88)（2025-11-06）分叉而来。上游仓库已于 2026 年 7 月归档，且从未发布过包含该提交的版本 —— 因此每一个 `mcli` 版本都比历史上任何官方 `mc` 二进制更新。分支至今的发布版本：[20260313]、[20260321]、[20260417]、[20260804](/zh/blog/release/mcli-20260804/)、[20260806](/zh/blog/release/mcli-20260806/)。

## 兼容原则 {#principles}

本分支只遵循一条规则：**改名的是交付物与渠道，不是你手里的工具。**

- **改名 / 更换** —— 磁盘上的制品名（`mcli`）、`--version` 与 `--help` 中的产品身份、分发渠道（GitHub `pgsty/mc`、Pigsty 软件仓库、`docker.io/pgsty/mc`），以及制品签名密钥。命令语法没有改 —— 而且取决于你怎么安装，连你敲的名字都可以不变。
- **保持不变** —— 全部命令、子命令与参数；S3 与 admin API 行为、请求签名与协议头（`x-minio-*`）；JSON 输出结构；正常操作的退出码；配置文件格式与别名语义；`MC_*` 环境变量（含 `MC_HOST_<alias>`）；`.part.minio` 断点续传后缀；以及 Go 模块路径 `github.com/minio/mc`。
- **切断** —— 所有连向 MinIO 运营服务的通道：发布/更新源、SUBNET 支持与许可门户、遥测，以及预置的 `play` 演示别名。受影响的命令为保持脚本兼容而保留，以稳定错误快速失败，而不是直接消失。
- **保留** —— 上游版权与 AGPL-3.0 许可证。运行时输出同时致谢 MinIO, Inc. 与 PGSTY。

上游 `mc` 写出的配置文件 `mcli` 原样可读，反之亦然；两个客户端都可以连接 MinIO 服务器、Silo 服务器以及任何其他 S3 兼容端点。

## 差异区别 {#changed}

按「影响到你的可能性」从高到低排列。

### 1. 名字 —— 你敲的是什么，配置就在哪 {#naming}

对许多用户来说这里其实什么都没变：容器镜像的入口仍然是 `mc`，以 `mc` 名安装的二进制与上游行为完全一致。变的是我们**交付**的东西 —— 归档包与 Linux 软件包把二进制装为 **`/usr/local/bin/mcli`**（软件包名 `mcli`）。

两个名字都没有被硬编码在任何地方。上游客户端自 2016 年起就根据被调用的名字派生运行时身份，而 `mcli` 正是上游自己的 `CONFLICT.md` 为解决与 Midnight Commander 的冲突所推荐的改名方案（[issue #873](https://github.com/minio/mc/issues/873#issuecomment-267583013)）—— 本分支只是把这个建议扶正为官方发行名，**代码零改动**。这套机制的实际含义如下：

| 跟随调用名 | 与名字无关、恒定不变 |
| :-- | :-- |
| 配置目录：`~/.mc` vs `~/.mcli`（Windows：`%USERPROFILE%\mc\` vs `…\mcli\`） | 环境变量：恒为 `MC_*` —— **不存在** `MCLI_CONFIG_DIR` |
| 帮助与用法文本中显示的程序名 | `config.json` 格式 —— 双向完全一致、可互换 |
| shell 自动补全的注册名 | 全部命令、参数、JSON 输出、退出码 |
| User-Agent 应用后缀（`mc/…` vs `mcli/…`） | `--config-dir` 与 `MC_CONFIG_DIR` 覆盖 |

唯一真正的坑：**第一次运行 `mcli` 时，你已有的 `mc` 别名不会出现** —— 它从空的 `~/.mcli` 开始。两种解法：继续以 `mc` 名调用它（一个符号链接即可 —— 起作用的是 argv[0]），或用 `cp -a ~/.mc ~/.mcli` 一次性搬运状态。自动化与配置模板则应显式设置 `MC_CONFIG_DIR`：环境变量前缀不跟随名字，一套模板即可通吃两个名字。详见[迁移指南](#migration)。

获取渠道：[GitHub Releases](https://github.com/pgsty/mc/releases)（SHA-256 校验文件 `mcli_<version>_checksums.txt`）、[Pigsty 软件仓库](https://pigsty.cc/docs/repo/infra/list/#object-storage)（RPM 经 GPG 签名，密钥指纹 `9592A7BC7A682E7333376E09E7935D8DB9BD8B20`），或 `docker.io/pgsty/mc`。上游的 minisign 公钥不为这些制品签名，`dl.min.io` 永远不会被访问。发布标签（`RELEASE.YYYY-MM-DDTHH-MM-SSZ`）与软件包版本（`YYYYMMDDHHMMSS.0.0`）沿用上游方案。

### 2. `mcli update` 恒定失败 —— 这是有意的 {#self-update}

自更新已移除。`mcli update` 不联网、不替换自身二进制，打印明确提示并**恒定以退出码 `1` 结束**。上游 `mc update` 在已是最新版时返回 `0`，因此**任何调用它并把非零退出码视为失败的 cron 任务或脚本都会开始报错** —— 请删除该调用，改用软件包管理器或 GitHub Releases 升级。每次执行时向上游发布源的版本探测也已移除，`MC_UPDATE` / `MINIO_UPDATE` 不再被读取。

（`mcli admin update ALIAS` —— 升级*服务端* —— 命令仍在，但 Silo 服务端会在服务侧拒绝就地升级。）

### 3. SUBNET、许可与遥测命令 {#subnet}

所有连向 MinIO SUBNET 的路径均在构建期关闭。受影响的命令保留名称与参数，打印稳定提示 —— *"MinIO SUBNET services (registration, licensing, uploads) are disabled in this Silo build of mc; diagnostics remain available locally."* —— 并以退出码 `1` 结束：

| 命令 | 现在的行为 | 替代方式 |
| :-- | :-- | :-- |
| `mcli license register` | 提示后退出码 `1` | —— |
| `mcli license update ALIAS`（在线续期） | 提示后退出码 `1` | `mcli license update ALIAS license.key`（离线，仍可用） |
| `mcli support upload` | 提示后退出码 `1` | 通过自有渠道传递文件 |
| `mcli support proxy set` | 提示后退出码 `1` | `proxy remove` 仍可清除遗留配置 |
| `mcli support callhome enable` | 提示后退出码 `1` | `disable` / `status` 照常工作 |

诊断能力本身全部保留：`mcli support diag` / `perf` / `profile` / `inspect` 恒定以本地（airgap）模式运行 —— 结果写入本地文件，不上传任何数据，SUBNET 注册也不再是前置条件。两项相关加固：`inspect` 不再回退到用内置的 MinIO 公钥加密输出（你的归档始终由你自己解密）；自 20260804 起 `--debug` 输出对 SUBNET 凭证脱敏 —— 如果你分享过旧版本的调试日志，请轮换其中的密钥。`mcli license info` 与 `unregister` 在本地照常工作。

### 4. `play` 演示别名不再预置 {#aliases}

全新配置只预置 `local`、`s3`、`gcs`，不含 `play`。假定演示别名存在的教程与冒烟脚本需要显式添加：`mcli alias set play https://play.min.io <access-key> <secret-key>` 即可恢复旧行为 —— 主动连接任何 S3 端点都不受限制。已有配置文件永远不会被修改。

### 5. 输出文案携带 Silo 身份 {#identity}

`mcli --version` 保留机器可读的首行，新增身份行与双版权行；`--help` 显示 "Silo client"，示例使用 `mysilo`。命令语法分毫未动 —— 只有 grep 上游身份字样（如 "MinIO Client"）的脚本需要调整。

### 6. 面向开发者 {#source}

模块路径保持 `github.com/minio/mc`，现有 import 无需修改即可编译 —— 但 `go install github.com/minio/mc@latest` 安装的是**已归档的上游版本**，不是本分支。请从源码构建（`git clone https://github.com/pgsty/mc && cd mc && make`）或通过 `replace` 指令引用。贡献无需 CLA，但每个提交必须携带 DCO 签署（`git commit -s`）。上游已归档也意味着继承的缺陷只会在本分支修复 —— 最需要注意的是 [minio/mc#5139](https://github.com/minio/mc/issues/5139)（版本化桶上的 `mirror --remove --watch`）。

## 迁移指南 {#migration}

从官方 `mc` 二进制迁移到 `mcli`：

1. **安装 `mcli`**，任选一条分支渠道（校验方式见 [§1](#naming)）：GitHub Releases 归档包、Pigsty 软件仓库的 `yum install mcli` / `apt install mcli`，或 `docker pull pgsty/mc`。
2. **决定用什么名字调用它** —— 这决定它读取哪份配置：
   - *保留 `mc` 名称（摩擦最小）*：确认系统中已无上游二进制（`command -v mc`）后，以 `mc` 名安装 —— 例如 `ln -s /usr/local/bin/mcli /usr/local/bin/mc`。以 `mc` 调用时它原样读取你现有的 `~/.mc`，无需迁移任何东西。
   - *改用 `mcli` 名称*：用 `cp -a ~/.mc ~/.mcli` 一次性搬运状态，或设置 `MC_CONFIG_DIR=~/.mc`。两个客户端也可以并存，各用各的目录。
3. **清理自动化脚本**：
   - 移除 `mc update` 调用 —— 现在恒定退出码 `1`；
   - 移除 `license register`、`support upload`、`support callhome enable`、`support proxy set` —— 同样是稳定失败；
   - `support diag` / `perf` / `profile` / `inspect` 照常工作并写本地文件；删除任何期待「上传到 SUBNET」的后续步骤；
   - 检查所有解析 `--version` 首行之外内容的逻辑。
4. **复查 `play` 依赖**（见 [§4](#aliases)）。
5. **验证**：`mcli --version`、`mcli alias ls`，然后对你的服务器执行 `mcli ls <alias>` 与 `mcli ping <alias>`。
6. **回退**始终是平凡操作：配置格式双向一致，保留旧的 `mc` 二进制即可随时切回。

## 参考阅读 {#see-also}

- [Silo 与 MinIO](/zh/compatibility/server/) —— `silo` 服务端与 `minio` 的对比

[20260313]: https://github.com/pgsty/mc/releases/tag/RELEASE.2026-03-13T08-57-32Z
[20260321]: https://github.com/pgsty/mc/releases/tag/RELEASE.2026-03-21T00-00-00Z
[20260417]: https://github.com/pgsty/mc/releases/tag/RELEASE.2026-04-17T00-00-00Z

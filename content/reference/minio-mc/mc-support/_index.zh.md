---
title: "mc support"
url: "/zh/reference/minio-mc/mc-support/"
weight: 380
icon: fa-solid fa-life-ring
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support.rst
upstream_modified: true
---

<a id="mc-support"></a>
<a id="command-mc.support"></a>
<a id="id2"></a>
<a id="id3"></a>

## 本地诊断工具 {#description}

`mcli support` 保留 SILO 诊断能力，不要求 MinIO SUBNET 订阅。管理员控制生成的文件与主动分享。

## 子命令 {#subcommands}

| 命令 | SILO 行为 |
| --- | --- |
| `diag` | 生成本地健康报告 |
| `perf` | 性能测试，结果在本地处理 |
| `profile` | 服务端性能剖析与本地输出 |
| `inspect` | 对象元数据诊断 |
| `top` | 实时观察服务端活动 |
| `callhome enable` | 禁用并返回退出码 1；disable/status 保留 |
| `proxy set` | 禁用并返回退出码 1；remove 保留 |
| `upload` | 禁用并返回退出码 1 |

用 `mcli support COMMAND --help` 查看参数。各诊断命令需要目标 SILO 的相应管理授权。
参考 [diag](/zh/reference/minio-mc/mc-support-diag/)、[perf](/zh/reference/minio-mc/mc-support-perf/)、
[profile](/zh/reference/minio-mc/mc-support-profile/)、[inspect](/zh/reference/minio-mc/mc-support-inspect/)与[mcli 兼容性](/zh/compatibility/mcli/#subnet)。

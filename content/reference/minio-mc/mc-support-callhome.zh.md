---
title: "mc support callhome"
url: "/zh/reference/minio-mc/mc-support-callhome/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-callhome.rst
upstream_modified: true
---

<a id="mc-support-callhome"></a>
<a id="command-mc.support.logs.disable"></a>
<a id="command-mc.support.logs.enable"></a>
<a id="command-mc.support.logs.status"></a>
<a id="command-mc.support.callhome"></a>
<a id="id2"></a>
<a id="id3"></a>
<a id="mc.support.callhome.enable"></a>
<a id="mc.support.callhome.disable"></a>
<a id="mc.support.callhome.status"></a>
<a id="id4"></a>
<a id="mc.support.callhome.ALIAS"></a>
<a id="mc.support.callhome.-diag"></a>
<a id="id5"></a>
<a id="callhome"></a>
<a id="id6"></a>
<a id="id7"></a>
<a id="id8"></a>

## 当前行为 {#description}

在 PGSTY mcli 中，`support callhome enable` 保留旧语法兼容入口，但 MinIO SUBNET 服务已在构建时禁用。
命令返回明确的禁用提示与退出码 **1**，不会注册订阅或上传文件。旧上游的订阅/API-key 操作步骤不适用。
`mcli support callhome disable ALIAS` 与 `status ALIAS` 仍保留。

## 用法 {#syntax}

查看所安装版本接受的兼容参数：

```shell
mcli support callhome --help
```

诊断工具 `mcli support diag`、`perf`、`profile`、`inspect` 仍在本地运行，无需 SUBNET 注册。
结果由管理员自行保存和分享。完整边界见 [mcli 兼容性](/zh/compatibility/mcli/#subnet)。

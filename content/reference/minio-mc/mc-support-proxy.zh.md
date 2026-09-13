---
title: "mc support proxy"
url: "/zh/reference/minio-mc/mc-support-proxy/"
weight: 60
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-proxy.rst
upstream_modified: true
---

<a id="mc-support-proxy"></a>
<a id="command-mc.support.proxy"></a>
<a id="id2"></a>
<a id="id3"></a>
<a id="url"></a>
<a id="id4"></a>
<a id="callhome"></a>
<a id="id5"></a>
<a id="mc.support.proxy.set"></a>
<a id="mc.support.proxy.show"></a>
<a id="mc.support.proxy.remove"></a>
<a id="id6"></a>

## 当前行为 {#description}

在 PGSTY mcli 中，`support proxy set` 保留旧语法兼容入口，但 MinIO SUBNET 服务已在构建时禁用。
命令返回明确的禁用提示与退出码 **1**，不会注册订阅或上传文件。旧上游的订阅/API-key 操作步骤不适用。
`mcli support proxy remove ALIAS` 仍可清除旧代理设置。

## 用法 {#syntax}

查看所安装版本接受的兼容参数：

```shell
mcli support proxy --help
```

诊断工具 `mcli support diag`、`perf`、`profile`、`inspect` 仍在本地运行，无需 SUBNET 注册。
结果由管理员自行保存和分享。完整边界见 [mcli 兼容性](/zh/compatibility/mcli/#subnet)。

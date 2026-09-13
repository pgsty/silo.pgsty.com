---
title: "mc license register"
url: "/zh/reference/minio-mc/mc-license-register/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-license-register.rst
upstream_modified: true
---

<a id="mc-license-register"></a>
<a id="command-mc.support.register"></a>
<a id="command-mc.license.register"></a>
<a id="id2"></a>
<a id="id3"></a>
<a id="mc.license.register.ALIAS"></a>
<a id="mc.license.register.-airgap"></a>
<a id="mc.license.register.-api-key"></a>
<a id="mc.license.register.-license"></a>
<a id="mc.license.register.-name"></a>
<a id="id4"></a>
<a id="id5"></a>
<a id="license"></a>
<a id="id6"></a>
<a id="id7"></a>
<a id="minio-license-register-airgap"></a>
<a id="id8"></a>
<a id="id9"></a>
<a id="id10"></a>
<a id="id11"></a>

## 当前行为 {#description}

在 PGSTY mcli 中，`license register` 保留旧语法兼容入口，但 MinIO SUBNET 服务已在构建时禁用。
命令返回明确的禁用提示与退出码 **1**，不会注册订阅或上传文件。旧上游的订阅/API-key 操作步骤不适用。


## 用法 {#syntax}

查看所安装版本接受的兼容参数：

```shell
mcli license register --help
```

诊断工具 `mcli support diag`、`perf`、`profile`、`inspect` 仍在本地运行，无需 SUBNET 注册。
结果由管理员自行保存和分享。完整边界见 [mcli 兼容性](/zh/compatibility/mcli/#subnet)。

---
title: "mc support upload"
url: "/zh/reference/minio-mc/mc-support-upload/"
weight: 80
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-upload.rst
upstream_modified: true
---

<a id="mc-support-upload"></a>
<a id="command-mc.support.upload"></a>
<a id="parameters"></a>
<a id="mc.support.upload.ALIAS"></a>
<a id="mc.support.upload.FILE"></a>
<a id="mc.support.upload.-comment"></a>
<a id="mc.support.upload.-enc"></a>
<a id="mc.support.upload.-issue"></a>
<a id="global-flags"></a>
<a id="examples"></a>
<a id="upload-a-file-to-an-issue"></a>
<a id="upload-a-file-to-an-issue-with-a-comment-for-minio-engineers"></a>

## 当前行为 {#description}

在 PGSTY mcli 中，`support upload` 保留旧语法兼容入口，但 MinIO SUBNET 服务已在构建时禁用。
命令返回明确的禁用提示与退出码 **1**，不会注册订阅或上传文件。旧上游的订阅/API-key 操作步骤不适用。


## 用法 {#syntax}

查看所安装版本接受的兼容参数：

```shell
mcli support upload --help
```

诊断工具 `mcli support diag`、`perf`、`profile`、`inspect` 仍在本地运行，无需 SUBNET 注册。
结果由管理员自行保存和分享。完整边界见 [mcli 兼容性](/zh/compatibility/mcli/#subnet)。

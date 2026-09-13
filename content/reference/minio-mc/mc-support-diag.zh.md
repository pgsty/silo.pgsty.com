---
title: "mc support diag"
url: "/zh/reference/minio-mc/mc-support-diag/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-diag.rst
upstream_modified: true
---

<a id="mc-support-diag"></a>
<a id="command-mc.support.diag"></a>
<a id="id2"></a>
<a id="id3"></a>
<a id="id4"></a>
<a id="subnet"></a>
<a id="id5"></a>
<a id="minio-support-diagnostics-airgap"></a>
<a id="id6"></a>
<a id="id7"></a>
<a id="id8"></a>
<a id="mc.support.diag.ALIAS"></a>
<a id="mc.support.diag.-airgap"></a>
<a id="mc.support.diag.-anonymize"></a>
<a id="mc.support.diag.-api-key"></a>
<a id="id9"></a>

## 健康诊断 {#description}

`mcli support diag ALIAS` 从 SILO 生成健康报告，保存在本地，不要求 SUBNET 注册，也不会自动上传。
`--airgap` 保留为兼容参数，本版本始终按本地模式运行。报告可能包含环境信息，分享前应自行检查。

## 用法 {#syntax}

```shell
mcli support diag mysilo
mcli support diag mysilo --anonymize=strict
```

`ALIAS` 是通过 `mcli alias set` 配置的目标。`--anonymize` 控制报告的匿名化级别；
默认 standard 不匿名化主机名，strict 用于包括主机名在内的严格匿名化。
`--api-key` 保留兼容语法，不启用已禁用的 SUBNET 上传。

## 本地报告 {#examples}

命令输出报告文件路径。保管并检查生成的压缩报告，再按自己的支持流程分享。
`support callhome enable` 和 `support upload` 已禁用，不会把报告送往 MinIO。
已发布 mcli 以私有文件权限保存支持产物；完整行为见 [mcli 兼容性](/zh/compatibility/mcli/#subnet)。

可用参数以 `mcli support diag --help` 为准。

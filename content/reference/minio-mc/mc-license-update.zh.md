---
title: "mc license update"
url: "/zh/reference/minio-mc/mc-license-update/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-license-update.rst
upstream_modified: true
---

<a id="mc-license-update"></a>
<a id="command-mc.license.update"></a>
<a id="id2"></a>
<a id="id3"></a>
<a id="minio1"></a>
<a id="id4"></a>
<a id="id5"></a>
<a id="mc.license.update.ALIAS"></a>
<a id="mc.license.update.LICENSE-FILE-WITH-PATH"></a>
<a id="mc.license.update.-airgap"></a>
<a id="id6"></a>

## 许可命令 {#description}

SILO 使用 AGPLv3。许可命令保留旧命令语法，不能购买或激活 MinIO 商业订阅。

| 命令 | 行为 |
| --- | --- |
| `mcli license info ALIAS` | 显示本地保存的许可信息，不访问 SUBNET |
| `mcli license unregister ALIAS` | 清除本地许可注册状态 |
| `mcli license update ALIAS license.key` | 保留显式本地文件更新路径，是否接受由目标服务端决定 |
| `mcli license update ALIAS` | 在线续订禁用，退出码 1 |
| `mcli license register ALIAS` | 注册禁用，退出码 1 |

## 用法 {#syntax}

使用 `mcli license COMMAND --help` 查看安装版本接受的参数。
旧 `--airgap`、API-key 等兼容参数不能重新启用在线注册/续订。
日常对象存储与诊断不要求 SUBNET 注册。

见 [SILO 许可说明](/zh/about/license/)与 [mcli 兼容性](/zh/compatibility/mcli/#subnet)。

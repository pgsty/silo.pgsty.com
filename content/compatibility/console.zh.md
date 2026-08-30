---
title: "Console 兼容性注记"
linkTitle: "Console"
description: "SILO Console 与上游 MinIO Console 的差异"
url: "/zh/compatibility/console/"
weight: 30
type: docs
icon: fa-solid fa-window-maximize
---

SILO Console 是 Silo 构建的 MinIO Console。本页记录二者在哪些地方可以互换使用，在哪些地方存在差异。

[`pgsty/silo-console`](https://github.com/pgsty/silo-console) 延续上游 `minio/console` 的历史，起点是其最终提交 [`feff71e4`](https://github.com/pgsty/silo-console/commit/feff71e48e39547834399a84a9460edb4fb50563)（2026-04-16），品牌重塑自 `50797deb`（2026-08-04）开始。上游仓库已不再公开 —— `github.com/minio/console` 现在返回 404，而 `minio/mc` 只是归档 —— 因此源码谱系只在这个分支中留存。Go 模块路径仍可解析，因为模块代理继续提供它此前缓存的版本。分支至今的发布版本：[v2.0.0](/zh/blog/release/console-2.0.0/)、[v2.1.0](/zh/blog/release/console-2.1.0/)、[v2.1.1]、[v2.2.0](/zh/blog/release/console-2.2.0/)、[v2.2.1]。

## 原则 {#principles}

本分支遵循与 Silo 其余部分相同的规则：**交付物及其分发渠道改名，其它软件所依赖的接口不改。**

- **改名** —— 磁盘上的产物（`silo-console`）、界面与 `--version` 中的产品标识、分发渠道、签名密钥。
- **不变** —— Go 模块路径 `github.com/minio/console`、全部 `CONSOLE_*` 环境变量（含 `CONSOLE_MINIO_SERVER` 与 `CONSOLE_MINIO_REGION`）、Web 应用调用的 REST API 结构，以及打包标识 `minio-console.service`、`console-user`、`/etc/default/console` —— 因此原地升级软件包依然可用。
- **切断** —— 自动自更新、遥测、分析、信标、外部脚本与字体、以及 call-home。只有在显式配置时才会访问版本目录，入口是 `SILO_RELEASE_SERVICE_HOST`，并保留 `RELEASE_SERVICE_HOST` 作为兼容回退。
- **保留** —— 上游版权与 AGPL-3.0 许可证。运行时输出同时致谢 MinIO, Inc. 与 PGSTY。

> [!NOTE]
> SILO Console 不是通用 S3 浏览器。它的管理功能需要 Silo 在 S3 API 之外实现的 MinIO 兼容管理 API。

## 差异 {#changed}

### 1. 保留了完整的管理控制台 {#scope}

这是最大的功能差异，方向与通常的分支相反：上游把社区版控制台裁剪成了对象浏览器，SILO Console 保留了完整的管理界面 —— 仪表盘、健康状态、日志、诊断与速度测试；存储桶、对象、生命周期、复制、通知与分层管理；用户、用户组、服务账号、策略、身份提供方与 KMS 配置；以及服务器配置。

### 2. 仪表盘面向 Metrics V3 {#metrics}

仪表盘组件查询 **MinIO Metrics V3** 指标目录 —— 也就是当前部署实际抓取的那一套 —— 并针对其零值语义与按节点导出的语义做了保护，使面板能区分"真实的零"与"数据缺失"。映射关系记录在 [`docs/metrics-v3.md`](https://github.com/pgsty/silo-console/blob/main/docs/metrics-v3.md)。

### 3. 更小、更安静的产物 {#payload}

内嵌前端从约 10 MB 降到 3 MB 以内，可逐字节复现构建，并由发布门禁强制校验。没有任何形式的遥测，页面本身也没有外部网络依赖。

### 4. 双语界面 {#i18n}

界面、帮助内容与文档链接提供英文与中文，通过页面级切换使用，且未引入额外的运行时依赖。

### 5. 面向开发者：模块图 {#source}

Go 模块路径保持 `github.com/minio/console`，Console 自身的 `require` 指令保持在**可解析的上游版本**上 —— 尤其是 `github.com/minio/pkg/v3 v3.6.1`。这些 require 是 Console 公开模块图的一部分，而 Go 取整个模块图中各要求的最大值，因此抬高它们会把每一个内嵌 Console 的服务器的模块图一起顶上去。

Silo 维护的实现改由 `replace` 指令选择：

```go
replace (
	github.com/minio/mc          => github.com/pgsty/mc ...
	github.com/minio/minio-go/v7 => github.com/pgsty/silo-go/v7 ...
	github.com/minio/pkg/v3      => github.com/pgsty/silo-pkg/v3 ...
)
```

由此得出两条结论，并且在实践中都会咬人：

1. **replace 不会被继承。** Go 会忽略依赖模块声明的 `replace`。内嵌 Console 源码的服务器必须在自己的 `go.mod` 里重复这些选择，否则会在无声无息中用上游包构建 Console。
2. **这些选择要成套采用。** 客户端与共享包是耦合的：`pgsty/mc` 需要基于 Silo 共享包的严格策略 API 编译。保留客户端 replace 的构建必须同时保留共享包 replace。Go 能够解析"一个项目的客户端 + 另一个项目的共享包"这种部分覆盖，但 Console 既不支持也不测试它。

Console 自身的源码不使用只有分支才有的 API —— 严格策略写入校验是本地实现而非引入的 —— 并且有一个 CI 任务通过丢弃全部三个 replace、在纯上游模块图上完成构建、vet、测试与交叉编译来证明这一点。这是构建兼容性的保证，不等于声称上游包与 Silo 包在运行时行为一致。

## 迁移 {#migration}

已有的 MinIO Console 部署可以原地升级。服务单元、服务账号与配置文件名称都不变，全部 `CONSOLE_*` 变量按原样读取，因此通常的做法是用 `silo-console` 软件包覆盖安装后重启。

有两处行为会在首次启动后改变，值得提前预期：

- `silo-console` 不会自我更新。请通过软件包、镜像或编排系统来推送新版本。
- 任何依赖控制台访问 MinIO 运营服务的流程 —— 更新源、许可、遥测 —— 都不再有可访问的对端。

## 参见 {#see-also}

- [Silo 服务器兼容性](/zh/compatibility/server/) —— 本控制台所管理的服务器
- [MCLI 客户端兼容性](/zh/compatibility/mcli/) —— 命令行客户端
- [Console 发布说明](/zh/tags/console/) 与 [`CHANGELOG.md`](https://github.com/pgsty/silo-console/blob/main/CHANGELOG.md)

[v2.1.1]: https://github.com/pgsty/silo-console/releases/tag/v2.1.1
[v2.2.1]: https://github.com/pgsty/silo-console/releases/tag/v2.2.1

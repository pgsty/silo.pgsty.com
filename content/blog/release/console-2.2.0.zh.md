---
title: "Silo Console 2.2.0 发布说明（草案）"
linkTitle: "silo/console 2.2.0"
date: 2026-08-24
author: "冯若航"
description: "SILO Console 2.2.0 候选草案：升级至 Go 1.27.0，切换到受维护的 silo-pkg 分支，采用 etcd client 3.7.1，审慎维护依赖，并修正下载进度的未知状态。"
tags: [发布, console]
weight: 1
draft: true
url: "/zh/blog/release/console-2.2.0/"
aliases:
  - /releases/console-2.2.0/
---

> [!CAUTION]
> **草案 —— 尚未发布。** 暂定发布日期为 **2026-08-24**，拟定版本为 **2.2.0**。目前没有对应的发布提交、标签、二进制、软件包、容器镜像、校验和、签名或任何公开制品；正式发布前，日期与范围均可能调整。

**暂定日期：** 2026-08-24 · **候选版本：** `v2.2.0` · **状态：** 草稿

这个候选版本计划将 SILO Console 迁移到 Go 1.27，把共享包依赖从上游 `minio/pkg` 切换到受维护的 [`pgsty/silo-pkg` 3.12.0 候选](/zh/blog/release/pkg-3.12.0/)，采用稳定的 etcd 3.7 client 版本线，纳入一组刻意收敛的小补丁，并包含已经提交的下载进度正确性修复。

拟定版本为 **2.2.0**，而不是 2.1.2。下载修复本身属于补丁规模，但共享策略/证书实现的提供方发生切换，同时跨越了 etcd client 的 minor 边界，因此更适合作为一次带明确兼容性说明的中版本发布。

## 下载进度不再伪造确定性 {#download-progress}

对象浏览器不再把未知的下载总大小转换成一个看似精确、实则虚假的百分比。

- 总大小缺失、无效或与已下载字节矛盾时，进度保持 **不确定状态**，不再被强行换算。
- 零字节对象走明确的规范化路径，不再和「总大小未知」混在一起。
- 中止与取消成为终态，迟到的进度事件不能把已经取消的下载重新变回活动状态。
- 单元测试与 Chromium 回归用例覆盖无效总量、零字节对象、取消流程和可见进度状态。

这项修复已经作为 [`16960f7a`](https://github.com/pgsty/silo-console/commit/16960f7ab894ee8c1750ad9a6a93f984f5cd5077) 提交。下文的依赖升级仍是尚未提交的本地候选。

## 工具链与 Go 官方模块 {#go-toolchain}

语言版本、容器构建、CI、tidy 与漏洞分析基线统一到 Go 1.27：

| 组件 | 原版本 | 候选版本 |
|:--|:--|:--|
| `go` 指令与构建镜像 | `1.26.5` | `1.27.0` |
| GitHub Actions 矩阵 | `1.26.x` | `1.27.x` |
| tidy 兼容版本 | `1.26` | `1.27` |

Go 1.27 延续 Go 1 兼容承诺，但编译器、运行时、标准库与默认 JSON 实现均有变化。因此候选版本不是只改元数据，而是在最终版 Go 1.27.0 工具链下完成构建和测试。

当前依赖图选择的 Go 项目官方模块也同步刷新：

| 模块 | 原版本 | 候选版本 |
|:--|:--|:--|
| `golang.org/x/crypto` | `v0.54.0` | `v0.55.0` |
| `golang.org/x/net` | `v0.57.0` | `v0.58.0` |
| `golang.org/x/text` | `v0.40.0` | `v0.41.0` |
| `golang.org/x/mod` | `v0.37.0` | `v0.40.0` |
| `golang.org/x/tools` | `v0.47.0` | `v0.49.0` |
| `golang.org/x/exp` | 2026-02-18 伪版本 | 2026-08-20 伪版本 |

`x/oauth2`、`x/sync`、`x/sys`、`x/term` 与 `x/time` 已经处于当前选定版本，因此保持不变。

完整模块图中也会出现历史 `x/exp/typeparams` 子模块与 `x/telemetry`，但它们只来自工具或历史传递要求。`go mod tidy` 不会把它们保留为根依赖，因此本候选不会仅为覆盖工具专用选择而制造未使用的固定版本。

## 与 `silo-pkg` 对齐 {#silo-pkg}

旧依赖图要求 `github.com/minio/pkg/v3 v3.6.1`，实际解析到的是上游 MinIO 模块。只改 require 版本，拿到的仍然是上游 `minio/pkg`，**不会**自动切换到 SILO 分支。最终版本计划显式选择同批次的 3.12 候选：

```go
require github.com/minio/pkg/v3 v3.12.0

replace github.com/minio/pkg/v3 => github.com/pgsty/silo-pkg/v3 v3.12.0
```

`v3.12.0` 标签与公共代理记录目前尚不存在，因此 Console 工作树暂时钉住已发布的 3.11.0 分支，并在根模块显式选择 3.12 候选所需的依赖下限。集成测试使用临时 modfile，把这个固定版本替换为当前本地 `silo-pkg` 3.12 工作树。只有 3.12.0 正式发布、replace 更新到真实版本，并通过公共模块路径重跑测试后，Console 才能打标签。

这种安排让所有现有 import 路径保持不变，同时保证最终二进制使用受维护的分支。3.12 候选建立在 3.11 的策略资源边界加固、条件键查找修复、LDAP 连接修复、证书监听器清理、种子随机数修复和时长往返编码修复之上（详见 [`silo-pkg` 3.11.0 发布说明](/zh/blog/release/pkg-3.11.0/)），并加入其 [3.12.0 草稿](/zh/blog/release/pkg-3.12.0/)所记录的 Go 1.27 / etcd 3.7 依赖基线。

Console 直接使用该分支的 `certs`、`env`、`net`、`policy`、`console`、`trie`、`words`、`ellipses` 与 `mimedb` 包。因此这是真实的运行时依赖选择，不是只为了文档对齐。

## 为什么是 etcd 3.7.1，而不是 3.6.14？ {#etcd-3-7}

这两个版本解决的是不同层次的问题：

| 版本线 | 含义 |
|:--|:--|
| `3.6.14` | 现有 3.6 版本线上的补丁；它是修复 GO-2026-6107 / CVE-2026-73500 的最小升级。 |
| `3.7.1` | 当前稳定的 3.7 minor 版本线；包含相同安全修复、3.7 client/API 更新，并要求 Go 1.26 或更高版本。 |

etcd 3.7 不是单纯的数字升级。它完成了从旧 protobuf 实现向 `google.golang.org/protobuf` 的大规模迁移，删除残留的 v2 client/server 组件，并把 `clientv3.New` 改为非阻塞创建，不再遵循已弃用的 `grpc.WithBlock` 行为。嵌入 etcd server、依赖内部包或依赖阻塞式 client 创建的消费者，需要专门迁移。

SILO Console 不涉及这些路径。它通过 `silo-pkg/quick` 接触 etcd：接收外部已经创建好的 `*clientv3.Client`，只使用既有的 v3 `Get` 与 `Put` 调用；Console 与 `silo-pkg` 都不会创建 etcd client，也不会嵌入 etcd server。按照 etcd 的模块版本约定，三个相关 Go 模块严格保持同版：

| 模块 | 原版本 | 候选版本 |
|:--|:--|:--|
| `go.etcd.io/etcd/api/v3` | `v3.6.8` | `v3.7.1` |
| `go.etcd.io/etcd/client/pkg/v3` | `v3.6.8` | `v3.7.1` |
| `go.etcd.io/etcd/client/v3` | `v3.6.8` | `v3.7.1` |

这里升级的只是 **编译进二进制的 Go client 库**。它不会替运维升级 etcd server，不修改集群数据，不开启 3.7 服务端功能，也不改变 SILO 的部署拓扑。真正把 etcd 集群从 3.6 升到 3.7，仍需遵循官方逐个 minor 升级的流程，并从 3.6.11 或更高补丁版本开始。

## 审慎处理第三方依赖 {#third-party}

第三方库没有做全量追新。在检查真实源码差异、而不是只看版本号之后，候选版本只保留一项独立补丁，以及 `silo-pkg` / etcd 对齐直接要求的关联变化：

| 模块或家族 | 原版本 | 候选版本 | 原因 |
|:--|:--|:--|:--|
| `github.com/cheggaaa/pb` | `v1.0.29` | `v1.0.30` | 同线补丁；与 `silo-pkg` 候选对齐 |
| `github.com/lestrrat-go/jwx` | `v2.1.6`（`/v2`） | `v3.0.13`（`/v3`） | `silo-pkg` 直接要求，并已在该分支审阅为维护中的 JWT 版本线 |
| `github.com/lestrrat-go/httprc` | `v1.0.6` | `v3.0.6`（`/v3`） | JWX 协调依赖，包含已审阅的刷新循环修复 |
| `github.com/go-openapi/swag/conv` | `v0.25.5` | `v0.28.0` | `silo-pkg` 直接要求，`typeutils` 随之对齐 |
| `github.com/grpc-ecosystem/grpc-gateway/v2` | `v2.28.0` | `v2.29.0` | etcd 3.7.1 声明的依赖 |
| `go.yaml.in/yaml/v3` | `v3.0.4` | `v3.0.5` | `silo-pkg` 直接要求 |

这些关联变化都是已接受的一方模块或安全依赖提出的要求，不是对 Console 第三方库进行独立扫荡。

第一轮曾提出 `minio-go` 7.0.100，以及每个现有 go-openapi minor 版本线上的最新补丁。源码审阅后撤销了这个决定：`minio-go` 7.0.99 → 7.0.100 涉及 19 个文件，包括签名、endpoint 与缓存行为；go-openapi 各补丁则分别改动 17–52 个文件，`spec` 还触及 expander、loader 与 SSRF 敏感路径。没有强制升级的 CVE，因此全部保留 Console 原版本。

其它明确暂缓的更新包括 `pb/v3` 3.2、`klauspost/compress` 1.19、`minio-go` 7.3、`testify` 1.12，以及更新的 go-openapi minor。当前候选版本没有可达漏洞或必要依赖关系要求它们。

本轮也审视了 `pgsty/mc` 分支。它目前发布的是面向应用的日期标签，而不是可以直接钉住的语义化 Go module 版本。让 Console 使用这个高度耦合的 `github.com/minio/mc` 库，需要额外的伪版本 replace，并会把应用行为改动混入依赖发布，因此这次暂缓迁移。

## 安全审查 {#security}

- **etcd TLS Listener 拒绝服务：** `go.etcd.io/etcd/client/pkg/v3` 在 3.6.14 / 3.7.1 之前受到 [GO-2026-6107 / CVE-2026-73500](https://pkg.go.dev/vuln/GO-2026-6107) 影响。选择 3.7.1 可以关闭漏洞，并保持三个 etcd 模块同版。
- **Go 模块校验：** `x/mod` 0.40.0 包含 [CVE-2026-56864](https://pkg.go.dev/vuln/GO-2026-6180) 与 [CVE-2026-56865](https://pkg.go.dev/vuln/GO-2026-6179) 的修复。
- **可达性结果：** 升级后 `govulncheck` 对 Console 报告可达漏洞为零、导入包漏洞为零；Swagger 构建工具也被单独扫描，结果相同。
- **OpenPGP 通告：** 扫描仍会报告模块级 [GO-2026-5932](https://pkg.go.dev/vuln/GO-2026-5932)，因为 `x/crypto` 模块包含已经停止维护的 `openpgp` 包。Console 没有导入它，Go 漏洞库也把所有版本都标为受影响且没有修复版本。

## 兼容性 {#compatibility}

- 依赖升级不计划修改 Console HTTP API、环境变量、命令、二进制名、systemd 单元、配置格式或嵌入数据布局。
- 最低 **构建工具链** 提升到 Go 1.27.0；发布后的自包含二进制不要求目标主机安装 Go。
- etcd Go 模块现在要求 Go 1.26，低于 Console 的 Go 1.27 构建基线。
- `silo-pkg` 分支会收紧并修复共享策略行为。虽然这是安全正确的变化，但它也是本次应按 minor 发布、并在打标签前重跑鉴权回归测试的原因之一。
- 当前候选树中的前端包仍报告 2.1.1。只有在最终 release commit 中才会改成 2.2.0，随后从干净工作树确定性重建嵌入资产。

## 当前已经完成的验证 {#verification}

尚未提交的依赖候选已经通过：

- Go 1.27.0 下的 `go mod tidy -diff`、`go mod verify`、`go vet ./...` 与全包编译检查；
- 所有不依赖外部服务的 Console 测试，其中 API 套件只排除了依赖 localhost MinIO 的单项测试；`integration`、`replication` 与 SSO 套件仍是需要独立拓扑的门禁；
- 带生产 `kqueue,operator` 标签的 `linux/amd64` 与 `linux/arm64` 静态构建；
- Swagger 2.0 规范校验与固定版本 Swagger 工具执行；
- 应用和构建工具的 `govulncheck`，可达漏洞与导入包漏洞均为零；
- 同一条 etcd 3.7.1 依赖线上的 `silo-pkg` 门禁：golangci-lint 零问题，以及完整的 `go test -race -tags kqueue ./...`。
- 使用临时 modfile 把 `minio/pkg/v3` 替换为当前本地 `silo-pkg` 3.12 候选后，Console 的 `pkg`、`cmd/console` 与 API 测试，以及带生产标签的 Linux/amd64 构建通过。

## 正式发布前尚需完成 {#remaining-gates}

这份草稿不能证明 v2.2.0 已经存在。正式发布前仍需：

1. 发布并验证 `silo-pkg` 3.12.0，把 Console 的 replace 从暂用的 3.11.0 固定版本更新到真实的 3.12.0 模块版本，并重跑 Go 门禁；
2. 确定最终源码范围，审阅所有计划进入 2.2.0 的非依赖改动；
3. 运行完整外部 MinIO 与 OpenLDAP/Dex SSO 测试；
4. 把前端包版本提升到 2.2.0，并从干净工作树重建嵌入资产；
5. 跑完前端类型检查、单元测试、Chromium、格式化和生产构建门禁；
6. 提交聚焦的改动，为精确验证过的树打标签，并构建发布二进制、软件包、镜像、校验和、签名与溯源元数据；
7. 逐项验证公开制品后，才能把本文从 `draft: true` 改成正式发布状态。

## 关联提交 {#related-commits}

- [`16960f7a`](https://github.com/pgsty/silo-console/commit/16960f7ab894ee8c1750ad9a6a93f984f5cd5077)：fix: keep unknown downloads indeterminate
- 依赖与发布提交：待补充。

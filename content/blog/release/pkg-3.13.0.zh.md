---
title: "silo-pkg 3.13.0 正式发布"
linkTitle: "silo/pkg 3.13.0"
date: 2026-08-30
author: "冯若航"
description: "silo-pkg 3.13.0 启用自有模块路径 github.com/pgsty/silo-pkg/v3，终结它此前赖以生效的 replace 指令安排；同时废弃 Silo Go SDK 分支，直接使用上游 minio-go。"
tags: [发布, pkg]
weight: 5
url: "/zh/blog/release/pkg-3.13.0/"
aliases:
  - /releases/pkg-3.13.0/
---

**发布日期：** 2026-08-30 · **版本：** [v3.13.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.13.0) · **提交：** [`215f116`](https://github.com/pgsty/silo-pkg/commit/215f116ec25120ce365c79bce4096cd7665b2c1e) · **仓库：** [pgsty/silo-pkg](https://github.com/pgsty/silo-pkg)

3.13.0 是一个破坏性版本，只有一条主线：本模块不再冒用上游的导入路径，改用自己的。同时废弃 `pgsty/silo-go` 分支——它已经不再包含任何上游没有的东西。

> [!WARNING]
> **本包发布与 SILO 服务器发布是两道不同的闸门。** 包标签与 GitHub Release 已公开，但 `silo`、`silo-console`、`mcli` **尚未**切换到新导入路径，它们仍通过旧的 `replace` 安排构建于 v3.12.2 之上。本文不建立任何 SILO 服务器标签、容器镜像、软件包、部署或生产上线。

## 版本速览 {#glance}

- **已发布：** `silo-pkg v3.13.0` 标签与 GitHub Release，声明 `module github.com/pgsty/silo-pkg/v3`。
- **已终结：** `github.com/minio/pkg/v3` 模块身份，以及每个消费者都必须重复一遍的 `replace` 指令。
- **已终结：** `github.com/pgsty/silo-go/v7` 分支，本版本直接依赖上游 `minio-go`。
- **未变：** 所有包、符号与行为。移动的只是它们被导入的路径。
- **不属于本次发布：** `silo`、`silo-console`、`mcli` 三方的配套迁移。

## 为什么要迁移路径 {#why}

此前本分支保留上游的 `github.com/minio/pkg/v3` 路径，以便充当直接替代品——消费者用一条 `replace` 指令即可选中它。但 Go **不会继承**依赖模块声明的 `replace`，在准备下一个 SILO 服务器版本时，这套安排的三笔账同时到期。

**每个消费者都要重复一遍重定向，漏写的那个会静默构建到上游。** 一个依赖了本包却没写 replace 的模块，会解析到真正的 `minio/pkg`，编译通过，然后悄无声息地失去本分支的行为。

**`require` 那行必须写一个源码早已不匹配的版本。** `ParseConfigStrict` 在上游要到 v3.11.0 才出现，`Resource.IsBareARN` 则在任何上游版本都不存在。当源码需要 v3.12 的 API，旁边却写着 `require github.com/minio/pkg/v3 v3.6.1`，这是靠改数字无法变真的元数据。

**为此打的补丁还会传播。** `pgsty/mc` 里有一行纯粹为此存在的编译期哨兵——引用 `Resource.IsBareARN`——目的是把静默降级变成响亮的构建失败。而把 `mc` 的下限抬高、让元数据变诚实，又会通过模块图把要求推上去，顶高 `silo-console` 那条刻意压低的下限——那条下限存在的意义恰恰是防止这件事。

上游路径在这里能提供的回报很少：`minio/pkg` 是一个小型内部库，而本模块的消费者只有 `silo`、`silo-console` 和 `mcli`。[Silo Go SDK](/zh/compatibility/mcli/) 则保留上游的 `github.com/minio/minio-go/v7` 路径——那里的直接替代能力有真实价值，上游也仍在积极维护。

## 上游 minio-go 取代 Silo Go SDK {#minio-go}

`pgsty/silo-go` 已经不再包含任何功能性差异。它唯一独有的改动 [Return CopyObject checksums in UploadInfo](https://github.com/minio/minio-go/pull/2295) 已于 2026-08-24 合入上游，其余内容只是一个版本字符串、一个 logo、一份 README 和一段 lint 工具声明。

上游最新标签 `v7.3.0` 比该合并早 14 个提交，其中包括[并行分段上传中共享校验和哈希器的数据竞争修复](https://github.com/minio/minio-go/pull/2290)，因此钉住这个标签反而是倒退。本版本改为依赖伪版本 `v7.3.1-0.20260828014306-0e78d3f18efe`，待上游切出新标签后再换成标签。

## 兼容性 {#compatibility}

所有包、导出符号与行为均未改变。本版本移动的是它们被导入的位置，仅此而已。

请与 `silo`、`silo-console`、`mcli` 的配套改动一起采用。单独升级本包的消费者将无法构建——新旧路径是两个不同的模块，类型无法在它们之间传递。

变更前：

```go
require github.com/minio/pkg/v3 v3.6.1

replace (
    github.com/minio/pkg/v3      => github.com/pgsty/silo-pkg/v3 v3.12.2
    github.com/minio/minio-go/v7 => github.com/pgsty/silo-go/v7 v7.3.1
)
```

变更后：

```go
require github.com/pgsty/silo-pkg/v3 v3.13.0
```

并把 `github.com/minio/pkg/v3/...` 的导入改写为 `github.com/pgsty/silo-pkg/v3/...`。继续沿用旧安排的消费者仍可构建于 v3.12.2 及更早版本之上，这些版本依然可用。

有一个后果值得预期：两条路径现在是不同的模块，因此一次构建里可能同时包含两者——某个第三方依赖若导入 `github.com/minio/pkg/v3`，它的导入不再被重定向。在 SILO 技术栈中这种情况只出现一次，来自 `minio/colorjson` 与 `minio/dperf`，二者都只用到 `pkg/v3/console`。而该包的颜色开关是 `fatih/color` 的进程级全局变量 `NoColor`，所有副本共享同一个，因此关闭颜色仍然会在各处一并生效。

## 验证 {#verification}

- `go build ./...`、`go vet ./...`、`go mod tidy -diff`、`gofmt -l .` 全部干净；`go test ./...` 通过 23 个包。
- 发布提交上的 CI：[Go](https://github.com/pgsty/silo-pkg/actions/runs/33318436618)、[LDAP Config Validator](https://github.com/pgsty/silo-pkg/actions/runs/33318438500)、[VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/33318440453)。
- 新路径已由一个不带任何 `replace` 指令的全新模块从模块代理解析成功，导入 `policy` 并运行通过。
- 下游迁移在发布前已端到端验证：`mcli`（194 个文件）、`silo-console`（36 个文件）与 `silo`（181 个文件）均通过构建、vet 与各自测试套件；`silo` 的 rebrand guard 通过，兼容基线差异恰为 19 条被删除的导入记录，环境变量、指标、请求头、路由、策略取值与导出符号均无变化。

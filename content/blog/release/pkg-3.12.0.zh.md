---
title: "silo-pkg 3.12.0 正式发布"
linkTitle: "silo/pkg 3.12.0"
date: 2026-08-24
author: "冯若航"
description: "silo-pkg 3.12.0 在严格策略写入路径上拒绝没有具体资源的裸 ARN 命名空间前缀，同时保留旧策略加载兼容；维护基线升级到 Go 1.27、Go 1.26 消费下限与 etcd 3.7.1。"
tags: [发布, pkg, 安全]
weight: 5
url: "/zh/blog/release/pkg-3.12.0/"
aliases:
  - /releases/pkg-3.12.0/
---

**发布日期：** 2026-08-24 · **版本：** [v3.12.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.0) · **提交：** [`2b087a1`](https://github.com/pgsty/silo-pkg/commit/2b087a11cf3547313a2e79275f52a0654c212e58) · **仓库：** [pgsty/silo-pkg](https://github.com/pgsty/silo-pkg)

3.12.0 是直接从主线发布的中版本，包含两条主线：第一，为“只有 ARN 命名空间前缀、却没有指定任何资源”的策略增加严格写入保护；第二，把维护基线推进到 Go 1.27 与 etcd 3.7。它新增两个导出的检查/校验方法，将验证过的消费者下限提高到 Go 1.26；同时也是第一个由 SILO 服务端在具名策略与服务账号策略写入路径上真正启用严格校验的 `silo-pkg` 版本。

> [!WARNING]
> **共享包发布与 SILO 服务端发布是两个不同的门。** `silo-pkg` 标签与 GitHub Release 已公开；SILO `main` 已在 [`eee05a17c`](https://github.com/pgsty/silo/commit/eee05a17c34a07cebb27220d12697be74c8bd617) 接入，并以 [`SN-2026-005`](https://github.com/pgsty/silo/commit/56c67dacf13cb3c5c1c59e64afec77ab145fb7f4) 记录运维影响。本文并不证明已有新的日期式 SILO 服务端标签、容器镜像、软件包、部署或生产发布。

## 发布状态一览 {#glance}

- **已经发布：** `silo-pkg v3.12.0` 标签、GitHub Release，以及裸 ARN 前缀的严格库级校验。
- **已进入 SILO 远端 `main`：** 具名策略与服务账号策略写入接入。
- **刻意保持宽松：** 既有 IAM 策略加载、IAM 导入与站点复制接收路径。
- **延后：** STS 内联策略严格校验与 Console 客户端侧提前校验；服务端仍是权威边界。
- **不属于本次发布：** SILO 服务端二进制、镜像、软件包、部署或生产发布。

## 裸 ARN 前缀为何会成为策略哑弹 {#bare-arn}

正常的 S3 资源 ARN 必须在命名空间前缀后指定资源：

```text
arn:aws:s3:::my-bucket
arn:aws:s3:::my-bucket/*
arn:aws:s3:::*
```

但原策略解析器也接受只有前缀的形式：

```text
arn:aws:s3:::
```

这个字符串没有指向任何 bucket 或对象。原解析器把它归一到通配资源类型，同时把 `arn:aws:s3:::` 保留为匹配模式；而真正进入 S3 鉴权的候选资源长成 `bucket` 或 `bucket/object`。因此整份策略虽然校验成功，这个模式通常什么也匹配不到。

对真正执行资源匹配的 Statement，实际影响取决于 `Effect`，以及前缀写在 `Resource` 还是 `NotResource`：

| 语句形状 | 原有运行结果 |
|:--|:--|
| `Allow` + 裸 `Resource` | 什么也不授权 |
| `Deny` + 裸 `Resource` | 本应生效的拒绝没有触发 |
| `Allow` + 裸 `NotResource` | 没有排除任何东西，可能远比预期授权得更宽 |
| `Deny` + 裸 `NotResource` | 可能远比预期拒绝得更宽 |

危险的两格属于依赖错误策略配置的 fail-open，而不是未认证远程漏洞，也没有 CVE。管理员、策略模板或自动化必须先提交这种错误资源，问题才会出现。同一问题也适用于已经注册的 S3 Tables 与 KMS ARN 前缀。

不操作资源的 Admin Action、`sts:*` Action Statement，以及 KMS 两阶段鉴权的第一阶段，本来就跳过资源匹配；裸前缀不会改变它们现有的运行时判定。严格写入仍拒绝这个具有误导性的字段，避免策略看起来像“限定了资源”，实际上该范围根本没有参与判定。

### 历史 `*arn:...` 形式 {#historical-spelling}

在沿用旧版本的宽松兼容路径中，把精确裸前缀解析后重新序列化，仍会在前面带上通配资源类型标记：

```text
arn:aws:s3:::  ->  *arn:aws:s3:::
```

这两种写法重新解析后得到完全相同的内部资源值。因此 3.12 同时识别精确前缀与历史星号形式。存量/导出策略，以及会在发送前先解析再序列化策略的客户端，都可能出现后者。

原有通配语料保持不变：`*`、`**`、`***`、`*foo`，以及 `arn:aws:s3:::*` 这样的显式资源仍按原方式解析。

## 严格写入，不做存储迁移 {#strict-path}

修复刻意把“加载已有策略”与“创建新策略”分开：

- `ParseConfig` 与 `Validate` 继续宽松；既有存量策略保持相同的加载、匹配与序列化行为。
- `ParseConfigStrict` 与 `ValidateStrict` 在 `Resource` 和 `NotResource` 中都拒绝“只有已注册 ARN 前缀、没有资源”的形式。
- `Resource.IsBareARN()` 识别精确/历史形式归一后的值，不改变导出的 `Resource` 结构、`ParseResource`、匹配算法或 JSON 表示。
- `ResourceSet.ValidateStrict()` 向消费者提供严格资源集合校验。

保留原资源表示对混合版本站点很重要：v3.11 与 v3.12 节点仍以相同方式比较、序列化存量策略，因此本修复不会制造站点复制 mismatch，也不要求迁移 IAM 存储。

## SILO 在三个边界启用保护 {#silo-integration}

SILO 提交 [`eee05a17c`](https://github.com/pgsty/silo/commit/eee05a17c34a07cebb27220d12697be74c8bd617) 选用 `silo-pkg v3.12.0`，并在以下场景使用严格解析：

1. 创建或替换具名 IAM 策略；
2. 创建带内联 Session Policy 的服务账号；
3. 更新服务账号的内联 Session Policy。

本轮中，以下兼容敏感路径仍保持宽松：

- 加载已经落盘的具名策略与嵌入策略；
- IAM 导入/恢复；
- 站点复制接收与应用；
- STS 内联 Session Policy；
- Bucket Policy——它现有的 bucket/action 校验已经会拒绝这些形式。

启用 `ParseConfigStrict` 还会激活两条早已存在的 Admin Policy 规则：同一条 Admin Statement 不能同时携带 `Resource` 与 `NotResource`；作用于 bucket 的 Admin Action 不能使用非 S3 资源。这些都是刻意的鉴权收紧，已经记录在 [`SN-2026-005`](https://github.com/pgsty/silo/blob/main/docs/security/advisories.md) 中。

> [!IMPORTANT]
> 本文所说的 **裸 ARN 前缀**，是 `arn:aws:s3:::` 这种命名空间后没有任何资源的形式；它不同于 3.11 桶/对象边界修复中的合法 **裸 bucket ARN**，例如 `arn:aws:s3:::my-bucket`。

## 运维需要做什么 {#operator-action}

工具不会自动改写存量策略，因为无法推断原作者真正想指定哪个资源。部署包含服务端严格接入的 SILO 构建前，应当：

1. 检查具名 IAM 策略中的精确/历史裸前缀；
2. 检查服务账号的内联策略；
3. 将每一处改成真正想要的具体资源；只有确实想表达整个命名空间时才使用尾部通配符；
4. 所有站点完成滚动升级后再审计一次。

不要机械地把每个命中改成 `arn:aws:s3:::*`：那可能把原本不起作用的语句变成集群范围的授权或拒绝。含裸前缀的旧策略仍可加载，但不能通过三个严格写入端点原样交回；在修改同一策略或服务账号的其它属性前，必须先纠正该资源。

更安全的审计方式，是使用 policy-info 与 access-key-info API，而不是完整 IAM Export——后者包含普通用户与服务账号的密钥。STS 严格校验继续延后，直到可以单独审计仍在使用的机器客户端及其 Session Policy 模板。

## 为什么是中版本 {#why-minor}

本次使用 `v3.12.0` 而不是 `v3.11.1`，因为它同时跨越三条兼容边界：

1. etcd 客户端从 3.6 中版本线进入 3.7；
2. 模块验证过的 `go` 下限从 1.25.0 提高到 1.26.0；
3. 新增了导出的裸 ARN 检查与严格资源集合校验 API。

模块路径仍是 `github.com/minio/pkg/v3`；`/v3` 导入后缀与全部现有 import 都无需修改。

## Go 与依赖基线 {#dependencies}

`go` 与 `toolchain` 指令承担不同职责：

- `go 1.26.0` 是选定 etcd 3.7 模块要求的消费者下限。
- `toolchain go1.27.0` 是维护开发与 CI 基线。
- CI Actions 迁移到 Node 24 runtime。

主要选中版本变化如下：

| 模块 | 3.11.0 | 3.12.0 |
|:--|:--|:--|
| `go.etcd.io/etcd/{api,client/pkg,client}/v3` | `3.6.6` | `3.7.1` |
| `golang.org/x/crypto` | `0.54.0` | `0.55.0` |
| `golang.org/x/net` | `0.57.0` | `0.58.0` |
| `golang.org/x/text` | `0.40.0` | `0.41.0` |
| `github.com/minio/minio-go/v7` | `7.0.97` | `7.0.99` |
| `github.com/minio/mux` | `1.8.2` | `1.9.2` |
| `github.com/cheggaaa/pb` | `1.0.29` | `1.0.30` |
| `github.com/lestrrat-go/jwx/v3` | `3.0.12` | `3.0.13` |
| `github.com/lestrrat-go/httprc/v3` | `3.0.1` | `3.0.6` |
| `github.com/grpc-ecosystem/grpc-gateway/v2` | `2.27.3` | `2.29.0` |
| `go.uber.org/zap` | `1.27.1` | `1.28.0` |

其它小型更新包括 `uax29` 2.3.1、`fastjson` 1.6.10、`secp256k1` 4.4.1 与 `goccy/go-json` 0.10.6。旧 `lestrrat-go/option` v1、`gogo/protobuf` 与陈旧的测试专用依赖退出选中依赖图。

etcd 3.7.1 是 3.7 版本线上第一个修复 [GO-2026-6107 / CVE-2026-73500](https://pkg.go.dev/vuln/GO-2026-6107) 的版本；该问题是未经认证即可触发的 TLS listener 拒绝服务。升级这些 Go 客户端模块 **不会** 自动升级运维使用的外部 etcd 服务端。SILO 不依赖被移除的 `grpc.WithBlock` 行为，发布验证也实际覆盖了 3.7.1 客户端连接 etcd 3.6.14 服务端。

依赖图声明 `coreos/go-systemd` 22.7.0，但模块将其 replace 为 22.6.0，因为 22.7.0 无法在 NetBSD 编译。SILO 服务端保留相同的可移植性覆盖。

## 兼容性 {#compatibility}

- import 路径与模块主版本不变。
- 既有策略继续按原方式加载和执行；只有严格创建/更新调用会拒绝错误前缀。
- 不执行策略、IAM 数据库、线缆协议或 etcd 数据迁移。
- 在 etcd 客户端拨号选项中使用 `grpc.WithBlock` 的下游，需要改用受支持的 readiness 检查；SILO 不使用它。
- 真正升级外部 etcd 集群仍是独立运维流程。
- 本分支没有引入上游 AIStor Memory 与新的 AIStor 专属 S3 Tables Action 词汇。

消费者按以下方式选用本版本：

```go
require github.com/minio/pkg/v3 v3.12.0

replace github.com/minio/pkg/v3 => github.com/pgsty/silo-pkg/v3 v3.12.0
```

## 验证 {#verification}

已打标签的包通过：

- 仓库完整 `make test` 门禁：固定版本 lint 加 `go test -race -tags kqueue ./...`；
- 重复运行裸 ARN 测试，以扰动 Go map 遍历顺序；
- `go mod verify`、`go vet`、`git diff --check` 与 `govulncheck`，可达漏洞为零；
- 实现级 Claude Opus Max 审查，结论为 **GO**，没有 P0/P1。

SILO 接入通过：

- 完整 IAM 服务端套件，包括具名策略精确/历史形式拒绝，以及服务账号创建/更新拒绝；
- `go test ./cmd -count=1`、`go vet ./cmd` 与 `go test ./...`；
- golangci-lint 2.13.1 零问题、`go mod verify` 与 `make check-gen`；
- 第二轮 Claude Opus Max 审查，结论为 **GO**；变异测试证明三个严格调用点与其集成断言都是承重的。

通过 VCS 直接解析模块，确认 `v3.12.0` 指向提交 `2b087a1`，模块校验和为：

```text
h1:1Bjqjb3KCt0oYhBLpH7W/e/5khTUoIgXWA12An1fbUc=
```

发布环境访问 `proxy.golang.org` 与 `sum.golang.org` 时持续超时，因此本文不把“公共代理已观察到”列为发布证据；Git 标签、GitHub Release、直接模块归档、来源提交与校验和均已验证。

## 相关变更 {#related-changes}

- [`2bc3a91`](https://github.com/pgsty/silo-pkg/commit/2bc3a91)：CI Actions 迁移到 Node 24
- [`c8c6872`](https://github.com/pgsty/silo-pkg/commit/c8c6872)：对齐 SILO Go 依赖栈
- [`2b087a1`](https://github.com/pgsty/silo-pkg/commit/2b087a11cf3547313a2e79275f52a0654c212e58)：在严格策略写入中拒绝裸 ARN 前缀；`v3.12.0` 标签提交
- [`30c49bd`](https://github.com/pgsty/silo-pkg/commit/30c49bd)：标签之后更新 README 依赖示例
- [`eee05a17c`](https://github.com/pgsty/silo/commit/eee05a17c34a07cebb27220d12697be74c8bd617)：SILO 启用具名策略与服务账号策略的严格写入
- [`56c67dacf`](https://github.com/pgsty/silo/commit/56c67dacf13cb3c5c1c59e64afec77ab145fb7f4)：登记 `SN-2026-005`

## 本文没有宣称什么 {#not-released}

本文不宣称已有新的 SILO 服务端版本、二进制、软件包、容器镜像、部署、生产发布、Console 发布或 STS 严格校验发布。这些仍是彼此独立的发布门，完成后必须分别报告。

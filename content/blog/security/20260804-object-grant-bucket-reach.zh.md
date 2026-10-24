---
title: "SN-2026-004：对象级策略授权越界命中桶级变更操作"
linkTitle: "SN-2026-004：对象授权越界修复"
date: 2026-08-04
author: "[冯若航](https://vonng.com) ([`@Vonng`](https://github.com/Vonng))"
description: "解析当 ObjectName 为空时 arn:aws:s3:::bucket/* 为何会命中桶级变更操作，以及 SN-2026-004 如何阻断该提权路径。"
url: "/zh/blog/security/object-grant-bucket-reach/"
tags: ["Security", "IAM", "Bucket Policy", "S3", "Authorization", "SILO"]
---

**`SN-2026-004`** 修复了 [silo-pkg `v3.11.0`](https://github.com/pgsty/silo-pkg/releases/tag/v3.11.0)（提交 `3c24ad1`、`1f97549`、`d8b1fa7`）与 [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z)（`97b7d2804`；上游参考 [`minio/minio#20449`](https://github.com/minio/minio/issues/20449)）中的一处 IAM 资源匹配缺陷：在评估桶级 S3 请求（`args.ObjectName == ""`）时，`Statement.IsAllowed` 会固定在桶名末尾拼接 `'/'` 生成 `"bucket/"` 作为待匹配资源字符串，导致原本仅面向桶内对象的通配授权（如 `Allow s3:* on arn:aws:s3:::bucket/*`）能够越界放行 `s3:PutBucketPolicy`、`s3:DeleteBucket` 等高危桶级变更操作。

## 结论先行 {#summary}

1. **根本原因**：当 `args.ObjectName` 为空时，`Statement.IsAllowed` 无条件向桶名追加了 `'/'`（得到 `"bucket/"`），从而被 `"arn:aws:s3:::bucket/*"` 的末尾通配符 `*` 匹配命中。
2. **多租户提权风险**：在多租户场景下，被授予 `Allow s3:* on arn:aws:s3:::tenant/*`（常见的“允许操作该桶内所有对象”简写写法）的租户凭据，可以调用 `PutBucketPolicy` 为该桶写入 `Principal: "*"` 公开策略，或调用 `DeleteBucket`、`PutReplicationConfiguration`、`PutBucketLifecycle`、`PutBucketVersioning` 与 `PutBucketObjectLockConfiguration`。
3. **为何不能一刀切去掉末尾斜杠**：直接对所有空对象名请求去掉 `'/'` 会立刻破坏 11 个现有的 STS `ListBucket` 兼容性测试，并且会导致 `Deny s3:* on arn:aws:s3:::bucket/*` 拒绝策略失效。
4. **精准收敛边界**：针对 `Allow` 语句上的 12 项高危桶级变更操作（`!legacyBucketResourceMatch && statement.Effect == Allow && isSensitiveBucketMutation(args.Action)`），资源模式必须**同时**匹配 `"bucket"` 与 `"bucket/"`。若存量环境短期内依赖旧行为，可通过 `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` 临时恢复 `20260804` 之前的匹配逻辑。

---

## 为什么 `arn:aws:s3:::bucket/*` 会命中桶级请求 {#the-defect}

在 `silo-pkg/bucket/policy/statement.go`（以及 `iam/policy/statement.go`）中，`Statement.IsAllowed(args Args)` 原本按如下逻辑构造待与 `Statement.Resources` 比对的资源路径：

```go
resource := args.BucketName
if args.ObjectName != "" {
    if !strings.HasPrefix(args.ObjectName, "/") {
        resource += "/"
    }
    resource += args.ObjectName
} else {
    resource += "/"
}
```

由于 `else` 分支无条件追加了 `"/"`，每一个不带对象名的桶级请求（`args.ObjectName == ""`）都会被构造为 `resource = "mybucket/"`。当它与资源模式 `"arn:aws:s3:::mybucket/*"` 进行通配比对时，`*` 会匹配 `"/"` 之后的空后缀并返回 `true`。

---

## 多租户环境下的越权影响 {#impact}

在 AWS IAM 与 S3 桶策略语义中，`arn:aws:s3:::mybucket` 代表桶本身，而 `arn:aws:s3:::mybucket/*` 代表桶内的对象。管理员在为租户或业务团队分配“桶内对象全权读写”权限时，经常将动作简写为 `s3:*` 并将资源限定在对象 ARN 上：

```json
{
  "Effect": "Allow",
  "Action": ["s3:*"],
  "Resource": ["arn:aws:s3:::tenant-a/*"]
}
```

由于 `s3:*` 同时涵盖了对象级动作与桶级动作，而 `"arn:aws:s3:::tenant-a/*"` 又命中了 `resource = "tenant-a/"`，持有该对象级策略的调用方便可在 `tenant-a` 桶上执行高危桶控制面变更：
- **`s3:PutBucketPolicy` / `s3:DeleteBucketPolicy`**：将桶策略篡改为 `"Principal": "*"` 以公开暴露整个桶，或直接为自己写入显式的桶级权限；
- **`s3:DeleteBucket` / `s3:ForceDeleteBucket`**：直接删除整个桶；
- **`s3:PutReplicationConfiguration`**：将桶复制目标指向攻击者控制的外部端点以窃取数据；
- **`s3:PutBucketLifecycle`**：配置生命周期规则使桶内所有对象与历史版本自动过期销毁；
- **`s3:PutBucketVersioning` / `s3:PutBucketObjectLockConfiguration`**：挂起版本控制或篡改默认合规保留配置。

---

## 为什么不直接全局移除末尾斜杠 {#why-narrow}

我们的第一版原型曾尝试直接删掉 `else { resource += "/" }` 分支，让所有 `args.ObjectName == ""` 的请求一律拿裸桶名 `"mybucket"` 去匹配。但运行测试集与代码审查后，我们发现这种一刀切改法会引发两个严重回归：

1. **破坏存量 `ListBucket` 兼容性**：`cmd/sts-handlers_test.go` 中有 11 个继承自上游的 STS 与 IAM 测试用例专门在 `arn:aws:s3:::mybucket/*` 上授予 `s3:ListBucket`（或 `s3:*`），而并未同时列出裸桶 ARN `arn:aws:s3:::mybucket`。如果对读取/列举操作也去掉 `"/"`，许多仅配置了 `arn:aws:s3:::mybucket/*` 的存量业务将无法列举桶。
2. **削弱 `Deny` 拒绝策略**：如果管理员编写了 `Deny s3:* on arn:aws:s3:::mybucket/*` 期望封禁该桶上的所有操作，把 `args.ObjectName == ""` 的匹配目标从 `"mybucket/"` 改为 `"mybucket"` 会导致该 `Deny` 语句**不再命中**桶级调用——原本用于收紧安全的补丁反而会变成 `Deny` 绕过漏洞！

---

## 修复方案：按动作收敛的双重资源匹配 {#the-fix}

为了在不破坏 `ListBucket` 兼容性且不削弱 `Deny` 语句的前提下阻断提权路径，`Statement.IsAllowed` 将严格检查精准限定在命中高危桶级变更动作的 `Allow` 语句上（`silo-pkg v3.11.0`，并在服务端提交 `97b7d2804` 中接入）：

```go
resource := args.BucketName
if args.ObjectName != "" {
    if !strings.HasPrefix(args.ObjectName, "/") {
        resource += "/"
    }
    resource += args.ObjectName
} else {
    resource += "/"
}

if args.ObjectName == "" && !legacyBucketResourceMatch &&
    statement.Effect == Allow && isSensitiveBucketMutation(args.Action) {
    return statement.Resources.Match(args.BucketName, args.ConditionValues) &&
        statement.Resources.Match(resource, args.ConditionValues)
}
return statement.Resources.Match(resource, args.ConditionValues)
```

对于 `Allow` 语句上的这些高危桶级变更动作，资源集合必须同时匹配裸桶名 `"mybucket"`（从而拒绝仅包含 `arn:aws:s3:::mybucket/*` 的策略，同时放行包含 `arn:aws:s3:::mybucket` 或 `arn:aws:s3:::*` 的策略）**以及** `"mybucket/"`（原因见下文[为什么单调性要求同时匹配两者](#monotonicity)）。

---

## 第二轮动作审计：哪些桶级写操作被纳入保护 {#second-pass}

初版草稿仅拦截了 `PutBucketPolicy` 与 `DeleteBucketPolicy`，遗漏了 `DeleteBucket` 以及生命周期、复制等变更操作。在第二轮审查中，我们逐一盘点了所有桶级写动作（`args.ObjectName == ""`），并将它们明确划分为两组。

纳入 `isSensitiveBucketMutation` 保护的 **12 项高危桶级变更动作**包括：
1. `s3:PutBucketPolicy`
2. `s3:DeleteBucketPolicy`
3. `s3:DeleteBucket`
4. `s3:ForceDeleteBucket`
5. `s3:PutBucketLifecycle`
6. `s3:PutReplicationConfiguration`
7. `s3:PutBucketVersioning`
8. `s3:PutBucketObjectLockConfiguration`
9. `s3:PutBucketQuotaConfig`
10. `s3:PutBucketRetentionConfig`
11. `s3:PutBucketCors`
12. `s3:DeleteBucketCors`

*（注：Server `20260804` 发布时桶级 CORS 接口尚未启用；当 [Server 20260903](/zh/blog/security/20260903-server-hardening/) 在 [`#71`](https://github.com/pgsty/silo/issues/71) / [`#80`](https://github.com/pgsty/silo/issues/80) 中正式实现桶级 CORS 时，`s3:PutBucketCors` 与 `s3:DeleteBucketCors` 已提前在 `isSensitiveBucketMutation` 中受控。）*

另有 4 类低风险或自动化建桶常用的桶级操作被有意保留为历史匹配行为，以免破坏将自动化凭据限定在 `arn:aws:s3:::app-bucket/*` 的存量部署流水线：
- `s3:CreateBucket`（使用前缀受限策略自动创建桶本身）；
- `s3:PutBucketTagging` / `s3:DeleteBucketTagging`；
- `s3:PutBucketEncryption`；
- `s3:PutBucketNotification`。

---

## 为什么单调性要求同时匹配 `"bucket"` 与 `"bucket/"` {#monotonicity}

我们在设计修复时要求满足严格的安全单调性（Monotonicity）不变量：**当 `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=off`（默认值）时，任何在旧逻辑下被拒绝的请求，绝不能在新逻辑下反而被 `Allow` 语句放行。**

在代码审查中，这一单调性证明经历了两次迭代才最终严密：

1. **第一次尝试（在 `NotResource` 上翻车）**：最初我们只检查了 `statement.Resources.Match(args.BucketName, ...)` 而未同时检查 `"mybucket/"`。此时如果策略使用了反向排除 `NotResource: ["arn:aws:s3:::mybucket/*"]`，在旧逻辑下 `"mybucket/"` 命中排除集因此被**拒绝**；而只检查 `"mybucket"` 时它不再命中排除集，结果反而从拒绝变成了**放行**！
2. **第二次尝试（在单字符通配符 `?` 上翻车）**：即便不使用 `NotResource`，仅检查 `args.BucketName` 也会在定长通配符 `?` 上破坏单调性！考虑策略 `Allow s3:PutBucketPolicy on Resource: ["arn:aws:s3:::mybucke?"]`：在旧逻辑下，待匹配串 `"mybucket/"` 长度为 9 个字符，因此 8 个字符的 `mybucke?` **不匹配**，请求被拒绝；如果新逻辑只拿 8 个字符的 `"mybucket"` 去匹配，`mybucke?` 就会突然匹配成功，从而**放行**了一个旧模式下原本拒绝的请求（`1f97549`）。

因此，要求 `statement.Resources.Match(args.BucketName, ...)` **与** `statement.Resources.Match(resource, ...)`（即同时匹配 `"mybucket"` 和 `"mybucket/"`）从数学上保证了新规则下通过的 `Allow` 集合必然是旧规则的真子集（`NewAllow = LegacyAllow ∧ MatchesBareBucket`，提交 `d8b1fa7`），彻底消除了在任何 `Resource` 或 `NotResource` 组合下出现反向放行的可能。这也意味着像 `arn:aws:s3:::mybucke?` 这样只匹配 8 字符 `"mybucket"` 却不匹配 9 字符 `"mybucket/"` 的人工边界模式将无法授权高危桶变更；管理员应规范编写 `arn:aws:s3:::mybucket` 或 `arn:aws:s3:::mybucket*`。

---

## 运维影响与兼容逃生开关 {#user-facing}

- **规范编写的策略无需任何改动**：凡是在 `arn:aws:s3:::mybucket`、`arn:aws:s3:::mybucket*` 或 `arn:aws:s3:::*` 上授予桶管理权限的策略，升级后行为完全不变。
- **仅含 `arn:aws:s3:::mybucket/*` 的策略**：依然可以正常读写对象并调用 `ListBucket`、`CreateBucket`、`PutBucketEncryption`、`PutBucketTagging` 和 `PutBucketNotification`，但在调用上述 12 项高危桶级变更动作时会收到 `AccessDenied`，除非在 `Resource` 中显式补上 `arn:aws:s3:::mybucket`。
- **兼容逃生开关**：如果存量自动化流程在迁移过渡期内确实依赖 `arn:aws:s3:::mybucket/*` 执行上述 12 项高危桶变更，可临时设置环境变量 `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on`，待策略修正后再关闭。

---

## 留白与后续演进 {#left-open}

- **不做启动期存量策略自动改写**：SILO 在升级时不会自动修改已存储的 IAM 策略或桶策略；运维人员可通过 `mcli admin policy info` 检查是否有管理角色依赖 `arn:aws:s3:::bucket/*` 执行桶级变更。
- **保持标准 `AccessDenied` 响应**：遵循 S3 安全惯例，鉴权拒绝响应不会向调用方披露具体是哪条语句或哪个 ARN 模式未命中。

## 总结 {#closing}

随 [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z)（`5ff00073a` 及 `silo-pkg` `d8b1fa7` / `v3.12.0`）发布后，12 项高危桶级变更操作默认要求策略 `Resource` 同时匹配桶级 ARN（除非显式开启 `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on`）。

---
title: "对象授权，越界到桶：当 bucket/* 能改写桶本身"
linkTitle: "对象授权越界到桶"
date: 2026-08-04
author: "冯若航"
description: "一个尾部斜杠,让一条只该管对象的 IAM 授权 arn:aws:s3:::bucket/* 触及了桶级操作——包括能把桶变公开的 PutBucketPolicy。我们只为最危险的写入动作做了一个窄的、对 Deny 无损的修复,其余刻意留给一次带迁移路径的变更。"
tags: [安全, Object Grant]
weight: 100
draft: false
url: "/zh/blog/security/object-grant-bucket-reach/"
---

**状态：** 已在 `pgsty/silo-pkg` `main` 修复,提交 `3c24ad1`,**尚未发布**(尚未发点版、也未抬进服务端构建)
**定级：** 访问控制加固——一条被收窄恢复的权限边界
**影响范围：** 仅被授予对象级(`arn:aws:s3:::bucket/*`)访问的 IAM 用户/角色/服务账号,且集群被多个租户共用的部署
**跟踪：** 上游 `minio/minio` issue [#20449](https://github.com/minio/minio/issues/20449)(2024 年起公开,至今未关闭)

## 先说结论 {#summary}

- 在 IAM 策略匹配中,桶级请求携带的是**空对象名**,匹配器把资源串拼成了 `"bucket/"`。于是对象级的策略模式 `"arn:aws:s3:::bucket/*"` 命中了它,一条本应只覆盖对象的授权**连带授予了桶级操作**。
- 最危险的是 **`PutBucketPolicy`**。一个只拿到 `bucket/*` 上 `s3:*` 的租户,可以装一条 `Principal:"*"` 的桶策略,把桶变成**匿名公网可读或可写**,或给自己授予桶级控制权。同一机制、同一类别的还有:`PutReplicationConfiguration`(外泄)、`PutBucketLifecycle`(批量删除)、`PutBucketVersioning`、`PutBucketObjectLockConfiguration`。
- **全量**修正是一次双向的行为变更:它既收紧过度授予的 `Allow` 语句,**又**放松过度阻断的 `Deny` 语句;而且会撤销**大量真实部署今天就写成 `bucket/*`** 的 `ListBucket`/`GetBucketLocation` 授权。那是一次兼容性破坏,不是一个干净的补丁。
- 所以我们做了一个**窄修复**:只让一小撮**敏感的桶配置写入动作**不再能通过 `bucket/*` 触及,且只作用于 `Allow` 语句(因此绝不削弱任何 `Deny`),并附带一个环境变量逃生舱。兼容敏感的读/列举族**按决定保持原样**。
- 修复在匹配器层**红/绿验证**通过;对象级热路径未被触碰。

## 斜杠,与那个空对象名 {#the-defect}

每一个桶级 S3 操作,鉴权时对象名都是空的——`checkRequestAuthType(ctx, r, policy.PutBucketPolicyAction, bucket, "")`。IAM 匹配器把它拼成资源串,而对空对象名的情况补了一个尾斜杠:

```go
resource.WriteString(args.BucketName)
if args.ObjectName != "" {
    // "bucket/object"
} else {
    resource.WriteByte('/') // "bucket/"  <-- 缺陷所在
}
```

`"bucket/"` 会被通配模式 `"bucket/*"` 命中,因为 `*` 匹配空串。于是一条把 `s3:*` 授在 `arn:aws:s3:::bucket/*` 上的策略——读起来是*"任意操作,但只作用于 `bucket` 里的对象"*——被评估成了也授予桶级操作。匿名/公开访问走的桶策略评估路径从来没有这个斜杠,是正确参照;只有 IAM 这条路径是错的,而且只错在一个地方。

这是上游 `minio/minio` 的 #20449,2024 年提交。上游早期的一次尝试直接删掉了斜杠,当天就因打破依赖旧行为的策略而被回滚。我们从那次回滚里吸取的教训,塑造了下面的修复。

## 它到底能做什么 {#impact}

`PutBucketPolicyHandler` 只有一道鉴权闸,闸后什么都没有。IAM 检查一过,调用者就能为该桶存入**任意**合法桶策略。

在多租户集群里的确切攻击链:

1. 管理员给租户 *A* 发策略 `Allow s3:* on arn:aws:s3:::bucket-a/*`,本意是*"A 只能操作 `bucket-a` 里的对象,别的都不行"*。
2. 因为那个斜杠,*A* 可以对 `bucket-a` 调用 `PutBucketPolicy`。
3. *A* 装上 `{ "Principal": "*", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::bucket-a/*" }`。`bucket-a` 里的每个对象现在**对匿名公网可读**;换成 `s3:*` 就是公网可写。把 `Principal` 指向 *A* 自控的账号即可外泄数据;在这条桶策略里给自己授桶级操作就是自我提权。

同一条对象级授权也能触及其它桶配置写入,后果相当:复制到攻击者的目标桶、一条一天过期的生命周期规则删光桶内内容、关闭版本控制、篡改对象锁保留策略。这些都不该从一条只作用于对象的授权里被触及。

它不可远程利用,也不需要任何缺失的凭据——调用者是你**主动**授予了受限策略的、已认证的主体。在单租户部署里,这个主体就是你自己信任的用户,现实风险很低;在共享的多租户集群里,它是一次真实的跨租户边界失效。

## 为何做窄修,而非整条边界 {#why-narrow}

显而易见的修法是:对所有桶级请求都不再补斜杠。我们没这么做,原因有两条,比那一行 diff 所暗示的更重要。

**它会打破常见的、良性的用法。** 这个修正撤销的不只是危险的桶写入——它也会撤销通过 `bucket/*` 授予的 `ListBucket`、`GetBucketLocation`、`ListBucketMultipartUploads`。大量部署正是这么写、并依赖它的。证据就是上游自己的测试套件:**11 个** STS 集成测试把 `s3:ListBucket` 授在 `bucket/*` 上,然后断言列举能成功。连写服务端的项目都这么写,生产策略里只会更多。一次维护升级把这些变成 `AccessDenied`,正是我们拒绝带给用户的那种意外。

**它切的是两个方向。** 匹配器对 `Allow` 和 `Deny` 拼的是同一套资源串。所以全量修正在收紧过度授予的 `Allow` 的**同时**,也放松了过度阻断的 `Deny`:一个用 `Deny s3:* on bucket/*` 锁死某个桶的管理员,会悄无声息地失去对桶级操作的那层保护。一个看着干净、却同时把安全推向两个方向的修复,不是维护补丁——它是一次迁移。

于是我们把改动收窄到"明确正确、且几乎零兼容代价"的地方:

- **只保护敏感的桶配置写入**:`PutBucketPolicy`、`DeleteBucketPolicy`、`PutReplicationConfiguration`、`PutBucketLifecycle`、`PutBucketVersioning`、`PutBucketObjectLockConfiguration`。几乎没有人会故意用对象级模式去授这些——你不会不小心依赖"一条对象授权还能改写桶策略"——所以撤掉这条路径基本不打破任何人。
- **只作用于 `Allow` 语句。** `Deny` 语句保持历史资源串,因此任何现存 `Deny` 都不会被削弱。窄修永远只*增加*拒绝。
- **读/列举族原样保留。** `bucket/*` 上的 `ListBucket` 照常工作。那是兼容敏感的部分,它等。

## 修复 {#the-fix}

匹配器在所有情况下都保留尾斜杠,只有一个例外:一条桶级 `Allow` 语句,正在为一个受保护动作求值,且兼容开关关闭。

```go
resource.WriteString(args.BucketName)
if args.ObjectName != "" {
    // "bucket/object" —— 不变
} else if args.BucketName == "" {
    resource.WriteByte('/') // KMS 两阶段哨兵 —— 不变
} else if legacyBucketResourceMatch.Load() ||
    statement.Effect != Allow ||
    !isSensitiveBucketMutation(args.Action) {
    resource.WriteByte('/') // Deny / 非敏感 / 开关开:历史行为
}
// else:裸 "bucket" —— 对象级 "bucket/*" 不再授予它
```

因为 `args.Action` 是**具体请求动作**,通配授权(`s3:*`)也被覆盖:通配在动作匹配那步命中,而轮到拼资源串时动作已经是具体的 `PutBucketPolicy`。裸桶资源(`arn:aws:s3:::bucket`)和 `*` 资源仍然命中,所以正确划定范围的授权——包括内置的 `readwrite` 策略——都不受影响。

逃生舱是 `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on`,启动时读一次。它恢复完整的历史行为——过度授予和过度阻断两个方向都恢复——供任何在调整策略期间仍需旧语义的运维使用。

## 你会察觉到什么 {#user-facing}

对绝大多数人:**什么都没有。** 对象访问不变,`bucket/*` 上的 `ListBucket` 不变,写对了的桶策略不变。

唯一可见的变化:当一个请求试图**修改桶的策略、复制、生命周期、版本控制或对象锁配置**,而它凭据的唯一匹配授权是一条对象级的 `bucket/*` 模式时,现在会返回 `AccessDenied`。这就是那条边界在被执行。如果某个部署确实依赖旧行为,设置 `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on`,并按自己的节奏把这些动作授在裸桶 ARN(`arn:aws:s3:::bucket`)上。

## 我们刻意留下的口子 {#left-open}

#20449 的一般性问题——`bucket/*` 会触及*任何*桶级操作,包括 `ListBucket`、`DeleteBucket`、以及生命周期/版本的*读取*——在这里**没有**被修复。彻底关掉它意味着撤销真实部署所依赖的授权,所以它属于将来一次带迁移路径的发布:一个在启动时点名每一条即将改变的存量策略(授予与拒绝两个方向都点)的审计、同一个兼容开关、以及告诉运维升级前该改什么的发布说明。

把边界写下来而非默认:今天只修正了这六个敏感写入。读/列举/删桶族在那次带迁移的变更落地前,仍按决定把 `bucket/*` 当作桶级授权。

## 收尾 {#closing}

一个补上的斜杠,把*"只有对象"*变成了*"连桶也算"*。诱人的修法是到处删掉斜杠,而这么做会打破半个世界都在依赖的列举写法,并悄悄削弱每一条写在 `bucket/*` 上的 `Deny`。我们发出的修复,只在"一条对象级授权本就绝不该触及"的地方删掉它——那些能把桶变公开的写入——别处一概不动。其余的都写了下来,等一个"打破它是被提前告知、而非凭空降临"的发布。

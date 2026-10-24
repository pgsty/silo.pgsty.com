---
title: "SN-2026-003：s3:versionid 条件求值缺陷与请求条件隔离加固"
linkTitle: "SN-2026-003：s3:versionid 条件修复"
date: 2026-08-04
author: "[冯若航](https://vonng.com) ([`@Vonng`](https://github.com/Vonng))"
description: "解析 s3:versionid 上的 Null 条件为何发生逻辑反转、为何仅修改 getConditionValues 会捅出 DeleteObjects XML 绕过漏洞，以及 SN-2026-003 与 SN-2026-005 的完整加固方案。"
url: "/zh/blog/security/s3-versionid-conditions/"
tags: ["Security", "IAM", "S3", "Versioning", "Bucket Policy", "SILO"]
---

**`SN-2026-003`** 与 **`SN-2026-005`** 涵盖了随 [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z)（提交 `80c2c9d03`、`2f55347f7`、`eee05a17c` 以及 [silo-pkg `v3.12.0`](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.0) 提交 `2b087a1`；[`pgsty/silo#40`](https://github.com/pgsty/silo/issues/40)、[`pgsty/silo#53`](https://github.com/pgsty/silo/issues/53)）发布的一组 S3 IAM 策略求值加固：
1. **`SN-2026-003`（`80c2c9d03`）**：当请求未携带 `versionId` 时，`getConditionValues` 依然无条件写入了 `args.ConditionValues["versionid"] = []string{""}`，导致针对 `s3:versionid` 的 IAM `Null` 条件恒判定为“键已存在”；而如果只修改 `getConditionValues`，又会导致批量删除 `DeleteObjects` 请求体中的 XML `<VersionId>` 绕过版本条件策略，必须配合 `authorizeRequestWithTags` 中的逐条重绑定一并修复。
2. **条件来源隔离（`2f55347f7`）**：严格隔离 URL 查询参数、HTTP 请求头、服务端内部派生键以及 `s3:ExistingObjectTag/<key>` 与 `s3:RequestObjectTag/<key>`，防止不可信查询串或请求头伪造内部条件键。
3. **`SN-2026-005`（`2b087a1` / `eee05a17c`）**：新增 `ParseConfigStrict`，在策略写入路径上拒绝退化的裸 ARN 前缀（`"arn:aws:s3:::"` 与 `"*arn:aws:s3:::"`）。

## 结论先行 {#summary}

1. **无条件写入空字符串切片导致 `Null` 判空反转**：在 `silo-pkg` 中，`nullFunc.evaluate` 通过检查键不存在或 `len(rvalues) == 0` 来判定条件键为空（`Null`）。由于 `getConditionValues` 无条件执行 `args.ConditionValues["versionid"] = []string{vid}`（当 `vid == ""` 时生成长度为 1 的 `[]string{""}`），`len(rvalues)` 永远为 `1`——导致 `Null: {"s3:versionid": "true"}` 永远为 `false`，而 `Null: {"s3:versionid": "false"}` 永远为 `true`。
2. **仅修改 `getConditionValues` 会在 `DeleteObjects` 上打开绕过口子**：在批量删除 `DeleteObjects`（`POST /?delete`）中，待删除的 `<VersionId>` 位于 XML 请求体的每个 `<Object>` 条目内，而非 URL 查询参数中。如果仅仅在 URL 没有 `versionId` 时省略 `"versionid"`，那么在 `DeleteObjects` 逐条鉴权时，用于禁止删除指定版本的策略（如 `Condition: {"Null": {"s3:versionid": "false"}}`）将因看不到 XML 中的 `<VersionId>` 而彻底失效！因此必须在 `authorizeRequestWithTags` 中根据 `ReqInfo.VersionID` 动态重绑定 `ConditionValues["versionid"]`。
3. **空白字符归一化消除 `Deny` 绕过**：业务 Handler 在读取 `versionId` 时调用了 `strings.TrimSpace(r.URL.Query().Get("versionId"))`，而 `getConditionValues` 却未做 `TrimSpace`。攻击者只需传入 `?versionId=V%20`（带尾随空格），即可在策略求值阶段绕过 `Deny StringEquals {"s3:versionid": "V"}`，随后在 Handler 阶段被去除空格并成功操作受保护的版本 `V`。

---

## 为什么 `s3:versionid` 上的 `Null` 条件完全反了 {#the-defect}

在 `silo-pkg/bucket/policy/condition/nullfunc.go` 中，IAM `Null` 条件算子按如下逻辑检查请求上下文中是否缺失某个条件键：

```go
func (f nullFunc) evaluate(values map[string][]string) bool {
    rvalues, ok := values[http.CanonicalHeaderKey(f.k.Name())]
    if !ok {
        return f.v
    }
    return f.v && len(rvalues) == 0
}
```

然而在 `cmd/signature-v4-utils.go` 中，`getConditionValues` 在函数末尾未判断 `vid` 是否为空便直接写入了 `"versionid"`：

```go
var vid string
if v := r.Form.Get("versionId"); v != "" {
    vid = v
} else if u, err := url.Parse(r.Header.Get(xhttp.AmzCopySource)); err == nil {
    vid = u.Query().Get("versionId")
}
args["versionid"] = []string{vid}
```

当调用方发起不带 `versionId` 的普通请求（如 `DELETE /bucket/key`）时，`vid` 为 `""`，`args["versionid"]` 被赋值为 `[]string{""}`（切片长度为 `1`）。结果：
- 通过 `"Null": {"s3:versionid": "true"}` 仅允许非版本化请求的策略，因 `len(rvalues) == 0` 为 `false` 而**错误拒绝**了所有正常请求；
- 通过 `"Null": {"s3:versionid": "false"}` 限制版本级操作的策略，因 `len(rvalues) > 0` 恒成立而**错误命中**了不带版本号的请求。

---

## 隐藏陷阱：为什么只省略空 `vid` 会捅出 `DeleteObjects` 绕过漏洞 {#the-trap}

乍看之下，修复似乎只需一行代码——仅当 `vid != ""` 时才写入 `args["versionid"] = []string{vid}`。但在审查调用链时，我们发现如果在 `getConditionValues` 里只做这一处改动，就会在 `DeleteMultipleObjectsHandler`（`POST /{bucket}?delete`）中打开一个致命的鉴权绕过口子。

与单对象删除 `DELETE /{bucket}/{object}?versionId=V` 不同，批量删除 `DeleteObjects` 请求的 URL 查询串里根本没有 `versionId`；真正的目标版本号写在 XML 请求体的每个 `<Object><Key>...</Key><VersionId>V</VersionId></Object>` 元素里。在 `DeleteMultipleObjectsHandler` 内部，服务端会遍历每条 XML 对象，将 `obj.VersionID` 写入请求上下文（`ReqInfo.VersionID = obj.VersionID`），然后针对 `DeleteObjectAction` 调用 `authorizeRequestWithTags`。

试想管理员配置了如下策略，允许普通删除（创建删除标记），但通过 `Null: false` 条件严禁永久删除任何历史版本：

```json
{
  "Effect": "Deny",
  "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"],
  "Resource": ["arn:aws:s3:::mybucket/*"],
  "Condition": {
    "Null": {"s3:versionid": "false"}
  }
}
```

由于 `authorizeRequestWithTags` 内部调用的 `getConditionValues(r, ...)` 只检查 HTTP 请求 URL 上的 `r.Form.Get("versionId")`，根本不看 `ReqInfo.VersionID`——如果只改 `getConditionValues` 使其在 URL 无 `versionId` 时省略 `"versionid"`，那么在 `DeleteObjects` 逐条鉴权时，`args["versionid"]` 将永远缺失，上述 `Deny` 策略将完全失效！更进一步，攻击者甚至可以在批量删除 URL 上故意挂一个诱饵参数（`POST /mybucket?delete&versionId=decoy`），同时在 XML 请求体里填入受保护的 `<VersionId>target-v1</VersionId>` 来欺骗基于具体版本号匹配的策略！

---

## 完整的双边修复（`80c2c9d03`） {#the-fix}

提交 `80c2c9d03` 将两端协同闭环：

1. **在 `getConditionValues` 中仅当 `vid != ""` 时写入 `"versionid"`**：
   ```go
   if vid != "" {
       args["versionid"] = []string{vid}
   }
   ```
2. **在 `authorizeRequestWithTags`（`cmd/auth-handler.go`）中针对 `DeleteObjectAction` 从 `ReqInfo.VersionID` 重绑定 `"versionid"`**：
   ```go
   if action == iampolicy.DeleteObjectAction {
       reqInfo := logger.GetReqInfo(ctx)
       if vid := strings.TrimSpace(reqInfo.VersionID); vid != "" {
           conditionValues["versionid"] = []string{vid}
       } else {
           delete(conditionValues, "versionid")
       }
   }
   ```

为什么只在 `action == iampolicy.DeleteObjectAction` 时用 `ReqInfo.VersionID` 覆盖 `conditionValues["versionid"]`，而不是对所有动作一刀切覆盖？因为在 `CopyObjectHandler` 中，`ReqInfo.VersionID` 存放的是目标对象的查询参数，而针对复制源执行的 `GetObjectAction` 鉴权必须校验来自请求头 `x-amz-copy-source` 的源版本号（`?versionId=...`）。将 `ReqInfo.VersionID` 重绑定限定在 `DeleteObjectAction`，既保证了单对象 `DeleteObjectHandler` 与批量 `DeleteMultipleObjectsHandler` 始终校验当前真正要删除的版本号，又在 `reqInfo.VersionID` 为空时显式执行 `delete(conditionValues, "versionid")`，彻底废掉了在批量删除 URL 上挂载 `?versionId=query-level-decoy` 诱饵参数的混淆手段。

---

## 消除空白字符归一化差异 {#trim}

在排查所有读取 `versionId` 的入口时，我们注意到各对象 Handler（`GetObjectHandler`、`HeadObjectHandler`、`DeleteObjectHandler`、`PutObjectRetentionHandler` 等）均通过以下方式提取版本号：

```go
versionID := strings.TrimSpace(r.URL.Query().Get(xhttp.VersionID))
```

然而 `getConditionValues` 在读取 `r.Form.Get("versionId")` 及 `x-amz-copy-source` 中的 `u.Query().Get("versionId")` 时却**没有**调用 `strings.TrimSpace`。

这意味着，如果策略通过 `"StringEquals": {"s3:versionid": "v1"}` 拒绝访问特定版本 `v1`，调用方只需请求 `?versionId=v1%20`（末尾带一个空格），策略求值时看到的条件值就是 `"v1 "`——从而绕过 `StringEquals` 拒绝规则——随后业务 Handler 将 `"v1 "` 去除空格还原为 `"v1"` 并成功读取或删除该受保护版本。在 `getConditionValues` 中对查询串 `versionId` 与 `x-amz-copy-source` 的 `versionId` 统一调用 `strings.TrimSpace` 彻底消除了这一解析偏差。

---

## 调用链影响与请求条件来源隔离（`2f55347f7`） {#impact}

| 操作类型 | `s3:versionid` 来源 | `20260804` 之前行为 | Server `20260804` 行为 |
|---|---|---|---|
| `GetObject` / `DeleteObject`（未传 `versionId`） | 无 | `["versionid"] = [""]`（`Null:true` 失败） | 省略该键（`Null:true` 正常命中） |
| `GetObject` / `DeleteObject`（`?versionId=v1%20`） | URL 查询参数 `versionId` | 策略看到 `"v1 "`，Handler 实际操作 `"v1"` | 策略与 Handler 均归一化为 `"v1"` |
| `CopyObject`（`x-amz-copy-source: /b/k?versionId=v1`） | `x-amz-copy-source` 查询参数 | 未去除首尾空白 | 统一去除首尾空白 |
| `DeleteObjects`（`POST /?delete` 含 `<VersionId>`） | 逐条 `ReqInfo.VersionID` | 忽略 XML `<VersionId>`，误读 URL 查询串 | 按 XML 条目逐条重绑定，忽略 URL 诱饵参数 |

在配套提交 `2f55347f7`（[`pgsty/silo#53`](https://github.com/pgsty/silo/issues/53)）中，我们还对 `getConditionValues` 中的其余请求条件键实施了来源隔离加固：
- **保护内部保留键**：客户端传入的 URL 查询参数与 HTTP 请求头不再被允许覆盖服务端内部派生的条件键（`username`、`userid`、`principaltype`、`authtype`、`signatureversion`、`tlsVersion`、`cipherSuite`）。
- **`s3:signatureAge`**：直接基于已验签的 SigV4 时间戳计算，不再信任客户端传入的同名参数。
- **对象标签条件隔离**：`s3:ExistingObjectTag/<key>` 严格只从已存储的对象元数据标签填充，而 `s3:RequestObjectTag/<key>` 严格只从当前请求的 `x-amz-tagging` 请求头填充。

---

## SN-2026-005：拒绝退化的裸 ARN 前缀 {#sn-2026-005}

在同一轮 IAM 策略审计中，我们还排查了 **`SN-2026-005`**（[silo-pkg `v3.12.0`](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.0) 提交 `2b087a1`，并在 [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) 提交 `eee05a17c` 中接入）：当策略中的资源字符串写成了既无桶名也无对象后缀的退化前缀（如 `"arn:aws:s3:::"` 或 `"*arn:aws:s3:::"`）时会发生什么？

由于旧解析器在剥离 `arn:aws:s3:::` 前缀后直接接受了空资源模式 `""`，该模式无法匹配任何实际的桶或对象。在普通 `Allow` 语句中它只是一条无效死规则；但在**使用 `Resource` 的 `Deny` 语句**或**使用 `NotResource` 的 `Allow` 语句**中，退化的 `arn:aws:s3:::` 会导致拒绝规则或排除集合完全轮空（Fail-Open）！

为了防止管理员误写入会导致策略静默失效的裸前缀，同时绝不让存量集群因历史数据在升级启动时崩溃：
- `silo-pkg v3.12.0` 新增了 `policy.ParseConfigStrict`，明确拒绝退化的裸 ARN 前缀（`arn:aws:s3:::` 与 `*arn:aws:s3:::`）。
- Server `20260804`（`eee05a17c`）在所有策略**写入**路径（桶策略、具名 IAM 策略、服务账号及 STS 内联策略）上调用 `ParseConfigStrict`；而持久化策略的加载路径继续使用宽容模式的 `ParseConfig`，确保存量集群平滑启动。

---

## 为什么 `SN-2026-003` 作为安全公告而非 CVE 跟踪 {#not-a-cve}

触发 `s3:versionid` 条件求值缺陷的前提是调用方已通过认证，且目标策略显式依赖了 `s3:versionid` 条件算子（`Null`、`StringEquals` 或 `StringNotEquals`）。不带该条件的标准 `s3:DeleteObjectVersion` 动作权限检查不受影响。我们将条件求值与 `DeleteObjects` 重绑定修复归入 `SN-2026-003`，将裸 ARN 前缀写入拦截归入 `SN-2026-005`。

---

## 边界说明与关联修复 {#boundary}

1. **`DeleteObjects` 的 Object Lock 治理模式绕过检查（`75a6734e4` / `#104`）**：在审查 `DeleteMultipleObjectsHandler` 的过程中，我们同步梳理了批量删除中请求头与逐条保留锁的交互；随后在 [Server 20260903](/zh/blog/security/20260903-server-hardening/)（`75a6734e4`，`SN-2026-008`）中收紧了 `x-amz-bypass-governance-retention` 的逐条鉴权边界。
2. **Snowball `PutObjectExtract` 的 `minio.versionId` PAX 扩展头**：在本次 `versionId` 审计中记录归档，并已在 [Server 20261018](/zh/blog/security/20260926-governance-retention-bypass/)（`SN-2026-016`，`14042b5aa`）中彻底封堵。
3. **其余身份条件键（`username`、`userid`、`signatureversion`、`authType`）**：`80c2c9d03` 有意将空切片省略限定在 `s3:versionid`，而不改变已认证请求上恒有定义的身份类条件键语义。

---

## 回归验证 {#verification}

`cmd/signature-v4-utils_test.go`、`cmd/auth-handler_test.go` 与 `cmd/bucket-policy_test.go` 中的回归测试覆盖并锁定了以下场景：
- 在带版本号与不带版本号的 `GetObject`、`DeleteObject`、`CopyObject` 及 `DeleteObjects` 请求下，验证 `Null: {"s3:versionid": "true"}` 与 `Null: {"s3:versionid": "false"}` 的求值结果；
- 验证 `?versionId=v1%20` 尾随空格在 `Deny StringEquals {"s3:versionid": "v1"}` 下被正确拦截；
- 验证携带 `POST /bucket?delete&versionId=query-level-decoy` 诱饵参数时，XML 请求体内的版本化与非版本化 `<Object>` 条目均严格按条目自身重绑定；
- 验证 `ParseConfigStrict` 对 `arn:aws:s3:::` 与 `*arn:aws:s3:::` 的拦截。

## 源码参考 {#source}

- [`80c2c9d03`](https://github.com/pgsty/silo/commit/80c2c9d03) — `s3:versionid` 空值省略、空白字符归一化与 `DeleteObjects` 逐条重绑定（`SN-2026-003`）
- [`2f55347f7`](https://github.com/pgsty/silo/commit/2f55347f7) — 请求条件键来源隔离（`#53`）
- [`eee05a17c`](https://github.com/pgsty/silo/commit/eee05a17c) / [`silo-pkg@2b087a1`](https://github.com/pgsty/silo-pkg/commit/2b087a1) — `ParseConfigStrict` 拒绝退化裸 ARN 前缀（`SN-2026-005`）

## 总结 {#closing}

随 [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) 发布的 `80c2c9d03` 与 `eee05a17c`（配合 `silo-pkg v3.12.0`）修复了单对象与批量 `DeleteObjects` 路径上的 `s3:versionid` 条件求值语义，并在策略写入入口拦截了退化的裸 S3 ARN 前缀。

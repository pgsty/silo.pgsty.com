---
title: "总量未知时，进度条应该说什么"
linkTitle: "文件夹下载进度"
date: 2026-08-23
lastmod: 2026-09-02
author: "冯若航"
description: "文件夹流式 ZIP 下载显示 NaN% 的修复 PRD：不改变服务端 API 与普通文件下载，用诚实的不确定进度替代非法百分比。"
tags: [设计, Console, 下载]
weight: 20
url: "/zh/blog/design/dir-percentage/"
---

> **状态**：已随 SILO Console 2.2.0 发布（`16960f7ab`）；服务端自更新 Console pin（`4d6e1ea8e`）起内嵌该修复 · **优先级**：P1 · **归属**：[`pgsty/silo-console`](https://github.com/pgsty/silo-console) · **关联问题**：[`pgsty/silo#62`](https://github.com/pgsty/silo/issues/62) · **PRD 复核**：Claude Fable 5（`xhigh`）— **APPROVE** · **实现复核**：Claude Fable 5（`xhigh`），2026-08-23 — **APPROVE**，无 P0/P1/P2 发现

SILO Console 下载文件夹时，Downloads / Uploads 面板会显示 `NaN%`。ZIP 通常仍在正常传输，存储对象也完好无损，但进度条已经从“总量未知”错误地跨进了一个非法的确定进度状态。用户看到一条近乎满格的进度条，以为下载失败或已经完成，于是重复点击。

建议的修复刻意保持狭窄：

> 只有当下载拥有一个有限、正数、并且适用于当前响应字节的总量时，才能进入 determinate 状态；否则必须保持 indeterminate，直到完成、失败或取消。

服务端继续流式生成 ZIP，普通文件继续显示百分比。前端只增加一道安全计算边界，复用已经存在的 indeterminate 渲染，再补齐一条缺失的取消状态转换。本文说明为什么这套方案既充分，又是最小且诚实的修复。

## 已观察到的故障 {#failure}

这个缺陷存在于当前 `silo-console v2.1.1`，Silo `RELEASE.2026-08-06T00-00-00Z` 内嵌的正是这一版本。

复现步骤：

1. 在某个 prefix 下放入若干对象，例如 `folder/`。
2. 停留在父目录，选择 `folder/` 并点击 **Download**。
3. 在传输完成前打开 **Downloads / Uploads**。
4. 任务行显示 `NaN%`，而 ZIP 请求仍在继续。

运行时验证使用了一个约 88.7 MiB 的 prefix，并对 Chromium 限速以保留观察窗口。两次独立下载都进入了相同的 `NaN%` 状态。

这是前端正确性问题，不代表对象损坏、磁盘格式变化或 S3 `GET` 失败。

## 实际发生了什么 {#root-cause}

可见的 `NaN%` 是三层契约错位的最终结果。

### Prefix 没有对象大小 {#prefix-size}

S3 的文件夹是 common prefix，不是实际存储的目录对象。在列表模型里，prefix 以 `/` 结尾并携带 `size=0`。Console 已经把这种大小显示为 `-`，正确地表达了“不适用”。

生成的 API 模型为 `size` 标记了 `omitempty`，所以逻辑上的零不会出现在列表 JSON 中。单选下载 thunk 却把 `object.size` 原样传给辅助函数：prefix 与零字节对象在运行时提供的是 `undefined`（人工构造的 prefix 记录也可能提供 `0`）。两者都不是有效分母。

### 流式 ZIP 没有事先可知的网络长度 {#streamed-zip}

服务端通过末尾的 `/` 识别文件夹，递归列出对象，再把 `zip.Writer` 接到 `io.Pipe` 上。对象一边读取、一边 Deflate、一边复制进 HTTP 响应，档案生成多少就发送多少。

这是一项有价值的行为：服务端不用把完整 ZIP 全部放进内存或临时磁盘，就能尽早发出首字节。它也带来一个同样刻意的结果：发送响应头时，最终压缩字节数尚不存在，因此响应只有 `Content-Type: application/zip` 和文件名，没有 `Content-Length`。

源对象大小之和不能替代这个总量。对象大小是压缩前字节；`ProgressEvent.loaded` 统计的是 ZIP 压缩与封装后的响应字节。它们不是同一个单位。

### 收到 progress 事件，不代表百分比可计算 {#progress-event}

客户端当前对每个事件都执行：

```ts
Math.round((event.loaded / fileSize) * 100)
```

Prefix 的分母为零或缺失。根据实际值与事件，JavaScript 会产生 `NaN`（`loaded / undefined` 或 `0 / 0`）或 `Infinity`（正数字节除以零）。

progress callback 随后把非有限值写入 Redux，同时设置 `waitingForFile=false`。第二个操作才是决定性的状态错误：任务仅仅因为“来了一个事件”就离开了现有 indeterminate 分支，而不是因为事件真的提供了可用总量。确定进度组件拿到非法值，最终渲染出非法标签。

完整链路如下：

```text
common prefix: size = 0
        |
        v
download(..., fileSize = 0)
        |
        v
流式 Deflate ZIP，没有 Content-Length
        |
        v
event.loaded / 0 => NaN 或 Infinity
        |
        v
非法百分比进入 Redux；waitingForFile 变成 false
        |
        v
determinate ProgressBar 渲染 NaN%
```

普通非空文件之所以不出问题，是因为服务端可以 stat 对象、设置 `Content-Length`，列表中的大小也为正数。如果浏览器为空响应触发 progress 事件，零字节文件虽然是真对象，却会抵达与 prefix 相同的算术边界，因此必须纳入回归契约。

## 产品契约 {#contract}

UI 只需要诚实地区分两种情况：

- **Determinate**：已传输字节与总字节都已知，而且单位相同。
- **Indeterminate**：请求正在进行，但总量未知。

由此得到四条承重不变量：

```text
determinate  => total 有限且 total > 0
determinate  => percentage 有限且 0 <= percentage <= 100
unknown total => indeterminate
terminal state => 非 indeterminate
```

这些不变量比 `objectPath.endsWith("/")` 更一般：无需发明对象类型特例，就能同时覆盖 prefix、零字节文件、异常元数据和未来任何未知长度响应。

## 目标与非目标 {#scope}

### 目标 {#goals}

1. 文件夹下载不再显示 `NaN%`、`Infinity%` 或伪造的确定百分比。
2. 总长度未知的传输使用现有 indeterminate 动画。
3. 总长度已知的普通文件保留当前百分比体验。
4. 完成、失败与取消都必须离开 indeterminate。
5. 零字节文件不得产生非有限百分比，并且仍能成功完成。
6. 非有限或越界下载百分比不得进入 Redux。
7. 修复可以先在 Console 独立发布，再由 Silo 更新依赖。

### 非目标 {#non-goals}

- 不在服务端预生成或缓存完整 ZIP。
- 不把文件夹内对象的未压缩大小之和冒充网络传输总量。
- 不重构整个 Object Manager 状态模型。
- 不把文件夹切换到当前“点击即完成”的 `BrowserDownload` 路径。
- 不在这里解决 `XMLHttpRequest.responseType="blob"` 的浏览器内存占用。
- 不改变取消记录是否保留到用户手动清理的现有产品行为。
- 不重新设计 HTTP 响应头发出之后，流式 ZIP 中途失败的错误表达。
- 不改变 S3 API、Console API、对象布局或 ZIP 内容。

这些都是合理的后续工作，但把它们绑进当前缺陷会扩大风险，却不是恢复诚实进度所必需的。

## 最终决策 {#decision}

最小生产修复由四部分组成。

### D1. 只使用有效总量计算 {#d1}

增加一个不依赖 DOM 和 Redux 副作用的小型纯函数：

```ts
type DownloadProgressEvent = Pick<
  ProgressEvent,
  "loaded" | "lengthComputable" | "total"
>;

export const calculateDownloadPercent = (
  event: DownloadProgressEvent,
  objectSize: number,
): number | null => {
  let total: number | null = null;

  if (Number.isFinite(objectSize) && objectSize > 0) {
    total = objectSize;
  } else if (
    event.lengthComputable &&
    Number.isFinite(event.total) &&
    event.total > 0
  ) {
    total = event.total;
  }

  if (
    total === null ||
    !Number.isFinite(event.loaded) ||
    event.loaded < 0
  ) {
    return null;
  }

  return Math.min(
    100,
    Math.max(0, Math.round((event.loaded / total) * 100)),
  );
};
```

总量来源的优先级用于保持兼容：

1. 有限且为正的 `objectSize` 保留普通文件当前算法。
2. 当对象大小不可用，但浏览器声明响应长度可计算，且 `event.total` 有限为正时，使用响应总量。
3. 其余情况返回 `null`：此时还不存在诚实的百分比。

辅助函数的输出契约是闭合的：要么是 `null`，要么是 `[0,100]` 内的有限数。

### D2. 未知总量保持 indeterminate {#d2}

XHR handler 只 dispatch 真实百分比：

```ts
req.addEventListener("progress", (event) => {
  const percent = calculateDownloadPercent(event, fileSize);

  if (percent !== null) {
    progressCallback(percent);
  }

  // 没有有效总量：保留 waitingForFile=true，让现有 UI 继续保持
  // indeterminate，而不是制造一个 determinate 数字。
});
```

下载任务本来就以 `waitingForFile=true` 创建，`ObjectHandled` 也已经把这个状态渲染成 `variant="indeterminate"`。没有必要把 Redux 扩成 `number | null`，也不用再加一个布尔值或修改 MDS。

首次获得有效百分比时，现有 `updateProgress` 会写入数值并设置 `waitingForFile=false`。如果整个请求始终没有有效总量，任务就保持 indeterminate，直到终态 action 到来。

### D3. 让取消成为真正的终态 {#d3}

完成和失败路径已经会清除 `waitingForFile`，取消路径没有。需要在 `cancelObjectInList` 中补上：

```ts
item.waitingForFile = false;
```

没有这一行，修复后的 prefix 下载会在 abort 后继续进入 indeterminate 渲染分支，遮住 Cancelled 状态。任务行继续遵循现有产品行为：保留一条已取消记录，由用户手动移除。本次不要求自动清理。

XHR 边界还需要一条事件顺序守卫。`abort()` 会先触发 `readystatechange(DONE, status=0)`，随后才触发 `abort` 事件；如果不提前返回，通用 DONE 分支会先把请求标成失败，`onabort` 再把它标成取消。DONE/status zero 因此交给专用的 `onerror` 或 `onabort` handler 处理，`onabort` 同时删除已存储的请求引用。

### D4. 还原被省略的零字节大小 {#d4}

单选下载 thunk 改为传递 `object.size || 0`，与另一个下载入口保持一致。这样会在 `Blob.size === fileSize` 完成校验之前，还原 API 模型省略的逻辑零，使 HTTP 200 的零字节对象以 100% 完成，而不是被误报为 incomplete。

### D5. 服务端流式行为保持不变 {#d5}

文件夹 handler 继续通过 `io.Pipe` 生成 Deflate ZIP，并且不设置 `Content-Length`。API、档案、存储和资源管理契约均不变化。

## 状态机 {#state-machine}

| 状态 | `waitingForFile` | `percentage` | 终态标志 | 表现 |
| --- | ---: | ---: | --- | --- |
| 排队 / 尚无有效进度 | `true` | `0` | 无 | indeterminate |
| 未知总量传输中 | `true` | `0` | 无 | indeterminate |
| 已知总量传输中 | `false` | `0..100` | 无 | 确定百分比 |
| 完成 | `false` | `100` | `done=true` | 成功 |
| 失败 | `false` | 最后有效值 | `failed=true, done=true` | 错误 |
| 取消 | `false` | `0` | `cancelled=true, done=true` | 已取消 |

状态不从 determinate 回退到 indeterminate。如果取得过有效百分比，之后某个事件又没有有效总量，handler 保留最后一个有效值即可。

现有 reducer 会在 Failed 与 Cancelled 时同时设置 `done=true`。`ObjectHandled` 依据 `done` 把关闭按钮从“中止请求”切换为“移除记录”；本次保持这一行为。取消后的 Redux 数值仍为 `0`，但现有 `ProgressBarWrapper` 会因为 `ready=true` 渲染一条满格橙色终态进度条并显示 Cancelled 标签；这种既有表现不属于本次修复范围。

`waitingForFile` 并不是“没有可计算进度”的理想长期命名。重命名它，或用 discriminated union 替代当前多个布尔值，都能改善模型，但那属于独立重构。本次所需的状态和渲染已经存在，复用它的兼容风险最低。

## 为什么这套方案充分 {#proof}

可以按情况验证修复的闭合性。

### 普通非空文件 {#case-file}

`objectSize > 0`，辅助函数继续使用当前分母。结果有限且经过边界限制，`updateProgress` 进入 determinate，完成时仍为 100%。

### 当前流式文件夹 {#case-folder}

`objectSize` 被归一化为 `0`，同时 `lengthComputable=false`、`event.total=0`。辅助函数返回 `null`；没有非法 action 被 dispatch，因此任务保持 indeterminate。完成时现有 reducer 设置 `waitingForFile=false`、`percentage=100`、`done=true`。

### 未来提供真实长度的响应 {#case-future}

如果代理或未来服务端实现提供了可信响应总量，`lengthComputable=true` 且 `event.total>0`。同一份代码会自动给出真实百分比，不需要再次修改产品逻辑。

### 零字节文件 {#case-zero}

列表中被省略的大小先还原为零，此后两个总量都为零，中间百分比在数学上未定义。任务在通常极短的生命周期里保持 indeterminate；零字节 Blob 与归一化后的预期大小相等，成功响应随即切换到 100%。整个过程不会计算 `0/0`。

### 失败与取消 {#case-terminal}

失败路径本来就会离开 indeterminate；新增的取消转换让 abort 也同样进入终态。终态任务不会仅仅因为总量未知而继续表现得像正在运行。

从数学上说，只有当 `total` 属于 `(0, +infinity)` 才会执行除法，结果随后被限制到 `[0,100]`。因此 `NaN` 和 `Infinity` 都不可能穿过计算边界进入 Redux 或确定进度组件。

## 被否决的替代方案 {#alternatives}

### 缓存 ZIP 以获得 Content-Length {#alt-buffer}

服务端可以先在内存或临时文件中生成完整档案，测量以后再发送。这样能得到精确网络总量，但代价是内存或磁盘压力、首字节延迟、清理复杂度与更差的并发下载表现。一个可观测性缺陷不足以成为放弃流式行为的理由。

### 对 prefix 下对象大小求和 {#alt-sum}

这个和是未压缩逻辑数据；`event.loaded` 是压缩响应加 ZIP 封装后的字节。单位不同，进度条可能停在 100% 以下、提前超过 100%，或随着压缩率而不是传输完成度移动。否决。

### 把非法进度变成 0% {#alt-zero}

这只会隐藏字符串，却会撒另一个谎：determinate 0% 表示总量已知，只是还没有传输。用户仍然会把它理解为下载卡死。未知就应该保持未知。

### 只特判以 `/` 结尾的路径 {#alt-folder-check}

它能修报告中的 prefix，却会漏掉真实零字节对象、非法元数据与其他未知长度响应。正确边界是 denominator 是否可用，而不是对象类型。

### 把文件夹交给 `BrowserDownload` {#alt-browser-download}

当前大文件路径创建 `<a>` 并在点击后立刻调用完成回调。它无法报告真实完成、Console 内取消或后续 HTTP 失败。它可以成为未来流式下载设计的基础，但今天使用它只会用另一个谎替换当前的谎。

### 在 ProgressBar 内部吞掉非法值 {#alt-component}

通用组件守卫可以作为第二道防线，但它会把非法数据留在 Redux，并向所有其他消费者隐藏错误状态转换。主要修复应该位于“进度成为应用状态”的边界。

### 现在引入 `percentage: number | null` {#alt-null-state}

如果要重新设计 Object Manager，discriminated progress state 会比当前布尔值组合更干净。但在保留 `waitingForFile`、`done`、`failed`、`cancelled` 的同时再加入 `null`，只会制造更多矛盾组合。彻底移除旧字段又超过当前缺陷所需范围。现在复用已经能渲染的 indeterminate，状态重构另立任务。

## 需求与验收 {#requirements}

### 功能需求 {#functional}

- **FR1：** 总量未知时，任务保持 indeterminate。
- **FR2：** 对象大小有限为正时，普通文件保留确定百分比。
- **FR3：** 只有 `lengthComputable=true` 时，有限为正的 `event.total` 才能作为回退。
- **FR4：** 所有 dispatch 的百分比都必须有限且位于 `[0,100]`。
- **FR5：** 零字节文件不显示非有限进度，并且最终成功。
- **FR6：** 完成、失败与取消都必须离开 indeterminate。
- **FR7：** 版本化对象、匿名下载、预览与长文件名入口保持现有调用契约。

### 非功能需求 {#non-functional}

- 不增加服务端 CPU、内存、磁盘缓存或请求成本。
- 不增加前端依赖或构建步骤。
- 不改变 S3 API、Console API、ZIP 内容或存储对象。
- 计算函数必须能在没有 DOM 与真实 store 的环境中测试。
- TypeScript typecheck 与生产前端构建必须通过。

### 验收标准 {#acceptance}

1. 没有 `Content-Length` 的文件夹 ZIP 传输期间，任务行显示 indeterminate 动画且没有百分比文本。
2. 成功完成后，任务显示成功/100%，ZIP 可以正常打开。
3. 普通非空文件继续显示有限的确定进度，并以 100% 完成。
4. 零字节文件不显示 `NaN%` 或 `Infinity%`，并且成功完成。
5. 取消未知总量下载会 abort 请求并显示 Cancelled，而不是继续播放活动动画。
6. 任何下载路径都不能把非有限或越界百分比放进 Redux。

## 测试计划 {#tests}

### 纯计算矩阵 {#unit-tests}

使用现有 `@playwright/test` runner 测试纯模块，不增加测试框架。这需要在 `web-app/playwright.config.ts` 中新增一个无依赖的 `unit` project，例如使用 `testMatch: /.*\.unit\.ts/`。现有 `chromium` project 依赖针对 `localhost:9090` 真实实例的登录 setup，纯计算与 reducer 测试不应被该环境门控。此为纯配置变更，不引入新依赖。

| 场景 | `loaded` | `objectSize` | `lengthComputable` | `event.total` | 期望 |
| --- | ---: | ---: | --- | ---: | --- |
| 普通文件一半 | 50 | 100 | false | 0 | `50` |
| Common prefix | 1024 | 0 | false | 0 | `null` |
| 初始零除零 | 0 | 0 | false | 0 | `null` |
| 响应总量回退 | 50 | 0 | true | 200 | `25` |
| 零总量不可用 | 0 | 0 | true | 0 | `null` |
| loaded 超过总量 | 150 | 100 | true | 100 | `100` |
| 非法对象大小 | 10 | `NaN` | false | 0 | `null` |
| 被省略的零大小 | 10 | `undefined` | false | 0 | `null` |
| 非法响应总量 | 10 | 0 | true | `Infinity` | `null` |
| 负 loaded | -1 | 100 | true | 100 | `null` |

### 状态测试 {#state-tests}

直接覆盖状态转换契约：

1. 新下载以 `waitingForFile=true` 开始。
2. 没有有效 progress action 时保持 indeterminate。
3. 有效 progress 产生有限值并设置 `waitingForFile=false`。
4. complete 产生 `done=true`、`waitingForFile=false`、`percentage=100`。
5. failure 产生 `failed=true`、`done=true`、`waitingForFile=false`。
6. cancel 产生 `cancelled=true`、`done=true`、`waitingForFile=false`、`percentage=0`。

### 浏览器回归 {#e2e-tests}

使用真实 Console 测试实例与 Chromium：

1. 创建临时桶，在 `folder/` 下放入多个对象。
2. 从父目录选择 prefix 并开始下载。
3. 使用 CDP 限制下载速度，保证中间状态可观察。
   限速用例需用 `test.setTimeout` 放宽默认 30 秒超时。
4. 打开 Downloads / Uploads，确认任务存在、没有百分比标签，也不存在 `NaN%` 或 `Infinity%`。
5. 取消下载并验证 Cancelled 终态。
6. 在 `finally` 中恢复网络条件。
7. 不限速再次下载，等待浏览器下载事件并验证 ZIP。
8. 对普通非空文件与零字节文件重复相应断言。
9. teardown 删除桶、对象、下载与临时文件。

当前 Playwright 项目只启用了 Chromium，因此 CDP 是可接受的测试机制。如果以后启用 Firefox 或 WebKit，纯函数和状态测试保持跨浏览器，只让限速观察测试受 Chromium project 门控。

## 实现边界 {#implementation}

预计 Console 变更：

1. 新增 `downloadProgress.ts`，承载纯计算逻辑。
2. 修改 `Objects/utils.ts`：只 dispatch 非 null 百分比，把 status-zero 终态交给专用 handler，并清理已取消请求。
3. 在单选下载 thunk 中还原被省略的零大小。
4. 修改 `cancelObjectInList`，清除 `waitingForFile`。
5. 使用现有依赖补充计算、状态与浏览器回归，并在 `playwright.config.ts` 中新增无依赖的 `unit` project。

预计保持不变：

- Go 文件夹下载 handler 与流式 ZIP。
- `ObjectHandled`、`ProgressBarWrapper` 与 MDS。
- `IFileItem.percentage: number` 及现有 thunk callback 类型。
- S3 与 Console API 路径。
- 存储对象与档案格式。

## 交付与回滚 {#delivery}

修复归属于 `pgsty/silo-console`，而不是当前收到报告的 Silo 服务端仓库。

交付顺序：

1. 把 #62 转移或交叉关联到 `pgsty/silo-console`。
2. 实现边界明确的 Console 修改。
3. 通过 typecheck、生产构建、纯函数/状态测试与真实浏览器回归。
4. 发布新的 Console 版本。
5. 更新 Silo 固定的 Console pseudo-version 或发布依赖。
6. 构建 Silo 候选版本，重复文件夹、普通文件、零字节、取消与 ZIP 完整性验证。
7. 发布 Silo，并在 Issue 中记录受影响与已修复版本。

没有数据迁移。如果前端修改出现回归，Silo 只需回退 Console 依赖；服务端数据与 API 行为保持兼容。

## 完成定义 {#done}

- [x] 计算函数只返回 `null` 或有限的 `[0,100]` 数字。
- [x] 活跃的未知总量文件夹下载渲染 indeterminate。
- [x] 普通文件保留确定进度。
- [x] 零字节文件不渲染非法进度。
- [x] 完成、失败与取消任务都离开 indeterminate。
- [x] 流式 ZIP 与服务端响应契约保持不变。
- [x] typecheck、生产构建与自动化回归已在本地通过。
- [ ] Console 发布完成。
- [ ] Silo 更新 Console 依赖并通过候选版本验证。

## 后续工作 {#follow-ups}

四项相邻改进应该分别建立设计档案：

1. 把大文件夹直接流式写入浏览器或文件系统，避免在内存中持有完整 Blob。
2. 用 discriminated progress/terminal state 替代 Object Manager 的布尔值组合。
3. 改进响应头已经发出后，ZIP 失败的端到端完整性与错误表达。
4. 为共享进度组件增加通用非有限值守卫，作为第二道防线。
5. 修复既有的 Blob JSON 错误解码与 HTTP 失败路径请求引用清理问题。

它们都不是停止当前 UI 撒谎所必需的。下一阶段维护迭代应先恢复最小而诚实的契约：已知总量才显示百分比，未知总量就保持未知。

---
title: "总量未知时，进度条应该说什么"
linkTitle: "文件夹下载进度"
date: 2026-08-23
lastmod: 2026-09-16
author: "冯若航"
summary: "文件夹流式 ZIP 下载显示 NaN% 的修复设计：不改变服务端流式 API 与普通文件下载，用诚实的不确定进度（Indeterminate）替代非法百分比。"
tags: [设计, Console, 下载]
weight: 20
draft: false
url: "/zh/blog/design/dir-percentage/"
---

在 SILO Console v2.1.1 中下载文件夹时，**Downloads / Uploads**（下载/上传）抽屉会显示 `NaN%`。尽管后端的流式 ZIP 归档仍在正常传输、底层存储对象也完好无损，但进度条却从“总量未知”错误地跳入了确定进度（determinate）渲染状态——导致运维人员误以为下载已卡死或失败，进而反复点击 **Download**。

该修复已随 [Console 2.2.0](/zh/blog/release/console-2.2.0/)（提交 `16960f7ab`，跟踪议题 [#62](https://github.com/pgsty/silo/issues/62)）发布，并自 [Server 20260903](/zh/blog/release/silo-20260903/)（`edc8be6ed`）起内嵌于服务端。其核心准则只有一条：

> 只有当下载任务拥有一个有限、正数且适用于当前响应字节流的总量时，才能进入确定百分比（determinate）模式；否则必须保持不确定（indeterminate）动画状态，直至完成、失败或取消。

（后续发布的 [Console 2.4.1](/zh/blog/release/console-2.4.1/#browser) 进一步将文件夹与多选下载演进为文件流写入与浏览器原生下载交接，不再将完整 ZIP 缓存在浏览器内存 `Blob` 中；详见文末[后续演进](#later-contract)。）

## 可观察故障 {#failure}

在 SILO Console v2.1.1 中：

1. 在某个公共前缀（如 `folder/`）下上传若干对象；
2. 停留在父级存储桶列表页，勾选 `folder/` 并点击 **Download**；
3. 在传输完成前打开 **Downloads / Uploads** 面板；
4. 当前下载行显示 `NaN%`，而底层 ZIP 流仍在继续传输。

## 根因分析 {#root-cause}

界面上出现的 `NaN%` 是 S3 前缀元数据、服务端流式 ZIP 响应与前端 XHR 进度算术三层契约错位共同作用的结果。

### 公共前缀没有对象大小 {#prefix-size}

S3 中的“文件夹”只是逻辑上的公共前缀（Common Prefix），并非实际存储的目录对象。在列表模型中，前缀以 `/` 结尾并携带逻辑大小 `size = 0`（Console 列表将其渲染为 `-`，表示大小不适用）。由于自动生成的 API 模型为 `size` 字段标记了 `omitempty`，逻辑零值在列表 JSON 中会被省略。而单选下载 thunk 直接将 `object.size` 原样传给下载辅助函数，导致运行时传入的 `fileSize` 为 `undefined`（或人工构造前缀记录中的 `0`）。这两者都不能作为除法运算的有效分母。

### 流式 ZIP 没有预先可知的网络传输长度 {#streamed-zip}

当服务端收到以 `/` 结尾的下载请求时，会递归列出该前缀下的所有对象，并将 `zip.Writer` 直接连接到 `io.Pipe`：一边读取源对象、一边执行 Deflate 压缩、一边将生成的字节直接刷入 HTTP 响应流。

这种边压缩边流式输出的设计十分合理：服务端无需在内存或临时磁盘中缓存完整 ZIP 归档即可立即发出首字节。但它的必然推论是：在发送 HTTP 响应头的那一刻，最终压缩后的归档总字节数尚不存在，因此响应只包含 `Content-Type: application/zip` 与文件名，不包含 `Content-Length`。源对象的未压缩大小之和也不能替代 `Content-Length`：源大小是未压缩的逻辑字节，而浏览器 `ProgressEvent.loaded` 统计的是经过 Deflate 压缩并附带 ZIP 帧头后的网络传输字节，两者的量纲完全不同。

### 进度事件缺乏有效分母时的算术异常 {#progress-event}

前端 XHR `progress` 监听器此前无条件执行以下计算：

```ts
Math.round((event.loaded / fileSize) * 100)
```

对于文件夹前缀或零字节对象，分母 `fileSize` 为 `undefined` 或 `0`，JavaScript 会计算出 `NaN`（`loaded / undefined` 或 `0 / 0`）或 `Infinity`（正数除以 `0`）：

```text
公共前缀：size = 0（或 undefined）
        |
        v
download(..., fileSize = 0)
        |
        v
流式 Deflate ZIP，无 Content-Length 响应头
        |
        v
event.loaded / 0 => NaN 或 Infinity
        |
        v
非法百分比写入 Redux；waitingForFile 被置为 false
        |
        v
确定模式的 ProgressBar 渲染出 "NaN%"
```

## 产品契约 {#contract}

进度展示需要严格遵守四条不变量：

```text
确定进度（determinate）  => 总量有限且 total > 0
确定进度（determinate）  => 百分比有限且 0 <= percentage <= 100
总量未知（unknown total）=> 保持不确定进度（indeterminate）
终态（terminal state）   => 退出不确定进度（not indeterminate）
```

以“分母是否合法有效”而非 `objectPath.endsWith("/")` 来定义契约，能够用同一套逻辑同时覆盖文件夹前缀、零字节对象、缺失大小元数据以及任何未来的分块流式响应，无需为特定对象类型编写脆弱的特判分支。

## 目标与非目标 {#scope}

### 目标 {#goals}

1. 文件夹下载在任何时刻都绝不显示 `NaN%`、`Infinity%` 或伪造的百分比。
2. 总量未知的传输任务复用现有的不确定进度（indeterminate）动画。
3. 已知大小的普通非空文件保持原有的确定百分比进度行为不变。
4. 完成、失败与取消三种终态均必须退出不确定进度动画。
5. 零字节文件下载过程中绝不产生非有限百分比，并在完成时正常到达 `100%`。
6. 严禁任何非有限数（`NaN`、`Infinity`）或越界百分比写入 Redux 状态树。

### 非目标 {#non-goals}

- 不为了凑出 `Content-Length` 而在服务端预先缓冲整个 ZIP 归档；
- 不把未压缩源对象大小之和当作压缩后网络传输进度的分母；
- 不在本次缺陷修复中重构整个 Object Manager 的 Redux 状态结构。

## 技术决策 {#decision}

最小生产修复由五个紧密配合的部分组成：

### D1. 仅在拥有合法总量时计算百分比 {#d1}

将进度算术抽离为独立于 DOM 与 Redux 副作用的纯函数（`downloadProgress.ts`）：

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

1. 若存在有限正数 `objectSize`，优先使用它以保持普通文件下载进度计算完全不变；
2. 若 `objectSize` 不可用（`0` 或 `undefined`），但浏览器声明响应长度可计算（`event.lengthComputable === true`）且提供了有限正数 `event.total`，则将其作为回退分母；
3. 其他情况下统一返回 `null`，表示当前不存在可诚实计算的百分比。

### D2. 总量未知时保持 Indeterminate 状态 {#d2}

修改 XHR `progress` 事件监听器，仅当 `calculateDownloadPercent` 返回非空数值时才派发 `progressCallback`：

```ts
req.addEventListener("progress", (event) => {
  const percent = calculateDownloadPercent(event, fileSize);

  if (percent !== null) {
    progressCallback(percent);
  }
});
```

由于下载条目初始化时默认 `waitingForFile = true`——且 `ObjectHandled` 组件已经将该状态渲染为 `<ProgressBar variant="indeterminate" />`——当 `percent === null` 时跳过派发即可让任务行自然保持在不确定进度模式，直到终态动作到达。

### D3. 确保取消操作正确进入终态 {#d3}

此前完成（complete）与失败（fail）reducer 都会清除 `waitingForFile`，唯独取消（`cancelObjectInList`）遗漏了这一转换。在 `cancelObjectInList` 中补齐 `item.waitingForFile = false`，可防止处于不确定进度模式的文件夹下载在用户点击取消后仍继续播放活动动画。

同时在 XHR 边界增加事件顺序保护：调用 `req.abort()` 时会先触发 `readystatechange (DONE, status = 0)`，随后才触发 `onabort` 事件。令通用 `DONE` 分支在 `status === 0` 时直接返回、交由专门的 `onabort` 或 `onerror` 处理器接管，可避免取消操作被抢先误标为下载失败。

### D4. 归一化被省略的零字节大小 {#d4}

在单选下载 thunk 中传入 `object.size || 0`，与多选下载入口对齐。这样可在完成回调检查 `Blob.size === fileSize` 之前恢复 API 模型因 `omitempty` 而省略的逻辑零值，确保零字节对象在收到 HTTP 200 空响应时顺利过渡到 `100%` 完成状态。

### D5. 保持服务端流式 ZIP 不变 {#d5}

Go 后端的文件夹下载处理器继续通过 `io.Pipe` 流式生成 Deflate 压缩 ZIP 并省略 `Content-Length`，无需改动任何服务端 API 或归档格式。

## 进度状态机 {#state-machine}

| 状态 | `waitingForFile` | `percentage` | 终态标志 | 界面渲染 |
| --- | ---: | ---: | --- | --- |
| 排队中 / 尚未收到有效进度 | `true` | `0` | 无 | 不确定进度条（indeterminate） |
| 总量未知的传输 | `true` | `0` | 无 | 不确定进度条（indeterminate） |
| 总量已知的传输 | `false` | `0..100` | 无 | 确定百分比进度条 |
| 已完成（Completed） | `false` | `100` | `done = true` | 成功（`100%`） |
| 已失败（Failed） | `false` | 上次有效值 | `failed = true, done = true` | 错误状态 |
| 已取消（Cancelled） | `false` | `0` | `cancelled = true, done = true` | 已取消状态 |

## 完备性证明 {#proof}

### 普通非空文件 {#case-file}

`objectSize > 0` 提供有限正数分母，辅助函数返回 `[0, 100]` 范围内的整数，`updateProgress` 将 `waitingForFile` 置为 `false` 进入确定百分比模式，下载完成时置为 `100%`。

### 流式文件夹 ZIP {#case-folder}

`objectSize` 归一化为 `0`，同时 `lengthComputable = false` 且 `event.total = 0`。辅助函数返回 `null`，不派发进度更新，任务行保持不确定动画；流式传输完成后置为 `waitingForFile = false`、`percentage = 100` 与 `done = true`。

### 未来带真实长度的响应 {#case-future}

若反向代理或未来的归档端点提供了可信的响应总长度（`lengthComputable = true` 且 `event.total > 0`），同一套代码会自动回退使用 `event.total` 显示真实百分比，无需再次修改前端。

### 零字节文件 {#case-zero}

被省略的列表大小归一化为 `0`；传输期间若触发进度事件则返回 `null`（绝不计算 `0 / 0`）；收到空响应后，零字节 `Blob.size` 与归一化后的期望大小相等，直接跃迁至 `100%` 完成状态。

### 失败与取消 {#case-terminal}

失败与取消均会将 `waitingForFile` 置为 `false` 并将 `done` 置为 `true`，确保没有任何已终止的任务行继续显示活动动画。

## 被拒绝的替代方案 {#alternatives}

### 在服务端缓冲完整 ZIP 以获取 Content-Length {#alt-buffer}

在服务端内存或临时磁盘中生成完整归档后再发送，虽然能提供精确的 `Content-Length`，但会显著推迟首字节时间（TTFB）、加剧内存与磁盘压力并恶化并发下载表现。绝不能为了一个前端进度展示缺陷而放弃流式传输。

### 将前缀下所有对象的未压缩大小相加 {#alt-sum}

源对象大小之和是未压缩的逻辑字节，而 `event.loaded` 是经过 Deflate 压缩后的网络字节加 ZIP 帧头。由于分子与分母单位不同，进度条会随压缩率剧烈波动，甚至停留在远低于 `100%` 的位置或提前达到 `100%`。

### 将非法进度强制转换为 `0%` {#alt-zero}

在长达数 GB 的文件夹下载过程中一直显示确定模式的 `0%`，会让用户误以为一个字节都没有传过来、连接已经卡死。“总量未知”必须诚实地表达为未知。

### 仅对 `/` 结尾的路径做特判 {#alt-folder-check}

只检查 `objectPath.endsWith("/")` 会遗漏真实的零字节对象、缺失元数据的响应以及其他不含 `Content-Length` 的分块传输响应。正确的判断边界是“分母是否可计算”，而非路径后缀。

### 将文件夹直接交给旧版 `BrowserDownload` {#alt-browser-download}

Console 2.2.0 时期的旧版 `BrowserDownload` 辅助函数会在点击隐藏 `<a>` 标签后立即触发完成回调，在首字节到达前就把任务标为 `100%` 完成，无法感知后续 HTTP 错误或支持取消。（真正的浏览器原生流式交接已在后续 [Console 2.4.1](#later-contract) 中独立设计与实现。）

### 仅在 `ProgressBar` 组件内部过滤 `NaN` {#alt-component}

仅在展示组件内屏蔽 `NaN` 会任由非法数值写入 Redux 状态树，且无法阻止 `waitingForFile` 被错误清零。主防线必须设在进度事件进入应用状态的入口处。

### 立即将 Redux 状态扩展为 `percentage: number | null` {#alt-null-state}

在保留 `waitingForFile`、`done`、`failed` 与 `cancelled` 四个布尔字段的同时再引入 `null`，只会制造更多自相矛盾的状态组合。既然现有 `waitingForFile = true` 已经准确建模并渲染了不确定进度状态，直接复用它的兼容性风险最小。

## 需求与验收条件 {#requirements}

### 功能需求 {#functional}

- **FR1–FR3：** `calculateDownloadPercent` 仅返回 `null` 或 `[0, 100]` 范围内的有限整数；总量未知的文件夹下载保持不确定模式（`waitingForFile = true`）；已知总量的普通对象下载保持确定百分比进度。
- **FR4–FR5：** 归一化被省略的零字节大小使空文件正常完成至 `100%`，并在完成、失败与取消时统一将 `waitingForFile` 置为 `false`。

### 非功能需求 {#non-functional}

- 保持服务端流式 ZIP（`io.Pipe` 无全量缓冲）、S3/Console API 路由以及 Redux 状态类型不变。

### 验收条件 {#acceptance}

- 在文件夹、普通文件、零字节文件与中途取消等全部下载场景中，下载面板均不出现 `NaN%` 或 `Infinity%`。

## 验证矩阵 {#tests}

### 纯函数计算矩阵 {#unit-tests}

| 场景 | `loaded` | `objectSize` | `lengthComputable` | `event.total` | 期望返回值 |
| --- | ---: | ---: | --- | ---: | --- |
| 普通文件下载过半 | `50` | `100` | `false` | `0` | `50` |
| 公共前缀（`folder/`） | `1024` | `0` | `false` | `0` | `null` |
| 初始 `0 / 0` | `0` | `0` | `false` | `0` | `null` |
| 响应总长度回退 | `50` | `0` | `true` | `200` | `25` |
| 响应总长度为零 | `0` | `0` | `true` | `0` | `null` |
| 已加载字节超过总量 | `150` | `100` | `true` | `100` | `100` |
| 非法对象大小 `NaN` | `10` | `NaN` | `false` | `0` | `null` |
| 省略的对象大小 `undefined` | `10` | `undefined` | `false` | `0` | `null` |
| 非有限响应总量 `Infinity` | `10` | `0` | `true` | `Infinity` | `null` |
| 负数 `loaded` | `-1` | `100` | `true` | `100` | `null` |

### 状态转换测试 {#state-tests}

单元测试直接验证：新下载任务以 `waitingForFile = true` 启动；无有效百分比派发时保持不确定模式；收到有效进度后更新有限百分比并将 `waitingForFile` 置为 `false`；完成、失败与取消均将 `waitingForFile` 置为 `false`。

### 真实浏览器端到端回归 {#e2e-tests}

Playwright 测试在真实 SILO + Console 实例上利用 Chromium CDP 网络限速保留传输观察窗口，验证文件夹下载期间进度抽屉显示不确定动画且不含 `NaN%` 或 `Infinity%`，验证中途取消能正确进入 **Cancelled** 终态，并验证不限速下载的 ZIP 归档完整性、普通非空文件进度以及零字节文件下载。

## 实现范围 {#implementation}

1. 新增 `downloadProgress.ts` 纯计算模块；
2. 修改 `Objects/utils.ts`：仅当计算结果非空时调用 `progressCallback`，并让 `status === 0` 的终止事件交由 `onabort` / `onerror` 处理；
3. 在单选下载 thunk 中将 `object.size || 0` 归一化；
4. 在 `cancelObjectInList` reducer 中将 `item.waitingForFile` 置为 `false`；
5. 在 `playwright.config.ts` 中配置纯单元测试与 Chromium 限速端到端回归测试。

## 交付与回滚 {#delivery}

该修复已随 [Console v2.2.0](/zh/blog/release/console-2.2.0/)（[silo-console#29](https://github.com/pgsty/silo-console/pull/29)）发布，并内嵌于 [SILO Server 20260903](/zh/blog/release/silo-20260903/)，关闭 [pgsty/silo#62](https://github.com/pgsty/silo/issues/62)。不涉及任何数据或 API 迁移。

### 完成定义 {#done}

- [x] `calculateDownloadPercent` 仅返回 `null` 或 `[0, 100]` 范围内的有限整数；
- [x] 总量未知的文件夹下载展示不确定进度，普通文件与零字节文件正常展示确定进度；
- [x] 完成、失败与取消均退出不确定进度模式（`waitingForFile = false`）；
- [x] 随 Console `2.2.0` 与 Server `20260903` 正式发布。

### 后续演进任务 {#follow-ups}

评审期间识别出的五项演进方向——消除前端整包 `Blob` 内存缓冲并直接流式交接给浏览器、进度终态可辨识联合类型、服务端流式 ZIP 错误中断传播、共享进度条组件的非有限值兜底守卫，以及 `Blob` JSON 错误响应解码——已分别在后续 Console 版本中推进落地。

## 后续演进：Console 2.4.1 的浏览器原生流式交接 {#later-contract}

在合入上述进度修复的同时，[Console 2.2.0](/zh/blog/release/console-2.2.0/) 还将对象列表中的 `size` 改为始终输出的 JSON 字段，并加固了服务端 ZIP 错误传播：不可读条目不再被静默跳过，响应头发出前的错误返回 HTTP 500，响应开始后的错误则通过中断流暴露给客户端。

随后发布的 [Console 2.4.1](/zh/blog/release/console-2.4.1/#browser) 进一步消除了整包 XHR `Blob` 内存缓冲：单文件夹与单对象下载直接交接给浏览器原生下载管理器，多选打包下载则通过文件系统流式写入器（FileSystemWritableFileStream）或原生流交接落盘。在这一新架构下，Console 下载面板中的完成状态代表“已成功交接给浏览器下载管理器”，后续字节传输进度与取消操作均由浏览器原生下载管理器接管。

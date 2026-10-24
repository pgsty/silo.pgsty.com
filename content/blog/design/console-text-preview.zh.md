---
title: "只预览文本，绝不执行：SILO Console 文本预览设计"
linkTitle: "安全文本预览"
date: 2026-08-23
lastmod: 2026-09-16
author: "冯若航"
summary: >
  SILO Console 安全文本预览设计：以严格 UTF-8 解码与 1 MiB 硬上限预览小型日志、纯文本、JSON 和 XML，绝不将对象内容作为同源可执行文档加载。
tags: [设计, Console, 预览, 安全]
weight: 10
draft: false
url: "/zh/blog/design/console-text-preview/"
---

SILO Console 支持预览图片、PDF、音频和视频，但在 v2.1.1 中却无法直接查看日常运维最常检查的小型日志、纯文本、JSON 与 XML 对象。即使对象保存了准确的 `Content-Type`，前端也会在选择预览渲染器之前将其判定为不支持。

恢复旧版浏览器原生 `<iframe>` 预览虽然简单，却是错误的修法。存储桶中的对象内容完全由上传者控制；一旦将其作为同源 HTML 或 XML 文档加载，一个便利的预览功能就会退化为同源脚本执行边界。

随 [Console 2.2.0](/zh/blog/release/console-2.2.0/) 交付的设计（跟踪议题 [#17](https://github.com/pgsty/silo/issues/17)）确立了一条严格的安全不变量：

> SILO Console 仅将符合条件的对象作为有界 UTF-8 纯文本预览，绝不让浏览器将其中的标记、MIME 类型或文件内容解析为可执行文档。

## 核心决策 {#decision}

Console 新增独立的 `text` 预览类型与 `PreviewText` 组件，并遵循十项契约规则：

1. 完整保留现有的 `image`、`pdf`、`audio` 与 `video` 媒体分类逻辑。
2. 仅当既有媒体分类器返回 `none` 时，才进入文本回退（fallback）判定。
3. 允许四种目标扩展名（`.log`、`.txt`、`.json`、`.xml`）或四种精确被动文本 MIME 类型（`text/plain`、`application/json`、`application/xml`、`text/xml`）。
4. 通过常规鉴权下载路径读取对象字节，不传递 `preview=true`。
5. 在应用层强制执行 1 MiB（`1,048,576` 字节）读取硬上限。
6. 仅执行严格 UTF-8 解码（`fatal: true`），并拒绝包含 NUL 字节的内容。
7. 在可滚动的 `<pre>` 容器中仅渲染单一 React 文本节点。
8. 绝不使用 `<iframe>`、HTML 解析器、XML 解析器或任何 HTML 注入 API。
9. 要么展示完整对象，要么完全不展示；绝不渲染被截断的 JSON 或 XML 半截片段。
10. 当文件超出大小上限、编码非法或无法加载时，始终保留 **Download**（下载）出口。

本设计不新增 S3 操作或后端预览路由，也不扩大后端的 `inline` MIME 白名单。交付过程中同步收敛了 Console 下载端点的字节范围语义：零字节对象的 `Range` 请求返回空 `200 OK`，不可满足的范围请求返回 `416 Range Not Satisfiable` 及 `Content-Range: bytes */N`，且对象 JSON 元数据始终输出 `size` 字段（详见 [Console 2.2.0](/zh/blog/release/console-2.2.0/#byte-ranges)）。

## Console 2.1.1 的原有行为 {#current-behavior}

在 SILO Console v2.1.1 中，前端预览联合类型仅包含：

```text
image | pdf | audio | video | none
```

其扩展名映射表只包含多媒体格式，未收录 `.log`、`.txt`、`.json` 或 `.xml`；MIME 分类器同样忽略 `text/plain`、`application/json`、`application/xml` 与 `text/xml`。运行时验证显示前端分类与后端响应头之间存在如下分裂：

| 对象 | 前端分类结果 | Console 下载响应头 |
| --- | --- | --- |
| `.log` / `text/plain` | `none` | `inline`，`X-Frame-Options: SAMEORIGIN` |
| `.txt` / `text/plain` | `none` | `inline`，`X-Frame-Options: SAMEORIGIN` |
| `.json` / `application/json` | “Preview unavailable” | `inline`，`X-Frame-Options: SAMEORIGIN` |
| `.xml` / `application/xml` | `none` | `attachment`，`X-Frame-Options: DENY` |

此外，对象详情抽屉在判断 **Preview** 按钮是否禁用时使用了错误的布尔逻辑连接词：有读取权限的用户可以对不支持预览的对象点击 **Preview** 并看到不可用提示，而在另一些权限组合下界面会放行实际上会被服务端拒绝的操作。

更关键的是，预览容器组件末尾仍残留着一条通用的同源 `<iframe>` 回退分支。由于封闭的五元联合类型无法落入该分支，v2.1.1 并未构成可利用的文本预览 XSS；但如果简单地把 `text` 加入联合类型并任其落入旧的 `<iframe>` 分支，就会直接激活同源文档执行风险。

## 根因分析 {#root-cause}

该缺陷源于三个独立演进层之间的契约漂移：

### 分类契约漂移 {#classification-drift}

浏览器前端依据文件名与对象的 `Content-Type` 元数据判断预览资格，但封闭的联合类型中根本没有 `text` 分支。再准确的元数据也无法选中一个不存在的渲染器。

### 响应策略漂移 {#response-drift}

Console 后端独立判断下载响应是否允许 `inline`：后端仍将纯文本与 JSON 视为安全的被动内联类型，同时将 XML 与 HTML 强制设为 `attachment`。这一服务端策略并未反映在前端分类器中。

### 渲染器漂移 {#renderer-drift}

在可达预览类型收缩为纯媒体类型后，旧版通用 `<iframe>` 回退分支仍残留在组件树中。修复方案必须引入专用的惰性文本渲染器并彻底删除不可达的 `<iframe>` 分支，而不能把 MIME 元数据当作安全边界。

## 为什么拒绝同源 Iframe 预览 {#iframe-risk}

`X-Frame-Options: SAMEORIGIN` 不是沙箱。它只限制哪些父级源可以嵌入该响应，并不限制同源 frame 内部的代码能执行什么操作。

一旦上传者可控的 HTML、XHTML、SVG 或活动 XML 被作为内联同源文档加载进 `<iframe>`，其中的脚本就会直接在 Console 的源（Origin）下运行。即便 `HttpOnly` 会话 Cookie 能阻止脚本直接读取 `document.cookie`，同源脚本仍然可以携带当前会话凭据向 Console 后端发起任意状态修改请求。

`X-Content-Type-Options: nosniff`、内容安全策略（CSP）与 `Content-Disposition` 都是有价值的纵深防御，但核心安全不变量必须建立在数据流本身之上：

```text
不受信任的对象字节
        |
        v
严格 UTF-8 TextDecoder
        |
        v
React <pre>{textContent}</pre>

绝不经过：
iframe / innerHTML / DOMParser / XML parser / 可执行文档
```

## 产品契约 {#product-contract}

本功能是一个只读源码文本查看器，既不是网页文档渲染器，也不是在线代码编辑器。

用户可以：

- 从存储桶对象列表或对象详情抽屉打开符合条件的小型文本对象；
- 在现有预览弹窗中查看保留空白与缩进的原始文本；
- 使用浏览器原生选择与复制功能；
- 清晰区分预览受阻是因为文件过大、非 UTF-8/二进制编码、权限不足、对象已被替换还是网络错误；
- 随时点击下载获取原始字节。

系统绝不会通过静默转换误导用户：

- 绝不对 JSON 执行解析重排（否则会篡改超出双精度范围的大整数、折叠重复键或改变空白格式）；
- 绝不将超限的 XML 或 JSON 静默截断为结构残缺的前缀片段；
- 绝不用 `U+FFFD` 替换字符掩盖非法的 UTF-8 字节序列。

## 目标与非目标 {#scope}

### 目标 {#goals}

1. 无需下载到本地即可直接预览小型 `.log`、`.txt`、`.json` 与 `.xml` 对象。
2. 无论扩展名、`Content-Type` 或载荷内容如何，始终保持对象内容完全惰性（inert）。
3. 将保留的响应字节与渲染文本严格限制在 1 MiB（`1,048,576` 字节）以内。
4. 原样保留存储的 UTF-8 文本，不做静默重排。
5. 统一对象列表与详情抽屉的预览资格及权限判断逻辑。
6. 同时支持当前对象版本与显式选中的历史 `versionId`。
7. 保持匿名访问（`X-Anonymous: 1`）与子路径托管（subpath hosting）行为不变。

### 非目标 {#non-goals}

- HTML、XHTML 或 Markdown 渲染；
- XML 解析、XSLT 转换、外部实体解析或 Schema 校验；
- JSON 自动美化缩进（`JSON.parse` / `JSON.stringify`）；
- 在线编辑、语法高亮、行号栏、代码折叠或 ANSI 转义序列渲染；
- 针对超过 1 MiB 大文件的首尾截取或截断预览；
- 针对 GBK、UTF-16、Latin-1 等非 UTF-8 编码的有损解码或自动编码探测。

当 `notes.md` 等文件的精确 MIME 类型为 `text/plain` 时，它可以作为原始 UTF-8 纯文本预览，但不会触发 Markdown 渲染。

## 准入资格契约 {#eligibility}

准入资格采用两阶段判定，以确保既有媒体预览行为零回归。

### 第一阶段：保留既有媒体判定 {#legacy-media}

首先原样运行现有的 `image`、`pdf`、`audio` 与 `video` 分类器。只要返回值不是 `none`，即直接采用该媒体类型。

### 第二阶段：应用文本回退判定 {#text-fallback}

仅当第一阶段返回 `none` 时：

1. 显式拒绝最终扩展名为 `.html`、`.htm` 与 `.xhtml` 的对象。
2. 将最终扩展名（忽略大小写）与 `.log`、`.txt`、`.json`、`.xml` 进行匹配。
3. 规范化 `Content-Type`：剥离参数（如 `; charset=...`）、去除首尾空白并转为小写。
4. 将规范化后的 MIME 类型与 `text/plain`、`application/json`、`application/xml`、`text/xml` 进行精确匹配。

只要命中允许的扩展名（且未被规则 1 排除）或命中允许的精确 MIME 类型，即判定为 `text`：

| 文件名与 MIME | 判定结果 | 原因 |
| --- | --- | --- |
| `report.txt` + `image/png` | `image` | 既有媒体分类优先 |
| `report.json` + `application/pdf` | `pdf` | 既有媒体分类优先 |
| `server.LOG` + `application/octet-stream` | `text` | 命中允许的扩展名（大小写不敏感） |
| 无扩展名 + `application/json; charset=utf-8` | `text` | 命中规范化后的精确 MIME |
| `page.html` + `text/plain` | `none` | 活动文档扩展名被显式排除 |
| `page.txt` + `text/html` | `text` | 扩展名准入；HTML 源码仅作为惰性纯文本展示 |
| `notes.md` + `text/plain` | `text` | 精确 MIME 准入原始纯文本 |
| `image.svg` + `image/svg+xml` | `image` | 走既有图片预览路径 |

## 资源上限契约 {#resource-contract}

二进制读取硬上限定义为：

```text
MAX_TEXT_PREVIEW_BYTES = 1,048,576
```

恰好 `1,048,576` 字节（1 MiB）的对象允许预览；`1,048,577` 字节则作为超限拒绝。

### 已知对象大小 {#known-size}

- 若选中版本的已知大小超过 `1,048,576` 字节，打开弹窗时直接进入 **Too Large**（文件过大）状态，不发起正文下载请求。点击 **Retry**（重试）会使用有界 `Range` 请求重新探测，以应对列表元数据过期的情况。
- 已知大小为 `0` 字节的对象仍会发起有界请求以验证权限与对象存在性，收到空 `200 OK` 后展示明确的 **File is empty**（文件为空）状态。
- 缺失大小元数据（`undefined`）必须保留为未知状态，不能通过布尔回退强制转换为 `0`，并进入有界流式读取路径。

### 有界请求与哨兵字节 {#bounded-request}

对于已知不超过 1 MiB 或大小未知的对象，客户端发送：

```http
Range: bytes=0-1048576
```

请求 `1,048,576 + 1` 字节是为了把第 `1,048,577` 个字节作为超限哨兵（sentinel byte）。客户端执行以下流程：

1. 响应到达后立即检查 `Content-Range` 与 `Content-Length` 响应头。
2. 通过 `ReadableStream` 流式读取正文，绝不直接调用 `response.text()` 或构造无界 `Blob`。
3. 内存中最多保留 `1,048,577` 字节。
4. 一旦读到第 `1,048,577` 个哨兵字节（包括反向代理忽略 `Range` 并返回完整 `200 OK` 的情况），立即中止流读取。
5. 仅当流正常结束且证明完整对象不超过 `1,048,576` 字节时，才执行解码与渲染。

## 请求标识与取消生命周期 {#request-lifecycle}

每个预览请求由 `bucket + object name + versionId` 唯一标识，并保留同源凭据、Console 子路径前缀、`version_id` 查询参数以及匿名模式下的 `X-Anonymous: 1` 请求头。关闭弹窗、切换对象或版本、切换存储桶或组件卸载时，会同时触发 `AbortController` 中止信号与代次令牌（generation token）失效检查，防止已读完但较晚完成解码的旧响应覆盖新对象的预览。主动中止的请求静默清理，不弹出错误提示。

## 编码与保真契约 {#encoding}

文本解码仅支持严格模式的 UTF-8：

```ts
new TextDecoder("utf-8", { fatal: true })
```

- 自动剥离前导 UTF-8 BOM（`EF BB BF`），不在界面上渲染零宽字符；
- 原样保留多字节 Unicode 字符、emoji、制表符、`LF` 与 `CRLF` 换行；
- 遇到非法 UTF-8 字节序列时直接抛出解码错误并进入 **Invalid UTF-8 / Binary** 状态，绝不插入 `U+FFFD` 替换字符；
- 解码结果中一旦包含 `NUL`（`\0`）字符，立即作为二进制内容拒绝。

## 安全渲染器与界面状态 {#safe-renderer}

成功状态仅在 `<pre>{content}</pre>` 中渲染单一 React 文本节点，使用等宽字体、保留空白字符、默认禁用自动换行（`white-space: pre`，以保持对齐日志的可读性，并避免超长单行 JSON 引发昂贵的浏览器排版计算）、双向滚动条以及原生键盘焦点支持。预览路由中残留的通用 `<iframe>` 回退分支被彻底移除。

### 界面状态与权限控制 {#ux}

在对象列表与对象详情抽屉中，当且仅当同时满足以下条件时才启用 **Preview** 按钮：

```text
符合预览类型准入条件
AND 具备 s3:GetObject（或 s3:GetObjectVersion）权限
AND 不是删除标记（Delete Marker）
AND 不是目录前缀
```

预览弹窗明确区分 **Loading**（加载中）、**Success**（成功展示源码与下载按钮）、**Empty**（`0` 字节空文件提示）、**Too Large**（超过 1 MiB，展示对象大小、上限说明、**Download** 与有界 **Retry**）、**Invalid UTF-8 / Binary**（编码非法或二进制说明与 **Download**）、**Forbidden（`403`）**、**Not Found（`404`）** 以及 **Network / Server Error**。任何 HTTP 错误响应体都绝不会被解码展示为预览内容。

## 功能与安全需求 {#requirements}

### 功能需求 {#functional-requirements}

- **FR1–FR3：** 保留现有媒体与 PDF 分类优先级，按两阶段扩展名/MIME 矩阵判定文本预览资格，并将不超过 1 MiB 的完整对象渲染为严格 UTF-8 源码。
- **FR4–FR6：** 超限对象不渲染半截内容，空文件展示独立状态，且元数据、大小与正文请求严格绑定同一 `versionId`。
- **FR7–FR9：** 保持匿名访问、Console 子路径、列表与详情页一致的按钮准入判定，以及既有下载/分享行为不变。

### 安全需求 {#security-requirements}

- **SR1–SR4：** 对象字节仅通过 `<pre>` 文本节点进入 DOM（不含任何 HTML/XML/SVG/Markdown 解析器），最多保留 `1,048,577` 字节，并在关闭弹窗或切换对象时使旧请求失效。
- **SR5–SR8：** 拒绝非法 UTF-8 与 `NUL` 字节，不在 Redux、本地存储、日志或错误体中留存预览文本，依赖服务端 S3 鉴权，且不放宽 CSP 或后端 `safeMimeTypes`。

## 实现范围 {#implementation}

1. 重构预览分类器，保留既有媒体判定并将 `text` 作为显式回退分支。
2. 新增 `PreviewText` 组件，内置流式字节上限、严格 UTF-8 解码、`AbortController` 取消与显式状态机。
3. 移除不可达的通用 `<iframe>` 回退分支，统一对象列表与详情抽屉的 **Preview** 启用条件，并保留 `undefined` 未知大小状态。

## 被拒绝的替代方案 {#alternatives}

### 继续禁用文本预览 {#alternative-disabled}

被拒原因：查看小型日志、状态文件与 JSON/XML 配置是高频日常运维操作，每次检查都强制下载到本地会造成不必要的操作摩擦。

### 复用旧版同源 Iframe {#alternative-iframe}

被拒原因：在同源 `<iframe>` 中加载上传者可控的内容会把可变的 MIME 元数据变成脚本执行边界，且无法限制浏览器内存占用。

### 新增专用后端预览 API {#alternative-backend}

被拒原因：现有鉴权下载端点已经完整执行了 `GetObject` / `GetObjectVersion` 权限检查并支持 HTTP `Range` 请求（`bytes=0-1048576`）。另起炉灶只会复制权限与版本逻辑，而不会建立新的数据访问边界。

### 截断展示大文件的前 1 MiB {#alternative-truncation}

被拒原因：展示 50 MiB JSON 或 XML 文件的前 1 MiB 会呈现结构残缺的半截文档，且需要额外处理多字节 UTF-8 截断边界。“要么完整展示、要么不展示”使预览语义保持严密。

### 使用替换字符有损解码非法 UTF-8 {#alternative-lossy}

被拒原因：静默插入 `U+FFFD` 会污染运维人员从预览框中复制出的文本内容。传统单字节编码或 UTF-16 文件应通过 **Download** 下载后使用专用工具查看。

### 自动解析并格式化 JSON {#alternative-json-format}

被拒原因：`JSON.parse` 再 `JSON.stringify` 会静默篡改超出 `Number.MAX_SAFE_INTEGER` 的 64 位整数、折叠重复键并改变原始空白格式。

### 引入 Monaco 等重型代码编辑器 {#alternative-editor}

被拒原因：对于有界 1 MiB 的只读预览而言，Web Worker、语法分析器与体积开销得不偿失；原生 `<pre>` 单文本节点更加轻量且易于安全审计。

## 验收矩阵与测试计划 {#acceptance}

### 分类矩阵测试 {#classification-tests}

锁定两阶段扩展名与 MIME 判定矩阵的每一行、大小写不敏感、参数剥离、`.html`/`.htm`/`.xhtml` 排除以及媒体类型优先规则。

### 资源边界测试 {#resource-tests}

覆盖 `0` 字节、`1` 字节、`1,048,576` 字节、`1,048,577` 字节、已知超限跳过首次请求、有界 **Retry**、`206 Partial Content`、服务端忽略 `Range` 返回 `200 OK` 以及关闭弹窗时的流取消。

### 编码与保真测试 {#encoding-tests}

覆盖 UTF-8 中文与 emoji、BOM 剥离、非法 UTF-8 序列、内嵌 `NUL` 字节、JSON 不安全大整数、重复键、原始空白以及 XML `DOCTYPE`/`CDATA`/stylesheet 指令。

### 安全载荷测试 {#security-tests}

验证包含 `<script>`、内联事件属性、`<iframe>`、SVG 事件处理器、XML 外部实体（XXE）与 XSLT 的载荷逐字出现在 `<pre>.textContent` 中，不创建任何子 DOM 节点，不触发任何脚本或外部网络请求。

### 权限与版本竞态测试 {#permission-tests}

确认 `401`/`403`/`404`/`416`/`5xx` 响应体绝不进入预览面板，且旧请求的迟到响应无法覆盖新选中的对象或 `versionId`。

### 真实浏览器回归 {#browser-tests}

在真实 SILO + Console 实例上通过 Playwright 验证中英文路由、亮色与暗色主题、桌面与窄屏视口，以及媒体、PDF、下载、分享与多版本工作流。

## 交付与完成门禁 {#delivery}

该特性已在 [`pgsty/silo-console` v2.2.0](/zh/blog/release/console-2.2.0/)（[PR #30](https://github.com/pgsty/silo-console/pull/30)）中发布，并随 [SILO Server 20260903](/zh/blog/release/silo-20260903/) 内嵌交付，关闭 [pgsty/silo#17](https://github.com/pgsty/silo/issues/17)。

## 利弊权衡 {#trade-offs}

本设计选择明确的准入范围而非通用浏览器查看器、选择完整小文件而非截断片段、选择原文保真而非自动格式化、选择严格 UTF-8 而非静默有损解码、选择单一惰性文本节点而非重型代码编辑器。超过 1 MiB 的大型日志与非 UTF-8 编码文件仍需点击 **Download** 下载查看——这一刻意的边界取舍，使得 Console 文本预览足够精简以便安全审计，也足够坚固以供生产环境信赖。

### 设计评审记录 {#review-record}

本方案在合入 [silo-console#30](https://github.com/pgsty/silo-console/pull/30) 前完成了产品范围、前端安全与 CSP 隔离以及 S3 `Range`/多版本语义三轮评审。

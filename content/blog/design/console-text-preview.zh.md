---
title: "只预览文本，绝不执行：SILO Console 文本预览 PRD"
linkTitle: "安全文本预览"
date: 2026-08-23
lastmod: 2026-09-02
author: "冯若航"
summary: >
  SILO Console 安全文本预览的最终 PRD：用严格 UTF-8 与 1 MiB 硬上限查看日志、纯文本、JSON 和 XML；任何对象内容都不得成为同源可执行文档。
tags: [设计, console, 预览, 安全]
weight: 10
draft: false
url: "/zh/blog/design/console-text-preview/"
---

> **状态：** 已随 SILO Console 2.2.0 发布 · **归属：** [pgsty/silo-console](https://github.com/pgsty/silo-console) · **跟踪：** [pgsty/silo#17](https://github.com/pgsty/silo/issues/17) · **审阅：** 产品、安全与前端架构三方共识

SILO Console 可以预览图片、PDF、音频和视频，却不能直接查看运维中最常见的小型日志、纯文本、JSON 与 XML。即使对象保存了完全正确的 <code>Content-Type</code>，前端也会在选择渲染器之前把它判为不支持。

恢复旧版浏览器原生预览很容易，却不是正确修复。对象内容由上传者控制；如果把它作为同源 HTML/XML 文档加载，一个便利功能就会变成代码执行边界。

因此最终设计给出一个更强的承诺：

> SILO 只把符合条件的对象作为有界 UTF-8 文本预览，绝不让浏览器把其中的标记、MIME 或内容解释成文档。

本文固定产品边界、资源上限、安全不变量、实现形态，以及功能进入发布版本前必须取得的证据。

## 最终决策 {#decision}

第一版增加独立的 <code>text</code> 预览类型和 <code>PreviewText</code> 组件。

契约如下：

1. 完整保留现有 image、PDF、audio、video 判定。
2. 只有旧分类器返回 <code>none</code> 时，才考虑文本 fallback。
3. 由四种目标扩展名或四种精确被动文本 MIME 触发。
4. 通过普通鉴权下载路径获取字节，不传 <code>preview=true</code>。
5. 在应用层强制执行 1 MiB 读取硬上限。
6. 只做严格 UTF-8 解码，并拒绝疑似二进制内容。
7. 在可滚动 <code>&lt;pre&gt;</code> 中只渲染一个 React 文本节点。
8. 永不使用 iframe、HTML/XML 解析器或 HTML 注入接口。
9. 要么显示完整对象，要么完全不显示；不展示截断 JSON/XML。
10. 文件超限、编码非法或加载失败时，始终保留 Download。

不新增 Console API 或 S3 API，也不扩大后端 inline MIME 白名单。

## 当前状况 {#current-behavior}

撰写本文时，SILO 当前锁定的 SILO Console v2.1.1 仍存在这个问题。

前端预览联合类型只有：

~~~text
image | pdf | audio | video | none
~~~

扩展名表包含媒体格式，却没有 <code>.log</code>、<code>.txt</code>、<code>.json</code>、<code>.xml</code>；MIME 分类器也不识别 <code>text/plain</code>、<code>application/json</code>、<code>application/xml</code>、<code>text/xml</code>。

运行时验证得到的分裂状态如下：

| 对象 | 前端结果 | Console 下载响应 |
| --- | --- | --- |
| <code>.log</code> / <code>text/plain</code> | <code>none</code> | inline，<code>SAMEORIGIN</code> |
| <code>.txt</code> / <code>text/plain</code> | <code>none</code> | inline，<code>SAMEORIGIN</code> |
| <code>.json</code> / <code>application/json</code> | “Preview unavailable” | inline，<code>SAMEORIGIN</code> |
| <code>.xml</code> / <code>application/xml</code> | <code>none</code> | attachment，<code>DENY</code> |

对象详情页判断 Preview 是否禁用时还使用了错误的与条件：有权限用户可以点开一个不支持对象，最后只看到 unavailable；另一些组合则会先提供按钮，再由服务端拒绝。

预览组件中仍残留一个通用同源 iframe fallback。按当前类型联合，这条分支实际上不可达，所以当前缺陷本身不是可利用的文本预览 XSS。但它很危险：如果只把 <code>text</code> 加入联合类型并让它落入旧 fallback，就会重新激活本文明确否决的同源文档加载。

## 根因 {#root-cause}

这是三个独立演进层之间的契约漂移。

### 分类契约漂移 {#classification-drift}

浏览器端根据文件名和对象元数据决定资格，但封闭类型联合中根本没有文本。再正确的元数据也无法选择一个不存在的渲染器。

### 响应策略漂移 {#response-drift}

Console 服务端又独立判断响应能否 inline：它仍把纯文本与 JSON 视为被动安全 MIME，而 XML/HTML 保持 attachment。这个服务端决定没有映射到前端分类。

### 渲染器漂移 {#renderer-drift}

当可达预览类型已经只剩媒体时，旧通用 iframe 仍留在组件里。代码看起来保留了一项能力，类型系统却不可能再调用它。

修复必须重新对齐三层契约，同时绝不能把 MIME 元数据提升成安全边界。

## 为什么拒绝同源 iframe {#iframe-risk}

<code>X-Frame-Options: SAMEORIGIN</code> 不是 sandbox。它只控制谁能嵌入响应，不限制同源 frame 中的代码能做什么。

一旦上传者控制的 HTML、XHTML、SVG 或主动 XML 被作为同源 inline 文档加载，它就可能获得 Console origin。HttpOnly Cookie 可以阻止脚本直接读取 Cookie，却不能阻止浏览器携带 Cookie 发出鉴权同源请求。只要 MIME 规则被错误放宽，存储对象就可能变成存储型应用代码。

<code>nosniff</code>、CSP 与 <code>Content-Disposition</code> 仍然是有价值的纵深防御，但都不能替代核心不变量：

~~~text
不可信对象字节
      |
      v
严格文本解码器
      |
      v
React textContent

永远不进入：
iframe / innerHTML / DOMParser / XML parser / 可执行文档
~~~

## 产品契约 {#product-contract}

这是一个只读文本查看器，不是网页预览器，也不是在线编辑器。

用户应该能够：

- 从列表或对象详情打开小型、符合条件的对象；
- 在现有预览弹窗里阅读保留空白的源码文本；
- 使用浏览器原生选择和复制；
- 分清失败来自大小、编码、权限、对象被替换还是网络错误；
- 随时下载原始字节。

系统绝不能让用户误以为：

- 格式化后的 JSON 就是存储原文；
- 截断 XML 是完整文档；
- 替换字符本来就存在于对象；
- 不支持的编码已经被忠实解码；
- 主动 HTML/XML 经“消毒”后可以安全执行。

## 目标与非目标 {#scope}

### 目标 {#goals}

1. 无需本地下载即可查看小型日志、纯文本、JSON 与 XML。
2. 无论扩展名、MIME 与载荷如何，对象内容始终保持惰性。
3. 把保留的响应字节与渲染文本限制在 1 MiB。
4. 忠实显示存储文本，不做静默格式化。
5. 列表与详情页按照相同权限和类型契约提供 Preview。
6. 支持当前对象版本和显式选择的历史版本。
7. 保持匿名访问和子路径部署行为。
8. 先独立发布 Console，再由 SILO 精确消费该 Console 修订。

### 非目标 {#non-goals}

- HTML/XHTML 渲染。
- XML 解析、XSLT、外部实体与 Schema 校验。
- Markdown 渲染。
- JSON 自动格式化。
- YAML/CSV 专用行为。
- 编辑与保存。
- 语法高亮、行号、搜索、折叠、ANSI 渲染与自动链接。
- 大对象 head、tail 或截断预览。
- 有损解码，以及 GBK、UTF-16、Latin-1 等编码自动探测。
- 新增后端文本预览接口。
- 修改现有 SVG、媒体、PDF、下载、分享或存储契约。

类似 <code>notes.md</code> 的对象如果精确 MIME 为 <code>text/plain</code>，仍可能作为原始文本显示，但不会获得 Markdown 语义。

## 资格判定契约 {#eligibility}

资格判定刻意分为两阶段。

### 第一阶段：保留旧媒体结论 {#legacy-media}

完全不变地运行当前 image、PDF、audio、video 分类器。只要结果不是 <code>none</code>，直接返回。

这样可以保留文件名与 MIME 冲突时的历史行为。

### 第二阶段：文本 fallback {#text-fallback}

只有旧结果为 <code>none</code> 时：

1. 最终扩展名为 <code>.html</code>、<code>.htm</code>、<code>.xhtml</code> 时明确拒绝；
2. 按大小写不敏感方式匹配最终扩展名：

   - <code>.log</code>
   - <code>.txt</code>
   - <code>.json</code>
   - <code>.xml</code>

3. 去掉参数、裁剪空白并转成小写，规范化 Content-Type；
4. 精确匹配：

   - <code>text/plain</code>
   - <code>application/json</code>
   - <code>application/xml</code>
   - <code>text/xml</code>

允许扩展名或精确 MIME 任意一项命中。本版禁止 <code>text/*</code>、子串匹配与 <code>application/*+json</code> 等宽泛规则。

以下矩阵是强制契约：

| 文件名与 MIME | 结果 | 原因 |
| --- | --- | --- |
| <code>report.txt</code> + <code>image/png</code> | image | 现有媒体结论优先。 |
| <code>report.json</code> + <code>application/pdf</code> | PDF | 现有媒体结论优先。 |
| <code>server.LOG</code> + <code>application/octet-stream</code> | text | 允许的扩展名，忽略大小写。 |
| 无扩展名 + <code>application/json; charset=utf-8</code> | text | 规范化后精确 MIME 命中。 |
| <code>page.html</code> + <code>text/plain</code> | none | 主动扩展名显式排除。 |
| <code>page.txt</code> + <code>text/html</code> | text | 扩展名命中，但 HTML 源码保持惰性文本。 |
| <code>notes.md</code> + <code>text/plain</code> | text | MIME 命中原始文本，不渲染 Markdown。 |
| <code>image.svg</code> + <code>image/svg+xml</code> | 现有 image 路径 | 不进入新 text/iframe 路径。 |

文件名和 MIME 只影响产品资格，永远不能选择可执行渲染模式。

## 资源契约 {#resource-contract}

二进制上限定义为：

~~~text
MAX_TEXT_PREVIEW_BYTES = 1,048,576
~~~

正好 1 MiB 可以预览，多一个字节就不可以。

### 已知大小 {#known-size}

- 选中版本的已知大小超过上限时，不请求正文；
- 已知大小为零时，显示空文件状态；
- 已知大小不超过上限时，开始有界请求；
- 缺失大小不等于零，必须进入有界未知大小路径。

因此当前从列表向弹窗传值时，不能再用 truthy fallback 把 <code>undefined</code> 强制变成零。

### 有界请求 {#bounded-request}

对于小型或未知大小对象，请求：

~~~http
Range: bytes=0-1048576
~~~

额外一字节用于探测超限。

客户端必须：

1. 在存在时检查 <code>Content-Range</code> 与 <code>Content-Length</code>；
2. 以 stream 读取响应，禁止调用 <code>response.text()</code> 或先构造完整 Blob；
3. 最多保留上限加一字节；
4. 观察到探测字节后立即取消；
5. 服务端忽略 Range、返回 200 时仍执行同一限制；
6. 只有 EOF 证明完整对象未超限后才开始渲染。

超限对象进入说明状态：显示已知大小、1 MiB 策略和 Download，不展示任何前缀片段。

## 请求身份与取消 {#request-lifecycle}

预览请求身份是：

~~~text
bucket + object name + version ID
~~~

请求必须复用现有生成 API 客户端或等价的 base-path-safe helper，从而保持：

- same-origin credentials；
- 当前 Console 子路径；
- <code>version_id</code>；
- 匿名模式 <code>X-Anonymous: 1</code>；
- 当前错误处理和权限边界。

关闭、对象变化、版本变化、bucket 变化和组件卸载都必须中止活动请求并清空旧内容。

仅依靠 abort 不够。还要使用 generation token 或失效标记，防止已经读完或解码完成的旧响应更新新的预览。

被取消的请求不是错误，不应产生错误 Toast。

## 编码与内容保真 {#encoding}

第一版只支持严格 UTF-8：

~~~ts
new TextDecoder("utf-8", { fatal: true })
~~~

要求：

- 正确处理 UTF-8 BOM，不显示 BOM；
- 保留 Unicode、emoji、TAB、LF、CRLF；
- 非法 UTF-8 直接拒绝，不插入替换字符；
- 解码后存在 NUL 时，按二进制或不支持内容拒绝；
- 不猜测其他编码；
- 不把对象正文写入日志或持久化；
- 永远保留下载原始字节的出口。

不支持编码状态应解释：

> 该对象不是有效的 UTF-8 文本，或包含二进制内容。请下载后检查原始字节。

JSON 与 XML 都按解码后的原始源码显示。第一版不得执行 <code>JSON.parse</code> 再 <code>JSON.stringify</code>：这会改变不安全整数、重复 key、空白、字面形式以及用户复制的文本。

## 安全渲染器 {#safe-renderer}

成功状态只渲染一个文本节点：

~~~tsx
<pre>{content}</pre>
~~~

禁止：

- iframe、object、embed；
- <code>dangerouslySetInnerHTML</code>、<code>innerHTML</code>；
- <code>DOMParser</code> 或 XML parser；
- Markdown/HTML 渲染；
- HTML data/blob URL；
- 按行或 token 生成大量 span；
- 自动链接、ANSI escape 与语法标记。

单个有界文本节点让 DOM 成本可预测，也让安全性质容易审计。

预格式化区域使用等宽字体、保留空白、默认不换行、独立承担横纵滚动、可键盘聚焦，并支持原生选择和复制。不换行是刻意选择：它能保留日志列对齐，也能避免一条 1 MiB 长行触发昂贵折行布局。

## UI 状态与权限 {#ux}

只有同时满足以下条件时，Preview 才可用：

~~~text
预览类型符合条件
AND 有对象读取权限
AND 不是 delete marker
AND 不是 prefix
~~~

对象详情页当前的与条件错误必须修复；列表与详情页必须共享同一资格函数。

符合格式但超限的对象仍然提供 Preview。弹窗负责解释正文为何没有加载；如果直接禁用按钮，用户无法区分大小、权限和类型问题。

弹窗必须区分：

| 状态 | 必要表现 |
| --- | --- |
| Loading | 可访问 busy 状态，不显示旧文本。 |
| Success | 可滚动原文和 Download。 |
| Empty | 明确“文件为空”。 |
| Too large | 对象大小、1 MiB 上限、Download；已知超限时正文请求数为零。 |
| Invalid UTF-8 / binary | 独立解释和 Download。 |
| Forbidden | 权限专属提示，不保留正文。 |
| Not found / replaced | 对象变化提示，不保留正文。 |
| Network / server error | 可操作的重试/下载状态。 |
| Aborted / closed | 静默清理。 |

HTTP 错误响应正文绝不能被解码后当作对象内容展示。

所有新增用户文案都必须走现有翻译层，并同时提供中英文。内容区和控制项必须在明暗主题、窄屏宽屏下保持可用。

## 功能与安全要求 {#requirements}

### 功能要求 {#functional-requirements}

- **FR1：** 现有媒体与 PDF 分类不变。
- **FR2：** 文本 fallback 严格遵守规范扩展名/MIME 矩阵。
- **FR3：** 不超过 1 MiB 的完整合格对象按严格 UTF-8 源码显示。
- **FR4：** 超限对象不显示部分内容。
- **FR5：** 空对象具有独立成功空状态。
- **FR6：** 当前版本与选定历史版本的元数据、大小和正文使用同一 version ID。
- **FR7：** 匿名访问与子路径部署保持当前请求行为。
- **FR8：** 列表与详情页采用相同类型/权限结论。
- **FR9：** 下载、分享、媒体、PDF 与存储行为不变。

### 安全要求 {#security-requirements}

- **SR1：** 对象字节只能通过文本内容进入 DOM。
- **SR2：** Text Preview 不得包含文档渲染器或解析器。
- **SR3：** 最多保留 1 MiB 加一个探测字节。
- **SR4：** 关闭或身份变化后，全部旧响应失效。
- **SR5：** 非法 UTF-8 与 NUL 内容不得冒充忠实文本。
- **SR6：** 错误、Redux、local storage、日志和遥测不得保存预览正文。
- **SR7：** 直接请求仍以服务端鉴权为最终权威。
- **SR8：** 不放宽 CSP 或后端 inline MIME。

## 实现范围 {#implementation}

预计 Console 改动：

1. 重构预览分类：完整保留当前媒体结论，显式增加文本 fallback；
2. 在预览类型联合中加入 <code>text</code>；
3. 新增 <code>PreviewText</code>：流式上限、严格解码、请求取消和明确状态；
4. 把文本对象显式路由到该组件；
5. 删除不可达的通用 iframe fallback；
6. 修复对象详情页 Preview 禁用表达式，并与列表共享资格逻辑；
7. 保留 unknown size，不再把它强制变成零；
8. 增加中英文文案；
9. 增加分类、组件、资源、安全、权限、版本与浏览器测试。

预计保持不变：

- Console 与 S3 API 路径；
- 后端 <code>safeMimeTypes</code>；
- CSP；
- 对象存储与元数据格式；
- 图片、PDF、音频、视频、下载和分享 handler；
- 外部前端依赖。

如果未来需要 tail、服务端转码、组织级策略，或者必须穿过不支持 Range 的代理链稳定工作，可另行设计专用服务端接口。

## 被否决的方案 {#alternatives}

### 继续禁用文本预览 {#alternative-disabled}

**优点：** 没有新代码和浏览器内存成本。  
**拒绝原因：** 日志与配置对象是日常对象存储工作流，强制下载查看是可以避免的 Console 能力退化。

### 复用同源 iframe {#alternative-iframe}

**优点：** 代码最少，浏览器原生展示。  
**拒绝原因：** 它把上传者控制内容与可变 MIME 元数据变成同源文档边界，同时也不限制资源使用。

### 现在新增后端预览 API {#alternative-backend}

**优点：** 服务端统一上限与文本响应。  
**第一版拒绝原因：** 用户本来就有对象读取权限，现有下载端点已经提供版本、鉴权与 Range；新 API 会重复契约，却没有建立新的数据访问边界。

### 显示大对象前 1 MiB {#alternative-truncation}

**优点：** 大日志更方便。  
**拒绝原因：** 部分 JSON/XML 在结构上会误导，UTF-8 边界还需要额外处理，而且同一个 Preview 动作不再意味着完整内容。

### 用替换字符解码非法 UTF-8 {#alternative-lossy}

**优点：** 损坏或旧日志仍可能部分可读。  
**拒绝原因：** 用户复制的文本不再忠实对应存储对象。有损查看和其他编码应建立独立、显式产品模式。

### 自动格式化 JSON {#alternative-json-format}

**优点：** 缩进更易读。  
**拒绝原因：** parse/stringify 会改变数字、重复 key、字面形式和复制内容。未来可以增加可选格式化视图，但绝不能替代原文默认。

### 引入 Monaco 或其他代码编辑器 {#alternative-editor}

**优点：** 行号、搜索、高亮与折叠。  
**拒绝原因：** Bundle、Worker、CSP 与维护成本超过有界只读预览所需；原生 <code>&lt;pre&gt;</code> 更小、更容易审计。

## 验收与测试计划 {#acceptance}

### 分类矩阵 {#classification-tests}

自动化测试必须锁定规范矩阵全部行、扩展名大小写、MIME 参数剥离、HTML/XHTML 显式拒绝，以及媒体冲突行为不变。

### 资源测试 {#resource-tests}

覆盖：

- 0 字节；
- 1 字节；
- 正好 1,048,576 字节；
- 1,048,577 字节；
- 已知超限且正文请求数为零；
- 未知大小；
- 206 且 <code>Content-Range</code> 已暴露总大小；
- 服务端忽略 Range 并返回 200；
- <code>Content-Length</code> 缺失或错误；
- 流式读取期间关闭和切换身份。

任何情况都不得保留或渲染超过允许的完整对象。

### 编码与保真测试 {#encoding-tests}

覆盖 UTF-8 中文、emoji、TAB、LF、CRLF、BOM、非法字节序列、NUL、JSON 不安全整数、重复 key、原始空白、XML 声明、DOCTYPE、CDATA 与 stylesheet 指令。

成功视图必须保留解码原文；非法与二进制情况必须进入独立状态。

### 安全测试 {#security-tests}

包含 <code>&lt;script&gt;</code>、事件属性、iframe 标签、SVG handler、XML stylesheet、外部实体与可疑 URL 的载荷必须：

- 逐字出现在 <code>&lt;pre&gt;.textContent</code>；
- 不创建对应 DOM 元素；
- 不执行脚本或弹窗；
- 不发出由对象正文触发的请求；
- 在 Text Preview 中接触不到 iframe、object、embed、HTML parser 或 XML parser。

### 权限与竞态测试 {#permission-tests}

验证：

- 没有 <code>GetObject</code> 时没有可用动作，也不保留正文；
- 历史版本遵守对应权限；
- 元数据与正文使用同一 version ID；
- 迟到旧响应不能覆盖新对象；
- 401、403、404、416、5xx 正文不成为预览内容；
- 匿名访问和 Console 子路径不回归。

### 浏览器回归 {#browser-tests}

使用真实 SILO/Console 测试实例检查中英文路由、明暗主题、窄屏与桌面宽度；新文本状态之外，还要对媒体、PDF、下载、分享与版本工作流进行冒烟验证。

## 交付与完成门槛 {#delivery}

虽然用户报告记录在 SILO 服务端仓库，修复本身归属 <code>pgsty/silo-console</code>。

交付分阶段进行：

1. 合入边界明确的 Console 源码与测试；
2. 通过 TypeScript 检查、生产构建、自动矩阵与真实浏览器安全回归；
3. 更新 Console 发布说明并重新生成实际嵌入的 Web 资产；
4. 发布 Console 版本；这项新增可见能力适合 minor 版本；
5. 更新 SILO 中 <code>github.com/minio/console =&gt; github.com/pgsty/silo-console</code> replacement 到精确新 pseudo-version；
6. 用精确依赖构建 SILO 候选版本并重复集成验证；
7. 发布 SILO 二进制与镜像，注明第一个包含此功能的版本。

这些是不同状态：

| 门槛 | 含义 |
| --- | --- |
| Console PR 合入 | 实现存在于源码。 |
| Console 资产/tag 发布 | Console 可以被独立消费。 |
| SILO 更新依赖 | SILO 主线已集成。 |
| SILO 正式发布 | 用户可以获得功能。 |

不能因为本地预览或 Console 源码 PR 已存在，就对用户宣称 issue #17 已经修复。

## 利弊取舍 {#trade-offs}

最终方案选择：

- 明确范围，而不是通用浏览器查看器；
- 完整小文件，而不是部分大文件；
- 原文保真，而不是自动格式化；
- 严格 UTF-8，而不是静默有损解码；
- 单个惰性文本节点，而不是完整编辑器；
- 复用下载 API，而不是新增后端契约；
- 可验证安全不变量，而不是便利的同源渲染。

代价真实存在：大型日志和旧编码仍需下载，第一版也没有搜索、行号、换行开关和高亮。这些缺失是刻意的，它们让功能足够小，可以审计；也足够强，可以信任。

## 审阅记录 {#review-record}

本设计从三个视角进行独立审阅：

- 产品范围、交付与验收；
- 安全与前端架构；
- 兼容性与当前源码验证。

评审者最初在“仅 MIME 是否可触发”和“非法 UTF-8 是否有损回退”上存在不同意见。交叉审阅后，三方达成唯一契约：

- 现有媒体分类优先；
- 文本 fallback 接受四种目标扩展名或四种精确规范化 MIME；
- HTML/XHTML 扩展名显式排除；
- 必须严格 UTF-8 并拒绝 NUL；
- 有损查看另立独立方案。

当前没有待裁决设计项，可以依照本文进入实现。

---
title: "Preview Text, Never Execute It: SILO Console Text Preview Design"
linkTitle: "Safe Text Preview"
date: 2026-08-23
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  Design for previewing small log, text, JSON, and XML objects in SILO Console as bounded, strict UTF-8 text—never as a same-origin executable document.
tags: [Design, Console, Preview, Security]
weight: 10
draft: false
url: "/blog/design/console-text-preview/"
---

SILO Console previews images, PDFs, audio, and video, but in v2.1.1 it could not preview the small logs, text files, JSON documents, and XML documents that operators inspect every day. Even when an object stored an accurate `Content-Type`, the frontend classified it as unsupported before selecting a preview renderer.

Restoring a browser-native iframe viewer would have been easy, and it would have been the wrong fix. An object in storage is controlled by the client that uploaded it. Loading that object as a same-origin HTML or XML document turns a convenience viewer into a script execution boundary.

The design shipped in [Console 2.2.0](/blog/release/console-2.2.0/) (tracking [#17](https://github.com/pgsty/silo/issues/17)) enforces a strict invariant:

> SILO Console previews eligible text objects as bounded UTF-8 text. It never asks the browser to interpret their markup, MIME type, or file contents as an executable document.

## Decision {#decision}

Console adds a dedicated `text` preview type and a `PreviewText` component governed by ten rules:

1. Preserve every existing `image`, `pdf`, `audio`, and `video` classification.
2. Consider a text fallback only when the existing media classifier returns `none`.
3. Admit the four target extensions (`.log`, `.txt`, `.json`, `.xml`) or four exact passive text MIME types (`text/plain`, `application/json`, `application/xml`, `text/xml`).
4. Fetch bytes through the ordinary authenticated download path without `preview=true`.
5. Enforce a hard application read limit of 1 MiB (`1,048,576` bytes).
6. Decode only strict UTF-8 (`fatal: true`) and reject payloads containing NUL bytes.
7. Render a single React text node inside a scrollable `<pre>` element.
8. Never use an `<iframe>`, HTML parser, XML parser, or HTML injection API.
9. Show the complete object or no object at all; never render a truncated JSON or XML fragment.
10. Keep **Download** available for files that exceed the size limit, fail UTF-8 decoding, or cannot be previewed.

No new S3 operation or backend preview route is added, and the backend inline MIME allowlist remains unchanged. Delivering this feature also tightened Console download responses: zero-byte `Range` requests return an empty `200 OK`, unsatisfiable ranges return `416 Range Not Satisfiable` with `Content-Range: bytes */N`, and `size` is always emitted in object JSON metadata (see [Console 2.2.0](/blog/release/console-2.2.0/#byte-ranges)).

## Previous Behavior in Console 2.1.1 {#current-behavior}

In SILO Console v2.1.1, the frontend preview type union contained only:

```text
image | pdf | audio | video | none
```

Its extension table listed media formats but omitted `.log`, `.txt`, `.json`, and `.xml`. Its MIME classifier likewise ignored `text/plain`, `application/json`, `application/xml`, and `text/xml`. Runtime verification showed the resulting split between frontend classification and backend response headers:

| Object | Frontend Classification | Console Download Response |
| --- | --- | --- |
| `.log` / `text/plain` | `none` | `inline`, `X-Frame-Options: SAMEORIGIN` |
| `.txt` / `text/plain` | `none` | `inline`, `X-Frame-Options: SAMEORIGIN` |
| `.json` / `application/json` | "Preview unavailable" | `inline`, `X-Frame-Options: SAMEORIGIN` |
| `.xml` / `application/xml` | `none` | `attachment`, `X-Frame-Options: DENY` |

In addition, the object-detail view used the wrong boolean conjunction when deciding whether **Preview** should be disabled: an authorized user could click **Preview** on an unsupported object only to receive an unavailable dialog, or see an enabled action that the server would reject.

Most importantly, the preview container still held a legacy generic same-origin `<iframe>` fallback. Because that branch was unreachable under the closed five-member type union, v2.1.1 did not have an exploitable text-preview XSS—but adding `text` to the union and letting it fall through to the `<iframe>` branch would have reactivated same-origin document execution.

## Root Cause {#root-cause}

The defect came from contract drift across three layers:

### Classification Drift {#classification-drift}

The browser frontend determines preview eligibility from the object's filename and `Content-Type` metadata, but its closed type union had no `text` variant. Even accurate object metadata could not select a renderer that did not exist.

### Response-Policy Drift {#response-drift}

The Console backend independently decides whether a download response may be served `inline`. It treated `text/plain` and `application/json` as passive inline types while forcing `application/xml` and `text/html` to `attachment`. That server policy was disconnected from the frontend classifier.

### Renderer Drift {#renderer-drift}

The dead `<iframe>` fallback remained in the component tree after reachable preview types were narrowed to media and PDF. Realigning the three layers required introducing a dedicated inert text renderer and deleting the dead `<iframe>` fallback rather than relying on MIME headers as a security boundary.

## Why Same-Origin Iframe Preview Was Rejected {#iframe-risk}

`X-Frame-Options: SAMEORIGIN` is not a sandbox. It restricts which parent origins may embed a response, not what script inside a same-origin frame can execute.

If uploader-controlled HTML, XHTML, SVG, or active XML is ever loaded as an inline same-origin document inside an `<iframe>`, script inside that frame runs in the Console origin. Even with `HttpOnly` session cookies blocking direct `document.cookie` reads, same-origin execution can still issue authenticated state-changing API requests against the Console backend.

`X-Content-Type-Options: nosniff`, Content Security Policy (CSP), and `Content-Disposition` provide defense in depth, but the primary security invariant must live in the data flow itself:

```text
untrusted object bytes
        |
        v
strict UTF-8 TextDecoder
        |
        v
React <pre>{textContent}</pre>

never:
iframe / innerHTML / DOMParser / XML parser / executable document
```

## Product Contract {#product-contract}

The feature is a read-only source-text viewer, not a web document renderer or an online code editor.

Users can:

- Open an eligible small object from either the bucket object list or the object-detail drawer.
- Read whitespace-preserving source text inside the preview modal.
- Select and copy text using native browser selection.
- Distinguish whether a preview refusal is caused by file size, non-UTF-8/binary encoding, missing permissions, object replacement, or network failure.
- Download the original bytes at any time.

Users are never misled by silent transformations:

- JSON is never parsed and re-serialized (which would alter large integers, duplicate keys, or whitespace).
- Large XML or JSON objects are never silently truncated into invalid prefix fragments.
- Invalid UTF-8 sequences are never masked with `U+FFFD` replacement characters.

## Goals and Non-Goals {#scope}

### Goals {#goals}

1. Preview small `.log`, `.txt`, `.json`, and `.xml` objects without requiring a local file download.
2. Keep object bytes strictly inert regardless of filename extension, `Content-Type`, or payload contents.
3. Bound retained response bytes and rendered text to 1 MiB (`1,048,576` bytes).
4. Preserve exact stored UTF-8 text rather than reformatting it.
5. Unify preview eligibility and permission checks across the list and object-detail views.
6. Support both current objects and explicitly selected historical `versionId` targets.
7. Preserve anonymous-access (`X-Anonymous: 1`) and subpath-hosting behavior.

### Non-Goals {#non-goals}

- HTML, XHTML, or Markdown rendering.
- XML parsing, XSLT evaluation, external entity resolution, or schema validation.
- Automatic JSON pretty-printing (`JSON.parse` / `JSON.stringify`).
- In-browser editing, syntax highlighting, line-number gutters, folding, or ANSI escape rendering.
- Head/tail or truncated prefix previews for objects larger than 1 MiB.
- Lossy decoding or charset guessing for GBK, UTF-16, or Latin-1 files.

An object such as `notes.md` stored with `Content-Type: text/plain` is eligible for raw UTF-8 text preview, without Markdown rendering.

## Eligibility Contract {#eligibility}

Eligibility is evaluated in two stages so existing media behavior never changes.

### Stage 1: Preserve Legacy Media Classification {#legacy-media}

Run the existing `image`, `pdf`, `audio`, and `video` classifier first. If it returns anything other than `none`, use that media classification.

### Stage 2: Apply Text Fallback {#text-fallback}

Only when the legacy media classifier returns `none`:

1. Explicitly reject final filename extensions `.html`, `.htm`, and `.xhtml`.
2. Match the final filename extension case-insensitively against `.log`, `.txt`, `.json`, and `.xml`.
3. Normalize `Content-Type` by stripping parameters (`; charset=...`), trimming whitespace, and lowercasing.
4. Match the normalized MIME type against `text/plain`, `application/json`, `application/xml`, and `text/xml`.

Matching either an allowed extension (when not excluded by rule 1) or an allowed exact MIME type selects `text`:

| Filename and MIME | Classification | Reason |
| --- | --- | --- |
| `report.txt` + `image/png` | `image` | Existing media classification wins |
| `report.json` + `application/pdf` | `pdf` | Existing media classification wins |
| `server.LOG` + `application/octet-stream` | `text` | Allowed extension, case-insensitive |
| No extension + `application/json; charset=utf-8` | `text` | Exact normalized MIME match |
| `page.html` + `text/plain` | `none` | Explicit HTML extension exclusion |
| `page.txt` + `text/html` | `text` | Extension admits it; HTML source renders as inert text |
| `notes.md` + `text/plain` | `text` | Exact MIME admits raw text |
| `image.svg` + `image/svg+xml` | `image` | Handled by existing image path |

## Resource Contract {#resource-contract}

The hard binary limit is:

```text
MAX_TEXT_PREVIEW_BYTES = 1,048,576
```

An object of exactly `1,048,576` bytes is eligible; `1,048,577` bytes is rejected as too large.

### Known Sizes {#known-size}

- If the selected object version has a known size exceeding `1,048,576` bytes, opening the modal goes directly to the **Too Large** state without issuing a body download request. Clicking **Retry** re-probes with a bounded `Range` request in case the listed size was stale.
- A known zero-byte size still issues the bounded request to verify authorization and existence, rendering the explicit **File is empty** state on an empty `200 OK`.
- Missing size metadata (`undefined`) is preserved as unknown rather than coerced to `0`, entering the bounded stream reader.

### Bounded Request and Sentinel Byte {#bounded-request}

For objects with a size within 1 MiB or an unknown size, the client sends:

```http
Range: bytes=0-1048576
```

Requesting `1,048,576 + 1` bytes uses the `1,048,577`th byte as an over-limit sentinel. The client:

1. Checks `Content-Range` and `Content-Length` headers immediately on response arrival.
2. Reads the response body as a `ReadableStream` rather than calling `response.text()` or buffering an unbounded `Blob`.
3. Accumulates at most `1,048,577` bytes in memory.
4. Aborts the stream immediately if the sentinel byte arrives (including when an upstream proxy ignores `Range` and streams a `200 OK`).
5. Renders text only after end-of-stream proves the complete object fits within `1,048,576` bytes.

## Request Identity and Cancellation {#request-lifecycle}

Each preview request is keyed by `bucket + object name + versionId` and preserves same-origin credentials, Console subpath routing, `version_id` query parameters, and `X-Anonymous: 1` headers. Closing the modal, switching objects or versions, or unmounting the component triggers both an `AbortController` signal and a generation-token invalidation check so a late stream completion can never overwrite a newer preview. Aborted requests clean up silently without firing error toasts.

## Encoding and Fidelity {#encoding}

Text decoding uses strict UTF-8:

```ts
new TextDecoder("utf-8", { fatal: true })
```

- A leading UTF-8 BOM (`EF BB BF`) is stripped automatically without displaying a zero-width character.
- Multi-byte Unicode, emoji, tabs, `LF`, and `CRLF` line endings are preserved verbatim.
- Invalid UTF-8 byte sequences throw a decode error and transition to the **Unsupported Encoding / Binary** state rather than substituting `U+FFFD`.
- Any decoded string containing a `NUL` (`\0`) character is rejected as binary data.

## Safe Renderer and UI States {#safe-renderer}

The success view renders a single React text node inside `<pre>{content}</pre>` with a monospace font, preserved whitespace, horizontal and vertical scrolling (`white-space: pre` by default to keep aligned logs readable and avoid expensive browser line-wrapping layout on long single-line JSON payloads), and native keyboard focus. The dead `<iframe>` fallback in the preview router is removed.

### UI States and Permissions {#ux}

The **Preview** action is enabled in both list and detail views if and only if:

```text
eligible preview type
AND s3:GetObject (or s3:GetObjectVersion) permission
AND not a delete marker
AND not a directory prefix
```

The modal presents distinct states for **Loading**, **Success**, **Empty** (`0` bytes), **Too Large** (`> 1 MiB`, showing object size, policy limit, **Download**, and bounded **Retry**), **Invalid UTF-8 / Binary**, **Forbidden (`403`)**, **Not Found (`404`)**, and **Network / Server Error**. HTTP error response bodies are never decoded into the preview pane.

## Functional and Security Requirements {#requirements}

### Functional Requirements {#functional-requirements}

- **FR1–FR3:** Preserve legacy media/PDF routing, classify text fallback via the normative extension/MIME matrix, and render complete eligible objects up to 1 MiB as strict UTF-8 source.
- **FR4–FR6:** Render no partial content for over-limit objects, provide an explicit empty-file state, and bind metadata, size, and body requests to the selected `versionId`.
- **FR7–FR9:** Preserve anonymous access, subpath routing, unified list/detail action eligibility, and existing download/share/media contracts.

### Security Requirements {#security-requirements}

- **SR1–SR4:** Render object bytes solely through `<pre>` text content without any HTML/XML/SVG/Markdown parser, retain at most `1,048,577` bytes, and invalidate in-flight requests on close or identity change.
- **SR5–SR8:** Reject invalid UTF-8 and `NUL` bytes, keep preview text out of Redux/storage/logs/error bodies, rely on server S3 authorization, and leave CSP and `safeMimeTypes` unchanged.

## Implementation Scope {#implementation}

1. Refactor preview classification so legacy media precedence is preserved and `text` is an explicit fallback.
2. Add the `PreviewText` component with streaming byte bounds, strict UTF-8 decoding, `AbortController` cancellation, and explicit modal states.
3. Remove the unreachable generic `<iframe>` fallback, align object-detail and list `Preview` eligibility, and preserve `undefined` unknown sizes.

## Rejected Alternatives {#alternatives}

### Keep Text Preview Disabled {#alternative-disabled}

Rejected because inspecting small logs, status files, and JSON/XML configurations is a daily operational workflow, and forcing a local file download for every check is unnecessary friction.

### Reuse the Legacy Same-Origin Iframe {#alternative-iframe}

Rejected because serving uploader-controlled content inside a same-origin `<iframe>` turns mutable MIME metadata into a script execution boundary and leaves browser memory use unbounded.

### Add a Dedicated Backend Preview Endpoint {#alternative-backend}

Rejected because the authenticated download endpoint already enforces `GetObject` / `GetObjectVersion` permissions and supports HTTP `Range` requests (`bytes=0-1048576`). Duplicating that logic in a second endpoint would widen the API surface without adding a new security boundary.

### Truncate Large Files to the First 1 MiB {#alternative-truncation}

Rejected because displaying a 1 MiB prefix of a 50 MiB JSON or XML file presents structurally broken markup as if it were the object, and requires extra multi-byte UTF-8 boundary slicing. Complete-or-nothing preview keeps the contract unambiguous.

### Decode Invalid UTF-8 with Replacement Characters {#alternative-lossy}

Rejected because silent `U+FFFD` substitution corrupts text that operators copy out of the preview modal. Legacy single-byte or UTF-16 encodings should be inspected via **Download**.

### Auto-Format JSON with Parse and Stringify {#alternative-json-format}

Rejected because `JSON.parse` followed by `JSON.stringify` silently mutates 64-bit integers exceeding `Number.MAX_SAFE_INTEGER`, collapses duplicate keys, and alters source whitespace.

### Embed Monaco or a Full Code Editor {#alternative-editor}

Rejected because web workers, syntax grammars, and editor bundle weight are unjustified for a bounded 1 MiB read-only viewer. A single `<pre>` text node is fast, predictable, and trivial to audit.

## Verification and Acceptance Plan {#acceptance}

### Classification Matrix {#classification-tests}

Automated tests lock every row of the two-stage extension/MIME matrix, case insensitivity, parameter stripping, `.html`/`.htm`/`.xhtml` exclusion, and media precedence.

### Resource Bounds {#resource-tests}

Tests cover `0` bytes, `1` byte, `1,048,576` bytes, `1,048,577` bytes, known over-limit skip, bounded **Retry**, `206 Partial Content`, `200 OK` when `Range` is ignored, and stream cancellation on close.

### Encoding and Fidelity {#encoding-tests}

Covers UTF-8 CJK and emoji, BOM stripping, invalid UTF-8 sequences, embedded `NUL` bytes, 64-bit JSON integers, duplicate JSON keys, and XML `DOCTYPE`/`CDATA`/stylesheet directives.

### Security Payloads {#security-tests}

Verifies that `<script>`, inline event handlers, `<iframe>`, SVG `onload`, and XML XXE/XSLT payloads appear literally in `<pre>.textContent`, create zero child DOM elements, and trigger zero network requests.

### Permissions and Version Races {#permission-tests}

Confirms that `401`/`403`/`404`/`416`/`5xx` bodies never render as preview content and that late responses from an older request generation cannot overwrite a newly selected object or `versionId`.

### Browser Regression {#browser-tests}

End-to-end Playwright checks against a live SILO + Console instance verify English and Chinese locales, light and dark themes, and desktop and narrow viewports alongside media, PDF, download, share, and version workflows.

## Delivery and Completion Gates {#delivery}

Shipped in [`pgsty/silo-console` v2.2.0](/blog/release/console-2.2.0/) ([PR #30](https://github.com/pgsty/silo-console/pull/30)) and embedded in [SILO Server 20260903](/blog/release/silo-20260903/), resolving [pgsty/silo#17](https://github.com/pgsty/silo/issues/17).

## Trade-Off Summary {#trade-offs}

This design chooses explicit scope over a generic browser viewer, complete small files over truncated fragments, source fidelity over automatic reformatting, strict UTF-8 over lossy decoding, and a single inert text node over an embedded code editor. Large logs (`> 1 MiB`) and non-UTF-8 files still require clicking **Download**—a deliberate boundary that keeps Console text preview small enough to audit and strong enough to trust.

### Design Review Record {#review-record}

Reviewed across product scope, frontend security/CSP isolation, and S3 `Range`/versioning semantics prior to merging [silo-console#30](https://github.com/pgsty/silo-console/pull/30).

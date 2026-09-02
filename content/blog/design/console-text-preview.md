---
title: "Preview Text, Never Execute It: SILO Console Text Preview PRD"
linkTitle: "Safe Text Preview"
date: 2026-08-23
lastmod: 2026-09-02
author: "Ruohang Feng"
summary: >
  The accepted PRD for previewing small log, text, JSON, and XML objects in SILO Console as bounded, strict UTF-8 text—never as a same-origin executable document.
tags: [Design, console, preview, security]
weight: 10
draft: false
url: "/blog/design/console-text-preview/"
---

> **Status:** shipped in SILO Console 2.2.0 · **Owner:** [pgsty/silo-console](https://github.com/pgsty/silo-console) · **Tracking:** [pgsty/silo#17](https://github.com/pgsty/silo/issues/17) · **Review:** consensus of product, security, and frontend architecture reviews

SILO Console can preview images, PDFs, audio, and video, but not the small logs, text files, JSON documents, and XML documents that operators inspect every day. A correctly stored <code>Content-Type</code> does not help: these objects are classified as unsupported before the preview renderer is selected.

Restoring the old browser-native behavior would be easy. It would also be the wrong fix. An object in storage is controlled by the user who uploaded it. Loading that object as a same-origin HTML or XML document would turn a convenience feature into an execution boundary.

The accepted design therefore makes a stronger promise:

> SILO previews eligible objects as bounded UTF-8 text. It never asks the browser to interpret their markup, MIME type, or file contents as a document.

This record fixes the product boundary, the resource limit, the security invariants, the implementation shape, and the evidence required before the feature can ship.

## Decision {#decision}

The first release will add a dedicated <code>text</code> preview type and a <code>PreviewText</code> component.

The contract is:

1. Preserve every existing image, PDF, audio, and video classification.
2. Only when the existing classifier returns <code>none</code>, consider a text fallback.
3. Admit the four target extensions or four exact passive text MIME types.
4. Fetch bytes through the ordinary authenticated download path, without <code>preview=true</code>.
5. Enforce a hard application read limit of 1 MiB.
6. Decode only strict UTF-8 and reject binary-looking content.
7. Render one React text node inside a scrollable <code>&lt;pre&gt;</code>.
8. Never use an iframe, HTML parser, XML parser, or HTML injection API.
9. Show the complete object or no object; do not show a truncated JSON or XML document.
10. Keep download available for files that are too large, invalidly encoded, or otherwise unavailable.

No Console API or S3 API change is required. The backend inline MIME allowlist is not expanded.

## Current behavior {#current-behavior}

The defect is present in SILO Console v2.1.1, the version currently pinned by SILO when this design was written.

The frontend preview union contains only:

~~~text
image | pdf | audio | video | none
~~~

Its extension table contains media formats, but not <code>.log</code>, <code>.txt</code>, <code>.json</code>, or <code>.xml</code>. Its MIME classifier likewise ignores <code>text/plain</code>, <code>application/json</code>, <code>application/xml</code>, and <code>text/xml</code>.

Runtime verification produced this split:

| Object | Frontend result | Console download response |
| --- | --- | --- |
| <code>.log</code> / <code>text/plain</code> | <code>none</code> | inline, <code>SAMEORIGIN</code> |
| <code>.txt</code> / <code>text/plain</code> | <code>none</code> | inline, <code>SAMEORIGIN</code> |
| <code>.json</code> / <code>application/json</code> | “Preview unavailable” | inline, <code>SAMEORIGIN</code> |
| <code>.xml</code> / <code>application/xml</code> | <code>none</code> | attachment, <code>DENY</code> |

The object-detail action also uses the wrong conjunction when deciding whether Preview should be disabled. An authorized user can click Preview for an unsupported object and receive only the unavailable message; in other combinations, the UI can offer an action before the server rejects it.

The preview component still contains a generic same-origin iframe fallback. It is unreachable under the current type union, so the current defect is not an exploitable text-preview XSS. The dead branch is nevertheless hazardous: adding <code>text</code> to the union and letting it fall through would reactivate precisely the document-loading behavior this design rejects.

## Root cause {#root-cause}

This is contract drift across three independently evolved layers.

### Classification drift {#classification-drift}

The browser code decides eligibility from filename and object metadata, but its closed type union has no text representation. Correct metadata cannot select a renderer that does not exist.

### Response-policy drift {#response-drift}

The Console server separately decides whether a response may be inline. It still treats plain text and JSON as safe passive MIME types, while XML and HTML remain attachments. That server decision is not reflected in the frontend classifier.

### Renderer drift {#renderer-drift}

The old generic iframe remains after the set of reachable preview types became media-only. The code therefore suggests a capability that the type system can no longer invoke.

The repair must realign the three layers without making MIME metadata a security boundary.

## Why same-origin iframe preview is rejected {#iframe-risk}

<code>X-Frame-Options: SAMEORIGIN</code> is not a sandbox. It controls who may embed a response; it does not limit what code inside a same-origin frame can do.

If uploader-controlled HTML, XHTML, SVG, or active XML were ever served as an inline same-origin document, it could act with the Console origin. An HttpOnly cookie would prevent direct cookie reads, but it would not prevent authenticated same-origin requests. A permissive or accidentally widened MIME rule would then turn stored content into stored application code.

<code>nosniff</code>, Content Security Policy, and <code>Content-Disposition</code> remain useful defense in depth, but none replaces the core invariant:

~~~text
untrusted object bytes
        |
        v
strict text decoder
        |
        v
React textContent

never:
iframe / innerHTML / DOMParser / XML parser / executable document
~~~

## Product contract {#product-contract}

The feature is a read-only text viewer, not a web previewer and not an online editor.

The user should be able to:

- open a small eligible object from either the list or object-detail surface;
- read whitespace-preserving source text in the existing preview modal;
- select and copy text using browser-native behavior;
- understand whether a failure is caused by size, encoding, permission, object replacement, or network error;
- download the original bytes at any time.

The user must never be led to believe that:

- formatted JSON is the stored object;
- a partial XML document is complete;
- replacement characters are original bytes;
- an unsupported encoding has been decoded faithfully;
- an active HTML/XML document has been safely “sanitized” and executed.

## Goals and non-goals {#scope}

### Goals {#goals}

1. Preview small logs, text, JSON, and XML without a local download.
2. Keep object content inert regardless of extension, MIME, or payload.
3. Bound retained response bytes and rendered text to 1 MiB.
4. Preserve the stored text rather than silently reformatting it.
5. Keep list and detail actions consistent with permissions and type eligibility.
6. Support current object versions and explicitly selected historical versions.
7. Preserve anonymous-access and subpath-hosting behavior.
8. Ship the feature in Console first, then consume that exact Console revision in SILO.

### Non-goals {#non-goals}

- HTML or XHTML rendering.
- XML parsing, XSLT, external entities, or schema validation.
- Markdown rendering.
- JSON pretty-printing.
- YAML or CSV-specific behavior.
- Editing or saving.
- Syntax highlighting, line numbers, search, folding, ANSI rendering, or linkification.
- Head, tail, or truncated previews for large objects.
- Lossy decoding or automatic detection of GBK, UTF-16, Latin-1, or other encodings.
- A new backend text-preview endpoint.
- Changes to the existing SVG, media, PDF, download, share, or storage contracts.

An object such as <code>notes.md</code> may still be shown as raw text when its exact MIME type is <code>text/plain</code>. It does not gain Markdown semantics.

## Eligibility contract {#eligibility}

Eligibility is deliberately two-stage.

### Stage 1: preserve the legacy media decision {#legacy-media}

Run the current image, PDF, audio, and video classifier unchanged. If it returns anything other than <code>none</code>, return that result.

This preserves historical behavior for conflicting filename and MIME combinations.

### Stage 2: apply text fallback {#text-fallback}

Only after the legacy result is <code>none</code>:

1. Reject final extensions <code>.html</code>, <code>.htm</code>, and <code>.xhtml</code>.
2. Match the final filename extension case-insensitively against:

   - <code>.log</code>
   - <code>.txt</code>
   - <code>.json</code>
   - <code>.xml</code>

3. Normalize Content-Type by removing parameters, trimming whitespace, and lowercasing it.
4. Match the normalized MIME exactly against:

   - <code>text/plain</code>
   - <code>application/json</code>
   - <code>application/xml</code>
   - <code>text/xml</code>

An allowed extension or an allowed exact MIME is sufficient. Broad matches such as <code>text/*</code>, substring tests, and <code>application/*+json</code> are forbidden in this release.

The resulting matrix is normative:

| Filename and MIME | Result | Reason |
| --- | --- | --- |
| <code>report.txt</code> + <code>image/png</code> | image | Existing media decision wins. |
| <code>report.json</code> + <code>application/pdf</code> | PDF | Existing media decision wins. |
| <code>server.LOG</code> + <code>application/octet-stream</code> | text | Allowed extension, case-insensitive. |
| no extension + <code>application/json; charset=utf-8</code> | text | Exact normalized MIME. |
| <code>page.html</code> + <code>text/plain</code> | none | Explicit active-extension exclusion. |
| <code>page.txt</code> + <code>text/html</code> | text | Extension admits it; HTML source remains inert text. |
| <code>notes.md</code> + <code>text/plain</code> | text | Exact MIME admits raw text, not Markdown rendering. |
| <code>image.svg</code> + <code>image/svg+xml</code> | existing image path | No new text or iframe path. |

Filename and MIME affect product eligibility only. They never select an executable rendering mode.

## Resource contract {#resource-contract}

The binary limit is:

~~~text
MAX_TEXT_PREVIEW_BYTES = 1,048,576
~~~

Exactly 1 MiB is eligible. 1 MiB plus one byte is not.

### Known sizes {#known-size}

- If the selected version has a known size greater than the limit, do not request its body.
- If its known size is zero, show the empty-file state.
- If its known size is within the limit, begin a bounded request.
- An absent size is not the same as zero; it enters the bounded unknown-size path.

The current list-to-modal handoff must therefore preserve <code>undefined</code> rather than converting it to zero with a truthy fallback.

### Bounded request {#bounded-request}

For a small or unknown size, request:

~~~http
Range: bytes=0-1048576
~~~

The extra byte is an over-limit sentinel.

The client must:

1. Inspect <code>Content-Range</code> and <code>Content-Length</code> when present.
2. Read the response as a stream rather than calling <code>response.text()</code> or building a complete Blob.
3. Retain at most the limit plus the sentinel byte.
4. Cancel immediately when the sentinel byte is observed.
5. Enforce the same limit when the server ignores Range and returns 200.
6. Render only after end-of-stream proves that the complete object is within the limit.

An over-limit object opens an explanation state with its known size, the 1 MiB policy, and a Download action. It never shows a prefix fragment.

## Request identity and cancellation {#request-lifecycle}

A preview request is identified by:

~~~text
bucket + object name + version ID
~~~

The request must use the existing generated API client or an equivalent base-path-safe helper so that it preserves:

- same-origin credentials;
- the current Console subpath;
- <code>version_id</code>;
- anonymous-mode <code>X-Anonymous: 1</code>;
- current error handling and permission boundaries.

Close, object change, version change, bucket change, and component unmount must abort the active request and clear the old content.

Abort alone is insufficient. A generation token or invalidation flag must also prevent a response that already completed reading or decoding from updating a newer preview.

An aborted request is not an error and must not produce an error toast.

## Encoding and fidelity {#encoding}

The first release supports strict UTF-8 only:

~~~ts
new TextDecoder("utf-8", { fatal: true })
~~~

Requirements:

- handle the UTF-8 BOM without displaying it;
- preserve Unicode text, emoji, tabs, LF, and CRLF;
- reject invalid UTF-8 rather than inserting replacement characters;
- reject decoded NUL characters as binary or unsupported content;
- do not guess another encoding;
- do not log or persist object text;
- always retain Download as the original-byte escape hatch.

The unsupported-encoding state should explain:

> This object is not valid UTF-8 text or contains binary data. Download it to inspect the original bytes.

JSON and XML are displayed exactly as decoded source text. The first release must not run <code>JSON.parse</code> followed by <code>JSON.stringify</code>: that can alter unsafe integers, duplicate keys, whitespace, lexical forms, and the text users copy.

## Safe renderer {#safe-renderer}

The success state renders one text node:

~~~tsx
<pre>{content}</pre>
~~~

The implementation must not use:

- iframe, object, or embed;
- <code>dangerouslySetInnerHTML</code> or <code>innerHTML</code>;
- <code>DOMParser</code> or an XML parser;
- Markdown or HTML rendering;
- an HTML data/blob URL;
- per-line or per-token spans;
- automatic links, ANSI escapes, or syntax markup.

One bounded text node keeps the DOM cost predictable and the security property inspectable.

The preformatted region uses a monospace font, preserves whitespace, defaults to no wrapping, owns both scrollbars, is keyboard focusable, and supports native selection and copy. No-wrap is intentional: it preserves aligned logs and avoids expensive layout of a single very long line.

## UI states and permissions {#ux}

The Preview action is enabled only when:

~~~text
eligible preview type
AND object read permission
AND not a delete marker
AND not a prefix
~~~

The object-detail conjunction bug must be fixed, and list and detail surfaces must share the same eligibility function.

An eligible over-limit object still offers Preview. The modal explains why content is not loaded; disabling the button would leave the user unable to distinguish size, permission, and type failures.

The modal distinguishes:

| State | Required behavior |
| --- | --- |
| Loading | Accessible busy state; no stale text. |
| Success | Scrollable raw text plus Download. |
| Empty | Explicit “File is empty” state. |
| Too large | Object size, 1 MiB limit, Download; no body request when size is already known. |
| Invalid UTF-8 / binary | Dedicated explanation and Download. |
| Forbidden | Permission-specific message; no retained text. |
| Not found / replaced | Object-change message; no retained text. |
| Network / server error | Actionable retry/download state. |
| Aborted / closed | Silent cleanup. |

HTTP error bodies must never be decoded and displayed as object content.

All new user-facing strings go through the existing translation layer and ship in English and Chinese together. The content region and controls must remain usable in light and dark themes and at narrow widths.

## Functional and security requirements {#requirements}

### Functional requirements {#functional-requirements}

- **FR1:** Existing media and PDF classification remains unchanged.
- **FR2:** The text fallback follows the normative extension/MIME matrix.
- **FR3:** Eligible complete objects up to 1 MiB render as strict UTF-8 source.
- **FR4:** Over-limit objects render no partial content.
- **FR5:** Empty objects have a distinct successful empty state.
- **FR6:** Current and selected historical versions use the same version for metadata, size, and body.
- **FR7:** Anonymous access and subpath hosting retain their current request behavior.
- **FR8:** List and detail actions apply the same type and permission decision.
- **FR9:** Download, share, media, PDF, and storage behavior do not change.

### Security requirements {#security-requirements}

- **SR1:** Object bytes can reach the DOM only through text content.
- **SR2:** Text Preview contains no document renderer or parser.
- **SR3:** At most 1 MiB plus one sentinel byte is retained.
- **SR4:** Closing or changing identity invalidates every previous response.
- **SR5:** Invalid UTF-8 and NUL content are not shown as faithful text.
- **SR6:** Errors, Redux, local storage, logs, and telemetry never retain preview text.
- **SR7:** Server authorization remains authoritative for direct requests.
- **SR8:** No CSP or backend inline MIME relaxation is introduced.

## Implementation scope {#implementation}

Expected Console changes:

1. Refactor preview classification so the current media decision is preserved and text is an explicit fallback.
2. Add <code>text</code> to the preview type union.
3. Add a dedicated <code>PreviewText</code> component with streaming bounds, strict decode, request cancellation, and explicit states.
4. Route text objects explicitly to that component.
5. Remove the unreachable generic iframe fallback.
6. Fix the object-detail Preview disable expression and share eligibility logic with the list surface.
7. Preserve unknown size instead of coercing it to zero.
8. Add English and Chinese strings.
9. Add classification, component, resource, security, permission, version, and browser tests.

Expected unchanged areas:

- Console and S3 API paths;
- the backend <code>safeMimeTypes</code> list;
- Content Security Policy;
- object storage and metadata formats;
- image, PDF, audio, video, download, and share handlers;
- external frontend dependencies.

If a future product requires tailing, server-side transcoding, organization-wide policy, or reliable behavior through proxies that ignore Range, a dedicated server endpoint may be designed separately.

## Rejected alternatives {#alternatives}

### Keep text preview disabled {#alternative-disabled}

**Benefit:** no new code or browser memory use.  
**Rejected because:** logs and configuration objects are a routine object-storage workflow, and download-only inspection is an avoidable Console regression.

### Reuse the same-origin iframe {#alternative-iframe}

**Benefit:** minimal code and browser-native presentation.  
**Rejected because:** it turns uploader-controlled content and mutable MIME metadata into a same-origin document boundary. It also leaves resource use unbounded.

### Add a backend preview API now {#alternative-backend}

**Benefit:** central server-side limits and normalized text responses.  
**Rejected for the first release because:** the user already has object-read permission, and the existing download endpoint provides versioning, authorization, and Range. A new API would duplicate contracts without establishing a new data-access boundary.

### Show the first 1 MiB of a large object {#alternative-truncation}

**Benefit:** better large-log convenience.  
**Rejected because:** partial JSON/XML is structurally misleading, UTF-8 boundaries need additional handling, and a single “preview” action would no longer mean complete content.

### Decode invalid UTF-8 with replacement characters {#alternative-lossy}

**Benefit:** some damaged or legacy logs remain partially readable.  
**Rejected because:** copied text would no longer faithfully represent the stored object. Lossy viewing and other encodings require a separate, explicit product mode.

### Auto-format JSON {#alternative-json-format}

**Benefit:** more readable indentation.  
**Rejected because:** parse/stringify can alter numbers, duplicate keys, lexical representation, and copied content. A future opt-in formatted view may sit beside, never replace, the raw default.

### Add Monaco or another code editor {#alternative-editor}

**Benefit:** line numbers, search, highlighting, and folding.  
**Rejected because:** bundle, worker, CSP, and maintenance costs exceed the needs of a bounded read-only preview. A native <code>&lt;pre&gt;</code> is smaller and easier to audit.

## Acceptance and test plan {#acceptance}

### Classification matrix {#classification-tests}

Automated tests must lock every normative matrix row, extension case handling, MIME parameter stripping, explicit HTML/XHTML denial, and unchanged media conflicts.

### Resource tests {#resource-tests}

Cover:

- 0 bytes;
- 1 byte;
- exactly 1,048,576 bytes;
- 1,048,577 bytes;
- known over-limit size with zero body requests;
- unknown size;
- 206 with a revealing <code>Content-Range</code>;
- server ignores Range and returns 200;
- missing or false <code>Content-Length</code>;
- close and identity changes during streaming.

No case may retain or render more than the complete allowed object.

### Encoding and fidelity tests {#encoding-tests}

Cover UTF-8 Chinese, emoji, tabs, LF, CRLF, BOM, invalid byte sequences, NUL bytes, JSON unsafe integers, duplicate keys, original whitespace, XML declarations, DOCTYPE, CDATA, and stylesheet processing instructions.

The raw success view must preserve decoded text. Invalid and binary cases must show their dedicated state.

### Security tests {#security-tests}

Payloads containing <code>&lt;script&gt;</code>, event attributes, iframe tags, SVG handlers, XML stylesheets, external entities, and suspicious URLs must:

- appear literally in <code>&lt;pre&gt;.textContent</code>;
- create no corresponding DOM elements;
- execute no script or dialog;
- cause no object-content-originated request;
- encounter no iframe, object, embed, HTML parser, or XML parser in Text Preview.

### Permission and race tests {#permission-tests}

Verify:

- no <code>GetObject</code> means no usable action and no retained body;
- historical versions require their corresponding permission;
- metadata and body use the same version ID;
- a late old response cannot replace a new object's preview;
- 401, 403, 404, 416, and 5xx bodies never become preview content;
- anonymous access and Console subpaths do not regress.

### Browser regression {#browser-tests}

Use a real SILO/Console test instance to inspect both English and Chinese routes, light and dark themes, and narrow and desktop widths. Media, PDF, download, share, and version workflows require smoke coverage alongside the new text states.

## Delivery and completion gates {#delivery}

The change belongs to <code>pgsty/silo-console</code>, even though the user report is tracked in the SILO server repository.

Delivery is staged:

1. Merge the focused Console source and test change.
2. Pass TypeScript checking, production build, automated matrices, and real-browser security regression.
3. Update Console release notes and regenerate the actual embedded web assets.
4. Publish a Console version; a minor release is appropriate for the new visible capability.
5. Update SILO's <code>github.com/minio/console =&gt; github.com/pgsty/silo-console</code> replacement to the exact new pseudo-version.
6. Build a SILO candidate from that exact dependency and repeat integration checks.
7. Publish the SILO binary and image, naming the first version that contains the feature.

These are separate states:

| Gate | Meaning |
| --- | --- |
| Console PR merged | Implementation exists in source. |
| Console assets/tag published | Console is independently consumable. |
| SILO dependency updated | SILO main has integrated the change. |
| SILO release published | Users can obtain the feature. |

Issue #17 should not be described as fixed for users merely because a local preview or Console source PR exists.

## Trade-off summary {#trade-offs}

The accepted design favors:

- explicit scope over a generic browser viewer;
- complete small files over partial large files;
- source fidelity over automatic formatting;
- strict UTF-8 over silent lossy decoding;
- one inert text node over a full editor;
- the existing download API over a new backend contract;
- a verifiable security invariant over convenient same-origin rendering.

The cost is real: large logs and legacy encodings still require download, and the first release has no search, line numbers, wrapping toggle, or highlighting. Those omissions are deliberate. They make the feature small enough to audit and strong enough to trust.

## Review record {#review-record}

The design was independently reviewed from three perspectives:

- product scope, delivery, and acceptance;
- security and frontend architecture;
- compatibility and current-source verification.

The reviewers initially differed on MIME-only eligibility and lossy UTF-8 fallback. After cross-review they reached a single contract:

- existing media classification wins;
- text fallback accepts the four target extensions or four exact normalized MIME types;
- HTML/XHTML extensions are explicitly excluded;
- strict UTF-8 and NUL rejection are required;
- lossy viewing is deferred to a separate proposal.

No unresolved design question remains. Implementation may proceed against this record.

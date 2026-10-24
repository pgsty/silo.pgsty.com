---
title: "When the Total Is Unknown: Folder Download Progress"
linkTitle: "Folder Download Progress"
date: 2026-08-23
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: "Design for replacing NaN% with truthful indeterminate progress when SILO Console downloads a streamed folder ZIP, without changing the server API or ordinary file downloads."
tags: [Design, Console, Download]
weight: 20
draft: false
url: "/blog/design/dir-percentage/"
---

SILO Console v2.1.1 displayed `NaN%` in the **Downloads / Uploads** drawer while downloading a folder. Although the streamed ZIP archive continued transferring normally and stored objects were intact, the progress bar entered an invalid determinate state—causing operators to assume the transfer had stalled or failed and to click **Download** repeatedly.

The repair shipped in [Console 2.2.0](/blog/release/console-2.2.0/) (`16960f7ab`, tracking [#62](https://github.com/pgsty/silo/issues/62)) and was embedded in [Server 20260903](/blog/release/silo-20260903/) (`edc8be6ed`). It enforces a single rule:

> A download may enter determinate mode only when it has a finite, positive total measured in bytes applicable to that response. Without such a total, it remains indeterminate until completion, failure, or cancellation.

([Console 2.4.1](/blog/release/console-2.4.1/#browser) later evolved folder and multi-selection downloads to use file-stream writers and native browser download handoff; see [Subsequent Evolution](#later-contract) below.)

## Observed Failure {#failure}

In SILO Console v2.1.1:

1. Upload several objects under a common prefix such as `folder/`.
2. In the parent bucket listing, select `folder/` and click **Download**.
3. Open **Downloads / Uploads** while the transfer is in flight.
4. The active row displays `NaN%` while the ZIP stream continues downloading.

## Root Cause {#root-cause}

The visible `NaN%` resulted from a three-layer mismatch between S3 prefix metadata, streamed ZIP responses, and XHR progress arithmetic.

### A Prefix Has No Object Size {#prefix-size}

S3 folders are logical common prefixes rather than stored directory objects. In the bucket listing model, a prefix ends with `/` and carries logical `size = 0` (which Console renders as `-` in the table). Because the generated API schema marks `size` as `omitempty`, zero-valued sizes are omitted from listing JSON. The single-selection download thunk passed `object.size` directly into the download helper, supplying `undefined` (or `0` for synthetic prefix records) as `fileSize`. Neither is a valid denominator.

### A Streamed ZIP Has No Known Wire Length {#streamed-zip}

When the server receives a download request for a path ending in `/`, it lists objects recursively under that prefix and connects a `zip.Writer` directly to an `io.Pipe`. Objects are read, compressed with Deflate, and flushed to the HTTP response stream on the fly.

Streaming the ZIP avoids buffering the entire archive in server RAM or temporary disk space and delivers the first response byte immediately. However, because the final compressed archive size does not exist when HTTP response headers are written, the server sends `Content-Type: application/zip` without a `Content-Length` header. Summing uncompressed source object sizes cannot substitute for `Content-Length` because `ProgressEvent.loaded` measures compressed wire bytes plus ZIP framing headers—two different units.

### Progress Events Without a Valid Denominator {#progress-event}

The XHR `progress` listener unconditionally evaluated:

```ts
Math.round((event.loaded / fileSize) * 100)
```

For a folder prefix or zero-byte object, `fileSize` was `undefined` or `0`, producing `NaN` (`loaded / undefined` or `0 / 0`) or `Infinity` (`loaded / 0`):

```text
common prefix: size = 0 (or undefined)
        |
        v
download(..., fileSize = 0)
        |
        v
streamed deflated ZIP, no Content-Length
        |
        v
event.loaded / 0 => NaN or Infinity
        |
        v
invalid percentage enters Redux; waitingForFile becomes false
        |
        v
determinate ProgressBar renders "NaN%"
```

## Product Contract {#contract}

The progress UI requires four invariants:

```text
determinate    => total is finite and total > 0
determinate    => percentage is finite and 0 <= percentage <= 100
unknown total  => indeterminate
terminal state => not indeterminate
```

Formulating the contract in terms of denominator validity rather than `objectPath.endsWith("/")` covers folder prefixes, zero-byte objects, omitted size metadata, and any future chunked response without special-casing object types.

## Goals and Non-Goals {#scope}

### Goals {#goals}

1. Never render `NaN%`, `Infinity%`, or a fabricated percentage during folder downloads.
2. Keep unknown-length transfers in the existing indeterminate progress animation.
3. Preserve determinate percentage progress for ordinary non-empty files.
4. Ensure completion, failure, and cancellation all exit indeterminate mode.
5. Ensure zero-byte files complete cleanly at `100%` without intermediate `NaN%`.
6. Prevent non-finite or out-of-range numbers from entering Redux state.

### Non-Goals {#non-goals}

- Buffering complete ZIP archives on the server just to compute `Content-Length`.
- Using the sum of uncompressed object sizes as a denominator for compressed ZIP wire bytes.
- Redesigning the Redux store schema in this bugfix.

## Technical Decision {#decision}

The repair comprises five focused rules:

### D1. Calculate Only from a Valid Total {#d1}

Extract progress arithmetic into a pure helper (`downloadProgress.ts`) with no DOM or Redux dependencies:

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

1. A finite positive `objectSize` preserves existing ordinary-file progress calculation.
2. When `objectSize` is unavailable (`0` or `undefined`), a finite positive `event.total` with `event.lengthComputable === true` serves as fallback.
3. Otherwise, the function returns `null`, signaling that no truthful percentage exists.

### D2. Keep Unknown Totals Indeterminate {#d2}

Update the XHR `progress` listener to dispatch `progressCallback` only when `calculateDownloadPercent` returns a non-null number:

```ts
req.addEventListener("progress", (event) => {
  const percent = calculateDownloadPercent(event, fileSize);

  if (percent !== null) {
    progressCallback(percent);
  }
});
```

Because download items initialize with `waitingForFile = true`—which `ObjectHandled` already renders as `<ProgressBar variant="indeterminate" />`—skipping `progressCallback` when `percent === null` keeps the row in indeterminate mode until completion, failure, or cancellation.

### D3. Make Cancellation Terminal {#d3}

Completion and failure already cleared `waitingForFile`, but `cancelObjectInList` did not. Setting `item.waitingForFile = false` on cancellation prevents an aborted indeterminate folder download from continuing to animate as if it were still active.

At the XHR boundary, calling `req.abort()` fires `readystatechange (DONE, status = 0)` before firing `onabort`. Guarding the generic `DONE` branch so `status === 0` defers to `onabort` / `onerror` ensures user cancellation is recorded as **Cancelled** rather than **Failed**.

### D4. Normalize Omitted Zero-Byte Sizes {#d4}

Passing `object.size || 0` in the single-selection download thunk restores the omitted logical zero before the response handler checks `Blob.size === fileSize`, allowing zero-byte objects to transition cleanly to `100%` on HTTP 200 completion.

### D5. Keep Server ZIP Streaming Unchanged {#d5}

The Go folder-download handler continues streaming Deflate-compressed ZIP archives over `io.Pipe` without buffering on disk or in memory.

## Progress State Machine {#state-machine}

| State | `waitingForFile` | `percentage` | Terminal Flags | Rendered UI |
| --- | ---: | ---: | --- | --- |
| Queued / awaiting first progress | `true` | `0` | None | Indeterminate bar |
| Active unknown-total transfer | `true` | `0` | None | Indeterminate bar |
| Active known-total transfer | `false` | `0..100` | None | Determinate percentage |
| Completed | `false` | `100` | `done = true` | Completed (`100%`) |
| Failed | `false` | Last valid | `failed = true, done = true` | Error state |
| Cancelled | `false` | `0` | `cancelled = true, done = true` | Cancelled state |

## Why This Design Is Sufficient {#proof}

### Ordinary Non-Empty File {#case-file}

`objectSize > 0` provides a finite positive denominator, `calculateDownloadPercent` returns a clamped integer in `[0, 100]`, `updateProgress` sets `waitingForFile = false`, and completion sets `100%`.

### Streamed Folder ZIP {#case-folder}

`objectSize` is `0`, `lengthComputable` is `false`, and `event.total` is `0`. `calculateDownloadPercent` returns `null`, no progress action is dispatched, and the row stays indeterminate until the stream finishes and sets `waitingForFile = false`, `percentage = 100`, and `done = true`.

### Future Response with Known Length {#case-future}

If a proxy or future archive endpoint supplies `Content-Length` (`lengthComputable = true` and `event.total > 0`), the fallback branch automatically renders determinate percentages without further code changes.

### Zero-Byte File {#case-zero}

The omitted size normalizes to `0`. Any intermediate progress event returns `null` rather than evaluating `0 / 0`, and upon receiving the empty `200 OK` body, `Blob.size === 0` matches `fileSize === 0` and transitions directly to `100%`.

### Failure and Cancellation {#case-terminal}

Both failure and cancellation set `waitingForFile = false` and `done = true`, guaranteeing that no terminated transfer continues showing an active indeterminate animation.

## Rejected Alternatives {#alternatives}

### Buffer the Entire ZIP on the Server {#alt-buffer}

Generating the full ZIP in server memory or temporary disk storage just to populate `Content-Length` would delay time-to-first-byte, increase server memory/disk pressure, and degrade concurrent downloads.

### Sum Uncompressed Object Sizes Under the Prefix {#alt-sum}

Summing logical source object sizes measures uncompressed input bytes, whereas `event.loaded` measures Deflate-compressed output bytes plus ZIP headers. Because the numerator and denominator have different units, the progress bar would stall below `100%` or jump erratically with compression ratio.

### Coerce Invalid Progress to `0%` {#alt-zero}

Displaying a determinate `0%` bar throughout a multi-gigabyte folder download misleads users into thinking zero bytes have transferred and the connection is dead.

### Special-Case Paths Ending in `/` {#alt-folder-check}

Checking `objectPath.endsWith("/")` would miss zero-byte files, missing metadata fields, and any other chunked response lacking `Content-Length`. Checking denominator validity handles all of them uniformly.

### Route Folders Through Immediate `BrowserDownload` {#alt-browser-download}

In Console 2.2.0, the legacy `BrowserDownload` helper clicked a hidden `<a>` tag and immediately marked the download `100%` complete before the first byte arrived, sacrificing error detection and cancellation. (A proper native browser handoff was later designed in [Console 2.4.1](#later-contract).)

### Sanitize `NaN` Inside `ProgressBar` Only {#alt-component}

Masking `NaN` only inside the React view component would leave corrupted `NaN` values in the Redux store and fail to keep `waitingForFile` in indeterminate mode.

### Widen Redux State to `percentage: number | null` Immediately {#alt-null-state}

Adding `null` alongside existing `waitingForFile`, `done`, `failed`, and `cancelled` booleans would multiply state combinations unnecessarily when `waitingForFile = true` already models and renders indeterminate progress.

## Requirements and Acceptance {#requirements}

### Functional Requirements {#functional}

- **FR1–FR3:** Return only `null` or an integer in `[0, 100]` from `calculateDownloadPercent`, keep unknown-total folder transfers in indeterminate mode (`waitingForFile = true`), and preserve determinate percentages for known-total object downloads.
- **FR4–FR5:** Normalize omitted zero-byte sizes so empty objects complete cleanly at `100%`, and clear `waitingForFile = false` across completion, failure, and cancellation.

### Non-Functional Requirements {#non-functional}

- Keep server-side ZIP streaming (`io.Pipe` without full-archive buffering), S3/Console API routes, and Redux state types unchanged.

### Acceptance Criteria {#acceptance}

- Zero `NaN%` or `Infinity%` labels appear in the download drawer across folder, ordinary-file, zero-byte, and cancelled transfers.

## Verification Plan {#tests}

### Pure Calculation Matrix {#unit-tests}

| Case | `loaded` | `objectSize` | `lengthComputable` | `event.total` | Expected |
| --- | ---: | ---: | --- | ---: | --- |
| Ordinary file, halfway | `50` | `100` | `false` | `0` | `50` |
| Common prefix (`folder/`) | `1024` | `0` | `false` | `0` | `null` |
| Initial `0 / 0` | `0` | `0` | `false` | `0` | `null` |
| Response-total fallback | `50` | `0` | `true` | `200` | `25` |
| Zero response total | `0` | `0` | `true` | `0` | `null` |
| Loaded exceeds total | `150` | `100` | `true` | `100` | `100` |
| Invalid `NaN` object size | `10` | `NaN` | `false` | `0` | `null` |
| Omitted `undefined` size | `10` | `undefined` | `false` | `0` | `null` |
| Non-finite `Infinity` total | `10` | `0` | `true` | `Infinity` | `null` |
| Negative `loaded` | `-1` | `100` | `true` | `100` | `null` |

### Reducer State Transitions {#state-tests}

Unit tests verify that new downloads start with `waitingForFile = true`, remain indeterminate when no numeric progress action is dispatched, transition to determinate on valid progress, and clear `waitingForFile = false` across completion, failure, and cancellation.

### End-to-End Browser Regression {#e2e-tests}

Playwright tests against a live SILO + Console instance use Chromium CDP network throttling to observe an active folder download, verify that the drawer shows an indeterminate bar with zero `NaN%` or `Infinity%` text, test mid-stream cancellation, and verify full ZIP completion alongside ordinary and zero-byte files.

## Implementation Scope {#implementation}

1. Add `downloadProgress.ts` with `calculateDownloadPercent`.
2. Update `Objects/utils.ts` to dispatch `progressCallback` only for non-null percentages and let `status === 0` XHR completions reach `onabort` / `onerror`.
3. Normalize `object.size || 0` in the single-selection download thunk.
4. Set `item.waitingForFile = false` in `cancelObjectInList`.
5. Add unit, reducer, and throttled Chromium Playwright regression tests.

## Delivery and Rollback {#delivery}

Shipped in [Console v2.2.0](/blog/release/console-2.2.0/) ([silo-console#29](https://github.com/pgsty/silo-console/pull/29)) and embedded in [SILO Server 20260903](/blog/release/silo-20260903/), resolving [pgsty/silo#62](https://github.com/pgsty/silo/issues/62). No storage or API migration is required.

### Definition of Done {#done}

- [x] `calculateDownloadPercent` returns only `null` or a finite integer in `[0, 100]`.
- [x] Active unknown-total folder downloads render indeterminate progress; ordinary and zero-byte files render valid determinate completion.
- [x] Completed, failed, and cancelled rows exit indeterminate mode (`waitingForFile = false`).
- [x] Shipped in Console `2.2.0` and Server `20260903`.

### Follow-Up Work {#follow-ups}

 Five follow-up items identified during this review—streaming downloads directly to the browser without in-memory `Blob` buffering, discriminated progress state, mid-stream ZIP error signaling, component-level non-finite guards, and `Blob` JSON error decoding—were tracked separately and addressed in subsequent Console releases.

## Subsequent Evolution: Browser Streaming Handoff in Console 2.4.1 {#later-contract}

Alongside this progress repair, [Console 2.2.0](/blog/release/console-2.2.0/) also made `size` an always-present JSON field in object listings and hardened server-side ZIP error propagation so unreadable entries abort the stream rather than being silently omitted.

Subsequently, [Console 2.4.1](/blog/release/console-2.4.1/#browser) eliminated in-memory XHR `Blob` buffering for downloads by handing single-folder and single-object downloads directly to the browser's native download manager and streaming multi-selection archives through file-system writers where supported. Under that newer architecture, the Console transfer row records the handoff to the browser, while ongoing byte progress and cancellation are managed natively by the browser's download manager.

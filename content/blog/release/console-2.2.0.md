---
title: "Silo Console 2.2.0 Release Notes"
linkTitle: "silo/console 2.2.0"
date: 2026-08-26
lastmod: 2026-08-26
author: "Ruohang Feng"
description: "SILO Console 2.2.0 release notes: safe text previews, downloads that cannot lie, repaired permission gating, an untangled user API, hardened notification and IAM policy writes, and a Go 1.27 dependency stack on maintained SILO forks."
tags: [Release, console]
weight: 1
draft: false
url: "/blog/release/console-2.2.0/"
aliases:
  - /releases/console-2.2.0/
---

> [!NOTE]
> **Released on 2026-08-26.** [`v2.2.0`](https://github.com/pgsty/silo-console/releases/tag/v2.2.0) points to final commit [`7dc4258a6`](https://github.com/pgsty/silo-console/commit/7dc4258a6a33b6e01b5b3bae8a0fd63f02b3bad8). The exact tagged tree passed the full CI matrix, vulnerability checks, and release pipeline. The public release contains six standalone binaries, nine Linux packages, and a SHA-256 checksum manifest.

**Version:** [`v2.2.0`](https://github.com/pgsty/silo-console/releases/tag/v2.2.0) · **Release commit:** `7dc4258a6` · **Status:** released · **Repository:** [pgsty/silo-console](https://github.com/pgsty/silo-console)

SILO Console 2.2.0 is a correctness-and-hardening release. It adds one new feature — a strictly bounded text preview for logs and structured text — and spends the rest of its budget making existing surfaces tell the truth: downloads that cannot silently ship a truncated archive, progress bars that cannot fabricate a percentage, permission gates that actually disable what they claim to disable, a user API that no longer entangles status changes with group membership, and database notification forms that emit exactly the connection string the server will store.

Underneath, the dependency stack moves to Go 1.27.0 and onto the maintained SILO forks: [`pgsty/silo-pkg` 3.12.1](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.1) replaces upstream `minio/pkg`, `pgsty/mc` replaces upstream `mc` as a library, `minio-go` moves to 7.3.0, and the etcd client line moves to 3.7.1, closing [CVE-2026-73500](https://pkg.go.dev/vuln/GO-2026-6107).

The final change set since [v2.1.1](https://github.com/pgsty/silo-console/releases/tag/v2.1.1) is 33 commits touching 176 source files (+8,794/−2,057 lines, not counting the regenerated embedded frontend assets).

**Why 2.2.0 and not 2.1.2:** the user-visible fixes alone would justify a patch release, but this cycle changes the provider of the shared policy/certificate implementation, crosses an etcd client minor boundary, splits a REST route, and deliberately changes download-failure semantics. Each of those deserves a minor-version line in the compatibility notes below rather than a silent patch.

## Text Preview for Logs and Structured Text {#text-preview}

The object browser can now preview `.log`, `.txt`, `.json`, and `.xml` objects as literal text. The implementation is deliberately paranoid, because "render arbitrary bucket content in the admin UI" is an XSS invitation:

- **Bounded by construction.** The request carries `Range: bytes=0-1048576`; the response is streamed into a fixed buffer with a hard cap, and `Content-Range`/`Content-Length` are strictly validated against what was actually read. An object over 1 MiB reports *too large* — it is never partially rendered as if complete.
- **Text or nothing.** The bytes must decode as strict UTF-8 (`TextDecoder` with `fatal: true`) and must not contain NUL; anything else reports *not previewable* instead of rendering mojibake or binary junk. Eligibility is an exact allowlist — the four extensions plus the precise MIME types `text/plain`, `application/json`, `application/xml`, `text/xml` — and `.html`/`.htm`/`.xhtml` are explicitly excluded even when their metadata claims `text/plain`.
- **No active document.** Content renders into a single DOM text node — never `innerHTML`, never an iframe, never a JSON-to-HTML transform. A regression suite feeds it HTML, SVG, and XML payloads and asserts they stay inert text.
- **Race-proof.** Switching quickly between objects invalidates in-flight previews by generation, so a slow response for the previous object cannot paint over the current one. Cancellation and retry are first-class states.
- **Anonymous-friendly.** Public/anonymous object pages get the same preview through the anonymous request path, without triggering any credentialed API call.

Alongside the new preview type, the existing preview plumbing was corrected: empty objects preview as empty instead of erroring, appended logs re-preview at their new length instead of the stale listed size, and metadata races when flipping between objects are gone. The preview and share dialogs now receive the object's real size ([`92e8f4e65`](https://github.com/pgsty/silo-console/commit/92e8f4e65fefad32581cfc86bd2a36f4305b7bd2)).

## Downloads That Cannot Lie {#downloads}

The whole download path — progress reporting, single objects, folders, archives, byte ranges — was rebuilt around one principle: **a download either completes correctly or fails visibly.**

### Honest progress {#download-progress}

A missing, invalid, or contradictory total no longer becomes a fabricated percentage: the progress indicator stays **indeterminate** until the real total is known. Zero-byte objects are normalized deliberately instead of falling into the unknown-total path, and abort/cancel are terminal states — a late progress event cannot resurrect a cancelled download. Download requests settle exactly once, JSON error blobs are parsed safely, and generated object URLs are revoked.

### Streaming folder downloads {#folder-downloads}

Single-folder downloads now use the browser's native streaming download path instead of accumulating the entire ZIP in JavaScript memory — a multi-GB folder no longer risks tab death. One consequence of the handoff model: the console's transfer manager reports the folder download *complete* once it hands the stream to the browser (a toast says so), and the browser's own download UI takes over from there — cancelling in the console after handoff does not stop the browser-side transfer. Multi-selection downloads still ride the existing POST response and therefore remain an in-memory `Blob`; changing that requires a separate API decision and is out of scope here.

### ZIP integrity — a deliberate behavior change {#zip-integrity}

> [!IMPORTANT]
> **This is the one change most likely to be noticed as "downloads broke".** In 2.1.1 and earlier, a folder/ZIP download that failed to read some objects **silently skipped them** and delivered an HTTP 200 archive missing files. In 2.2.0 any per-object failure — list, stat, read, entry creation, close, or copy — aborts the archive: a clean error if nothing was sent yet, an aborted connection mid-stream, so a truncated ZIP can never pass for a complete one.
>
> The practical consequence: a user whose policy grants *List* on a prefix but *GetObject* on only a subset of it — a common IAM setup — previously received a partial archive; now the download fails at the first denied object. That was silent data omission, and 2.2.0 treats it as the bug. Download exactly what you can read, or scope the folder download to a readable prefix.

### Byte ranges and status codes {#byte-ranges}

- Malformed or unsatisfiable non-empty `Range` headers now return **`416` with `Content-Range: bytes */N`** instead of a 500. Range parsing is stricter than Go's lenient default: signs, embedded whitespace, `bytes=-0`, and empty range elements are rejected.
- A range request against a **zero-byte object** returns an empty 200 instead of a 500 — this was the empty-object preview bug.
- Failures from the lazy object `Stat` now surface the **real S3 status** (403, 404, …) instead of a blanket 500.
- `206` responses now set `Content-Length` *before* the header flush, so partial responses carry correct framing.
- Object sizes are now **always serialized** — REST and WebSocket listings report `"size": 0` for zero-byte objects instead of omitting the field, and the UI displays `0 B`. This is the ground truth the honest-progress work stands on.

### Version history {#versions}

S3's valid `null` version ID stays visible instead of being dropped, version counting filters prefix matches to the exact object, and history is retained after bucket versioning is suspended or disabled.

## Permission Gates That Actually Gate {#permissions}

### Row actions were never disabled {#table-actions}

Every screen with a data table passed its permission predicate through a prop name (`disableButtonFunction`) that the table component **no longer reads** — so view/edit/delete buttons rendered enabled regardless of permission, on every one of the 10 affected screens (Users, Groups, Policies, IDP, webhook settings, bucket access/replication/lifecycle panels). The predicates are now wired to the prop the component actually honors, and a source-guard test fails the build if the dead prop name ever reappears. Server-side authorization was never affected — the buttons produced errors when clicked — but the UI now communicates permissions instead of lying about them.

### Independent service-account capabilities {#service-accounts}

Access-key management previously keyed several UI decisions off one combined permission check. 2.2.0 derives four independent capabilities — List, Create, Update, Remove — in one module and applies them consistently across the self-service Account screen and the admin user-details screen:

- the service-accounts tab shows when you can *list*, the create button when you can *create*, row selection and bulk delete only when you can *remove*, and the edit pencil only when you can *update*;
- **View is now genuinely read-only**: all fields disabled, no submit path, Enter is inert — previously "view" opened the editable dialog;
- the session's advertised *Create Access Key* capability is computed correctly for request-scoped policies: a `Deny` conditioned on `svc:DurationSeconds` (an expiry restriction that can only be evaluated once a concrete request exists) keeps the capability visible — including with wildcard admin actions — while unconditional or login-time denies now properly hide it. The server remains the final authority at request time. The previous code kept the capability visible for *any* conditional deny, which over-advertised it.
- an OIDC create/list/get/delete integration regression now runs through the UI's explicit-credential endpoint, including the expected self-update denial.

### Validate IAM policies before writes {#policy-validation}

Named-policy and service-account policy writes now reject malformed documents and bare S3 resource ARNs with a client error before making an Admin API request. Historical policy reads stay permissive for compatibility, but an incompatible stored policy must be corrected before it can be saved again. The strict parser and resource checks live in the console's write path instead of importing fork-only policy APIs, preserving the advertised upstream `minio/pkg v3.6.1` source-build floor.

### Anonymous pages behave anonymously {#anonymous}

Anonymous object-browser pages no longer issue protected Object Lock/retention requests that could only produce `Access Denied` noise, and they gained the language (文/A) and dark-mode controls.

## User Status and Groups Are Separate Operations {#user-api}

Toggling a user's enabled/disabled status and editing their group membership were one combined `PUT /user/{name}` call that required both payloads and — through the combined permission gate — demanded `admin:EnableUser` merely to edit groups. 2.2.0 splits them:

- **`PUT /user/{name}/status`** (new) changes only the status, validates the value against `enabled|disabled`, and rejects the signed-in user's attempt to enable/disable themselves. Failed toggles no longer leave the switch out of sync — the UI reflects the server's answer, not an optimistic flip.
- **`PUT /user/{name}/groups`** (existing) is now the only thing group editing calls, and no longer requires `admin:EnableUser`.
- **`PUT /user/{name}`** survives unchanged on the wire as a **deprecated compatibility endpoint** for existing API consumers; an unknown status there is now a 400 instead of a 500.

See [Compatibility](#compatibility) for the API-contract details, including a caveat for regenerated Swagger clients.

## Database Notification Forms That Emit What They Mean {#notifications}

The PostgreSQL and MySQL event-destination forms were rewritten around a shared DSN parser/serializer:

- Structured fields and the raw connection string are one state: the raw string stays authoritative until a structured field is edited, at which point a **canonical DSN** is rebuilt — libpq keyword/value quoting for PostgreSQL, IPv6-bracket-aware `go-sql-driver` format for MySQL. Mode switches no longer mangle manually entered strings.
- Generated previews **mask credentials**; the mask can never reach the API payload (the payload always uses the raw connection value).
- Saving requires both a connection string and a table, and cleared values actually propagate.
- The server now **rejects DSNs its own configuration grammar would corrupt** — embedded newlines, values that would parse as sibling config keys (`table=…` inside a password), unbalanced quoting — with a 400 *before* anything is stored, and without echoing the submitted secret back.
- Generic password and token fields across notification targets (Kafka, Redis, MQTT, NATS, webhooks) render as password inputs, including environment-overridden values.

### Restart honesty {#restart}

Configuration add, update, delete, and reset now honor the **server's actual restart-required answer** instead of hardcoding "restart needed" (or worse, dropping it). The pending-restart flag is monotonic: once any operation requires a restart, later operations that don't cannot clear it — only an actual service restart does.

### Upload advisory {#upload-advisory}

Browser uploads larger than 5 GiB get a non-blocking warning: the console uploads as one non-resumable request, and `mcli` with multipart upload is the right tool at that size.

## Sessions, Metrics Auth, and i18n Hardening {#hardening}

- **Sessions fail fast.** An anonymous/empty session gets an immediate 401 instead of hanging on an empty-credential admin request. The console accepts the canonical `401` and the legacy `403` invalid-session responses, and expired-session redirects are subpath-aware — a console served under `/console/` redirects within its base path.
- **Prometheus Basic auth works everywhere.** The health check and the root-fallback probe now send Basic credentials (previously Bearer-only, so a Basic-auth Prometheus disabled every dashboard widget), Bearer tokens keep precedence, and every response body is drained so keep-alive connections are actually reused.
- **Placeholder substitution is escape-proof by construction.** Translated placeholder filling uses a one-pass literal formatter: values containing `$&`, `$1`, `` $` ``, backticks, or braces stay literal, repeated placeholders all fill, and an AST source-guard test bans the unsafe `String.replace` pattern from ever returning.

## Toolchain and Dependencies {#dependencies}

### Go 1.27 baseline {#go-toolchain}

| Component | 2.1.1 | 2.2.0 |
|:--|:--|:--|
| `go` directive, build image, CI matrix | `1.26.5` / `1.26.x` | `1.27.0` / `1.27.x` |
| `golang.org/x/crypto` | v0.54.0 | v0.55.0 |
| `golang.org/x/net` | v0.57.0 | v0.58.0 |
| `golang.org/x/text` | v0.40.0 | v0.41.0 |
| `golang.org/x/mod` | v0.37.0 | v0.40.0 (closes [CVE-2026-56864/-56865](https://pkg.go.dev/vuln/GO-2026-6180)) |
| `golang.org/x/tools` | v0.47.0 | v0.49.0 |

### The SILO forks {#silo-forks}

```go
require github.com/minio/pkg/v3 v3.6.1

replace github.com/minio/pkg/v3 => github.com/pgsty/silo-pkg/v3 v3.12.1
replace github.com/minio/mc => github.com/pgsty/mc v0.0.0-20260806055018-b0021fd01ccb
```

- **`silo-pkg` 3.12.1 is the release dependency.** [`pgsty/silo-pkg` v3.12.1](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.1) was published on 2026-08-25 and the console pins it directly. It builds on the [3.12.0 release](/blog/release/pkg-3.12.0/), which carries the policy resource-boundary hardening, condition-key lookup repair, LDAP and certificate-watcher fixes, and the Go 1.27 / etcd 3.7 baseline.
- **The `mc` library moved to the `pgsty/mc` fork** at a date-tagged pseudo-version. Import paths are unchanged.
- **The `require` line stays on upstream `v3.6.1` deliberately.** Go ignores `replace` directives in dependency modules, so a downstream module that requires this console resolves *upstream* `minio/pkg` — and the SILO `v3.12.1` tag does not exist upstream. Requiring a real upstream tag keeps the console resolvable downstream; the replace applies the fork for the console's own builds. The final CI verifies the public source-build surface against upstream v3.6.1. This is compile compatibility: a downstream build without its own top-level replace gets upstream *behavior*, not the fork's SILO-specific IAM semantics.
- **`go-systemd` is pinned back to v22.6.0**: v22.7.0 uses `CLOCK_MONOTONIC` on NetBSD, which doesn't compile there; the pin holds until upstream ships the fix.

### etcd 3.7.1 — client libraries only {#etcd-3-7}

All three etcd Go modules move together from 3.6.8 to 3.7.1, closing the TLS-listener denial of service [GO-2026-6107 / CVE-2026-73500](https://pkg.go.dev/vuln/GO-2026-6107). etcd 3.7 removes legacy protobuf remnants and makes `clientv3.New` non-blocking — migrations that matter to consumers that construct clients or embed servers. The console does neither: its only etcd path is `silo-pkg/quick` operating on an already-created client with plain v3 `Get`/`Put`. **This upgrades compiled client libraries only** — it does not touch an operator's etcd servers, cluster data, or deployment topology; a server upgrade to 3.7 still follows etcd's own one-minor-at-a-time procedure.

### Third-party maintenance stays conservative {#third-party}

The final release updates `minio-go` to v7.3.0 after a separate compatibility review, migrates its INI import path, and adds lifecycle-filter XML coverage. A console-side compatibility decoder accepts legacy AccountInfo tag payloads returned by older servers. Other accepted maintenance moves include `jwx` v2→v3 with `httprc` v3, `go-openapi/swag/conv`+`typeutils` 0.28.0, `grpc-gateway` 2.29.0, `cheggaaa/pb` 1.0.30, and `go.yaml.in/yaml/v3` 3.0.5. Larger unrelated go-openapi, `pb/v3`, compression, and test-library updates remain deferred.

On the frontend, the vulnerability workflow now covers pushes, manual runs, and development dependencies with immutable installs; vulnerable transitive resolutions were refreshed (`fast-xml-parser` 5.11, `nanoid` 3.3.18, `@babel/core` 7.29.7), dead exports and the unused `http-status-codes` dependency were removed. The new `fast-xml-parser` 5.x transitive tree (`@nodable/entities`, `is-unsafe`, `anynum`, `fast-xml-builder`, `path-expression-matcher`, `xml-naming`) was supply-chain-checked during this review: all six packages are published by the fast-xml-parser author's own account and organization, their installed code is free of execution/network/exfiltration patterns, and the whole tree is development-only — nothing ships in the browser bundle.

## Security Review {#security}

- `govulncheck` at the release tree: **zero vulnerable symbols reached, zero vulnerable imported packages**. The Swagger build tool scans clean separately.
- Closed by dependency moves: [CVE-2026-73500](https://pkg.go.dev/vuln/GO-2026-6107) (etcd TLS listener DoS), [CVE-2026-56864 / CVE-2026-56865](https://pkg.go.dev/vuln/GO-2026-6180) (x/mod verification).
- Still reported, still unreachable: the module-level [GO-2026-5932](https://pkg.go.dev/vuln/GO-2026-5932) openpgp advisory — the console does not import `x/crypto/openpgp`, and no fixed release exists.
- The text preview was reviewed as an XSS surface (see [above](#text-preview)); its regression suite includes active-payload tests.
- The permission-gating fixes are UI-truthfulness fixes: server-side authorization was never bypassed in 2.1.1; the console simply displayed controls it shouldn't have.

## Compatibility {#compatibility}

**Nothing changes for deployment plumbing:** no environment variable, configuration format, command, binary name, systemd unit, port, or embedded data layout changes. The release binary remains self-contained; Go 1.27.0 is a build-time requirement only.

**HTTP API contract** (console's own REST API):

| Route | Change |
|:--|:--|
| `PUT /user/{name}` | Unchanged on the wire; now deprecated. OperationId renamed `UpdateUserInfo` → `UpdateUserInfoLegacy`, body model renamed to `legacyUpdateUser` (identical schema). Unknown status: 500 → 400. |
| `PUT /user/{name}/status` | **New.** Status-only body (`enabled`/`disabled` enum, 422 on violation), returns a user object populated with access key and status only — clients must not read group data from it. |
| `updateUser` model | Now status-only with enum — **breaking for generated-spec consumers**; the old shape lives on as `legacyUpdateUser`. |
| Object download | Error semantics changed: bad ranges 500→416 (+`Content-Range: bytes */N`), range-on-empty 500→200, `Stat` failures 500→real S3 status, ZIP failures silent-partial-200→visible failure, 206 responses carry `Content-Length`. |
| Listings & WebSocket | `size` always serialized, including `0`. Additive. |
| `PUT /configs` | New 400 class for database DSNs the server's config grammar would corrupt. |
| Config reset/delete | `restart` in the response now reflects the server's real answer instead of always `true`. |
| `GET /session` | 401 for empty-credential principals; the advertised Create-Access-Key capability is computed more strictly (see [service accounts](#service-accounts)). |

> [!NOTE]
> **If you generate client SDKs from `swagger.yml`:** the `UpdateUserInfo` operation now points at `/user/{name}/status` with a status-only body. Code calling the generated `UpdateUserInfo` symbol keeps compiling but targets the new route; the old combined call is `UpdateUserInfoLegacy`. Audit call sites when you regenerate.

**Behavior changes an operator may notice:**

1. Folder/ZIP downloads over partially readable prefixes **fail instead of silently omitting** unreadable objects ([details](#zip-integrity)).
2. Range parsing is stricter than Go's lenient default; degenerate range headers (`bytes=-0`, empty elements) now get 416 instead of best-effort handling.
3. Database notification configs that only worked by accident (DSNs the config grammar mangled on the way in) are now rejected up front with a 400.
4. The Create-Access-Key control is hidden for sessions whose policy unconditionally denies it (previously any conditional deny kept it visible).
5. A pending restart-required indicator persists until an actual restart, instead of being clearable by a later unrelated config change.
6. If a reverse proxy in front of the console compresses `/api/v1/…/download` responses, the text preview's strict `Content-Length` verification will reject every preview as an error. The console itself only compresses static assets — leave API responses uncompressed at the proxy.

## Regression Review {#regression-review}

Because this release rewrites the download path and re-platforms the shared policy library, the full diff against v2.1.1 was re-reviewed adversarially in five parallel passes (Go API; object browser preview/download; permission gating and service accounts; forms/i18n/session; dependencies/build/CI), each hunting specifically for behavior that worked in 2.1.1 and silently changed.

**Verdict: no unintentional regressions found.** Every confirmed behavioral difference is one of the deliberate changes documented above. The review did surface two small pre-existing UI-guard defects, now visible because the dead disable-prop was brought back to life with predicates whose argument type was never right:

- the "cannot delete the Default IDP configuration" row guard compares the row object against the string `"Default"` and therefore never engages (`IDPConfigurations.tsx`);
- the "cannot delete an env-override webhook endpoint" row guard has the same object-vs-string mismatch and is inert (`WebhookSettings.tsx`).

Neither is a 2.2.0 regression — both predicates were entirely dead in 2.1.1 — and in both cases the server still enforces the real rules. They remain documented follow-up items after the release. Two sharp edges are recorded as known limitations rather than defects: the new PostgreSQL DSN parser accepts only canonical `key=value` syntax when populating structured fields (an unusual-but-libpq-valid DSN shows empty structured fields, and editing a structured field then rebuilds the DSN from those fields), and TestCafe/Playwright coverage asserts UI gating while live-server deny-path coverage remains the integration suites' job.

## Verification {#verification}

The release decision combines local release-preparation evidence with remote gates run against the exact tagged tree, [`7dc4258a6`](https://github.com/pgsty/silo-console/commit/7dc4258a6a33b6e01b5b3bae8a0fd63f02b3bad8):

**Local release-preparation gates** — `go build ./...`, `go vet ./...` (plus `-tags testrunmain`), `gofmt`, `golangci-lint`, `go test -race ./...`, `go tool swagger validate`, `govulncheck`, TypeScript `tsc`, Playwright, Prettier, knip, release-tag cross-compiles for linux/amd64 and linux/arm64, and `go mod verify`.

**Embedded-assets determinism** — the frontend was rebuilt from source through the full pipeline (`yarn build` + embed optimization) and the result compared against the committed `web-app/build`: **byte-identical, zero dirty files**. The nine commits after the earlier `19047161f` candidate changed Go compatibility, workflows, and browser-test timing, but not product frontend source or embedded assets.

**CI, exact final tree** — [Workflow run 32888892876](https://github.com/pgsty/silo-console/actions/runs/32888892876) reported 32 successful jobs and one explicitly disabled React-test placeholder. It covered lint, semgrep, Go and API tests, five cross-compile targets, Swagger drift, latest-MinIO source builds, distributed integration, site replication, hermetic SSO, the complete TestCafe permissions matrix, subpath-nginx, Playwright, and coverage. [Vulnerability Check 32888899120](https://github.com/pgsty/silo-console/actions/runs/32888899120) passed both jobs on the same commit.

**Release pipeline** — [goreleaser run 32916237254](https://github.com/pgsty/silo-console/actions/runs/32916237254) passed both jobs against `v2.2.0` and published the public GitHub release.

**Downstream contract** — in a scratch tree with every `replace` removed, `go mod tidy` + `go build ./...` succeed against upstream `minio/pkg v3.6.1`, proving the fork replacement never leaks fork-only symbols into the public module surface.

**Test-infrastructure repairs shipped in this cycle** (so the gates above actually gate): the Docker-backed integration/replication/SSO suites are back behind the `testrunmain` build tag (a bare `go test ./...` no longer tries to start containers); the SSO gate is hermetic — no `sudo /etc/hosts` edits, no ad-hoc pip installs, pinned SILO image, own port, real teardown; the integration gate asserts the new 416 range semantics and stopped binding its PostgreSQL fixture to a host port; the browser gates run off-Linux by publishing fixture ports; a stale pre-fork "MinIO administrator" selector was fixed; state-mutating TestCafe suites are serialized; Playwright CI installs the committed lockfile immutably.

## Release Artifacts {#release-artifacts}

The [v2.2.0 GitHub release](https://github.com/pgsty/silo-console/releases/tag/v2.2.0) publishes:

1. six standalone binaries: Linux amd64/arm64/armv6, macOS amd64/arm64, and Windows amd64;
2. nine Linux packages: DEB, RPM, and APK for amd64, arm64, and armv6;
3. `silo-console_2.2.0_checksums.txt`, plus the SHA-256 digest GitHub records for every asset.

Those assets, the tag, and the release page are verified here. This page does not claim a separately distributed container image or detached signatures.

## Related Commits {#related-commits}

- [`16960f7ab`](https://github.com/pgsty/silo-console/commit/16960f7ab894ee8c1750ad9a6a93f984f5cd5077) — fix: keep unknown downloads indeterminate
- [`5968bb37d`](https://github.com/pgsty/silo-console/commit/5968bb37df0f340398f1283a2a63f2c1c9e9ad5f) — chore(deps): align the SILO Go dependency stack
- [`288ab1240`](https://github.com/pgsty/silo-console/commit/288ab12401f1d077511840a790dc697c5295e789) — fix: harden sessions, metrics, and translations
- [`ecf3bb492`](https://github.com/pgsty/silo-console/commit/ecf3bb492691b5bb81d83473321aec4f376a33d7) — fix: harden object previews and downloads
- [`902d9650d`](https://github.com/pgsty/silo-console/commit/902d9650d491723a63dceca7e7f866a2311ce5e4) — chore: tighten dependency and test gates
- [`194c70c7a`](https://github.com/pgsty/silo-console/commit/194c70c7a81bc08716be12b12e87e384dfc89425) — build: prepare SILO Console v2.2.0
- [`927b44e26`](https://github.com/pgsty/silo-console/commit/927b44e26a70ddbefc610371627d1aaddee94697) — fix: harden database notification forms
- [`da2191be9`](https://github.com/pgsty/silo-console/commit/da2191be97ef279c9316c38996ac8c8c0209d26d) — fix: clarify console upload and secret limits
- [`6141c2445`](https://github.com/pgsty/silo-console/commit/6141c2445f3f2872553003021093d84137c742e5) — build: refresh SILO Console v2.2.0 assets
- [`097e76155`](https://github.com/pgsty/silo-console/commit/097e761559b62695e34d3543543d55189bce19c5) — chore(deps): bump the shared package fork to v3.12.0
- [`99ca523d6`](https://github.com/pgsty/silo-console/commit/99ca523d693c8b0b6b3523c615e8079125663aa3) — fix: split user status updates out of the combined user route
- [`f4097992f`](https://github.com/pgsty/silo-console/commit/f4097992f1a25ecadf5c874649885187b1c45768) — fix: honor the server restart result for configuration changes
- [`f1280032a`](https://github.com/pgsty/silo-console/commit/f1280032a8462de1fd00f60626f50bc11045b033) — fix: restore permission-gated table row actions
- [`24ce0af97`](https://github.com/pgsty/silo-console/commit/24ce0af974a3d1fe31449cb3d78e1a0935692dbf) — fix: keep request-scoped access key conditions visible in the console
- [`92e8f4e65`](https://github.com/pgsty/silo-console/commit/92e8f4e65fefad32581cfc86bd2a36f4305b7bd2) — fix: pass the object size into the preview and share dialogs
- [`8f6fb3c78`](https://github.com/pgsty/silo-console/commit/8f6fb3c78e9bd5aed73386bf0c709a143ff4fa0f) — test: make the SSO gate hermetic and pin it to a SILO release
- [`384a2cb95`](https://github.com/pgsty/silo-console/commit/384a2cb95abe5db6ecbbe6edbaef8b1dd9c13840) — build: refresh SILO Console assets and record the changes
- [`a73cda376`](https://github.com/pgsty/silo-console/commit/a73cda376148a0ac19f9f714dd18d5925399ca1d) — test: fix the integration gate's stale range and host port
- [`cf5049c1d`](https://github.com/pgsty/silo-console/commit/cf5049c1df59092aea3f9caea7f5f8e64e0333a6) — test: make the browser gates runnable and fix a stale selector
- [`6fa19d857`](https://github.com/pgsty/silo-console/commit/6fa19d8575f6f0a42954747a16a43d3b9cde1d97) — fix: complete service account permission boundaries
- [`7e57771a4`](https://github.com/pgsty/silo-console/commit/7e57771a44495e7c23e21dcff8f19b171d60c672) — build: refresh SILO Console assets
- [`57cfe7aa0`](https://github.com/pgsty/silo-console/commit/57cfe7aa078361e0e1d41897e460adef1cd1e5a3) — fix: restore downstream and browser release gates
- [`19047161f`](https://github.com/pgsty/silo-console/commit/19047161fa0e6ad6436057e5cc996ac6eb0751e4) — test: stabilize permissions browser gates
- [`e37dec873`](https://github.com/pgsty/silo-console/commit/e37dec873bf1a2f8e15b6937aa391da2b9626ba4) — fix: validate IAM policies before writes
- [`28505ed23`](https://github.com/pgsty/silo-console/commit/28505ed238084b0df4f2026b35adbb2145969cb4) — chore: update minio-go to v7.3.0
- [`16abb971e`](https://github.com/pgsty/silo-console/commit/16abb971e12610a333f3f38a3cb9f52d815f18c9) — ci: harden validation and release gates
- [`2ddfcd036`](https://github.com/pgsty/silo-console/commit/2ddfcd0361b537a5a6ab531600bd3d37f408cf59) — fix: accept legacy AccountInfo tag payloads
- [`31332bca9`](https://github.com/pgsty/silo-console/commit/31332bca9456a1b3340b98fa9108650216578eaf) — fix: preserve policy source compatibility
- [`3a8251086`](https://github.com/pgsty/silo-console/commit/3a82510863366abc2ed7c865f12f4e0bb1562a2a) — ci: allow permission tests to finish
- [`c159fff78`](https://github.com/pgsty/silo-console/commit/c159fff78af92ec5ee237f3c4f289a11461cb401) — ci: serialize shared-role permission tests
- [`2e91cdf9a`](https://github.com/pgsty/silo-console/commit/2e91cdf9afa71f588d467a785e922fb9b54e0a40) — test: wait for watch controls to become ready
- [`7dc4258a6`](https://github.com/pgsty/silo-console/commit/7dc4258a6a33b6e01b5b3bae8a0fd63f02b3bad8) — test: allow asynchronous UI controls to settle

Links:

- [SILO Console source](https://github.com/pgsty/silo-console) · [v2.2.0 release](https://github.com/pgsty/silo-console/releases/tag/v2.2.0)
- [silo-pkg 3.12.1 release](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.1) · [silo-pkg 3.12.0 release notes](/blog/release/pkg-3.12.0/)
- [SILO website](https://silo.pgsty.com/) · [Documentation](https://silo.pgsty.com/docs/)

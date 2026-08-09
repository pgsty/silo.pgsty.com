---
title: "Silo Console 2.1.0 Released"
linkTitle: "silo/console 2.1.0"
date: 2026-08-06
author: "Ruohang Feng"
description: "A bilingual console: a zero-dependency English/Chinese interface across every screen, the dashboard migrated to MinIO Metrics V3 with explicit zero-state semantics, and a batch of correctness fixes including escape-proof placeholders and a select-all that cannot lie."
tags: [Release, console]
weight: 3
url: "/blog/release/console-2.1.0/"
aliases:
  - /releases/console-2.1.0/
---
**Published:** 2026-08-06 · **Version:** [v2.1.0](https://github.com/pgsty/silo-console/releases/tag/v2.1.0) · **Repository:** [pgsty/silo-console](https://github.com/pgsty/silo-console)

SILO Console 2.1.0 is the first feature release after the independent 2.0.0. It does three things:

1. **Speaks two languages** — every console screen, help topic, and documentation link now renders in English or Chinese, behind a toggle on every page, with zero new runtime dependencies;
2. **Reads the right metrics** — the dashboard moves off the MinIO Metrics V2 names onto V3, with explicit handling for the semantics V3 changed underneath it;
3. **Stops lying in edge cases** — a select-all that matched what a bulk action would delete, placeholders that survive object names containing `$&`, timestamps that carry a timezone, and empty metrics that read "no data" instead of a fabricated `0`.

This is a **minor release**. No environment variable, module path, API contract, binary name, or data layout changes. Upgrading is a binary or image swap.

{{% alert color="info" %}}
**A 2.1.1 patch follows this release**

[v2.1.1](https://github.com/pgsty/silo-console/releases/tag/v2.1.1), published the same day, completes the legend hardening described below: a label placeholder the legend builder cannot resolve is now removed instead of leaking literal braces into the Traffic chart legends, the one remaining substitution branch is escape-proofed against label values containing `$&` or `$1`, and the License page reports the actual release version instead of 2.0.0. Nothing else changes — upgrade straight to 2.1.1, and everything in this note applies unchanged.
{{% /alert %}}

{{% alert color="info" %}}
**Rebuild your embedded assets if you vendor this console**

2.1.0 fixes a packaging defect present on the `main` branch after 2.0.0: the `go:embed` payload still carried the 2.0.0 frontend build, so a binary built from an intermediate commit would serve the old UI. The released 2.1.0 artifacts are built from the regenerated payload and are unaffected.
{{% /alert %}}

## A Bilingual Console {#bilingual-console}

The console is an administration surface for an object store, and a large share of its operators read Chinese first. 2.1.0 makes the interface bilingual without importing an i18n framework — the embedded delivery model means every kilobyte is paid for in the binary. This is [issue #6](https://github.com/pgsty/silo-console/issues/6), which proposed `i18next`; the dependency-free substitution is the one deliberate deviation from it.

### How it works {#i18n-architecture}

The design constraint was: no new dependency, no build step, no extraction pipeline, and partial coverage must never break the page.

- **English source strings are the dictionary keys.** `t("Create Bucket")` looks up the Chinese entry; a missing key returns the English string unchanged. Coverage can therefore grow incrementally, and a typo degrades to English rather than to a raw key like `console.bucket.create`.
- **Three dictionaries, one merge.** `zh.ts` (165 chrome entries), `zhHelp.ts` (247 help-topic entries), and `zhScreens.ts` (1,373 screen entries) merge with chrome taking precedence — about 1,785 entries in total.
- **The language preference mirrors dark mode**: `localStorage` → `systemSlice` → `setLanguage`. There is **no browser-locale detection**; the default is English, and the choice is explicit.
- **Central interception points** rather than per-callsite edits: the page-header wrapper, confirm dialogs, help items, route definitions, and the dashboard's panel renderer each translate on the way out. This is why 220 screen files could be localized without touching their business logic.
- **Module split matters.** `i18n/lang.ts` holds pure primitives (`translate`, `localizeUrl`) and imports no store — `systemSlice` depends on it, so importing the store back would form a cycle. The hooks (`useT`, `useLanguage`, `useLocalizedLink`) and `interpolate()` live in `i18n/index.tsx`.

The toggle is a stroke-drawn 文/A icon mounted in the page header on every page and reused on the login page.

### What it covers {#i18n-coverage}

Login and SSO flows, navigation and the command palette, the dashboard and every metrics panel, buckets and the full object browser (uploads, previews, sharing, versioning, rewind), users/groups/policies/access keys, configuration and event destinations, IDP and KMS, logs, health reports, speedtest, profiling, inspect, trace, watch, and the license page.

Beyond visible strings:

- **Documentation links localize.** `silo.pgsty.com` links gain a `/zh` prefix in Chinese; the Pigsty site swaps domains (`pigsty.io` ↔ `pigsty.cc`). GitHub, MinIO, AWS, and YouTube links are left alone.
- **The help blog feed is per-language**, fetching `/zh/blog/index.xml` in Chinese, with an independent cache per language.
- **The command palette stays searchable in both languages.** Menu entries translate for display but keep their English originals as keywords, so "桶" and "buckets" both match.
- **Chart legends translate only their static prefix.** `translateLegend` preserves instance suffixes like `[server:drive]`, and the data layer keeps raw legends so components that match on them for arithmetic (capacity summing) keep working.
- **Timestamps are unified**, not merely translated — see below.

### What it costs {#i18n-cost}

Roughly **+61 KB** on the embedded payload (2.79 MB → 2.85 MB, +2.2%), **zero new dependencies**, and the dictionaries land in their own lazily-loaded chunk. The English rendering path is byte-stable: with the default language, output is identical to 2.0.0.

### What stays English {#i18n-limits}

Backend error strings (182 of them) are produced by the Go server and are not translatable from the frontend. A handful of strings hardcoded inside the vendored `mds` component library — the collapsed-menu "Sign Out" tooltip, and the data table's "Columns", "Loading…", and ON/OFF toggles — remain English; two of them ("Sign Out", "Actions:") are swapped via a scoped CSS rule, but the rest would require patching the vendor.

## Metrics V3 Migration {#metrics-v3}

The dashboard queried MinIO Metrics **V2** names. SILO deployments scrape **V3** (`/minio/metrics/v3`), so the dashboard depended on an endpoint the monitoring pipeline no longer collected. 2.1.0 rewrites all **26 widgets** onto the V3 catalog — 31 queries over 29 distinct metric names — and drops three widgets (51/61/62) that no layout ever referenced. This is [issue #7](https://github.com/pgsty/silo-console/issues/7); the Info-page half is [#8](https://github.com/pgsty/silo-console/issues/8).

The decision is **V3-only**: no runtime fallback, no probing, no version-selection knob. SILO Console targets SILO deployments, where the server, the scrape pipeline, and the console ship together. The SILO server keeps serving V2 endpoints for external consumers; the console simply stopped using them. A fallback would have been actively harmful — a metrics store retaining 15 days of V2 series would let an `or`-fallback silently read stale data.

### The semantics V3 changed {#v3-semantics}

Three properties of V3 break a naive name-for-name rewrite, and each needed a deliberate answer:

1. **Cluster groups are exported identically by every node.** `/cluster/*` metrics carry no server label and are not leader-gated, so an N-node scrape yields N duplicate series. Queries aggregate with `max()`/`min()` — never `sum()`, which would multiply cluster totals by the node count.
2. **Zero values are not exported at all.** Any metric whose value is ≤ 0 is skipped. Offline drive counts, healing-drive counts, and erasure-set health simply vanish rather than reporting `0`, which a stat card renders as an empty panel. Every affected query carries a companion guard so the panel reads a real `0`.
3. **There is no `minio_heal_*` namespace.** The V2 heal activity signal was in-memory anyway — it reset on restart and bumped on any scan. It is replaced by two cards with defensible semantics: **Erasure Health** (baselined on write quorum) and **Usage Data Age** (how stale the scanner's usage snapshot is).

### Zero-state semantics {#zero-state-semantics}

An adversarial review of the migration produced eight findings, all fixed before release. They share one theme — the difference between *zero*, *no data*, and *not yet scanned*:

- **Capacity** free/used baselines on the always-present total, so a full cluster reads `0 free` instead of vanishing.
- **Online Drives** is guarded against the all-offline case, where the zero-skip would erase the panel exactly when it matters most.
- **Bucket and object counts** guard on the usage group's own freshness gauge, so a cluster that has not completed its first scan reads *no data* rather than a fabricated `0`.
- **Empty single-value results** render as `—`, not `0`.
- **An empty size distribution** no longer fabricates seven zero-height bins.
- **Fractional rates stay visible** (`parseFloat` axis domain, two-decimal CPU formatter) instead of collapsing to `0`.
- **Sub-second Usage Data Age** clamps to "1 second" instead of rendering blank.

A regression suite (`api/admin_info_metrics_test.go`) now pins every widget query to the V3 catalog, asserts widget-ID uniqueness, and enforces the per-widget guard taxonomy: health and traffic widgets need a nodes-online companion, usage counts need the usage-group freshness companion, and capacity needs the total baseline. The full mapping is documented in [`docs/metrics-v3.md`](https://github.com/pgsty/silo-console/blob/main/docs/metrics-v3.md).

### Also fixed {#metrics-other-fixes}

- Widget 17 queried `sent_bytes` twice and widget 11 queried `syscall_read` twice — both internode/syscall pairs were transposed into duplicates.
- Label-less matrices (the result of `max()` aggregation) serialize with **no** `metric` field at all, which crashed the frontend's label extraction and produced a `0 B` capacity donut and an empty usage-growth chart. Guarded.
- An unused per-widget Prometheus label-values prefetch stalled every widget request by up to a second. Deleted.
- The dashboard's usage cards, chart controls, and dense Traffic/Resources panels were rebuilt on one grammar and now reflow through tablet widths.

Two **server-side** bugs were identified during this work and are tracked upstream rather than worked around here: `minio_cluster_usage_buckets_since_last_update_seconds` emits nanoseconds (the objects variant is correct), and V3 bucket-level sent/received traffic are transposed.

## Correctness Fixes {#correctness-fixes}

### Placeholders that survive real object names {#escape-proofing}

`String.prototype.replace` interprets `$&`, `$'`, `` $` ``, and `$1` **in the replacement value** as directives. S3 keys legally contain `$`. So an object named `report$&.csv` did not render as itself — it re-injected the matched placeholder text into the output and corrupted the message. All **37** dictionary placeholder substitutions now pass the value through a function replacement, where no such interpretation happens. This was a latent bug in the original English UI, not something i18n introduced; the i18n audit is simply what found it.

### A select-all that means what it shows {#select-all}

The vendored data table renders a plain untranslatable "Select" header whenever `onSelectAll` is absent — which was the case on all seven selectable tables. Worse, the naive fix is wrong: a select-all that replaces the whole selection **drops rows hidden by an active filter**, so the header checkbox and a subsequent bulk action can target different sets. The implementation toggles only the currently visible rows and preserves filter-hidden selections, so the header state can no longer imply a different set than the action would touch.

### Timestamps with a timezone {#timestamps}

Bucket, object, version, rewind, and access-key timestamps rendered as a mix of verbose English forms and — in several places — a 12-hour clock **without AM/PM**, which is simply ambiguous. All of them now render as `yyyy-MM-dd HH:mm[:ss] (ZZZZ)` in both languages.

### A translation runtime that survives live data {#translation-runtime}

`t()` also receives runtime strings: user agents, RSS titles, object names. Two hardening changes followed:

- misses return **unchanged, unconditionally** — the implicit `@context` suffix stripping is gone, because it silently mutated live data that happened to contain `@`;
- dictionary lookups are guarded with `hasOwnProperty`, so a hostile input naming an inherited `Object.prototype` member (`constructor`, `toString`) cannot leak a function into the UI.

### Interaction and accessibility {#interaction-fixes}

- An expired session opening a deep link **bounced through `/login` and back**, accumulating a redirect chain instead of landing on the form once ([#1](https://github.com/pgsty/silo-console/issues/1)).
- Collapsed sidebar buttons carried no accessible name; screen readers announced them as unlabelled ([#4](https://github.com/pgsty/silo-console/issues/4)). Access Key inputs now declare their autocomplete intent instead of letting password managers guess ([#5](https://github.com/pgsty/silo-console/issues/5)).
- Mobile metrics and bucket panels scroll instead of clipping ([#3](https://github.com/pgsty/silo-console/issues/3)).
- The speedtest control row wraps instead of overflowing its card, its duration accepts seconds or minutes, and its size defaults to MiB to match its own unit list.
- Sidebar bucket rows use a virtual row pitch matching the 44px item, so selected and hovered highlights no longer overlap.
- Unit chips render the selected unit's **label** rather than its raw value.

## No SUBNET, No Telemetry {#no-telemetry}

Upstream removed Subnet, Registration, and Call Home; this fork inherited that state but still carried three traces. 2.1.0 removes them:

- the health websocket's `subnetResponse` field never addressed a subnet — it is a sentinel meaning "the report was assembled" — and is now `reportStatus: "ok"`;
- two help topics claimed the health report "uploads automatically to SUBNET" and that inspect output is "transmitted to SILO SUBNET". Neither was true. They now describe what happens: the report is generated on the deployment and downloaded by the browser;
- the unreferenced `CONSOLE_SUBNET_PROXY` constant is deleted.

For the record, 2.1.0's outbound network posture is unchanged and remains: **no analytics, no telemetry, no beacons, no external scripts or fonts**. `silo-console update` is still disabled. The release catalog is contacted only if `SILO_RELEASE_SERVICE_HOST` (or `RELEASE_SERVICE_HOST`) is explicitly set — there is no default. The only automatic outbound request the browser makes is the help panel's blog feed, and only after a user opens the Blog tab.

## Upgrade Guide {#upgrade-guide}

There is nothing to migrate. No environment variable, module path, protocol field, systemd unit, binary name, or data layout changes between 2.0.0 and 2.1.0.

```bash
install -m 0755 silo-console-linux-amd64 /usr/local/bin/silo-console
```

Two things are worth knowing:

- **The dashboard now requires Metrics V3.** If your Prometheus scrapes only the V2 endpoints, dashboard panels will read no-data. Point the scrape at `/minio/metrics/v3`; Pigsty-managed deployments already do.
- **The language default is English**, chosen per browser and stored in `localStorage`. There is no server-side default and no browser-locale detection, so no existing deployment changes appearance on upgrade.

## Verification Scope {#verification-scope}

Before tagging, the full change set was reviewed and the following gates were run against the final tree: `go build`, `go vet`, `golangci-lint` (0 issues), the Go unit suite across all packages, `gofmt`, TypeScript type checking, the frontend production build, Prettier across all sources, dictionary duplicate-key checks, and a debug-leftover scan of the complete diff.

The 29 intermediate commits were restructured into 20 logical ones by pure tree operations, and the rebuilt tip was verified **byte-identical** to the pre-rewrite tree. The embedded payload was rebuilt twice from a clean directory and confirmed byte-identical, which is the property the release pipeline's zero-diff gate depends on. The pre-rewrite history is retained in a backup ref.

The Metrics V3 migration was additionally reviewed adversarially by an independent model, and all eight findings were fixed (see [Zero-state semantics](#zero-state-semantics)); its queries were validated against a live metrics store with real cluster data.

## Known Limitations {#known-limitations}

- The SSO end-to-end suite requires an external OpenLDAP/Dex/MinIO topology and was not run in that environment this cycle; the OIDC code paths are covered by unit tests.
- Backend error strings and several vendored `mds` component strings remain English (see [What stays English](#i18n-limits)).
- Chinese translation covers the console's own surfaces; help-topic bodies are translated, but the documentation pages they link to follow the docs site's own language coverage.
- Two server-side V3 metric bugs (nanosecond bucket-usage age, transposed bucket traffic) are tracked upstream and are not worked around in the console.
- Automatic self-update remains disabled; upgrades are explicit.

## Issues Closed {#issues-closed}

2.1.0 closes every issue filed against 2.0.0. Each carries a comment on the tracker describing the fix, the commits, and the coverage added.

| Issue | Resolution |
| --- | --- |
| [#1](https://github.com/pgsty/silo-console/issues/1) — unauthenticated deep routes recurse `/login` | Absolute, base-path-aware login destination; deep-link and subpath test coverage |
| [#2](https://github.com/pgsty/silo-console/issues/2) — stale Uptime, malformed legends, cramped menus | Uptime derived from real server state, legends resolve on the V3 `name` label, 32 px chart controls, popup width floors |
| [#3](https://github.com/pgsty/silo-console/issues/3) — 390 px viewport clips content | Scrollable metrics tab strip; bucket table with a deliberate mobile column budget |
| [#4](https://github.com/pgsty/silo-console/issues/4) — unnamed collapsed sidebar buttons | Labels visually hidden rather than removed from the accessibility tree; named, keyboard-operable collapse toggle |
| [#5](https://github.com/pgsty/silo-console/issues/5) — Access Key fields lack autocomplete metadata | Field-level `username` / `new-password` tokens in a dedicated autofill section |
| [#6](https://github.com/pgsty/silo-console/issues/6) — English/Chinese localization | Hand-rolled bilingual layer, zero new dependencies, English-as-key fallback |
| [#7](https://github.com/pgsty/silo-console/issues/7) — migrate monitoring queries to Metrics V3 | V3-only; 26 widgets, 31 queries, 29 metric names, guard taxonomy, regression suite |
| [#8](https://github.com/pgsty/silo-console/issues/8) — replace N/A Info metrics | Erasure Health and Usage Data Age, sharing the advanced dashboard's widget results |

Three acceptance criteria are recorded as unmet rather than quietly ticked: `web-app` has no unit-test runner, so the i18n test suite (#6) and the focused `constructLabelNames` test (#2) would require introducing test tooling first, and #6's contributor documentation for adding translation keys is not yet written.

## Related Commits and Links {#related-links}

The complete v2.1.0 change set consists of 20 logical commits. The `v2.1.0` tag additionally carries three later documentation commits that rewrote the repository README; they change no shipped behavior.

- [`8764f5d`](https://github.com/pgsty/silo-console/commit/8764f5de) — fix(web): stop recursive login redirects
- [`437c56c`](https://github.com/pgsty/silo-console/commit/437c56cd) — fix(ui): make the dashboard and bucket list usable on narrow screens
- [`85fc0c6`](https://github.com/pgsty/silo-console/commit/85fc0c61) — fix(a11y): name collapsed sidebar controls and credential fields
- [`e3fed07`](https://github.com/pgsty/silo-console/commit/e3fed077) — fix(metrics): rebuild dashboard cards, chart controls, and layout
- [`fa11576`](https://github.com/pgsty/silo-console/commit/fa115764) — feat(login): polish controls and legal attribution
- [`9fc17c1`](https://github.com/pgsty/silo-console/commit/9fc17c16) — feat(i18n): add hand-rolled EN/ZH core, dictionaries, and language toggle
- [`622c02e`](https://github.com/pgsty/silo-console/commit/622c02e8) — feat(i18n): localize login, navigation, and the help system
- [`6a03719`](https://github.com/pgsty/silo-console/commit/6a03719c) — feat(i18n): localize dashboard and metrics screens
- [`14b1c2d`](https://github.com/pgsty/silo-console/commit/14b1c2de) — feat(i18n): localize bucket and object browser screens
- [`0298062`](https://github.com/pgsty/silo-console/commit/0298062a) — feat(i18n): localize identity, configuration, and event destinations
- [`41094f6`](https://github.com/pgsty/silo-console/commit/41094f65) — feat(i18n): localize observability, admin tools, and shared components
- [`e964992`](https://github.com/pgsty/silo-console/commit/e964992f) — feat(metrics): migrate the dashboard to MinIO Metrics V3
- [`0b2251f`](https://github.com/pgsty/silo-console/commit/0b2251f5) — fix(i18n): harden the translation runtime for live data and chart legends
- [`9b60148`](https://github.com/pgsty/silo-console/commit/9b601489) — fix(console): unify timestamps on a timezone-carrying standard format
- [`bf110ae`](https://github.com/pgsty/silo-console/commit/bf110aea) — fix(console): give selectable tables a visible-rows select-all
- [`5fc8f22`](https://github.com/pgsty/silo-console/commit/5fc8f221) — fix(i18n): escape-proof all placeholder substitutions
- [`fef8fab`](https://github.com/pgsty/silo-console/commit/fef8fabe) — fix(console): polish speedtest, sidebar, and help chrome
- [`c4911e8`](https://github.com/pgsty/silo-console/commit/c4911e88) — chore(console): drop SUBNET remnants from health reporting
- [`1d631c4`](https://github.com/pgsty/silo-console/commit/1d631c47) — docs: record the SILO Console v2.1.0 changelog
- [`912d847`](https://github.com/pgsty/silo-console/commit/912d847b) — build: regenerate optimized embedded web assets

Links:

- [SILO Console source](https://github.com/pgsty/silo-console) · [Releases](https://github.com/pgsty/silo-console/releases)
- [SILO website](https://silo.pgsty.com/) · [Documentation](https://silo.pgsty.com/docs/)
- [Licensing](https://silo.pgsty.com/about/license/) · [Attribution](https://silo.pgsty.com/about/attribution/) · [Trademark](https://silo.pgsty.com/about/trademark/)

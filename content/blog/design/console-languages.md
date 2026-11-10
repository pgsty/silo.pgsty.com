---
title: "Adding Multilingual Support to SILO"
linkTitle: "Console Languages"
date: 2026-11-09
lastmod: 2026-11-10
author: "PGSTY SILO Maintainers"
summary: >
  Why SILO adds ten UI languages, how the registry and maintenance tiers work, and why per-language compression with eager loading balances size, caching and implementation cost.
tags: [Design, Console, Internationalization]
weight: 10
draft: false
url: "/blog/design/console-languages/"
---

[Console PR #83](https://github.com/pgsty/silo-console/pull/83), contributed by Eduardo Andrade Machado, supplies Brazilian Portuguese. [silo#277](https://github.com/pgsty/silo/issues/277), opened by siyahkut, requests Turkish. These contributions led to a configurable ten-language UI.

**Status:** Shipped in [Console 2.7.0](/blog/release/console-2.7.0/) ([`4e91ae506e70`](https://github.com/pgsty/silo-console/commit/4e91ae506e706ccdecb512b1d8b5ab4d9871d505), `pgsty/silo-console:v2.7.0`) and embedded in [SILO Server 20261109](/blog/release/silo-20261109/) (`d998292387cc`). Final pre-release review verified compact labels, RTL input controls, and layout bounds across phone, tablet, and desktop widths.

## Decision {#tldr}

**Ship one precompressed JavaScript asset per translated language, import all dictionaries statically, and cache each content-hashed asset independently.** Splitting files does not require lazy loading. Once the application has loaded, changing language is synchronous and works without another network request.

The nine translation catalogs total **555,105 bytes with `gzip -9`** when split, versus **549,712 bytes** when combined: a difference of **5,393 bytes, about 1%**. Their size is acceptable for this administration console. We accept the initial download for every user, including English users, in exchange for avoiding language-specific loading states, timeout handling, retries and late-response races. Independent files improve cache reuse when only one translation changes.

English remains the default and sole fallback. Chinese is maintained by the core team with complete coverage. Other languages can temporarily fall back to English while being updated. Only UI text is localized; server messages and log payloads remain unchanged. This decision covers the Console, not a multilingual Server, CLI or documentation set.

## Why add languages? {#motivation}

An administration console asks users to understand access policies, retention settings, replication and destructive operations. Familiar language can make those controls easier to understand and makes the product accessible to more operators. Portuguese and Turkish already have concrete community contributions or requests; a common registry lets subsequent languages follow the same path.

The recurring cost is more substantial than adding a menu item. English copy changes need translation updates; storage terminology must stay consistent; longer labels and RTL text affect layout. A translation that reverses the meaning of a retention or deletion warning is worse than a clear English fallback. Complete dictionaries alone do not establish linguistic quality.

The design therefore keeps the scope narrow, distinguishes maintenance commitments, and validates structure automatically. It adds no translation service, model download or external runtime dependency to an installation.

## Decisions {#decisions}

1. Merge #83 before making the maintainer's changes; keep its authorship.
2. Use one shared dropdown language menu and language commands in KBar.
3. Support English, Chinese, French, German, Russian, Spanish, Brazilian Portuguese, Japanese, Arabic and Turkish.
4. Default to English without browser-language detection; preserve explicit preferences.
5. Keep Chinese coverage release-gating and report coverage for other languages.
6. Keep all dictionaries eagerly loaded. Split the generated assets by language and precompress them at build time; use content hashes and long-lived caching.
7. Ship Arabic with RTL layout and LTR isolation for protocol data.
{.steps}

## Previous design {#current-design}

English source strings are dictionary keys. The original Chinese dictionaries were `zh`, `zhHelp` and `zhScreens`; merge precedence was chrome > screens > help. Chinese text was already included in the login and Console bundles for all users.

Keeping source strings as keys makes the fallback readable and avoids rewriting thousands of call sites merely to introduce opaque message IDs. It also means an English wording change is a key migration. Reviewers must update the catalogs deliberately instead of treating copy edits as translation-neutral changes.

The code also contained language-specific branches for number/date formatting, links, spacing and menu behavior. Five quantity displays selected English singular/plural forms, which is insufficient for Russian and Arabic.

## PR #83 {#pr-83}

The contribution contained 2,249 catalog entries and a Portuguese-specific asynchronous loader. It changed the two-language toggle into an English → Chinese → Portuguese cycle. Its translation work was worth accepting, while its selector and loading mechanism needed to become general features rather than Portuguese-specific exceptions. PR #83 was merged first, preserving the contributor's original commits, before the broader registry and UI changes.

The original loader could register successful common dictionaries without notifying mounted components when the screen dictionary failed. The final static implementation removes that failure mode entirely. It also removes `catalogRevision`, startup waits, retry state and the Portuguese-only loader. The contribution's mounted-copy tests remain, adapted to synchronous language selection and offline behavior.

## Size and packaging {#costs}

### Measurement basis {#measurement}

These are production-build measurements from 2026-11-09, based on Console [revision `b0371b6`](https://github.com/pgsty/silo-console/commit/b0371b69cc1eae78eb30342afa8613dfbd78971b), after translation and compact-label review. Future copy changes require fresh measurements. There are ten selectable languages and nine translation catalogs: English uses source keys and needs no duplicate dictionary. KB means 1,000 bytes; MB means 1,000,000 bytes.

The nine production dictionary assets contain **1,863,188 uncompressed bytes** in total. The production pipeline uses pinned `fflate` 0.8.3 with `level: 9` and `mtime: 0`, producing **568,470 bytes**. The optimized embedded GUI totals **2,357,925 bytes**, up **452,217 bytes (23.7%)** from the merged Portuguese PR baseline of **1,905,708 bytes**. These totals describe embedded web resources, not the complete Go executable.

Initial login JavaScript totals **794.08 KB gzip**. Its limits are 850 KB for the initial dependency graph, 630 KB for all language data and 350 KB per chunk. The checker sums all language chunks, requires each one to belong to the initial static dependency graph, and enforces the per-chunk limit as well. Splitting a large asset cannot bypass its budget.

### One file or one file per language? {#packaging}

The comparison keeps the production source, minifier and static imports unchanged. Only the bundler grouping changes: one group for all dictionaries, or one group for each language directory. Each language group includes its chrome, help and screens dictionaries. The resulting JavaScript is compressed separately with the local `gzip -n -9` command and with the existing pinned compressor.

| Packaging                       | `gzip -n -9`, bytes | `fflate` level 9, bytes | Language asset requests on a cold load |
| ------------------------------- | ------------------: | ----------------------: | -------------------------------------: |
| All languages combined          |             549,712 |                 562,448 |                                      1 |
| One asset per language, total   |             555,105 |                 568,470 |                                      9 |
| Additional bytes from splitting |       5,393 (0.98%) |           6,022 (1.07%) |                                      8 |
{.wide .expand}

Compression level is not a guarantee of identical output across implementations. The system command is useful for comparison; the pinned production compressor provides reproducible output across build hosts. The packaging conclusion is the same with both, so changing compressor implementations is not required.

| Language             | `gzip -n -9`, bytes |
| -------------------- | ------------------: |
| Chinese              |              58,319 |
| French               |              60,684 |
| German               |              60,717 |
| Russian              |              70,315 |
| Spanish              |              59,296 |
| Brazilian Portuguese |              57,689 |
| Japanese             |              63,159 |
| Arabic               |              64,095 |
| Turkish              |              60,831 |
{.wide .expand}

Combining files does not eliminate every repeated English key across catalogs. DEFLATE references previous text within a 32 KiB window, while each complete language catalog is much larger. This helps explain why a large cross-language compression gain should not be assumed; the table above measures the actual result. See [RFC 1951, section 2](https://www.rfc-editor.org/rfc/rfc1951#section-2).

### Cache reuse and request cost {#caching}

In a second build, only the Turkish translation of one UI label changed. With separate language files, only the Turkish language asset changed its hash; the other eight kept theirs. With a combined file, the entire language asset changed. If the browser retains valid cached copies, the language data downloaded after that correction is about **63 KB instead of 562 KB** with the production compressor. Entry modules may also change, so this is not a claim about total update traffic. If every language changes together, the reuse advantage largely disappears.

The price is eight extra requests on a cold load. All languages still download and initialize before the application uses them; splitting does not reduce initial bytes, dictionary allocation or JavaScript parsing work. Extra requests can matter on high-latency HTTP/1.1 connections. These measurements establish byte sizes and hash stability, not a measured improvement in load time or memory use.

Independent caching needs an explicit server policy. The earlier combined-asset implementation supplied `Content-Encoding: gzip` and `Vary: Accept-Encoding` but no explicit long-lived `Cache-Control`. The implemented policy adds:

- Existing content-hashed, non-personalized JavaScript and CSS assets: `Cache-Control: public, max-age=31536000, immutable`.
- HTML entry points: `Cache-Control: private, no-cache`, so they revalidate and discover current asset names. Missing asset URLs that fall back to HTML do not inherit the immutable policy; API cache policies stay under their handlers' control.
- Compress assets at build time and serve the existing gzip representation. A `.js.gz` asset is an HTTP-encoded JavaScript file, not an archive the user must unpack.

This follows the [HTTP caching guidance for versioned resources](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching#avoiding_revalidation). A browser check against the actual Go static-resource handler loaded all nine production language files on the first visit and reused all nine from cache on reload. All ten languages could be selected offline without losing unsaved input. The API responses in this asset check were controlled fixtures; it is not a full SILO deployment acceptance run.

### Why keep eager loading? {#eager-tradeoff}

Roughly 0.57 MB of compressed dictionaries is acceptable for the current Console. Loading all catalogs with the application avoids a second failure path during language switching: no partial catalog arrival, loading indicator, startup grace period, retry loop or stale response to coordinate. It also preserves offline switching after the application has loaded. It does not make the Console available offline before its initial load or remove the need for the server for storage operations.

The costs remain real: English users download translations they may never use, and all users parse and retain them. If the language corpus grows substantially, the initial graph exceeds its budget, or measurements on target networks and devices show a problem, revisit selective loading. A smaller byte count alone does not justify introducing that runtime complexity today.

## Design {#design}

### Scope {#scope}

Translate static UI labels, help topics, control accessibility names, date/number formats and chart-legend prefixes. Keep server errors, logs, audit/Trace/health-report data, object names, paths, configuration identifiers, policy JSON and RSS content intact. Documentation remains bilingual: Chinese links for Chinese, English links for other languages.

### Locale registry {#registry}

[`src/i18n/locales.ts`](https://github.com/pgsty/silo-console/blob/b0371b69cc1eae78eb30342afa8613dfbd78971b/web-app/src/i18n/locales.ts) owns `LOCALES` and `CATALOGS`. Metadata records each language's autonym, BCP 47 tag, direction and maintenance tier. `CATALOGS` is typed as `Record<Lang, Dictionary>` so a newly registered language requires a corresponding dictionary mapping.

This is a build-time configuration in source, not an administration setting or a remote language-pack service. Components derive menus, formatting and direction from it instead of adding another chain of language-specific branches. For example:

```ts
tr: { label: "Türkçe", tag: "tr", dir: "ltr", tier: "maintained" },
```

| ID    | Menu label         | Direction | Tier       |
| ----- | ------------------ | --------- | ---------- |
| en    | English            | LTR       | source     |
| zh    | 简体中文           | LTR       | core       |
| fr    | Français           | LTR       | maintained |
| de    | Deutsch            | LTR       | maintained |
| ru    | Русский            | LTR       | maintained |
| es    | Español            | LTR       | maintained |
| pt-BR | Português (Brasil) | LTR       | maintained |
| ja    | 日本語             | LTR       | maintained |
| ar    | العربية            | RTL       | maintained |
| tr    | Türkçe             | LTR       | maintained |
{.wide .expand}

The stored `zh` preference remains valid. The experimental `pt` value maps to `pt-BR`; unknown or disabled values fall back to English. An unfinished language can be excluded from the menu with `enabled: false`; hiding it does not itself remove its static import from the build.

### Catalog layout {#catalogs}

Each language has `chrome.ts`, `help.ts` and `screens.ts` under `src/i18n/locales/<id>/`. These files organize translation work, not loading stages. Literal TypeScript retains translator comments and supports static validation. The established precedence remains chrome > screens > help.

### Loading {#loading}

All three parts are statically imported for every language. The browser loads their JavaScript dependencies during application startup; rendering and later language selection do not wait for a separate locale fetch. There is no language-fetch API, promise cache or startup timer. The shared dropdown popup is also statically imported so the first language-menu interaction works offline after initial application loading. Existing route splitting and heavyweight editor/chart/PDF loading remain independent of language selection.

### Formatting and links {#branches}

Components read formatting tags and site-language metadata from the registry. Whole-sentence templates determine punctuation and spacing. MDS `ControlLabelsProvider` supplies the Actions heading instead of CSS-generated Chinese text.

### Language menu {#menu}

Login, anonymous pages and the Console use the same globe button and dropdown. Autonyms carry their own `lang` and `dir`, the selected language is marked, and keyboard selection returns focus to the trigger. KBar offers the same set of language commands.

A ten-language cycle makes users step through unfamiliar interfaces to find their language. A dropdown makes every language directly selectable and keeps working as the list grows. Autonyms let users recognize their own language even if the current interface is unfamiliar. No country flags are needed to represent languages.

### Plurals {#plurals}

`tn(count, one, other)` uses `Intl.PluralRules`. Multi-form translations live under the English plural key and include all categories used by their language. Missing translations use English plural rules, rather than applying Russian or Arabic rules to English fallback text.

### Typography {#typography}

Chinese and Japanese avoid Latin uppercase letter spacing; Arabic uses normal spacing. System fallback fonts cover non-Latin text without adding font downloads. German headings and controls allow hyphenation.

Compact wording is a UI requirement. Improving accuracy must not restore labels that overflow their existing controls. For example, Spanish `Tiempo activo`, French `Temps actif` and Portuguese `Tempo ativo` preserve the duration meaning of Uptime; `EC` keeps erasure-coding health labels short. Lifecycle expiry labels still identify older object versions. Review these labels in the real metric cards and forms, not just in a dictionary table.

### Right-to-left layout {#rtl}

Logical CSS properties govern spacing, alignment, borders and the mobile drawer. Directional icons, tab-arrow navigation and switch movement follow RTL. Object paths, bucket names, ARN/JSON, policy editors and raw Trace/log data stay LTR. Protocol-field action buttons and unit selectors remain at the text's end in RTL so password, URL, email, and number inputs are not covered ([`a9da731c5`](https://github.com/pgsty/silo-console/commit/a9da731c5)), and the task-count badge stays anchored in its corner ([`bc17e124a`](https://github.com/pgsty/silo-console/commit/bc17e124a)). Charts and physical viewport coordinates are not blindly mirrored.

## Maintenance tiers and checks {#tiers}

Chinese coverage is a hard gate. Other catalogs report missing entries and fall back to English; their temporary gaps do not block unrelated releases. They still require review and correction, and all catalogs must pass structural validation. The reviewed dictionaries cover **2,252 entries per language** across the three parts, or **2,235 distinct keys**. These counts describe key coverage, not linguistic proficiency.

The two translation tiers reflect maintenance ownership. The core team commits to complete Chinese; other languages can evolve through contributions without implying that the team can personally guarantee native-level fluency in all of them. English remains the single fallback, so a missing French string cannot unexpectedly become Chinese.

Malformed placeholders, empty translations, invalid plural categories, duplicate or misplaced keys, invalid locale tags and registry/directory mismatches fail validation. Existing Chinese orphan and duplicate baselines remain historical exceptions and may not be expanded to hide regressions.

## Producing translations {#translations}

New catalogs use AI-assisted drafts followed by terminology, UI-context and destructive-operation review. The glossary covers core storage and access-control terms. Review pays particular attention to negation, permissions, irreversible actions, retention periods, placeholders and protocol identifiers. Complete key coverage is not a claim of native-speaker review, and an AI review does not establish that either. The initial review and subsequent compact-label verification are complete; corrections to long help passages remain welcome.

The contributor README explains `i18n:report`, which exports missing keys with Chinese reference text and source locations, and `i18n:rename`, which migrates reviewed English key changes across catalogs. Translation tooling and services are not build or runtime dependencies.

## Layout checks {#layout-checks}

Real-language browser checks cover login and a dense site-replication form at 350, 768 and 1440 pixels. Additional cases cover keyboard navigation, persisted preferences, all-language offline switching, unsaved form data, RTL drawers/tabs and unchanged raw log/path content.

The same three viewport widths cover actual metric-row components and the bulk lifecycle dialog in every language. Checks reject labels that overlap values, clip field text or cause horizontal overflow, and preserve the compact metric layout. This guards the layout constraint when translations are revised again.

Development-only `en-XA` expands labels by roughly 40%; `ar-XB` exercises RTL. Neither appears in the public menu or production catalog. Catalog checks, type checking, the full frontend unit suite and production bundle limits complement these browser checks.

## Alternatives considered {#alternatives}

| Option                                | Benefit                                                               | Cost and decision                                                                                                             |
| ------------------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Keep only English and Chinese         | Lowest translation maintenance burden                                 | Does not address the Portuguese contribution or Turkish request; reject.                                                      |
| One combined asset, eager loading     | One language request and the smallest gzip total                      | Any language edit invalidates all translation data; a valid simple baseline, but per-language assets cost only about 1% more. |
| One asset per language, eager loading | Independent cache reuse with the existing synchronous runtime         | Eight extra cold requests and the same initial dictionary workload; selected.                                                 |
| One asset per language, lazy loading  | English can avoid all catalogs; other users fetch only what they need | Adds partial-load, failure, retry and state coordination paths; defer until measurements justify it.                          |
| Add a full translation framework      | More advanced message tooling and ecosystem integrations              | Adds a dependency and migration work; current source-key lookup, `Intl` and React/Redux cover the required behavior.          |
{.wide .expand}

Per-language lazy loading was evaluated and removed after the maintainer selected the static tradeoff. Separate gzip files retain a natural boundary for revisiting loading later, without introducing those states now.

## Delivery {#delivery}

PR #83 was merged with its original history. The initial ten-language [implementation](https://github.com/pgsty/silo-console/commit/51a735992) and [embedded GUI](https://github.com/pgsty/silo-console/commit/0059ee2d9) were committed separately. Subsequent commits added [reviewed translations and compact-layout checks](https://github.com/pgsty/silo-console/commit/34de5907eb8d290ddb3e7f43c6bec68f1eb76daa), [per-language assets and cache policy](https://github.com/pgsty/silo-console/commit/b0371b69cc1eae78eb30342afa8613dfbd78971b), and the [intermediate GUI rebuild](https://github.com/pgsty/silo-console/commit/efe12ae972579972327b0d56e085fcfc8ba62923). Pre-release polish restored the task-count badge position ([`bc17e124a`](https://github.com/pgsty/silo-console/commit/bc17e124a)) and kept protocol-field action buttons at the text's end in RTL ([`a9da731c5`](https://github.com/pgsty/silo-console/commit/a9da731c5)), followed by the final [Console 2.7.0 release asset build `4e91ae506e70`](https://github.com/pgsty/silo-console/commit/4e91ae506e706ccdecb512b1d8b5ab4d9871d505) superseding `efe12ae97`.

The released `v2.7.0` source passed all frontend unit tests, Go API tests, type checking, formatting, dead-code checks, and production bundle budgets, and shipped in standalone [Console 2.7.0](/blog/release/console-2.7.0/) (`pgsty/silo-console:v2.7.0`) and embedded in [SILO Server 20261109](/blog/release/silo-20261109/). A correction to a catalog must reach the embedded GUI as well as the TypeScript files.

Acceptance covers missing-key fallback, placeholders and plurals, persisted language preferences, offline switching after initial load, unsaved form values, Arabic layout, unchanged raw data, and cache reuse after changing one language.

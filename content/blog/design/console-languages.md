---
title: "Console Languages: A Static Registry and Two Maintenance Tiers"
linkTitle: "Console Languages"
date: 2026-11-09
lastmod: 2026-11-09
author: "PGSTY SILO Maintainers"
summary: >
  Ten UI languages, a shared language menu, English defaults and fallback, complete first-party Chinese, and Arabic RTL. The measured catalog size is small enough to bundle statically and avoid asynchronous language loading.
tags: [Design, Console, Internationalization]
weight: 10
draft: false
url: "/blog/design/console-languages/"
---

[Console PR #83](https://github.com/pgsty/silo-console/pull/83), contributed by Eduardo Andrade Machado, supplies Brazilian Portuguese. [silo#277](https://github.com/pgsty/silo/issues/277), opened by siyahkut, requests Turkish. These contributions led to a configurable ten-language UI.

**Status:** merged to Console `main` on 2026-11-09. PR #83 was merged first, preserving the contributor's original commits. The [implementation](https://github.com/pgsty/silo-console/commit/51a735992) and [embedded GUI](https://github.com/pgsty/silo-console/commit/0059ee2d9) were committed separately. Source integration is separate from a product release.

## Decision {#tldr}

Bundle all UI dictionaries statically. A combined measurement of the nine translated catalogs is approximately **554 KiB gzip**, with individual languages around 60–70 KiB. This is acceptable for an administration console and removes language-download failures, loading indicators, startup timeouts, retries and late-response state. The price is a larger first download for every user, including English users. The dictionaries reside in a separately cacheable static asset.

English remains the default and sole fallback. Chinese is maintained by the core team with complete coverage. Other languages can temporarily fall back to English while being updated. Only UI text is localized; server messages and log payloads remain unchanged.

## Decisions {#decisions}

1. Merge #83 before making the maintainer's changes; keep its authorship.
2. Use one shared dropdown language menu and language commands in KBar.
3. Support English, Chinese, French, German, Russian, Spanish, Brazilian Portuguese, Japanese, Arabic and Turkish.
4. Default to English without browser-language detection; preserve explicit preferences.
5. Keep Chinese coverage release-gating and report coverage for other languages.
6. Use static dictionaries. The earlier proposal for per-language lazy loading was superseded after measuring the payload.
7. Ship Arabic with RTL layout and LTR isolation for protocol data.

## Previous design {#current-design}

English source strings are dictionary keys. The original Chinese dictionaries were `zh`, `zhHelp` and `zhScreens`; merge precedence was chrome > screens > help. Chinese text was already included in the login and Console bundles for all users.

The code also contained language-specific branches for number/date formatting, links, spacing and menu behavior. Five quantity displays selected English singular/plural forms, which is insufficient for Russian and Arabic.

## PR #83 {#pr-83}

The contribution contained 2,249 catalog entries and a Portuguese-specific asynchronous loader. It changed the two-language toggle into an English → Chinese → Portuguese cycle. The maintainer added compatibility with TestCafe's TypeScript compiler and rebuilt the embedded GUI before merging the PR.

The original loader could register successful common dictionaries without notifying mounted components when the screen dictionary failed. The final static implementation removes that failure mode entirely. It also removes `catalogRevision`, startup waits, retry state and the Portuguese-only loader. The contribution's mounted-copy tests remain, adapted to synchronous language selection and offline behavior.

## Costs {#costs}

The production dictionary asset, excluding application code, contains **1,878,674 raw bytes** and **567,087 gzip bytes** for nine non-English languages. English uses source keys and needs no duplicate dictionary. Turkish measured separately is **63,421 gzip bytes**.

The optimized embedded GUI totals **2,352,016 bytes**, up **446,308 bytes (23.4%)** from the merged Portuguese PR. Initial login JavaScript totals **792.47 KB gzip**. The explicit limits are 850 KB for the initial graph, 630 KB for language data and the existing 350 KB limit for other chunks.

| Cost | Consequence |
| --- | --- |
| Initial download | All users download roughly 0.57 MB of compressed dictionaries, then use the cache. |
| Embedded server assets | Language data adds less than 1 MB; it does not add fonts, translation models or runtime services. |
| Switching language | Synchronous; no network request and no loss of unsaved form values. |
| Maintenance | English key changes can invalidate translations; terminology and destructive-operation explanations need review. |

The tradeoff is intentional. A smaller first download would justify asynchronous loading in a different product or at a substantially larger language count. For this console, a simple static mapping is easier to maintain.

## Design {#design}

### Scope {#scope}

Translate static UI labels, help topics, control accessibility names, date/number formats and chart-legend prefixes. Keep server errors, logs, audit/Trace/health-report data, object names, paths, configuration identifiers, policy JSON and RSS content intact. Documentation remains bilingual: Chinese links for Chinese, English links for other languages.

### Locale registry {#registry}

`src/i18n/locales.ts` owns `LOCALES` and `CATALOGS`. Metadata records each language's autonym, BCP 47 tag, direction and maintenance tier. `CATALOGS` is typed as `Record<Lang, Dictionary>` so a newly registered language requires a corresponding dictionary mapping.

| ID | Menu label | Direction | Tier |
| --- | --- | --- | --- |
| en | English | LTR | source |
| zh | 简体中文 | LTR | core |
| fr | Français | LTR | maintained |
| de | Deutsch | LTR | maintained |
| ru | Русский | LTR | maintained |
| es | Español | LTR | maintained |
| pt-BR | Português (Brasil) | LTR | maintained |
| ja | 日本語 | LTR | maintained |
| ar | العربية | RTL | maintained |
| tr | Türkçe | LTR | maintained |

The stored `zh` preference remains valid. The experimental `pt` value maps to `pt-BR`; unknown or disabled values fall back to English. An unfinished language can be excluded from the menu with `enabled: false`.

### Catalog layout {#catalogs}

Each language has `chrome.ts`, `help.ts` and `screens.ts` under `src/i18n/locales/<id>/`. These files organize translation work, not loading stages. Literal TypeScript retains translator comments and supports static validation. The established precedence remains chrome > screens > help.

### Loading {#loading}

All three parts are imported synchronously. There is no language-fetch API, promise cache or startup timer. The shared dropdown popup is also statically imported so the first language-menu interaction works offline. Existing route splitting and heavyweight editor/chart/PDF loading remain independent of language selection.

### Formatting and links {#branches}

Components read formatting tags and site-language metadata from the registry. Whole-sentence templates determine punctuation and spacing. MDS `ControlLabelsProvider` supplies the Actions heading instead of CSS-generated Chinese text.

### Language menu {#menu}

Login, anonymous pages and the Console use the same globe button and dropdown. Autonyms carry their own `lang` and `dir`, the selected language is marked, and keyboard selection returns focus to the trigger. KBar offers the same set of language commands.

### Plurals {#plurals}

`tn(count, one, other)` uses `Intl.PluralRules`. Multi-form translations live under the English plural key and include all categories used by their language. Missing translations use English plural rules, rather than applying Russian or Arabic rules to English fallback text.

### Typography {#typography}

Chinese and Japanese avoid Latin uppercase letter spacing; Arabic uses normal spacing. System fallback fonts cover non-Latin text without adding font downloads. German headings and controls allow hyphenation.

### Right-to-left layout {#rtl}

Logical CSS properties govern spacing, alignment, borders and the mobile drawer. Directional icons, tab-arrow navigation and switch movement follow RTL. Object paths, bucket names, ARN/JSON, policy editors and raw Trace/log data stay LTR. Charts and physical viewport coordinates are not blindly mirrored.

## Maintenance tiers and checks {#tiers}

Chinese coverage is a hard gate. Other catalogs report missing entries and fall back to English; the release workflow should fill missing copy and record coverage. The initial dictionaries cover **2,252 entries per language** across the three parts, or **2,235 distinct keys**.

Malformed placeholders, empty translations, invalid plural categories, duplicate or misplaced keys, invalid locale tags and registry/directory mismatches fail validation. Existing Chinese orphan and duplicate baselines remain historical exceptions and may not be expanded to hide regressions.

## Producing translations {#translations}

New catalogs use AI-assisted drafts followed by terminology, UI-context and destructive-operation review. The glossary covers core storage and access-control terms. Complete key coverage is not a claim of native-speaker review; corrections to long help passages are welcome.

The contributor README explains `i18n:report`, which exports missing keys with Chinese reference text and source locations, and `i18n:rename`, which migrates reviewed English key changes across catalogs. Translation tooling and services are not build or runtime dependencies.

## Layout checks {#layout-checks}

Real-language browser checks cover login and a dense site-replication form at 350, 768 and 1440 pixels. Additional cases cover keyboard navigation, persisted preferences, all-language offline switching, unsaved form data, RTL drawers/tabs and unchanged raw log/path content.

Development-only `en-XA` expands labels by roughly 40%; `ar-XB` exercises RTL. Neither appears in the public menu or production catalog. Catalog checks, type checking, the full frontend unit suite and production bundle limits complement these browser checks.

## Alternatives considered {#alternatives}

Per-language lazy loading would reduce initial transfer but introduce states for delayed or failed downloads. It was implemented during evaluation and removed after the maintainer selected the simpler static tradeoff. A translation framework is also unnecessary: source-key lookup, `Intl` and React/Redux already cover the required behavior.

## Delivery {#delivery}

1. Merge #83 with its original contributor history.
2. Commit the registry, static dictionaries, Turkish support, menu, formatting, RTL and regression checks directly on the updated main line.
3. Rebuild embedded GUI resources in a separate commit after source verification.
4. Maintain this bilingual design record separately from Console source. A source commit, generated-asset commit, documentation publication and product release are distinct deliverables.

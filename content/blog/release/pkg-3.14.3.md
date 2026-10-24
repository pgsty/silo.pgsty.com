---
title: "silo-pkg 3.14.3 Released"
linkTitle: "silo-pkg 3.14.3"
date: 2026-10-18T07:29:13+08:00
author: "Vonng"
description: "Faster admin-action classification during policy evaluation with unchanged authorization behavior."
tags: [Release, pkg]
weight: 1
url: "/blog/release/pkg-3.14.3/"
---

**Release:** [v3.14.3](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.3) · **Source:** [`e9d585ba1e7a`](https://github.com/pgsty/silo-pkg/commit/e9d585ba1e7a30ee5eb85b992d883820b83768f5). See the [v3.14.2 release notes](/blog/release/pkg-3.14.2/) for the October dependency baseline.

`github.com/pgsty/silo-pkg/v3 v3.14.3` reduces the cost of classifying `admin:` actions during IAM policy evaluation and is selected by [Server 20261018](/blog/release/silo-20261018/).

`AdminAction.IsValid` and `HasResource` now perform exact map lookups before scanning the action sets: literal misses return immediately, and wildcard patterns whose prefix cannot match the `admin:` namespace skip the validation scan, while patterns such as `adm*` and `a*d*m*i*n*` retain their exact existing behavior.

## Performance and validation {#validation}

Across six alternating single-CPU benchmark runs on an Apple M5 Max (Go 1.27.2), median evaluation time for a policy with 100 non-matching bucket grants followed by a matching grant dropped from **303.2 µs to 54.4 µs** (**~82% reduction**) with zero additional heap allocations.

Validation covered Go 1.26 and 1.27 race suites, lint, LDAP integration, vulnerability scanning, 60 seconds of equivalence fuzzing, and an exhaustive comparison across 50,000 policies and 970,020 policy evaluations against v3.14.2; `mcli 20261018` also produced identical results against server builds using v3.14.2 and v3.14.3.

## Adoption {#adoption}

Public APIs, policy formats, authorization decisions, dependencies, and the `go 1.26` floor are unchanged. Server 20261018 adopts `v3.14.3`, while standalone `mcli 20261018` and `Console v2.4.2` remain on `v3.14.2` (see the [component matrix](/compatibility/versions/)).

Thanks to [Denis Babchuk (@botdeniska)](https://github.com/botdeniska) for [PR #11](https://github.com/pgsty/silo-pkg/pull/11), and [Klaus Post (@klauspost)](https://github.com/klauspost) for the original optimization.

[Changes since v3.14.2](https://github.com/pgsty/silo-pkg/compare/v3.14.2...v3.14.3)

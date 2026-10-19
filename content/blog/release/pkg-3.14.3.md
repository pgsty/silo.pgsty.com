---
title: "silo-pkg 3.14.3 Released"
linkTitle: "silo-pkg 3.14.3"
date: 2026-10-18T07:29:13+08:00
author: "Vonng"
description: "Faster policy evaluation with unchanged authorization behavior."
tags: [Release, pkg]
weight: 1
url: "/blog/release/pkg-3.14.3/"
---

**Source:** [`e9d585ba1e7a`](https://github.com/pgsty/silo-pkg/commit/e9d585ba1e7a30ee5eb85b992d883820b83768f5). See [v3.14.2 release notes](/blog/release/pkg-3.14.2/) for the dependency baseline.

[silo-pkg v3.14.3](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.3)
reduces the cost of classifying admin actions during policy evaluation.
It is a source-only release of `github.com/pgsty/silo-pkg/v3`.

`AdminAction.IsValid` and `HasResource` now try exact lookups before scanning
the action sets. Literal misses return immediately, and wildcard patterns
that cannot match the `admin:` namespace skip the validation scan. Patterns
such as `adm*` and `a*d*m*i*n*` retain their existing behavior.

## Performance and validation {#validation}

On an Apple M5 Max with Go 1.27.2, six alternating single-CPU benchmark runs
reduced median evaluation time for 100 nonmatching bucket grants followed by
a matching grant from **303.2 microseconds to 54.4 microseconds**, about
**82% less time**, with no additional allocations. This measures policy
evaluation, not end-to-end S3 throughput.

Validation included Go 1.26 and 1.27 race tests, lint, LDAP integration,
vulnerability scanning, 60 seconds of equivalence fuzzing, and an independent
comparison of 50,000 policies and 970,020 policy evaluations against v3.14.2.
The published mcli also produced the same results against server builds using
the old and new package.

## Adoption {#adoption}

Public APIs, policy formats, authorization decisions, dependencies, and the
Go 1.26 library floor are unchanged. Applications must update their dependency
and rebuild to use the optimization. A server can adopt v3.14.3 while the
published mcli 20261018 and standalone Console v2.4.2 continue using v3.14.2;
this patch does not require simultaneous component releases.

Publishing this module does not update the existing Server draft or installed
binaries. See the [component matrix](/compatibility/versions/) for their
selected dependencies.

Thanks to [Denis Babchuk (@botdeniska)](https://github.com/botdeniska) for
[PR #11](https://github.com/pgsty/silo-pkg/pull/11), and
[Klaus Post (@klauspost)](https://github.com/klauspost) for the original work.

[Changes since v3.14.2](https://github.com/pgsty/silo-pkg/compare/v3.14.2...v3.14.3)

---
title: "mc support"
url: "/reference/minio-mc/mc-support/"
weight: 380
icon: fa-solid fa-life-ring
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support.rst
upstream_modified: true
---

<a id="mc-support"></a>
<a id="command-mc.support"></a>

## Local diagnostics {#description}

`mcli support` retains SILO diagnostics without a MinIO SUBNET subscription.
Administrators control generated files and deliberate sharing.

## Subcommands {#subcommands}

| Command | SILO behavior |
| --- | --- |
| `diag` | Generate a local health report |
| `perf` | Run performance tests with local results |
| `profile` | Server profiling and local output |
| `inspect` | Inspect object metadata |
| `top` | Observe live server activity |
| `callhome enable` | Disabled, exit 1; disable/status remain |
| `proxy set` | Disabled, exit 1; remove remains |
| `upload` | Disabled, exit 1 |

Use `mcli support COMMAND --help` for flags. Diagnostics still require the
corresponding administrative permissions on the target SILO server.
See [diag](/reference/minio-mc/mc-support-diag/),
[perf](/reference/minio-mc/mc-support-perf/),
[profile](/reference/minio-mc/mc-support-profile/),
[inspect](/reference/minio-mc/mc-support-inspect/) and
[mcli compatibility](/compatibility/mcli/#subnet).

---
title: "mc support proxy"
url: "/reference/minio-mc/mc-support-proxy/"
weight: 60
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-proxy.rst
upstream_modified: true
---

<a id="mc-support-proxy"></a>
<a id="command-mc.support.proxy"></a>
<a id="examples"></a>
<a id="set-a-proxy-url"></a>
<a id="remove-the-proxy-url-configured-for-a-deployment"></a>
<a id="disable-callhome-logs"></a>
<a id="mc.support.proxy.set"></a>
<a id="mc.support.proxy.show"></a>
<a id="mc.support.proxy.remove"></a>
<a id="global-flags"></a>

## Current behavior {#description}

PGSTY mcli retains the legacy syntax of `support proxy set` for compatibility, but
MinIO SUBNET services are disabled at build time. The command reports the
explicit disabled-service error and exits **1**, without registration or uploads.
Upstream subscription/API-key instructions do not apply.
`mcli support proxy remove ALIAS` still clears legacy proxy settings.

## Syntax {#syntax}

Inspect the compatibility flags accepted by your installed version:

```shell
mcli support proxy --help
```

`mcli support diag`, `perf`, `profile` and `inspect` still run locally without
SUBNET registration. Administrators control storage and any deliberate sharing
of the results. See [mcli compatibility](/compatibility/mcli/#subnet).

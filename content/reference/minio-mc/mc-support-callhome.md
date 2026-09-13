---
title: "mc support callhome"
url: "/reference/minio-mc/mc-support-callhome/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-callhome.rst
upstream_modified: true
---

<a id="mc-support-callhome"></a>
<a id="command-mc.support.logs.disable"></a>
<a id="command-mc.support.logs.enable"></a>
<a id="command-mc.support.logs.status"></a>
<a id="command-mc.support.callhome"></a>
<a id="mc.support.callhome.enable"></a>
<a id="mc.support.callhome.disable"></a>
<a id="mc.support.callhome.status"></a>
<a id="parameters"></a>
<a id="mc.support.callhome.ALIAS"></a>
<a id="mc.support.callhome.-diag"></a>
<a id="examples"></a>
<a id="enable-callhome-reporting"></a>
<a id="disable-callhome-reporting"></a>
<a id="display-current-callhome-settings"></a>
<a id="global-flags"></a>

## Current behavior {#description}

PGSTY mcli retains the legacy syntax of `support callhome enable` for compatibility, but
MinIO SUBNET services are disabled at build time. The command reports the
explicit disabled-service error and exits **1**, without registration or uploads.
Upstream subscription/API-key instructions do not apply.
`mcli support callhome disable ALIAS` and `status ALIAS` remain available.

## Syntax {#syntax}

Inspect the compatibility flags accepted by your installed version:

```shell
mcli support callhome --help
```

`mcli support diag`, `perf`, `profile` and `inspect` still run locally without
SUBNET registration. Administrators control storage and any deliberate sharing
of the results. See [mcli compatibility](/compatibility/mcli/#subnet).

---
title: "mc license register"
url: "/reference/minio-mc/mc-license-register/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-license-register.rst
upstream_modified: true
---

<a id="mc-license-register"></a>
<a id="command-mc.support.register"></a>
<a id="command-mc.license.register"></a>
<a id="parameters"></a>
<a id="mc.license.register.ALIAS"></a>
<a id="mc.license.register.-airgap"></a>
<a id="mc.license.register.-api-key"></a>
<a id="mc.license.register.-license"></a>
<a id="mc.license.register.-name"></a>
<a id="examples"></a>
<a id="register-a-deployment-using-the-deployment-s-name"></a>
<a id="register-a-deployment-using-the-account-s-license-file"></a>
<a id="register-a-deployment-with-a-different-deployment-name"></a>
<a id="minio-license-register-airgap"></a>
<a id="register-a-deployment-without-direct-internet-access"></a>
<a id="global-flags"></a>
<a id="behavior"></a>
<a id="automatic-license-updates"></a>

## Current behavior {#description}

PGSTY mcli retains the legacy syntax of `license register` for compatibility, but
MinIO SUBNET services are disabled at build time. The command reports the
explicit disabled-service error and exits **1**, without registration or uploads.
Upstream subscription/API-key instructions do not apply.


## Syntax {#syntax}

Inspect the compatibility flags accepted by your installed version:

```shell
mcli license register --help
```

`mcli support diag`, `perf`, `profile` and `inspect` still run locally without
SUBNET registration. Administrators control storage and any deliberate sharing
of the results. See [mcli compatibility](/compatibility/mcli/#subnet).

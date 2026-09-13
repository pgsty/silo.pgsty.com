---
title: "mc support upload"
url: "/reference/minio-mc/mc-support-upload/"
weight: 80
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-upload.rst
upstream_modified: true
---

<a id="mc-support-upload"></a>
<a id="command-mc.support.upload"></a>
<a id="parameters"></a>
<a id="mc.support.upload.ALIAS"></a>
<a id="mc.support.upload.FILE"></a>
<a id="mc.support.upload.-comment"></a>
<a id="mc.support.upload.-enc"></a>
<a id="mc.support.upload.-issue"></a>
<a id="global-flags"></a>
<a id="examples"></a>
<a id="upload-a-file-to-an-issue"></a>
<a id="upload-a-file-to-an-issue-with-a-comment-for-minio-engineers"></a>

## Current behavior {#description}

PGSTY mcli retains the legacy syntax of `support upload` for compatibility, but
MinIO SUBNET services are disabled at build time. The command reports the
explicit disabled-service error and exits **1**, without registration or uploads.
Upstream subscription/API-key instructions do not apply.


## Syntax {#syntax}

Inspect the compatibility flags accepted by your installed version:

```shell
mcli support upload --help
```

`mcli support diag`, `perf`, `profile` and `inspect` still run locally without
SUBNET registration. Administrators control storage and any deliberate sharing
of the results. See [mcli compatibility](/compatibility/mcli/#subnet).

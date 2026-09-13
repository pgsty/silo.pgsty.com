---
title: "mc support diag"
url: "/reference/minio-mc/mc-support-diag/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-diag.rst
upstream_modified: true
---

<a id="mc-support-diag"></a>
<a id="command-mc.support.diag"></a>
<a id="sample-output"></a>
<a id="generate-health-data-for-a-cluster-and-automatically-upload-to-subnet"></a>
<a id="minio-support-diagnostics-airgap"></a>
<a id="generate-health-data-for-a-cluster-to-upload-manually"></a>
<a id="upload-data-to-subnet-with-strict-anonymization"></a>
<a id="parameters"></a>
<a id="mc.support.diag.ALIAS"></a>
<a id="mc.support.diag.-airgap"></a>
<a id="mc.support.diag.-anonymize"></a>
<a id="mc.support.diag.-api-key"></a>
<a id="global-flags"></a>

## Health diagnostics {#description}

`mcli support diag ALIAS` generates a SILO health report and saves it locally.
It does not require SUBNET registration or upload automatically. `--airgap`
remains a compatibility flag; this build always uses local mode. Reports may
contain environment details, so inspect them before sharing.

## Syntax {#syntax}

```shell
mcli support diag mysilo
mcli support diag mysilo --anonymize=strict
```

`ALIAS` is the target configured with `mcli alias set`. `--anonymize` controls
report anonymization: default `standard` retains hostnames; `strict` includes
hostnames in anonymization. `--api-key` retains compatibility syntax and cannot
enable the disabled SUBNET upload path.

## Local reports {#examples}

The command prints the saved report path. Keep and inspect the compressed file,
then share it through your own support process if needed. `support callhome
enable` and `support upload` are disabled and cannot send it to MinIO.
Published mcli writes support artifacts with private file permissions; see
[mcli compatibility](/compatibility/mcli/#subnet).

Use `mcli support diag --help` for the installed version's full flag list.

---
title: "SUBNET"
url: "/administration/console/subnet-registration/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/53e14984e3cacacd5a0206822693f15442186bb8/source/administration/console/subnet-registration.rst
upstream_modified: true
---

<a id="subnet"></a>
<a id="minio-console-subscription"></a>

## SILO licensing and support {#license}

SILO Console retains the AGPL license, corresponding-source and third-party
attribution pages. It does not provide MinIO commercial subscription signup,
purchasing or online renewal, and does not upload diagnostics to SUBNET.
This URL remains for old documentation links; upstream subscription instructions
do not apply to SILO.

## Health {#health}

The Health page generates a deployment report for download and your own
diagnostics. Reports may contain hostnames and environment details; inspect them
before deliberately sharing. SILO does not upload them automatically.

## Performance {#performance}

Performance tools exercise paths such as S3 GET/PUT. Run them in an appropriate
test environment and interpret results against your actual workload.

## Profile {#profile}

The Profile page retains server profiling and local downloads without a SUBNET
subscription requirement.

## Inspect {#inspect}

Inspect gathers erasure-coded object metadata for administrator-controlled
storage and analysis with your own diagnostic tools.

## Call Home {#call-home}

SILO does not send periodic health reports or logs to MinIO. Compatibility
commands remain, but `mcli support callhome enable` returns a disabled-service
error; disable/status can inspect or clear legacy settings.

See [mcli compatibility](/compatibility/mcli/#subnet), [licensing](/about/license/)
and [component versions](/compatibility/versions/).

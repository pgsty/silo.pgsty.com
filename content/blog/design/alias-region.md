---
title: "Alias regions: a small configuration change with compatibility boundaries"
linkTitle: "Alias regions"
date: 2026-10-23
lastmod: 2026-11-09
author: "Ruohang Feng"
summary: "Why mcli needs an optional region per alias, why the resolved region belongs in the client cache key, and how to preserve ordinary upgrades without promising lossless downgrades."
tags: [Design, mcli, S3, Compatibility]
weight: 8
draft: false
url: "/blog/design/alias-region/"
---

**Decision, 2026-10-23:** [mcli PR #44](https://github.com/pgsty/mc/pull/44)
is merged on `main` at
[`91006a587`](https://github.com/pgsty/mc/commit/91006a5879d34422725d7f6aab9640319be88c94).
We accepted the per-alias region design, kept its small production implementation
and supplemented the regression coverage. This records the original design decision. The capability is included in
the published [mcli 20261109](/blog/release/mcli-20261109/); the configuration
boundaries below have been checked against that release source.

The original patch and tests came from
[mr javad seydi](https://github.com/mrjavadseydi). The change addresses the
configuration gap reported in [upstream issue #5268](https://github.com/minio/mc/issues/5268).

## The missing capability {#problem}

The issue describes an internal S3 service that returns `501 Not Implemented`
for `GetBucketLocation`. Before a normal object request, the SDK tries to find
the bucket's region. Discovery fails, so the object request never runs. Adding
`"region": "us-west-1"` to the alias JSON did not help: the old configuration
structure had no such field and silently ignored it.

There was already a workaround. `MC_REGION` and `AWS_REGION` set the SDK's
region and skip discovery. For one endpoint, an environment variable is enough:

```shell
MC_REGION=us-west-1 mcli cp example.txt archive/bucket/example.txt
```

The gap is persistent configuration **per alias**. A process-wide override
cannot express two aliases with different regions in the same command, and it
does not travel with an exported alias. The proposed field fills that gap.
This is an additional configuration capability, rather than a regression in a
previously supported alias option. SILO itself implements `GetBucketLocation`;
the reported failure does not indicate a missing SILO server API.

## The smallest complete path {#implementation}

The [original production patch](https://github.com/pgsty/mc/commit/7d154ca1aa5c9becabd670e486077d36359b093e)
adds 13 lines and removes two across four files:

| Layer | Change | Why it is needed |
| --- | --- | --- |
| Alias JSON | Add optional `region` to `aliasConfigV10` | Read, save and export the value |
| Client configuration | Add `Config.Region` | Carry the value through the existing client interface |
| Alias conversion | Copy the alias field in `NewS3Config` | Connect stored configuration to client construction |
| S3 factory | Resolve the region for the SDK and cache key | Use the value and prevent reuse of a client fixed to another region |
{.wide .expand}

The precedence is:

```text
MC_REGION > AWS_REGION > alias.region > SDK automatic discovery
```

The first non-empty value wins. Missing or empty alias regions keep the existing
discovery path; JSON `null` is also accepted as an empty value. Existing
environment overrides retain their priority. A same-name `MC_HOST_<alias>`
environment alias still replaces the whole file alias, so it does not inherit
the file's region.

The cache change is part of correctness. Two aliases can have the same endpoint
and credentials but different regions. If the cache only recognizes the old
identity, the second alias reuses the first alias's fixed SDK region. Including
the **resolved** region prevents that reuse. When an environment override makes
both effective regions equal, the clients can still be shared. One resolver
serves the SDK and cache so their precedence cannot drift apart.

The SDK already supports an explicit region. Wiring that option through the
existing configuration is enough; no SDK fork, provider-specific `501` fallback,
new dependency or configuration-version migration is needed. Silently guessing
a region after a discovery error would conceal configuration mistakes and make
signing behavior harder to explain.

## A fixed region is a choice {#fixed-region}

A non-empty region fixes the SDK's region. It skips bucket discovery and can
bypass the SDK's region-correction retry path. It is not a suggestion to try
before discovering the real region. That is the same strong override already
provided by the two environment variables. See the SDK's
[explicit-region path](https://github.com/minio/minio-go/blob/320af050c445/bucket-cache.go)
and [region-correction condition](https://github.com/minio/minio-go/blob/320af050c445/api.go).

This distinction matters when one alias reaches buckets in several regions.
Leave the region unset for normal discovery, or create an alias for each region.
When an endpoint or its region changes, update a fixed alias accordingly. A
wrong region can also affect generated signatures: `share upload` can generate
a POST form that fails when used, whereas `share download` first performs a
Stat and can fail earlier.

## What can change on upgrade? {#compatibility}

The patch does not populate old aliases with a new default. Configurations
written by the old CLI normally have no region field, so ordinary upgrades
retain their discovery and environment-override behavior. The exceptions need
more precise treatment than a blanket claim of forward compatibility.

| Situation | Consequence |
| --- | --- |
| An old alias has no `region` | Existing region selection continues |
| A template or earlier experiment left a non-empty `region` in old JSON | A previously ignored field becomes active; an incorrect or stale value can break access |
| An old unknown `region` contains a number, boolean, object or array | The new string field rejects it; parsing the whole configuration fails, including for commands targeting another alias |
| The tested pre-change client reads a new configuration | It accepts the JSON but ignores the region and resumes its old selection behavior |
| That old client changes any alias and saves the configuration | It rewrites the whole file and drops the unknown region from every alias |
{.wide .expand}

The last case is easy to miss. Reading a new configuration with an old binary
does not itself erase the file. Saving it does, even when the user only changed
an unrelated alias. Upgrading again cannot recover the lost fields. Back up the
configuration before downgrade and use separate configuration directories when
old and new clients must coexist. This is backward compatibility for ordinary
old configurations, with readable but semantically incomplete and lossy
downgrades for the tested predecessor.

The more plausible upgrade surprise is a generated template that has always
written a default region, or a forgotten manual experiment. A non-string value
is a narrower malformed-input case. Neither risk justifies silently ignoring
the new field, but both are reasons to inspect existing custom JSON.

## Configure and maintain the alias {#usage}

With a client containing this change, save the following as `archive.json`,
substituting the endpoint, credentials and actual region:

```json
{
  "url": "https://s3.example.com",
  "accessKey": "REPLACE_WITH_ACCESS_KEY",
  "secretKey": "REPLACE_WITH_SECRET_KEY",
  "api": "S3v4",
  "path": "auto",
  "region": "us-west-1"
}
```

```shell
chmod 600 archive.json
mcli alias import archive archive.json
mcli stat archive/existing-bucket
```

The import document is one alias object, not the complete version-10 config.
[Import](/reference/minio-mc/mc-alias-import/) replaces the target alias, so
include the full intended configuration when rotating credentials. Importing an
object without `region` clears an existing region. The
[export command](/reference/minio-mc/mc-alias-export/) preserves the field and
can be used to inspect it; its output also includes credentials.

`alias set` has no `--region` flag. It rebuilds the alias and clears the field;
its connection probe also does not inherit the saved region. Credential-rotation
scripts that use `alias set` therefore need attention after enabling this
feature. `alias list`, including JSON output, does not display the region.
These are explicit management limits of the initial change. Adding CLI support
can be a separate improvement without expanding this patch's production scope.

Bucket creation has a separate setting. `mb --region` retains its own default
of `us-east-1`; an alias region does not replace it. For example, use
`mcli mb --region us-west-1 archive/new-bucket` when that is the intended creation
region. Fixed client configuration and the bucket's creation location must agree.

## Regression coverage and tradeoffs {#tests}

The released [region regression tests](https://github.com/pgsty/mc/blob/e1d4cc5abfe00b674eb36347399e7398990be467/cmd/client-s3-region_test.go)
use the production configuration loader and an HTTP fixture that rejects
`GetBucketLocation`. They cover Stat/Put with a fixed region, signing regions,
environment precedence and client-cache isolation. This checks the path from
stored configuration to the SDK; it does not establish compatibility with every
third-party S3 service. The maintained release graph is SILO, SILO Console, mcli
and silo-pkg. Upstream MinIO/MC compatibility remains best effort.

The change connects the SDK's existing region option to persistent aliases,
while ordinary old configurations retain discovery. Operators must account for
fixed-region semantics, alias replacement and old-client writeback. Additional
CLI options can be evaluated separately.

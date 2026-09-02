---
title: "mc admin update"
url: "/reference/minio-mc-admin/mc-admin-update/"
weight: 180
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-update.rst
upstream_modified: true
---

<a id="mc-admin-update"></a>

<a id="command-mc.admin.update"></a>

## Description {#description}

The [`mc admin update`](#command-mc.admin.update) command invokes the MinIO-compatible server-side in-place update API. The client can pass an optional release mirror URL, and the server distributes the selected binary to all nodes.

After running the command, a prompt displays to confirm the update. Type `y` and `[ENTER]` to confirm and proceed with the update.

The user **must** have `write` permissions for the target location where the binary installs.

> [!CAUTION]
> **Do not use the default update path on Silo**
>
> Since `RELEASE.2026-08-06T00-00-00Z` the Silo server disables the in-place updater: `mc admin update ALIAS` cannot replace the binary and no longer contacts the upstream `dl.min.io` feed. Servers still on `RELEASE.2026-08-04T00-00-00Z` or older resolve an omitted `MIRROR_URL` through that feed and retain the upstream MinIO signing key, so running `mc admin update` against them can replace Silo with an upstream MinIO binary. Roll out new versions through packages, images, or your orchestrator.
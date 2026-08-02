---
title: "mc quota"
url: "/reference/deprecated/mc-quota/"
weight: 70
icon: fa-solid fa-box-archive
minio_origin: true
silo_modified: false
---

<a id="mc-quota"></a>

<a id="command-mc.quota"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2024-07-31T15-58-33Z**

`mc quota` and its subcommands are deprecated.
{{% /alert %}}

## Description {#description}

The [`mc quota`](#command-mc.quota) commands configure, display, or remove a quota limit on a bucket.

When a bucket with a quota configured reaches the specified limit, as determined by the MinIO object scanner, MinIO rejects further `PUT` requests for the bucket.

Each time the MinIO [object scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) scans a bucket for pending [object lifecycle transitions](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management), it also checks if the bucket has exceeded a configured quota.

{{% alert color="info" %}}
**Quota enforcement is not immediate**

Bucket quotas are not intended to enforce a strict hard limit on a bucket’s size. If a bucket exceeds its quota between scanner passes, MinIO continues to accept `PUT` requests for that bucket until _after_ the next scanner pass identifies the quota violation.
{{% /alert %}}

## Subcommands {#subcommands}

[`mc quota`](#command-mc.quota) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/deprecated/mc-quota-clear/#command-mc.quota.clear"><code>clear</code></a></p></td>
      <td><p>The <a href="/reference/deprecated/mc-quota-clear/#command-mc.quota.clear"><code>mc quota clear</code></a> command removes a configured storage quota for a bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/deprecated/mc-quota-info/#command-mc.quota.info"><code>info</code></a></p></td>
      <td><p>The <a href="/reference/deprecated/mc-quota-info/#command-mc.quota.info"><code>mc quota info</code></a> command displays the currently configured quota for a bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/deprecated/mc-quota-set/#command-mc.quota.set"><code>set</code></a></p></td>
      <td><p>The <a href="/reference/deprecated/mc-quota-set/#command-mc.quota.set"><code>mc quota set</code></a> assigns a hard quota limit to a bucket beyond which MinIO does not allow writes.</p></td>
    </tr>
  </tbody>
</table>

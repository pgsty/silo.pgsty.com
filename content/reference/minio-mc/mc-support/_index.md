---
title: "mc support"
url: "/reference/minio-mc/mc-support/"
weight: 380
icon: fa-solid fa-life-ring
minio_origin: true
silo_modified: false
---

<a id="mc-support"></a>

<a id="command-mc.support"></a>

## Description {#description}

The MinIO Client [`mc support`](#command-mc.support) commands provides tools for analyzing deployment health or performance and for running diagnostics. You can also upload generated health reports for further analysis by MinIO engineering.

{{% alert color="warning" %}}
**Important**

The `mc support` commands require an active [MinIO SUBNET](https://min.io/pricing?jmp=docs) registration.

[`mc support proxy set`](/reference/minio-mc/mc-support-proxy/#mc.support.proxy.set) and [`mc support proxy remove`](/reference/minio-mc/mc-support-proxy/#mc.support.proxy.remove) are exceptions, as you may need to set up a proxy to complete the deployment registration.
{{% /alert %}}

## Subcommands {#subcommands}

[`mc support`](#command-mc.support) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-support-callhome/#command-mc.support.callhome"><code>callhome</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-support-callhome/#command-mc.support.callhome"><code>mc support callhome</code></a> command allows the enabling or disabling of diagnostic information from a deployment to <a href="https://min.io/pricing?jmp=docs">MinIO SUBNET</a>.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-support-diag/#command-mc.support.diag"><code>diag</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-support-diag/#command-mc.support.diag"><code>mc support diag</code></a> command generates a health report for a MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-support-inspect/#command-mc.support.inspect"><code>inspect</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-support-inspect/#command-mc.support.inspect"><code>mc support inspect</code></a> command collects the data and metadata associated to objects at the specified path.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-support-perf/#command-mc.support.perf"><code>perf</code></a></p></td>
      <td><p>Use the <a href="/reference/minio-mc/mc-support-perf/#command-mc.support.perf"><code>mc support perf</code></a> command to review the performance of the S3 API (read/write), network IO, and storage (drive read/write).</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-support-profile/#command-mc.support.profile"><code>profile</code></a></p></td>
      <td><p><a href="/reference/minio-mc/mc-support-profile/#command-mc.support.profile"><code>mc support profile</code></a> runs a system profile for your deployment.
The results of the profile can provide insight into the MinIO server process running on a given node.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-support-proxy/#command-mc.support.proxy"><code>proxy</code></a></p></td>
      <td><p>Use the <a href="/reference/minio-mc/mc-support-proxy/#command-mc.support.proxy"><code>mc support proxy</code></a> command to configure a proxy to use to communicate with <a href="https://min.io/pricing?jmp=docs">MinIO SUBNET</a>.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-support-top/#command-mc.support.top"><code>top</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-support-top/#command-mc.support.top"><code>mc support top</code></a> command returns statistics for distributed
MinIO deployments, similar to the output of the <code>top</code> command in a shell.</p></td>
    </tr>
  </tbody>
</table>

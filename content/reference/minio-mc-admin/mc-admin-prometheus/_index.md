---
title: "mc admin prometheus"
url: "/reference/minio-mc-admin/mc-admin-prometheus/"
weight: 120
icon: fa-solid fa-chart-line
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-prometheus.rst
upstream_modified: false
---

<a id="mc-admin-prometheus"></a>

<a id="command-mc.admin.prometheus"></a>

## Description {#description}

The [`mc admin prometheus`](#command-mc.admin.prometheus) command and its subcommands provide access to MinIO Prometheus metrics.

## Subcommands {#subcommands}

[`mc admin prometheus`](#command-mc.admin.prometheus) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-prometheus-generate/#command-mc.admin.prometheus.generate"><code>generate</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-prometheus-generate/#command-mc.admin.prometheus.generate"><code>mc admin prometheus generate</code></a> command generates a metrics scraping configuration file for use with <a href="https://prometheus.io/">Prometheus</a>.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-prometheus-metrics/#command-mc.admin.prometheus.metrics"><code>metrics</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-prometheus-metrics/#command-mc.admin.prometheus.metrics"><code>mc admin prometheus metrics</code></a> command prints Prometheus metrics for a cluster.</p></td>
    </tr>
  </tbody>
</table>

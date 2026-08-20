---
title: "mc event"
url: "/reference/minio-mc/mc-event/"
weight: 100
icon: fa-solid fa-bell
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-event.rst
upstream_modified: false
---

<a id="mc-event"></a>

<a id="command-mc.event"></a>

## Description {#description}

The [`mc event`](#command-mc.event) command supports adding, removing, and listing bucket event notifications.

MinIO automatically sends triggered events to the configured notification targets. MinIO supports notification targets like AMQP (RabbitMQ), Redis, ElasticSearch, NATS and PostgreSQL. See [MinIO Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) for more information.

## Subcommands {#subcommands}

[`mc event`](#command-mc.event) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-event-add/#command-mc.event.add"><code>add</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-event-add/#command-mc.event.add"><code>mc event add</code></a> command adds event notification triggers to a bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-event-list/#command-mc.event.ls"><code>ls</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-event-list/#command-mc.event.ls"><code>mc event ls</code></a> command lists all event notification triggers for a
bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-event-remove/#command-mc.event.rm"><code>rm</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-event-remove/#command-mc.event.rm"><code>mc event rm</code></a> command removes an event notification trigger from a bucket.</p></td>
    </tr>
  </tbody>
</table>

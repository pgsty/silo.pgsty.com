---
title: "mc admin logs"
url: "/reference/minio-mc-admin/mc-admin-logs/"
weight: 100
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-logs.rst
upstream_modified: false
---

<a id="mc-admin-logs"></a>

<a id="command-mc.support.logs.show"></a>

<a id="command-mc.admin.logs"></a>

> [!NOTE]
> **SUBNET Registration Required**
>
> The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.

> [!NOTE]
> **Changed: RELEASE.2022-12-02T23-48-47Z**
>
> `mc support logs` moved to `mc admin logs` and provide a simpler command interface for displaying server logs for the MinIO deployment.
>
> The output is similar to what is available via `journalctl -uf minio` for systemd-controlled deployments.

## Description {#description}

Use the [`mc admin logs`](#command-mc.admin.logs) command to show MinIO server logs.

The uploading feature remains disabled by default until explicitly enabled for a deployment on an opt-in only basis. If enabled, you can disable the feature at any time with [`mc support callhome disable`](/reference/minio-mc/mc-support-callhome/#mc.support.callhome.disable).

## Examples {#examples}

### Show Logs for a Deployment {#show-logs-for-a-deployment}

The following command displays the most recent ten server logs of any type for the alias `minio1`.

```shell
mc admin logs minio1
```

### Show Last 5 Log Entries for a Node {#show-last-5-log-entries-for-a-node}

The following command shows the most recent five log entries for a `node1` on the deployment with alias `minio1`.

```shell
mc admin logs --last 5 myminio node1
```

### Show Application Type Log Entires for a Deployment {#show-application-type-log-entires-for-a-deployment}

The following command shows log entries of the type `application` for all nodes on the deployment with alias `minio1`.

```shell
mc admin logs --type application minio1
```

## Syntax {#syntax}

The command has the following syntax:

```shell
mc admin logs [GLOBAL FLAGS]     \
              [--last, -l value] \
              [--type, -t value] \
              ALIAS              \
              [NODE]
```

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.logs.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

##### `--last, -l` {#mc.admin.logs.-last}

*mc-cmd*

*Optional*

Show only the most recent specified number of log entries.

If this flag is not included, up to the last 10 log entries show.

##### `--type, --type` {#mc.admin.logs.-type}

*mc-cmd*

*Optional*

List log entries of a specified type. Valid types are `minio`, `application`, or `all`.

If not specified, all log entry types show.

##### `NODE` {#mc.admin.logs.NODE}

*mc-cmd*

*Optional*

In distributed deployments, specify which node’s logs to show by entering the node’s name.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

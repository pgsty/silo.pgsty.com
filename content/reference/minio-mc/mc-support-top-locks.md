---
title: "mc support top locks"
url: "/reference/minio-mc/mc-support-top-locks/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="mc-support-top-locks"></a>

<a id="command-mc.support.top.locks"></a>

{{% alert color="info" %}}
**SUBNET Registration Required**

The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.
{{% /alert %}}

## Syntax {#syntax}

The [`mc support top locks`](#command-mc.support.top.locks) command lists the ten oldest [locks](/administration/object-management/object-retention/#minio-object-locking) on a MinIO deployment.

The command outputs the age of the lock, type of lock, owner, and resource. The output resembles the following:

```shell
Since                 Type    Owner                 Resource
13 hours ago          WRITE   10.68.100.18:9000     .minio.sys/leader.lock
13 hours ago          WRITE   10.68.100.18:9000     .minio.sys/callhome/runCallhome.lock
13 hours ago          WRITE   10.68.100.23:9000     .minio.sys/new-drive-healing/0/0
```

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command displays the current in-progress S3 API calls on the [alias](/glossary/#term-alias) `myminio`.

```shell
mc support top locks myminio/
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] support top locks  \
                 [--stale]          \
                 TARGET
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `TARGET` {#mc.support.top.locks.TARGET}

*mc-cmd*

*Required*

The full path to the [alias](/reference/minio-mc/mc-alias-set/#minio-mc-alias) or prefix where the command should run.

##### `--stale` {#mc.support.top.locks.-stale}

*mc-cmd*

*Optional*

Return only stale locks.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Display the 10 Oldest Locks on the `myminio` Deployment {#display-the-10-oldest-locks-on-the-myminio-deployment}

```shell
mc support top locks myminio/
```

### Display Stale Locks on the `myminio` Deployment {#display-stale-locks-on-the-myminio-deployment}

The following command displays all in-progress `s3.PutObject` calls for the `myminio` deployment:

```shell
mc support top locks --stale myminio/
```

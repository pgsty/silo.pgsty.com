---
title: "mc support perf"
url: "/reference/minio-mc/mc-support-perf/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-perf.rst
upstream_modified: false
---

<a id="mc-support-perf"></a>

<a id="command-mc.support.perf"></a>

> [!NOTE]
> **Changed: RELEASE.2022-07-24T02-25-13Z**
>
> `mc support perf` replaces the `mc admin speedtest` command.

> [!NOTE]
> **SUBNET Registration Required**
>
> The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.

## Description {#description}

Use the [`mc support perf`](#command-mc.support.perf) command to review the performance of the S3 API (read/write), network IO, and storage (drive read/write).

The resulting tests can provide general guidance of deployment performance under S3 `GET` and `PUT` requests and identify any potential bottlenecks. For more complete performance testing, consider using a combination of load-testing using your staging application environments and the MinIO [WARP](https://github.com/minio/warp)<a id="warp"></a> S3 benchmarking tool.

[`mc support perf`](#command-mc.support.perf) has the following subcommands

1. [`drive`](#mc.support.perf.drive)

   Measure the speed of drives in a MinIO deployment.

   [`mc support perf drive`](#mc.support.perf.drive) temporarily suspends S3 API calls during the test. Incoming requests are held in a queue while the command runs. When the command completes or ends, MinIO processes the queued requests and resumes normal operations.
2. [`object`](#mc.support.perf.object)

   Measure the speed of reading and writing objects in a cluster.
3. [`net`](#mc.support.perf.net)

   Measure the network throughput of all nodes.

   [`mc support perf net`](#mc.support.perf.net) temporarily suspends S3 API calls during the test. Incoming requests are held in a queue while the command runs. When the command completes or ends, MinIO processes the queued requests and resumes normal operations.
4. [`client`](#mc.support.perf.client)

   Measure the network throughput to a client.
5. [`site-replication`](#mc.support.perf.site-replication)

   Measure the speed of site replication operations.

> [!NOTE]
> **SUBNET Registration Required**
>
> The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.

## Examples {#examples}

### Measure Speed of an Object {#measure-speed-of-an-object}

Measure the performance of S3 read/write of an object on the alias `minio1`. MinIO autotunes concurrency to obtain maximum throughput and IOPS (Input/Output Per Second).

```shell
mc support perf object minio1
```

### Measure Speed of an Object of a Specific Size for a Specific Duration {#measure-speed-of-an-object-of-a-specific-size-for-a-specific-duration}

Run object the S3 read/write performance of an object for 20 seconds with object size of 128MiB on alias `minio1`. MinIO autotunes concurrency to obtain maximum throughput.

```shell
mc support perf object minio1 --duration 20s --size 128MiB
```

### Test Speed of All Drives on All Nodes with Default Specifications {#test-speed-of-all-drives-on-all-nodes-with-default-specifications}

Run drive read/write performance measurements on all drive on all nodes for a cluster with alias `minio1`. The command does not specify the blocksize, so the default of 4MiB is used.

```shell
mc support perf drive minio1
```

### Test Drive Speed Measurements with Custom Specifications {#test-drive-speed-measurements-with-custom-specifications}

Run drive read/write performance measurements on a cluster with alias `minio1` specifying a blocksize of 64KiB and data read/written from each drive of 2GiB.

```shell
mc support perf drive minio1 --blocksize 64KiB --filesize 2GiB
```

### Test Network Throughput {#test-network-throughput}

Run a network throughput test on a cluster with alias `minio1`.

```shell
mc support perf net minio1
```

### Test Site Replication Speed {#test-site-replication-speed}

Run a test on the speed of site replication operations from the `minio1` site to other configured peers.

```shell
mc support perf site-replication minio1
```

## Syntax {#syntax}

#### `mc support perf drive` {#mc.support.perf.drive}

*mc-cmd*

Measure the read/write speed of the drives in a cluster.

```shell
mc [GLOBAL FLAGS] support perf drive   \
                [--concurrent]         \
                [--verbose, -v]        \
                [--filesize]           \
                [--blocksize]          \
                [--serial]             \
                [--airgap]             \
                ALIAS
```

#### `mc support perf object` {#mc.support.perf.object}

*mc-cmd*

Measure the S3 performance of reading and writing objects in a cluster.

```shell
mc [GLOBAL FLAGS] support perf object  \
                [--size]               \
                [--concurrent]         \
                [--verbose, -v]        \
                [--airgap]             \
                ALIAS
```

#### `mc support perf net` {#mc.support.perf.net}

*mc-cmd*

Measure the network throughput of all nodes in a cluster.

```shell
mc [GLOBAL FLAGS] support perf net  \
                [--concurrent]      \
                [--verbose, -v]     \
                [--serial]          \
                [--airgap]          \
                ALIAS
```

#### `mc support perf client` {#mc.support.perf.client}

*mc-cmd*

Measure the network throughput from the local device running the MinIO Client to the server.

```shell
mc [GLOBAL FLAGS] support perf client  \
                --duration             \
                [--verbose, -v]        \
                [--airgap]             \
                ALIAS
```

#### `mc support perf site-replication` {#mc.support.perf.site-replication}

*mc-cmd*

Measure the speed of site replication operations from the specified `ALIAS` to other configured peers.

```shell
mc [GLOBAL FLAGS] support perf site-replication \
                  --duration                    \
                  [--verbose, -v]               \
                  ALIAS
```

### Parameters {#parameters}

##### `--airgap` {#mc.support.perf.-airgap}

*mc-cmd*

*Optional*

Use in environments without network access to SUBNET (for example, airgapped, firewalled, or similar configuration).

If the deployment is airgapped, but the local device where you are using the [minio client](/reference/minio-mc/#minio-client) has network access, you do not need to use the `--airgap` flag.

##### `--size` {#mc.support.perf.-size}

*mc-cmd*

*Optional*

Applies to the [`object`](#mc.support.perf.object) command.

Specify the size of the object to use for upload and download performance test.

If not specified, the default value is `64MiB`.

Use `--size <value>` where `<value>` is a number and the storage unit, `KiB`, `MiB`, or `GiB`.

##### `--concurrent` {#mc.support.perf.-concurrent}

*mc-cmd*

*Optional*

Applies to the [`drive`](#mc.support.perf.drive), [`object`](#mc.support.perf.object), and [`net`](#mc.support.perf.net) commands.

Specify the number of concurrent requests to test per server.

If not specified, the default value is `32`.

Use `--concurrent <value>` where `<value>` is a number.

##### `--verbose, -v` {#mc.support.perf.-verbose}

*mc-cmd*

*Optional*

Applies to the [`drive`](#mc.support.perf.drive), [`object`](#mc.support.perf.object), and [`net`](#mc.support.perf.net) commands.

Show per-server stats in the output.

##### `--filesize` {#mc.support.perf.-filesize}

*mc-cmd*

*Optional*

Applies to the [`drive`](#mc.support.perf.drive) command.

Specify the total size of data to read or write to each drive.

If not specified, the default value is `1GiB`.

Use `--filesize <value>` where `<value>` is a number and storage unit, `KiB`, `MiB`, or `GiB`.

##### `--blocksize` {#mc.support.perf.-blocksize}

*mc-cmd*

*Optional*

Applies to the [`drive`](#mc.support.perf.drive) command.

Specify the read/write block size.

If not specified, the default value is `4MiB`.

Use `--filesize <value>` where `<value>` is a number and a storage unit, using standard storage unit abbreviations.

##### `--serial` {#mc.support.perf.-serial}

*mc-cmd*

*Optional*

Applies to the [`drive`](#mc.support.perf.drive) and [`net`](#mc.support.perf.net) commands.

Run performance tests on drive(s) one by one.

##### `ALIAS` {#mc.support.perf.ALIAS}

*mc-cmd*

*Required*

Applies to the [`drive`](#mc.support.perf.drive), [`object`](#mc.support.perf.object), [`net`](#mc.support.perf.net), and [`client`](#mc.support.perf.client) commands.

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

##### `--duration` {#mc.support.perf.-duration}

*mc-cmd*

*Required*

Applies to the [`client`](#mc.support.perf.client) command.

Length of time in seconds to perform the test. Time cannot be *0* or negative.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

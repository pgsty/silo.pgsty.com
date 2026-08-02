---
title: "mc ready"
url: "/reference/minio-mc/mc-ready/"
weight: 310
minio_origin: true
silo_modified: false
---

<a id="mc-ready"></a>

<a id="command-mc.ready"></a>

## Syntax {#syntax}

The [`mc ready`](#command-mc.ready) command checks the status of a cluster and whether the cluster has `read` and `write` quorum.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following sends a `GET` request to the cluster at alias `myminio` and returns its status.

```shell
mc ready myminio
```

The command sends a `GET` request to the deployment at the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) `myminio`.’ The command repeats the request until it is successful.

The output before the cluster at alias `myminio` is ready resembles the following:

```text
The cluster `myminio` is unreachable: Get "http://myminio.example.com:9000/minio/health/cluster": dial tcp 198.51.100.0:9000: connect: connection refused
```

Once the request succeeds in connecting to the `myminio` deployment, the output resembles the following:

```text
The cluster `myminio` is ready
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ready            \
                 TARGET           \
                 [--cluster-read] \
                 [--maintenance]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `TARGET` {#mc.ready.TARGET}

*mc-cmd*

*Required*

The full path to the [alias](/reference/minio-mc/mc-alias-set/#minio-mc-alias) or prefix where the command should run.

##### `--cluster-read` {#mc.ready.-cluster-read}

*mc-cmd*

*Optional*

Checks if the cluster has enough [quorum](/glossary/#term-read-quorum) to serve `READ` requests.

##### `--maintenance` {#mc.ready.-maintenance}

*mc-cmd*

*Optional*

Checks if the cluster can maintain read and write quorum if the node for the alias is taken down for maintenance.

Use an alias for the specific node you expect to take down for maintenance and not an alias set to a load balancer.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Check if the cluster has read quorum {#check-if-the-cluster-has-read-quorum}

The following command checks that a deployment has sufficient drives available for read operations.

```shell
mc read myminio --cluster-read
```

### Check if a cluster is down for maintenance {#check-if-a-cluster-is-down-for-maintenance}

The following command checks whether the cluster can maintain read and write quorum during maintenance when the node at alias `myminio` is taken down.

```shell
mc ready myminio --maintenance
```

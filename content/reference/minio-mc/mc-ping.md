---
title: "mc ping"
url: "/reference/minio-mc/mc-ping/"
weight: 270
minio_origin: true
silo_modified: false
---

<a id="mc-ping"></a>

<a id="command-mc.ping"></a>

## Syntax {#syntax}

The [`mc ping`](#command-mc.ping) command performs a liveness check on a specified target.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following sends a response request to the target(s) and outputs the minimum, maximum, average, and roundtrip times of the response, as well as the number of errors encountered when processing the request.

```shell
mc ping play --count 5
```

The command pings the deployment at the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) `play` for five cycles. The output resembles the following:

```shell
1: https://play.min.io   min=213.00ms   max=213.00ms   average=213.00ms   errors=0   roundtrip=213.00ms
2: https://play.min.io   min=67.15ms    max=213.00ms   average=140.07ms   errors=0   roundtrip=67.15ms
3: https://play.min.io   min=67.15ms    max=213.00ms   average=115.85ms   errors=0   roundtrip=67.41ms
4: https://play.min.io   min=61.26ms    max=213.00ms   average=102.20ms   errors=0   roundtrip=61.26ms
5: https://play.min.io   min=61.26ms    max=213.00ms   average=95.03ms    errors=0   roundtrip=66.36ms
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ping                       \
                 TARGET                     \
                 [--count, -c value]        \
                 [--error-count, -e value]  \
                 [--interval, -i value]     \
                 [--distributed, -a value]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `TARGET` {#mc.ping.TARGET}

*mc-cmd*

*Required*

The full path to the [alias](/reference/minio-mc/mc-alias-set/#minio-mc-alias) or prefix where the command should run.

##### `--count` {#mc.ping.-count}

*mc-cmd*

*Optional*

Specify the number of times to perform the check.

If not specified, the liveness check performs continuously until stopped.

##### `--error-count` {#mc.ping.-error-count}

*mc-cmd*

*Optional*

Specify a number of errors to receive before exiting.

For example, to stop the ping process after receiving five errors, use

```shell
mc ping TARGET -e 5
```

##### `--exit` {#mc.ping.-exit}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: RELEASE.2023-05-30T22-41-38Z**

{{% /alert %}}

Exit after the first successful check.

##### `--interval` {#mc.ping.-interval}

*mc-cmd*

*Optional*

The length of time in seconds to wait between requests.

By default, the command waits 1 second between requests.

##### `--distributed` {#mc.ping.-distributed}

*mc-cmd*

*Optional*

Send requests to all servers in the MinIO cluster.

{{% alert color="info" %}}
**Note**

Use this option for distributed deployments where you have direct access to each node or pod. This flag does not work when nodes are placed behind a service, such as a load balancer.
{{% /alert %}}

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Return Latency and Liveness for 5 Requests {#return-latency-and-liveness-for-5-requests}

The following command sends a liveness check for a deployment with the alias `myminio` five times, outputs the result of each check, then ends.

```shell
mc ping myminio --count 5
```

### Send Liveness Checks Repeatedly with 5 Minute Wait Between Each Request {#send-liveness-checks-repeatedly-with-5-minute-wait-between-each-request}

The following command sends continuous liveness check requests with an interval of 5 minutes (300 seconds) between each request.

```shell
mc ping myminio --interval 300
```

### End Liveness Checks for Error Counts Greater Than 20 {#end-liveness-checks-for-error-counts-greater-than-20}

The following command sends continuous liveness checks until 20 errors have been encountered:

```shell
mc ping myminio --error-count 20
```

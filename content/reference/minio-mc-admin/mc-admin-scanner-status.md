---
title: "mc admin scanner status"
url: "/reference/minio-mc-admin/mc-admin-scanner-status/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-admin-scanner-status"></a>

<a id="command-mc.admin.scanner.info"></a>

<a id="command-mc.admin.scanner.status"></a>

## Description {#description}

The [`mc admin scanner status`](#command-mc.admin.scanner.status) command displays a real-time summary of [scanner](/operations/concepts/scanner/#minio-concepts-scanner) information for a MinIO Server.

This command has an alias of `mc admin scanner info`.

{{% alert color="info" %}}
**Use `mc admin` on MinIO Deployments Only**

MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.
{{% /alert %}}

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example returns information about the current state of the scanner process.

```shell
mc admin scanner status myminio
```

The command returns results similar to the following:

```shell
Overall Statistics
------------------
Last full scan time:   0d0h15m; Estimated 2879.79/month
Current cycle:         (between cycles)
Active drives: 0

Last Minute Statistics
----------------------
Objects Scanned:       3 objects; Avg: 67.611µs; Rate: 4320/day
Versions Scanned:      3 versions; Avg: 2.506µs; Rate: 4320/day
Versions Heal Checked: 0 versions; Avg: 0ms
Read Metadata:         3 objects; Avg: 40.817µs, Size: 395 bytes/obj
ILM checks:            3 versions; Avg: 714ns
Check Replication:     3 versions; Avg: 892ns
Verify Deleted:        0 folders; Avg: 0ms
Yield:                 18ms total; Avg: 6ms/obj
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc admin scanner status ALIAS
                       [--bucket <string>]     \
                       [--interval <value>]   \
                       [--max-paths <value>]  \
                       [-n <integer>]         \
                       [--nodes <string>]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.scanner.status.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment for which to display [scanner](/operations/concepts/scanner/#minio-concepts-scanner) API operations.

##### `--bucket` {#mc.admin.scanner.status.-bucket}

*mc-cmd*

*Optional*

Filter scanner statistics to the specified bucket.

##### `--interval` {#mc.admin.scanner.status.-interval}

*mc-cmd*

*Optional*

The number of seconds to wait between status request refreshes. If not specified, the status refreshes every 3 seconds.

##### `--max-paths` {#mc.admin.scanner.status.-max-paths}

*mc-cmd*

*Optional*

The maximum number of active paths to show. Use `-1` for an unlimited number of paths.

Limiting the number of paths shown can reduce the scrolling of the console window when there are a large number of drives being scanned.

If not specified, the results return for an unlimited number of active paths.

##### `-n` {#mc.admin.scanner.status.-n}

*mc-cmd*

*Optional*

The number of status requests to return before automatically exiting. Use `0` to return an unlimited number of status results.

If not specified, the results continuously refresh at the specified interval until manually exited.

##### `--nodes` {#mc.admin.scanner.status.-nodes}

*mc-cmd*

*Optional*

Returns scanner status information for the specified node(s). Specify multiple nodes as a comma-separated list.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

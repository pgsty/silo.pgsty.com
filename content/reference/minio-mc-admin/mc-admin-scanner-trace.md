---
title: "mc admin scanner trace"
url: "/reference/minio-mc-admin/mc-admin-scanner-trace/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-scanner-trace.rst
upstream_modified: false
---

<a id="mc-admin-scanner-trace"></a>

<a id="command-mc.admin.scanner.trace"></a>

## Description {#description}

The [`mc admin scanner trace`](#command-mc.admin.scanner.trace) command displays [scanner](/operations/concepts/scanner/#minio-concepts-scanner)-specific API operations occurring on the target MinIO deployment.

> [!NOTE]
> **Use `mc admin` on MinIO Deployments Only**
>
> MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example returns a list of API operations related to the scanner on the `myminio` deployment.

```shell
mc admin scanner trace myminio
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc admin scanner trace ALIAS
                       [--filter-request]            \
                       [--filter-response]           \
                       [--filter-size <value>]       \
                       [--funcname <value>]          \
                       [--node <value>]              \
                       [--path <value>]              \
                       [--response-duration <value>] \
                       [--verbose, -v]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.scanner.trace.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment for which to display [scanner](/operations/concepts/scanner/#minio-concepts-scanner) API operations.

##### `--filter-request` {#mc.admin.scanner.trace.-filter-request}

*mc-cmd*

*Optional*

Trace scanner operations or calls with request size greater than the specified [`--filter-size`](#mc.admin.scanner.trace.-filter-size) value.

**Must** be used with [`--filter-size`](#mc.admin.scanner.trace.-filter-size) flag.

##### `--filter-response` {#mc.admin.scanner.trace.-filter-response}

*mc-cmd*

*Optional*

Trace scanner operations or calls with response size greater than the specified [`--filter-size`](#mc.admin.scanner.trace.-filter-size) value.

**Must** be used with [`--filter-size`](#mc.admin.scanner.trace.-filter-size) flag.

##### `--filter-size` {#mc.admin.scanner.trace.-filter-size}

*mc-cmd*

*Optional*

Filter output to request sizes or response sizes greater than the specified size.

Must be used with either [`--filter-request`](#mc.admin.scanner.trace.-filter-request) or [`--filter-response`](#mc.admin.scanner.trace.-filter-response) flag.

Valid units include:

| Suffix | Unit Size |
| --- | --- |
| `k` | KB (Kilobyte, 1000 Bytes) |
| `m` | MB (Megabyte, 1000 Kilobytes) |
| `g` | GB (Gigabyte, 1000 Megabytes) |
| `t` | TB (Terrabyte, 1000 Gigabytes) |
| `ki` | KiB (Kibibyte, 1024 Bites) |
| `mi` | MiB (Mebibyte, 1024 Kibibytes) |
| `gi` | GiB (Gibibyte, 1024 Mebibytes) |
| `ti` | TiB (Tebibyte, 1024 Gibibytes) |

##### `--funcname` {#mc.admin.scanner.trace.-funcname}

*mc-cmd*

*Optional*

Returns calls for the entered function name.

##### `--node` {#mc.admin.scanner.trace.-node}

*mc-cmd*

*Optional*

Returns calls for the specified server.

##### `--path` {#mc.admin.scanner.trace.-path}

*mc-cmd*

*Optional*

Returns calls for the specified path.

##### `--response-duration` {#mc.admin.scanner.trace.-response-duration}

*mc-cmd*

*Optional*

Trace calls with response duration greater than the specified value.

##### `--verbose, -v` {#mc.admin.scanner.trace.-verbose}

*mc-cmd*

*Optional*

Returns verbose output.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Monitor all scanner API operations {#monitor-all-scanner-api-operations}

Use [`mc admin scanner trace`](#command-mc.admin.scanner.trace) to monitor [scanner](/operations/concepts/scanner/#minio-concepts-scanner) API operations on the MinIO deployment at the alias `myminio`:

```shell
mc admin scanner trace myminio
```

### Show scanner trace for a specific path {#show-scanner-trace-for-a-specific-path}

Use [`mc admin scanner trace`](#command-mc.admin.scanner.trace) to monitor API operations for a the path `my-bucket/my-prefix/*` on the deployment at the `myminio` alias:

```shell
 mc admin scanner trace --path my-bucket/my-prefix/* myminio
```

### Show scanner API operations for the `scanObject` function {#show-scanner-api-operations-for-the-scanobject-function}

Monitor scanner activity for the `scanObject function` on the `myminio` deployment:

```shell
mc admin scanner trace --funcname=scanner.ScanObject myminio
```

### Show scanner operation requests greater than `1MB` in size {#show-scanner-operation-requests-greater-than-1mb-in-size}

Use [`mc admin scanner trace`](#command-mc.admin.scanner.trace) to monitor requests larger than a `1MB` on the `myminio` deployment:

```shell
mc admin scanner trace --filter-request --filter-size 1MB myminio
```

### Show scanner operation responses greater than `1MB` in size {#show-scanner-operation-responses-greater-than-1mb-in-size}

Use [`mc admin scanner trace`](#command-mc.admin.scanner.trace) to monitor large response sizes:

```shell
 mc admin scanner trace --filter-response --filter-size 1MB myminio
```

### Show scanner operations that last longer than five milliseconds {#show-scanner-operations-that-last-longer-than-five-milliseconds}

Use [`mc admin scanner trace`](#command-mc.admin.scanner.trace) to monitor long operations:

```shell
 mc admin scanner trace --response-duration 5ms myminio
```

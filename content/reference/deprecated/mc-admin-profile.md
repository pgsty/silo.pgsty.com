---
title: "mc admin profile"
url: "/reference/deprecated/mc-admin-profile/"
weight: 170
minio_origin: true
silo_modified: false
---

<a id="mc-admin-profile"></a>

<a id="command-mc.admin.profile"></a>

{{% alert color="info" %}}
**Note**

This command has been replaced by [`mc support profile`](/reference/minio-mc/mc-support-profile/#command-mc.support.profile) as of *mc* RELEASE.2023-04-06T16-51-10Z.
{{% /alert %}}

## Description {#description}

The [`mc admin profile`](#command-mc.admin.profile) command generates profiling data for debugging purposes.

{{% alert color="info" %}}
**Use `mc admin` on MinIO Deployments Only**

MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.
{{% /alert %}}

### Profile Data Format {#profile-data-format}

[`mc admin profile`](#command-mc.admin.profile) produces a `ZIP` archive `profile.zip` that contains one or more `.pprof` files. Use the [pprof](https://github.com/google/pprof) `go` utility to read the profile data.

## Examples {#examples}

### Profile Data for Single Resource {#profile-data-for-single-resource}

Use [`mc admin profile start`](#mc.admin.profile.start) with the [`type`](#mc.admin.profile.start.type) flag to start profiling the resource:

```shell
mc admin profile start --type "TYPE" ALIAS
```

- Replace [`ALIAS`](#mc.admin.profile.start.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO host.
- Replace [`TYPE`](#mc.admin.profile.start.type) with the resource to profile.

Use [`mc admin profile stop`](#mc.admin.profile.stop) to stop profiling data from the specified resource and output the results:

```shell
mc admin profile stop
```

The command outputs the profiled data as `profile.zip`.

### Profile Data for Multiple Resources {#profile-data-for-multiple-resources}

Use [`mc admin profile start`](#mc.admin.profile.start) with the [`type`](#mc.admin.profile.start.type) flag to start profiling the resources:

```shell
mc admin profile start --type "TYPE,[TYPE...]" ALIAS
```

- Replace [`ALIAS`](#mc.admin.profile.start.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO host.
- Replace [`TYPE`](#mc.admin.profile.start.type) with the resources to profile. Specify multiple resources as a comma-separated list.

Use [`mc admin profile stop`](#mc.admin.profile.stop) to stop profiling data from the specified resources and output the results:

```shell
mc admin profile stop
```

The command outputs the profiled data as `profile.zip`.

## Syntax {#syntax}

[`mc admin profile`](#command-mc.admin.profile) has the following syntax:

```shell
mc admin profile SUBCOMMAND
```

[`mc admin profile`](#command-mc.admin.profile) supports the following subcommands:

#### `mc admin profile start` {#mc.admin.profile.start}

*mc-cmd*

Starts collecting profiling data on the target MinIO deployment. The command has the following syntax:

```shell
mc admin profile start [FLAGS] TARGET
```

[`mc admin profile start`](#mc.admin.profile.start) supports the following arguments:

#### `TARGET` {#mc.admin.profile.start.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment from which the command collects profiling data.

#### `type` {#mc.admin.profile.start.type}

*mc-cmd*

The type(s) of profiling data to collect from the [`TARGET`](#mc.admin.profile.start.TARGET) MinIO deployment.

Specify one or more of the following supported types as a comma-separated list:

- `cpu`
- `mem`
- `block`
- `mutex`
- `trace`
- `threads`
- `goroutines`

Defaults to `cpu,mem,block` if omitted.

#### `mc admin profile stop` {#mc.admin.profile.stop}

*mc-cmd*

Stops the profiling process and returns the collected data as `profile.zip`. The `zip` file contains one or more `.pprof` files which are readable with programs like the `go` [pprof](https://github.com/google/pprof) utility.

The command has the following syntax:

```shell
mc admin profile stop TARGET
```

The command supports the following arguments:

#### `TARGET` {#mc.admin.profile.stop.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment from which the command returns available profiling data.

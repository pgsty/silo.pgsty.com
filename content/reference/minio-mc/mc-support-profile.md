---
title: "mc support profile"
url: "/reference/minio-mc/mc-support-profile/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="mc-support-profile"></a>

<a id="command-mc.support.profile"></a>

{{% alert color="info" %}}
**SUBNET Registration Required**

The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.
{{% /alert %}}

## Description {#description}

[`mc support profile`](#command-mc.support.profile) runs a system profile for your deployment. The results of the profile can provide insight into the MinIO server process running on a given node.

The resulting report is intended for use by MinIO Engineering. You can upload the report to [MinIO SUBNET](https://min.io/pricing?jmp=docs). Independent or third-party use of these profiles for diagnostics and remediation is done at your own risk.

{{% alert color="info" %}}
**SUBNET Registration Required**

The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.
{{% /alert %}}

## Examples {#examples}

### Fetch CPU Profiling {#fetch-cpu-profiling}

This command retrieves the CPU profile on a MinIO deployment with the alias `minio1`. The profile runs for the default of 10 seconds.

```shell
mc support profile --type cpu minio1/
```

### Fetch CPU, Memory, and Block Profiling Concurrently {#fetch-cpu-memory-and-block-profiling-concurrently}

This command fetches the profile of the CPU, memory, and block usage on the alias `minio2`. The profile runs for the default of 10 seconds.

```shell
mc support profile --type cpu,mem,block minio2/
```

### Fetch CPU, Memory, and Block Profiling Concurrently for 10 Minutes {#fetch-cpu-memory-and-block-profiling-concurrently-for-10-minutes}

This command fetches the profile of the CPU, memory, and block on the alias `minio3`. The profile runs for 10 minutes (600 seconds).

```shell
mc support profile --type cpu,mem,block --duration 600 minio3/
```

## Syntax {#syntax}

The [`mc support profile`](#command-mc.support.profile) command has the following syntax:

```shell
mc [GLOBALFLAGS] support profile       \
                         COMMAND       \
                         [--type]      \
                         [--airgap]    \
                         [--duration]  \
                         ALIAS
```

### Parameters {#parameters}

##### `--duration` {#mc.support.profile.-duration}

*mc-cmd*

*Optional*

Run profiling for the specified duration in seconds.

Use `--type <value>` where `<value>` is the number of seconds for the profile to run.

If not specified, the command collects data for 10 seconds.

##### `--type` {#mc.support.profile.-type}

*mc-cmd*

*Optional*

Specify the profile(s) to gather data for.

Use `--type <value>` where `<value>` is one or more comma-separated types of data to collect.

Valid types are:

- `cpu`
- `cpuio`
- `mem`
- `block`
- `mutex`
- `trace`
- `threads`
- `goroutines`

If not specified, the command collects data for CPU, memory, block, mutex, threads, and goroutines.

{{% alert color="warning" %}}
**Important**

Do not use the `cpuio` or `trace` data types unless directed to by MinIO Support. These profiles require significant resources and may degrade cluster performance if used without guidance.
{{% /alert %}}

##### `--airgap` {#mc.support.profile.-airgap}

*mc-cmd*

*Optional*

Use in environments without network access to SUBNET (for example, airgapped, firewalled, or similar configuration).

If the deployment is airgapped, but the local device where you are using the [minio client](/reference/minio-mc/#minio-client) has network access, you do not need to use the `--airgap` flag.

##### `ALIAS` {#mc.support.profile.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

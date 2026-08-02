---
title: "mc support callhome"
url: "/reference/minio-mc/mc-support-callhome/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-support-callhome"></a>

<a id="command-mc.support.logs.disable"></a>

<a id="command-mc.support.logs.enable"></a>

<a id="command-mc.support.logs.status"></a>

<a id="command-mc.support.callhome"></a>

## Description {#description}

The [`mc support callhome`](#command-mc.support.callhome) command allows the enabling or disabling of diagnostic information from a deployment to [MinIO SUBNET](https://min.io/pricing?jmp=docs).

All `mc support` commands require an active SUBNET subscription.

When enabled, MinIO sends diagnostic information to SUBNET.

MinIO disables this functionality by default, regardless of registration status. You must explicitly enable the `callhome` function to begin information upload.

{{% alert color="info" %}}
**SUBNET Registration Required**

The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.
{{% /alert %}}

## Syntax {#syntax}

#### `mc support callhome enable` {#mc.support.callhome.enable}

*mc-cmd*

Begin sending a deployment’s diagnostics, logs, or both to SUBNET.

```shell
mc support callhome enable    \
                    ALIAS     \
                    [--logs]  \
                    [--diag]
```

{{% alert color="info" %}}
**Note**

The `--logs` and `--diag` flags are no longer supported in SUBNET and will be removed in a future release.
{{% /alert %}}

#### `mc support callhome disable` {#mc.support.callhome.disable}

*mc-cmd*

Stop sending a deployment’s diagnostics, logs, or both to SUBNET.

```shell
mc support callhome disable  \
                    ALIAS    \
                    [--logs] \
                    [--diag]
```

{{% alert color="info" %}}
**Note**

The `--logs` and `--diag` flags are no longer supported in SUBNET and will be removed in a future release.
{{% /alert %}}

#### `mc support callhome status` {#mc.support.callhome.status}

*mc-cmd*

Output whether a deployment currently sends diagnostics, logs, or both to SUBNET.

```shell
mc support callhome status   \
                    ALIAS    \
                    [--diag]
```

{{% alert color="info" %}}
**Note**

The `--diag` flag is no longer supported in SUBNET and will be removed in a future release.
{{% /alert %}}

### Parameters {#parameters}

##### `ALIAS` {#mc.support.callhome.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

##### `--diag` {#mc.support.callhome.-diag}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Note**

This option is no longer supported in SUBNET and will be removed in a future release.
{{% /alert %}}

Send or stop sending deployment diagnostic information to SUBNET every 24 hours.

## Examples {#examples}

### Enable `callhome` reporting {#enable-callhome-reporting}

Enable sending diagnostic information to SUBNET for a deployment registered to SUBNET with an [alias](/reference/minio-mc/mc-alias-set/#alias) of `minio1`.

```shell
mc support callhome enable minio1
```

### Disable `callhome` reporting {#disable-callhome-reporting}

Disable sending diagnostic information to SUBNET for a deployment registered to SUBNET with an [alias](/reference/minio-mc/mc-alias-set/#alias) of `minio1`.

```shell
mc support callhome disable minio1
```

### Display Current `callhome` settings {#display-current-callhome-settings}

Display whether a deployment with the alias `minio1` sends information to SUBNET.

```shell
mc support callhome status minio1
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

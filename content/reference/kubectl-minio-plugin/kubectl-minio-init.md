---
title: "kubectl minio init"
url: "/reference/kubectl-minio-plugin/kubectl-minio-init/"
weight: 9164
toc_hide: true
minio_origin: true
silo_modified: false
---

<a id="kubectl-minio-init"></a>
<a id="id1"></a>

<a id="command-kubectl.minio.init"></a>

## Description {#description}

The [`kubectl minio init`](#command-kubectl.minio.init) command initialize the MinIO Operator.

If the Kubernetes cluster has an existing MinIO Operator installation, this command upgrades the Operator to match the MinIO plugin version. For more information on upgrading the MinIO Operator, see [Upgrade MinIO Operator](/operations/deployments/k8s-upgrade-minio-operator-kubernetes/#minio-k8s-upgrade-minio-operator).

## Syntax {#syntax}

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command initializes a new MinIO Operator deployment running 7.1.1.

```shell
kubectl minio init
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
kubectl minio init                      \
              [--cluster-domain]        \
              [--console-image]         \
              [--console-tls]           \
              [--default-kes-image]     \
              [--default-minio-image]   \
              [--image]                 \
              [--image-pull-secret]     \
              [--namespace]             \
              [--namespace-to-watch]    \
              [--output]                \
              [--prometheus-name]       \
              [--prometheus-namespace]
```

{{% /tab %}}
{{< /tabpane >}}

## Flags {#flags}

The command supports the following flags:

#### `--cluster-domain` {#kubectl.minio.init.-cluster-domain}

*mc-cmd*

*Optional*

The domain name to use when configuring the DNS hostname of the operator. Defaults to `cluster.local`.

#### `--console-image` {#kubectl.minio.init.-console-image}

*mc-cmd*

*Optional*

The image to use when deploying the [Operator Console](https://github.com/minio/operator) in Operator mode, where administrators can create and manage MinIO tenants using a Graphical User Interface. Defaults to the [version bundled in variable DefaultOperatorImage for the matching Operator release](https://github.com/minio/operator/blob/master/kubectl-minio/cmd/helpers/constants.go).

#### `--console-tls` {#kubectl.minio.init.-console-tls}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: 4.5.6**

{{% /alert %}}

Enables TLS for the Operator Console.

Disabled by default.

#### `--default-kes-image` {#kubectl.minio.init.-default-kes-image}

*mc-cmd*

*Optional*

The default [kes](https://github.com/minio/kes) image to use when creating a new MinIO tenant. Defaults to the [version bundled in variable DefaultKESImage for the matching Operator release](https://github.com/minio/operator/blob/master/kubectl-minio/cmd/helpers/constants.go).

#### `--default-minio-image` {#kubectl.minio.init.-default-minio-image}

*mc-cmd*

*Optional*

The default [minio](https://github.com/minio/minio) image to use when creating a new MinIO tenant. Defaults to the [version bundled in variable DefaultTenantImage for the matching Operator release](https://github.com/minio/operator/blob/master/kubectl-minio/cmd/helpers/constants.go).

#### `--image` {#kubectl.minio.init.-image}

*mc-cmd*

*Optional*

The image to use for deploying the operator. Defaults to the [latest release of the operator](https://github.com/minio/operator/releases/latest).

#### `--image-pull-secret` {#kubectl.minio.init.-image-pull-secret}

*mc-cmd*

*Optional*

Secret key for use with pulling the [`--image`](#kubectl.minio.init.-image).

The MinIO-hosted `minio/operator` image is *not* password protected. This option is only required for non-MinIO image sources which are password protected.

#### `--namespace` {#kubectl.minio.init.-namespace}

*mc-cmd*

*Optional*

The namespace into which to deploy the operator. Defaults to `minio-operator`.

#### `--namespace-to-watch` {#kubectl.minio.init.-namespace-to-watch}

*mc-cmd*

*Optional*

The namespace which the operator watches for MinIO tenants. Defaults to `""` for *all namespaces*.

#### `--output` {#kubectl.minio.init.-output}

*mc-cmd*

*Optional*

Performs a dry run and outputs the generated YAML to `STDOUT`. Use this option to customize the YAML and apply it manually using `kubectl apply -f <FILE>`.

#### `--prometheus-name` {#kubectl.minio.init.-prometheus-name}

*mc-cmd*

*Optional*

The name of the Prometheus service managed by the Prometheus Operator. Defaults to `PROMETHEUS_NAME`

#### `--prometheus-namespace` {#kubectl.minio.init.-prometheus-namespace}

*mc-cmd*

*Optional*

The namespace into which to deploy Prometheus. Defaults to `PROMETHEUS_NAMESPACE`

#### `--sts` {#kubectl.minio.init.-sts}

*mc-cmd*

*Optional*

Enable Operator sts (v1alpha1)

{{% alert color="info" %}}
**Added: 5.0.0**

{{% /alert %}}

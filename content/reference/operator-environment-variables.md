---
title: "MinIO Operator Environment Variables"
url: "/reference/operator-environment-variables/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/operator-environment-variables.rst
upstream_modified: false
---

<a id="minio-operator-environment-variables"></a>
<a id="minio-operator-envvars"></a>

The [MinIO Operator](/operations/deployments/kubernetes/#minio-operator-installation) uses the following environment variables during startup to set configuration settings. Configure these variables in the `minio-operator` container.

## Setting Environment Variables in Kubernetes {#setting-environment-variables-in-kubernetes}

To set these environment variables, modify the operator container’s yaml at `.spec.env` or use the following `kubectl` command syntax:

```shell
kubectl set env -n minio-operator deployment/minio-operator <ENV_VARIABLE>=<value> ... <ENV_VARIABLE2>=<value2>
```

Replace:

- `minio-operator` with the namespace for your Operator, if not using the default value.
- `deployment/minio-operator` with the deployment for your Operator, if not the default value. (Most deployments use the default value.)
- `<ENV_VARIABLE>` with the environment variable to set or modify.
- `<value>` with the value to use for the environment variable.

You can set or modify multiple environment variables by separating each `VARIABLE=value` pair with a space.

## Available MinIO Operator Environment Variables {#available-minio-operator-environment-variables}

#### `MINIO_OPERATOR_CERTIFICATES_VERSION` {#envvar.MINIO_OPERATOR_CERTIFICATES_VERSION}

*envvar*

Specifies the certificate API version to use.

Valid values are `v1` or `v1beta1`.

When not specified, the default is the API Kubernetes provides.

#### `MINIO_OPERATOR_RUNTIME` {#envvar.MINIO_OPERATOR_RUNTIME}

*envvar*

Specify the type of runtime to use.

Valid values are `EKS`, `Rancher`, or `OpenShift`. Leave blank if none of the options apply.

When set as `EKS`, the [`MINIO_OPERATOR_CSR_SIGNER_NAME`](#envvar.MINIO_OPERATOR_CSR_SIGNER_NAME) must be `beta.eks.amazonaws.com/app-serving`.

#### `MINIO_OPERATOR_CSR_SIGNER_NAME` {#envvar.MINIO_OPERATOR_CSR_SIGNER_NAME}

*envvar*

Override the default signer for certificate signing requests (CSRs).

When not specified, the default value is `kubernetes.io/kubelet-serving`.

#### `OPERATOR_CERT_PASSWD` {#envvar.OPERATOR_CERT_PASSWD}

*envvar*

*Optional*

The password Operator should use to decrypt the private key in the TLS certificate for Operator.

#### `OPERATOR_STS_ENABLED` {#envvar.OPERATOR_STS_ENABLED}

*envvar*

Toggle STS Service `on` or `off`.

> [!NOTE]
> **Changed: v5.0.11**
>
> When not specified, the default value is `on`.

For versions prior to Operator 5.0.11, the default value was `off`.

#### `MINIO_CONSOLE_DEPLOYMENT_NAME` {#envvar.MINIO_CONSOLE_DEPLOYMENT_NAME}

*envvar*

The name to use for the Operator Console.

When not specified, the default value is `operator`.

#### `MINIO_CONSOLE_TLS_ENABLE` {#envvar.MINIO_CONSOLE_TLS_ENABLE}

*envvar*

Toggle Console TLS service `on` or `off`.

When not specified, the default value is `off`.

#### `MINIO_OPERATOR_IMAGE` {#envvar.MINIO_OPERATOR_IMAGE}

*envvar*

> [!NOTE]
> **Added: v5.0.11**

Specify the image of the MinIO instance sidecar container loaded by the Operator.

Omit to use the Operator image.

#### `WATCHED_NAMESPACE` {#envvar.WATCHED_NAMESPACE}

*envvar*

A comma-separated list of the namespace(s) Operator should watch for tenants.

When not specified, the default value is `""` to watch all namespaces.

---
title: "MinIO Kubernetes Operator"
url: "/operations/deployments/k8s-minio-operator/"
weight: 10
icon: fa-solid fa-dharmachakra
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/deployments/k8s-minio-operator.rst
upstream_modified: true
---

<a id="minio-kubernetes-operator"></a>
<a id="deploy-minio-operator"></a>

Silo is an S3-compatible object store. MinIO Operator is an upstream Kubernetes component whose repository was archived and made read-only on 2026-03-20. Its final release, `v7.1.1`, can manage a Silo server image through the Tenant CRD. The Operator name, API groups, CRD kinds, resource names, image names, and environment variables remain upstream contracts and are not rebranded here.

MinIO Operator installs [Custom Resource Definitions (CRDs)](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/#customresourcedefinitions), including the `Tenant` kind used to describe managed object-storage workloads as Kubernetes [objects](https://kubernetes.io/docs/concepts/overview/working-with-objects/kubernetes-objects/).

The pinned v7.1.1 Kustomize manifest deploys the Operator in the `minio-operator` namespace as one `minio-operator` Deployment with two controller replicas. It does not deploy a separate Operator Console pod.

This site verifies the Silo image override used by its deployment examples. The archived Operator has no ongoing upstream platform-support or commercial-support commitment, and this site does not create one.

See the pinned MinIO Operator v7.1.1 [CRD Reference](https://github.com/minio/operator/blob/v7.1.1/docs/tenant_crd.adoc) for the upstream CRD contract.

<a id="minio-operator-prerequisites"></a>

## Operator Prerequisites {#operator-prerequisites}

### Kubernetes Version {#kubernetes-version}

The archived v7.1.1 README requires Kubernetes 1.30.0 or later. Use a currently maintained Kubernetes release whose APIs remain compatible, and validate the exact combination in your own cluster. See the [maintained Kubernetes releases](https://kubernetes.io/releases/) and the [Operator v7.1.1 release](https://github.com/minio/operator/releases/tag/v7.1.1); Silo does not publish a broader Kubernetes support matrix.

Kubernetes infrastructure running end-of-life API versions may exhibit unexpected or undesired behavior if used for deploying the Operator.

### Kustomize and `kubectl` {#kustomize-and-kubectl}

[Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization) is a YAML-based templating tool that allows you to define Kubernetes resources in a declarative and repeatable fashion. Kustomize is included with the [kubectl](https://kubernetes.io/docs/reference/kubectl) command line tool.

This procedure assumes that your local host machine has both the matching version of `kubectl` for your Kubernetes cluster *and* the necessary access to that cluster to create new resources.

The pinned [MinIO Operator v7.1.1 Kustomize template](https://github.com/minio/operator/blob/v7.1.1/kustomization.yaml) provides a reproducible starting point. You can modify that Kustomization file or apply your own [patches](https://datatracker.ietf.org/doc/html/rfc6902) for your cluster. Do not infer that a newer supported upstream release exists; review any fork or replacement independently.

<a id="minio-k8s-deploy-operator-tls"></a>

### Kubernetes TLS Certificate API {#kubernetes-tls-certificate-api}

The MinIO Operator manages TLS Certificate Signing Requests (CSR) using the Kubernetes `certificates.k8s.io` [TLS certificate management API](https://kubernetes.io/docs/tasks/tls/managing-tls-in-a-cluster/) to create signed TLS certificates in the following circumstances:

- When `autoCert` is enabled.
- For the Tenant Console when the [`MINIO_CONSOLE_TLS_ENABLE`](/reference/operator-environment-variables/#envvar.MINIO_CONSOLE_TLS_ENABLE) environment variable is set to `on`.
- For [STS service](/developers/security-token-service/#minio-security-token-service) when [`OPERATOR_STS_ENABLED`](/reference/operator-environment-variables/#envvar.OPERATOR_STS_ENABLED) environment variable is set to `on`.
- For retrieving the health of the cluster.

The MinIO Operator reads certificates inside the `operator-ca-tls` secret and syncs this secret within the tenant namespace to trust private certificate authorities, such as when using cert-manager.

For any of these circumstances, the MinIO Operator *requires* that the Kubernetes `kube-controller-manager` configuration include the following [configuration settings](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/#options):

- `--cluster-signing-key-file` - Specify the PEM-encoded RSA or ECDSA private key used to sign cluster-scoped certificates.
- `--cluster-signing-cert-file` - Specify the PEM-encoded x.509 Certificate Authority certificate used to issue cluster-scoped certificates.

The Kubernetes TLS API uses the CA signature algorithm when generating a new certificate. ECDSA (for example, the [NIST P-256 curve](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf)) or EdDSA (for example, <a id="index-0"></a>[**Curve25519**](https://datatracker.ietf.org/doc/html/rfc7748.html)) can require less computation than RSA. See [Supported TLS Cipher Suites](/operations/network-encryption/#minio-tls-supported-cipher-suites) for the Silo server's supported suites.

If the Kubernetes cluster is not configured to respond to a generated <abbr title="Certificate Signing Request">CSR</abbr>, the Operator cannot complete initialization. Some Kubernetes providers do not specify these configuration values by default.

To check whether the `kube-controller-manager` specifies the cluster signing key and certificate files, use the following command:

```shell
kubectl get pod kube-controller-manager-$CLUSTERNAME-control-plane \
  -n kube-system -o yaml
```

- Replace `$CLUSTERNAME` with the name of the Kubernetes cluster.

Confirm that the output contains the highlighted lines. The output of the example command above may differ from the output in your terminal:

```shell
 spec:
 containers:
 - command:
     - kube-controller-manager
     - --allocate-node-cidrs=true
     - --authentication-kubeconfig=/etc/kubernetes/controller-manager.conf
     - --authorization-kubeconfig=/etc/kubernetes/controller-manager.conf
     - --bind-address=127.0.0.1
     - --client-ca-file=/etc/kubernetes/pki/ca.crt
     - --cluster-cidr=10.244.0.0/16
     - --cluster-name=my-cluster-name
     - --cluster-signing-cert-file=/etc/kubernetes/pki/ca.crt
     - --cluster-signing-key-file=/etc/kubernetes/pki/ca.key
 ...
```

> [!WARNING]
> **Important**
>
> MinIO Operator can generate TLS certificates for Tenant pods using the specified Certificate Authority (CA). Clients external to the Kubernetes cluster must trust that CA to connect to the Silo Tenant endpoints.
>
> Disabling TLS validation is suitable only for controlled testing. Production clients should trust the issuing CA or use certificates issued by a CA they already trust.
>
> Alternatively, generate x.509 TLS certificates signed by a known and trusted CA and pass those certificates through the Tenant CRD. See [Network Encryption (TLS)](/operations/network-encryption/#minio-tls) for more complete documentation.

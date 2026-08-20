---
title: "cert-manager for Operator"
url: "/operations/cert-manager/cert-manager-operator/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/cert-manager/cert-manager-operator.rst
upstream_modified: false
---

<a id="cert-manager-for-operator"></a>
<a id="minio-certmanager-operator"></a>

MinIO Operator manages TLS certificate issuing for the services hosted in the `minio-operator` namespace.

This page describes how to manage the Operator’s TLS certificates with [cert-manager](/operations/network-encryption/cert-manager/#minio-certmanager).

## Prerequisites {#prerequisites}

- A [supported version of Kubernetes](https://kubernetes.io/releases/).
- [kustomize](https://kustomize.io/) installed
- `kubectl` access to your `k8s` cluster
- Completed the steps to [set up cert-manager](/operations/network-encryption/cert-manager/#minio-setup-certmanager)
- The MinIO Operator must not yet be installed.

## 1) Create a CA Issuer for the `minio-operator` namespace {#create-a-ca-issuer-for-the-minio-operator-namespace}

This guide **disables** the automatic generation of certificates in MinIO Operator and issues certificates using cert-manager instead.

The `minio-operator` namespace must have its own certificate authority (CA), derived from the cluster’s `ClusterIssuer` certificate created during [cert-manager setup](/operations/network-encryption/cert-manager/#minio-certmanager). Create this CA certificate using cert-manager.

> [!WARNING]
> **Important**
>
> This CA certificate **must** exist *before* installing MinIO Operator.

1. If it does not exist, create the `minio-operator` namespace

   ```shell
   kubectl create ns minio-operator
   ```

2. Request a new Certificate with `spec.isCA: true` specified.

   This certificate serves as the <abbr title="Certificate Authority">CA</abbr> for the *minio-operator* namespace.

   Create a file called `operator-ca-tls-secret.yaml` with the following contents:

   ```yaml
   # operator-ca-tls-secret.yaml
   apiVersion: cert-manager.io/v1
   kind: Certificate
   metadata:
     name: minio-operator-ca-certificate
     namespace: minio-operator
   spec:
     isCA: true
     commonName: operator
     secretName: operator-ca-tls
     duration: 70128h # 8y
     privateKey:
       algorithm: ECDSA
       size: 256
     issuerRef:
       name: selfsigned-root
       kind: ClusterIssuer
       group: cert-manager.io
   ```

   > [!WARNING]
   > **Important**
   >
   > The `spec.issueRef.name` must match the name of the `ClusterIssuer` created when [setting up cert-manager](/operations/network-encryption/cert-manager/#minio-cert-manager-create-cluster-issuer). If you specified a different `ClusterIssuer` name or are using a different `Issuer` from the guide, modify the `issuerRef` to match your environment.
3. Apply the resource:

   ```shell
   kubectl apply -f operator-ca-tls-secret.yaml
   ```

Kubernetes creates a new secret with the name `operator-ca-tls` in the `minio-operator` namespace.

> [!WARNING]
> **Important**
>
> Make sure to trust this certificate in any applications that need to interact with the MinIO Operator.

## 2) Use the secret to create the `Issuer` {#use-the-secret-to-create-the-issuer}

Use the `operator-ca-tls` secret to add an `Issuer` resource for the `minio-operator` namespace.

1. Create a file called `operator-ca-issuer.yaml` with the following contents:

   ```yaml
   # operator-ca-issuer.yaml
   apiVersion: cert-manager.io/v1
   kind: Issuer
   metadata:
     name: minio-operator-ca-issuer
     namespace: minio-operator
   spec:
     ca:
       secretName: operator-ca-tls
   ```

2. Apply the resource:

   ```shell
   kubectl apply -f operator-ca-issuer.yaml
   ```

## 3) Create TLS certificate {#create-tls-certificate}

Now that the `Issuer` exists in the `minio-operator` namespace, cert-manager can add a certificate.

The certificate from cert-manager must be valid for the following DNS domains:

- `sts`
- `sts.minio-operator.svc.`
- `sts.minio-operator.svc.<cluster domain>`

  > [!WARNING]
  > **Important**
  >
  > Replace `<cluster domain>` with the actual value for your MinIO tenant. `cluster domain` is the internal root DNS domain assigned in your Kubernetes cluster. Typically, this is `cluster.local`, but confirm the value by checking your CoreDNS configuration for the correct value for your Kubernetes cluster.
  >
  > For example:
  >
  > ```shell
  > kubectl get configmap coredns -n kube-system -o jsonpath="{.data}"
  > ```
  >
  > Different Kubernetes providers manage the root domain differently. Check with your Kubernetes provider for more information.

1. Create a `Certificate` for the specified domains:

   Create a file named `sts-tls-certificate.yaml` with the following contents:

   ```yaml
   # sts-tls-certificate.yaml
   apiVersion: cert-manager.io/v1
   kind: Certificate
   metadata:
     name: sts-certmanager-cert
     namespace: minio-operator
   spec:
     dnsNames:
       - sts
       - sts.minio-operator.svc
       - sts.minio-operator.svc.cluster.local # Replace cluster.local with the value for your domain.
     secretName: sts-tls
     issuerRef:
       name: minio-operator-ca-issuer
   ```

   > [!WARNING]
   > **Important**
   >
   > The `spec.secretName` is not optional.
   >
   > The secret name **must** be `sts-tls`. Confirm this by setting `spec.secretName: sts-tls` as highlighted in the certificate YAML.
2. Apply the resource:

   ```shell
   kubectl apply -f sts-tls-certificate.yaml
   ```

This creates a secret called `sts-tls` in the `minio-operator` namespace.

> [!CAUTION]
> **Warning**
>
> The STS service will not start if the `sts-tls` secret, containing the TLS certificate, is missing or contains an invalid `key-value` pair.

## 4) Install Operator with Auto TLS disabled {#install-operator-with-auto-tls-disabled}

You can now [install the MinIO Operator](/operations/deployments/kubernetes/#minio-operator-installation).

When installing the Operator deployment, set the `OPERATOR_STS_AUTO_TLS_ENABLED` environment variable to `off` in the `minio-operator` container.

Disabling this environment variable prevents the MinIO Operator from issuing the certificates. Instead, Operator relies on cert-manager to issue the TLS certificate.

There are various methods to define an environment variable depending on how you install the Operator. The following steps define the variable with kustomize.

1. Create a kustomization patch file called `kustomization.yaml` with the following contents:

   ```yaml
   # minio-operator/kustomization.yaml
   apiVersion: kustomize.config.k8s.io/v1beta1
   kind: Kustomization

   resources:
   - github.com/minio/operator/resources

   patches:
   - patch: |-
       apiVersion: apps/v1
       kind: Deployment
       metadata:
         name: minio-operator
         namespace: minio-operator
       spec:
         template:
           spec:
             containers:
               - name: minio-operator
                 env:
                   - name: OPERATOR_STS_AUTO_TLS_ENABLED
                     value: "off"
                   - name: OPERATOR_STS_ENABLED
                     value: "on"
   ```

2. Apply the kustomization resource to the cluster:

   ```shell
   kubectl apply -k minio-operator
   ```

## Migrate an existing MinIO Operator deployment to cert-manager {#migrate-an-existing-minio-operator-deployment-to-cert-manager}

To transition an existing MinIO Operator deployment from using AutoCert to cert-manager, complete the following steps:

1. Complete the steps for [installing cert-manager](/operations/network-encryption/cert-manager/#minio-certmanager), including disabling auto-cert.
2. Complete steps 1-3 on this page to generate the certificate authority for the Operator.
3. When you get to the install step on this page, instead replace the existing Operator TLS certificate with the cert-manager issued certificate.
4. Create new cert-manager certificates for each tenant, similar to the steps described on the [cert-manager for Tenants](/operations/cert-manager/cert-manager-tenants/#minio-certmanager-tenants) page.
5. Replace the secrets in the MinIO Operator namespace for the tenants with secrets related to each tenant’s cert-manager issued certificate.

## Next steps {#next-steps}

Set up [cert-manager for a MinIO Tenant](/operations/cert-manager/cert-manager-tenants/#minio-certmanager-tenants).

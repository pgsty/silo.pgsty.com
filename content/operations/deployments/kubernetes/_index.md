---
title: "Deploy Silo on Kubernetes"
url: "/operations/deployments/kubernetes/"
weight: 10
icon: fa-solid fa-dharmachakra
minio_origin: true
silo_modified: true
---

<a id="deploy-minio-on-kubernetes"></a>
<a id="minio-operator-installation"></a>
<a id="deploy-operator-aks"></a>
<a id="deploy-operator-gke"></a>
<a id="deploy-operator-eks"></a>
<a id="deploy-operator-rancher"></a>
<a id="deploy-operator-openshift"></a>
<a id="deploy-operator-kubernetes"></a>
<a id="minio-kubernetes"></a>

Silo is an S3-compatible object storage server that can run in Kubernetes. The final upstream MinIO Kubernetes Operator release, `v7.1.1`, can deploy a `Tenant` with the Silo image when `tenant.image.repository` is overridden to `pgsty/minio` and a tested tag or digest is pinned.

These guides assume familiarity with the referenced Kubernetes concepts, utilities, and procedures. They are not a replacement for the official [Kubernetes Documentation](https://kubernetes.io/docs/), and the Silo project does not inherit the former MinIO vendor support matrix for Kubernetes distributions.

The MinIO Operator, its Helm charts, CRDs, and `Tenant` kind remain upstream contracts independent of Silo releases. The upstream `minio/operator` repository was archived and made read-only on 2026-03-20, so its release lifecycle is frozen and these guides are a compatibility snapshot.

The archived Operator code provides MinIO-compatible Tenant management and configuration. Validate the pinned Operator and chart against your cluster before deployment or upgrade; there is no ongoing upstream compatibility or support promise.

You can interact with the Operator through its [Custom Resource Definition (CRD)](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/#customresourcedefinitions).

The CRD provides a customizable entry point for tools such as Kustomize, Helm, and `kubectl` to deploy and manage Silo-backed Tenants.

{{% alert color="warning" %}}
**Important**

The MinIO Operator Console UI is deprecated and removed in MinIO Operator 6.0.0.

You can continue to use standard Kubernetes approaches for MinIO Tenant management, such as Kustomize templates, Helm Charts, and `kubectl` commands for introspecting Tenant namespaces and resources.
{{% /alert %}}

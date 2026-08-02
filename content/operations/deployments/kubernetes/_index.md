---
title: "Deploy MinIO on Kubernetes"
url: "/operations/deployments/kubernetes/"
weight: 10
icon: fa-solid fa-dharmachakra
minio_origin: true
silo_modified: false
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

MinIO is a Kubernetes-native high performance object store with an S3-compatible API. The MinIO Kubernetes Operator supports deploying MinIO Tenants onto private and public cloud infrastructures (“Hybrid” Cloud).

All documentation assumes familiarity with referenced Kubernetes concepts, utilities, and procedures. While MinIO documentation *may* provide guidance for configuring or deploying Kubernetes-related resources on a best-effort basis, it is not a replacement for the official [Kubernetes Documentation](https://kubernetes.io/docs/).

The MinIO Operator is a first-party Kubernetes-native operator that manages the deployment of MinIO Tenants onto Kubernetes infrastructure.

The Operator provides MinIO-centric functionality around Tenant management, including support for configuring all core MinIO features.

You can interact with the Operator through the MinIO [Custom Resource Definition (CRD)](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/#customresourcedefinitions), or through the Operator Console UI.

The CRD provides a highly customizable entry point for using tools like Kustomize for deploying Tenants. You can also use the MinIO Operator Console, a rich web-based UI that has complete support for deploying and configuring MinIO Tenants.

{{% alert color="warning" %}}
**Important**

The MinIO Operator Console UI is deprecated and removed in MinIO Operator 6.0.0.

You can continue to use standard Kubernetes approaches for MinIO Tenant management, such as Kustomize templates, Helm Charts, and `kubectl` commands for introspecting Tenant namespaces and resources.
{{% /alert %}}

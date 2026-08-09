---
title: "Deploy Operator With Helm"
url: "/operations/deployments/k8s-deploy-operator-helm-on-kubernetes/"
weight: 10
minio_origin: true
silo_modified: true
---

<a id="deploy-operator-with-helm"></a>
<a id="minio-k8s-deploy-operator-helm"></a>

## Overview {#overview}

Helm is a tool for automating the deployment of applications to Kubernetes clusters. A [Helm chart](https://helm.sh/docs/topics/charts/) is a set of YAML files, templates, and other files that define the deployment details. The following procedure uses a Helm Chart to install the [MinIO Kubernetes Operator](/operations/deployments/kubernetes/#minio-operator-installation) to a Kubernetes cluster.

{{% alert color="warning" %}}
The upstream MinIO Operator repository was archived on March 20, 2026. This procedure is pinned to its final release, `v7.1.1`, as a frozen compatibility baseline. It does not imply ongoing upstream maintenance or support; validate it against your Kubernetes platform before production use.
{{% /alert %}}

## Prerequisites {#prerequisites}

See the [Operator Prerequisites](/operations/deployments/k8s-minio-operator/#minio-operator-prerequisites) for a baseline of requirements. Helm installations have the following additional requirements:

- [Helm](https://helm.sh/docs/intro/install/) (Use the Version appropriate for your Kubernetes API version)
- [yq](https://github.com/mikefarah/yq/#install)

For more about Operator installation requirements, including supported Kubernetes versions and TLS certificates, see the [Operator deployment prerequisites](/operations/deployments/k8s-minio-operator/#minio-operator-prerequisites).

This procedure assumes familiarity with the referenced Kubernetes concepts and utilities. While this documentation may provide guidance for configuring or deploying Kubernetes-related resources on a best-effort basis, it is not a replacement for the official [Kubernetes Documentation](https://kubernetes.io/docs/).

<a id="minio-k8s-deploy-operator-helm-repo"></a>

## Install the MinIO Operator using Helm Charts {#install-the-minio-operator-using-helm-charts}

The following procedure installs the Operator using the MinIO Operator Chart Repository. This method supports a simplified installation path compared to the [local chart installation](#minio-k8s-deploy-operator-helm-local). You can modify the Operator deployment after installation.

{{% alert color="warning" %}}
**Important**

If you use Helm charts to install the Operator, you must use Helm to manage that installation. Do not use `kubectl krew`, Kustomize, or similar methods to update or manage the MinIO Operator installation.
{{% /alert %}}

1. Add the MinIO Operator Repo to Helm

   The archived project repository endpoint at [https://operator.min.io](https://operator.min.io) currently serves the `v7.1.1` charts. Add this repository to Helm:

   ```shell
   helm repo add minio-operator https://operator.min.io
   ```

   You can validate the repo contents using `helm search`:

   ```shell
   helm search repo minio-operator
   ```

   The response should resemble the following:

   ```shell
   NAME                            CHART VERSION   APP VERSION     DESCRIPTION
   minio-operator/minio-operator   4.3.7           v4.3.7          A Helm chart for MinIO Operator
   minio-operator/operator         7.1.1           v7.1.1          A Helm chart for MinIO Operator
   minio-operator/tenant           7.1.1           v7.1.1          A Helm chart for MinIO Operator
   ```

   The `minio-operator/minio-operator` is a legacy chart and should **not** be installed under normal circumstances.
2. Install the Operator

   Run the `helm install` command to install the Operator. The following command specifies and creates a dedicated namespace `minio-operator` for installation. MinIO strongly recommends using a dedicated namespace for the Operator.

   ```shell
   helm install \
     --namespace minio-operator \
     --create-namespace \
     --version 7.1.1 \
     operator minio-operator/operator
   ```

3. Verify the Operator installation

   Check the contents of the specified namespace (`minio-operator`) to ensure all pods and services have started successfully.

   ```shell
   kubectl get all -n minio-operator
   ```

   The response should resemble the following:

   ```shell
   NAME                                  READY   STATUS    RESTARTS   AGE
   pod/minio-operator-699f797b8b-th5bk   1/1     Running   0          25h
   pod/minio-operator-699f797b8b-nkrn9   1/1     Running   0          25h

   NAME               TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)             AGE
   service/operator   ClusterIP   10.43.44.204    <none>        4221/TCP            25h
   service/sts        ClusterIP   10.43.70.4      <none>        4223/TCP            25h

   NAME                             READY   UP-TO-DATE   AVAILABLE   AGE
   deployment.apps/minio-operator   2/2     2            2           25h

   NAME                                        DESIRED   CURRENT   READY   AGE
   replicaset.apps/minio-operator-79f7bfc48    2         2         2       123m
   ```

You can now [deploy a tenant using Helm Charts](/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/#deploy-tenant-helm).

<a id="minio-k8s-deploy-operator-helm-local"></a>

## Install the MinIO Operator using Local Helm Charts {#install-the-minio-operator-using-local-helm-charts}

The following procedure installs the Operator using a local copy of the Helm Charts. This method may support easier pre-configuration of the Operator compared to the [repo-based installation](#minio-k8s-deploy-operator-helm-repo)

1. Download the Helm charts

   On your local host, download the Operator Helm charts to a convenient directory:

   ```shell
   curl -O https://operator.min.io/helm-releases/operator-7.1.1.tgz
   ```

2. (Optional) Modify the `values.yaml`

   The chart contains a `values.yaml` file you can customize to suit your needs. For details on the options available in the MinIO Operator `values.yaml`, see [Operator Helm Charts](/reference/operator-chart-values/#minio-operator-chart-values).

   For example, you can change the number of replicas for `operator.replicaCount` to increase or decrease pod availability in the deployment. See [Operator Helm Charts](/reference/operator-chart-values/#minio-operator-chart-values) for more complete documentation on the Operator Helm Chart and Values.

   For more about customizations, see [Helm Charts](https://helm.sh/docs/topics/charts/).
3. Install the Helm Chart

   Use the `helm install` command to install the downloaded chart archive.

   ```shell
   helm install \
   --namespace minio-operator \
   --create-namespace \
   minio-operator ./operator-7.1.1.tgz
   ```

4. To verify the installation, run the following command:

   ```shell
   kubectl get all --namespace minio-operator
   ```

   If you initialized the Operator with a custom namespace, replace `minio-operator` with that namespace.

   With the chart defaults, the namespace should contain a `minio-operator` Deployment with two ready replicas, an `operator` ClusterIP service on port `4221`, and an `sts` ClusterIP service on port `4223`. Pod hashes, cluster IPs, and ages vary by installation.

You can now [deploy a tenant using Helm Charts](/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/#deploy-tenant-helm).

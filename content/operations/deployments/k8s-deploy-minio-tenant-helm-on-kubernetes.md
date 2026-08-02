---
title: "Deploy a MinIO Tenant with Helm Charts"
url: "/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="deploy-a-minio-tenant-with-helm-charts"></a>
<a id="deploy-tenant-helm"></a>

## Overview {#overview}

Helm is a tool for automating the deployment of applications to Kubernetes clusters. A [Helm chart](https://helm.sh/docs/topics/charts/) is a set of YAML files, templates, and other files that define the deployment details. The following procedure uses a Helm Chart to deploy a Tenant managed by the MinIO Operator.

This procedure requires the Kubernetes cluster have a valid [Operator](/operations/deployments/kubernetes/#deploy-operator-kubernetes) deployment. You cannot use the MinIO Operator Tenant chart to deploy a Tenant independent of the Operator.

{{% alert color="warning" %}}
**Important**

The MinIO Operator Tenant Chart is *distinct* from the community-managed [MinIO Chart](https://github.com/minio/minio/tree/master/helm/minio).

The Community Helm Chart is built, maintained, and supported by the community. MinIO does not guarantee support for any given bug, feature request, or update referencing that chart.

The [Operator Tenant Chart](/reference/tenant-chart-values/#minio-tenant-chart-values) is officially maintained and supported by MinIO. MinIO strongly recommends the official Helm Chart for [Operator](/reference/operator-chart-values/#minio-operator-chart-values) and [Tenants](/reference/tenant-chart-values/#minio-tenant-chart-values) for production environments.
{{% /alert %}}

## Prerequisites {#prerequisites}

You must meet the following requirements to install a MinIO Tenant with Helm:

- An existing Kubernetes cluster
- The `kubectl` CLI tool on your local host with version matching the cluster.
- [Helm](https://helm.sh/docs/intro/install/) version 3.8 or greater.
- [yq](https://github.com/mikefarah/yq/#install) version 4.18.1 or greater.
- An existing [MinIO Operator installation](/operations/deployments/kubernetes/#deploy-operator-kubernetes).

This procedure assumes your Kubernetes cluster access grants you broad administrative permissions.

For more about Tenant installation requirements, including supported Kubernetes versions and TLS certificates, see the [Tenant deployment prerequisites](/operations/checklists/hardware/#minio-hardware-checklist-storage).

This procedure assumes familiarity the with referenced Kubernetes concepts and utilities. While this documentation may provide guidance for configuring or deploying Kubernetes-related resources on a best-effort basis, it is not a replacement for the official [Kubernetes Documentation](https://kubernetes.io/docs/).

### Namespace {#namespace}

The tenant must use its own namespace and cannot share a namespace with another tenant. In addition, MinIO strongly recommends using a dedicated namespace for the tenant with no other applications running in the namespace.

<a id="deploy-tenant-helm-repo"></a>

## Deploy a MinIO Tenant using Helm Charts {#deploy-a-minio-tenant-using-helm-charts}

The following procedure deploys a MinIO Tenant using the MinIO Operator Chart Repository. This method supports a simplified installation path compared to the [local chart installation](#deploy-tenant-helm-local).

The following procedure uses Helm to deploy a MinIO Tenant using the official MinIO Tenant Chart.

{{% alert color="warning" %}}
**Important**

If you use Helm to deploy a MinIO Tenant, you must use Helm to manage or upgrade that deployment. Do not use `kubectl krew`, Kustomize, or similar methods to manage or upgrade the MinIO Tenant.
{{% /alert %}}

This procedure is not exhaustive of all possible configuration options available in the [Tenant Chart](/reference/tenant-chart-values/#minio-tenant-chart-values). It provides a baseline from which you can modify and tailor the Tenant to your requirements.

1. Verify your MinIO Operator Repo Configuration

   MinIO maintains a Helm-compatible repository at [https://operator.min.io](https://operator.min.io). If the repository does not already exist in your local Helm configuration, add it before continuing:

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
2. Create a local copy of the Helm `values.yaml` for modification

   ```shell
   curl -sLo values.yaml https://raw.githubusercontent.com/minio/operator/master/helm/tenant/values.yaml
   ```

   Open the `values.yaml` object in your preferred text editor.
3. Configure the Tenant topology

   The following fields share the `tenant.pools[0]` prefix and control the number of servers, volumes per server, and storage class of all pods deployed in the Tenant:

   <table>
     <thead>
       <tr>
         <th><p>Field</p></th>
         <th><p>Description</p></th>
       </tr>
     </thead>
     <tbody>
       <tr>
         <td><p><code>servers</code></p></td>
         <td><p>The number of MinIO pods to deploy in the Server Pool.</p></td>
       </tr>
       <tr>
         <td><p><code>volumesPerServer</code></p></td>
         <td><p>The number of persistent volumes to attach to each MinIO pod (<code>servers</code>).
   The Operator generates <code>volumesPerServer x servers</code> Persistant Volume Claims for the Tenant.</p></td>
       </tr>
       <tr>
         <td><p><code>storageClassName</code></p></td>
         <td><p>The Kubernetes storage class to associate with the generated Persistent Volume Claims.</p><p>If no storage class exists matching the specified value <em>or</em> if the specified storage class cannot meet the requested number of PVCs or storage capacity, the Tenant may fail to start.</p></td>
       </tr>
       <tr>
         <td><p><code>size</code></p></td>
         <td><p>The amount of storage to request for each generated PVC.</p></td>
       </tr>
     </tbody>
   </table>
4. Configure Tenant Affinity or Anti-Affinity

   The Tenant Chart supports the following Kubernetes Selector, Affinity and Anti-Affinity configurations:

   - Node Selector (`tenant.nodeSelector`)
   - Node/Pod Affinity or Anti-Affinity (`spec.pools[n].affinity`)

   MinIO recommends configuring Tenants with Pod Anti-Affinity to ensure that the Kubernetes schedule does not schedule multiple pods on the same worker node.

   If you have specific worker nodes on which you want to deploy the tenant, pass those node labels or filters to the `nodeSelector` or `affinity` field to constrain the scheduler to place pods on those nodes.
5. Configure Network Encryption

   The MinIO Tenant CRD provides the following fields with which you can configure tenant TLS network encryption:

   <table>
     <thead>
       <tr>
         <th><p>Field</p></th>
         <th><p>Description</p></th>
       </tr>
     </thead>
     <tbody>
       <tr>
         <td><p><code>tenant.certificate.requestAutoCert</code></p></td>
         <td><p>Enable or disable MinIO <a href="/operations/network-encryption/#minio-tls">automatic TLS certificate generation</a>.</p><p>Defaults to <code>true</code> or enabled if omitted.</p></td>
       </tr>
       <tr>
         <td><p><code>tenant.certificate.certConfig</code></p></td>
         <td><p>Customize the behavior of <a href="/operations/network-encryption/#minio-tls">automatic TLS</a>, if enabled.</p></td>
       </tr>
       <tr>
         <td><p><code>tenant.certificate.externalCertSecret</code></p></td>
         <td><p>Enable TLS for multiple hostnames via Server Name Indication (SNI).</p><p>Specify one or more Kubernetes secrets of type <code>kubernetes.io/tls</code> or <code>cert-manager</code>.</p></td>
       </tr>
       <tr>
         <td><p><code>tenant.certificate.externalCACertSecret</code></p></td>
         <td><p>Enable validation of client TLS certificates signed by unknown, third-party, or internal Certificate Authorities (CA).</p><p>Specify one or more Kubernetes secrets of type <code>kubernetes.io/tls</code> containing the full chain of CA certificates for a given authority.</p></td>
       </tr>
     </tbody>
   </table>
6. Configure MinIO Environment Variables

   You can set MinIO Server environment variables using the `tenant.configuration` field.

   <table>
     <thead>
       <tr>
         <th><p>Field</p></th>
         <th><p>Description</p></th>
       </tr>
     </thead>
     <tbody>
       <tr>
         <td><p><code>tenant.configuration</code></p></td>
         <td><p>Specify a Kubernetes opaque secret whose data payload <code>config.env</code> contains each MinIO environment variable you want to set.</p><p>The <code>config.env</code> data payload <strong>must</strong> be a base64-encoded string.
   You can create a local file, set your environment variables, and then use <code>cat LOCALFILE | base64</code> to create the payload.</p></td>
       </tr>
     </tbody>
   </table>

   The YAML includes an object `kind: Secret` with `metadata.name: storage-configuration` that sets the root username, password, erasure parity settings, and enables Tenant Console.

   Modify this as needed to reflect your Tenant requirements.
7. Deploy the Tenant

   Use `helm` to install the Tenant Chart using your `values.yaml` as an override:

   ```shell
   helm install \
   --namespace TENANT-NAMESPACE \
   --create-namespace \
   --values values.yaml \
   TENANT-NAME minio-operator/tenant
   ```

   You can monitor the progress using the following command:

   ```shell
   watch kubectl get all -n TENANT-NAMESPACE
   ```
8. Expose the Tenant MinIO S3 API port

   To test the MinIO Client [`mc`](/reference/minio-mc/#command-mc) from your local machine, forward the MinIO port and create an alias.

   - Forward the Tenant’s MinIO port:

   ```shell
   kubectl port-forward svc/TENANT-NAME-hl 9000 -n TENANT-NAMESPACE
   ```

   - Create an alias for the Tenant service:

   ```shell
   mc alias set myminio https://localhost:9000 minio minio123 --insecure
   ```

   You can use [`mc mb`](/reference/minio-mc/mc-mb/#command-mc.mb) to create a bucket on the Tenant:

   ```shell
   mc mb myminio/mybucket --insecure
   ```

   If you deployed your MinIO Tenant using TLS certificates minted by a trusted Certificate Authority (CA) you can omit the `--insecure` flag.

   See [Connect to the Tenant](/operations/deployments/k8s-deploy-minio-tenant-on-kubernetes/#create-tenant-connect-tenant) for additional documentation on external connectivity to the Tenant.

<a id="deploy-tenant-helm-local"></a>

## Deploy a Tenant using a Local Helm Chart {#deploy-a-tenant-using-a-local-helm-chart}

The following procedure deploys a Tenant using a local copy of the Helm Charts. This method may support easier pre-configuration of the Tenant compared to the [repo-based installation](#deploy-tenant-helm-repo).

1. Download the Helm charts

   On your local host, download the Tenant Helm charts to a convenient directory:

   ```shell
   curl -O https://raw.githubusercontent.com/minio/operator/master/helm-releases/tenant-7.1.1.tgz
   ```

   Each chart contains a `values.yaml` file you can customize to suit your needs. For details on the options available in the MinIO Tenant `values.yaml`, see [Tenant Helm Charts](/reference/tenant-chart-values/#minio-tenant-chart-values).

   Open the `values.yaml` object in your preferred text editor.
2. Configure the Tenant topology

   The following fields share the `tenant.pools[0]` prefix and control the number of servers, volumes per server, and storage class of all pods deployed in the Tenant:

   <table>
     <thead>
       <tr>
         <th><p>Field</p></th>
         <th><p>Description</p></th>
       </tr>
     </thead>
     <tbody>
       <tr>
         <td><p><code>servers</code></p></td>
         <td><p>The number of MinIO pods to deploy in the Server Pool.</p></td>
       </tr>
       <tr>
         <td><p><code>volumesPerServer</code></p></td>
         <td><p>The number of persistent volumes to attach to each MinIO pod (<code>servers</code>).
   The Operator generates <code>volumesPerServer x servers</code> Persistant Volume Claims for the Tenant.</p></td>
       </tr>
       <tr>
         <td><p><code>storageClassName</code></p></td>
         <td><p>The Kubernetes storage class to associate with the generated Persistent Volume Claims.</p><p>If no storage class exists matching the specified value <em>or</em> if the specified storage class cannot meet the requested number of PVCs or storage capacity, the Tenant may fail to start.</p></td>
       </tr>
       <tr>
         <td><p><code>size</code></p></td>
         <td><p>The amount of storage to request for each generated PVC.</p></td>
       </tr>
     </tbody>
   </table>
3. Configure Tenant Affinity or Anti-Affinity

   The Tenant Chart supports the following Kubernetes Selector, Affinity and Anti-Affinity configurations:

   - Node Selector (`tenant.nodeSelector`)
   - Node/Pod Affinity or Anti-Affinity (`spec.pools[n].affinity`)

   MinIO recommends configuring Tenants with Pod Anti-Affinity to ensure that the Kubernetes schedule does not schedule multiple pods on the same worker node.

   If you have specific worker nodes on which you want to deploy the tenant, pass those node labels or filters to the `nodeSelector` or `affinity` field to constrain the scheduler to place pods on those nodes.
4. Configure Network Encryption

   The MinIO Tenant CRD provides the following fields from which you can configure tenant TLS network encryption:

   | Field | Description |
   | --- | --- |
   | `tenant.certificate.requestAutoCert` | Enables or disables MinIO [automatic TLS certificate generation](/operations/network-encryption/#minio-tls) |
   | `tenant.certificate.certConfig` | Controls the settings for [automatic TLS](/operations/network-encryption/#minio-tls). Requires `spec.requestAutoCert: true` |
   | `tenant.certificate.externalCertSecret` | Specify one or more Kubernetes secrets of type `kubernetes.io/tls` or `cert-manager`. MinIO uses these certificates for performing TLS handshakes based on hostname (Server Name Indication). |
   | `tenant.certificate.externalCACertSecret` | Specify one or more Kubernetes secrets of type `kubernetes.io/tls` with the Certificate Authority (CA) chains which the Tenant must trust for allowing client TLS connections. |
5. Configure MinIO Environment Variables

   You can set MinIO Server environment variables using the `tenant.configuration` field.

   The field must specify a Kubernetes opaque secret whose data payload `config.env` contains each MinIO environment variable you want to set.

   The YAML includes an object `kind: Secret` with `metadata.name: storage-configuration` that sets the root username, password, erasure parity settings, and enables Tenant Console.

   Modify this as needed to reflect your Tenant requirements.
6. The following Helm command creates a MinIO Tenant using the standard chart:

   ```shell
   helm install \
   --namespace TENANT-NAMESPACE \
   --create-namespace \
   TENANT-NAME tenant-7.1.1.tgz
   ```

   To deploy more than one Tenant, create a Helm chart with the details of the new Tenant and repeat the deployment steps. Redeploying the same chart updates the previously deployed Tenant.
7. Expose the Tenant MinIO port

   To test the MinIO Client [`mc`](/reference/minio-mc/#command-mc) from your local machine, forward the MinIO port and create an alias.

   - Forward the Tenant’s MinIO port:

     ```shell
     kubectl port-forward svc/TENANT-NAME-hl 9000 -n TENANT-NAMESPACE
     ```
   - Create an alias for the Tenant service:

     ```shell
     mc alias set myminio https://localhost:9000 minio minio123 --insecure
     ```

     This example uses the non-TLS `myminio-hl` service, which requires the `--insecure` option..

     If you have a TLS cert configured, omit `--insecure` and use `svc/minio` instead.

   You can use [`mc mb`](/reference/minio-mc/mc-mb/#command-mc.mb) to create a bucket on the Tenant:

   > ```shell
   > mc mb myminio/mybucket --insecure
   > ```

See [Connect to the Tenant](/operations/deployments/k8s-deploy-minio-tenant-on-kubernetes/#create-tenant-connect-tenant) for additional documentation on external connectivity to the Tenant.

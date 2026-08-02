---
title: "Deploy a MinIO Tenant"
url: "/operations/deployments/k8s-deploy-minio-tenant-on-kubernetes/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="deploy-a-minio-tenant"></a>
<a id="deploy-minio-tenant-redhat-openshift"></a>
<a id="minio-k8s-deploy-minio-tenant"></a>

This procedure documents deploying a MinIO Tenant using the MinIO Operator.

Deploying Single-Node topologies requires additional configurations not covered in this documentation. You can alternatively use a simple Kubernetes YAML object to describe a Single-Node topology for local testing and evaluation as necessary. MinIO does not recommend nor support single-node deployment topologies for production environments.

This documentation assumes familiarity with all referenced Kubernetes concepts, utilities, and procedures. While this documentation *may* provide guidance for configuring or deploying Kubernetes-related resources on a best-effort basis, it is not a replacement for the official [Kubernetes Documentation](https://kubernetes.io/docs/).

<a id="minio-k8s-deploy-minio-tenant-security"></a>

## Deploy a MinIO Tenant using Kustomize {#deploy-a-minio-tenant-using-kustomize}

The following procedure uses `kubectl -k` to deploy a MinIO Tenant using the `base` Kustomization template in the [MinIO Operator Github repository](https://github.com/minio/operator/tree/master/examples/kustomization/base).

You can select a different base or pre-built template from the [repository](https://github.com/minio/operator/tree/master/examples/kustomization/) as your starting point, or build your own Kustomization resources using the [MinIO Custom Resource Documentation](/reference/operator-crd/#minio-operator-crd).

{{% alert color="warning" %}}
**Important**

If you use Kustomize to deploy a MinIO Tenant, you must use Kustomize to manage or upgrade that deployment. Do not use `kubectl krew`, a Helm Chart, or similar methods to manage or upgrade the MinIO Tenant.
{{% /alert %}}

This procedure is not exhaustive of all possible configuration options available in the [Tenant CRD](/reference/operator-crd/#minio-operator-crd). It provides a baseline from which you can modify and tailor the Tenant to your requirements.

1. Create a YAML object for the Tenant

   Use the `kubectl kustomize` command to produce a YAML file containing all Kubernetes resources necessary to deploy the `base` Tenant:

   ```shell
   kubectl kustomize https://github.com/minio/operator/examples/kustomization/base/ > tenant-base.yaml
   ```

   The command creates a single YAML file with multiple objects separated by the `---` line. Open the file in your preferred editor.

   The following steps reference each object based on it’s `kind` and `metadata.name` fields:
2. Configure the Tenant topology

   The `kind: Tenant` object describes the MinIO Tenant.

   The following fields share the `spec.pools[0]` prefix and control the number of servers, volumes per server, and storage class of all pods deployed in the Tenant:

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
         <td><p><code>volumeClaimTemplate.spec.storageClassName</code></p></td>
         <td><p>The Kubernetes storage class to associate with the generated Persistent Volume Claims.</p><p>If no storage class exists matching the specified value <em>or</em> if the specified storage class cannot meet the requested number of PVCs or storage capacity, the Tenant may fail to start.</p></td>
       </tr>
       <tr>
         <td><p><code>volumeClaimTemplate.spec.resources.requests.storage</code></p></td>
         <td><p>The amount of storage to request for each generated PVC.</p></td>
       </tr>
     </tbody>
   </table>
3. Configure Tenant Affinity or Anti-Affinity

   The MinIO Operator supports the following Kubernetes Affinity and Anti-Affinity configurations:

   - Node Affinity (`spec.pools[n].nodeAffinity`)
   - Pod Affinity (`spec.pools[n].podAffinity`)
   - Pod Anti-Affinity (`spec.pools[n].podAntiAffinity`)

   MinIO recommends configuring Tenants with Pod Anti-Affinity to ensure that the Kubernetes schedule does not schedule multiple pods on the same worker node.

   If you have specific worker nodes on which you want to deploy the tenant, pass those node labels or filters to the `nodeAffinity` field to constrain the scheduler to place pods on those nodes.
4. Configure Network Encryption

   The MinIO Tenant CRD provides the following fields from which you can configure tenant TLS network encryption:

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
         <td><p>Enable or disable MinIO <a href="/operations/network-encryption/#minio-tls">automatic TLS certificate generation</a></p><p>Defaults to <code>true</code> or enabled if omitted.</p></td>
       </tr>
       <tr>
         <td><p><code>tenant.certificate.certConfig</code></p></td>
         <td><p>Customize the behavior of <a href="/operations/network-encryption/#minio-tls">automatic TLS</a>, if enabled.</p></td>
       </tr>
       <tr>
         <td><p><code>tenant.certificate.externalCertSecret</code></p></td>
         <td><p>Enable TLS for multiple hostnames via Server Name Indication (SNI)</p><p>Specify one or more Kubernetes secrets of type <code>kubernetes.io/tls</code> or <code>cert-manager</code>.</p></td>
       </tr>
       <tr>
         <td><p><code>tenant.certificate.externalCACertSecret</code></p></td>
         <td><p>Enable validation of client TLS certificates signed by unknown, third-party, or internal Certificate Authorities (CA).</p><p>Specify one or more Kubernetes secrets of type <code>kubernetes.io/tls</code> containing the full chain of CA certificates for a given authority.</p></td>
       </tr>
     </tbody>
   </table>
5. Configure MinIO Environment Variables

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
6. Review the Namespace

   The YAML object `kind: Namespace` sets the default namespace for the Tenant to `minio-tenant`.

   You can change this value to create a different namespace for the Tenant. You must change **all** `metadata.namespace` values in the YAML file to match the Namespace.
7. Deploy the Tenant

   Use the `kubectl apply -f` command to deploy the Tenant.

   ```shell
   kubectl apply -f tenant-base.yaml
   ```

   The command creates each of the resources specified in the YAML object at the configured namespace.

   You can monitor the progress using the following command:

   ```shell
   watch kubectl get all -n minio-tenant
   ```
8. Expose the Tenant MinIO S3 API port

   To test the MinIO Client [`mc`](/reference/minio-mc/#command-mc) from your local machine, forward the MinIO port and create an alias.

   - Forward the Tenant’s MinIO port:

   ```shell
   kubectl port-forward svc/MINIO_TENANT_NAME-hl 9000 -n MINIO_TENANT_NAMESPACE
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

   See [Connect to the Tenant](#create-tenant-connect-tenant) for specific instructions.

<a id="create-tenant-connect-tenant"></a>

## Connect to the Tenant {#connect-to-the-tenant}

The MinIO Operator creates services for the MinIO Tenant.

Use the `kubectl get svc -n NAMESPACE` command to review the deployed services. For Kubernetes services which use a custom `kubectl` analog, you can substitute the name of that program.

```shell
kubectl get svc -n minio-tenant-1
```

```shell
NAME                               TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)          AGE
minio                              LoadBalancer   10.97.114.60     <pending>     443:30979/TCP    2d3h
TENANT-NAMESPACE-console           LoadBalancer   10.106.103.247   <pending>     9443:32095/TCP   2d3h
TENANT-NAMESPACE-hl                ClusterIP      None             <none>        9000/TCP         2d3h
```

- The `minio` service corresponds to the MinIO Tenant service. Applications should use this service for performing operations against the MinIO Tenant.
- The `*-console` service corresponds to the [MinIO Console](https://github.com/minio/console). Administrators should use this service for accessing the MinIO Console and performing administrative operations on the MinIO Tenant.

The remaining services support Tenant operations and are not intended for consumption by users or administrators.

By default each service is visible only within the Kubernetes cluster. Applications deployed inside the cluster can access the services using the `CLUSTER-IP`.

Applications external to the Kubernetes cluster can access the services using the `EXTERNAL-IP`. This value is only populated for Kubernetes clusters configured for Ingress or a similar network access service. Kubernetes provides multiple options for configuring external access to services.

See the Kubernetes documentation on [Publishing Services (ServiceTypes)](https://kubernetes.io/docs/concepts/services-networking/service/#publishing-services-service-types) and [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/) for more complete information on configuring external access to services.

For specific flavors of Kubernetes, such as OpenShift or Rancher, defer to the service documentation on the preferred or available methods of exposing Services to internal or external access.

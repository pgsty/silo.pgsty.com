---
title: "Expand a Silo Tenant"
url: "/operations/deployments/k8s-expand-minio-tenant-on-kubernetes/"
weight: 50
minio_origin: true
silo_modified: true
---

<a id="expand-a-minio-tenant"></a>
<a id="minio-k8s-expand-minio-tenant"></a>

This procedure documents expanding the available storage capacity of an existing MinIO tenant by deploying an additional pool of MinIO pods in the Kubernetes infrastructure.

{{% alert color="warning" %}}
**Important**

The MinIO Operator Console is deprecated and removed in Operator 6.0.0.

See [Modify a MinIO Tenant](/operations/deployments/k8s-modify-minio-tenant-on-kubernetes/#minio-k8s-modify-minio-tenant) for instructions on migrating Tenants installed via the Operator Console to Kustomization.
{{% /alert %}}

## Prerequisites {#prerequisites}

### MinIO Kubernetes Operator {#minio-kubernetes-operator}

This procedure *requires* a valid installation of the MinIO Kubernetes Operator and assumes the local host has a matching Operator installation. It uses `v7.1.1`, the final upstream release before the repository was archived, as a frozen compatibility baseline.

See [Deploy MinIO on Kubernetes](/operations/deployments/kubernetes/#deploy-operator-kubernetes) for complete documentation on deploying the MinIO Operator.

### Available Worker Nodes {#available-worker-nodes}

MinIO deploys additional [`minio server`](/reference/minio-server/#command-minio.server) pods as part of the new Tenant pool. The Kubernetes cluster *must* have sufficient available worker nodes on which to schedule the new pods.

The MinIO Operator provides configurations for controlling pod affinity and anti-affinity to direct scheduling to specific workers.

### Persistent Volumes {#persistent-volumes}

{{% alert color="info" %}}
**Exclusive access to drives**

MinIO **requires** *exclusive* access to the drives or volumes provided for object storage. No other processes, software, scripts, or persons should perform *any* actions directly on the drives or volumes provided to MinIO or the objects or files MinIO places on them.

Unless directed by MinIO Engineering, do not use scripts or tools to directly modify, delete, or move any of the data shards, parity shards, or metadata files on the provided drives, including from one drive or node to another. Such operations are very likely to result in widespread corruption and data loss beyond MinIO’s ability to heal.
{{% /alert %}}

MinIO can use any Kubernetes [Persistent Volume (PV)](https://kubernetes.io/docs/concepts/storage/persistent-volumes) that supports the [ReadWriteOnce](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes) access mode. MinIO’s consistency guarantees require the exclusive storage access that `ReadWriteOnce` provides.

For Kubernetes clusters where nodes have Direct Attached Storage, MinIO strongly recommends using the [DirectPV CSI driver](https://min.io/directpv?ref=docs). DirectPV provides a distributed persistent volume manager that can discover, format, mount, schedule, and monitor drives across Kubernetes nodes. DirectPV addresses the limitations of manually provisioning and monitoring [local persistent volumes](https://kubernetes.io/docs/concepts/storage/volumes/#local).

{{% alert color="info" %}}
**Note**

MinIO Tenants on EKS must use the [EBS CSI Driver](https://github.com/kubernetes-sigs/aws-ebs-csi-driver) to provision the necessary underlying persistent volumes. MinIO strongly recommends using SSD-backed EBS volumes for best performance. For more information on EBS resources, see [EBS Volume Types](https://aws.amazon.com/ebs/volume-types/).
{{% /alert %}}

## Procedure {#procedure}

The MinIO Operator supports expanding a MinIO Tenant by adding additional pools.

{{< tabpane text=true persist=header >}}
{{% tab header="Kustomization" %}}
1. Review the Kustomization object which describes the Tenant object (`tenant.yaml`).

   The `spec.pools` array describes the current pool topology.
2. Add a new entry to the `spec.pools` array.

   The new pool must reflect your intended combination of Worker nodes, volumes per server, storage class, and affinity/scheduler settings. See [MinIO Custom Resource Definition](/reference/operator-crd/#minio-operator-crd) for more complete documentation on Pool-related configuration settings.
3. Apply the updated Tenant configuration

   Use the `kubectl apply` command to update the Tenant:

   ```shell
   kubectl apply -k ~/kustomization/TENANT-NAME
   ```

   Modify the path to the Kustomization directory to match your local configuration.
{{% /tab %}}
{{% tab header="Helm" %}}
1. Review the Helm `values.yaml` file.

   The `tenant.pools` array describes the current pool topology.
2. Add a new entry to the `tenant.pools` array.

   The new pool must reflect your intended combination of Worker nodes, volumes per server, storage class, and affinity/scheduler settings. See [Tenant Helm Charts](/reference/tenant-chart-values/#minio-tenant-chart-values) for more complete documentation on Pool-related configuration settings.
3. Apply the updated Tenant configuration

   Use the `helm upgrade` command to update the Tenant:

   ```shell
   helm upgrade TENANT-NAME minio-operator/tenant -f values.yaml -n TENANT-NAMESPACE
   ```

   The command above assumes use of the MinIO Operator Chart repository. If you installed the Chart manually or by using a different repository name, specify that chart or name in the command.

   Replace `TENANT-NAME` and `TENANT-NAMESPACE` with the name and namespace of the Tenant respectively. You can use `helm list -n TENANT-NAMESPACE` to validate the Tenant name.
{{% /tab %}}
{{< /tabpane >}}

You can use the `kubectl get events -n TENANT-NAMESPACE --watch` to monitor the progress of expansion. The MinIO Operator updates services to route connections appropriately across the new nodes. If you use customized services, routes, ingress, or similar Kubernetes network components, you may need to update those components for the new pod hostname ranges.

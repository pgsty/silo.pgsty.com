---
title: "Modify a Silo Tenant"
url: "/operations/deployments/k8s-modify-minio-tenant-on-kubernetes/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/deployments/k8s-modify-minio-tenant-on-kubernetes.rst
upstream_modified: true
---

<a id="modify-a-minio-tenant"></a>
<a id="minio-k8s-modify-minio-tenant-security"></a>
<a id="minio-k8s-modify-minio-tenant"></a>

You can modify tenants after deployment to change mutable configuration settings. See [MinIO Custom Resource Definition](/reference/operator-crd/#minio-operator-crd) for a complete description of available settings in the MinIO Custom Resource Definition.

The method for modifying the Tenant depends on how you deployed the tenant:

{{< tabs group="kustomize-helm" >}}
{{< tab label="Kustomize" value="kustomize" >}}
For Kustomize-deployed Tenants, you can modify the base Kustomization resources and apply them using `kubectl apply -k` against the directory containing the `kustomization.yaml` object.

```shell
kubectl apply -k ~/kustomization/TENANT-NAME/
```

Modify the path to the Kustomization directory to match your local configuration.
{{< /tab >}}
{{< tab label="Helm" value="helm" >}}
For Helm-deployed Tenants, you can modify the base `values.yaml` and upgrade the Tenant using the chart:

```shell
helm upgrade TENANT-NAME minio-operator/tenant -f values.yaml -n TENANT-NAMESPACE
```

The command above assumes use of the MinIO Operator Chart repository. If you installed the Chart manually or by using a different repository name, specify that chart or name in the command.

Replace `TENANT-NAME` and `TENANT-NAMESPACE` with the name and namespace of the Tenant, respectively. You can use `helm list -n TENANT-NAMESPACE` to validate the Tenant name.
{{< /tab >}}
{{< /tabs >}}

**Add Trusted Certificate Authorities**

> The MinIO Tenant validates the TLS certificate presented by each connecting client against the host system’s trusted root certificate store. The MinIO Operator can attach additional third-party Certificate Authorities (CA) to the Tenant to allow validation of client TLS certificates signed by those CAs.
>
> To customize the trusted CAs mounted to each Tenant MinIO pod, enable the **Custom Certificates** switch. Select the **Add CA Certificate +** button to add third party CA certificates.
>
> If the MinIO Tenant cannot match an incoming client’s TLS certificate issuer against either the container OS’s trust store *or* an explicitly attached CA, MinIO rejects the connection as invalid.

## Manage Tenant Pools {#manage-tenant-pools}

### Specify Runtime Class {#specify-runtime-class}

> [!NOTE]
> **Added: Console**
>
> 0.23.1

When adding a new pool or modifying an existing pool for a tenant, you can specify the [Runtime Class Name](https://kubernetes.io/docs/concepts/containers/runtime-class/) for pools to use.

### Decommission a Tenant Server Pool {#decommission-a-tenant-server-pool}

MinIO Operator 4.4.13 and later support decommissioning a server pool in a Tenant. Specifically, you can follow the [Decommission a Server pool](https://silo.pgsty.com/operations/deployments/baremetal-decommission-server-pool/) procedure to remove the pool from the tenant, then edit the tenant YAML to drop the pool from the StatefulSet. When removing the Tenant pool, ensure the `spec.pools.[n].name` fields have values for all remaining pools.

> [!NOTE]
> **Maintain pool order when decommissioning and then adding**
>
> If you decommission one pool in a multiple pool deployment, you cannot use the same node sequence for a new pool. For example, consider a deployment with the following pools:
>
> ```text
> https://minio-{1...4}.example.net/mnt/drive-{1...4}
> https://minio-{5...8}.example.net/mnt/drive-{1...4}
> https://minio-{9...12}.example.net/mnt/drive-{1...4}
> ```
>
> If you decommission the `minio-{5...8}` pool, you cannot add a new pool with the same node numbering. You must add the new pool *after* `minio-{9...12}`:
>
> ```text
> https://minio-{1...4}.example.net/mnt/drive-{1...4}
> https://minio-{9...12}.example.net/mnt/drive-{1...4}
> https://minio-{13...16}.example.net/mnt/drive-{1...4}
> ```

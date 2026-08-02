---
title: "Upgrade a MinIO Tenant"
url: "/operations/deployments/k8s-upgrade-minio-tenant-on-kubernetes/"
weight: 40
minio_origin: true
silo_modified: false
---

<a id="upgrade-a-minio-tenant"></a>
<a id="minio-k8s-upgrade-minio-tenant"></a>

The following procedures upgrade a single MinIO Tenant, using either Kustomize or Helm. MinIO recommends you test upgrades in a lower environment such as a Dev or QA Tenant, before upgrading production Tenants.

{{% alert color="warning" %}}
**Important**

For Tenants using a MinIO Image older than [RELEASE.2024-03-30T09-41-56Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-03-30T09-41-56Z) running with [AD/LDAP](/reference/minio-server/settings/iam/ldap/#minio-ldap-config-settings) enabled, you **must** read through the release notes for [RELEASE.2024-04-18T19-09-19Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-04-18T19-09-19Z) before starting this procedure. You must take the extra steps documented in the linked release as part of the upgrade procedure.
{{% /alert %}}

<a id="minio-upgrade-tenant-kustomize"></a>
<a id="minio-upgrade-tenant-plugin"></a>

## Upgrade a Tenant using Kustomize {#upgrade-a-tenant-using-kustomize}

The following procedure upgrades a MinIO Tenant using Kustomize and the `kubectl` CLI. If you deployed the Tenant using [Helm](/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/#deploy-tenant-helm), use the [Upgrade the Tenant using the MinIO Helm Chart](#minio-upgrade-tenant-helm) procedure instead.

To upgrade a Tenant with Kustomize:

If the tenant was deployed with Operator Console, there are additional steps to create a base configuration file before upgrading.

If the tenant was deployed with Kustomize, the base configuration is your existing `kustomization` files from the original tenant deployment.

Choose a tab below depending on how the tenant was deployed:

{{< tabpane text=true persist=header >}}
{{% tab header="Operator Console-Deployed Tenant" selected=true %}}
1. Create the base configuration file:

   1. In a convenient directory, save the current Tenant configuration to a file using `kubectl get`:

      > ```shell
      > kubectl get tenant/my-tenant -n my-tenant-ns -o yaml > my-tenant-base.yaml
      > ```
      >
      > Replace `my-tenant` and `my-tenant-ns` with the name and namespace of the Tenant to upgrade.
      >
      > Edit the file to remove the following lines:
      >
      > - `creationTimestamp:`
      > - `resourceVersion:`
      > - `uid:`
      > - `selfLink:` (if present)
      >
      > For example, remove the highlighted lines:
      >
      > ```shell
      > metadata:
      >   creationTimestamp: "2024-05-29T21:22:20Z"
      >   generation: 1
      >   name: my-tenant
      >   namespace: my-tenant-ns
      >   resourceVersion: "4699"
      >   uid: d5b8e468-3bed-4aa3-8ddb-dfe1ee0362da
      > ```
   2. In the same directory, create a `kustomization.yaml` file with contents resembling the following:

      ```shell
      apiVersion: kustomize.config.k8s.io/v1beta1
      kind: Kustomization

      resources:
      - my-tenant-base.yaml

      patches:
      - path: upgrade-minio-tenant.yaml
      ```

      If you used a different filename for the `kubectl get` output in the previous step, replace `my-tenant-base.yaml` with the name of that file.
{{% /tab %}}
{{% tab header="Existing Kustomized-deployed Tenant" %}}
1. You can upgrade the tenant using the `kustomization` files from the original deployment as the base configuration. If you no longer have these files, follow the instructions in the Operator Console-Deployed Tenant tab.
{{% /tab %}}
{{< /tabpane >}}

2. Create a `upgrade-minio-tenant.yaml` file with contents resembling the following:

```shell
apiVersion: minio.min.io/v2
kind: Tenant

metadata:
  name: my-tenant
  namespace: my-tenant-ns

spec:
  image: minio/minio:MINIOLATEST
```

This file instructs Kustomize to upgrade the tenant using the specified image. The name of this file, `upgrade-minio-tenant.yaml`, must match the `patches.path` filename specified in the `kustomization.yaml` file created in the previous step.

Replace `my-tenant` and `my-tenant-ns` with the name and namespace of the Tenant to upgrade. Specify the MinIO version to upgrade to in `image:`.

Alternatively, you can update the base configuration directly, according to your local procedures. Refer to the [Kustomize Documentation](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization) for more information.

3. From the same directory as the above files, apply the updated configuration to the Tenant with `kubectl apply`:

> ```shell
> kubectl apply -k ./
> ```
>
> The output resembles the following:
>
> ```shell
> tenant.minio.min.io/my-tenant configured
> ```

<a id="minio-upgrade-tenant-helm"></a>

## Upgrade the Tenant using the MinIO Helm Chart {#upgrade-the-tenant-using-the-minio-helm-chart}

This procedure upgrades an existing MinIO Tenant using Helm Charts.

If you deployed the Tenant using Kustomize, use the [Upgrade a Tenant using Kustomize](#minio-upgrade-tenant-kustomize) procedure instead.

1. Verify the existing MinIO Tenant installation.

   Use `kubectl get all -n TENANT_NAMESPACE` to verify the health and status of all Tenant pods and services.

   Use the `helm list` command to view the installed charts in the namespace:

   ```shell
   helm list -n TENANT_NAMESPACE
   ```

   The result should resemble the following:

   ```shell
   NAME            NAMESPACE         REVISION        UPDATED                                 STATUS          CHART           APP VERSION
   CHART_NAME      TENANT_NAMESPACE  1               2023-11-01 15:49:58.810412732 -0400 EDT deployed        tenant-5.0.x   v5.0.x
   ```
2. Update the Operator Repository

   Use `helm repo update minio-operator` to update the MinIO Operator repo. If you set a different alias for the MinIO Operator repository, specify that to the command. You can use `helm repo list` to review your installed repositories.

   Use `helm search` to check the latest available chart version after updating the Operator Repo:

   ```shell
   helm search repo minio-operator
   ```

   The response should resemble the following:

   ```shell
   NAME                            CHART VERSION   APP VERSION     DESCRIPTION
   minio-operator/minio-operator   4.3.7           v4.3.7          A Helm chart for MinIO Operator
   minio-operator/operator         7.1.1          v7.1.1         A Helm chart for MinIO Operator
   minio-operator/tenant           7.1.1          v7.1.1         A Helm chart for MinIO Operator
   ```

   The `minio-operator/minio-operator` is a legacy chart and should **not** be installed under normal circumstances.
3. Run `helm upgrade`

   Helm uses the latest chart to upgrade the Tenant:

   ```shell
   helm upgrade -n minio-tenant \
     CHART_NAME minio-operator/tenant
   ```

   The command results should return success with a bump in the `REVISION` value.
4. Validate the Tenant Upgrade

   Check that all services and pods are online and functioning normally.

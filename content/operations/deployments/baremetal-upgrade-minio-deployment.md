---
title: "Upgrade a MinIO Deployment"
url: "/operations/deployments/baremetal-upgrade-minio-deployment/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="upgrade-a-minio-deployment"></a>
<a id="minio-upgrade"></a>

{{% alert color="warning" %}}
**Important**

For deployments older than [RELEASE.2024-03-30T09-41-56Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-03-30T09-41-56Z) running with [AD/LDAP](/reference/minio-server/settings/iam/ldap/#minio-ldap-config-settings) enabled, you **must** read through the release notes for [RELEASE.2024-04-18T19-09-19Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-04-18T19-09-19Z) before starting this procedure. You must take the extra steps documented in the linked release as part of the upgrade.
{{% /alert %}}

MinIO uses an update-then-restart methodology for upgrading a deployment to a newer release:

1. Update the MinIO binary with the newer release.
2. Restart the deployment using [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart).

This procedure does not require taking downtime and is non-disruptive to ongoing operations.

This page documents methods for upgrading using the update-then-restart method for both `systemctl` and user-managed MinIO deployments. Deployments using Ansible, Terraform, or other management tools can use the procedures here as guidance for implementation within the existing automation framework.

## Prerequisites {#prerequisites}

### Back Up Cluster Settings First {#back-up-cluster-settings-first}

Use the [`mc admin cluster bucket export`](/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) and [`mc admin cluster iam export`](/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) commands to take a snapshot of the bucket metadata and IAM configurations prior to starting decommissioning. You can use these snapshots to restore [bucket](/reference/minio-mc-admin/mc-admin-cluster-bucket-import/#minio-mc-admin-cluster-bucket-import) and [IAM](/reference/minio-mc-admin/mc-admin-cluster-iam-import/#minio-mc-admin-cluster-iam-import) settings to recover from user or process errors as necessary.

### Check Release Notes {#check-release-notes}

MinIO publishes [Release Notes](https://github.com/minio/minio/releases) for your reference as part of identifying the changes applied in each release. Review the associated release notes between your current MinIO version and the newer release so you have a complete view of any changes.

Pay particular attention to any releases that are *not* backwards compatible. You cannot trivially downgrade from any such release.

### Test Upgrades Before Applying To Production {#test-upgrades-before-applying-to-production}

MinIO uses a testing and validation suite as part of all releases. However, no testing suite can account for unique combinations and permutations of hardware, software, and workloads of your production environment.

You should always validate any MinIO upgrades in a lower environment (Dev/QA/Staging) *before* applying those upgrades to Production deployments, or any other environment containing critical data. Performing updates to production environments without first validating in lower environments is done at your own risk.

For MinIO deployments that are significantly behind latest stable (6+ months), consider using [MinIO SUBNET](https://min.io/pricing?jmp=docs) for additional support and guidance during the upgrade procedure.

## Considerations {#considerations}

### Upgrades Are Non-Disruptive {#upgrades-are-non-disruptive}

MinIO’s upgrade-then-restart procedure does *not* require taking downtime or scheduling a maintenance period. MinIO restarts are fast, such that restarting all server processes in parallel typically completes in a few seconds. MinIO operations are atomic and strictly consistent, such that applications using MinIO or S3 SDKs can rely on the built-in [transparent retry](https://docs.aws.amazon.com/general/latest/gr/api-retries.html) without further client-side logic. This ensures upgrades are non-disruptive to ongoing operations.

<a id="minio-upgrade-systemctl"></a>

## Update `systemctl`-Managed MinIO Deployments {#update-systemctl-managed-minio-deployments}

Use these steps to upgrade a MinIO deployment where the MinIO server process is managed by `systemctl`, such as those created using the MinIO [DEB/RPM packages](/operations/deployments/baremetal/#deploy-minio-distributed-baremetal).

This procedure assumes you have the [`MINIO_CONFIG_ENV_FILE`](/reference/minio-server/settings/core/#envvar.MINIO_CONFIG_ENV_FILE) variable set on all MinIO nodes.

1. Update the MinIO Binary on Each Node

   The following tabs provide examples of updating MinIO onto 64-bit Linux operating systems using RPM, DEB, or binary:

   {{< tabpane text=true persist=header >}}
   {{% tab header="RPM (RHEL)" %}}
   Use the following commands to download the latest stable MinIO RPM and update the existing installation.

   ```shell
   wget RPMURL -O minio.rpm
   sudo dnf update minio.rpm
   ```
   {{% /tab %}}
   {{% tab header="DEB (Debian/Ubuntu)" %}}
   Use the following commands to download the latest stable MinIO DEB and upgrade the existing installation:

   ```shell
   wget DEBURL -O minio.deb
   sudo dpkg -i minio.deb
   ```
   {{% /tab %}}
   {{% tab header="Binary" %}}
   Use the following commands to download the latest stable MinIO binary and overwrite the existing binary:

   ```shell
   wget https://dl.min.io/server/minio/release/linux-amd64/minio
   chmod +x minio
   sudo mv -f ./minio /usr/local/bin/minio
   ```

   Replace `/usr/local/bin` with the location of the existing MinIO binary. Run `which minio` to identify the path if not already known.
   {{% /tab %}}
   {{< /tabpane >}}

   Run `minio --version` on each node to validate that you successfully upgraded all binaries to the same version. Do **not** proceed unless all nodes use the same MinIO binary version.
2. Restart the Deployment

   Run the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart all MinIO server processes in the deployment simultaneously.

   ```shell
   mc admin service restart ALIAS
   ```

   Replace [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment to restart.

   S3-compatible SDKs and applications should retry operations automatically, such that the restart process is typically *non-disruptive* to ongoing operations.
3. Validate the Upgrade

   Use the [`mc admin info`](/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info) command to check that all MinIO servers are online, operational, and reflect the installed MinIO version.
4. Update MinIO Client

   You should upgrade your [`mc`](/reference/minio-mc/#command-mc) binary to match or closely follow the MinIO server release. You can use the [`mc update`](/reference/minio-mc/mc-update/#command-mc.update) command to update the binary to the latest stable release:

   ```shell
   mc update
   ```

<a id="minio-upgrade-mc-admin-update"></a>

## Update Non-System Managed MinIO Deployments {#update-non-system-managed-minio-deployments}

Use these steps to upgrade a MinIO deployment where the MinIO server process is managed outside of the system (`systemd`, `systemctl`), such as by a user, an automated script, or some other process management tool. This procedure only works for systems where the user running the MinIO process has write permissions for the path to the MinIO binary. For deployments managed using `systemctl`, see [Update systemctl-Managed MinIO Deployments](#minio-upgrade-systemctl).

### Update using `mc admin update` {#update-using-mc-admin-update}

The [`mc admin update`](/reference/minio-mc-admin/mc-admin-update/#command-mc.admin.update) command updates all MinIO server binaries in the target MinIO deployment before restarting all nodes simultaneously. The restart process typically completes within a few seconds and is *non-disruptive* to ongoing operations.

The following command updates a MinIO deployment with the specified [alias](/reference/minio-mc/mc-alias-set/#alias) to the latest stable release:

```shell
mc admin update ALIAS
```

The user running the `mc admin update` command **must** have `write` permissions to the location where the binary installs.

You can specify a URL resolving to a specific MinIO server binary version. Airgapped or internet-isolated deployments may utilize this feature for updating from an internally-accessible server:

```shell
mc admin update ALIAS https://minio-mirror.example.com/minio.sha256sum
```

You should upgrade your [`mc`](/reference/minio-mc/#command-mc) binary to match or closely follow the MinIO server release. You can use the [`mc update`](/reference/minio-mc/mc-update/#command-mc.update) command to update the binary to the latest stable release:

```shell
mc update
```

### Update by manually replacing the binary {#update-by-manually-replacing-the-binary}

You can download and manually replace the `minio` server binary on each of the host nodes in the deployment. You must then restart all nodes simultaneously, such as by using [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart).

For example, the following command downloads the latest stable MinIO binary for Linux and copies it to `/usr/local/bin`. The command overwrites the existing `minio` binary at that path.

```shell
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x ./minio
sudo mv -f ./minio /usr/local/bin/minio
```

Once you have replaced the binary on all MinIO hosts in the deployment, you must restart all nodes simultaneously.

You should upgrade your [`mc`](/reference/minio-mc/#command-mc) binary to match or closely follow the MinIO server release. You can use the [`mc update`](/reference/minio-mc/mc-update/#command-mc.update) command to update the binary to the latest stable release:

```shell
mc update
```

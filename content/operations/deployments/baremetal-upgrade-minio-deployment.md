---
title: "Upgrade a Silo Deployment"
url: "/operations/deployments/baremetal-upgrade-minio-deployment/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/deployments/baremetal-upgrade-minio-deployment.rst
upstream_modified: true
---

<a id="upgrade-a-minio-deployment"></a>
<a id="minio-upgrade"></a>

> [!WARNING]
> **Legacy upstream upgrades**
>
> If the deployment still runs an upstream MinIO release older than [`RELEASE.2024-03-30T09-41-56Z`](https://github.com/minio/minio/releases/tag/RELEASE.2024-03-30T09-41-56Z) with AD/LDAP enabled, read the upstream notes for [`RELEASE.2024-04-18T19-09-19Z`](https://github.com/minio/minio/releases/tag/RELEASE.2024-04-18T19-09-19Z) and complete its migration steps before moving to Silo. These names and links identify upstream release contracts and are intentionally retained.

Upgrade Silo by installing a verified server artifact on every node and then restarting the deployment as one coordinated operation. A full-cluster restart creates a brief availability interruption. Applications should retry failed or interrupted requests; operation atomicity does not remove the need for retry handling.

This page covers `systemctl`-managed and manually managed bare-metal deployments. When Ansible, Terraform, containers, or another orchestrator owns the service, apply the same release, verification, and restart boundaries through that tool instead of editing its managed files by hand.

## Before You Upgrade {#prerequisites}

1. **Back up cluster settings.** Export bucket metadata and IAM configuration with [`mc admin cluster bucket export`](/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) and [`mc admin cluster iam export`](/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export).
2. **Choose a published Silo release.** Use [Download & Install](/download/#server), [Silo release notes](/blog/release/), and [GitHub Releases](https://github.com/pgsty/minio/releases). A local tag, branch commit, draft release, or uploaded draft asset is not a published release.
3. **Verify the artifact.** Check its SHA-256 digest against the checksum published with that exact release. Pin one release across all nodes.
4. **Read every intervening release note.** Pay particular attention to format, identity, configuration, and downgrade warnings.
5. **Test the exact upgrade in a lower environment.** Exercise representative reads, writes, policies, lifecycle rules, replication, notifications, and recovery procedures before production.
6. **Disable the inherited in-place updater.** Set `MINIO_UPDATE=off` in the server environment and restart the service so the setting takes effect.
7. **Check bucket-scoped policies for object-only resources.** In the exported IAM configuration, look for statements that grant one of twelve bucket-level write actions — or `s3:*` — on a resource pattern containing `/`, with no bare bucket ARN for the same bucket. Those statements no longer authorize those actions. Add the bare ARN alongside the object pattern; see [Bucket and Object Resources](/administration/identity-access-management/policy-based-access-control/#bucket-and-object-resources). Built-in policies and any statement using `arn:aws:s3:::*` are unaffected.

> [!CAUTION]
> **Do not use `mc admin update ALIAS` for Silo**
>
> As of 2026-08-05, an omitted update URL still selects the upstream `dl.min.io` feed and upstream MinIO signing key in the latest published Silo server. The command can therefore replace Silo with an upstream binary. Use the verified package or binary procedure below. The separate client command [`mc update`](/reference/minio-mc/mc-update/#command-mc.update) is disabled and cannot perform an upgrade.

<a id="minio-upgrade-systemctl"></a>

## `systemctl`-Managed Deployments {#update-systemctl-managed-minio-deployments}

1. Download the same published server release for every node from [Download & Install](/download/#server), then verify its checksum.
2. Install the package or replace the binary on every node **without restarting only part of the cluster**:

   {{< tabs group="rpm-rhel-family-deb-debianubuntu-binary" >}}
   {{< tab label="RPM (RHEL family)" value="rpm-rhel-family" >}}
   ```shell
   sudo dnf install /path/to/minio.rpm
   ```
   {{< /tab >}}
   {{< tab label="DEB (Debian/Ubuntu)" value="deb-debianubuntu" >}}
   ```shell
   sudo dpkg -i /path/to/minio.deb
   ```
   {{< /tab >}}
   {{< tab label="Binary" value="binary" >}}
   ```shell
   sha256sum ./minio
   sudo install -m 0755 ./minio /usr/local/bin/minio
   ```

   Replace `/usr/local/bin/minio` with the path returned by `command -v minio` when your installation uses a different location.
   {{< /tab >}}
   {{< /tabs >}}

3. Run `minio --version` on every node. Do not proceed until every node reports the same intended release.
4. Restart all server processes as one coordinated operation. Where the admin API is available, use:

   ```shell
   mc admin service restart ALIAS
   ```

   Otherwise coordinate `systemctl restart minio` across all nodes through your automation. Do not improvise a rolling mixed-version deployment unless the target release explicitly supports it.
5. Validate the deployment with [`mc admin info`](/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info), then test representative S3 reads and writes, console access, identity login, and any configured replication or notifications.
6. Upgrade the client separately from [Download & Install](/download/#client). Standalone artifacts use `mcli`; source builds and the container retain `mc`.

<a id="minio-upgrade-mc-admin-update"></a>

## Manually Managed Deployments {#update-non-system-managed-minio-deployments}

For a process managed by a user script or another supervisor, download and verify the same Silo binary on every node, replace the executable at the path used by that supervisor, confirm `minio --version`, and restart all nodes as one coordinated operation. The service account must be able to execute the new binary; the operator performing the replacement must be able to write its installation path.

After restart, run the same validation described above. Preserve the previous verified binary until validation completes so that any rollback decision can follow the target release's documented downgrade constraints.

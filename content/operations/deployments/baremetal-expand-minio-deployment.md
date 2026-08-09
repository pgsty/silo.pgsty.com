---
title: "Expand a Distributed Silo Deployment"
url: "/operations/deployments/baremetal-expand-minio-deployment/"
weight: 30
minio_origin: true
silo_modified: true
math: true
---

<a id="expand-a-distributed-minio-deployment"></a>
<a id="expand-minio-distributed"></a>

Silo supports expanding an existing distributed deployment by adding a new [Server Pool](/operations/concepts/#minio-intro-server-pool). Each pool expands the total available storage capacity of the cluster.

Expansion does not provide Business Continuity/Disaster Recovery (BC/DR)-grade protections. While each pool is an independent set of servers with distinct [erasure sets](/operations/concepts/erasure-coding/#minio-ec-erasure-set) for availability, the complete loss of one pool results in MinIO stopping I/O for all pools in the deployment. Similarly, an erasure set which loses quorum in one pool represents data loss of objects stored in that set, regardless of the number of other erasure sets or pools.

The new server pool does **not** need to use the same type or size of hardware and software configuration as any existing server pool, though doing so may allow for simplified cluster management and more predictable performance across pools. All drives in the new pool **should** be of the same type and size within the new pool. Review MinIO’s [hardware recommendations](/operations/checklists/hardware/#minio-hardware-checklist) for more complete guidance on selecting an appropriate configuration.

To provide BC-DR grade failover and recovery support for your single or multi-pool MinIO deployments, use [site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview).

The procedure on this page expands an existing [distributed](/operations/deployments/installation/#deploy-minio-distributed) MinIO deployment with an additional server pool.

{{% alert color="warning" %}}
**Important**

MinIO does not support expanding Single-Node Single-Drive topologies.
{{% /alert %}}

<a id="expand-minio-distributed-prereqs"></a>

## Prerequisites {#prerequisites}

### Networking and Firewalls {#networking-and-firewalls}

Each node should have full bidirectional network access to every other node in the deployment. For containerized or orchestrated infrastructures, this may require specific configuration of networking and routing components such as ingress or load balancers. Certain operating systems may also require setting firewall rules. For example, the following command explicitly opens the default MinIO server API port `9000` on servers using `firewalld`:

```shell
firewall-cmd --permanent --zone=public --add-port=9000/tcp
firewall-cmd --reload
```

All MinIO servers in the deployment *must* use the same listen port.

If you set a static [MinIO Console](/administration/minio-console/#minio-console) port (e.g. `:9001`) you must *also* grant access to that port to ensure connectivity from external clients.

MinIO **strongly recomends** using a load balancer to manage connectivity to the cluster. The Load Balancer should use a “Least Connections” algorithm for routing requests to the MinIO deployment, since any MinIO node in the deployment can receive, route, or process client requests.

The following load balancers are known to work well with MinIO:

- [NGINX](https://www.nginx.com/products/nginx/load-balancing/)
- [HAProxy](https://cbonte.github.io/haproxy-dconv/2.3/intro.html#3.3.5)

Configuring firewalls or load balancers to support MinIO is out of scope for this procedure. The [Configure NGINX Proxy for MinIO Server](/integrations/setup-nginx-proxy-with-minio/#integrations-nginx-proxy) reference provides a baseline configuration for using NGINX as a reverse proxy with basic load balancing configured.

### Sequential Hostnames {#sequential-hostnames}

MinIO *requires* using expansion notation `{x...y}` to denote a sequential series of MinIO hosts when creating a server pool. MinIO therefore *requires* using sequentially-numbered hostnames to represent each [`minio server`](/reference/minio-server/#command-minio.server) process in the pool.

Create the necessary DNS hostname mappings *prior* to starting this procedure. For example, the following hostnames would support a 4-node distributed server pool:

- `minio5.example.com`
- `minio6.example.com`
- `minio7.example.com`
- `minio8.example.com`

You can specify the entire range of hostnames using the expansion notation `minio{5...8}.example.com`.

Configuring DNS to support MinIO is out of scope for this procedure.

### Storage Requirements {#storage-requirements}

The following requirements summarize the [Storage](/operations/checklists/hardware/#minio-hardware-checklist-storage) section of MinIO’s hardware recommendations:

**Use Local Storage**

> Direct-Attached Storage (DAS) has significant performance and consistency advantages over networked storage (<abbr title="Network Attached Storage">NAS</abbr>, <abbr title="Storage Area Network">SAN</abbr>, <abbr title="Network File Storage">NFS</abbr>). MinIO strongly recommends flash storage (NVMe, SSD) for primary or “hot” data.

**Use XFS-Formatting for Drives**

> MinIO strongly recommends provisioning XFS formatted drives for storage. MinIO uses XFS as part of internal testing and validation suites, providing additional confidence in performance and behavior at all scales.
>
> MinIO does **not** test nor recommend any other filesystem, such as EXT4, BTRFS, or ZFS.

**Use Consistent Type of Drive**

> MinIO does not distinguish drive types and does not benefit from mixed storage types. Each [pool](/glossary/#term-pool) must use the same type (NVMe, SSD)
>
> For example, deploy a pool consisting of only NVMe drives. If you deploy some drives as SSD or HDD, MinIO treats those drives identically to the NVMe drives. This can result in performance issues, as some drives have differing or worse read/write characteristics and cannot respond at the same rate as the NVMe drives.

**Use Consistent Size of Drive**

> MinIO limits the size used per drive to the smallest drive in the pool.
>
> For example, deploy a pool consisting of the same number of NVMe drives with identical capacity of `7.68TiB`. If you deploy one drive with `3.84TiB`, MinIO treats all drives in the pool as having that smaller capacity.

**Configure Sequential Drive Mounting**

> MinIO uses Go expansion notation `{x...y}` to denote a sequential series of drives when creating the new server pool, where all nodes in the server pool have an identical set of mounted drives. Configure drive mounting paths as a sequential series to best support this notation. For example, mount your drives using a pattern of `/mnt/drive-n`, where `n` starts at `1` and increments by `1` per drive.

**Persist Drive Mounting and Mapping Across Reboots**

> Use `/etc/fstab` to ensure consistent drive-to-mount mapping across node reboots.
>
> Non-Linux Operating Systems should use the equivalent drive mount management tool.

{{% alert color="info" %}}
**Exclusive access to drives**

MinIO **requires** *exclusive* access to the drives or volumes provided for object storage. No other processes, software, scripts, or persons should perform *any* actions directly on the drives or volumes provided to MinIO or the objects or files MinIO places on them.

Unless directed by MinIO Engineering, do not use scripts or tools to directly modify, delete, or move any of the data shards, parity shards, or metadata files on the provided drives, including from one drive or node to another. Such operations are very likely to result in widespread corruption and data loss beyond MinIO’s ability to heal.
{{% /alert %}}

### Minimum Drives for Erasure Code Parity {#minimum-drives-for-erasure-code-parity}

MinIO requires each pool satisfy the deployment [erasure code](/operations/concepts/erasure-coding/#minio-erasure-coding) settings. Specifically the new pool topology must support a minimum of `2 x EC:N` drives per [erasure set](/operations/concepts/erasure-coding/#minio-ec-erasure-set), where `EC:N` is the [Standard](/reference/minio-server/settings/storage-class/#minio-ec-storage-class) parity storage class of the deployment. This requirement ensures the new server pool can satisfy the expected <abbr title="Service Level Agreement">SLA</abbr> of the deployment.

You can use the [MinIO Erasure Code Calculator](https://min.io/product/erasure-code-calculator?ref=docs) to check the **Erasure Code Stripe Size (K+M)** of your new pool. If the highest listed value is at least `2 x EC:N`, the pool supports the deployment’s erasure parity settings.

### Time Synchronization {#time-synchronization}

Multi-node systems must maintain synchronized time and date to maintain stable internode operations and interactions. Make sure all nodes sync to the same time server regularly. Operating systems vary for methods used to synchronize time and date, such as with `ntp`, `timedatectl`, or `timesyncd`.

Check the documentation for your operating system for how to set up and maintain accurate and identical system clock times across nodes.

### Back Up Cluster Settings First {#back-up-cluster-settings-first}

Use the [`mc admin cluster bucket export`](/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) and [`mc admin cluster iam export`](/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) commands to take a snapshot of the bucket metadata and IAM configurations respectively prior to starting decommissioning. You can use these snapshots to restore [bucket](/reference/minio-mc-admin/mc-admin-cluster-bucket-import/#minio-mc-admin-cluster-bucket-import) and [IAM](/reference/minio-mc-admin/mc-admin-cluster-iam-import/#minio-mc-admin-cluster-iam-import) settings to recover from user or process errors as necessary.

## Considerations {#considerations}

<a id="minio-writing-files"></a>

### Writing Files {#writing-files}

MinIO does not automatically rebalance objects across the new server pools. Instead, MinIO performs new write operations to the pool with the most free storage weighted by the amount of free space on the pool divided by the free space across all available pools.

The formula to determine the probability of a write operation on a particular pool is

\(FreeSpaceOnPoolA / FreeSpaceOnAllPools\)

Consider a situation where a group of three pools has a total of 10 TiB of free space distributed as:

- Pool A has 3 TiB of free space
- Pool B has 2 TiB of free space
- Pool C has 5 TiB of free space

MinIO calculates the probability of a write operation to each of the pools as:

- Pool A: 30% chance (\(3TiB / 10TiB\))
- Pool B: 20% chance (\(2TiB / 10TiB\))
- Pool C: 50% chance (\(5TiB / 10TiB\))

In addition to the free space calculation, if a write option (with parity) would bring a drive usage above 99% or a known free inode count below 1000, MinIO does not write to the pool.

If desired, you can manually initiate a rebalance procedure with [`mc admin rebalance`](/reference/minio-mc-admin/mc-admin-rebalance/#command-mc.admin.rebalance). For more about how rebalancing works, see [managing objects across a deployment](/operations/concepts/#minio-rebalance).

Likewise, MinIO does not write to pools in a decommissioning process.

### Expansion is Non-Disruptive {#expansion-is-non-disruptive}

Adding a new server pool requires restarting *all* MinIO server processes in the deployment at around same time.

MinIO strongly recommends restarting all MinIO Server processes in a deployment simultaneously. MinIO operations are atomic and strictly consistent. As such the restart procedure is non-disruptive to applications and ongoing operations.

Do **not** perform “rolling” (e.g. one node at a time) restarts.

### Capacity-Based Planning {#capacity-based-planning}

MinIO recommends planning storage capacity sufficient to store **at least** 2 years of data before reaching 70% usage. Performing [server pool expansion](#expand-minio-distributed) more frequently or on a “just-in-time” basis generally indicates an architecture or planning issue.

For example, consider an application suite expected to produce at least 100 TiB of data per year and a 3 year target before expansion. The deployment has ~500TiB of usable storage in the initial server pool, such that the cluster safely met the 70% threshold with some buffer for data growth. The new server pool should **ideally** meet at minimum 500TiB of additional storage to allow for a similar lifespan before further expansion.

Since MinIO [erasure coding](/operations/concepts/erasure-coding/#minio-erasure-coding) requires some storage for parity, the total **raw** storage must exceed the planned **usable** capacity. Consider using the MinIO [Erasure Code Calculator](https://min.io/product/erasure-code-calculator) for guidance in planning capacity around specific erasure code settings.

### Recommended Operating Systems {#recommended-operating-systems}

This tutorial assumes all hosts running MinIO use a [recommended Linux operating system](/operations/deployments/baremetal/#minio-installation-platform-support).

All hosts in the deployment should run with matching [software configurations](/operations/checklists/software/#minio-software-checklists).

<a id="id1"></a>

## Expand a Distributed MinIO Deployment {#expand-minio-distributed-baremetal}

The following procedure adds a [Server Pool](/operations/concepts/#minio-intro-server-pool) to an existing MinIO deployment. Each Pool expands the total available storage capacity of the cluster while maintaining the overall [availability](/operations/concepts/erasure-coding/#minio-erasure-coding) of the cluster.

All commands provided below use example values. Replace these values with those appropriate for your deployment.

Review the [Prerequisites](#expand-minio-distributed-prereqs) before starting this procedure.

Complete any planned hardware expansion prior to [decommissioning older hardware pools](/operations/deployments/baremetal-decommission-server-pool/#minio-decommissioning).

### 1) Install the Silo Binary on Each Node in the New Server Pool {#install-the-minio-binary-on-each-node-in-the-new-server-pool}

Install the **same published Silo release** used by the existing pool. Download the x86-64 or ARM64 RPM, DEB, or standalone archive from [Download & Install](/download/#server), and verify its checksum before installation. The Silo release currently publishes those two Linux architectures; inherited references to unsupported `ppc64le` and `s390x` downloads have been removed.

{{< tabpane text=true persist=header >}}
{{% tab header="RPM (RHEL family)" %}}

```shell
sudo dnf install ./minio-*.rpm
```

{{% /tab %}}
{{% tab header="DEB (Debian/Ubuntu)" %}}

```shell
sudo dpkg -i ./minio_*_amd64.deb
```

Use the `arm64` package name on ARM64 hosts.
{{% /tab %}}
{{% tab header="Standalone archive" %}}

```shell
tar -xzf minio_*_linux_*.tar.gz
sudo install -m 0755 ./minio /usr/local/bin/minio
minio --version
```

{{% /tab %}}
{{< /tabpane >}}

Run `minio --version` on every new node and compare it with the existing pool. Do not join a node running a different release. For upgrades, follow the [`systemctl`-managed Silo procedure](/operations/deployments/baremetal-upgrade-minio-deployment/#minio-upgrade-systemctl).

### 2) Add TLS/SSL Certificates {#add-tls-ssl-certificates}

MinIO enables [Transport Layer Security (TLS)](/operations/network-encryption/#minio-tls) 1.2+ automatically upon detecting a valid x.509 certificate (`.crt`) and private key (`.key`) in the MinIO `${HOME}/.minio/certs` directory.

For `systemd`-managed deployments, use the `$HOME` directory for the user which runs the MinIO server process. The provided `minio.service` file runs the process as `minio-user`. The previous step includes instructions for creating this user with a home directory `/home/minio-user`.

- Place TLS certificates into `/home/minio-user/.minio/certs` on each host.
- If *any* MinIO server or client uses certificates signed by an unknown Certificate Authority (self-signed or internal CA), you *must* place the CA certs in the `/home/minio-user/.minio/certs/CAs` on all MinIO hosts in the deployment. MinIO rejects invalid certificates (untrusted, expired, or malformed).

If the `minio.service` file specifies a different user account, use the `$HOME` directory for that account. Alternatively, specify a custom certificate directory using the [`minio server --certs-dir`](/reference/minio-server/#minio.server.-certs-dir) commandline argument. Modify the `MINIO_OPTS` variable in `/etc/default/minio` to set this option. The `systemd` user which runs the MinIO server process *must* have read and listing permissions for the specified directory.

For more specific guidance on configuring MinIO for TLS, including multi-domain support via Server Name Indication (SNI), see [Network Encryption (TLS)](/operations/network-encryption/#minio-tls). You can optionally skip this step to deploy without TLS enabled. MinIO strongly recommends *against* non-TLS deployments outside of early development.

### 3) Create the `systemd` Service File {#create-the-systemd-service-file}

The `.deb` or `.rpm` packages install the following [systemd](https://www.freedesktop.org/wiki/Software/systemd/) service file to `/usr/lib/systemd/system/minio.service`. For binary installations, create this file manually on all MinIO hosts.

{{% alert color="info" %}}
**Note**

`systemd` checks the `/etc/systemd/...` path before checking the `/usr/lib/systemd/...` path and uses the first file it finds. To avoid conflicting or unexpected configuration options, check that the file only exists at the `/usr/lib/systemd/system/minio.service` path.

Refer to the [man page for systemd.unit](https://www.man7.org/linux/man-pages/man5/systemd.unit.5.html) for details on the file path search order.
{{% /alert %}}

```shell
[Unit]
Description=MinIO
Documentation=https://silo.pgsty.com/docs/
Wants=network-online.target
After=network-online.target
AssertFileIsExecutable=/usr/local/bin/minio

[Service]
Type=notify

WorkingDirectory=/usr/local

User=minio-user
Group=minio-user
ProtectProc=invisible

EnvironmentFile=-/etc/default/minio
ExecStart=/usr/local/bin/minio server $MINIO_OPTS $MINIO_VOLUMES

# Let systemd restart this service always
Restart=always

# Specifies the maximum file descriptor number that can be opened by this process
LimitNOFILE=1048576

# Turn-off memory accounting by systemd, which is buggy.
MemoryAccounting=no

# Specifies the maximum number of threads this process can create
TasksMax=infinity

# Disable timeout logic and wait until process is stopped
TimeoutSec=infinity

# Disable killing of MinIO by the kernel's OOM killer
OOMScoreAdjust=-1000

SendSIGKILL=no

[Install]
WantedBy=multi-user.target

# Built for ${project.name}-${project.version} (${project.name})
```

The `minio.service` file runs as the `minio-user` User and Group by default. You can create the user and group using the `groupadd` and `useradd` commands. The following example creates the user, group, and sets permissions to access the folder paths intended for use by MinIO. These commands typically require root (`sudo`) permissions.

```shell
groupadd -r minio-user
useradd -M -r -g minio-user minio-user
chown minio-user:minio-user /mnt/disk1 /mnt/disk2 /mnt/disk3 /mnt/disk4
```

The specified drive paths are provided as an example. Change them to match the path to those drives intended for use by MinIO.

Alternatively, change the `User` and `Group` values to another user and group on the system host with the necessary access and permissions.

MinIO publishes additional startup script examples on [github.com/minio/minio-service](https://github.com/minio/minio-service).

To update deployments managed using `systemctl`, see [Update systemctl-Managed MinIO Deployments](/operations/deployments/baremetal-upgrade-minio-deployment/#minio-upgrade-systemctl).

### 4) Create the Service Environment File {#create-the-service-environment-file}

Create an environment file at `/etc/default/minio`. The MinIO service uses this file as the source of all [environment variables](/reference/minio-server/settings/#minio-server-environment-variables) used by MinIO *and* the `minio.service` file.

The following examples assumes that:

- The deployment has a single server pool consisting of four MinIO server hosts with sequential hostnames.

  ```shell
  minio1.example.com   minio3.example.com
  minio2.example.com   minio4.example.com
  ```

  Each host has 4 locally attached drives with sequential mount points:

  ```shell
  /mnt/disk1/minio   /mnt/disk3/minio
  /mnt/disk2/minio   /mnt/disk4/minio
  ```

- The new server pool consists of eight new MinIO hosts with sequential hostnames:

  ```shell
  minio5.example.com   minio9.example.com
  minio6.example.com   minio10.example.com
  minio7.example.com   minio11.example.com
  minio8.example.com   minio12.example.com
  ```

- All hosts have eight locally-attached drives with sequential mount-points:

  ```shell
  /mnt/disk1/minio  /mnt/disk5/minio
  /mnt/disk2/minio  /mnt/disk6/minio
  /mnt/disk3/minio  /mnt/disk7/minio
  /mnt/disk4/minio  /mnt/disk8/minio
  ```

- The deployment has a load balancer running at `https://minio.example.net` that manages connections across all MinIO hosts. The load balancer should not be routing requests to the new hosts at this step, but should have the necessary configuration updates planned.

Modify the example to reflect your deployment topology:

```shell
# Set the hosts and volumes MinIO uses at startup
# The command uses MinIO expansion notation {x...y} to denote a
# sequential series.
#
# The following example starts the MinIO server with two server pools.
#
# The space delimiter indicates a seperate server pool
#
# The second set of hostnames and volumes is the newly added pool.
# The pool has sufficient stripe size to meet the existing erasure code
# parity of the deployment (2 x EC:4)
#
# The command includes the port on which the MinIO servers listen for each
# server pool.

MINIO_VOLUMES="https://minio{1...4}.example.net:9000/mnt/disk{1...4}/minio https://minio{5...12}.example.net:9000/mnt/disk{1...8}/minio"

# Set all MinIO server options
#
# The following explicitly sets the MinIO Console listen address to
# port 9001 on all network interfaces. The default behavior is dynamic
# port selection.

MINIO_OPTS="--console-address :9001"

# Set the root username. This user has unrestricted permissions to
# perform S3 and administrative API operations on any resource in the
# deployment.
#
# Defer to your organizations requirements for superadmin user name.

MINIO_ROOT_USER=minioadmin

# Set the root password
#
# Use a long, random, unique string that meets your organizations
# requirements for passwords.

MINIO_ROOT_PASSWORD=minio-secret-key-CHANGE-ME
```

You may specify other [environment variables](/reference/minio-server/settings/#minio-server-environment-variables) or server commandline options as required by your deployment. All MinIO nodes in the deployment should include the same environment variables with the matching values.

### 5) Restart the MinIO Deployment with Expanded Configuration {#restart-the-minio-deployment-with-expanded-configuration}

Issue the following commands on each node **simultaneously** in the deployment to restart the MinIO service:

```shell
sudo systemctl restart minio.service
```

Use the following commands to confirm the service is online and functional:

```shell
sudo systemctl status minio.service
journalctl -f -u minio.service
```

MinIO may log an increased number of non-critical warnings while the server processes connect and synchronize. These warnings are typically transient and should resolve as the deployment comes online.

MinIO strongly recommends restarting all MinIO Server processes in a deployment simultaneously. MinIO operations are atomic and strictly consistent. As such the restart procedure is non-disruptive to applications and ongoing operations.

Do **not** perform “rolling” (e.g. one node at a time) restarts.

### 6) Next Steps {#next-steps}

- Update any load balancers, reverse proxies, or other network control planes to route client requests to the new hosts in the MinIO distributed deployment. While MinIO automatically manages routing internally, having the control planes handle initial connection management may reduce network hops and improve efficiency.
- Review the [MinIO Console](/administration/minio-console/#minio-console) to confirm the updated cluster topology and monitor performance.

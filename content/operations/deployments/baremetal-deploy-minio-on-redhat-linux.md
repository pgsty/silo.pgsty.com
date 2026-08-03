---
title: "Deploy MinIO on RedHat Linux"
url: "/operations/deployments/baremetal-deploy-minio-on-redhat-linux/"
weight: 10
minio_origin: true
silo_modified: true
---

<a id="deploy-minio-on-redhat-linux"></a>
<a id="deploy-minio-rhel"></a>

This page documents deploying MinIO on RedHat Linux operating systems, including distributions that are binary-compatible with RHEL. This page makes no distinction or special remarks between RHEL and those distributions, and guidance given for RHEL can typically be applied to those distributions.

MinIO strongly recommends that production deployments use RHEL versions in the **Full Support** or **Maintenance Support** phases of the Red Hat life cycle. At the time of writing, that includes:

- RHEL 9.5+ (**Recommended**)
- RHEL 8.10+

Your organization should have the necessary service contracts with Red Hat to ensure end-to-end supportability of your deployments.

MinIO *may* run on versions of RHEL no longer supported by Red Hat Linux, with limited support or troubleshooting from either MinIO or RedHat.

The procedure focuses on production-grade Multi-Node Multi-Drive (MNMD) “Distributed” configurations. <abbr title="Multi-Node Multi-Drive">MNMD</abbr> deployments provide enterprise-grade performance, availability, and scalability and are the recommended topology for all production workloads.

The procedure includes guidance for deploying Single-Node Multi-Drive (SNMD) and Single-Node Single-Drive (SNSD) topologies in support of early development and evaluation environments.

## Considerations {#considerations}

### Review Checklists {#review-checklists}

Ensure you have reviewed our published Hardware, Software, and Security checklists before attempting this procedure.

### Erasure Coding Parity {#erasure-coding-parity}

MinIO automatically determines the default [erasure coding](/operations/concepts/erasure-coding/#minio-erasure-coding) configuration for the cluster based on the total number of nodes and drives in the topology. You can configure the per-object [parity](/glossary/#term-parity) setting when you set up the cluster *or* let MinIO select the default (`EC:4` for production-grade clusters).

Parity controls the relationship between object availability and storage on disk. Use the MinIO [Erasure Code Calculator](https://min.io/product/erasure-code-calculator) for guidance in selecting the appropriate erasure code parity level for your cluster.

While you can change erasure parity settings at any time, objects written with a given parity do **not** automatically update to the new parity settings.

### Capacity-Based Planning {#capacity-based-planning}

MinIO recommends planning storage capacity sufficient to store **at least** 2 years of data before reaching 70% usage. Performing [server pool expansion](/operations/deployments/baremetal-expand-minio-deployment/#expand-minio-distributed) more frequently or on a “just-in-time” basis generally indicates an architecture or planning issue.

For example, consider an application suite expected to produce at least 100 TiB of data per year and a 3 year target before expansion. By ensuring the deployment has ~500TiB of usable storage up front, the cluster can safely meet the 70% threshold with additional buffer for growth in data storage output per year.

Consider using the MinIO [Erasure Code Calculator](https://min.io/product/erasure-code-calculator) for guidance in planning capacity around specific erasure code settings.

## Procedure {#procedure}

### 1. Download the MinIO RPM {#download-the-minio-rpm}

MinIO provides builds for the following architectures:

- AMD64
- ARM64
- PowerPC 64 LE
- S390X

Use the following commands to download the latest stable MinIO RPM for your host architecture and install it.

{{< tabpane text=true persist=header >}}
{{% tab header="AMD64" %}}
```shell
wget RPMURL -O minio.rpm
sudo dnf install minio.rpm
```
{{% /tab %}}
{{% tab header="ARM64" %}}
```shell
wget RPMARM64URL -O minio.rpm
sudo dnf install minio.rpm
```
{{% /tab %}}
{{% tab header="PPC64LE" %}}
```shell
wget RPMPPC64LEURL -O minio.rpm
sudo dnf install minio.rpm
```
{{% /tab %}}
{{< /tabpane >}}

### 2. Review the `systemd` Service File {#review-the-systemd-service-file}

The `.rpm` package install the following [systemd](https://www.freedesktop.org/wiki/Software/systemd/) service file to `/usr/lib/systemd/system/minio.service`:

```shell
[Unit]
Description=MinIO
Documentation=https://silo.pgsty.com/docs/
Wants=network-online.target
After=network-online.target
AssertFileIsExecutable=/usr/local/bin/minio

[Service]
WorkingDirectory=/usr/local

User=minio-user
Group=minio-user
ProtectProc=invisible

EnvironmentFile=-/etc/default/minio
ExecStartPre=/bin/bash -c "if [ -z \"${MINIO_VOLUMES}\" ]; then echo \"Variable MINIO_VOLUMES not set in /etc/default/minio\"; exit 1; fi"
ExecStart=/usr/local/bin/minio server $MINIO_OPTS $MINIO_VOLUMES

# MinIO RELEASE.2023-05-04T21-44-30Z adds support for Type=notify (https://www.freedesktop.org/software/systemd/man/systemd.service.html#Type=)
# This may improve systemctl setups where other services use `After=minio.server`
# Uncomment the line to enable the functionality
# Type=notify

# Let systemd restart this service always
Restart=always

# Specifies the maximum file descriptor number that can be opened by this process
LimitNOFILE=65536

# Specifies the maximum number of threads this process can create
TasksMax=infinity

# Disable timeout logic and wait until process is stopped
TimeoutStopSec=infinity
SendSIGKILL=no

[Install]
WantedBy=multi-user.target

# Built for ${project.name}-${project.version} (${project.name})
```

### 3. Create a User and Group for MinIO {#create-a-user-and-group-for-minio}

The `minio.service` file runs as the `minio-user` User and Group by default. You can create the user and group using the `groupadd` and `useradd` commands. The following example creates the user, group, and sets permissions to access the folder paths intended for use by MinIO. These commands typically require root (`sudo`) permissions.

```shell
groupadd -r minio-user
useradd -M -r -g minio-user minio-user
```

The command above creates the user **without** a home directory, as is typical for system service accounts.

You **must** `chown` the drive paths you intend to use with MinIO. If the `minio-user` user or group cannot read, write, or list contents of any drive, the MinIO process returns errors on startup.

For example, the following command sets `minio-user:minio-user` as the user-group owner of all drives at `/mnt/drives-n` where `n` is between 1 and 16 inclusive:

```shell
chown -R minio-user:minio-user /mnt/drives-{1...16}
```

### 4. Enable TLS Connectivity {#enable-tls-connectivity}

Create or provide [Transport Layer Security (TLS)](/operations/network-encryption/#minio-tls) certificates to MinIO to automatically enable HTTPS-secured connections between the server and clients.

Place the certificates in a directory accessible by the `minio-user` user/group:

```shell
mkdir -p /opt/minio/certs
chown -R minio-user:minio-user /opt/minio/certs

cp private.key /opt/minio/certs
cp public.crt /opt/minio/certs
```

For local testing or development environments, you can use the MinIO [certgen](https://github.com/minio/certgen) to mint self-signed certificates. For example, the following command generates a self-signed certificate with a set of IP and DNS Subject Alternate Names (SANs) associated to the MinIO Server hosts:

```shell
certgen -host "localhost,minio-*.example.net"
```

Place the generated `public.crt` and `private.key` into the `/path/to/certs` directory to enable TLS for the MinIO deployment. Applications can use the `public.crt` as a trusted Certificate Authority to allow connections to the MinIO deployment without disabling certificate validation.

When MinIO runs with TLS enabled, it also verifies connecting client certificates against the OS list of trusted Certificate Authorities. To enable verification of third-party or internally-signed certificates, place the CA file in the `/opt/minio/certs/CAs` folder. The CA file should include the full chain of trust from leaf to root to ensure successful verification.

For more specific guidance on configuring MinIO for TLS, including multi-domain support via Server Name Indication (SNI), see [Network Encryption (TLS)](/operations/network-encryption/#minio-tls). You can optionally skip this step to deploy without TLS enabled. MinIO strongly recommends *against* non-TLS deployments outside of early development.

### 5. Create the MinIO Environment File {#create-the-minio-environment-file}

Create an environment file at `/etc/default/minio`. The MinIO service uses this file as the source of all [environment variables](/reference/minio-server/settings/#minio-server-environment-variables) used by MinIO *and* the `minio.service` file.

Modify the example to reflect your deployment topology.

{{< tabpane text=true persist=header >}}
{{% tab header="Multi-Node Multi-Drive" %}}
Use Multi-Node Multi-Drive (“Distributed”) deployment topologies in production environments.

```shell
# Set the hosts and volumes MinIO uses at startup
# The command uses MinIO expansion notation {x...y} to denote a
# sequential series.
#
# The following example covers four MinIO hosts
# with 4 drives each at the specified hostname and drive locations.
#
# The command includes the port that each MinIO server listens on
# (default 9000).
# If you run without TLS, change https -> http

MINIO_VOLUMES="https://minio{1...4}.example.net:9000/mnt/disk{1...4}/minio"

# Set all MinIO server command-line options
#
# The following explicitly sets the MinIO Console listen address to
# port 9001 on all network interfaces.
# The default behavior is dynamic port selection.

MINIO_OPTS="--console-address :9001 --certs-dir /opt/minio/certs"

# Set the root username.
# This user has unrestricted permissions to perform S3 and
# administrative API operations on any resource in the deployment.
#
# Defer to your organizations requirements for superadmin user name.

MINIO_ROOT_USER=minioadmin

# Set the root password
#
# Use a long, random, unique string that meets your organizations
# requirements for passwords.

MINIO_ROOT_PASSWORD=minio-secret-key-CHANGE-ME
```
{{% /tab %}}
{{% tab header="Single-Node Multi-Drive" %}}
Use Single-Node Multi-Drive deployments in development and evaluation environments. You can also use them for smaller storage workloads which can tolerate data loss or unavailability due to node downtime.

```shell
# Set the volumes MinIO uses at startup
# The command uses MinIO expansion notation {x...y} to denote a
# sequential series.
#
# The following specifies a single host with 4 drives at the specified location
#
# The command includes the port that the MinIO server listens on
# (default 9000).
# If you run without TLS, change https -> http

MINIO_VOLUMES="https://minio1.example.net:9000/mnt/drive{1...4}/minio"

# Set all MinIO server command-line options
#
# The following explicitly sets the MinIO Console listen address to
# port 9001 on all network interfaces.
# The default behavior is dynamic port selection.

MINIO_OPTS="--console-address :9001 --certs-dir /opt/minio/certs"

# Set the root username.
# This user has unrestricted permissions to perform S3 and
# administrative API operations on any resource in the deployment.
#
# Defer to your organizations requirements for superadmin user name.

MINIO_ROOT_USER=minioadmin

# Set the root password
#
# Use a long, random, unique string that meets your organizations
# requirements for passwords.

MINIO_ROOT_PASSWORD=minio-secret-key-CHANGE-ME
```
{{% /tab %}}
{{% tab header="Single-Node Single-Drive" %}}
Use Single-Node Single-Drive (“Standalone”) deployments in early development and evaluation environments. MinIO does not recommend Standalone deployments in production, as the loss of the node or its storage medium results in data loss.

{{% alert color="warning" %}}
**Important**

SNSD deployments do not support storage expansion through adding new server pools.
{{% /alert %}}

```shell
# Set the volume MinIO uses at startup
#
# The following specifies the drive or folder path

MINIO_VOLUMES="/mnt/drive1/minio"

# Set all MinIO server command-line options
#
# The following explicitly sets the MinIO Console listen address to
# port 9001 on all network interfaces.
# The default behavior is dynamic port selection.

MINIO_OPTS="--console-address :9001 --certs-dir /opt/minio/certs"

# Set the root username.
# This user has unrestricted permissions to perform S3 and
# administrative API operations on any resource in the deployment.
#
# Defer to your organizations requirements for superadmin user name.

MINIO_ROOT_USER=minioadmin

# Set the root password
#
# Use a long, random, unique string that meets your organizations
# requirements for passwords.

MINIO_ROOT_PASSWORD=minio-secret-key-CHANGE-ME
```
{{% /tab %}}
{{< /tabpane >}}

Specify any other [environment variables](/reference/minio-server/settings/#minio-server-environment-variables) or server command-line options as required by your deployment.

For distributed deployments, all nodes **must** have matching `/etc/default/minio` environment files. Use a utility such as `shasum -a 256 /etc/default/minio` on each node to verify an exact match across all nodes.

### 6. Start the MinIO Deployment {#start-the-minio-deployment}

Use `systemctl start minio` to start each node in the deployment.

You can track the status of the startup using `journalctl -u minio` on each node.

On successful startup, the MinIO process emits a summary of the deployment that resembles the following output:

```shell
MinIO Object Storage Server
Copyright: 2015-2024 MinIO, Inc.
License: GNU AGPLv3 - https://www.gnu.org/licenses/agpl-3.0.html
Version: RELEASE.2024-06-07T16-42-07Z (go1.22.4 linux/amd64)

API: https://minio-1.example.net:9000 https://203.0.113.10:9000 https://127.0.0.1:9000
   RootUser: minioadmin
   RootPass: minioadmin

WebUI: https://minio-1.example.net:9001 https://203.0.113.10:9001 https://127.0.0.1:9001
   RootUser: minioadmin
   RootPass: minioadmin

CLI: https://silo.pgsty.com/reference/minio-mc/#quickstart
   $ mc alias set 'myminio' 'https://minio-1.example.net:9000' 'minioadmin' 'minioadmin'

Docs: https://silo.pgsty.com/docs/
Status:         16 Online, 0 Offline.
```

You may see increased log churn as the cluster starts up and synchronizes.

Common reasons for startup failure include:

- The MinIO process does not have read-write-list access to the specified drives
- The drives are not empty or contain non-MinIO data
- The drives are not formatted or mounted properly
- One or more hosts are not reachable over the network

Following our checklists typically mitigates the risk of encountering those or similar issues.

### 7. Connect to the Deployment {#connect-to-the-deployment}

{{< tabpane text=true persist=header >}}
{{% tab header="Console" %}}
Open your browser and access any of the MinIO hostnames at port `:9001` to open the [MinIO Console](/administration/minio-console/#minio-console) login page. For example, `https://minio1.example.com:9001`.

Log in with the **MINIO_ROOT_USER** and **MINIO_ROOT_PASSWORD** from the previous step.

<img src="/images/minio-console/console-login.png" alt="MinIO Console Login Page" style="max-width: (&#x27;600px&#x27;, &#x27;auto&#x27;);" />

You can use the MinIO Console for general administration tasks like Identity and Access Management, Metrics and Log Monitoring, or Server Configuration. Each MinIO server includes its own embedded MinIO Console.
{{% /tab %}}
{{% tab header="CLI" %}}
Follow the [installation instructions](/reference/minio-mc/#mc-install) for `mc` on your local host. Run `mc --version` to verify the installation.

If your MinIO deployment uses third-party or self-signed TLS certificates, copy the <abbr title="Certificate Authority">CA</abbr> files to `~/.mc/certs/CAs` to allow `mc`

Once installed, create an alias for the MinIO deployment:

```shell
mc alias set myminio https://minio-1.example.net:9000 USERNAME PASSWORD
```

Change the hostname, username, and password to reflect your deployment. The hostname can be any MinIO node in the deployment. You can also specify the hostname load balancer, reverse proxy, or similar network control plane that handles connections to the deployment.
{{% /tab %}}
{{< /tabpane >}}

### 8. Next Steps {#next-steps}

TODO

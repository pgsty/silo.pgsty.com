---
title: "Deploy Silo on macOS"
url: "/operations/deployments/baremetal-deploy-minio-on-macos/"
weight: 40
minio_origin: true
silo_modified: true
---

<a id="deploy-minio-on-macos"></a>
<a id="deploy-minio-macos"></a>

- [Object Storage Essentials](https://www.youtube.com/playlist?list=PLFOIsHSSYIK3WitnqhqfpeZ6fRFKHxIr7)
- [How to Connect to MinIO with JavaScript](https://www.youtube.com/watch?v=yUR4Fvx0D3E&list=PLFOIsHSSYIK3Dd3Y_x7itJT1NUKT5SxDh&index=5)

This page documents deploying Silo onto Apple macOS hosts for development and evaluation.

Silo publishes separate macOS archives for Intel and Apple Silicon. The current project CI runs on Linux and does not establish a macOS support-lifecycle guarantee, so the inherited, dated list of “supported” macOS releases has been removed. Validate the exact operating-system version and workload before production use.

The procedure includes guidance for deploying Single-Node Multi-Drive (SNMD) and Single-Node Single-Drive (SNSD) topologies in support of early development and evaluation environments.

This guide does not validate Multi-Node Multi-Drive (MNMD) distributed configurations on macOS hosts.

## Considerations {#considerations}

### Review Checklists {#review-checklists}

Ensure you have reviewed our published Hardware, Software, and Security checklists before attempting this procedure.

### Erasure Coding Parity {#erasure-coding-parity}

MinIO automatically determines the default [erasure coding](/operations/concepts/erasure-coding/#minio-erasure-coding) configuration for the cluster based on the total number of nodes and drives in the topology. You can configure the per-object [parity](/glossary/#term-parity) setting when you set up the cluster *or* let MinIO select the default (`EC:4` for production-grade clusters).

Parity controls the relationship between object availability and storage on disk. Use the MinIO [Erasure Code Calculator](https://min.io/product/erasure-code-calculator) for guidance in selecting the appropriate erasure code parity level for your cluster.

While you can change erasure parity settings at any time, objects written with a given parity do **not** automatically update to the new parity settings.

## Procedure {#procedure}

### 1. Download the Silo Binary {#download-the-minio-binary}

Choose the Intel (`darwin_amd64`) or Apple Silicon (`darwin_arm64`) archive from [Download & Install](/download/#server). Verify the archive against the checksum published with the same release, extract it, and install the `minio` compatibility binary:

```shell
tar -xzf minio_*_darwin_*.tar.gz
sudo install -m 0755 ./minio /usr/local/bin/minio
minio --version
```

The old Homebrew commands on this page installed the upstream MinIO formula, not Silo, and have therefore been removed.

### 2. Enable TLS Connectivity {#enable-tls-connectivity}

You can skip this step to deploy without TLS enabled. MinIO strongly recommends *against* non-TLS deployments outside of early development.

Create or provide [Transport Layer Security (TLS)](/operations/network-encryption/#minio-tls) certificates to MinIO to automatically enable HTTPS-secured connections between the server and clients.

MinIO expects the default certificate names of `private.key` and `public.crt` for the private and public keys respectively. Place the certificates in a dedicated directory:

```shell
mkdir -p /opt/minio/certs

cp private.key /opt/minio/certs
cp public.crt /opt/minio/certs
```

MinIO verifies client certificates against the OS/System’s default list of trusted Certificate Authorities. To enable verification of third-party or internally-signed certificates, place the CA file in the `/opt/minio/certs/CAs` folder. The CA file should include the full chain of trust from leaf to root to ensure successful verification.

For more specific guidance on configuring MinIO for TLS, including multi-domain support via Server Name Indication (SNI), see [Network Encryption (TLS)](/operations/network-encryption/#minio-tls).

{{% details title="Certificates for Early Development" closed="true" %}}
For local testing or development environments, you can use the MinIO [certgen](https://github.com/minio/certgen) to mint self-signed certificates. For example, the following command generates a self-signed certificate with a set of IP and DNS Subject Alternate Names (SANs) associated to the MinIO Server hosts:

```shell
certgen -host "localhost,minio-*.example.net"
```

Place the generated `public.crt` and `private.key` into the `/path/to/certs` directory to enable TLS for the MinIO deployment. Applications can use the `public.crt` as a trusted Certificate Authority to allow connections to the MinIO deployment without disabling certificate validation.
{{% /details %}}

### 3. Create the MinIO Environment File {#create-the-minio-environment-file}

Create an environment file at `/etc/default/minio`. The MinIO service uses this file as the source of all [environment variables](/reference/minio-server/settings/#minio-server-environment-variables) used by MinIO *and* the `minio.service` file.

Modify the example to reflect your deployment topology.

{{< tabpane text=true persist=header >}}
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

### 4. Start the MinIO Server {#start-the-minio-server}

The following command starts the MinIO Server attached to the current terminal/shell window:

```shell
export MINIO_CONFIG_ENV_FILE=/etc/default/minio
minio server --console-address :9001
```

The command output resembles the following:

```shell

```

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
Status:         1 Online, 0 Offline.
```

The `API` block lists the network interfaces and port on which clients can access the MinIO S3 API. The `Console` block lists the network interfaces and port on which clients can access the MinIO Web Console.

To run the MinIO server process in the background or as a daemon, defer to the macOS documentation for best practices and procedures.

### 5. Connect to the Deployment {#connect-to-the-deployment}

{{< tabpane text=true persist=header >}}
{{% tab header="Console" %}}
Open your browser and access any of the MinIO hostnames at port `:9001` to open the [MinIO Console](/administration/minio-console/#minio-console) login page. For example, `https://minio1.example.com:9001`.

Log in with the **MINIO_ROOT_USER** and **MINIO_ROOT_PASSWORD** from the previous step.

<img src="/images/silo-console/console-login.webp" alt="MinIO Console Login Page" style="max-width: 600px; height: auto;" />

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

### 6. Next Steps {#next-steps}

- [Enable TLS](/operations/network-encryption/enable-minio-tls/) before exposing the service beyond a trusted development network.
- Create least-privilege users and policies through [Identity and Access Management](/administration/identity-access-management/).
- Configure [monitoring and alerting](/operations/monitoring/) before relying on the deployment for persistent data.

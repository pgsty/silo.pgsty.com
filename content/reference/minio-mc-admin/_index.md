---
title: "MinIO Admin Client"
url: "/reference/minio-mc-admin/"
weight: 20
icon: fa-solid fa-user-gear
minio_origin: true
silo_modified: false
---

<a id="minio-admin-client"></a>

<a id="command-mc.admin"></a>

The MinIO Client [`mc`](/reference/minio-mc/#command-mc) command line tool provides the [`mc admin`](#command-mc.admin) command for performing administrative tasks on your MinIO deployments.

While [`mc`](/reference/minio-mc/#command-mc) supports any S3-compatible service, [`mc admin`](#command-mc.admin) *only* supports MinIO deployments.

[`mc admin`](#command-mc.admin) has the following syntax:

```shell
mc admin [FLAGS] COMMAND [ARGUMENTS]
```

## Command Quick reference {#command-quick-reference}

The following table lists [`mc admin`](#command-mc.admin) commands:

<table>
  <thead>
    <tr>
      <th><p>Command</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-accesskey/#command-mc.admin.accesskey"><code>mc admin accesskey</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-accesskey/#command-mc.admin.accesskey"><code>mc admin accesskey</code></a> command and its subcommands create and manage <a href="/administration/identity-access-management/minio-user-management/#minio-idp-service-account">Access Keys</a> for internally managed users on a MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-cluster-bucket/#command-mc.admin.cluster.bucket"><code>mc admin cluster bucket</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-cluster-bucket/#command-mc.admin.cluster.bucket"><code>mc admin cluster bucket</code></a> command and its subcommands provide tools for manually importing and exporting MinIO bucket metadata.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-cluster-iam/#command-mc.admin.cluster.iam"><code>mc admin cluster iam</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-cluster-iam/#command-mc.admin.cluster.iam"><code>mc admin cluster iam</code></a> command and its subcommands provide tools for manually importing and exporting MinIO <a href="/administration/identity-access-management/#minio-authentication-and-identity-management">identity and access management (IAM)</a> metadata.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-decommission/#command-mc.admin.decommission"><code>mc admin decommission</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-decommission/#command-mc.admin.decommission"><code>mc admin decommission</code></a> command starts the decommissioning process for a
MinIO <a href="/operations/concepts/#minio-intro-server-pool">server pools</a>. Decommissioning is designed
for removing an older server pool whose hardware is no longer sufficient or
performant compared to the pools in the deployment. MinIO automatically migrates
data from the decommissioned pool to the remaining pools in the deployment based
on the ratio of free space available in each pool.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-group/#command-mc.admin.group"><code>mc admin group</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-group/#command-mc.admin.group"><code>mc admin group</code></a> command manages groups on a MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-heal/#command-mc.admin.heal"><code>mc admin heal</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-heal/#command-mc.admin.heal"><code>mc admin heal</code></a> command scans for objects that are damaged or corrupted and heals those objects.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info"><code>mc admin info</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info"><code>mc admin info</code></a> command displays information on a MinIO server.
For distributed MinIO deployments, <a href="/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info"><code>mc admin info</code></a> displays information
for each MinIO server in the deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-kms-key/#command-mc.admin.kms.key"><code>mc admin kms key</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-kms-key/#command-mc.admin.kms.key"><code>mc admin kms key</code></a> command performs cryptographic key management
operations through the MinIO Key Encryption Service (KES).</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs"><code>mc admin logs</code></a></p></td>
      <td><p>Use the <a href="/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs"><code>mc admin logs</code></a> command to show MinIO server logs.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-policy/#command-mc.admin.policy"><code>mc admin policy</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-policy/#command-mc.admin.policy"><code>mc admin policy</code></a> commands manage policies for use with <a href="/administration/identity-access-management/policy-based-access-control/#minio-policy">MinIO Policy-Based Access Control</a> (PBAC).
MinIO PBAC uses IAM-compatible policy JSON documents to define rules for accessing resources on a MinIO server.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-prometheus/#command-mc.admin.prometheus"><code>mc admin prometheus</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-prometheus/#command-mc.admin.prometheus"><code>mc admin prometheus</code></a> command and its subcommands provide access to MinIO Prometheus metrics.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-rebalance/#command-mc.admin.rebalance"><code>mc admin rebalance</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-rebalance/#command-mc.admin.rebalance"><code>mc admin rebalance</code></a> command allows starts, monitors, or stops a rebalancing operation on a MinIO deployment.
Rebalancing redistributes objects across all pools in the deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-replicate/#command-mc.admin.replicate"><code>mc admin replicate</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-replicate/#command-mc.admin.replicate"><code>mc admin replicate</code></a> command creates and manages <a href="/operations/replication/multi-site-replication/#minio-site-replication-overview">site replication</a> for a set of MinIO peer sites.</p><p>Site replication mimics an active-active bucket replication, but for multiple MinIO deployments.
Wherever a change occurs to IAM settings, buckets, or objects across the set of sites, the change replicates across all sites in the site replication group.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-scanner/#command-mc.admin.scanner"><code>mc admin scanner</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-scanner/#command-mc.admin.scanner"><code>mc admin scanner</code></a> commands provide information about the <a href="/operations/concepts/scanner/#minio-concepts-scanner">scanner</a> process.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-service/#command-mc.admin.service"><code>mc admin service</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-service/#command-mc.admin.service"><code>mc admin service</code></a> command can restart or unfreeze MinIO servers.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-trace/#command-mc.admin.trace"><code>mc admin trace</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-trace/#command-mc.admin.trace"><code>mc admin trace</code></a> command displays API operations occurring on the target MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-update/#command-mc.admin.update"><code>mc admin update</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-update/#command-mc.admin.update"><code>mc admin update</code></a> command updates all MinIO servers in the deployment.
The command also supports using a private mirror server for environments where the deployment does not have public internet access.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc-admin/mc-admin-user/#command-mc.admin.user"><code>mc admin user</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc-admin/mc-admin-user/#command-mc.admin.user"><code>mc admin user</code></a> command and its subcommands manage <a href="/administration/identity-access-management/minio-identity-management/#minio-internal-idp">MinIO users</a>.</p></td>
    </tr>
  </tbody>
</table>

<a id="mc-admin-install"></a>

## Installation {#installation}

{{< tabpane text=true persist=header >}}
{{% tab header="Linux" %}}
The following commands add a *temporary* extension to your system PATH for running the `mc` utility. Defer to your operating system instructions for making permanent modifications to your system PATH.

Alternatively, execute `mc` by navigating to the parent folder and running `./mc --help`

**64-bit Intel**

```shell
curl https://dl.min.io/client/mc/release/linux-amd64/mc \
  --create-dirs \
  -o $HOME/minio-binaries/mc

chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries/

mc --help
```

**64-bit PPC**

```shell
curl https://dl.min.io/client/mc/release/linux-ppc64le/mc \
  --create-dirs \
  -o ~/minio-binaries/mc

chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries/

mc --help
```

**ARM64**

```shell
curl https://dl.min.io/client/mc/release/linux-arm64/mc \
  --create-dirs \
  -o ~/minio-binaries/mc

chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries/

mc --help
```

{{% alert color="info" %}}
**Install from the MinIO Download Page**

MinIO does not officially publish its binaries to common Linux repositories or package managers (Ubuntu, RHEL, Archlinux/AUR). The only official source of MinIO binaries is the [MinIO Download Page](https://dl.min.io/client/mc/release/).

MinIO does not recommend installation through a package manager, as upstream repositories may install the incorrect package or a renamed package.

All documentation assumes the installation of the *official* `mc` client binary through the download page *only*, with no changes to binary naming.
{{% /alert %}}
{{% /tab %}}
{{% tab header="macOS" %}}
```shell
brew install minio/stable/mc
mc --help
```
{{% /tab %}}
{{% tab header="Windows" %}}
Open the following file in a browser:

[https://dl.min.io/client/mc/release/windows-amd64/mc.exe](https://dl.min.io/client/mc/release/windows-amd64/mc.exe)

Execute the file by double clicking on it, *or* by running the following in the command prompt or powershell:

```powershell
\path\to\mc.exe --help
```
{{% /tab %}}
{{% tab header="Source" %}}
Installation from source is intended for developers and advanced users and requires a working Golang environment. See [How to install Golang](https://golang.org/doc/install).

Run the following commands in a terminal environment to install `mc` from source:

```shell
go install github.com/minio/mc@latest
```

[`mc update`](/reference/minio-mc/mc-update/#command-mc.update) does not support source-based installations.
{{% /tab %}}
{{< /tabpane >}}

## Quickstart {#quickstart}

Ensure that the host machine has [`mc`](/reference/minio-mc/#command-mc) [installed](#mc-admin-install) prior to starting this procedure.

{{% alert color="warning" %}}
**Important**

The following example temporarily disables the bash history to mitigate the risk of authentication credentials leaking in plain text. This is a basic security measure and does not mitigate all possible attack vectors. Defer to security best practices for your operating system for inputting sensitive information on the command line.
{{% /alert %}}

Use the [`mc alias set`](/reference/minio-mc/mc-alias-set/#command-mc.alias.set) command to add the deployment to the **`mc`** configuration.

```shell
bash +o history
mc config host add <ALIAS> <ENDPOINT> ACCESS_KEY SECRET_KEY
bash -o history
```

Replace each argument with the required values. Specifying only the `mc config host add` command starts an input prompt for entering the required values.

Use the [`mc admin info`](/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info) command to test the connection to the newly added MinIO deployment:

```shell
mc admin info <ALIAS>
```

## Global Options {#global-options}

[`mc admin`](#command-mc.admin) supports the same global options as [`mc`](/reference/minio-mc/#command-mc). See [Global Options](/reference/minio-mc/#minio-mc-global-options).

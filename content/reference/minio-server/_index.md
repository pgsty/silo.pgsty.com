---
title: "MinIO Server"
url: "/reference/minio-server/"
weight: 30
aliases:
  - "/reference/minio-server/minio-server/"
icon: fa-solid fa-database
minio_origin: true
silo_modified: false
---

<a id="minio-server"></a>

<a id="command-minio"></a>

## MinIO Server {#id1}

The [`minio server`](#command-minio.server) command starts the MinIO server process:

```shell
minio server /mnt/disk{1...4}
```

For examples of deploying [`minio server`](#command-minio.server) on a bare metal environment, see [Installation and Management](/operations/deployments/installation/#minio-installation).

For examples of deploying [`minio server`](#command-minio.server) on a Kubernetes environment, see [Deploying a MinIO Tenant](/operations/deployments/k8s-deploy-minio-tenant-on-kubernetes/#minio-k8s-deploy-minio-tenant).

<a id="syntax"></a>
<a id="minio-server-parameters"></a>

### Syntax {#command-minio.server}

Starts the `minio` server process.

The command has the following syntax:

```shell
minio server [FLAGS] HOSTNAME/DIRECTORIES [HOSTNAME/DIRECTORIES..]
```

The command accepts the following arguments:

##### `HOSTNAME` {#minio.server.HOSTNAME}

*mc-cmd*

The hostname of a [`minio server`](#command-minio.server) process.

For standalone deployments, this field is *optional*. You can start a standalone [`server`](#command-minio.server) process with only the [`DIRECTORIES`](#minio.server.DIRECTORIES) argument.

For distributed deployments, specify the hostname of each [`minio server`](#command-minio.server) in the deployment. The group of [`minio server`](#command-minio.server) processes represent a single [Server Pool](/operations/concepts/#minio-intro-server-pool).

[`HOSTNAME`](#minio.server.HOSTNAME) supports MinIO expansion notation `{x...y}` to denote a sequential series of hostnames. MinIO *requires* sequential hostnames to identify each [`minio server`](#command-minio.server) process in the set.

For example, `https://minio{1...4}.example.net` expands to:

- `https://minio1.example.net`
- `https://minio2.example.net`
- `https://minio3.example.net`
- `https://minio4.example.net`

You must run the [`minio server`](#command-minio.server) command with the *same* combination of [`HOSTNAME`](#minio.server.HOSTNAME) and [`DIRECTORIES`](#minio.server.DIRECTORIES) on each host in the Server Pool.

Each additional `HOSTNAME/DIRECTORIES` pair denotes an additional Server Set for the purpose of horizontal expansion of the MinIO deployment. For more information on Server Pools, see [Server Pool](/operations/concepts/#minio-intro-server-pool).

##### `DIRECTORIES` {#minio.server.DIRECTORIES}

*mc-cmd*

*Required*

The directories or drives the [`minio server`](#command-minio.server) process uses as the storage backend.

[`DIRECTORIES`](#minio.server.DIRECTORIES) supports MinIO expansion notation `{x...y}` to denote a sequential series of folders or drives. For example, `/mnt/disk{1...4}` expands to:

- `/mnt/disk1`
- `/mnt/disk2`
- `/mnt/disk3`
- `/mnt/disk4`

The [`DIRECTORIES`](#minio.server.DIRECTORIES) path(s) *must* be empty when first starting the [`minio`](#command-minio.server) process.

The [`minio server`](#command-minio.server) process requires *at least* 4 drives or directories to enable [erasure coding](/operations/concepts/erasure-coding/#minio-erasure-coding).

{{% alert color="warning" %}}
**Important**

MinIO recommends locally-attached drives, where the [`DIRECTORIES`](#minio.server.DIRECTORIES) path points to each drive on the host machine. MinIO recommends *against* using network-attached storage, as network latency reduces performance of those drives compared to locally-attached storage.

For development or evaluation, you can specify multiple logical directories or partitions on a single physical volume to enable erasure coding on the deployment.

For production environments, MinIO does **not recommend** using multiple logical directories or partitions on a single physical disk. While MinIO supports those configurations, the potential cost savings come at the risk of decreased reliability.
{{% /alert %}}

##### `--address` {#minio.server.-address}

*mc-cmd*

*Optional*

Binds the [`minio`](#command-minio.server) server process to a specific network address and port number. Specify the address and port as `ADDRESS:PORT`, where `ADDRESS` is an IP address or hostname and `PORT` is a valid and open port on the host system. MinIO supports both IPv4 and IPv6 addressing, provided that the specified addresses are routable and resolveable.

To change the port number for all IP addresses or hostnames configured on the host machine, specify only `:PORT` where `PORT` is a valid and open port on the host.

{{% alert color="info" %}}
**Changed: RELEASE.2023-01-02T09-40-09Z**

You can configure your hosts file to have MinIO only listen on specific IPs. For example, if the machine’s */etc/hosts* file contains the following:

```shell
127.0.1.1       minioip
127.0.1.2       minioip
```

A command like the following would listen for API calls on port `9000` on both configured IP addresses.

```shell
minio server --address "minioip:9000" ~/miniodirectory
```
{{% /alert %}}

If omitted, [`minio`](#command-minio.server) binds to port `9000` on all configured IPv4 addresses, IPv6 addresses, and hostnames on the host machine.

##### `--console-address` {#minio.server.-console-address}

*mc-cmd*

*Optional*

Specifies a static port for the embedded MinIO Console.

Omit to direct MinIO to generate a dynamic port at server startup. The MinIO server outputs the port to the system log.

##### `--ftp` {#minio.server.-ftp}

*mc-cmd*

*Optional*

Enable and configure a File Transfer Protocol (`FTP`) or File Transfer Protocol over SSL/TLS (`FTPS`) server. Use this flag multiple times to specify an address port, a passive port range of addresses, or a TLS certificate and key as key-value pairs.

Valid keys:

- `address`, which takes a single port to use for the server, typically `8021`
- *(Optional)* `passive-port-range`, which restricts the range of potential ports the server can use to transfer data, such as when tight firewall rules limit the port the FTP server can request for the connection
- *(Optional)* `tls-private-key`, which takes the path to the user’s private key for accessing the MinIO deployment by TLS

  Use with `tls-public-cert`.
- *(Optional)* `tls-public-cert`, which takes the path to the certificate for accessing the MinIO deployment by TLS

  Use with `tls-private-key`.

For MinIO deployments with TLS enabled, omit `tls-private-key` and `tls-public-key` to direct MinIO to use the default TLS keys for the MinIO deployment. See [Network Encryption (TLS)](/operations/network-encryption/#minio-tls) for more information. You only need to specify a certificate and private key to a different set of TLS certificate and key than the MinIO default (for example, to use a different domain).

For example:

```shell
minio server http://server{1...4}/disk{1...4} \
--ftp="address=:8021"                         \
--ftp="passive-port-range=30000-40000"        \
--ftp="tls-private-key=path/to/private.key"   \
--ftp="tls-public-cert=path/to/public.crt"    \
...
```

##### `--sftp` {#minio.server.-sftp}

*mc-cmd*

*Optional*

Enable and configure a SSH File Transfer Protocol (`SFTP`) server. Use multiple times to specify each desired key-value pair.

The following table lists valid keys.

<table>
  <thead>
    <tr>
      <th><p>Key</p></th>
      <th><p>Description</p></th>
      <th><p>Valid values</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><code>address</code></p></td>
      <td><p>Port to use for connecting to SFTP.</p></td>
      <td><p>Any valid port number, typically <code>8022</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>ssh-private-key</code></p></td>
      <td><p>Path to the user’s private key file.</p></td>
      <td><p>Absolute path or relative path from current location to the key file to use.</p></td>
    </tr>
    <tr>
      <td><p><code>trusted-user-ca-key</code></p></td>
      <td><p>Specifies a file containing public key of a certificate authority that is trusted to sign user certificates for authentication.
The file must contain a <a href="https://man.openbsd.org/ssh-keygen#CERTIFICATES">user principals list</a>, and the list must include the user(s) that can authenticate with the key.</p></td>
      <td><p>Absolute path or relative path from current location to the user’s trusted certificate authority public key file.</p></td>
    </tr>
    <tr>
      <td><p><code>pub-key-algos</code></p></td>
      <td><p>Comma-separated list of the public key algorithms to support.</p></td>
      <td><pre><code class="language-text">ssh-ed25519
sk-ssh-ed25519@openssh.com
sk-ecdsa-sha2-nistp256@openssh.com
ecdsa-sha2-nistp256
ecdsa-sha2-nistp384
ecdsa-sha2-nistp521
rsa-sha2-256
rsa-sha2-512
ssh-rsa
ssh-dss</code></pre></td>
    </tr>
    <tr>
      <td><p><code>kex-algos</code></p></td>
      <td><p>Comma-separated list in priority order of the key-exchange algorithms to support.</p></td>
      <td><pre><code class="language-text">curve25519-sha256
curve25519-sha256@libssh.org
ecdh-sha2-nistp256
ecdh-sha2-nistp384
ecdh-sha2-nistp521
diffie-hellman-group14-sha256
diffie-hellman-group16-sha512
diffie-hellman-group14-sha1
diffie-hellman-group1-sha1</code></pre></td>
    </tr>
    <tr>
      <td><p><code>cipher-algos</code></p></td>
      <td><p>Comma-separated list of cipher algorithms to support</p></td>
      <td><pre><code class="language-text">aes128-ctr
aes192-ctr
aes256-ctr
aes128-gcm@openssh.com
aes256-gcm@openssh.com
chacha20-poly1305@openssh.com
arcfour256
arcfour128
arcfour
aes128-cbc
3des-cbc</code></pre></td>
    </tr>
    <tr>
      <td><p><code>mac-algos</code></p></td>
      <td><p>Comma-separated list in preference order of MAC algorithms to support.
Based on <a href="https://www.rfc-editor.org/rfc/rfc4253">RFC 4253 section 6.4</a> with the exception of <code>hmac-md5</code> variants, which are end of life.</p></td>
      <td><pre><code class="language-text">hmac-sha2-256-etm@openssh.com
hmac-sha2-512-etm@openssh.com
hmac-sha2-256
hmac-sha2-512
hmac-sha1
hmac-sha1-96</code></pre></td>
    </tr>
    <tr>
      <td><p><code>disable-password-auth</code></p></td>
      <td><p>Disable password authentication.</p></td>
      <td><p><code>true</code></p></td>
    </tr>
  </tbody>
</table>

For example:

```shell
minio server http://server{1...4}/disk{1...4}                                 \
--sftp="address=:8022" --sftp="ssh-private-key=/home/miniouser/.ssh/id_rsa"   \
--sftp="kex-algos=diffie-hellman-group14-sha256,curve25519-sha256@libssh.org" \
...
```

##### `--certs-dir, -S` {#minio.server.-certs-dir}

*mc-cmd*

*Optional*

Specifies the path to the folder containing certificates the [`minio`](#command-minio) process uses for configuring TLS/SSL connectivity.

The contents of the specified folder must follow that of the [default path structure](/operations/network-encryption/#minio-tls-user-generated). For example, the path contents of `--certs-dir /etc/minio` should resemble the following:

```shell
/etc/minio
  private.key
  public.crt
  domain.tld/
    private.key
    public.crt
  CAs/
    full-chain-ca.crt
```

Omit to use the default directory paths:

- Linux/macOS: `${HOME}/.minio/certs`
- Windows: `%%USERPROFILE%%\.minio\certs`.

See [Network Encryption (TLS)](/operations/network-encryption/#minio-tls) for more information on TLS/SSL connectivity.

{{% alert color="warning" %}}
**Important**

[MinIO Server RELEASE.2023-12-09T18-17-51Z](https://github.com/minio/minio/releases/tag/RELEASE.2023-12-09T18-17-51Z) removes the deprecated `--config-dir | -C` parameter. Deployments using this flag may start without TLS enabled. Replace those parameters with `--certs-dir | -S` and restart to re-enable TLS.
{{% /alert %}}

##### `--quiet` {#minio.server.-quiet}

*mc-cmd*

*Optional*

Disables startup information.

##### `--anonymous` {#minio.server.-anonymous}

*mc-cmd*

*Optional*

Hides sensitive information from logging.

##### `--json` {#minio.server.-json}

*mc-cmd*

*Optional*

Outputs server logs and startup information in `JSON` format.

{{% alert color="info" %}}
**Note**

You can define any of the `minio` parameters above by setting them in the [`MINIO_OPTS`](/reference/minio-server/settings/core/#envvar.MINIO_OPTS) environment variable. This variable takes as its value a single string that contains any of the above parameters and their values that you want to set when starting the MinIO Server.
{{% /alert %}}

## Settings {#settings}

You can perform other customizations to the MinIO Server process by defining additional [Configuration Values](/reference/minio-server/settings/#minio-server-configuration-options) or [Environment Variables](/reference/minio-server/settings/#minio-server-environment-variables).

Many configuration values and environment variables define the same value. If you set both a configuration value and the matching environment variable, MinIO uses the value from the environment variable.

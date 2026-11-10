---
title: "Silo Server (silo)"
url: "/reference/minio-server/"
weight: 30
aliases:
  - "/reference/minio-server/minio-server/"
icon: fa-solid fa-database
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-server/minio-server.rst
upstream_modified: true
---

<a id="minio-server"></a>

<a id="command-minio"></a>

## Silo Server {#id1}

The [`silo server`](#command-minio.server) command starts the SILO server process. The official executable is named `silo`; this page retains its historical URL and anchors so existing documentation links remain valid:

```shell
silo server /mnt/disk{1...4}
```

For examples of deploying [`silo server`](#command-minio.server) on a bare metal environment, see [Installation and Management](/operations/deployments/installation/#minio-installation).

For examples of deploying [`silo server`](#command-minio.server) on Kubernetes, see [Deploying a Silo Tenant](/operations/deployments/k8s-deploy-minio-tenant-on-kubernetes/#minio-k8s-deploy-minio-tenant).

<a id="syntax"></a>
<a id="minio-server-parameters"></a>

### Syntax {#command-minio.server}

Starts the `silo` server process.

The command has the following syntax:

```shell
silo server [FLAGS] HOSTNAME/DIRECTORIES [HOSTNAME/DIRECTORIES..]
```

The command accepts the following arguments:

##### `HOSTNAME` {#minio.server.HOSTNAME}

*mc-cmd*

The hostname of a [`silo server`](#command-minio.server) process.

For standalone deployments, this field is *optional*. You can start a standalone [`server`](#command-minio.server) process with only the [`DIRECTORIES`](#minio.server.DIRECTORIES) argument.

For distributed deployments, specify the hostname of each [`silo server`](#command-minio.server) in the deployment. The group of [`silo server`](#command-minio.server) processes represent a single [Server Pool](/operations/concepts/#minio-intro-server-pool).

[`HOSTNAME`](#minio.server.HOSTNAME) supports expansion notation `{x...y}` to denote a sequential series of hostnames. A single pool can also use explicitly listed endpoints; adding multiple pools through command-line arguments requires expansion notation in each pool argument.

For example, `https://minio{1...4}.example.net` expands to:

- `https://minio1.example.net`
- `https://minio2.example.net`
- `https://minio3.example.net`
- `https://minio4.example.net`

You must run the [`silo server`](#command-minio.server) command with the *same* combination of [`HOSTNAME`](#minio.server.HOSTNAME) and [`DIRECTORIES`](#minio.server.DIRECTORIES) on each host in the Server Pool.

With expansion notation, each space-separated `HOSTNAME/DIRECTORIES` argument defines a server pool, which is divided into erasure sets. For more information on Server Pools, see [Server Pool](/operations/concepts/#minio-intro-server-pool).

##### `DIRECTORIES` {#minio.server.DIRECTORIES}

*mc-cmd*

*Required*

The directories or drives the [`silo server`](#command-minio.server) process uses as the storage backend.

[`DIRECTORIES`](#minio.server.DIRECTORIES) supports expansion notation `{x...y}` to denote a sequential series of folders or drives. For example, `/mnt/disk{1...4}` expands to:

- `/mnt/disk1`
- `/mnt/disk2`
- `/mnt/disk3`
- `/mnt/disk4`

The [`DIRECTORIES`](#minio.server.DIRECTORIES) path(s) *must* be empty when first starting the [`silo`](#command-minio.server) process.

SILO supports [erasure coding](/operations/concepts/erasure-coding/#minio-erasure-coding) with a minimum of 2 drives or directory endpoints. A two-drive set defaults to `EC:1`: one data shard and one parity shard, with a read quorum of 1 and a write quorum of 2. If one drive becomes unavailable while the service is running, existing objects can still be read when their data and metadata on the remaining drive are intact, but writes cannot continue. A single-drive deployment uses `EC:0` and provides no erasure-code redundancy.

> [!WARNING]
> **Important**
>
> Silo recommends locally attached drives, where the [`DIRECTORIES`](#minio.server.DIRECTORIES) path points to each drive on the host machine. Avoid network-attached storage for primary object data unless the complete stack has been validated, because network latency and failure semantics differ from locally attached storage.
>
> For development or evaluation, you can specify multiple logical directories or partitions on a single physical volume to enable erasure coding on the deployment.
>
> For production environments, do **not** treat multiple logical directories or partitions on one physical disk as independent failure domains. The apparent drive count does not provide physical-disk redundancy.

##### `--config` {#minio.server.-config}

*mc-cmd*

*Optional*

Specifies the path to a YAML server configuration file (`version: v1` or `version: v2`). You can also set this path with the `MINIO_CONFIG` environment variable.

The YAML file can define storage pools, network bind addresses (`--address`, `--console-address`), the TLS certificates directory (`--certs-dir`), root credentials, and FTP or SFTP listener options. When the YAML file defines storage pools, you can omit `HOSTNAME/DIRECTORIES` on the command line.

##### `--address` {#minio.server.-address}

*mc-cmd*

*Optional*

Binds the [`silo`](#command-minio.server) server process to a specific network address and port number. Specify the address and port as `ADDRESS:PORT`, where `ADDRESS` is an IP address or hostname and `PORT` is a valid and open port on the host system. MinIO supports both IPv4 and IPv6 addressing, provided that the specified addresses are routable and resolveable.

To change the port number for all IP addresses or hostnames configured on the host machine, specify only `:PORT` where `PORT` is a valid and open port on the host.

> [!NOTE]
> **Changed: RELEASE.2023-01-02T09-40-09Z**
>
> You can configure your hosts file to have MinIO only listen on specific IPs. For example, if the machine’s */etc/hosts* file contains the following:
>
> ```shell
> 127.0.1.1       minioip
> 127.0.1.2       minioip
> ```
>
> A command like the following would listen for API calls on port `9000` on both configured IP addresses.
>
> ```shell
> silo server --address "minioip:9000" ~/miniodirectory
> ```

If omitted, [`silo`](#command-minio.server) binds to port `9000` on all configured IPv4 addresses, IPv6 addresses, and hostnames on the host machine.

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
silo server http://server{1...4}/disk{1...4} \
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
silo server http://server{1...4}/disk{1...4}                                 \
--sftp="address=:8022" --sftp="ssh-private-key=/home/miniouser/.ssh/id_rsa"   \
--sftp="kex-algos=diffie-hellman-group14-sha256,curve25519-sha256@libssh.org" \
...
```

##### `--certs-dir, -S` {#minio.server.-certs-dir}

*mc-cmd*

*Optional*

Specifies the path to the folder containing certificates the [`silo`](#command-minio) process uses for configuring TLS/SSL connectivity.

The contents of the specified folder must follow that of the [default path structure](/operations/network-encryption/#minio-tls-user-generated). For example, the path contents of `--certs-dir /etc/silo/certs` should resemble the following:

```shell
/etc/silo/certs
  private.key
  public.crt
  domain.tld/
    private.key
    public.crt
  CAs/
    full-chain-ca.crt
```

When no directory is explicitly configured, a new installation uses:

- Linux/macOS: `${HOME}/.silo/certs`
- Windows: `%USERPROFILE%\.silo\certs`

If the user's home contains only the legacy `.minio` directory and no `.silo`, SILO continues to use `.minio/certs`. When both exist, it uses `.silo/certs` and logs a warning. For service accounts, configure `--certs-dir` explicitly instead of relying on an interactive user's home directory.

[SILO 20261109](/blog/release/silo-20261109/) (`RELEASE.2026-11-09T00-00-00Z`) still accepts the deprecated `--config-dir` / `-C` parameter. When it is set without `--certs-dir`, certificates are loaded from `<config-dir>/certs`; an explicit `--certs-dir` takes precedence. Upstream MinIO release notes about removing this parameter do not describe SILO's current behavior.

See [Network Encryption (TLS)](/operations/network-encryption/#minio-tls) for more information.

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

> [!NOTE]
> **Note**
>
> You can define any of the `minio` parameters above by setting them in the [`MINIO_OPTS`](/reference/minio-server/settings/core/#envvar.MINIO_OPTS) environment variable. This variable takes as its value a single string that contains any of the above parameters and their values that you want to set when starting the MinIO Server.

## Silo Healthcheck {#command-silo.healthcheck}

The `silo healthcheck` subcommand probes a SILO server health endpoint and reports the result through its process exit code. Container images, orchestrators, and maintenance scripts can run `silo healthcheck` directly without `curl` or external HTTP tools.

### Syntax {#silo.healthcheck.syntax}

```shell
silo healthcheck [FLAGS] [CHECK]
```

##### `CHECK` {#silo.healthcheck.CHECK}

*Optional*

Selects the health endpoint to probe. When omitted, `silo healthcheck` runs the `live` check.

| Check          | Endpoint                     | Description                                                                               |
| -------------- | ---------------------------- | ----------------------------------------------------------------------------------------- |
| `live`         | `/minio/health/live`         | Default check. Confirms the HTTP listener serves requests and touches no external system. |
| `ready`        | `/minio/health/ready`        | Checks liveness plus KMS and `etcd` reachability when configured.                         |
| `cluster`      | `/minio/health/cluster`      | Checks cluster-wide write quorum across every erasure set.                                |
| `cluster-read` | `/minio/health/cluster/read` | Checks cluster-wide read quorum across every erasure set.                                 |
{.wide .expand}

##### `--address` {#silo.healthcheck.-address}

*Optional*

Probes the server bound to `ADDRESS:PORT` (environment variable `MINIO_ADDRESS`, default `:9000`). An empty host probes `127.0.0.1` and selects `https` automatically when both `public.crt` and `private.key` exist in the certificates directory.

##### `--url` {#silo.healthcheck.-url}

*Optional*

Probes an explicit `http://HOST:PORT` or `https://HOST:PORT` base URL (environment variable `MINIO_HEALTHCHECK_URL`) instead of deriving the target from `--address` and `--certs-dir`.

##### `--maintenance` {#silo.healthcheck.-maintenance}

*Optional*

Valid with the `cluster` check only. Appends `?maintenance=true` to check whether taking the target node down preserves write quorum. Exits `1` when the server returns HTTP `412 Precondition Failed`.

##### `--timeout` {#silo.healthcheck.-timeout}

*Optional*

Sets the overall probe deadline. Defaults to `5s` for `live` and `ready`, and `15s` for `cluster` and `cluster-read`.

##### `--certs-dir, -S` {#silo.healthcheck.-certs-dir}

*Optional*

Specifies the path to the certificates directory (environment variable `MINIO_CERTS_DIR`) used to detect HTTPS when `--url` is not set. When `--certs-dir` is omitted and `--config-dir` is set, `silo healthcheck` checks `<config-dir>/certs`.

##### `--json` {#silo.healthcheck.-json}

*Optional*

Emits a single JSON object containing `check`, `healthy`, `status`, `durationMs`, `serverStatus`, `writeQuorum`, `readQuorum`, `healingDrives`, and `error`.

##### `--quiet, -q` {#silo.healthcheck.-quiet}

*Optional*

Suppresses standard output when the probe succeeds.

### Behavior and Exit Codes {#silo.healthcheck.behavior}

`silo healthcheck` sends an anonymous `GET` request, bypasses `HTTP_PROXY` and `HTTPS_PROXY`, and skips TLS certificate verification to match kubelet HTTPS probe behavior. It exits `0` when the target endpoint returns HTTP `200 OK` (including when `--maintenance` confirms that taking the node down preserves write quorum) and exits `1` otherwise.

For startup readiness behavior and data-path verification guidance, see [Healthcheck API: Native probes and application startup](/operations/monitoring/healthcheck-probe/#native-probe).

## Settings {#settings}

You can perform other customizations to the MinIO Server process by defining additional [Configuration Values](/reference/minio-server/settings/#minio-server-configuration-options) or [Environment Variables](/reference/minio-server/settings/#minio-server-environment-variables).

Many configuration values and environment variables define the same value. If you set both a configuration value and the matching environment variable, MinIO uses the value from the environment variable.

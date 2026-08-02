---
title: "File Transfer Protocol (FTP/SFTP)"
url: "/developers/file-transfer-protocol/"
weight: 220
icon: fa-solid fa-file-arrow-up
minio_origin: true
silo_modified: false
---

<a id="file-transfer-protocol-ftp-sftp"></a>
<a id="minio-ftp"></a>

- [File Transport Using FTP and SFTP with MinIO](https://www.youtube.com/watch?v=lNZyL8wD-lI)

{{< tabpane text=true persist=header >}}
{{% tab header="Kubernetes" %}}
Starting with Operator 5.0.7 and [MinIO Server RELEASE.2023-04-20T17-56-55Z](https://github.com/minio/minio/releases/tag/RELEASE.2023-04-20T17-56-55Z), you can use the SSH File Transfer Protocol (SFTP) to interact with the objects on a MinIO Operator Tenant deployment.

SFTP is defined by the Internet Engineering Task Force (IETF) as an extension of SSH 2.0. It allows file transfer over SSH for use with [Transport Layer Security (TLS)](/operations/network-encryption/#minio-tls) and virtual private network (VPN) applications.

Enabling SFTP does not affect other MinIO features.
{{% /tab %}}
{{% tab header="Baremetal" %}}
Starting with [MinIO Server RELEASE.2023-04-20T17-56-55Z](https://github.com/minio/minio/releases/tag/RELEASE.2023-04-20T17-56-55Z), you can use the File Transfer Protocol (FTP) to interact with the objects on a MinIO deployment.

You must specifically enable FTP or SFTP when starting the server. Enabling either server type does not affect other MinIO features.

This page uses the abbreviation FTP throughout, but you can use any of the supported FTP protocols described below.
{{% /tab %}}
{{< /tabpane >}}

## Supported Protocols {#supported-protocols}

{{< tabpane text=true persist=header >}}
{{% tab header="Kubernetes" %}}
The MinIO Operator only supports configuring SSH File Transfer Protocol (SFTP).
{{% /tab %}}
{{% tab header="Baremetal" %}}
When enabled, MinIO supports FTP access over the following protocols:

- SSH File Transfer Protocol (SFTP)

  SFTP is defined by the Internet Engineering Task Force (IETF) as an extension of SSH 2.0. SFTP allows file transfer over SSH for use with [Transport Layer Security (TLS)](/operations/network-encryption/#minio-tls) and virtual private network (VPN) applications.

  Your FTP client must support SFTP.
- File Transfer Protocol over SSL/TLS (FTPS)

  FTPS allows for encrypted FTP communication with TLS certificates over the standard FTP communication channel. FTPS should not be confused with SFTP, as FTPS does not communicate over a Secure Shell (SSH).

  Your FTP client must support FTPS.
- File Transfer Protocol (FTP)

  Unencrypted file transfer.

  MinIO does **not** recommend using unencrypted FTP for file transfer.
{{% /tab %}}
{{< /tabpane >}}

## Supported Commands {#supported-commands}

When enabled, MinIO supports the following SFTP operations:

- `get`
- `put`
- `ls`
- `mkdir`
- `rmdir`
- `delete`

MinIO does not support either `append` or `rename` operations.

## Considerations {#considerations}

### Versioning {#versioning}

SFTP clients can only operate on the [latest version](/administration/object-management/object-versioning/#minio-bucket-versioning) of an object. Specifically:

- For read operations, MinIO only returns the latest version of the requested object(s) to the SFTP client.
- For write operations, MinIO applies normal versioning behavior and creates a new object version at the specified namespace. `rm` and `rmdir` operations create `DeleteMarker` objects.

### Authentication and Access {#authentication-and-access}

SFTP access requires the same authentication as any other S3 client. MinIO supports the following authentication providers:

- [MinIO IDP](/administration/identity-access-management/minio-identity-management/#minio-internal-idp) users and their service accounts
- [Active Directory/LDAP](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap) users and their service accounts
- [OpenID/OIDC](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid) service accounts

[STS](/developers/security-token-service/#minio-security-token-service) credentials **cannot** access buckets or objects over SFTP.

Authenticated users can access buckets and objects based on the [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) assigned to the user or parent user account.

The SFTP protocol does not require any of the `admin:*` [permissions](/administration/identity-access-management/policy-based-access-control/#minio-policy-mc-admin-actions). You may not perform other MinIO admin actions with SFTP.

## Prerequisites {#prerequisites}

{{< tabpane text=true persist=header >}}
{{% tab header="Kubernetes" %}}
- MinIO Operator v5.0.7 or later.
- Enable an SFTP port (8022) for the server.
- A port to use for the SFTP commands and a range of ports to allow the SFTP server to request to use for the data transfer.
{{% /tab %}}
{{% tab header="Baremetal" %}}
- MinIO RELEASE.2023-04-20T17-56-55Z or later.
- Enable an FTP or SFTP port for the server.
- A port to use for the FTP commands and a range of ports to allow the FTP server to request to use for the data transfer.
{{% /tab %}}
{{< /tabpane >}}

## Procedure {#procedure}

{{< tabpane text=true persist=header >}}
{{% tab header="Kubernetes" %}}
1. Enable SFTP for the desired Tenant:

   Use the following Kubectl command to edit the Tenant YAML configuration:

   ```yaml
   kubectl edit tenants/my-tenant -n my-tenant-ns
   ```

   Replace `my-tenant` and `my-tenant-ns` with the desired Tenant and namespace.

   > In the `features:` section, set the value of `enableSFTP` to `true`:
   >
   > ```yaml
   > spec:
   >    configuration:
   >       name: my-tenant-env-configuration
   >    credsSecret:
   >       name: my-tenant-secret
   >    exposeServices:
   >       console: true
   >       minio: true
   >    features:
   >       enableSFTP: true
   > ```
   >
   > Kubectl restarts MinIO to apply the change.
   >
   > You may also set `enableSFTP` in your [Helm chart](https://github.com/minio/operator/blob/8385948929bc95648d1be82d96f829c810519674/helm/tenant/values.yaml) or [Kustomize configuration](https://github.com/minio/operator/blob/8385948929bc95648d1be82d96f829c810519674/examples/kustomization/base/tenant.yaml) to enable SFTP for newly created Tenants.
2. If needed, configure ingress for the SFTP port according to your local policies.
3. Validate the configuration

   The following `kubectl get` command uses [yq](https://github.com/mikefarah/yq/#install) to display the value of `enableSFTP`, indicating whether SFTP is enabled:

   ```console
   kubectl get tenants/my-tenant -n my-tenant-ns -o yaml | yq '.spec.features'
   ```

   Replace `my-tenant` and `my-tenant-ns` with the desired Tenant and namespace.

   If SFTP is enabled, the output resembles the following:

   ```console
   enableSFTP: true
   ```
4. Use your preferred SFTP client to connect to the MinIO deployment. You must connect as a user whose [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) allow access to the desired buckets and objects.

   The specifics of connecting to the MinIO deployment depend on your SFTP client. Refer to the documentation for your client.

   The following example connects to the MinIO Tenant SFTP server forwarded to the local host system, and lists the contents of a bucket named `runner`.

   > ```console
   > > sftp -P 8022 minio@localhost
   > minio@localhost's password:
   > Connected to localhost.
   > sftp> ls runner/
   > chunkdocs  testdir
   > ```

The following `kubectl get` command uses [yq](https://github.com/mikefarah/yq/#install) to display the value of `enableSFTP`, indicating whether SFTP is enabled:

```console
kubectl get tenants/my-tenant -n my-tenant-ns -o yaml | yq '.spec.features'
```

Replace `my-tenant` and `my-tenant-ns` with the desired Tenant and namespace.

If SFTP is enabled, the output resembles the following:

```console
enableSFTP: true
```
{{% /tab %}}
{{% tab header="Baremetal" %}}
1. Start MinIO with an FTP and/or SFTP port enabled.

   {{< tabpane text=true persist=header >}}
   {{% tab header="FTPS" %}}
   The following example starts MinIO with FTPS enabled.

   ```shell
   minio server http://server{1...4}/disk{1...4} \
   --ftp="address=:8021"                         \
   --ftp="passive-port-range=30000-40000"        \
   --ftp="tls-private-key=path/to/private.key"   \
   --ftp="tls-public-cert=path/to/public.crt"    \
   ...
   ```

   {{% alert color="info" %}}
   **Note**

   Omit `tls-private-key` and `tls-public-cert` to use the MinIO default TLS keys for FTPS. For more information, see the [TLS on MinIO documentation](/operations/network-encryption/#minio-tls).
   {{% /alert %}}
   {{% /tab %}}
   {{% tab header="SFTP/FTP" %}}
   ```shell
   minio server http://server{1...4}/disk{1...4}        \
   --ftp="address=:8021"                                \
   --ftp="passive-port-range=30000-40000"               \
   --sftp="address=:8022"                               \
   --sftp="ssh-private-key=/home/miniouser/.ssh/id_rsa" \
   ...
   ```

   See the [`minio server --ftp`](/reference/minio-server/#minio.server.-ftp) and [`minio server --sftp`](/reference/minio-server/#minio.server.-sftp) for details on using these flags to start the MinIO service. To connect to the an FTP port with TLS (FTPS), pass the `tls-private-key` and `tls-public-cert` keys and values, as well, unless using the MinIO default TLS keys.

   The output of the command should return a response that resembles the following:

   ```shell
   MinIO FTP Server listening on :8021
   MinIO SFTP Server listening on :8022
   ```
   {{% /tab %}}
   {{< /tabpane >}}
2. Use your preferred FTP client to connect to the MinIO deployment. You must connect as a user whose [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) allow access to the desired buckets and objects.

   The specifics of connecting to the MinIO deployment depend on your FTP client. Refer to the documentation for your client.

   To connect over TLS or through SSH, you must use a client that supports the desired protocol.
3. Connect to MinIO

   {{< tabpane text=true persist=header >}}
   {{% tab header="SFTP/FTP" %}}
   The following example connects to an SFTP server, and lists the contents of a bucket named `runner`.

   ```console
   > sftp -P 8022 minio@localhost
   minio@localhost's password:
   Connected to localhost.
   sftp> ls runner/
   chunkdocs  testdir
   ```
   {{% /tab %}}
   {{% tab header="FTPS" %}}
   The following uses the Linux uses the [FTP CLI client](https://linux.die.net/man/1/ftp) to connect to the MinIO server using `minio` credentials to list contents in a bucket named `runner`

   ```shell
   > ftp localhost -P 8021
   Connected to localhost.
   220 Welcome to MinIO FTP Server
   Name (localhost:user): minio
   331 User name ok, password required
   Password:
   230 Password ok, continue
   Remote system type is UNIX.
   Using binary mode to transfer files.
   ftp> ls runner/
   229 Entering Extended Passive Mode (|||39155|)
   150 Opening ASCII mode data connection for file list
   drwxrwxrwx 1 nobody nobody            0 Jan  1 00:00 chunkdocs/
   drwxrwxrwx 1 nobody nobody            0 Jan  1 00:00 testdir/
   ...
   ```
   {{% /tab %}}
   {{< /tabpane >}}
4. Download an Object

   {{< tabpane text=true persist=header >}}
   {{% tab header="SFTP/FTP" %}}
   This example lists items in a bucket, then downloads the contents of the bucket.

   ```console
   > sftp -P 8022 minio@localhost
   minio@localhost's password:
   Connected to localhost.
   sftp> ls runner/
   chunkdocs  testdir
   sftp> get runner/chunkdocs/metadata metadata
   Fetching /runner/chunkdocs/metadata to metadata
   metadata                               100%  226    16.6KB/s   00:00
   sftp>
   ```
   {{% /tab %}}
   {{% tab header="FTPS" %}}
   This example lists items in a bucket, then downloads the contents of the bucket.

   ```console
   > ftp localhost -P 8021
   Connected to localhost.
   220 Welcome to MinIO FTP Server
   Name (localhost:user): minio
   331 User name ok, password required
   Password:
   230 Password ok, continue
   Remote system type is UNIX.
   Using binary mode to transfer files.ftp> ls runner/chunkdocs/metadata
   229 Entering Extended Passive Mode (|||44269|)
   150 Opening ASCII mode data connection for file list
   -rwxrwxrwx 1 nobody nobody           45 Apr  1 06:13 chunkdocs/metadata
   226 Closing data connection, sent 75 bytes
   ftp> get
   (remote-file) runner/chunkdocs/metadata
   (local-file) test
   local: test remote: runner/chunkdocs/metadata
   229 Entering Extended Passive Mode (|||37785|)
   150 Data transfer starting 45 bytes
      45        3.58 KiB/s
   226 Closing data connection, sent 45 bytes
   45 bytes received in 00:00 (3.55 KiB/s)
   ...
   ```
   {{% /tab %}}
   {{< /tabpane >}}
{{% /tab %}}
{{< /tabpane >}}

<a id="minio-certificate-key-file-sftp-k8s"></a>

## Connect to MinIO Using SFTP with a Certificate Key File {#connect-to-minio-using-sftp-with-a-certificate-key-file}

{{% alert color="info" %}}
**Added: RELEASE.2024-05-07T06-41-25Z**

{{% /alert %}}

MinIO supports mutual TLS (mTLS) certificate-based authentication on SFTP, where both the server and the client verify the authenticity of each other.

This type of authentication requires the following:

1. Public key file for the trusted certificate authority
2. Public key file for the MinIO Server minted and signed by the trusted certificate authority
3. Public key file for the user minted and signed by the trusted certificate authority for the client connecting by SFTP and located in the user’s `.ssh` folder (or equivalent for the operating system)

The keys must include a [principals list](https://man.openbsd.org/ssh-keygen#CERTIFICATES) of the user(s) that can authenticate with the key:

```shell
ssh-keygen -s ~/.ssh/ca_user_key -I miniouser -n miniouser -V +1h -z 1 miniouser1.pub
```

- `-s` specifies the path to the certificate authority public key to use for generating this key. The specified public key must have a `principals` list that includes this user.
- `-I` specifies the key identity for the public key.
- `-n` creates the `user principals` list for which this key is valid. You must include the user for which this key is valid, and the user must match the username in MinIO.
- `-V` limits the duration for which the generated key is valid. In this example, the key is valid for one hour. Adjust the duration for your requirements.
- `-z` adds a serial number to the key to distinguish this generated public key from other keys signed by the same certificate authority public key.

MinIO requires specifying the Certificate Authority used to sign the certificates for SFTP access. Start or restart the MinIO Server and specify the path to the trusted certificate authority’s public key using an `--sftp="trusted-user-ca-key=PATH"` flag:

```shell
minio server {path-to-server} --sftp="trusted-user-ca-key=/path/to/.ssh/ca_user_key.pub" {...other flags}
```

When connecting to the MinIO Server with SFTP, the client verifies the MinIO Server’s certificate. The client then passes its own certificate to the MinIO Server. The MinIO Server verifies the key created above by comparing its value to the the known public key from the certificate authority provided at server startup.

Once the MinIO Server verifies the client’s certificate, the user can connect to the MinIO server over SFTP:

```bash
sftp -P <SFTP port> <server IP>
```

### Require service account or LDAP for authentication {#require-service-account-or-ldap-for-authentication}

To force authentication to SFTP using LDAP or service account credentials, append a suffix to the username. Valid suffixes are either `=ldap` or `=svc`.

```console
> sftp -P 8022 my-ldap-user=ldap@[minio@localhost]:/bucket
```

```console
> sftp -P 8022 my-ldap-user=svc@[minio@localhost]:/bucket
```

- Replace `my-ldap-user` with the username to use.
- Replace `[minio@localhost]` with the address of the MinIO server.

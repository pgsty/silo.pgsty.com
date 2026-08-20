---
title: "Network Encryption (TLS)"
url: "/operations/network-encryption/"
weight: 70
icon: fa-solid fa-shield-halved
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/network-encryption.rst
upstream_modified: false
---

<a id="network-encryption-tls"></a>
<a id="minio-tls-user-generated"></a>
<a id="minio-tls-third-party-ca"></a>
<a id="minio-tls"></a>

> [!NOTE]
> **SSL is Deprecated**
>
> TLS is the successor to Secure Socket Layer (SSL) encryption. SSL is fully [deprecated](https://tools.ietf.org/html/rfc7568) as of June 30th, 2018.

## Overview {#overview}

MinIO supports Transport Layer Security (TLS) 1.2+ encryption of incoming and outgoing traffic. MinIO can automatically detect certificates specified to either a default or custom search path and enable TLS for all connections. MinIO supports Server Name Indication (SNI) requests from clients, where MinIO attempts to locate the appropriate TLS certificate for the hostname specified by the client.

MinIO requires *at minimum* a single default TLS certificate and can support multiple TLS certificates in support of SNI connectivity. MinIO uses the TLS Subject Alternate Name (SAN) list to determine which certificate to return to the client. If MinIO cannot find a TLS certificate whose SAN covers the client-requested hostname, MinIO uses the default certificate and attempts to establish the handshake.

You can specify a single TLS certificate which covers all possible SANs for which the MinIO deployment accepts connections.

This configuration requires the least configuration, but necessarily exposes all hostnames configured in the TLS SAN to connecting clients. Depending on your TLS configuration, this may include internal or private SAN domains.

You can instead specify multiple TLS certificates separated by domain(s) with a single default certificate for any non-matching hostname requests. This configuration requires more configuration, but only exposes those hostnames configured in the returned TLS SAN array.

<a id="minio-tls-kubernetes"></a>

## MinIO TLS on Kubernetes {#minio-tls-on-kubernetes}

The MinIO Kubernetes Operator provides three approaches for configuring TLS on MinIO Tenants:

**Automatic TLS using Cluster Signing API**

> For Kubernetes clusters with a valid [TLS Cluster Signing Certificate](/operations/deployments/k8s-minio-operator/#minio-k8s-deploy-operator-tls),the MinIO Kubernetes Operator can automatically generate TLS certificates while [deploying](/operations/deployments/k8s-deploy-minio-tenant-on-kubernetes/#minio-k8s-deploy-minio-tenant-security) or [modifying](/operations/deployments/k8s-modify-minio-tenant-on-kubernetes/#minio-k8s-modify-minio-tenant-security) a MinIO Tenant.
>
> The Kubernetes TLS API uses the Kubernetes cluster Certificate Authority (CA) signature algorithm when generating new TLS certificates. See [Supported TLS Cipher Suites](#minio-tls-supported-cipher-suites) for a complete list of MinIO’s supported TLS Cipher Suites and recommended signature algorithms.
>
> By default, Kubernetes places a certificate bundle on each pod at `/var/run/secrets/kubernetes.io/serviceaccount/ca.crt`. This CA bundle should include the cluster or root CA used to sign the MinIO Tenant TLS certificates. Other applications deployed within the Kubernetes cluster can trust this cluster certificate to connect to a MinIO Tenant using the [MinIO service DNS name](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/) (e.g. `https://minio.minio-tenant-1.svc.cluster-domain.example:443`).
>
> > [!NOTE]
> > **Subject Alternative Name Certificates**
> >
> > If you have a custom Subject Alternative Name (SAN) certificate that is *not* also a wildcard cert, the TLS certificate SAN **must** apply to the hostname for its parent node. Without a wildcard, the SAN must match exactly to be able to connect to the tenant.

**cert-manager Certificate Management**

> The MinIO Operator supports using [cert-manager](https://cert-manager.io/) as a full replacement for its built-in automatic certificate management *or* user-driven manual certificate management. For instructions for deploying the MinIO Operator and tenants using cert-manager, refer to the [cert-manager page](/operations/network-encryption/cert-manager/#minio-certmanager).

**Manual Certificate Management**

> **The Tenant CRD spec `spec.externalCertsSecret` supp .. include:: /includes/common/common-configure-keycloak-identity-management.rst**
>
> > > - **start-after:** start-configure-keycloak-minio-cli
> >
> > orts specifying either `opaque` or `kubernetes.io/tls` type [secrets](https://kubernetes.io/docs/concepts/configuration/secret/#secret-types) containing the `private.key` and `public.crt` to use for TLS.
>
> You can specify multiple certificates to support Tenants which have multiple assigned hostnames.

### Self-signed, Internal, Private Certificates, and Public CAs with Intermediate Certificates {#self-signed-internal-private-certificates-and-public-cas-with-intermediate-certificates}

If deploying MinIO Tenants with certificates minted by a non-global or non-public Certificate Authority, *or* if using a global CA that requires the use of intermediate certificates, you must provide those CAs to the Operator to ensure it can trust those certificates.

The Operator may log warnings related to TLS cert validation for Tenants deployed with untrusted certificates.

The following procedure attaches a secret containing the `public.crt` of the Certificate Authority to the MinIO Operator. You can specify multiple CAs in a single certificate, as long as you maintain the `BEGIN` and `END` delimiters as-is.

1. Create the `operator-ca-tls` secret

   The following creates a Kubernetes secret in the MinIO Operator namespace (`minio-operator`).

   ```shell
   kubectl create secret generic operator-ca-tls \
      --from-file=public.crt -n minio-operator
   ```

   The `public.crt` file must correspond to a valid TLS certificate containing one or more CA definitions.
2. Restart the Operator

   Once created, you must restart the Operator to load the new CAs:

   ```shell
   kubectl rollout restart deployments.apps/minio-operator -n minio-operator
   ```

### Third-Party Certificate Authorities {#third-party-certificate-authorities}

The MinIO Kubernetes Operator can automatically attach third-party Certificate Authorities when [deploying](/operations/deployments/k8s-deploy-minio-tenant-on-kubernetes/#minio-k8s-deploy-minio-tenant-security) or [modifying](/operations/deployments/k8s-modify-minio-tenant-on-kubernetes/#minio-k8s-modify-minio-tenant-security) a MinIO Tenant.

You can add, update, or remove CAs from the tenant at any time. You must restart the MinIO Tenant for the changes to the configured CAs to apply.

The Operator places the specified CAs on each MinIO Server pod such that all pods have a consistent set of trusted CAs.

If the MinIO Server cannot match an incoming client’s TLS certificate issuer against any of the available CAs, the server rejects the connection as invalid.

<a id="minio-tls-baremetal"></a>

## MinIO TLS on Baremetal {#minio-tls-on-baremetal}

The MinIO Server searches for TLS keys and certificates for each node and uses those credentials for enabling TLS. MinIO automatically enables TLS upon discovery and validation of certificates. The search location depends on your MinIO configuration:

{{< tabs group="default-path-custom-path" >}}
{{< tab label="Default Path" value="default-path" >}}
By default, the MinIO server looks for the TLS keys and certificates for each node in the following directory:

```shell
${HOME}/.minio/certs
```

Where `${HOME}` is the home directory of the user running the MinIO Server process. You may need to create the `${HOME}/.minio/certs` directory if it does not exist.

For `systemd` managed deployments this must correspond to the `USER` running the MinIO process. If that user has no home directory, use the **Custom Path** option instead.
{{< /tab >}}
{{< tab label="Custom Path" value="custom-path" >}}
You can specify a path for the MinIO server to search for certificates using the [`minio server --certs-dir`](/reference/minio-server/#minio.server.-certs-dir) or `-S` parameter.

For example, the following command fragment directs the MinIO process to use the `/opt/minio/certs` directory for TLS certificates.

```shell
minio server --certs-dir /opt/minio/certs ...
```

The user running the MinIO service *must* have read and write permissions to this directory.
{{< /tab >}}
{{< /tabs >}}

Place the TLS certificates for the default domain (e.g. `minio.example.net`) in the `/certs` directory, with the private key as `private.key` and public certificate as `public.crt`.

For distributed MinIO deployments, each node in the deployment must have matching TLS certificate configurations.

### Self-signed, Internal, Private Certificates, and Public CAs with Intermediate Certificates {#id1}

If using Certificates signed by a non-global or non-public Certificate Authority, *or* if using a global CA that requires the use of intermediate certificates, you must provide those CAs to the MinIO Server. If the MinIO server does not have the necessary CAs, it may return warnings or errors related to TLS validation when connecting to other services.

Place the CA certificates in the `/certs/CAs` folder. The root path for this folder depends on whether you use the default certificate path *or* a custom certificate path ([`minio server --certs-dir`](/reference/minio-server/#minio.server.-certs-dir) or `-S`)

{{< tabs group="default-certificate-path-custom-certificate-path" >}}
{{< tab label="Default Certificate Path" value="default-certificate-path" >}}
```shell
mv myCA.crt ${HOME}/.minio/certs/CAs
```
{{< /tab >}}
{{< tab label="Custom Certificate Path" value="custom-certificate-path" >}}
The following example assumes the MinIO Server was started with `--certs dir /opt/minio/certs`:

```shell
mv myCA.crt /opt/minio/certs/CAs/
```
{{< /tab >}}
{{< /tabs >}}

For a self-signed certificate, the Certificate Authority is typically the private key used to sign the cert.

For certificates signed by an internal, private, or other non-global Certificate Authority, use the same CA that signed the cert. A non-global CA must include the full chain of trust from the intermediate certificate to the root.

If the provided file is not an X.509 certificate, MinIO ignores it and may return errors for validating certificates signed by that CA.

### Third-Party Certificate Authorities {#id2}

The MinIO Server validates the TLS certificate presented by each connecting client against the host system’s trusted root certificate store.

Place the CA certificates in the `/certs/CAs` folder. The root path for this folder depends on whether you use the default certificate path *or* a custom certificate path ([`minio server --certs-dir`](/reference/minio-server/#minio.server.-certs-dir) or `-S`)

{{< tabs group="default-certificate-path-custom-certificate-path" >}}
{{< tab label="Default Certificate Path" value="default-certificate-path" >}}
```shell
mv myCA.crt ${HOME}/certs/CAs
```
{{< /tab >}}
{{< tab label="Custom Certificate Path" value="custom-certificate-path" >}}
The following example assumes the MinIO Server was started with `--certs dir /opt/minio/certs`:

```shell
mv myCA.crt /opt/minio/certs/CAs/
```
{{< /tab >}}
{{< /tabs >}}

Place the certificate file for each CA into the `/CAs` subdirectory. Ensure all hosts in the MinIO deployment have a consistent set of trusted CAs in that directory. If the MinIO Server cannot match an incoming client’s TLS certificate issuer against any of the available CAs, the server rejects the connection as invalid.

<a id="minio-tls-supported-cipher-suites"></a>

### Supported TLS Cipher Suites {#supported-tls-cipher-suites}

MinIO recommends generating ECDSA (e.g. [NIST P-256 curve](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf)) or EdDSA (e.g. <a id="index-0"></a>[**Curve25519**](https://datatracker.ietf.org/doc/html/rfc7748.html)) TLS private keys/certificates due to their lower computation requirements compared to RSA.

MinIO supports the following TLS 1.2 and 1.3 cipher suites as supported by [Go](https://cs.opensource.google/go/go/+/refs/tags/go1.17.1:src/crypto/tls/cipher_suites.go;l=52). The lists mark recommended algorithms with a <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-star-fill" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"></path></svg> icon:

{{< tabs group="tls-13-tls-12" >}}
{{< tab label="TLS 1.3" value="tls-13" >}}
- `TLS_CHACHA20_POLY1305_SHA256` <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-star-fill" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"></path></svg>
- `TLS_AES_128_GCM_SHA256`
- `TLS_AES_256_GCM_SHA384`
{{< /tab >}}
{{< tab label="TLS 1.2" value="tls-12" >}}
- `TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305` <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-star-fill" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"></path></svg>
- `TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256` <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-star-fill" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"></path></svg>
- `TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384` <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-star-fill" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"></path></svg>
- `TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305`
- `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256`
- `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384`
{{< /tab >}}
{{< /tabs >}}

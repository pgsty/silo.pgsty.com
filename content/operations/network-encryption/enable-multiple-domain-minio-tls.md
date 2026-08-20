---
title: "Enable Multiple-Domain TLS for Silo"
url: "/operations/network-encryption/enable-multiple-domain-minio-tls/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/network-encryption/enable-multiple-domain-minio-tls.rst
upstream_modified: true
---

<a id="enable-multiple-domain-tls-for-minio"></a>

MinIO supports Transport Layer Security (TLS) 1.2+ encryption of incoming and outgoing traffic.

{{< tabs group="kubernetes-baremetal" >}}
{{< tab label="Kubernetes" value="kubernetes" >}}
The MinIO Operator supports the following approaches to enabling TLS on a MinIO Tenant:

- Automatic TLS provisioning using Kubernetes Cluster Signing Certificates
- User-specified TLS using Kubernetes secrets
- Certmanager-managed TLS certificates

The MinIO Operator supports attaching user-specified TLS certificates when [deploying](/operations/deployments/k8s-deploy-minio-tenant-on-kubernetes/#minio-k8s-deploy-minio-tenant-security) or [modifying](/operations/deployments/k8s-modify-minio-tenant-on-kubernetes/#minio-k8s-modify-minio-tenant-security) the MinIO Tenant.

These custom certificates support [Server Name Indication (SNI)](https://en.wikipedia.org/wiki/Server_Name_Indication), where the MinIO server identifies which certificate to use based on the hostname specified by the connecting client. For example, you can generate certificates signed by your organization’s preferred Certificate Authority (CA) and attach those to the MinIO Tenant. Applications which trust that <abbr title="Certificate Authority">CA</abbr> can connect to the MinIO Tenant and fully validate the Tenant TLS certificates.
{{< /tab >}}
{{< tab label="Baremetal" value="baremetal" >}}
MinIO automatically detects TLS certificates in the configured or default directory and starts with TLS enabled.

The MinIO server supports multiple TLS certificates, where the server uses [Server Name Indication (SNI)](https://en.wikipedia.org/wiki/Server_Name_Indication) to identify which certificate to use when responding to a client request. When a client connects using a specific hostname, MinIO uses <abbr title="Server Name Indication">SNI</abbr> to select the appropriate TLS certificate for that hostname.
{{< /tab >}}
{{< /tabs >}}

This procedure documents enabling TLS for multiple domains in MinIO. For a deployment that serves one hostname, use the [single-domain TLS guide](/operations/network-encryption/enable-minio-tls/).

## Prerequisites {#prerequisites}

### Access to MinIO Cluster {#access-to-minio-cluster}

{{< tabs group="kubernetes-baremetal" >}}
{{< tab label="Kubernetes" value="kubernetes" >}}
You must have access to the Kubernetes cluster, with administrative permissions associated to your `kubectl` configuration.

This procedure assumes your permission sets extends sufficiently to support deployment or modification of MinIO-associated resources on the Kubernetes cluster, including but not limited to pods, statefulsets, replicasets, deployments, and secrets.
{{< /tab >}}
{{< tab label="Baremetal" value="baremetal" >}}
This procedure uses [`mc`](/reference/minio-mc/#command-mc) for performing operations on the MinIO cluster. Install `mc` on a machine with network access to the cluster. See the `mc` [Installation Quickstart](/reference/minio-mc/#mc-install) for instructions on downloading and installing `mc`.

This procedure assumes a configured [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) for the MinIO cluster.

This procedure also assumes SSH or similar shell-level access with administrative permissions to each MinIO host server.
{{< /tab >}}
{{< /tabs >}}

### TLS Certificates {#tls-certificates}

Provision the necessary TLS certificates with a [supported cipher suite](/operations/network-encryption/#minio-tls-supported-cipher-suites) for use by MinIO.

{{< tabs group="kubernetes-baremetal" >}}
{{< tab label="Kubernetes" value="kubernetes" >}}
See [MinIO TLS on Kubernetes](/operations/network-encryption/#minio-tls-kubernetes) for more complete guidance on the supported Tenant TLS configurations.
{{< /tab >}}
{{< tab label="Baremetal" value="baremetal" >}}
Provision certificates using your preferred path, such as your organization's internal Certificate Authority or a well-known public provider.

You can create self-signed certificates using `openssl` or the MinIO [certgen](https://github.com/minio/certgen) tool.

For example, the following command generates a self-signed certificate with a set of IP and DNS Subject Alternate Names (SANs) associated to the MinIO Server hosts:

```shell
certgen -host "localhost,minio-*.example.net"
```

See [MinIO TLS on Baremetal](/operations/network-encryption/#minio-tls-baremetal) for more complete guidance on certificate generation and placement.
{{< /tab >}}
{{< /tabs >}}

## Procedure {#procedure}

{{< tabs group="kubernetes-baremetal" >}}
{{< tab label="Kubernetes" value="kubernetes" >}}
The MinIO Operator supports three methods of TLS certificate management on MinIO Tenants:

- MinIO automatic TLS certificate generation
- User-specified TLS certificates
- `cert-manager` managed TLS certificates

You can also deploy MinIO Tenants without TLS enabled.

{{< tabs group="minio-auto-tls-certmanager-user-specified" >}}
{{< tab label="MinIO Auto-TLS" value="minio-auto-tls" >}}
The following steps apply to both new and existing MinIO Deployments using `Kustomize`:

1. Review the [Tenant CRD](/reference/operator-crd/#minio-operator-crd) `TenantSpec.requestAutoCert` and `TenantSpec.certConfig` fields.

   For existing MinIO Tenants, review the Kustomize resources used to create the Tenant and introspect those fields and their current configuration, if any.
2. Create or Modify your Tenant YAML to set the values of `requestAutoCert` and `certConfig` as necessary. For example:

   ```yaml
   spec:
      requestAutoCert: true
      certConfig:
        commonName: "CN=MinioTenantCommonName"
        organizationName: "O=MyOrganizationName"
        dnsNames:
          - 'minio-tenant.domain.tld'
          - '*.kubernete.cluster.dns.path.tld'
   ```

   The `spec.certConfig.dnsNames` should contain a list of <abbr title="Subject Alternate Names">SAN</abbr> the TLS certificate covers.

   See the [pinned `v7.1.1` Kustomize Tenant base YAML](https://github.com/minio/operator/blob/v7.1.1/examples/kustomization/base/tenant.yaml) for a baseline template for guidance in creating or modifying your Tenant resource.
3. Apply the new Kustomization template

   Once you apply the changes, the MinIO Operator automatically redeploys the Tenant with the updated configuration.
{{< /tab >}}
{{< tab label="CertManager" value="certmanager" >}}
The following steps apply to both new and existing MinIO Deployments using `Kustomize`:

1. Review the [Tenant CRD](/reference/operator-crd/#minio-operator-crd) `TenantSpec.externalCertsCecret` fields

   For existing MinIO Tenants, review the Kustomize resources used to create the Tenant and introspect that field’s current configuration, if any.
2. Create or Modify your Tenant YAML to reference the appropriate `cert-manager` resources.

   For example, the following Tenant YAML fragment references a cert-manager resource `myminio-tls`:

   ```yaml
   apiVersion: minio.min.io/v2
   kind: Tenant
   metadata:
   name: myminio
   namespace: minio-tenant
   spec:
      ## Disable default tls certificates.
      requestAutoCert: false
      ## Use certificates generated by cert-manager.
      externalCertSecret:
         - name: default-domain
           type: cert-manager.io/v1
         - name: internal-domain
           type: cert-manager.io/v1
         - name: external-domain
           type: cert-manager.io/v1
   ```

3. Apply the new Kustomization Template

   Once you apply the changes, the MinIO Operator automatically redeploys the Tenant with the updated configuration.
{{< /tab >}}
{{< tab label="User-Specified" value="user-specified" >}}
The following steps apply to both new and existing MinIO deployments using `Kustomize`:

1. Review the [Tenant CRD](/reference/operator-crd/#minio-operator-crd) `TenantSpec.externalCertSecret` field.

   For existing MinIO Tenants, review the Kustomize resources used to create the Tenant and introspect that field’s current configuration, if any.
2. Create or modify your Tenant YAML to reference a secret of type `kubernetes.io/tls`:

   For example, the following Tenant YAML fragment references two TLS secrets for each domain for which the MinIO Tenant accepts connections:

   ```yaml
   apiVersion: minio.min.io/v2
   kind: Tenant
   metadata:
   name: myminio
   namespace: minio-tenant
   spec:
      ## Disable default tls certificates.
      requestAutoCert: false
      ## Use certificates generated by cert-manager.
      externalCertSecret:
      - name: domain-certificate-1
      type: kubernetes.io/tls
      - name: domain-certificate-2
      type: kubernetes.io/tls
   ```

3. Apply the new Kustomization Template

   Once you apply the changes, the MinIO Operator automatically redeploys the Tenant with the updated configuration.
{{< /tab >}}
{{< /tabs >}}
{{< /tab >}}
{{< tab label="Baremetal" value="baremetal" >}}
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

Place the certificates in the `/certs` folder, creating a subfolder in `/certs` for each additional domain for which MinIO should present TLS certificates. While MinIO has no requirements for folder names, consider creating subfolders whose name matches the domain to improve human readability. Place the TLS private and public key for that domain in the subfolder.

```shell
/path/to/certs
   private.key
   public.crt
   s3-example.net/
      private.key
      public.crt
   internal-example.net/
      private.key
      public.crt
```
{{< /tab >}}
{{< /tabs >}}

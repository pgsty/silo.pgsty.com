---
title: "Enable TLS for Silo"
url: "/operations/network-encryption/enable-minio-tls/"
weight: 10
minio_origin: true
silo_modified: true
---

<a id="enable-tls-for-minio"></a>

MinIO supports Transport Layer Security (TLS) 1.2+ encryption of incoming and outgoing traffic.

{{< tabpane text=true persist=header >}}
{{% tab header="Kubernetes" %}}
The MinIO Operator supports the following approaches to enabling TLS on a MinIO Tenant:

- Automatic TLS provisioning using Kubernetes Cluster Signing Certificates
- User-specified TLS using Kubernetes secrets
- Certmanager-managed TLS certificates
{{% /tab %}}
{{% tab header="Baremetal" %}}
MinIO automatically detects TLS certificates in the configured or default directory and starts with TLS enabled.
{{% /tab %}}
{{< /tabpane >}}

This procedure documents enabling TLS for a single domain in MinIO. To serve more than one hostname with SNI, use the [multiple-domain TLS guide](/operations/network-encryption/enable-multiple-domain-minio-tls/).

## Prerequisites {#prerequisites}

### Access to MinIO Cluster {#access-to-minio-cluster}

{{< tabpane text=true persist=header >}}
{{% tab header="Kubernetes" %}}
You must have access to the Kubernetes cluster, with administrative permissions associated to your `kubectl` configuration.

This procedure assumes your permission sets extends sufficiently to support deployment or modification of MinIO-associated resources on the Kubernetes cluster, including but not limited to pods, statefulsets, replicasets, deployments, and secrets.
{{% /tab %}}
{{% tab header="Baremetal" %}}
This procedure uses [`mc`](/reference/minio-mc/#command-mc) for performing operations on the MinIO cluster. Install `mc` on a machine with network access to the cluster. See the `mc` [Installation Quickstart](/reference/minio-mc/#mc-install) for instructions on downloading and installing `mc`.

This procedure assumes a configured [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) for the MinIO cluster.

This procedure also assumes SSH or similar shell-level access with administrative permissions to each MinIO host server.
{{% /tab %}}
{{< /tabpane >}}

### TLS Certificates {#tls-certificates}

Provision the necessary TLS certificates with a [supported cipher suite](/operations/network-encryption/#minio-tls-supported-cipher-suites) for use by MinIO.

{{< tabpane text=true persist=header >}}
{{% tab header="Kubernetes" %}}
See [MinIO TLS on Kubernetes](/operations/network-encryption/#minio-tls-kubernetes) for more complete guidance on the supported Tenant TLS configurations.
{{% /tab %}}
{{% tab header="Baremetal" %}}
Provision certificates using your preferred path, such as your organization's internal Certificate Authority or a well-known public provider.

You can create self-signed certificates using `openssl` or the MinIO [certgen](https://github.com/minio/certgen) tool.

For example, the following command generates a self-signed certificate with a set of IP and DNS Subject Alternate Names (SANs) associated to the MinIO Server hosts:

```shell
certgen -host "localhost,minio-*.example.net"
```

See [MinIO TLS on Baremetal](/operations/network-encryption/#minio-tls-baremetal) for more complete guidance on certificate generation and placement.
{{% /tab %}}
{{< /tabpane >}}

## Procedure {#procedure}

{{< tabpane text=true persist=header >}}
{{% tab header="Kubernetes" %}}
The MinIO Operator supports three methods of TLS certificate management on MinIO Tenants:

- MinIO automatic TLS certificate generation
- `cert-manager` managed TLS certificates
- User managed TLS certificates

You can use any combination of the above methods to enable and configure TLS. MinIO strongly recommends using `cert-manager` for user-specified certificates for a streamlined management and renewal proces.

You can also deploy MinIO Tenants without TLS enabled.

{{< tabpane text=true persist=header >}}
{{% tab header="MinIO Auto-TLS" %}}
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
          - '*.minio-tenant.domain.tld'
   ```

   See the [pinned `v7.1.1` Kustomize Tenant base YAML](https://github.com/minio/operator/blob/v7.1.1/examples/kustomization/base/tenant.yaml) for a baseline template for guidance in creating or modifying your Tenant resource.
3. Apply the new Kustomization template

   Once you apply the changes, the MinIO Operator automatically redeploys the Tenant with the updated configuration.
{{% /tab %}}
{{% tab header="CertManager" %}}
The following steps apply to both new and existing MinIO Deployments using `Kustomize`:

1. Review the [Tenant CRD](/reference/operator-crd/#minio-operator-crd) `TenantSpec.externalCertsCecret` fields

   For existing MinIO Tenants, review the Kustomize resources used to create the Tenant and introspect that field’s current configuration, if any.
2. Create or Modify your Tenant YAML to reference the appropriate `cert-manager` resource.

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
         - name: myminio-tls
            type: cert-manager.io/v1
   ```

3. Apply the new Kustomization Template

   Once you apply the changes, the MinIO Operator automatically redeploys the Tenant with the updated configuration.
{{% /tab %}}
{{% tab header="User-Managed" %}}
The following steps apply to both new and existing MinIO deployments using `Kustomize`:

1. Review the [Tenant CRD](/reference/operator-crd/#minio-operator-crd) `TenantSpec.externalCertSecret` field.

   For existing MinIO Tenants, review the Kustomize resources used to create the Tenant and introspect that field’s current configuration, if any.
2. Create or modify your Tenant YAML to reference a secret of type `kubernetes.io/tls`:

   For example, the following Tenant YAML fragment references a TLS secret which covers the domain on which the MinIO Tenant accepts connections.

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
      - name: domain-certificate
        type: kubernetes.io/tls
   ```

3. Apply the new Kustomization Template

   Once you apply the changes, the MinIO Operator automatically redeploys the Tenant with the updated configuration.
{{% /tab %}}
{{< /tabpane >}}
{{% /tab %}}
{{% tab header="Baremetal" %}}
The MinIO Server searches for TLS keys and certificates for each node and uses those credentials for enabling TLS. MinIO automatically enables TLS upon discovery and validation of certificates. The search location depends on your MinIO configuration:

{{< tabpane text=true persist=header >}}
{{% tab header="Default Path" %}}
By default, the MinIO server looks for the TLS keys and certificates for each node in the following directory:

```shell
${HOME}/.minio/certs
```

Where `${HOME}` is the home directory of the user running the MinIO Server process. You may need to create the `${HOME}/.minio/certs` directory if it does not exist.

For `systemd` managed deployments this must correspond to the `USER` running the MinIO process. If that user has no home directory, use the **Custom Path** option instead.
{{% /tab %}}
{{% tab header="Custom Path" %}}
You can specify a path for the MinIO server to search for certificates using the [`minio server --certs-dir`](/reference/minio-server/#minio.server.-certs-dir) or `-S` parameter.

For example, the following command fragment directs the MinIO process to use the `/opt/minio/certs` directory for TLS certificates.

```shell
minio server --certs-dir /opt/minio/certs ...
```

The user running the MinIO service *must* have read and write permissions to this directory.
{{% /tab %}}
{{< /tabpane >}}

Place the TLS certificates for the default domain (e.g. `minio.example.net`) in the `/certs` directory, with the private key as `private.key` and public certificate as `public.crt`.

For example:

```shell
/path/to/certs
private.key
public.crt
```

You can use the MinIO [certgen](https://github.com/minio/certgen) to mint self-signed certificates for evaluating MinIO with TLS enabled. For example, the following command generates a self-signed certificate with a set of IP and DNS Subject Alternate Names (SANs) associated to the MinIO Server hosts:

```shell
certgen -host "localhost,minio-*.example.net"
```

Place the generated `public.crt` and `private.key` into the `/path/to/certs` directory to enable TLS for the MinIO deployment. Applications can use the `public.crt` as a trusted Certificate Authority to allow connections to the MinIO deployment without disabling certificate validation.

If you are reconfiguring an existing deployment that did not previously have TLS enabled, update [`MINIO_VOLUMES`](/reference/minio-server/settings/core/#envvar.MINIO_VOLUMES) to specify `https` instead of `http`. You may also need to update URLs used by applications or clients.
{{% /tab %}}
{{< /tabpane >}}

---
title: "Security Checklist"
url: "/operations/checklists/security/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="security-checklist"></a>
<a id="minio-security-checklist"></a>

Use the following checklist when planning the security configuration for a production, distributed MinIO deployment.

## Required Steps {#required-steps}

<table>
  <tbody>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Define group policies either on MinIO or the selected 3rd party Identity Provider (LDAP/Active Directory or OpenID)</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Define individual access policies on MinIO or the selected 3rd party Identity Provider</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>(For Kubernetes deployments only) Configure the tenant(s) to use the selected 3rd party Identity Provider</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Grant firewall access for TCP traffic to the MinIO Server S3 API Listen Port (Default: <code>9000</code>).</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Grant firewall access for TCP traffic to the <a href="/administration/minio-console/#minio-console-port-assignment">MinIO Server Console Listen Port</a> (Recommended Default: <code>9090</code>).</p></td>
    </tr>
  </tbody>
</table>

## [Encryption-at-Rest](/administration/server-side-encryption/#minio-sse) {#encryption-at-rest}

MinIO supports the following external KMS providers through Key Encryption Service (KES):

- [HashiCorp Vault Root KMS](/operations/server-side-encryption/configure-minio-kes/#minio-sse-vault)
- [AWS Root KMS](/operations/server-side-encryption/configure-minio-kes/#minio-sse-aws)
- [Google Cloud Platform Secret Manager Root KMS](/operations/server-side-encryption/configure-minio-kes/#minio-sse-gcp)
- [Azure Key Vault Root KMS](/operations/server-side-encryption/configure-minio-kes/#minio-sse-azure)

<table>
  <tbody>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Download and install the MinIO Key Encryption Service (KES)</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Enable TLS</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Generate private and public keys for KES</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Generate private and public keys for MinIO</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Create a KES configuration file and start the service</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Generate an external key for the key management service (KMS)</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Connect MinIO to the KES</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Enable server side encryption</p></td>
    </tr>
  </tbody>
</table>

## [Encryption-in-Transit (“In flight”)](/operations/network-encryption/#minio-tls) {#encryption-in-transit-in-flight}

<table>
  <tbody>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p><a href="/operations/network-encryption/#minio-tls">Enable TLS</a></p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Add separate certificates and keys for each internal and external domain that accesses MinIO</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Generate public and private TLS keys using a supported cipher for TLS 1.3 or TLS 1.2</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Configure trusted Certificate Authority (CA) store(s)</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>Expose your Kubernetes service, such as with NGINX</p></td>
    </tr>
    <tr>
      <td><p><svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-circle" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8z"></path></svg></p></td>
      <td><p>(Optional) Validate certificates, such as with <a href="https://www.sslchecker.com/certdecoder">https://www.sslchecker.com/certdecoder</a></p></td>
    </tr>
  </tbody>
</table>

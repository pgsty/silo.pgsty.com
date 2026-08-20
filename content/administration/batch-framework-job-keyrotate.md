---
title: "Batch Key Rotation"
url: "/administration/batch-framework-job-keyrotate/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/batch-framework-job-keyrotate.rst
upstream_modified: false
---

<a id="batch-key-rotation"></a>
<a id="minio-batch-framework-keyrotate-job"></a>

> [!NOTE]
> **Added: MinIO**
>
> RELEASE.2023-04-07T05-28-58Z

The MinIO Batch Framework allows you to create, manage, monitor, and execute jobs using a YAML-formatted job definition file (a “batch file”). The batch jobs run directly on the MinIO deployment to take advantage of the server-side processing power without constraints of the local machine where you run the [MinIO Client](/reference/minio-mc/#minio-client).

The `keyrotate` batch job type cycles the [sse-s3 or sse-kms keys](/operations/server-side-encryption/#minio-sse-data-encryption) for encrypted objects on a MinIO deployment.

The YAML configuration supports filters to restrict key rotation to a specific set of objects by creation date, tags, metadata, or kms key. You can also define retry attempts or set a notification endpoint and token.

<a id="minio-batch-framework-keyrotate-job-ref"></a>

## Key Rotate Batch Job Reference {#key-rotate-batch-job-reference}

> [!NOTE]
> **Added: MinIO**
>
> RELEASE.2023-04-07T05-28-58Z

Use the `keyrotate` job type to create a batch job that cycles the [sse-s3 or sse-kms keys](/operations/server-side-encryption/#minio-sse-data-encryption) for encrypted objects.

### Required Fields {#required-fields}

> <table>
>   <tbody>
>     <tr>
>       <td><p><code>type:</code></p></td>
>       <td><p>Either <code>sse-s3</code> or <code>sse-kms</code>.</p></td>
>     </tr>
>     <tr>
>       <td><p><code>key:</code></p></td>
>       <td><p>Only for use with the <code>sse-kms</code> type.
> The key to use to unseal the key vault.</p></td>
>     </tr>
>   </tbody>
> </table>

### Optional Fields {#optional-fields}

For **flag based filters**

<table>
  <tbody>
    <tr>
      <td><p><code>newerThan:</code></p></td>
      <td><p>A string representing a length of time in <code>#d#h#s</code> format.</p><p>Keys rotate only for objects newer than the specified length of time.
For example, <code>7d</code>, <code>24h</code>, <code>5d12h30s</code> are valid strings.</p></td>
    </tr>
    <tr>
      <td><p><code>olderThan:</code></p></td>
      <td><p>A string representing a length of time in <code>#d#h#s</code> format.</p><p>Keys rotate only for objects older than the specified length of time.</p></td>
    </tr>
    <tr>
      <td><p><code>createdAfter:</code></p></td>
      <td><p>A date in <code>YYYY-MM-DDTHH:MM:SSZ</code> <a href="https://datatracker.ietf.org/doc/html/rfc3339.html"><strong>RFC3339</strong></a>  date and time format.</p><p>Keys rotate only for objects created after the date.</p></td>
    </tr>
    <tr>
      <td><p><code>createdBefore:</code></p></td>
      <td><p>A date in <code>YYYY-MM-DDTHH:MM:SSZ</code> <a href="https://datatracker.ietf.org/doc/html/rfc3339.html"><strong>RFC3339</strong></a>  date and time format.</p><p>Keys rotate only for objects created prior to the date.</p></td>
    </tr>
    <tr>
      <td><p><code>context:</code></p></td>
      <td><p>Only for use with the <code>sse-kms</code> type.
The context within which to perform actions.</p></td>
    </tr>
    <tr>
      <td><p><code>tags:</code></p></td>
      <td><p>Rotate keys only for objects with tags that match the specified <code>key:</code> and <code>value:</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>metadata:</code></p></td>
      <td><p>Rotate keys only for objects with metadata that match the specified <code>key:</code> and <code>value:</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>kmskey:</code></p></td>
      <td><p>Rotate keys only for objects with a KMS key-id that match the specified value.
This is only applicable for the <code>sse-kms</code> type.</p></td>
    </tr>
  </tbody>
</table>

For **notifications**

<table>
  <tbody>
    <tr>
      <td><p><code>endpoint:</code></p></td>
      <td><p>The predefined endpoint to send events for notifications.</p></td>
    </tr>
    <tr>
      <td><p><code>token:</code></p></td>
      <td><p>An optional JSON Web Token (JWT) to access the <code>endpoint</code>.</p></td>
    </tr>
  </tbody>
</table>

For **retry attempts**

If something interrupts the job, you can define a maximum number of retry attempts. For each retry, you can also define how long to wait between attempts.

<table>
  <tbody>
    <tr>
      <td><p><code>attempts:</code></p></td>
      <td><p>Number of tries to complete the batch job before giving up.</p></td>
    </tr>
    <tr>
      <td><p><code>delay:</code></p></td>
      <td><p>The amount of time to wait between each attempt.</p></td>
    </tr>
  </tbody>
</table>

## Sample YAML Description File for a `keyrotate` Job Type {#sample-yaml-description-file-for-a-keyrotate-job-type}

Use [`mc batch generate`](/reference/minio-mc/mc-batch-generate/#command-mc.batch.generate) to create a basic `keyrotate` batch job for further customization:

```yaml
keyrotate:
  apiVersion: v1
  bucket: BUCKET
  prefix: PREFIX
  encryption:
    type: sse-s3 # valid values are sse-s3 and sse-kms
    key: <new-kms-key> # valid only for sse-kms
    context: <new-kms-key-context> # valid only for sse-kms

  # optional flags based filtering criteria
  # for all objects
  flags:
    filter:
      newerThan: "7d" # match objects newer than this value (e.g. 7d10h31s)
      olderThan: "7d" # match objects older than this value (e.g. 7d10h31s)
      createdAfter: "date" # match objects created after this date and time in RFC3339 format
      createdBefore: "date" # match objects created before this date and time in RFC3339 format
      tags:
        - key: "name"
          value: "pick*" # match objects with tag 'name', with all values starting with 'pick'
      metadata:
        - key: "content-type"
          value: "image/*" # match objects with 'content-type', with all values starting with 'image/'
      kmskey: "key-id" # match objects with KMS key-id (applicable only for sse-kms)
    notify:
      endpoint: "https://notify.endpoint" # notification endpoint to receive job status events
      token: "Bearer xxxxx" # optional authentication token for the notification endpoint
    retry:
      attempts: 10 # number of retries for the job before giving up
      delay: "500ms" # least amount of delay between each retry

```

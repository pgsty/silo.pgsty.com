---
title: "Batch Expiration"
url: "/administration/batch-framework-job-expire/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="batch-expiration"></a>
<a id="minio-batch-framework-expire-job"></a>

{{% alert color="info" %}}
**Added: MinIO**

RELEASE.2023-12-02T10-51-33Z
{{% /alert %}}

The MinIO Batch Framework allows you to create, manage, monitor, and execute jobs using a YAML-formatted job definition file (a “batch file”). The batch jobs run directly on the MinIO deployment to take advantage of the server-side processing power without constraints of the local machine where you run the [MinIO Client](/reference/minio-mc/#minio-client).

The `expire` batch job applies [Automatic Object Expiration](/administration/object-management/create-lifecycle-management-expiration-rule/#minio-lifecycle-management-create-expiry-rule) behavior to a single bucket. The job determines expiration eligibility based on the provided configuration, independent of any configured expiration rules.

## Behavior {#behavior}

### Immediate Expiration of Objects {#immediate-expiration-of-objects}

Batch expiration occurs immediately as part of the batch job, as compared to the [passive scanner-based application of expiration rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner). Specifically, batch expiration does not yield to application I/O and may impact performance of regular read/write operations on the deployment.

### Expiration Eligibility Determined at Batch-Run {#expiration-eligibility-determined-at-batch-run}

The batch expiration works per-bucket and runs once to completion. The job determines expiration eligibility at the time the job runs, and does *not* rescan or recheck for new objects periodically.

To capture any new objects eligible for expiration, re-run the batch job.

### Expiry Rules Check Latest Object Only {#expiry-rules-check-latest-object-only}

The batch expiration job only checks the latest or “current” version of each object against each batch expiration rule.

<a id="minio-batch-framework-expire-job-ref"></a>

## Expire Batch Job Reference {#expire-batch-job-reference}

<table>
  <tbody>
    <tr>
      <td><p>Field</p></td>
      <td><p>Description</p></td>
    </tr>
    <tr>
      <td><p><code>expire</code></p></td>
      <td><p><em>Required</em></p><p>Top-level field for the expiration job type.</p></td>
    </tr>
    <tr>
      <td><p><code>apiVersion</code></p></td>
      <td><p><em>Required</em></p><p>Set to <code>v1</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>bucket</code></p></td>
      <td><p><em>Required</em></p><p>Specify the name of the bucket in which the job runs.</p></td>
    </tr>
    <tr>
      <td><p><code>prefix</code></p></td>
      <td><p><em>Optional</em></p><p>Specify the bucket prefix in which the job runs.</p></td>
    </tr>
    <tr>
      <td><p><code>rules</code></p></td>
      <td><p><em>Required</em></p><p>An array of one or more expiration rules to apply to objects in the specified <code>bucket</code> and <code>prefix</code> (if any).</p></td>
    </tr>
    <tr>
      <td><p><code>rules.[n].type</code></p></td>
      <td><p><em>Required</em></p><p>Supports one of the following two values:</p><ul><li><p><code>object</code> - Applies only to objects which do <strong>not</strong> have a <code>DeleteMarker</code> as the current version.</p></li><li><p><code>deleted</code> - Applies only to objects which <strong>do</strong> Have a <code>DeleteMarker</code> as the current version.</p></li></ul><p>See <a href="/administration/object-management/object-delete/#minio-object-delete">Object Deletion</a> for more complete documentation on <code>DeleteMarker</code> or delete operations in versioned buckets.</p></td>
    </tr>
    <tr>
      <td><p><code>rules.[n].name</code></p></td>
      <td><p><em>Optional</em></p><p>Specify a match string to use for filtering objects.</p><p>Supports glob-style wildcards (<code>*</code>, <code>?</code>).</p></td>
    </tr>
    <tr>
      <td><p><code>rules.[n].olderThan</code></p></td>
      <td><p><em>Optional</em></p><p>Specify the age of objects for filtering objects.
The rule applies to only those objects older than the specified unit of time.</p><p>For example, <code>72h</code> or <code>3d</code> selects objects older than three days.</p></td>
    </tr>
    <tr>
      <td><p><code>rules.[n].createdBefore</code></p></td>
      <td><p><em>Optional</em></p><p>Specify an <a href="https://datatracker.ietf.org/doc/html/rfc3339.html"><strong>RFC3339</strong></a> date and time for filtering objects.</p><p>The rule applies to only those objects created <em>before</em> the specified timestamp.</p></td>
    </tr>
    <tr>
      <td><p><code>rules.[n].tags</code></p></td>
      <td><p><em>Optional</em></p><p>Specify an array of key-value pairs describing object tags to use for filtering objects.
The <code>value</code> entry supports glob-style wildcards (<code>*</code>, <code>?</code>).</p><p>For example, the following filters the rule to only objects with matching tags:</p><pre><code class="language-yaml">tags:
  - key: archive
    value: True</code></pre><p>This key is incompatible with <code>rules.[n].type: deleted</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>rules.[n].metadata</code></p></td>
      <td><p><em>Optional</em></p><p>Specify an array of key-value pairs describing object metadata to use for filtering objects.
The <code>value</code> key supports glob-style wildcards (<code>*</code>, <code>?</code>).</p><p>For example, the following filters the rule to only objects with matching metadata:</p><pre><code class="language-yaml">metadata:
  - key: content-type
    value: image/*</code></pre><p>This key is incompatible with <code>rules.[n].type: deleted</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>rules.[n].size</code></p></td>
      <td><p><em>Optional</em></p><p>Specify the range of object sizes for filtering objects.</p><ul><li><p><code>lessThan</code> - matches objects with size less than the specified amount (e.g. <code>MiB</code>, <code>GiB</code>).</p></li><li><p><code>greaterThan</code> - matches objects with size greater than the specified amount (e.g. <code>MiB</code>, <code>GiB</code>).</p></li></ul></td>
    </tr>
    <tr>
      <td><p><code>rules.[n].purge.retainVersions</code></p></td>
      <td><p><em>Optional</em></p><p>Specify the number of object versions to retain when applying expiration.</p><p>Defaults to <code>0</code> for deleting all object versions (fastest).</p></td>
    </tr>
    <tr>
      <td><p><code>notify.endpoint</code></p></td>
      <td><p><em>Optional</em></p><p>The predefined endpoint to send events for notifications.</p></td>
    </tr>
    <tr>
      <td><p><code>notify.token</code></p></td>
      <td><p><em>Optional</em></p><p>An optional JSON Web Token (JWT) to access the <code>notify.endpoint</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>retry.attempts</code></p></td>
      <td><p><em>Optional</em></p><p>The number of tries to complete the batch job before giving up.</p></td>
    </tr>
    <tr>
      <td><p><code>retry.delay</code></p></td>
      <td><p><em>Optional</em></p><p>The amount of time to wait between each attempt (<code>ms</code>).</p></td>
    </tr>
  </tbody>
</table>

## Sample YAML Description for an `expire` Job Type {#sample-yaml-description-for-an-expire-job-type}

Use [`mc batch generate`](/reference/minio-mc/mc-batch-generate/#command-mc.batch.generate) to create a basic `expire` batch job for further customization.

```yaml
expire:
  apiVersion: v1
  bucket: mybucket # Bucket where this job will expire matching objects from
  prefix: myprefix # (Optional) Prefix under which this job will expire objects matching the rules below.
  rules:
    - type: object  # objects with zero ore more older versions
      name: NAME # match object names that satisfy the wildcard expression.
      olderThan: 70h # match objects older than this value
      createdBefore: "2006-01-02T15:04:05.00Z" # match objects created before this date and time in RFC3339 format
      tags:
        - key: name
          value: pick* # match objects with tag 'name', all values starting with 'pick'
      metadata:
        - key: content-type
          value: image/* # match objects with 'content-type', all values starting with 'image/'
      size:
        lessThan: 10MiB # match objects with size less than this value (e.g. 10MiB)
        greaterThan: 1MiB # match objects with size greater than this value (e.g. 1MiB)
      purge:
          # retainVersions: 0 # (default) delete all versions of the object. This option is the fastest.
          # retainVersions: 5 # keep the latest 5 versions of the object.

    - type: deleted # objects with delete marker as their latest version
      name: NAME # match object names that satisfy the wildcard expression.
      olderThan: 10h # match objects older than this value (e.g. 7d10h31s)
      createdBefore: "2006-01-02T15:04:05.00Z" # match objects created before this date and time in RFC3339 format
      purge:
          # retainVersions: 0 # (default) delete all versions of the object. This option is the fastest.
          # retainVersions: 5 # keep the latest 5 versions of the object including delete markers.

  notify:
    endpoint: https://notify.endpoint # notification endpoint to receive job completion status
    token: Bearer xxxxx # optional authentication token for the notification endpoint

  retry:
    attempts: 10 # number of retries for the job before giving up
    delay: 500ms # least amount of delay between each retry

```

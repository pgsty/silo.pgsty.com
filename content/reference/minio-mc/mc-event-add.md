---
title: "mc event add"
url: "/reference/minio-mc/mc-event-add/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-event-add.rst
upstream_modified: false
---

<a id="mc-event-add"></a>
<a id="minio-mc-event-add"></a>

<a id="command-mc.event.add"></a>

## Syntax {#syntax}

The [`mc event add`](#command-mc.event.add) command adds event notification triggers to a bucket.

MinIO automatically sends triggered events to the configured [notification target](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command creates a new event notification trigger for all `PUT` and `DELETE` operations for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc event add --event "put,delete" myminio/mydata arn:aws:sqs::primary:target
```

The specified ARN corresponds to a configured [bucket notification target](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) on the `myminio` deployment.
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] event add \
                 [--event "string"]  \
                 [--ignore-existing] \
                 [--prefix "string"] \
                 [--suffix "string"] \
                 ALIAS               \
                 ARN
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.event.add.ALIAS}

*mc-cmd*

*Required*

The MinIO [alias](/reference/minio-mc/mc-alias-set/#alias) and bucket to which the command adds the new event notification. For example:

```shell
mc event add play/mybucket
```

##### `ARN` {#mc.event.add.ARN}

*mc-cmd*

*Required*

The [Amazon Resource Name (ARN)](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns) of the notification target.

The MinIO server outputs an ARN for each configured notification target at server startup. See [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) for more information.

##### `--event` {#mc.event.add.-event}

*mc-cmd*

*Optional*

The event(s) for which MinIO generates bucket notifications.

Supports the following values:

- `put`
- `get`
- `delete`

Specify multiple value using a comma `,` delimiter. Do not add any whitespace between values.

If not specified, defaults to `put,delete,get`.

See [Supported Bucket Events](#mc-event-supported-events) for a detailed list of S3 events associated to each of the supported values.

##### `ignore-existing, p` {#mc.event.add.ignore-existing}

*mc-cmd*

*Optional*

Directs MinIO to ignore the specified event triggers if a matching trigger already exists.

##### `--prefix` {#mc.event.add.-prefix}

*mc-cmd*

*Optional*

The bucket prefix in which the specified [`--event`](#mc.event.add.-event) can trigger a bucket notification.

For example, given a [`ALIAS`](#mc.event.add.ALIAS) of `play/mybucket` and a [`--prefix`](#mc.event.add.-prefix) of `photos`, only events in `play/mybucket/photos` trigger bucket notifications.

Omit to trigger the event for all prefixes and objects in the bucket.

##### `--suffix` {#mc.event.add.-suffix}

*mc-cmd*

*Optional*

The bucket suffix in which the specified [`--event`](#mc.event.add.-event) can trigger a bucket notification.

For example, given a [`ALIAS`](#mc.event.add.ALIAS) of `play/mybucket` and a [`--suffix`](#mc.event.add.-suffix) of `.jpg`, only events in `play/mybucket/*.jpg` trigger bucket notifications.

Omit to trigger the event for all objects regardless of suffix.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Add an Event Notification to a Bucket {#add-an-event-notification-to-a-bucket}

{{< tabs group="example-syntax" >}}
{{< tab label="Example" value="example" >}}
The following command adds a new event notification trigger for all S3 `PUT`, `GET`, and `DELETE` operations on a bucket. The command assumes the MinIO deployment has at least one configured [bucket notification target](/administration/monitoring/bucket-notifications/#minio-bucket-notifications):

```shell
mc event add myminio/mydata arn:minio:sqs::primary:webhook
```
{{< /tab >}}
{{< tab label="Syntax" value="syntax" >}}
```shell
mc event add ALIAS ARN
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment and the bucket on which to add the bucket notification event. For example:

  `myminio/mydata`
- Replace `ARN` with the notification target [`ARN`](#mc.event.add.ARN).
{{< /tab >}}
{{< /tabs >}}

## Behavior {#behavior}

<a id="mc-event-supported-events"></a>

### Supported Bucket Events {#supported-bucket-events}

The following table lists the supported [`mc event add`](#command-mc.event.add) values and their corresponding [S3 events](/administration/monitoring/bucket-notifications/#minio-bucket-notifications-event-types):

<table>
  <thead>
    <tr>
      <th><p>Supported Value</p></th>
      <th><p>Corresponding S3 Events</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><code>put</code></p></td>
      <td><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectCreated-CompleteMultipartUpload"><code>s3:ObjectCreated:CompleteMultipartUpload</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectCreated-Copy"><code>s3:ObjectCreated:Copy</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectCreated-DeleteTagging"><code>s3:ObjectCreated:DeleteTagging</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectCreated-Post"><code>s3:ObjectCreated:Post</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectCreated-Put"><code>s3:ObjectCreated:Put</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectCreated-PutLegalHold"><code>s3:ObjectCreated:PutLegalHold</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectCreated-PutRetention"><code>s3:ObjectCreated:PutRetention</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectCreated-PutTagging"><code>s3:ObjectCreated:PutTagging</code></a><br /></td>
    </tr>
    <tr>
      <td><p><code>get</code></p></td>
      <td><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectAccessed-Head"><code>s3:ObjectAccessed:Head</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectAccessed-Get"><code>s3:ObjectAccessed:Get</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectAccessed-GetRetention"><code>s3:ObjectAccessed:GetRetention</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectAccessed-GetLegalHold"><code>s3:ObjectAccessed:GetLegalHold</code></a><br /></td>
    </tr>
    <tr>
      <td><p><code>delete</code></p></td>
      <td><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectRemoved-Delete"><code>s3:ObjectRemoved:Delete</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectRemoved-DeleteMarkerCreated"><code>s3:ObjectRemoved:DeleteMarkerCreated</code></a><br /></td>
    </tr>
    <tr>
      <td><p><code>replica</code></p></td>
      <td><a href="/administration/monitoring/bucket-notifications/#data.s3-Replication-OperationCompletedReplication"><code>s3:Replication:OperationCompletedReplication</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-Replication-OperationFailedReplication"><code>s3:Replication:OperationFailedReplication</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-Replication-OperationMissedThreshold"><code>s3:Replication:OperationMissedThreshold</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-Replication-OperationNotTracked"><code>s3:Replication:OperationNotTracked</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-Replication-OperationReplicatedAfterThreshold"><code>s3:Replication:OperationReplicatedAfterThreshold</code></a><br /></td>
    </tr>
    <tr>
      <td><p><code>ilm</code></p></td>
      <td><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectTransition-Failed"><code>s3:ObjectTransition:Failed</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectTransition-Complete"><code>s3:ObjectTransition:Complete</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectRestore-Post"><code>s3:ObjectRestore:Post</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-ObjectRestore-Completed"><code>s3:ObjectRestore:Completed</code></a><br /></td>
    </tr>
    <tr>
      <td><p><code>scanner</code></p></td>
      <td><a href="/administration/monitoring/bucket-notifications/#data.s3-Scanner-ManyVersions"><code>s3:Scanner:ManyVersions</code></a><br /><a href="/administration/monitoring/bucket-notifications/#data.s3-Scanner-BigPrefix"><code>s3:Scanner:BigPrefix</code></a><br /></td>
    </tr>
  </tbody>
</table>

For more complete documentation on the listed S3 events, see [S3 Supported Event Types](https://docs.aws.amazon.com/AmazonS3/latest/userguide/NotificationHowTo.html#notification-how-to-event-types-and-destinations).

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

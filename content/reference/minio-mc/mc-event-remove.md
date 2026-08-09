---
title: "mc event rm"
url: "/reference/minio-mc/mc-event-remove/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="mc-event-rm"></a>
<a id="minio-mc-event-remove"></a>

<a id="command-mc.event.remove"></a>

<a id="command-mc.event.rm"></a>

## Syntax {#syntax}

The [`mc event rm`](#command-mc.event.rm) command removes an event notification trigger from a bucket.

The [`mc event remove`](#command-mc.event.remove) command has equivalent functionality to [`mc event rm`](#command-mc.event.rm).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command removes a configured event notifications for the specified [bucket notification target](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc event rm myminio/mydata arn:aws:sqs::primary:target
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] event remove        \
                 ALIAS               \
                 [ARN]               \
                 [--event "string"]  \
                 [--force]           \
                 [--prefix "string"] \
                 [--suffix "string"]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

```shell
mc [GLOBALFLAGS] event remove [FLAGS] ALIAS ARN
```

### Parameters {#parameters}

##### `ALIAS` {#mc.event.rm.ALIAS}

*mc-cmd*

*Required*

The S3 service [alias](/reference/minio-mc/mc-alias-set/#alias) and bucket from which the command removes the event notification. For example:

```shell
mc event rm play/mybucket
```

##### `ARN` {#mc.event.rm.ARN}

*mc-cmd*

*Required*

The [Amazon Resource Name (ARN)](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns) of the notification target.

The MinIO server outputs an ARN at startup for each configured notification target. See [Bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) for more information.

Retrieve the ARN by running [`mc event ls`](/reference/minio-mc/mc-event-list/#command-mc.event.ls) on the bucket.

##### `--event` {#mc.event.rm.-event}

*mc-cmd*

*Optional*

The event type(s) specified when the event was added. The entries **must** match the values used when adding the event. If no event matches the list of event types, the command returns a `no notification configuration matched` error.

Specify multiple events using a comma `,` delimiter. See [Supported Bucket Events](/reference/minio-mc/mc-event-add/#mc-event-supported-events) for supported event types.

Defaults to removing an event that triggers for all event types on the [`ALIAS`](#mc.event.rm.ALIAS) bucket with the [`ARN`](#mc.event.rm.ARN) notification target.

Retrieve the event types used by running [`mc event ls`](/reference/minio-mc/mc-event-list/#command-mc.event.ls) on the bucket. Use the following table to convert event types in the command’s output to the entry required for the [`mc event rm`](#command-mc.event.rm) command:

| Output of `mv event ls` | Event type to use |
| --- | --- |
| `s3:objectAccessed` | `get` |
| `s3:objectCreated` | `put` |
| `s3:objectRemoved` | `delete` |

For example, if the `mc event ls` returns the following:

```shell
arn:minio:sqs::mytest:webhook   s3:ObjectAccessed:*,s3:ObjectCreated:*   Filter:
```

Use the following command to remove the event:

```shell
mc event rm alias/bucket arn:minio:sqs::mytest:webhook --event get,put
```

The order of event types does not matter, only that you include the same ones that exist for the event.

##### `--force` {#mc.event.rm.-force}

*mc-cmd*

*Optional*

Removes all events on the [`ALIAS`](#mc.event.rm.ALIAS) bucket with the [`ARN`](#mc.event.rm.ARN) notification target.

##### `--prefix` {#mc.event.rm.-prefix}

*mc-cmd*

*Optional*

The bucket prefix in which the command removes bucket notifications.

For example, given a [`ALIAS`](#mc.event.rm.ALIAS) of `play/mybucket` and a [`--prefix`](#mc.event.rm.-prefix) of `photos`, the command only removes bucket notifications in `play/mybucket/photos`.

##### `--suffix` {#mc.event.rm.-suffix}

*mc-cmd*

*Optional*

The bucket suffix in which the command removes bucket notifications.

For example, given a [`ALIAS`](#mc.event.rm.ALIAS) of `play/mybucket` and a [`--suffix`](#mc.event.rm.-suffix) of `.jpg`, the command only removes bucket notifications in `play/mybucket/*.jpg`.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Remove Event Notifications from a Bucket {#remove-event-notifications-from-a-bucket}

{{< tabpane text=true persist=header >}}
{{% tab header="Example" %}}
The following command removes all event notification triggers on a bucket. The command assumes the MinIO deployment has at least one configured [bucket notification target](/administration/monitoring/bucket-notifications/#minio-bucket-notifications):

```shell
mc event rm myminio/mydata arn:minio:sqs::primary:webhook
```

{{% /tab %}}
{{% tab header="Syntax" %}}

```shell
mc event rm ALIAS ARN
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment on which to add the bucket notification event. For example:

  `myminio/mydata`
- Replace `ARN` with the notification target [`ARN`](/reference/minio-mc/mc-event-add/#mc.event.add.ARN).
{{% /tab %}}
{{< /tabpane >}}

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

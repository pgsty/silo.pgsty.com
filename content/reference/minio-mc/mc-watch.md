---
title: "mc watch"
url: "/reference/minio-mc/mc-watch/"
weight: 440
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-watch.rst
upstream_modified: false
---

<a id="mc-watch"></a>

<a id="command-mc.watch"></a>

## Syntax {#syntax}

The [`mc watch`](#command-mc.watch) command watches for events on the specified MinIO bucket or local filesystem path. For S3 services, use [`mc event add`](/reference/minio-mc/mc-event-add/#command-mc.event.add) to configure bucket event notifications on S3-compatible services.

You can also use [`mc watch`](#command-mc.watch) against a local filesystem directory to produce similar results to running the `inotify -e modify,create,delete,move` command.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command watches for [events](/reference/minio-mc/mc-event-add/#mc-event-supported-events) on any object or prefix in the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc watch --recursive myminio/mydata
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] watch                \
                 [--event "string"]   \
                 [--prefix "string"]  \
                 [--recursive]        \
                 [--suffix "string"]  \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.watch.ALIAS}

*mc-cmd*

*Required* The [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment and the full path to the bucket to watch for configured events. For example:

```shell
mc watch myminio/mybucket
```

##### `--event` {#mc.watch.-event}

*mc-cmd*

The event(s) to watch for. Specify multiple events using a comma `,` delimiter. See [Supported Bucket Events](/reference/minio-mc/mc-event-add/#mc-event-supported-events) for supported events.

Defaults to `put,delete, get`.

##### `--prefix` {#mc.watch.-prefix}

*mc-cmd*

The bucket prefix in which to watch for the specified [`--event`](#mc.watch.-event).

For example, given a [`ALIAS`](#mc.watch.ALIAS) of `play/mybucket` and a [`--prefix`](#mc.watch.-prefix) of `photos`, only events in `play/mybucket/photos` trigger bucket notifications.

##### `--recursive, r` {#mc.watch.-recursive}

*mc-cmd*

Recursively watch for events in the specified [`ALIAS`](#mc.watch.ALIAS) bucket path or local directory.

##### `--suffix` {#mc.watch.-suffix}

*mc-cmd*

The bucket suffix in which to watch for the specified [`--event`](#mc.watch.-event).

For example, given a [`ALIAS`](#mc.watch.ALIAS) of `play/mybucket` and a [`--suffix`](#mc.watch.-suffix) of `.jpg`, only events in `play/mybucket/*.jpg` trigger bucket notifications.

### Global Flags {#global-flags}

##### `--json` {#mc.watch.-json}

*mc-cmd*

*Optional*

Enables [JSON lines](http://jsonlines.org/)<a id="json-lines"></a> formatted output to the console.

For example:

```shell
mc --json COMMAND
```

## Examples {#examples}

### Watch for Events in a Bucket {#watch-for-events-in-a-bucket}

```shell
mc watch --recursive ALIAS/PATH
```

- Replace [`ALIAS`](#mc.watch.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.watch.ALIAS) with the path to the bucket.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

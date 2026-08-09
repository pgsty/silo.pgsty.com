---
title: "mc share download"
url: "/reference/minio-mc/mc-share-download/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-share-download"></a>

<a id="command-mc.share.download"></a>

## Syntax {#syntax}

The [`mc share download`](#command-mc.share.download) command generates a temporary presigned URL with integrated access credentials for downloading objects from a MinIO bucket. The temporary URL expires after a configurable time limit.

- Applications can perform a `GET` to retrieve the object from the URL.
- Users can open the URL in a browser to download the object.

For more information on shareable object URLs, see the Amazon S3 documentation on [Pre-Signed URLs](https://docs.aws.amazon.com/AmazonS3/latest/dev/ShareObjectPreSignedURL.html).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command generates a new presigned download URL for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc share download --recursive myminio/mydata
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] share download           \
                 [--expire "string"]      \
                 [--recursive]            \
                 [--version-id "string"]  \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.share.download.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deplyment and the full path to the object for which to generate a download URL. For example:

```shell
mc share download play/mybucket/object.txt
```

You can specify multiple objects on the same or different MinIO deployments. For example:

```shell
mc share download play/mybucket/object.txt play/mybucket/otherobject.txt
```

If specifying the path to a bucket or bucket prefix, you **must** also specify the [`--recursive`](#mc.share.download.-recursive) argument. For example:

```shell
mc share download --recursive play/mybucket/

mc share download --recursive play/mybucket/myprefix/
```

##### `--expire, E` {#mc.share.download.-expire}

*mc-cmd*

*Optional*

Set the expiration time limit for all generated URLs.

Specify a string with format `##h##m##s` format. For example: `12h34m56s` for an expiry of 12 hours, 34 minutes, and 56 seconds after URL generation.

Defaults to `168h` or 168 hours (7 days).

##### `--recursive, r` {#mc.share.download.-recursive}

*mc-cmd*

*Optional*

Recursively generate URLs for all objects in a [`mc share download ALIAS`](#mc.share.download.ALIAS) bucket or bucket prefix.

Required if any `ALIAS` specifies a path to a bucket or bucket prefix.

##### `--version-id, vid` {#mc.share.download.-version-id}

*mc-cmd*

*Optional*

Directs [`mc share download`](#command-mc.share.download) to operate only on the specified object version.

[`--version-id`](#mc.share.download.-version-id) requires that the specified [`ALIAS`](#mc.share.download.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Generate a URL to Download Object(s) {#generate-a-url-to-download-object-s}

{{< tabpane text=true persist=header >}}
{{% tab header="Get Specific Object" %}}
Use [`mc share download`](#command-mc.share.download) to generate a URL that supports `GET` requests for an object:

```shell
mc share download --expire DURATION ALIAS/PATH
```

- Replace [`ALIAS`](#mc.share.download.ALIAS) with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.
- Replace [`PATH`](#mc.share.download.ALIAS) with the path to the object on the MinIO deployment.
- Replace [`DURATION`](#mc.share.download.-expire) with the duration after which the URL expires. For example, to set a 30 day expiry, specify `30d`.
{{% /tab %}}
{{% tab header="Get Object(s) in a Bucket" %}}
Use [`mc share download`](#command-mc.share.download) with the [`--recursive`](#mc.share.download.-recursive) option to generate a URL for each object in a bucket. Each URL supports `GET` requests for its associated object:

```shell
mc share download --recursive --expire DURATION ALIAS/PATH
```

- Replace [`ALIAS`](#mc.share.download.ALIAS) with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.
- Replace [`PATH`](#mc.share.download.ALIAS) with the path to the bucket or bucket prefix on the MinIO deployment.
- Replace [`DURATION`](#mc.share.download.-expire) with the duration after which the URL expires. For example, to set a 30 day expiry, specify `30d`.
{{% /tab %}}
{{< /tabpane >}}

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

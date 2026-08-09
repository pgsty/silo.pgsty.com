---
title: "mc share upload"
url: "/reference/minio-mc/mc-share-upload/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="mc-share-upload"></a>

<a id="command-mc.share.upload"></a>

## Syntax {#syntax}

The [`mc share upload`](#command-mc.share.upload) command generates a temporary presigned URL with integrated access credentials for uploading objects to a MinIO bucket. The temporary URL expires after a configurable time limit.

Applications can perform a `PUT` to upload an object using the URL.

For more information on shareable object URLs, see the Amazon S3 documentation on [Pre-Signed URLs](https://docs.aws.amazon.com/AmazonS3/latest/dev/ShareObjectPreSignedURL.html).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command generates a new presigned upload URL for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc share upload --recursive myminio/mydata
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] share upload               \
                 [--content-type "string"]  \
                 [--expire "string"]        \
                 [--recursive]              \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.share.upload.ALIAS}

*mc-cmd*

*Required* The [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deplyment and the full path to the object for which to generate an upload URL. For example:

```shell
mc share upload play/mybucket/object.txt
```

You can specify multiple objects on the same or different MinIO deployments. For example:

```shell
mc share upload play/mybucket/object.txt play/mybucket/otherobject.txt
```

If specifying the path to a bucket or bucket prefix, you **must** also specify the [`--recursive`](#mc.share.upload.-recursive) argument. For example:

```shell
mc share upload --recursive play/mybucket/

mc share upload --recursive play/mybucket/myprefix/
```

##### `--content-type, T` {#mc.share.upload.-content-type}

*mc-cmd*

*Optional* Restrict uploads to only requests with a specific [Content-Type](https://www.w3.org/Protocols/rfc1341/4_Content-Type.html) header.

Specify a string with the desired `Content-Type` value to accept. For example, `video/mp4`.

If configured, clients using the generated URL must include a `Content-Type` header for the specified type. MinIO rejects requests that do not have the correct `Content-Type` header.

Content types are also known as [media types](https://www.iana.org/assignments/media-types/media-types.xhtml).

##### `--expire, E` {#mc.share.upload.-expire}

*mc-cmd*

*Optional* Set the expiration time limit for all generated URLs.

Specify a string with format `##h##m##s` format. For example: `12h34m56s` for an expiry of 12 hours, 34 minutes, and 56 seconds after URL generation.

Defaults to `168h` or 168 hours (7 days).

##### `--recursive, r` {#mc.share.upload.-recursive}

*mc-cmd*

*Optional* Modifies the CURL URL to support uploading objects to a bucket or bucket prefix. Required if any `ALIAS` specifies a path to a bucket or bucket prefix. The modified CURL output resembles the following:

```shell
curl ... -F key=<NAME> -F file=@<FILE>
```

Replace `<FILE>` with the path to the file to upload.

Replace `<NAME>` with the object name once uploaded. This may include [prefixes](/glossary/#term-prefix).

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Generate a URL to Upload Object(s) {#generate-a-url-to-upload-object-s}

{{< tabpane text=true persist=header >}}
{{% tab header="Upload Single Object" %}}
Use [`mc share upload`](#command-mc.share.upload) to generate a URL that supports `POST` requests for uploading a file to a specific object location on a MinIO deployment:

```shell
mc share upload --expire DURATION ALIAS/PATH
```

- Replace [`ALIAS`](#mc.share.upload.ALIAS) with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.
- Replace [`PATH`](#mc.share.upload.ALIAS) with the path to the object on the MinIO deployment.
- Replace [`DURATION`](#mc.share.upload.-expire) with the duration after which the URL expires. For example, to set a 30 day expiry, specify `30d`.
{{% /tab %}}
{{% tab header="Upload Multiple Objects" %}}
Use [`mc share upload`](#command-mc.share.upload) with the [`--recursive`](#mc.share.upload.-recursive) and [`--expire`](#mc.share.upload.-expire) options to generate a temporary URL that supports `POST` requests for uploading files to a bucket on a MinIO deployment:

```shell
mc share upload --recursive --expire DURATION ALIAS/PATH
```

- Replace [`ALIAS`](#mc.share.upload.ALIAS) with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.
- Replace [`PATH`](#mc.share.upload.ALIAS) with the path to the bucket or bucket prefix on the MinIO deployment.
- Replace [`DURATION`](#mc.share.upload.-expire) with the duration after which the URL expires. For example, to set a 30 day expiry, specify `30d`.

The command returns a CURL command for uploading an object to the specified bucket prefix.

- Replace the `<FILE>` string in the returned CURL command with the path to the file to upload.
- Replace the `<NAME>` string in the returned CURL command with the name of the object in the bucket. This may include [prefixes](/glossary/#term-prefix).

You can use a shell script loop to recursively upload the contents of a filesystem directory to the S3-compatible service:

```shell
#!/bin/sh

for file in ~/Documents/photos/
do
   curl https://play.min.io/mybucket/ \
   -F policy=AAAAA -F x-amz-algorithm=AWS4-HMAC-SHA256 \
   -F x-amz-credential=AAAA/us-east-1/s3/aws4_request \
   -F x-amz-date=20200812T202556Z \
   -F x-amz-signature=AAAA \
   -F bucket=mybucket -F key=photos/${file} -F file=@${file}

done
```

This example will upload each file in the directory `~/Documents/photos/` to the `mybucket` bucket under the prefix `photos`. Defer to the documented best practices for your preferred scripting language for iterating through files in a directory.
{{% /tab %}}
{{< /tabpane >}}

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

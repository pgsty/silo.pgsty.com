---
title: "mc od"
url: "/reference/minio-mc/mc-od/"
weight: 260
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-od.rst
upstream_modified: false
---

<a id="mc-od"></a>

<a id="command-mc.od"></a>

## Syntax {#syntax}

The [`mc od`](#command-mc.od) command copies a local file to a remote location in a specified number of parts and part sizes. The command outputs the time it took to upload the file.

Use the [`mc od`](#command-mc.od) to mimic the functionality of the Linux `dd` command.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command Upload 200MiB of a file to a bucket in 5 parts of size 40MiB. The output shows the results of the upload, including the length of time it took for the upload to complete.

```shell
mc od if=file.zip of=myminio/mybucket/file.zip size=40MiB parts=5
```

If passing the `--json` [global flag](/reference/minio-mc/#minio-mc-global-options), the output of the command resembles the following:

```json
{
  "source": "home/user/file.zip"
  "target": "myminio/mybucket/file.zip"
  "partSize": 41943040
  "totalSize": 209715200
  "parts": 5
  "elapsed": "314ms"
}
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] od                                            \
                 if=<path of source file to upload>            \
                 of=<target MinIO path to upload to>           \
                 [size=<size of file>]                         \
                 [parts=<number of parts to split file into>]  \
                 [skip=<number of parts to skip>]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `if` {#mc.od.if}

*mc-cmd*

*Required*

The path of the source object to use for the upload. Use the full path relative to your current location.

```text
mc od if=file.zip of=myminio/mybucket/file.zip
```

##### `of` {#mc.od.of}

*mc-cmd*

*Required*

The full target path to upload the object to.

##### `size` {#mc.od.size}

*mc-cmd*

*Optional*

The size for each part of the file to upload. If not specified, MinIO determines the size for parts from the source stream.

##### `parts` {#mc.od.parts}

*mc-cmd*

*Optional*

The number of parts to divide the object into for uploading. If not specified, MinIO determines the number of parts based on the size of the source stream.

##### `skip` {#mc.od.skip}

*mc-cmd*

*Optional*

The number of parts of the file to skip during the upload. For example, use this option to test the upload speed for a large file of many parts on only a portion of the object’s parts.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Upload a Full File with 40MiB Parts {#upload-a-full-file-with-40mib-parts}

Use [`mc od`](#command-mc.od) to upload a file to MinIO in a set of parts of specified size. The [`size`](#mc.od.size) option allows you to specify the desired part size.

```shell
mc od if=file.zip of=myminio/mybucket/file.zip size=40MiB
```

- Replace `myminio/mybucket/file.zip` with the path of the object or file stream to upload.
- Replace [`size`](#mc.od.size) with the desired size of the object parts.

MinIO examines the source file and divides it into the necessary number of parts so that no part is larger than the specified 40MiB part size.

### Upload a First Five 40 MiB Parts of a File {#upload-a-first-five-40-mib-parts-of-a-file}

Use [`mc od`](#command-mc.od) to upload parts of a file to MinIO of specified part size. The [`size`](#mc.od.size) option allows you to specify the desired part size. The [`parts`](#mc.od.parts) option allows you to specify the total number of parts to use for the object.

```shell
mc od if=file.zip of=myminio/mybucket/file.zip size=40MiB parts=5
```

- Replace `myminio/mybucket/file.zip` with the path of the object or file stream to upload.
- Replace [`size`](#mc.od.size) with the desired size of the object parts.
- Replace [`parts`](#mc.od.parts) with the number of desired parts to use for the object.

In this command example, if the source object stream is larger than 200MiB (40MiB × 5 parts), only the first 200MiB of the file upload.

> [!WARNING]
> **Important**
>
> Using the command this way may not upload the entirety of an object.

### Upload a Full File in 5 Parts {#upload-a-full-file-in-5-parts}

Take a source file, divide the file into a specified number of parts, then upload all parts of the file to a MinIO target.

```shell
mc od if=file.zip of=myminio/mybucket/file.zip parts=5
```

The above command divides the source file into five equal parts, then uploads those parts.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

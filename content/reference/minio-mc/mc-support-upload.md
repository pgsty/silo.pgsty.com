---
title: "mc support upload"
url: "/reference/minio-mc/mc-support-upload/"
weight: 80
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-upload.rst
upstream_modified: false
---

<a id="mc-support-upload"></a>

<a id="command-mc.support.upload"></a>

## Description {#description}

[`mc support upload`](#command-mc.support.upload) copies a file from the local file system to a SUBNET ticket.

> [!NOTE]
> **SUBNET Registration Required**
>
> The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.

## Syntax {#syntax}

The [`mc support profile`](/reference/minio-mc/mc-support-profile/#command-mc.support.profile) command has the following syntax:

```shell
mc [GLOBALFLAGS] support profile              \
                         ALIAS                \
                         FILE                 \
                         [--comment "string"] \
                         [--enc]              \
                         [--issue integer]
```

### Parameters {#parameters}

##### `ALIAS` {#mc.support.upload.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

##### `FILE` {#mc.support.upload.FILE}

*mc-cmd*

*Required*

The path to the file to upload to SUBNET.

##### `--comment` {#mc.support.upload.-comment}

*mc-cmd*

*Optional*

Include a message to the issue when uploading the file.

##### `--enc` {#mc.support.upload.-enc}

*mc-cmd*

*Optional*

Encrypt contents of the upload. The key used for the encryption is only accessible to MinIO.

##### `--issue` {#mc.support.upload.-issue}

*mc-cmd*

*Optional*

Specify the issue number to which to add the file. If not specified, the file uploads to the generic issue number `0`.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Upload a file to an issue {#upload-a-file-to-an-issue}

This command uploads the file `./trace.log` from the local file system to the SUBNET issue number 10001 for the deployment with alias `minio1`.

```shell
mc support upload --issue 10001 minio1 ./trace.log
```

### Upload a file to an issue with a comment for MinIO Engineers {#upload-a-file-to-an-issue-with-a-comment-for-minio-engineers}

This command uploads the file `./trace.log` from the local file system to the SUBNET issue number 10001 for the deployment with alias `minio1`. The command also includes a comment available to MinIO Engineers about the file.

```shell
mc support upload --issue 10001 --comment "here is the requested trace log" minio1 ./trace.log
```

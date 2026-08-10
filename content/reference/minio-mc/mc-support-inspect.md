---
title: "mc support inspect"
url: "/reference/minio-mc/mc-support-inspect/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="mc-support-inspect"></a>

<a id="command-mc.support.inspect"></a>

{{% alert color="info" %}}
**SUBNET Registration Required**

The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.
{{% /alert %}}

## Description {#description}

The [`mc support inspect`](#command-mc.support.inspect) command collects the data and metadata associated to objects at the specified path.

MinIO assembles this data from each backend drive storing an [erasure shard](/operations/concepts/erasure-coding/#minio-erasure-coding) for each specified object. The command produces an encrypted zip file that includes all matching files with their respective *host+drive+path*.

If this information is required to diagnose a [MinIO SUBNET](https://min.io/pricing?jmp=docs) issue, MinIO Engineering will provide the appropriate command. The resulting report is intended for use by MinIO Engineering via SUBNET and may contain internal or private data points associated to the object. Exercise caution before sending a report to a third party or posting the report in a public forum.

{{% alert color="info" %}}
**Changed: RELEASE.2023-01-11T03-14-16Z**

The file uploads to MinIO for use by the engineering team in support efforts. If the upload fails, such as in an air-gapped environment, the command saves the file to the current working directory.
{{% /alert %}}

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-12T19-27-27Z**

When writing the zip archive, MinIO also encrypts the zip index of file names included in the archive.
{{% /alert %}}

{{% alert color="info" %}}
**Changed: RELEASE.2024-10-29T15-34-59Z**

Inspect now generates unique file names to help distinguish one inspect file from another. The file name reflects the inspected path.
{{% /alert %}}

{{% alert color="warning" %}}
**Important**

[`mc support inspect`](#command-mc.support.inspect) requires a MinIO deployment server from October 2021 or later.
{{% /alert %}}

## Wildcards {#wildcards}

The command supports wildcard `*` pattern matching for prefixes or objects when using the Bash shell. For non-Bash shells, a message displays indicating that wildcard patterns are only supported in Bash.

```shell
mc support inspect ALIAS/bucket/path/**/xl.meta
```

This command collects all `xl.meta` associated to objects at `ALIAS/bucket/path/`.

## Examples {#examples}

### Download Metadata for an Object {#download-metadata-for-an-object}

You can download the metadata for an object. Metadata stores in an `xl.meta` binary file.

The following command downloads the `xl.meta` from `mybucket/myobject` on the `minio1` deployment.

The file downloads from all drives as a zip archive file.

```shell
mc support inspect minio1/mybucket/myobject/xl.meta
```

The contents of the `xl.meta` file are not human readable. You can convert the contents of an `xl.meta` file to JSON format.

### Download All Objects at a Prefix Recursively {#download-all-objects-at-a-prefix-recursively}

The following command downloads all objects recursively found at a prefix.

{{% alert color="danger" %}}
**Caution**

This can be an expensive operation. Proceed with caution.
{{% /alert %}}

```shell
mc support inspect minio1/mybucket/myobject/**
```

## Syntax {#syntax}

The command has the following syntax:

```shell
mc [GLOBALFLAGS] support inspect       \
                         [--legacy]   \
                         TARGET
```

### Parameters {#parameters}

##### `--legacy` {#mc.support.inspect.-legacy}

*mc-cmd*

*Optional*

Use the older method of exporting inspection data, which does not encrypt data by default.

##### `TARGET` {#mc.support.inspect.TARGET}

*mc-cmd*

*Required*

The path to the location or object to inspect. The path should include the *alias &lt;alias&gt;* of the MinIO deployment and, if needed, the prefix and/or object name.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

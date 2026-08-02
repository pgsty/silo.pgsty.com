---
title: "mc support top api"
url: "/reference/minio-mc/mc-support-top-api/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-support-top-api"></a>

<a id="command-mc.support.top.api"></a>

{{% alert color="info" %}}
**SUBNET Registration Required**

The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.
{{% /alert %}}

## Syntax {#syntax}

The [`mc support top api`](#command-mc.support.top.api) command summarizes the real-time API events on a MinIO deployment server.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command displays the current in-progress S3 API calls on the [alias](/glossary/#term-alias) `myminio`.

```shell
mc support top api myminio/
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] support top api    \
                 TARGET             \
                 [--name "string"]  \
                 [--path "string"]  \
                 [--node "string"]  \
                 [--errors, -e]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `TARGET` {#mc.support.top.api.TARGET}

*mc-cmd*

*Required*

The full path to the alias, prefix, or object where the command should run. The path must include at least an [ALIAS](/reference/minio-mc/mc-alias-set/#minio-mc-alias).

##### `--name` {#mc.support.top.api.-name}

*mc-cmd*

*Optional*

Outputs a summary of current API calls matching the entered string.

##### `--path` {#mc.support.top.api.-path}

*mc-cmd*

*Optional*

Outputs a summary of current API calls for a specified path.

##### `--node` {#mc.support.top.api.-node}

*mc-cmd*

*Optional*

Outputs a summary of the current API calls on matching servers.

##### `--errors, -e` {#mc.support.top.api.-errors}

*mc-cmd*

*Optional*

Outputs a summary of current API calls returning errors.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Display All Current In-progress S3 API Calls {#display-all-current-in-progress-s3-api-calls}

The following command displays all in-progress S3 calls for the `myminio` deployment:

```shell
mc support top api myminio/
```

### Display Current, In-progress `s3.PutObject` Calls {#display-current-in-progress-s3-putobject-calls}

The following command displays all in-progress `s3.PutObject` calls for the `myminio` deployment:

```shell
mc support top api --name s3.PutObject myminio/
```

---
title: "Core Settings"
url: "/reference/minio-server/settings/core/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="core-settings"></a>
<a id="minio-server-envvar-core"></a>

This page covers settings that control core behavior of the MinIO process.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

## MinIO Server CLI Options {#minio-server-cli-options}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
#### `MINIO_OPTS` {#envvar.MINIO_OPTS}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
There is no configuration setting for this variable, as these settings apply at server startup.
{{% /tab %}}
{{< /tabpane >}}

*Optional*

Set a string of [parameters](/reference/minio-server/#minio-server-parameters) to use when starting the MinIO Server.

For Unix-like systems using the recommended MinIO `systemd` service, use the `/etc/default/minio` file and create an environment variable `MINIO_OPTS` for specifying parameters to append to the `minio` systemd process:

```shell
# Editing /etc/default/minio

MINIO_OPTS=' --console-address=":9001" --ftp="address=:8021" --ftp="passive-port-range=30000-40000" '
```

For systems running `minio` on the command line, `MINIO_OPTS` is optional. To use it, declare the environment variable using standard shell semantics, then reference the environment variable when starting up the MinIO Server:

```shell
export MINIO_OPTS=' --console-address=":9001" --ftp="address=:8021" --ftp="passive-port-range=30000-40000" '

minio server $MINIO_OPTS ...

# The above is equivalent to running the following:
# minio server --console-address=":9001" \
#              --ftp="address=:8021"     \
#              --ftp="passive-port-range=30000-40000"
```

{{% alert color="warning" %}}
**Important**

The `minio server` command does not read `$MINIO_OPTS` directly. The variable only functions if used as described above.
{{% /alert %}}

## Storage Volumes {#storage-volumes}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
#### `MINIO_VOLUMES` {#envvar.MINIO_VOLUMES}

*envvar*

The directories or drives the [`minio server`](/reference/minio-server/#command-minio.server) process uses as the storage backend.

Functionally equivalent to setting [`minio server DIRECTORIES`](/reference/minio-server/#minio.server.DIRECTORIES). Use this value when configuring MinIO to run using an environment file.
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

## Environment Variable File Path {#environment-variable-file-path}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
#### `MINIO_CONFIG_ENV_FILE` {#envvar.MINIO_CONFIG_ENV_FILE}

*envvar*

Specifies the full path to the file the MinIO server process uses for loading environment variables.

For `systemd`-managed files, set this value to the path of the environment file (`/etc/default/minio`) to direct MinIO to reload changes to that file when using [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) to restart the deployment.
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

## Workers for Expiration {#workers-for-expiration}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
#### `MINIO_ILM_EXPIRY_WORKERS` {#envvar.MINIO_ILM_EXPIRY_WORKERS}

*envvar*

Specifies the number of workers to make available to expire objects configured with ILM rules for expiration. When not set, MinIO defaults to using up to half of the available processing cores available.
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

## Domain {#domain}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
#### `MINIO_DOMAIN` {#envvar.MINIO_DOMAIN}

*envvar*

Enables Virtual Host-style requests to the MinIO deployment. Set the value to the Fully Qualified Domain Name (FQDN) for MinIO to accept incoming virtual host requests.

Omitting this setting directs MinIO to only accept the default path-style requests.

For example, consider a MinIO deployment with an assigned FQDN of `minio.example.net`.

- With path-style lookups, applications can access the bucket using its full path as `minio.example.net/mybucket`.
- With virtual-host lookups, application can access the bucket as a virtual host as `mybucket.minio.example.net/`.

{{% alert color="warning" %}}
**Important**

If you configure `MINIO_DOMAIN`, you **must** consider all subdomains of the specified FQDN as exclusively assigned for use as bucket names. Any MinIO services which conflict with those domains, such as replication targets, may exhibit unexpected or undesired behavior as a result of the collision.

For example, if setting `MINIO_DOMAIN=minio.example.net`, you **cannot** assign any subdomains of `minio.example.net` (in the form of `*.minio.example.net`) to any MinIO service or target. This includes hostnames for use with [bucket](/administration/bucket-replication/#minio-bucket-replication), [batch](/administration/batch-framework-job-replicate/#minio-batch-framework-replicate-job), or [site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview).
{{% /alert %}}
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

<a id="minio-scanner-speed-options"></a>

## Scanner Speed {#scanner-speed}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
#### `MINIO_SCANNER_SPEED` {#envvar.MINIO_SCANNER_SPEED}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
#### `scanner speed` {#mc-conf.scanner.speed}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Manage the maximum wait period for the [scanner](/operations/concepts/scanner/#minio-concepts-scanner) when balancing MinIO read/write performance to scanner processes.

MinIO utilizes the [scanner](/operations/concepts/scanner/#minio-concepts-scanner) for [bucket replication](/administration/bucket-replication/#minio-bucket-replication), [site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview), [lifecycle management](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management), and [healing](/operations/concepts/healing/#minio-concepts-healing) tasks.

Valid values include:

<table>
  <tbody>
    <tr>
      <td><p><code>fastest</code></p></td>
      <td><p>Removes scanner wait on read/write latency, allowing the scanner to operate at full-speed and IOPS consumption.
This setting may result in reduced read and write performance.</p></td>
    </tr>
    <tr>
      <td><p><code>fast</code></p></td>
      <td><p>Sets a short scanner wait time on read/write latency, allowing the scanner to operate at a higher speed and IOPS consumption.
This setting may result in reduced read and write performance.</p></td>
    </tr>
    <tr>
      <td><p><code>default</code></p></td>
      <td><p>Sets a moderate scanner wait time on read/write latency, allowing the scanner to operate at a balanced speed and IOPS consumption.
This setting seeks to maintain read and write performance while allowing ongoing scanner activity.</p></td>
    </tr>
    <tr>
      <td><p><code>slow</code></p></td>
      <td><p>Sets a medium scanner wait time on read/write latency, where the scanner operates at a reduced speed and IOPS consumption.
This setting allows better read and write performance while reducing scanner performance.</p><p>May impact scanner-dependent features, such as lifecycle management and replication.</p></td>
    </tr>
    <tr>
      <td><p><code>slowest</code></p></td>
      <td><p>Sets a large scanner wait time on read/write latency, where the scanner operates at a substantially lower speed and IOPS consumption.
This setting prioritizes read and write operations at the potential cost of scanner operations.</p><p>May impact scanner-dependent features, such as lifecycle management and replication.</p></td>
    </tr>
  </tbody>
</table>

## Batch Replication {#batch-replication}

{{< tabpane text=true persist=header >}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

## Data Compression {#data-compression}

The following section documents settings for enabling data compression for objects. See [Data Compression](/administration/object-management/data-compression/#minio-data-compression) for tutorials on using these configuration settings.

All of the settings in this section fall under the following top-level key:

#### `compression` {#mc-conf.compression}

*mc-conf*

### Enable Compression {#enable-compression}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_COMPRESSION_ENABLE` {#envvar.MINIO_COMPRESSION_ENABLE}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `compression enable` {#mc-conf.compression.enable}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

*Optional*

Set to `on` to enable data compression for new objects. Defaults to `off`.

Enabling or disabling data compression does not change existing objects.

### Allow Encryption {#allow-encryption}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_COMPRESSION_ALLOW_ENCRYPTION` {#envvar.MINIO_COMPRESSION_ALLOW_ENCRYPTION}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `compression allow_encryption` {#mc-conf.compression.allow_encryption}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

*Optional*

Set to `on` to encrypt objects after compressing them. Defaults to `off`.

{{% alert color="info" %}}
**Encrypting compressed objects may compromise security**

MinIO strongly recommends against encrypting compressed objects. If you require encryption, carefully evaluate the risk of potentially leaking information about the contents of encrypted objects.
{{% /alert %}}

### Compression Extensions {#compression-extensions}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_COMPRESSION_EXTENSIONS` {#envvar.MINIO_COMPRESSION_EXTENSIONS}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `compression extensions` {#mc-conf.compression.extensions}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

*Optional*

Comma-separated list of the file extensions to compress. Setting a new list of file extensions replaces the previously configured list. Defaults to `".txt, .log, .csv, .json, .tar, .xml, .bin"`.

{{% alert color="info" %}}
**Changed: RELEASE.2024-03-15T01-07-19Z**

Specify `"*"` to direct MinIO to compress all supported file types.
{{% /alert %}}

MinIO does not support compressing file types on the [Excluded File Types](/administration/object-management/data-compression/#minio-data-compression-excluded-types) list, even if explicitly specified in this argument.

### Compression MIME Types {#compression-mime-types}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_COMPRESSION_MIME_TYPES` {#envvar.MINIO_COMPRESSION_MIME_TYPES}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Variable" %}}
##### `compression mime_types` {#mc-conf.compression.mime_types}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

*Optional*

Comma-separated list of the MIME types to compress. Setting a new list of types replaces the previously configured list. Defaults to `"text/*, application/json, application/xml, binary/octet-stream"`.

{{% alert color="info" %}}
**Default excluded files**

Some types of files cannot be significantly reduced in size. MinIO will *not* compress these, even if specified in an [`mime_types`](#mc-conf.compression.mime_types) argument. See [Excluded types](/administration/object-management/data-compression/#minio-data-compression-excluded-types) for details.
{{% /alert %}}

### Comments {#comments}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
This setting does not have an environment variable option. Use the configuration setting instead.
{{% /tab %}}
{{% tab header="Configuration Setting" selected=true %}}
##### `compression comment` {#envvar.compression.comment}

*envvar*
{{% /tab %}}
{{< /tabpane >}}

*Optional*

Specify a comment to associate with the data compression configuration.

## Erasure Stripe Size {#erasure-stripe-size}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
#### `MINIO_ERASURE_SET_DRIVE_COUNT` {#envvar.MINIO_ERASURE_SET_DRIVE_COUNT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Variable" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

*Optional*

The [erasure set size](/operations/concepts/erasure-coding/#minio-ec-basics) to apply for all drives in a given [server pool](/glossary/#term-server-pool).

If you set this value, you **must** do so *before* you initialize the cluster The selected stripe size is **immutable** after the cluster has been initialized and affects any future server pools added to the cluster.

[MinIO SUBNET](https://min.io/pricing?jmp=docs) users should log in and open an issue to discuss stripe size settings prior to implementing them in any environment.

{{% alert color="danger" %}}
**Warning**

**Do not** change the stripe size setting unless directed to by MinIO engineering.

Changes to stripe size have significant impact to deployment functionality, availability, performance, and behavior. MinIO’s stripe selection algorithms set appropriate defaults for the majority of workloads. Changing the stripe size from this default is unusual and generally not necessary or advised.
{{% /alert %}}

## Maximum Object Versions {#maximum-object-versions}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
#### `MINIO_API_OBJECT_MAX_VERSIONS` {#envvar.MINIO_API_OBJECT_MAX_VERSIONS}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
#### `api object_max_versions` {#mc-conf.api.object_max_versions}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

*Optional*

Defines the default maximum versions to allow per object.

By default, MinIO allows up to the maximum value of an Int64 versions per object, or over 9.2 quintillion.

{{% alert color="info" %}}
**Note**

MinIO versions from ```RELEASE.2023-08-04T17-40-21Z``to ``RELEASE.2024-03-26T22-10-45Z``` had a default limit of 10,000 object versions. This setting can be used to override that limit to another value.
{{% /alert %}}

Arbitrarily high versions per objects may cause performance degradation on some operations, such as `LIST`. This is especially true on systems running budget hardware or spinning drives (HDD). Applications or workloads which produce thousands or more versions per object may require design or architecture review to mitigate potential performance degradations.

Setting a limit of no more than `100` should provide enough versions for most typical use cases.

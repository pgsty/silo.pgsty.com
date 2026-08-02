---
title: "Data Compression"
url: "/administration/object-management/data-compression/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="data-compression"></a>
<a id="minio-data-compression"></a>

## Overview {#overview}

MinIO Server supports compressing objects to reduce disk usage. Objects are compressed on PUT before writing to disk, and uncompressed on GET before they are sent to the client. This makes the compression process transparent to client applications and services.

Depending on the type of data, compression may also increase overall throughput. Write throughput for a production deployment is generally 500MB per second or greater per available CPU core in the system. Decompression is approximately 1 GB per second or greater for each CPU core.

For best results, review MinIO’s [recommended hardware configuration](/operations/checklists/hardware/#deploy-minio-distributed-recommendations) or use [MinIO SUBNET](https://min.io/pricing?jmp=docs) to work directly with engineers for analyzing compression performance.

<a id="minio-data-compression-default-types"></a>

### Default File Types {#default-file-types}

Data compression is a global option, the configured settings apply to all buckets in a deployment. Enabling data compression compresses the following types of data by default:

<table>
  <thead>
    <tr>
      <th><p>File Extensions</p></th>
      <th><p>Media (MIME) Types</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><code>.txt</code></p><p><code>.log</code></p><p><code>.csv</code></p><p><code>.json</code></p><p><code>.tar</code></p><p><code>.xml</code></p><p><code>.bin</code></p></td>
      <td><p><code>text/*</code></p><p><code>application/json</code></p><p><code>application/xml</code></p><p><code>binary/octet-stream</code></p></td>
    </tr>
  </tbody>
</table>

You can control which objects are compressed by specifying the desired file extensions and [media (MIME) types](https://en.wikipedia.org/wiki/Media_type).

{{% alert color="info" %}}
**Existing objects are not modified**

Enabling, disabling, or updating a deployment’s compression settings does not modify existing objects. New objects are compressed according to the settings in effect at the time they are created.
{{% /alert %}}

<a id="minio-data-compression-excluded-types"></a>

### Excluded File Types {#excluded-file-types}

Some data cannot be effectively compressed. For example: video, already compressed data, or files less than 4KiB. MinIO does not compress common incompressible file types, even if they are specified in the compression configuration.

Objects of these types are never compressed:

<table>
  <thead>
    <tr>
      <th><p>Object Type</p></th>
      <th><p>File Extension</p></th>
      <th><p>Media (MIME) Type</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p>Audio</p></td>
      <td></td>
      <td><p><code>audio/*</code></p></td>
    </tr>
    <tr>
      <td><p>Video</p></td>
      <td><code>*.mp4</code><br /><code>*.mkv</code><br /><code>*.mov</code><br /></td>
      <td><p><code>video/*</code></p></td>
    </tr>
    <tr>
      <td><p>Image</p></td>
      <td><code>*.jpg</code><br /><code>*.png</code><br /><code>*.gif</code><br /></td>
      <td><p><code>application/x-compress</code> (LZW)</p></td>
    </tr>
    <tr>
      <td><p>7ZIP Compressed</p></td>
      <td><p><code>*.7z</code></p></td>
      <td></td>
    </tr>
    <tr>
      <td><p>BZIP2 Compressed</p></td>
      <td><p><code>*.bz2</code></p></td>
      <td><p><code>application/x-bz2</code></p></td>
    </tr>
    <tr>
      <td><p>GZIP Compressed</p></td>
      <td><p><code>*.gz</code></p></td>
      <td><p><code>application/x-gzip</code></p></td>
    </tr>
    <tr>
      <td><p>RAR Compressed</p></td>
      <td><p><code>*.rar</code></p></td>
      <td></td>
    </tr>
    <tr>
      <td><p>LZMA Compressed</p></td>
      <td><p><code>*.xz</code></p></td>
      <td><p><code>application/x-xz</code></p></td>
    </tr>
    <tr>
      <td><p>ZIP Compressed</p></td>
      <td><p><code>*.zip</code></p></td>
      <td><code>application/zip</code><br /><code>application-x-zip-compressed</code><br /></td>
    </tr>
    <tr>
      <td><p>Smaller than 4 KiB</p></td>
      <td></td>
      <td></td>
    </tr>
  </tbody>
</table>

### Data Compression and Encryption {#data-compression-and-encryption}

MinIO supports encrypting compressed objects but recommends against combining compression and encryption without a prior risk assessment. Before enabling encryption for compressed objects, carefully consider the security needs of your environment.

See [Transparent Data Compression on MinIO](https://blog.min.io/transparent-data-compression/) for more about combining compression and encryption. [MinIO SUBNET](https://min.io/pricing?jmp=docs) users can [log in](https://subnet.min.io/?ref=docs) and engage with our engineering and security teams to review encryption options.

## Tutorials {#tutorials}

### Enable Data Compression {#enable-data-compression}

To enable data compression, use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set the [`compression`](/reference/minio-server/settings/core/#mc-conf.compression) key [`enable`](/reference/minio-server/settings/core/#mc-conf.compression.enable) option to `on`.

The following enables compression for new objects of the [default types](#minio-data-compression-default-types):

```shell
mc admin config set ALIAS compression enable=on
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.

Existing uncompressed objects are not modified. To configure which extensions and types to compress, see [Configure Which Objects to Compress](#minio-data-compression-configure-objects).

To view the current compression settings:

```shell
mc admin config get ALIAS compression
```

### Disable Data Compression {#disable-data-compression}

To disable data compression, use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set the [`compression`](/reference/minio-server/settings/core/#mc-conf.compression) key [`enable`](/reference/minio-server/settings/core/#mc-conf.compression.enable) option to `off`:

The following disables data compression for new objects:

```shell
mc admin config set ALIAS compression enable=off
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.

Existing compressed objects are not modified.

<a id="minio-data-compression-configure-objects"></a>

### Configure Which Objects to Compress {#configure-which-objects-to-compress}

Configure the objects to compress by specifying the desired file extensions and media types in [`extensions`](/reference/minio-server/settings/core/#mc-conf.compression.extensions) or [`mime_types`](/reference/minio-server/settings/core/#mc-conf.compression.mime_types) arguments.

The default data compression configuration compresses the following types of data:

<table>
  <thead>
    <tr>
      <th><p>File Extensions</p></th>
      <th><p>Media (MIME) Types</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><code>.txt</code></p><p><code>.log</code></p><p><code>.csv</code></p><p><code>.json</code></p><p><code>.tar</code></p><p><code>.xml</code></p><p><code>.bin</code></p></td>
      <td><p><code>text/*</code></p><p><code>application/json</code></p><p><code>application/xml</code></p><p><code>binary/octet-stream</code></p></td>
    </tr>
  </tbody>
</table>

{{% alert color="info" %}}
**Default excluded extensions and types are never compressed**

Some objects cannot be efficiently compressed. MinIO will not attempt to compress these objects, even if they are specified in [`extensions`](/reference/minio-server/settings/core/#mc-conf.compression.extensions) or [`mime_types`](/reference/minio-server/settings/core/#mc-conf.compression.mime_types) arguments. See [Excluded File Types](#minio-data-compression-excluded-types) for a list of excluded types.
{{% /alert %}}

The sections below describe how to configure compression for the desired file extensions and media types.

#### Compress All Compressible Objects {#compress-all-compressible-objects}

To compress all objects except the [default excluded types](#minio-data-compression-excluded-types), use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set the [`compression`](/reference/minio-server/settings/core/#mc-conf.compression) key [`extensions`](/reference/minio-server/settings/core/#mc-conf.compression.extensions) and [`mime_types`](/reference/minio-server/settings/core/#mc-conf.compression.mime_types) options to empty lists:

```shell
mc admin config set ALIAS compression extensions= mime_types=
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.

#### Compress Objects by File Extension {#compress-objects-by-file-extension}

To compress objects with certain file extensions, use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set the desired file extensions in an [`extensions`](/reference/minio-server/settings/core/#mc-conf.compression.extensions) argument.

The following command compresses files with the extensions `.bin` and `.txt`:

```shell
mc admin config set ALIAS compression extensions=".bin, .txt"
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.

The new list of file extensions replaces the previous list. To add or remove an extension, repeat the [`extensions`](/reference/minio-server/settings/core/#mc-conf.compression.extensions) command with the complete list of extensions to compress.

The following adds `.pdf` to the list of file extensions from the previous example:

```shell
mc admin config set ALIAS compression extensions=".bin, .txt, .pdf"
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.

#### Compress Objects by Media Type {#compress-objects-by-media-type}

To compress objects of certain media types, use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set the [`compression`](/reference/minio-server/settings/core/#mc-conf.compression) key [`mime_types`](/reference/minio-server/settings/core/#mc-conf.compression.mime_types) option to a list of the desired types.

The following example compresses files of types `application/json` and `image/bmp`:

```shell
mc admin config set ALIAS compression mime_types="application/json, image/bmp"
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.

The new list of media types replaces the previous list. To add or remove a type, repeat the [`mime_types`](/reference/minio-server/settings/core/#mc-conf.compression.mime_types) command with the complete list of types to compress.

You can use `*` to specify all subtypes of a single media type. The following command adds all `text` subtypes to the list from the previous example:

```shell
mc admin config set ALIAS compression mime_types="application/json, image/bmp, text/*"
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.

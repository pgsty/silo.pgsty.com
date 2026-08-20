---
title: "mc sql"
url: "/reference/minio-mc/mc-sql/"
weight: 360
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-sql.rst
upstream_modified: false
---

<a id="mc-sql"></a>

<a id="command-mc.sql"></a>

## Syntax {#syntax}

The [`mc sql`](#command-mc.sql) command provides an S3 Select interface for performing sql queries on objects in the specified MinIO deployment.

See [Selecting content from objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/selecting-content-from-objects) for more information on S3 Select behavior and limitations.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command queries all objects in the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc sql --recursive --query "select * from S3Object" myminio/mydata
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] mc sql                          \
                 --query "string"                \
                 [--csv-input "string"]          \
                 [--compression "string"]        \
                 [--csv-output "string"]         \
                 [--csv-output-header "string"]  \
                 [--enc-c "string"]              \
                 [--json-input "string"]         \
                 [--json-output "string"]        \
                 [--recursive]                   \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.sql.ALIAS}

*mc-cmd*

*Required*

The full path to the bucket or object to run the SQL query against. Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of a configured S3 service as the prefix to the `ALIAS` path. For example:

```shell
mc sql [FLAGS] play/mybucket
```

##### `--query, e` {#mc.sql.-query}

*mc-cmd*

*Required*

The SQL statement to execute on the specified [`ALIAS`](#mc.sql.ALIAS) directory or object. Wrap the entire SQL query in double quotes `"`.

Defaults to `"select * from S3Object"`.

##### `--csv-input` {#mc.sql.-csv-input}

*mc-cmd*

*Optional*

The data format for `.csv` input objects. Specify a string of comma-seperated `key=value,...` pairs. See [CSV Formatting Fields](#mc-sql-csv-format) for more information on valid keys.

##### `--compression` {#mc.sql.-compression}

*mc-cmd*

*Optional*

The compression type of the input object. Specify one of the following supported values:

- `GZIP`
- `BZIP2`
- `NONE` (default)

Compression schemes supported by MinIO backend only:

- `ZSTD` [Zstandard](https://facebook.github.io/zstd/)
- `LZ4` [LZ4](https://lz4.github.io/lz4/) stream
- `S2` [S2](https://github.com/klauspost/compress/tree/master/s2#s2-compression) framed stream
- `SNAPPY` [Snappy](http://google.github.io/snappy/) framed stream

##### `--csv-output` {#mc.sql.-csv-output}

*mc-cmd*

*Optional*

The data format for `.csv` output. Specify a string of comma-seperated `key=value,...` pairs. See [CSV Formatting Fields](#mc-sql-csv-format) for more information on valid keys.

See the S3 API [CSVOutput](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CSVOutput.html) for more information.

##### `--csv-output-header` {#mc.sql.-csv-output-header}

*mc-cmd*

*Optional*

The header row of the `.csv` output file. Specify a string of comma-separated fields as `field1,field2,...`.

Omit to output a `.csv` with no header row.

##### `--enc-c` {#mc.sql.-enc-c}

*mc-cmd*

*Optional*

Encrypt or decrypt objects using server-side [SSE-C encryption](/administration/server-side-encryption/#minio-sse) with client-managed keys.

The parameter accepts a key-value pair formatted as `KEY=VALUE`

<table>
  <tbody>
    <tr>
      <td><p><code>KEY</code></p></td>
      <td><p>The full path to the object as <code>alias/bucket/path/object.ext</code>.</p><p>You can specify only the top-level path to use a single encryption key for all operations in that path.</p></td>
    </tr>
    <tr>
      <td><p><code>VALUE</code></p></td>
      <td><p>Specify either a 32-byte RawBase64-encoded key <em>or</em> a 64-byte hex-encoded key for use with SSE-C encryption.</p><p>Raw Base64 encoding <strong>rejects</strong> <code>=</code>-padded keys.
Omit the padding or use a Base64 encoder that supports RAW formatting.</p></td>
    </tr>
  </tbody>
</table>

- `KEY` - the full path to the object as `alias/bucket/path/object`.
- `VALUE` - the 32-byte RAW Base64-encoded data key to use for encrypting object(s).

For example:

```shell
# RawBase64-Encoded string "mybucket32byteencryptionkeyssec"
--enc-c "myminio/mybucket/prefix/object.obj=bXlidWNrZXQzMmJ5dGVlbmNyeXB0aW9ua2V5c3NlYwo"
```

You can specify multiple encryption keys by repeating the parameter.

Specify the path to a prefix to apply encryption to all matching objects at that path:

```shell
--enc-c "myminio/mybucket/prefix/=bXlidWNrZXQzMmJ5dGVlbmNyeXB0aW9ua2V5c3NlYwo"
```

> [!NOTE]
> **Note**
>
> MinIO strongly recommends against using SSE-C encryption in production workloads. Use SSE-KMS via the `--enc-kms` or SSE-S3 via `--enc-s3` parameters instead.

##### `--json-input` {#mc.sql.-json-input}

*mc-cmd*

*Optional*

The data format for `.json` or `.ndjson` input objects. Specify the type of the JSON contents as `type=<VALUE>`. The value can be either:

- `DOCUMENT` - JSON [document](https://www.json.org/json-en.html).
- `LINES` - JSON [lines](http://jsonlines.org/).

See the S3 API [JSONInput](https://docs.aws.amazon.com/AmazonS3/latest/API/API_JSONInput.html) for more information.

##### `--json-output` {#mc.sql.-json-output}

*mc-cmd*

*Optional*

The data format for the `.json` output. Supports the `rd=value` key, where `rd` is the `RecordDelimiter` for the JSON document.

Omit to use the default newline character `\n`.

See the S3 API [JSONOutput](https://docs.aws.amazon.com/AmazonS3/latest/API/API_JSONOutput.html) for more information.

##### `--recursive, r` {#mc.sql.-recursive}

*mc-cmd*

*Optional*

Recursively searches the specified [`ALIAS`](#mc.sql.ALIAS) directory using the [`--query`](#mc.sql.-query) SQL statement.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Select all Columns in all Objects in a Bucket {#select-all-columns-in-all-objects-in-a-bucket}

Use [`mc sql`](#command-mc.sql) with the [`--recursive`](#mc.sql.-recursive) and [`--query`](#mc.sql.-query) options to apply the query to all objects in a bucket:

```shell
mc sql --recursive --query "select * from S3Object" ALIAS/PATH
```

- Replace [`ALIAS`](#mc.sql.ALIAS) with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.
- Replace [`PATH`](#mc.sql.ALIAS) with the path to the bucket on the MinIO deployment.

### Run an Aggregation Query on an Object {#run-an-aggregation-query-on-an-object}

Use [`mc sql`](#command-mc.sql) with the [`--query`](#mc.sql.-query) option to query an object on an MinIO deployment:

```shell
mc sql --query "select count(s.power) from S3Object" ALIAS/PATH
```

- Replace [`ALIAS`](#mc.sql.ALIAS) with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.
- Replace [`PATH`](#mc.sql.ALIAS) with the path to the object on the MinIO deployment.

## Behavior {#behavior}

### Input Formats {#input-formats}

[`mc sql`](#command-mc.sql) supports the following input formats:

| Type | `content-type` Value |
| --- | --- |
| `.csv` | `text/csv` |
| `.json` | `application/json` |
| `.parquet` | none |

For `.csv` file types, use [`mc sql --csv-input`](#mc.sql.-csv-input) to specify the CSV data format. See [CSV Formatting Fields](#mc-sql-csv-format) for more information on CSV formatting fields.

For `.json` file types, use [`mc sql --json-input`](#mc.sql.-json-input) to specify the JSON data format.

For `.parquet` file types, [`mc sql`](#command-mc.sql) automatically interprets the data format.

[`mc sql`](#command-mc.sql) determines the type by the file extension of the target object. For example, an object named `data.json` is interpreted as a JSON file.

You can query data of a supported type but a different extension if the object has the appropriate `content-type`. For more information, see [`mc cp --attr`](/reference/minio-mc/mc-cp/#mc.cp.-attr).

<a id="mc-sql-csv-format"></a>

### CSV Formatting Fields {#csv-formatting-fields}

The following table lists valid key-value pairs for use with [`mc sql --csv-input`](#mc.sql.-csv-input) and [`mc sql --csv-output`](#mc.sql.-csv-output). Certain key pairs are only valid for [`--csv-input`](#mc.sql.-csv-input). See the documentation for S3 API [CSVInput](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CSVInput.html) for more information on S3 CSV formatting.

<table>
  <thead>
    <tr>
      <th><p>Key</p></th>
      <th><p><code>--csv-input</code> Only</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><code>rd</code></p></td>
      <td></td>
      <td><p>The character that seperates each record (row) in the input <code>.csv</code> file.</p><p>Corresponds to <code>RecordDelimiter</code> in the S3 API <code>CSVInput</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>fd</code></p></td>
      <td></td>
      <td><p>The character that seperates each field in a record. Defaults to <code>,</code>.</p><p>Corresponds to <code>FieldDelimeter</code> in the S3 API <code>CSVInput</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>qc</code></p></td>
      <td></td>
      <td><p>The character used for escaping when the <code>fd</code> character is part of a value. Defaults to <code>&quot;</code>.</p><p>Corresponds to <code>QuoteCharacter</code> in the S3 API <code>CSVInput</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>qec</code></p></td>
      <td></td>
      <td><p>The character used for escaping a quotation mark <code>&quot;</code> character inside an already escaped value.</p><p>Corresponds to <code>QuoteEscapeCharacter</code> in the S3 API <code>CSVInput</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>fh</code></p></td>
      <td><p>Yes</p></td>
      <td><p>The content of the first line in the <code>.csv</code> file.</p><p>Specify one of the following supported values:</p><ul><li><p><code>NONE</code> - The first line is not a header.</p></li><li><p><code>IGNORE</code> - Ignore the first line.</p></li><li><p><code>USE</code> - The first line is a header.</p></li></ul><p>For <code>NONE</code> or <code>IGNORE</code>, you must specify column positions <code>_#</code> to identify a column in the <a href="#mc.sql.-query"><code>--query</code></a> statement.</p><p>For <code>USE</code>, you can specify header values to identify a column in the <a href="#mc.sql.-query"><code>--query</code></a> statement.</p><p>Corresponds to <code>FieldHeaderInfo</code> in the S3 API <code>CSVInput</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>cc</code></p></td>
      <td><p>Yes</p></td>
      <td><p>The character used to indicate a record should be ignored.
The character <em>must</em> appear at the beginning of the record.</p><p>Corresponds to <code>Comment</code> in the S3 API <code>CSVInput</code>.</p></td>
    </tr>
    <tr>
      <td><p><code>qrd</code></p></td>
      <td><p>Yes</p></td>
      <td><p>Specify <code>TRUE</code> to indicate that fields may contain record delimiter values (<code>rd</code>).</p><p>Defaults to <code>FALSE</code>.</p><p>Corresponds to <code>AllowQuotedRecordDelimiter</code> in the S3 API <code>CSVInput</code>.</p></td>
    </tr>
  </tbody>
</table>

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

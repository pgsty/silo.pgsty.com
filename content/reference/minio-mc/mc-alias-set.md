---
title: "mc alias set"
url: "/reference/minio-mc/mc-alias-set/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-alias-set.rst
upstream_modified: false
---

<a id="mc-alias-set"></a>
<a id="alias"></a>
<a id="minio-mc-alias"></a>
<a id="minio-mc-alias-set"></a>

<a id="command-mc.alias.set"></a>

## Syntax {#syntax}

The [`mc alias set`](#command-mc.alias.set) command adds or updates an alias to the local **`mc`** configuration.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command adds an [alias](#alias) for a MinIO deployment `myminio` running at the URL `https://myminio.example.net`. **`mc`** uses the specified username and password for authenticating to the MinIO deployment:

```shell
mc alias set myminio https://myminio.example.net minioadminuser minioadminpassword
```

If the `myminio` alias already exists, the command overwrites that alias with the new URL, access key, and secret key.
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The [`mc alias set`](#command-mc.alias.set) command has the following syntax:

```shell
mc [GLOBALFLAGS] alias set \
                 [--api "string"]                           \
                 [--path "string"]                          \
                 ALIAS                                      \
                 URL                                        \
                 ACCESSKEY                                  \
                 SECRETKEY
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.alias.set.ALIAS}

*mc-cmd*

*Required* The name to associate with the S3-compatible service. Aliases are case-sensitive and must meet the following requirements:

- Contain only [ASCII](https://en.wikipedia.org/wiki/ASCII) lower case letters (`a-z`), upper case letters (`A-Z`), numbers (`[0-9]`), hyphen (`-`), or underscore (`_`).
- 2 or more characters in length.
- The first character must be a letter.

> [!NOTE]
> **Changed: RELEASE.2024-01-11T05-49-32Z**
>
> An alias may also be a single letter (`a-z` or `A-Z`).

Examples of some valid alias values include:

- `myminio`
- `Test-1`
- `A`
- `a`

##### `URL` {#mc.alias.set.URL}

*mc-cmd*

*Required* The URL to the S3-compatible service endpoint. For example:

`https://minio.example.net`

##### `ACCESSKEY` {#mc.alias.set.ACCESSKEY}

*mc-cmd*

*Required*

The access key for authenticating to the S3 service.

##### `SECRETKEY` {#mc.alias.set.SECRETKEY}

*mc-cmd*

*Required*

The secret key for authenticating to the S3 service.

##### `--api` {#mc.alias.set.-api}

*mc-cmd*

*Optional*

Specifies the signature calculation method to use when connecting to the S3-compatible service. Supports the following values:

- `S3v4` (Default)
- `S3v2`

> [!NOTE]
> **Note**
>
> AWS Signature V2 is considered [deprecated](https://aws.amazon.com/blogs/aws/amazon-s3-update-sigv2-deprecation-period-extended-modified/) by AWS. [`mc alias set`](#command-mc.alias.set) includes this option only for S3 buckets or services still reliant on the Signature V2.
>
> Use `S3v4` unless explicitly required by the S3-compatible service. MinIO server does not rely on nor require `S3v2`, nor are all API operations available on `S3v2`.

##### `--path` {#mc.alias.set.-path}

*mc-cmd*

*Optional*

Specifies the bucket path lookup setting used by the server. Supports the following values:

- `"auto"` (Default)
- `"on"`
- `"off"`

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Add or Update an Alias for a MinIO Deployment {#add-or-update-an-alias-for-a-minio-deployment}

Use [`mc alias set`](#command-mc.alias.set) to add an S3-compatible service for use with **`mc`**:

{{< tabs group="example-syntax" >}}
{{< tab label="Example" value="example" >}}
The following command creates a new alias `myminio` pointing at a MinIO deployment at `https://minio.example.net`. The alias uses the `miniouser` and `miniopassword` credentials for performing operations against the deployment.

```shell
mc alias set myminio https://minio.example.net miniouser miniopassword
```

If the `myminio` alias already exists, the [`mc alias set`](#command-mc.alias.set) command overwrites that alias with the specified arguments.
{{< /tab >}}
{{< tab label="Syntax" value="syntax" >}}
```shell
mc alias set ALIAS HOSTNAME ACCESSKEY SECRETKEY
```

- Replace `ALIAS` with the name to associate with the MinIO service.
- Replace `HOSTNAME` with the URL for any node in the MinIO deployment. You can alternatively specify the URL for a load balancer or reverse proxy managing connections to the MinIO deployment.
- Replace `ACCESSKEY` and `SECRETKEY` with credentials for a user on the MinIO deployment.
{{< /tab >}}
{{< /tabs >}}

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

### Required Credentials and Access Control {#required-credentials-and-access-control}

[`mc alias set`](#command-mc.alias.set) requires specifying an access key and corresponding secret key for the S3-compatible host. **`mc`** functionality is limited based on the policies associated to the specified credentials. For example, if the specified credentials do not have read/write access to a specific bucket, **`mc`** cannot perform read or write operations on that bucket.

For more information on MinIO Access Control, see [Access Management](/administration/identity-access-management/#minio-access-management).

For more complete documentation on S3 Access Control, see [Amazon S3 Security](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security.html).

For all other S3-compatible services, defer to the documentation for that service.

### Certificates {#certificates}

The MinIO Client fetches the peer certificate, computes the public key fingerprint, and asks the user whether to accept the deployment’s certificate.

If trusted, the MinIO Client automatically adds the certificate authority to:

- `~/.mc/certs/CAs/` on Linux and other Unix-like systems.
- `C:\Users\[username]\mc\certs\CAs\` on Windows systems.

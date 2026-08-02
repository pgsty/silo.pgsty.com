---
title: "mc legalhold set"
url: "/reference/minio-mc/mc-legalhold-set/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="mc-legalhold-set"></a>
<a id="minio-mc-legalhold-set"></a>

<a id="command-mc.legalhold.set"></a>

## Syntax {#syntax}

The [`mc legalhold set`](#command-mc.legalhold.set) command enables [legal hold](/administration/object-management/object-retention/#minio-object-locking-legalhold) Write-Once Read-Many (WORM) object locking on an object or objects.

[`mc legalhold`](/reference/minio-mc/mc-legalhold/#command-mc.legalhold) *requires* that the specified bucket has [object locking enabled](/administration/object-management/object-retention/#minio-object-locking). You can **only** enable object locking at bucket creation. See [`mc mb --with-lock`](/reference/minio-mc/mc-mb/#mc.mb.-with-lock) for documentation on creating buckets with object locking enabled.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command enables legalhold WORM locking on all existing objects in the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc legalhold set --recursive myminio/mydata
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] legalhold set  \
                 [--recursive]  \
                 [--rewind]     \
                 [--version-id] \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.legalhold.set.ALIAS}

*mc-cmd*

*Required*

The MinIO [alias](/reference/minio-mc/mc-alias-set/#alias) and path to the object or objects on which to enable the legal hold. For example:

```shell
mc legalhold set play/mybucket/myobjects/objects.txt
```

##### `--recursive, r` {#mc.legalhold.set.-recursive}

*mc-cmd*

*Optional*

Applies the legal hold to all existing objects in the [`ALIAS`](#mc.legalhold.set.ALIAS) bucket or bucket prefix.

{{% alert color="info" %}}
**`--recursive` only applies to existing objects**

To enable legal hold for future objects, periodically repeat the [`mc legalhold`](/reference/minio-mc/mc-legalhold/#command-mc.legalhold) command as new objects are created.
{{% /alert %}}

##### `--rewind` {#mc.legalhold.set.-rewind}

*mc-cmd*

*Optional*

Directs [`mc legalhold set`](#command-mc.legalhold.set) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.legalhold.set.-rewind) requires that the specified [`ALIAS`](#mc.legalhold.set.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--version-id, vid` {#mc.legalhold.set.-version-id}

*mc-cmd*

*Optional*

Directs [`mc legalhold set`](#command-mc.legalhold.set) to operate only on the specified object version.

[`--version-id`](#mc.legalhold.set.-version-id) requires that the specified [`ALIAS`](#mc.legalhold.set.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

Use [`mc legalhold set`](#command-mc.legalhold.set) to enable legal hold on objects:

```shell
mc legalhold set [--recursive] ALIAS/PATH
```

- Replace [`ALIAS`](#mc.legalhold.set.ALIAS) with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the S3-compatible host.
- Replace [`PATH`](#mc.legalhold.set.ALIAS) with the path to the bucket or object on the S3-compatible host. If specifying the path to a bucket or bucket prefix, include the [`--recursive`](#mc.legalhold.set.-recursive) option.

## Behavior {#behavior}

### Legal Holds Require Explicit Removal {#legal-holds-require-explicit-removal}

Legal holds are indefinite and enforce complete immutability for locked objects. Only privileged users with the [`s3:PutObjectLegalHold`](/administration/identity-access-management/policy-based-access-control/#policy-action.s3-PutObjectLegalHold) can set or lift the legal hold.

### Legal Holds Complement Other Retention Modes {#legal-holds-complement-other-retention-modes}

Legal holds are complementary to both [GOVERNANCE Mode](/administration/object-management/object-retention/#minio-object-locking-governance) and [COMPLIANCE Mode](/administration/object-management/object-retention/#minio-object-locking-compliance) retention settings. An object held under both legal hold *and* a `GOVERNANCE/COMPLIANCE` retention rule remains WORM locked until the legal hold is lifed *and* the rule expires.

For `GOVERNANCE` locked objects, the legal hold prevents mutating the object *even if* the user has the necessary privileges to bypass retention.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

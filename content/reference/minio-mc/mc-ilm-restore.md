---
title: "mc ilm restore"
url: "/reference/minio-mc/mc-ilm-restore/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-ilm-restore.rst
upstream_modified: true
---

<a id="mc-ilm-restore"></a>
<a id="minio-mc-ilm-restore"></a>

<a id="command-mc.ilm.restore"></a>

## Syntax {#syntax}

The [`mc ilm restore`](#command-mc.ilm.restore) command creates a temporary local copy of an object archived on a remote tier. The temporary copy expires after 1 day by default.

Use this command to let applications read a transitioned object from local storage on the SILO deployment. The transitioned data remains on the remote tier while the temporary local copy serves read requests for the restored version until the restore period expires.

> [!NOTE]
> **Added: mc**
>
> RELEASE.2023-04-12T02-21-51Z
>
> Use [`mc stat`](/reference/minio-mc/mc-stat/#command-mc.stat) to display whether a restored object reads from the local temporary copy or the remote tier. Objects currently in the process of restoration from the remote tier show a status of `Ongoing : true`.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command restores a copy of a transitioned object from the remote tier back to the `myminio` MinIO deployment:

```shell
mc ilm restore myminio/mybucket/object.txt
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ilm restore         \
                 [--days "int" ]     \
                 [--recursive]       \
                 [--vid "string"]    \
                 [--versions]        \
                 [--enc-c "string"]  \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.ilm.restore.ALIAS}

*mc-cmd*

*Required*

The MinIO [alias](/reference/minio-mc/mc-alias-set/#alias), bucket, and path to the archived object to restore.

```shell
mc ilm restore myminio/mybucket/object.txt
```

##### `--days` {#mc.ilm.restore.-days}

*mc-cmd*

*Optional*

The number of days after which MinIO expires the restored copy of the archived object.

##### `--enc-c` {#mc.ilm.restore.-enc-c}

*mc-cmd*

*Optional*

Encrypt or decrypt objects using server-side [SSE-C encryption](/administration/server-side-encryption/#minio-sse) with client-managed keys.

The parameter accepts a key-value pair formatted as `KEY=VALUE`:

| Component | Description                                                                                                                                                                            |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `KEY`     | The full path to the object as `alias/bucket/path/object.ext`. Specify only the top-level path to use one encryption key for all operations under that path.                           |
| `VALUE`   | Either a 32-byte RawBase64-encoded key *or* a 64-byte hex-encoded key for SSE-C encryption. Raw Base64 encoding **rejects** `=`-padded keys; omit padding or use a RAW Base64 encoder. |
{.wide .expand}

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

##### `--recursive, r` {#mc.ilm.restore.-recursive}

*mc-cmd*

*Optional*

Restores all objects under the specified prefix.

##### `--versions` {#mc.ilm.restore.-versions}

*mc-cmd*

*Optional*

Restores all versions of the object on the remote tier.

##### `--version-id, vid` {#mc.ilm.restore.-version-id}

*mc-cmd*

*Optional*

Restores the specified version of the object on the remote tier.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Restore an Archived Object {#restore-an-archived-object}

The following command restores an object archived to a remote tier:

```shell
mc ilm restore myminio/mybucket/object.txt
```

### Restore a Specific Archived Object Version {#restore-a-specific-archived-object-version}

The following command restores a specific object version archived to a remote tier:

```shell
mc ilm restore --vid "VERSIONID" myminio/mybucket/object.txt
```

### Restore All Archived Objects at a Bucket Prefix {#restore-all-archived-objects-at-a-bucket-prefix}

The following command restores all objects archived under a specified prefix on the remote tier:

```shell
mc ilm restore --recursive myminio/mybucket/data/
```

## Behavior {#behavior}

### Restored Objects Expire Automatically {#restored-objects-expire-automatically}

SILO automatically expires the restored local copy after the specified number of days (default: 1 day). In [SILO 20261109](/blog/release/silo-20261109/), expiring a restored copy removes only the temporary local cache while keeping the object version and its remote-tier data intact ([#281](https://github.com/pgsty/silo/issues/281)).

<a id="restored-objects-become-head"></a>

### Two-Phase In-Place Version Restore {#two-phase-restore}

Starting in [SILO 20261109](/blog/release/silo-20261109/), native restore (`POST ?restore`, commit [`86dc6ee2e`](https://github.com/pgsty/silo/commit/86dc6ee2e)) runs in two phases; see [Native Restore in Two Phases](/blog/design/native-restore-two-phase/) for design details:

- **In-place version restoration:** SILO restores the exact addressed version in place without changing version ordering or creating a new `HEAD` version. Multi-pool restores no longer hang or remain stuck in progress ([#289](https://github.com/pgsty/silo/issues/289)).
- **Two-phase locking:** Phase 1 downloads and stages the remote-tier data outside the object write lock so concurrent `GET`, `HEAD`, and `PUT` requests on the key do not wait for the download. Phase 2 acquires a short object lock and validates attempt ownership and version metadata before publishing the restored copy ([#284](https://github.com/pgsty/silo/issues/284)).
- **Fast failure cleanup:** If a restore fails or is canceled, the server returns immediately and attempts marker cleanup for `100 ms` before switching to bounded background retries, instead of waiting up to one minute for the object lock.
- **Rolling-upgrade gate:** During a mixed-version rolling upgrade, upgraded nodes return `503 Service Unavailable` to `POST ?restore` while any peer runs an older version or is unreachable. Pause new restores until all nodes run `SILO 20261109`.

### S3 Compatibility {#s3-compatibility}

SILO is the supported server for PGSTY mcli; compatibility with upstream MinIO and other S3 services is [best effort](/reference/minio-mc/#command-mc).

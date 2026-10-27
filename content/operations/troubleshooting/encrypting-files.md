---
title: "Encrypting Files"
url: "/operations/troubleshooting/encrypting-files/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/troubleshooting/encrypting-files.rst
upstream_modified: true
---

<a id="encrypting-files"></a>
<a id="minio-support-encryption"></a>

## Description {#description}

[`mcli support inspect`](/reference/minio-mc/mc-support-inspect/) downloads raw object data and metadata from the server's underlying drives. PGSTY mcli saves diagnostic archives locally without requiring SUBNET registration or uploading anything automatically. Treat both the archive and its decryption key as sensitive material.

## Encryption {#encryption}

Current SILO and mcli releases always encrypt `support inspect` output (there is no `--encrypt` flag on the command):

```shell
mcli support inspect 'mysilo/mybucket/myobject/xl.meta'
```

If no user-supplied `support_public.pem` is present in the client configuration directory, SILO generates a random one-time key and mcli prints the decryption key alongside the downloaded filename. Save that key immediately—it cannot be recovered later, and PGSTY does not embed any vendor decryption key.

If you provide `support_public.pem`, keep the matching private key safe. Quote paths containing wildcards so the shell passes the pattern directly to mcli. Because recursive inspection can pull object shards from multiple drives, collect only the specific files needed for troubleshooting.

<a id="minio-support-decryption"></a>

## Decryption {#decryption}

<a id="go"></a>

Build the `inspect` decryption utility from the maintained SILO source repository using the Go toolchain version required by that release:

```shell
git clone --branch RELEASE.2026-10-26T00-00-00Z --depth 1 https://github.com/pgsty/silo.git
cd silo/docs/debugging/inspect
go build -o inspect .
```

To decrypt an archive using the symmetric key printed during download:

```shell
./inspect -key=DECRYPTION_KEY /path/to/inspect.enc
```

If you omit `-key` and no private key file is specified, the utility prompts interactively for the decryption key.

To decrypt output encrypted with `support_public.pem`, pass the matching private key:

```shell
./inspect -private-key=/secure/path/support_private.pem /path/to/inspect.enc
```

With `-key`, the utility writes a decrypted ZIP archive next to the input file; with `-private-key`, it extracts the decrypted streams (including `inspect.zip`) into an output directory. Review the extracted files before sharing them, and note that unwrapping the `inspect.enc` diagnostic archive does not decrypt objects that are themselves stored with server-side encryption (SSE).

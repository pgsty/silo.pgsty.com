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

[`mcli support inspect`](/reference/minio-mc/mc-support-inspect/) downloads object data and metadata from the server's drives. PGSTY mcli saves diagnostics locally without SUBNET registration or automatic uploads. Treat the archive and its decryption material as sensitive.

## Encryption {#encryption}

Current SILO/mcli encrypts inspect output. There is no `--encrypt` flag on the current `support inspect` command. For example:

```shell
mcli support inspect 'mysilo/mybucket/myobject/xl.meta'
```

Without a user-supplied `support_public.pem` in the client configuration directory, SILO generates a random key and mcli prints the decryption key with the downloaded filename. Save that key securely: it cannot be recovered later. PGSTY does not add a vendor decryption key.

If you supply `support_public.pem`, retain its matching private key. Quote wildcard paths so the shell passes the pattern to mcli. Limit collection to the files needed for diagnosis; recursive inspection can download object contents from many drives.

<a id="minio-support-decryption"></a>

## Decryption {#decryption}

<a id="go"></a>

Build the inspect utility from the maintained SILO source checkout using the Go version required by that checkout:

```shell
git clone --branch RELEASE.2026-10-18T00-00-00Z --depth 1 https://github.com/pgsty/silo.git
cd silo/docs/debugging/inspect
go build -o inspect .
```

For an archive downloaded with a printed symmetric key:

```shell
./inspect -key=DECRYPTION_KEY /path/to/inspect.enc
```

If you omit `-key` and no private key file is found, the utility prompts for the decryption key.

For output encrypted to your `support_public.pem`, use its corresponding private key:

```shell
./inspect -private-key=/secure/path/support_private.pem /path/to/inspect.enc
```

With `-key`, the utility writes a decrypted ZIP beside the input file. With `-private-key`, it extracts the decrypted streams, including `inspect.zip`, into an output directory. Protect that output and share it only with an intended recipient after reviewing its contents. Decrypting the diagnostic wrapper does not remove any separate SSE encryption on collected object data.

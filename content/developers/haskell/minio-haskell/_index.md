---
title: "Haskell Quickstart Guide"
description: "Connect a Haskell application to SILO with the MinIO Haskell SDK."
url: "/developers/haskell/minio-haskell/"
weight: 60
icon: fa-solid fa-code
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/developers/haskell/minio-haskell.rst
upstream_modified: true
---

## MinIO Haskell SDK {#haskell-sdk}

SILO implements the S3-compatible server contract, so Haskell applications can use the upstream [`minio-hs`](https://github.com/minio/minio-hs) package directly.

> [!WARNING]
> The latest tagged upstream release is `1.7.0`, published in 2023, and its package metadata lists GHC 8.10.7 as the tested compiler. Validate `minio-hs` against your current GHC, resolver, TLS stack, and workload before adopting it. Check [Hackage](https://hackage.haskell.org/package/minio-hs) and [upstream releases](https://github.com/minio/minio-hs/releases) for newer compatibility information.

## Install the package {#install}

Add `minio-hs` to the `build-depends` section of your Cabal package or to the dependency list in `package.yaml`. For an interactive inspection of the installed API:

```shell
cabal repl
```

Then run `:browse Network.Minio` in GHCi.

## Configure the connection {#configure}

Version 1.7.0 provides `fromMinioEnv`, which reads the following credential variables:

```shell
export S3_ENDPOINT=http://127.0.0.1:9000
export MINIO_ACCESS_KEY=silo-admin
export MINIO_SECRET_KEY=replace-with-a-strong-secret
```

`S3_ENDPOINT` is a complete URL, including the `http://` or `https://` scheme. Keep credentials outside source control.

## Create a bucket and upload an object {#upload}

Save the following as `Main.hs`:

```haskell
{-# LANGUAGE OverloadedStrings #-}

import Control.Monad (unless)
import Data.String (fromString)
import Network.Minio
import System.Environment (getEnv)

main :: IO ()
main = do
  endpoint <- getEnv "S3_ENDPOINT"
  connection <-
    setCredsFrom [fromMinioEnv] (fromString endpoint :: ConnectInfo)

  result <- runMinio connection $ do
    let bucket = "haskell-quickstart"
        object = "hello.txt"

    exists <- bucketExists bucket
    unless exists $ makeBucket bucket Nothing
    fPutObject bucket object "hello.txt" defaultPutObjectOptions

  case result of
    Left err -> putStrLn $ "Upload failed: " ++ show err
    Right () -> putStrLn "Uploaded hello.txt"
```

Create `hello.txt`, then run the program with the build tool and resolver selected for your project. The repository's [examples directory](https://github.com/minio/minio-hs/tree/master/examples) and [API reference](https://hackage.haskell.org/package/minio-hs/docs/Network-Minio.html) cover streaming, presigned URLs, encryption, notifications, object locking, and other operations.

## Production checklist {#production}

- Use TLS and verify the server certificate; do not disable certificate validation.
- Load credentials from a secret manager or protected environment.
- Grant the application only the bucket and object permissions it needs.
- Pin and test the GHC, resolver, SDK, TLS, and HTTP dependency versions together.
- Define timeouts and handle `MinioErr`, retries, resource cleanup, and incomplete multipart uploads explicitly.

See [Identity and Access Management](/administration/identity-access-management/) for server-side policy configuration.

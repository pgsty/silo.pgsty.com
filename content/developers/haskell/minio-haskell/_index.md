---
title: "Haskell Quickstart Guide"
url: "/developers/haskell/minio-haskell/"
weight: 60
icon: fa-solid fa-code
minio_origin: true
silo_modified: false
---

<a id="haskell-quickstart-guide"></a>
<a id="minio-haskell-quickstart"></a>

## 兼容 Amazon S3 对象存储的 MinIO Haskell Client SDK [![CI](https://github.com/minio/minio-hs/actions/workflows/ci.yml/badge.svg)](https://github.com/minio/minio-hs/actions/workflows/ci.yml)[![Hackage](https://img.shields.io/hackage/v/minio-hs.svg)](https://hackage.haskell.org/package/minio-hs)[![Slack](https://slack.min.io/slack?type=svg)](https://slack.min.io) {#amazon-s3-minio-haskell-client-sdk}

MinIO Haskell Client SDK 提供简洁的 API，用于访问 [MinIO](https://min.io) 以及任何兼容 Amazon S3 的对象存储。

本指南假定你已具备可用的 [Haskell 开发环境](https://www.haskell.org/downloads/)。

### 安装 {#id1}

#### 添加到项目中 {#id2}

将 `minio-hs` 添加到项目的 `.cabal` 依赖部分；如果你使用 hpack，则添加到 `package.yaml` 文件中。

#### 在 [REPL](https://en.wikipedia.org/wiki/Read%E2%80%93eval%E2%80%93print_loop) 中试用 {#repl}

##### 对于使用 cabal 的用户 {#cabal}

下载库源代码并切换到解压后的目录：

```sh
$ cabal get minio-hs
$ cd minio-hs-1.6.0/ # directory name could be different

```

然后在已加载该库的 `ghci` REPL 环境中查看可用的 API：

```sh
$ cabal repl
ghci> :browse Network.Minio

```

##### 对于使用 stack 的用户 {#stack}

在主目录或任意非 Haskell 项目目录中直接运行：

```sh
stack install minio-hs

```

然后启动解释器会话，并通过以下命令查看可用的 API：

```sh
$ stack ghci
> :browse Network.Minio

```

### 示例 {#id3}

[`examples`](https://github.com/minio/minio-hs/tree/master/examples) 目录包含许多示例，你可以通过试用这些示例进行学习，并用于开发自己的项目。

#### 快速入门示例 - 文件上传器 {#id4}

该示例程序会连接到 MinIO 对象存储服务器，在服务器上创建一个存储桶，然后将文件上传到该存储桶。

本示例使用部署在 <https://play.min.io> 的 MinIO 服务器。你可以使用该服务进行测试和开发。访问凭证已内置在库中，且为公开信息。

#### FileUploader.hs {#fileuploader-hs}

```haskell
#!/usr/bin/env stack
-- stack --resolver lts-14.11 runghc --package minio-hs --package optparse-applicative --package filepath

--
-- MinIO Haskell SDK, (C) 2017-2019 MinIO, Inc.
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.
--


{-# LANGUAGE OverloadedStrings   #-}
{-# LANGUAGE ScopedTypeVariables #-}
import           Network.Minio

import           Data.Monoid           ((<>))
import           Data.Text             (pack)
import           Options.Applicative
import           System.FilePath.Posix
import           UnliftIO              (throwIO, try)

import           Prelude

-- | The following example uses minio's play server at
-- https://play.min.io.  The endpoint and associated
-- credentials are provided via the libary constant,
--
-- > minioPlayCI :: ConnectInfo
--

-- optparse-applicative package based command-line parsing.
fileNameArgs :: Parser FilePath
fileNameArgs = strArgument
               (metavar "FILENAME"
                <> help "Name of file to upload to AWS S3 or a MinIO server")

cmdParser = info
            (helper <*> fileNameArgs)
            (fullDesc
             <> progDesc "FileUploader"
             <> header
             "FileUploader - a simple file-uploader program using minio-hs")

main :: IO ()
main = do
  let bucket = "my-bucket"

  -- Parse command line argument
  filepath <- execParser cmdParser
  let object = pack $ takeBaseName filepath

  res <- runMinio minioPlayCI $ do
    -- Make a bucket; catch bucket already exists exception if thrown.
    bErr <- try $ makeBucket bucket Nothing

    -- If the bucket already exists, we would get a specific
    -- `ServiceErr` exception thrown.
    case bErr of
      Left BucketAlreadyOwnedByYou -> return ()
      Left e                       -> throwIO e
      Right _                      -> return ()

    -- Upload filepath to bucket; object name is derived from filepath.
    fPutObject bucket object filepath defaultPutObjectOptions

  case res of
    Left e   -> putStrLn $ "file upload failed due to " ++ show e
    Right () -> putStrLn "file upload succeeded."

```

#### 运行 FileUploader {#fileuploader}

```sh
./FileUploader.hs "path/to/my/file"


```

### 贡献 {#id5}

[贡献指南](https://github.com/minio/minio-hs/blob/master/CONTRIBUTING.md)

#### 开发 {#id6}

##### 下载源码 {#id7}

```sh
$ git clone https://github.com/minio/minio-hs.git
$ cd minio-hs/

```

##### 构建软件包 {#id8}

使用 `cabal`：

```sh
$ # Configure cabal for development enabling all optional flags defined by the package.
$ cabal configure --enable-tests --test-show-details=direct -fexamples -fdev -flive-test
$ cabal build

```

使用 `stack`：

```sh
$ stack build --test --no-run-tests --flag minio-hs:live-test --flag minio-hs:dev --flag minio-hs:examples

```

##### 运行测试 {#id9}

默认情况下，部分测试会使用远程 MinIO Play 服务器 `https://play.min.io`。在库开发过程中，使用该远程服务器可能较慢。若要针对本地运行的 MinIO server `http://localhost:9000` 执行测试，并使用凭证 `access_key=minio` 与 `secret_key=minio123`，只需将环境变量 `MINIO_LOCAL` 设置为任意值（取消设置后将切回 Play）。

使用 `cabal`：

```sh
$ export MINIO_LOCAL=1 # to run live tests against local MinIO server
$ cabal test

```

使用 `stack`：

```sh
$ export MINIO_LOCAL=1 # to run live tests against local MinIO server
stack test --flag minio-hs:live-test --flag minio-hs:dev

```

这将运行所有测试套件。

##### 构建文档 {#id10}

```sh
$ cabal haddock
$ # OR
$ stack haddock

```

---
title: "Software Development Kits (SDK)"
url: "/developers/minio-drivers/"
weight: 190
icon: fa-solid fa-cubes
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/developers/minio-drivers.rst
upstream_modified: true
---

<a id="software-development-kits-sdk"></a>
<a id="minio-drivers"></a>

MinIO publishes the following Software Development Kits (SDK):

- [Go](#go-sdk)
- [Python](#python-sdk)
- [Java](#java-sdk)
- [.NET](#dotnet-sdk)
- [JavaScript](#javascript-sdk)
- [Haskell](#haskell-sdk)
- [C++](#cpp-sdk)
- [Rust](#rust-sdk)

<a id="go-sdk"></a>

## Go {#go}

GitHub: [minio/minio-go](https://github.com/minio/minio-go)

Latest Version: GOVERSION

Quickstart Guide: [Go Quickstart Guide](/developers/go/minio-go/)

Reference: [MinIO Go SDK API](https://pkg.go.dev/github.com/minio/minio-go/v7)

Download from GitHub

> ```shell
> go get github.com/minio/minio-go/v7
> ```

<a id="python-sdk"></a>

## Python {#python}

GitHub: [minio/minio-py](https://github.com/minio/minio-py)

Latest Version: PYTHONVERSION

Quickstart Guide: [Python Quickstart Guide](/developers/python/minio-py/)

Reference: [MinIO Python SDK](https://github.com/minio/minio-py)

**Install Methods**

> - pip
>
>   ```shell
>   pip3 install minio
>   ```
>
> - source
>
>   ```shell
>   git clone https://github.com/minio/minio-py
>   cd minio-py
>   python setup.py install
>   ```

<a id="java-sdk"></a>

## Java {#java}

GitHub: [minio/minio-java](https://github.com/minio/minio-java)

Latest version: JAVAVERSION

Quickstart Guide: [Java Quickstart Guide](/developers/java/minio-java/#minio-java-quickstart)

Reference: [MinIO Java SDK](https://github.com/minio/minio-java)

**Install methods**

> - Maven
>
>   ```java
>   <dependency>
>       <groupId>io.minio</groupId>
>       <artifactId>minio</artifactId>
>       <version>JAVAVERSION</version>
>   </dependency>
>   ```
>
> - Gradle
>
>   ```java
>   dependencies {
>       implementation("io.minio:minio:JAVAVERSION")
>   }
>   ```
>
> - JAR
>
>   Download the latest JAR file for version JAVAVERSION of the SDK from the Sonatype Maven Central Repository.

<a id="dotnet-sdk"></a>

## .NET {#net}

GitHub: [minio/minio-dotnet](https://github.com/minio/minio-dotnet)

Latest Version: DOTNETVERSION

Quickstart Guide: [.NET Quickstart Guide](/developers/dotnet/minio-dotnet/)

Reference: [MinIO .NET SDK](https://github.com/minio/minio-dotnet)

**Download from NuGet**

> Run the following command in the NuGet Package Manager Console.
>
> ```shell
> PM> Install-Package Minio
> ```

<a id="javascript-sdk"></a>

## JavaScript {#javascript}

GitHub: [minio/minio-js](https://github.com/minio/minio-js)

Latest Version: JAVASCRIPTVERSION

Quickstart Guide: [JavaScript Quickstart Guide](/developers/javascript/minio-javascript/)

Reference: [MinIO JavaScript SDK](https://github.com/minio/minio-js)

**Install**

> - NPM
>
>   ```shell
>   npm install --save minio
>   ```
>
> - Source
>
>   ```shell
>   git clone https://github.com/minio/minio-js
>   cd minio-js
>   npm install
>   npm install -g
>   ```

<a id="haskell-sdk"></a>

## Haskell {#haskell}

GitHub: [minio/minio-hs](https://github.com/minio/minio-hs)

Latest Version: HASKELLVERSION

Quickstart Guide: [Haskell Quickstart Guide](/developers/haskell/minio-haskell/)

**Install**

> Add `minio-hs` to your project’s `.cabal` dependencies section.
>
> or
>
> If you are using `hpack`, add `minio-hs` to your `package.yaml` file.

<a id="cpp-sdk"></a>

## C++ {#c}

GitHub: [minio/minio-cpp](https://github.com/minio/minio-cpp)

Reference: [MinIO C++ SDK Reference](https://minio-cpp.min.io/)

**Install**

> - `vcpkg`
>
>   ```shell
>   vcpkg install minio-cpp
>   ```
>
> - Source
>
>   ```shell
>   git clone https://github.com/minio/minio-cpp
>   cd minio-cpp
>   wget --quiet -O vcpkg-master.zip https://github.com/microsoft/vcpkg/archive/refs/heads/master.zip
>   unzip -qq vcpkg-master.zip
>   ./vcpkg-master/bootstrap-vcpkg.sh
>   ./vcpkg-master/vcpkg integrate install
>   cmake -B ./build -DCMAKE_BUILD_TYPE=Debug -DCMAKE_TOOLCHAIN_FILE=./vcpkg-master/scripts/buildsystems/vcpkg.cmake
>   cmake --build ./build --config Debug
>   ```

<a id="rust-sdk"></a>

## Rust {#rust}

GitHub: [minio/minio-rs](https://github.com/minio/minio-rs)

**Latest Version**

> RUSTVERSION

Reference: [MinIO Rust SDK Reference](https://docs.rs/minio/latest/minio/)

Quickstart Guide: [Rust Quickstart Guide](/developers/rust/minio-rust/)

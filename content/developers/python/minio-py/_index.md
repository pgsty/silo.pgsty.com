---
title: "Python Quickstart Guide"
description: "Connect a Python application to SILO with the MinIO Python SDK."
url: "/developers/python/minio-py/"
weight: 20
icon: fa-brands fa-python
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/developers/python/minio-py.rst
upstream_modified: true
---

## MinIO Python SDK {#python-sdk}

SILO implements the S3-compatible server contract, so Python applications can use the upstream [MinIO Python SDK](https://github.com/minio/minio-py) directly.

> [!NOTE]
> Supported Python versions and SDK APIs can change independently of SILO. Check the [current package metadata](https://pypi.org/project/minio/) and [SDK releases](https://github.com/minio/minio-py/releases) before pinning a version.

## Install the package {#install}

Install `minio` in a virtual environment:

```shell
python3 -m venv .venv
source .venv/bin/activate
python -m pip install minio
```

## Configure the connection {#configure}

```shell
export S3_ENDPOINT=127.0.0.1:9000
export S3_ACCESS_KEY=silo-admin
export S3_SECRET_KEY=replace-with-a-strong-secret
export S3_USE_SSL=false
```

`S3_ENDPOINT` is a host and optional port, without an `http://` or `https://` prefix. Keep credentials outside source control and set `S3_USE_SSL=true` when the endpoint serves TLS.

## Create a bucket and upload an object {#upload}

Save the following as `quickstart.py`:

```python
import io
import os

from minio import Minio


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


client = Minio(
    required("S3_ENDPOINT"),
    access_key=required("S3_ACCESS_KEY"),
    secret_key=required("S3_SECRET_KEY"),
    secure=os.environ.get("S3_USE_SSL", "false").lower() == "true",
)

bucket = "python-quickstart"
object_name = "hello.txt"
payload = b"hello from SILO\n"

if not client.bucket_exists(bucket):
    client.make_bucket(bucket)

client.put_object(
    bucket,
    object_name,
    io.BytesIO(payload),
    length=len(payload),
    content_type="text/plain",
)

stat = client.stat_object(bucket, object_name)
print(f"Uploaded {object_name}: {stat.size} bytes")
```

Run it with:

```shell
python quickstart.py
```

Use the repository's [API reference](https://github.com/minio/minio-py/blob/master/docs/API.md) and [maintained examples](https://github.com/minio/minio-py/tree/master/examples) for presigned URLs, server-side encryption, notifications, object locking, multipart operations, and other APIs.

## Production checklist {#production}

- Use TLS and verify the server certificate.
- Load credentials from a secret manager or protected environment.
- Grant the application only the bucket and object permissions it needs.
- Pin and test the Python runtime, SDK, and HTTP dependencies together.
- Define timeouts and handle SDK exceptions, retries, streaming resources, and incomplete multipart uploads explicitly.

See [Identity and Access Management](/administration/identity-access-management/) for server-side policy configuration.

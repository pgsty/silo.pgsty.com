---
title: "Python Quickstart Guide"
url: "/developers/python/minio-py/"
weight: 20
icon: fa-brands fa-python
minio_origin: true
silo_modified: false
---

<a id="python-quickstart-guide"></a>
<a id="minio-python-quickstart"></a>

## MinIO Python Client SDK for Amazon S3 Compatible Cloud Storage [![Slack](https://slack.min.io/slack?type=svg)](https://slack.min.io) [![Apache V2 License](https://img.shields.io/badge/license-Apache%20V2-blue.svg)](https://github.com/minio/minio-py/blob/master/LICENSE) {#minio-python-client-sdk-for-amazon-s3-compatible-cloud-storage}

MinIO Python Client SDK 提供高级 API，可用于访问任意 MinIO 对象存储或其他兼容 Amazon S3 的服务。

本快速入门指南介绍如何安装 MinIO Python Client SDK、连接对象存储服务并创建一个示例文件上传器。

以下示例使用：

- [Python version 3.7+](https://www.python.org/downloads/)
- [MinIO `mc` 命令行工具](https://min.io/docs/minio/linux/reference/minio-mc.html)
- MinIO `play` 测试服务器

`play` 服务器是位于 [https://play.min.io](https://play.min.io) 的公开 MinIO 集群。 该集群运行 MinIO 的最新稳定版本，可用于测试与开发。 示例中的访问凭证对公众开放，上传到 `play` 的所有数据都应视为公开且全网可读。

如需查看完整的 API 与示例列表，请参阅 [Python Client API Reference](https://min.io/docs/minio/linux/developers/python/API.html)

### 安装 MinIO Python SDK {#minio-python-sdk}

Python SDK 要求 Python 版本 3.7+。 你可以使用 `pip` 安装 SDK，或从 [`minio/minio-py` GitHub 仓库](https://github.com/minio/minio-py) 安装：

#### 使用 `pip` {#pip}

```sh
pip3 install minio

```

#### 使用 GitHub 源码安装 {#github}

```sh
git clone https://github.com/minio/minio-py
cd minio-py
python setup.py install

```

### 创建 MinIO Client {#minio-client}

要连接目标服务，请使用 `Minio()` 方法并传入以下必需参数来创建 MinIO Client：

| Parameter | Description |
| --- | --- |
| `endpoint` | 目标服务的 URL。 |
| `access_key` | 服务中某个用户账户的 Access key（用户 ID）。 |
| `secret_key` | 用户账户的 Secret key（密码）。 |

例如：

```py
from minio import Minio

client = Minio("play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
)

```

### 示例：文件上传器 {#id1}

此示例执行以下操作：

- 使用提供的凭证连接到 MinIO `play` 服务器。
- 如果不存在名为 `python-test-bucket` 的存储桶，则创建该存储桶。
- 从 `/tmp` 上传名为 `test-file.txt` 的文件，并将其重命名为 `my-test-file.txt`。
- 使用 [`mc ls`](https://min.io/docs/minio/linux/reference/minio-mc/mc-ls.html) 验证文件已创建。

#### `file_uploader.py` {#file-uploader-py}

```py
# file_uploader.py MinIO Python SDK example
from minio import Minio
from minio.error import S3Error

def main():
    # Create a client with the MinIO server playground, its access key
    # and secret key.
    client = Minio("play.min.io",
        access_key="Q3AM3UQ867SPQQA43P2F",
        secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    )

    # The file to upload, change this path if needed
    source_file = "/tmp/test-file.txt"

    # The destination bucket and filename on the MinIO server
    bucket_name = "python-test-bucket"
    destination_file = "my-test-file.txt"

    # Make the bucket if it doesn't exist.
    found = client.bucket_exists(bucket_name)
    if not found:
        client.make_bucket(bucket_name)
        print("Created bucket", bucket_name)
    else:
        print("Bucket", bucket_name, "already exists")

    # Upload the file, renaming it in the process
    client.fput_object(
        bucket_name, destination_file, source_file,
    )
    print(
        source_file, "successfully uploaded as object",
        destination_file, "to bucket", bucket_name,
    )

if __name__ == "__main__":
    try:
        main()
    except S3Error as exc:
        print("error occurred.", exc)

```

运行此示例：

1. 在 `/tmp` 中创建一个名为 `test-file.txt` 的文件。 如果要使用不同路径或文件名，请修改 `source_file` 的值。
2. 使用以下命令运行 `file_uploader.py`：

```sh
python file_uploader.py

```

如果服务器上不存在该存储桶，输出类似如下内容：

```sh
Created bucket python-test-bucket
/tmp/test-file.txt successfully uploaded as object my-test-file.txt to bucket python-test-bucket

```

3. 使用 `mc ls` 验证已上传文件：

```sh
mc ls play/python-test-bucket
[2023-11-03 22:18:54 UTC]  20KiB STANDARD my-test-file.txt

```

### 更多参考 {#id2}

- [Python Client API Reference](https://min.io/docs/minio/linux/developers/python/API.html)
- [Examples](https://github.com/minio/minio-py/tree/master/examples)

### 进一步了解 {#id3}

- [Complete Documentation](https://min.io/docs/minio/kubernetes/upstream/index.html)

### 参与贡献 {#id4}

[Contributors Guide](https://github.com/minio/minio-py/blob/master/CONTRIBUTING.md)

### 许可证 {#id5}

此 SDK 按 [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0) 分发，更多信息请参阅 [LICENSE](https://github.com/minio/minio-py/blob/master/LICENSE) 和 [NOTICE](https://github.com/minio/minio-go/blob/master/NOTICE)。

[![PYPI](https://img.shields.io/pypi/v/minio.svg)](https://pypi.python.org/pypi/minio)

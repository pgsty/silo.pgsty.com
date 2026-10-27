---
title: "加密文件"
url: "/zh/operations/troubleshooting/encrypting-files/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/troubleshooting/encrypting-files.rst
upstream_modified: true
---

<a id="encrypting-files"></a>
<a id="minio-support-encryption"></a>
<span id="id1" data-td-print-local></span><span id="id3" data-td-print-local></span>

## 说明 {#description}

[`mcli support inspect`](/zh/reference/minio-mc/mc-support-inspect/) 用于从服务端底层磁盘采集原始对象数据与元数据。PGSTY mcli 将采集到的诊断包直接保存在本地，无需注册 SUBNET，也不会自动向外部上传。诊断归档与解密密钥包含底层存储数据，请按敏感资料妥善保管。

<span id="id4" data-td-print-local></span>
## 加密 {#encryption}

当前版本的 SILO 与 mcli 默认对 inspect 输出进行加密（`support inspect` 命令不再设 `--encrypt` 开关）：

```shell
mcli support inspect 'mysilo/mybucket/myobject/xl.meta'
```

如果客户端配置目录中未放置自定义的 `support_public.pem` 公钥，SILO 会自动生成一次性随机密钥，并由 mcli 在完成下载时随文件名一并打印。请立即保存该密钥（丢失后无法找回，PGSTY 也不内置任何厂商后门密钥）。

如果配置了 `support_public.pem`，请妥善保管与之配对的私钥。路径中包含通配符时请加上引号，防止被本地 shell 提前展开。由于递归采集可能拉取多块磁盘上的完整对象分片，建议仅采集排查所需的目标文件。

<span id="id5" data-td-print-local></span>
<a id="minio-support-decryption"></a>
## 解密 {#decryption}

<a id="go"></a>

从维护中的 SILO 源码仓库构建 `inspect` 解密工具（需使用该版本要求的 Go 工具链）：

```shell
git clone --branch RELEASE.2026-10-26T00-00-00Z --depth 1 https://github.com/pgsty/silo.git
cd silo/docs/debugging/inspect
go build -o inspect .
```

对于下载时打印了对称密钥的归档，传入 `-key` 解密：

```shell
./inspect -key=DECRYPTION_KEY /path/to/inspect.enc
```

若省略 `-key` 且未指定私钥文件，工具会交互式提示输入解密密钥。

对于使用 `support_public.pem` 公钥加密的归档，传入对应的私钥文件解密：

```shell
./inspect -private-key=/secure/path/support_private.pem /path/to/inspect.enc
```

使用 `-key` 时，工具会在输入文件同级目录下生成解密后的 ZIP 归档；使用 `-private-key` 时，则会将包含 `inspect.zip` 在内的解密数据流解压到输出目录。向他人发送前请先核查解压内容；注意解开 `inspect.enc` 的外层诊断包装并不会替开启了服务端加密（SSE）的对象本身执行解密。

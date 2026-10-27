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

[`mcli support inspect`](/zh/reference/minio-mc/mc-support-inspect/)从服务端磁盘下载对象数据与元数据。PGSTY mcli 将诊断资料保存在本地，无须注册 SUBNET，也不会自动上传。诊断归档及其解密材料都应按敏感资料保管。

<span id="id4" data-td-print-local></span>
## 加密 {#encryption}

当前 SILO/mcli 会加密 inspect 输出，`support inspect` 命令没有 `--encrypt` 标志。例如：

```shell
mcli support inspect 'mysilo/mybucket/myobject/xl.meta'
```

如果客户端配置目录中没有用户提供的 `support_public.pem`，SILO 会生成随机密钥，mcli 会随下载文件名打印解密密钥。请妥善保存，之后无法恢复。PGSTY 不添加厂商解密密钥。

如果提供了 `support_public.pem`，请保留对应的私钥。包含通配符的路径应加引号，让 shell 将原模式传给 mcli。只采集诊断所需的文件；递归 inspect 可能下载多个磁盘上的对象内容。

<span id="id5" data-td-print-local></span>
<a id="minio-support-decryption"></a>
## 解密 {#decryption}

<a id="go"></a>

从维护中的 SILO 源码构建 inspect 工具，使用该源码要求的 Go 版本：

```shell
git clone --branch RELEASE.2026-10-26T00-00-00Z --depth 1 https://github.com/pgsty/silo.git
cd silo/docs/debugging/inspect
go build -o inspect .
```

对于下载时打印了对称密钥的归档：

```shell
./inspect -key=DECRYPTION_KEY /path/to/inspect.enc
```

如果省略 `-key` 且未找到私钥文件，工具会交互式请求解密密钥。

对于使用 `support_public.pem` 加密的输出，请使用相应私钥：

```shell
./inspect -private-key=/secure/path/support_private.pem /path/to/inspect.enc
```

使用 `-key` 时，工具在输入文件旁生成解密后的 ZIP。使用 `-private-key` 时，会将包括 `inspect.zip` 在内的已解密数据流提取到输出目录。保护这些输出，在检查内容后仅分享给预期接收者。解开诊断归档的外层加密，不会移除采集对象数据自身独立的 SSE 加密。

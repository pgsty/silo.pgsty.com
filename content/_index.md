---
title: "SILO: S3-Compatible Object Storage by Pigsty"
description: "S3-compatible object storage, forked from MinIO and maintained by the Pigsty community: versioned releases, signed packages, the full web console, and security fixes with public advisories."
url: "/"
weight: 1
type: home
cascade:
  type: docs
minio_origin: true
silo_modified: true
---

{{% alert color="warning" %}}
**Important**: SILO is a MinIO fork maintained by the PIGSTY community.
This project is **not** affiliated with, endorsed by, or sponsored by MinIO, Inc. “MinIO” is a trademark of MinIO, Inc., used here solely to identify the upstream project.
This documentation repository lives at [`pgsty/silo.pgsty.com`](https://github.com/pgsty/silo.pgsty.com),
and its content is forked from the upstream MinIO documentation project [`minio/docs`](https://github.com/minio/docs).

{{% /alert %}}

- [Installing and Running MinIO on Docker: Overview](https://youtu.be/mg9NRR6Js1s?ref=docs)
- [Installing and Running MinIO on Docker: Installation Lab](https://youtu.be/Z0FtabDUPtU?ref=docs)
- [Object Storage Essentials](https://www.youtube.com/playlist?list=PLFOIsHSSYIK3WitnqhqfpeZ6fRFKHxIr7)
- [How to Connect to MinIO with JavaScript](https://www.youtube.com/watch?v=yUR4Fvx0D3E&list=PLFOIsHSSYIK3Dd3Y_x7itJT1NUKT5SxDh&index=5)

Silo is S3-compatible object storage maintained by the Pigsty community for existing deployments that need an open release and security-maintenance path. This site documents Silo operations, administration, development, downloads, release boundaries, and compatibility contracts.

## Quickstart {#quickstart}

{{< tabpane text=true persist=header >}}
{{% tab header="Sandbox" %}}
MinIO maintains a sandbox instance of the community server at [https://play.min.io](https://play.min.io). You can use this instance for experimenting or evaluating the MinIO product on your local system.

Follow the [`mc`](/reference/minio-mc/#command-mc) CLI [installation guide](/reference/minio-mc/#mc-install) to install the utility on your local host.

[`mc`](/reference/minio-mc/#command-mc) includes a pre-configured `play` alias for connecting to the sandbox. For example, you can use the following commands to create a bucket and copy objects to `play`:

```shell
mc mb play/mynewbucket

mc cp /path/to/file play/mynewbucket/prefix/filename.extension

mc stat play/mynewbucket/prefix/filename.extension
```

{{% alert color="warning" %}}
**Important**: MinIO’s Play sandbox is an ephemeral public-facing deployment with well-known access credentials. Any private, confidential, internal, secured, or other important data uploaded to Play is effectively made public. Exercise caution and discretion in any data you upload to Play.
{{% /alert %}}
{{% /tab %}}
{{% tab header="Baremetal" %}}
1. Download the Silo server for your operating system

   Use [Download & Install](/download/#server) to select a published Silo package or archive, then verify its checksum. The executable intentionally retains the [`minio server`](/reference/minio-server/#command-minio.server) command contract.
2. Create a folder for object data

   For example, create a folder `~/minio` in Linux/MacOS or `C:\minio` in Windows.
3. Start the MinIO Server

   Run the [`minio server`](/reference/minio-server/#command-minio.server) specifying the path to the directory and the [`--console-address`](/reference/minio-server/#minio.server.-console-address) parameter to set a static console listen path:

   ```shell
   minio server ~/minio --console-address :9001
   # For Windows, use minio.exe server ~/minio --console-address :9001
   ```

   The output includes connection instructions for both [`mc`](/reference/minio-mc/#command-mc) and connecting to the Console using your browser.
{{% /tab %}}
{{% tab header="Kubernetes" %}}
Use the [`pgsty/minio`](https://hub.docker.com/r/pgsty/minio) image and follow the [Silo tenant deployment guide](/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/). Pin a tested release tag or digest; do not treat `latest` as a production version contract.
{{% /tab %}}
{{< /tabpane >}}

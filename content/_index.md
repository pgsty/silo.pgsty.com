---
title: "SILO: Community-Maintained MinIO Fork by Pigsty"
description: "A community-maintained MinIO fork providing security updates, versioned releases, S3 compatibility, and operational continuity for existing deployments."
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

MinIO is a Kubernetes-native S3-compatible object storage solution designed to deploy wherever your applications are - on premises, in the private cloud, in the public cloud, and edge infrastructure. MinIO is designed to support modern application workload patterns where high performance distributed computing meets petabyte-scale storage requirements.
This site documents Operations, Administration, and Development of SILO Community Object Storage deployments on supported platforms.

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
1. Download the MinIO Server Process for your Operating System

   Follow the instructions on the [MinIO Download Page](https://min.io/downloads?ref=docs) for your operating system to download and install the [`minio server`](/reference/minio-server/#command-minio.server) process.
2. Create a folder for use with MinIO

   For example, create a folder `~/minio` in Linux/MacOS or `C:\minio` in Windows.
3. Start the MinIO Server

   Run the [`minio server`](/reference/minio-server/#command-minio.server) specifying the path to the directory and the [`--console-address`](/reference/minio-server/#minio.server.-console-address) parameter to set a static console listen path:

   ```shell
   minio server ~/minio --console-address :9001
   # For windows, use minio.exe server ~/minio --console-address :9001`
   ```

   The output includes connection instructions for both [`mc`](/reference/minio-mc/#command-mc) and connecting to the Console using your browser.
{{% /tab %}}
{{% tab header="Kubernetes" %}}
Download [minio-dev.yaml](https://raw.githubusercontent.com/minio/docs/master/source/extra/examples/minio-dev.yaml) to your host machine:

```shell
curl https://raw.githubusercontent.com/minio/docs/master/source/extra/examples/minio-dev.yaml -O
```

The file describes two Kubernetes resources:

- A new namespace `minio-dev`, and
- A MinIO pod using a drive or volume on the Worker Node for serving data

Use `kubectl port-forward` to access the Pod, or create a service for the pod for which you can configure Ingress, Load Balancing, or similar Kubernetes-level networking.
{{% /tab %}}
{{< /tabpane >}}

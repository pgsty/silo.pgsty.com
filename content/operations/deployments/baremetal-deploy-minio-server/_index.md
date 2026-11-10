---
title: "Install the Silo Server"
url: "/operations/deployments/baremetal-deploy-minio-server/"
weight: 10
icon: fa-solid fa-hard-drive
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/deployments/baremetal-deploy-minio-server.rst
upstream_modified: true
---

<a id="install-the-minio-server"></a>
<a id="deploy-minio-standalone"></a>

Install Silo on a physical machine or virtualized host using the current [server artifacts](/download/#server) and the platform-specific instructions in this section. SILO ships the server executable (`silo`), Linux packages (`silo`), `systemd` unit (`silo.service`), and container image (`docker.io/pgsty/silo`) under the `silo` name, while `MINIO_*` environment variables, `/etc/default/minio` fallback when `/etc/default/silo` is absent, S3 and Admin wire APIs, and the on-disk erasure format retain MinIO-compatible names.

---
title: "Deployment and Upgrades"
description: "Choose a deployment model, install SILO, and plan upgrades using the exact component versions."
url: "/operations/deployments/"
weight: 20
---

Choose a deployment model, install SILO, and plan upgrades using the exact component versions. The current published baseline is [SILO Server 20261109](/blog/release/silo-20261109/) (`RELEASE.2026-11-09T00-00-00Z`, package `20261109000000.0.0`, standalone `helm/silo` chart `7.0.4`), paired with [Console 2.7.0](/blog/release/console-2.7.0/), [mcli 20261109](/blog/release/mcli-20261109/), and `silo-pkg` `v3.16.0`.

- [Installation and package management](/operations/deployments/installation/)
- [Bare-metal deployment](/operations/deployments/baremetal/)
- [Kubernetes deployment](/operations/deployments/kubernetes/)
- [Upgrade a bare-metal deployment](/operations/deployments/baremetal-upgrade-minio-deployment/)
- [Upgrade a Kubernetes deployment](/operations/deployments/k8s-upgrade-minio-tenant-on-kubernetes/)
- [Component versions and upgrade boundaries](/compatibility/versions/)

Inherited MinIO Operator instructions do not establish release acceptance for arbitrary upstream versions. The maintained stack is SILO, SILO Console, mcli, and silo-pkg; upstream compatibility is best effort.

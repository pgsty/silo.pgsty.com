---
title: "部署与升级"
description: "选择部署方式，安装 SILO，并按实际组件版本安排升级。"
url: "/zh/operations/deployments/"
weight: 20
---

选择部署方式，安装 SILO，并按实际组件版本安排升级。当前正式发布基线为 [SILO Server 20261109](/zh/blog/release/silo-20261109/)（`RELEASE.2026-11-09T00-00-00Z`，软件包版本 `20261109000000.0.0`，独立 `helm/silo` Chart `7.0.4`），配套 [Console 2.7.0](/zh/blog/release/console-2.7.0/)、[mcli 20261109](/zh/blog/release/mcli-20261109/) 与 `silo-pkg` `v3.16.0`。

- [安装与软件包管理](/zh/operations/deployments/installation/)
- [裸机部署](/zh/operations/deployments/baremetal/)
- [Kubernetes 部署](/zh/operations/deployments/kubernetes/)
- [升级裸机部署](/zh/operations/deployments/baremetal-upgrade-minio-deployment/)
- [升级 Kubernetes 部署](/zh/operations/deployments/k8s-upgrade-minio-tenant-on-kubernetes/)
- [组件版本与升级边界](/zh/compatibility/versions/)

继承的 MinIO Operator 指南不构成对任意上游版本的发布验收承诺。正式维护组合为 SILO、SILO Console、mcli 和 silo-pkg；上游兼容性尽最大努力提供。

---
title: "故障排查"
url: "/zh/operations/troubleshooting/"
weight: 100
icon: fa-solid fa-screwdriver-wrench
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/troubleshooting.rst
upstream_modified: true
---

<a id="id1" data-td-print-local></a>

## 概述 {#id3}

<a id="slack"></a>

可复现的 SILO 问题请提交至 [SILO issue tracker](https://github.com/pgsty/silo/issues)，附上 Server 与客户端版本、拓扑、已脱敏配置、错误信息和最小复现。疑似安全漏洞请遵循[私密安全报告流程](/zh/about/security/)。

SILO 由 PGSTY 独立维护，MinIO SUBNET 订阅及原上游 Slack 均不是 SILO 的支持渠道。社区协助不承诺响应时间或恢复 SLA。

## 工具 {#id4}

维护的客户端以 `mcli` 分发，继承文档也使用兼容命令名 `mc`。

- [`mcli admin info`](/zh/reference/minio-mc-admin/mc-admin-info/) 显示部署信息。
- [`mcli admin trace`](/zh/reference/minio-mc-admin/mc-admin-trace/) 跟踪 API 请求。
- [`mcli admin logs`](/zh/reference/minio-mc-admin/mc-admin-logs/) 查看服务端日志。
- [`mcli support diag`](/zh/reference/minio-mc/mc-support-diag/)、[`profile`](/zh/reference/minio-mc/mc-support-profile/) 和 [`inspect`](/zh/reference/minio-mc/mc-support-inspect/) 在本地收集诊断，无需注册 SUBNET，也不会自动上传。

诊断文件可能包含拓扑、配置、元数据或对象原文，分享前应检查其内容。另见[文件加密](/zh/operations/troubleshooting/encrypting-files/)。

## 升级与版本支持 {#id5}

使用[已发布制品](/zh/download/)，并阅读跨越版本的[发布说明](/zh/blog/release/)和[安全公告](/zh/about/security-advisories/)。源码改动或计划发布日期不能证明公开制品已经可用。

### 选择升级版本 {#id6}

优先处理影响实际部署的问题，在生产升级前验证确切版本、工作负载和恢复流程。SILO 不承诺继承的上游六个月支持窗口。遵循[协调升级流程](/zh/operations/deployments/baremetal-upgrade-minio-deployment/)；维护栈已禁用在线 `mcli admin update` 和客户端 `mcli update`。

### 版本对齐 {#id7}

正式支持的组合为 SILO Server、SILO Console、PGSTY mcli 和 `silo-pkg`；KES 是独立发布的可选服务。按[组件矩阵](/zh/compatibility/versions/)核对版本，不能仅凭发布日期相近推断兼容。对原厂 MinIO/MC 的兼容属于 best effort。

保留的 [MinIO Operator 指南](/zh/operations/deployments/kubernetes/)使用归档的 `v7.1.1` 快照。应在实际 Kubernetes 平台验证该组合并显式固定 SILO 镜像；更新 Operator 不会自动更新现有 Tenant 的服务端镜像。

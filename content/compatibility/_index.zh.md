---
title: "兼容性"
linkTitle: "兼容性"
description: "Silo 与 MinIO 在服务端、客户端与控制台三处的一致之处，以及有意为之的差异。"
url: "/zh/compatibility/"
weight: 7
type: docs
icon: fa-solid fa-code-compare
minio_origin: false
silo_modified: false
---

Silo 是 MinIO 的社区分支，二者是近亲而非两套彼此独立的产品。本节按组件逐一记录：Silo 从 MinIO 继承了什么、在哪些地方有意做出了不同的选择，以及这对双向迁移意味着什么。

一个组件一页：`silo` 服务端、`mcli` 客户端，以及 Web 控制台。[特性设计](/zh/compatibility/feature/)子节则记录相反的方向——Silo 在上游之外新增能力的设计笔记。

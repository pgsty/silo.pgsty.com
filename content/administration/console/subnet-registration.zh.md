---
title: "SUBNET"
url: "/zh/administration/console/subnet-registration/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/53e14984e3cacacd5a0206822693f15442186bb8/source/administration/console/subnet-registration.rst
upstream_modified: true
---

<a id="subnet"></a>
<a id="minio-console-subscription"></a>
<a id="id2"></a>
<a id="id3"></a>
<a id="id4"></a>

## SILO 的许可与支持 {#license}

SILO Console 保留开源 AGPL 许可信息、对应源码与第三方署名页面。它不提供 MinIO 商业订阅注册、购买或在线续订，也不会把诊断自动上传到 SUBNET。
此 URL 保留用于旧文档兼容；旧上游的商业订阅说明不适用于 SILO。

## 健康诊断 {#health}

Health 页面生成部署健康报告，可下载用于自己的诊断流程。文件可能包含主机名等环境信息，应在主动分享前检查。SILO 不自动将其上传。

## 性能 {#performance}

性能工具测试 S3 GET/PUT 等路径。应在适合的测试环境中运行，并结合实际负载解释结果。

## 性能剖析 {#profile}

Profile 页面保留服务端剖析与本地下载功能，不依赖 SUBNET 订阅。

## 对象检查 {#inspect}

Inspect 工具收集对象的纠删码元数据；由管理员自行保管并使用自己的诊断工具分析。

## Call Home {#call-home}

SILO 不发送周期性健康报告或日志到 MinIO。旧命令保留兼容入口，但 `mcli support callhome enable` 返回禁用错误；disable/status 用于检查或清理旧设置。

参见 [mcli 兼容性](/zh/compatibility/mcli/#subnet)、[许可说明](/zh/about/license/)与[组件版本](/zh/compatibility/versions/)。

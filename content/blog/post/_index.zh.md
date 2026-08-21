---
title: 文章
linkTitle: 文章
description: 关于 MinIO、S3 兼容对象存储与 SILO 社区分支的文章与分析。
weight: 10
icon: fa-solid fa-newspaper
sidebar_expanded: true
module: [BLOG]
# 沉浸式文章：cascade 里的四个键是 OINK 0.6.0 的配方 —— 文章自带的 featured
# 图铺成整幅 hero，右栏换成随正文起始的流式目录并去掉分类云，左侧文档树与面
# 包屑一并让位。没有配图的文章会自动退回普通排版，不会出错。
#
# Hugo 的 cascade 也作用在声明它的这一页上，而栏目索引是导航面不是文章，所以
# 下面五个键把常规文档壳按回来（同一页的 front matter 优先于 cascade）。
sidebar_enabled: true
breadcrumb: true
toc_taxonomies: true
toc_style: fixed
featured_image: none
cascade:
  featured_image: hero
  toc_style: flow
  toc_taxonomies: false
  sidebar_enabled: false
  breadcrumb: false
---

关于 MinIO、S3 兼容对象存储与 SILO 社区分支的文章与分析。

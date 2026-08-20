---
title: "mc idp ldap policy"
url: "/zh/reference/minio-mc/mc-idp-ldap-policy/"
weight: 170
icon: fa-solid fa-file-shield
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-idp-ldap-policy.rst
upstream_modified: false
---

<a id="mc-idp-ldap-policy"></a>
<a id="minio-mc-idp-ldap-policy"></a>

<a id="command-mc.idp.ldap.policy"></a>

> [!NOTE]
> **新增: RELEASE.2023-05-26T23-31-54Z**
>
> [`mc idp ldap policy`](#command-mc.idp.ldap.policy) 及其子命令替代 `mc admin idp ldap policy`。

## 说明 {#id2}

[`mc idp ldap policy`](#command-mc.idp.ldap.policy) 命令用于显示策略与关联组或用户之间的映射关系。

[`mc idp ldap policy`](#command-mc.idp.ldap.policy) 命令仅支持 MinIO 部署。

[`mc idp ldap policy`](#command-mc.idp.ldap.policy) 命令包含以下子命令：

<table>
  <thead>
    <tr>
      <th><p>子命令</p></th>
      <th><p>说明</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/zh/reference/minio-mc/mc-idp-ldap-policy-attach/#command-mc.idp.ldap.policy.attach"><code>mc idp ldap policy attach</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc/mc-idp-ldap-policy-attach/#command-mc.idp.ldap.policy.attach"><code>mc idp ldap policy attach</code></a> 命令将一个或多个策略附加到实体。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc/mc-idp-ldap-policy-detach/#command-mc.idp.ldap.policy.detach"><code>mc idp ldap policy detach</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc/mc-idp-ldap-policy-detach/#command-mc.idp.ldap.policy.detach"><code>mc idp ldap policy detach</code></a> 命令可从实体分离一个或多个策略。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc/mc-idp-ldap-policy-entities/#command-mc.idp.ldap.policy.entities"><code>mc idp ldap policy entities</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc/mc-idp-ldap-policy-entities/#command-mc.idp.ldap.policy.entities"><code>mc idp ldap policy entities</code></a> 命令显示用户、组和/或策略的映射关系列表。</p></td>
    </tr>
  </tbody>
</table>

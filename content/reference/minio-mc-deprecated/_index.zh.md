---
title: "弃用命令"
url: "/zh/reference/minio-mc-deprecated/"
weight: 40
icon: fa-solid fa-box-archive
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-deprecated.rst
upstream_modified: false
---

<a id="id1"></a>

下表列出了 MinIO 已弃用的命令。 该表包含：

- 已弃用命令
- 替代命令（如适用）
- 弃用版本

## 弃用命令表 {#id3}

| 已弃用命令 | 替代命令 | 弃用版本 |
| --- | --- | --- |
| `mc ilm add` | [`mc ilm rule add`](/zh/reference/minio-mc/mc-ilm-rule-add/#command-mc.ilm.rule.add) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc ilm edit` | [`mc ilm rule edit`](/zh/reference/minio-mc/mc-ilm-rule-edit/#command-mc.ilm.rule.edit) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc ilm export` | [`mc ilm rule export`](/zh/reference/minio-mc/mc-ilm-rule-export/#command-mc.ilm.rule.export) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc ilm import` | [`mc ilm rule import`](/zh/reference/minio-mc/mc-ilm-rule-import/#command-mc.ilm.rule.import) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc ilm ls` | [`mc ilm rule ls`](/zh/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc ilm rm` | [`mc ilm rule rm`](/zh/reference/minio-mc/mc-ilm-rule-rm/#command-mc.ilm.rule.rm) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc quota` | 无 | mc RELEASE.2024-07-31T15-58-33Z |
| `mc quota clear` | 无 | mc RELEASE.2024-07-31T15-58-33Z |
| `mc quota info` | 无 | mc RELEASE.2024-07-31T15-58-33Z |
| `mc quota set` | 无 | mc RELEASE.2024-07-31T15-58-33Z |
| `mc replicate diff` | [`mc replicate backlog`](/zh/reference/minio-mc/mc-replicate-backlog/#command-mc.replicate.backlog) | mc RELEASE.2023-07-18T21-05-38Z |

## 弃用管理命令表 {#id4}

| 已弃用命令 | 替代命令 | 弃用版本 |
| --- | --- | --- |
| `mc admin bucket remote` | [`mc replicate`](/zh/reference/minio-mc/mc-replicate/#command-mc.replicate) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin bucket remote add` | [`mc replicate add`](/zh/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin bucket remote ls` | [`mc replicate ls`](/zh/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin bucket remote rm` | [`mc replicate rm`](/zh/reference/minio-mc/mc-replicate-rm/#command-mc.replicate.rm) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin bucket remote update` | [`mc replicate update`](/zh/reference/minio-mc/mc-replicate-update/#command-mc.replicate.update) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin bucket quota` | [`mc quota clear`](/zh/reference/deprecated/mc-quota-clear/#command-mc.quota.clear), [`mc quota info`](/zh/reference/deprecated/mc-quota-info/#command-mc.quota.info), [`mc quota set`](/zh/reference/deprecated/mc-quota-set/#command-mc.quota.set) | mc RELEASE.2022-12-13T00-23-28Z |
| `mc admin console` | [`mc admin logs`](/zh/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs) | mc RELEASE.2022-06-26T18-51-48Z |
| `mc admin idp ldap add` | [`mc idp ldap add`](/zh/reference/minio-mc/mc-idp-ldap-add/#command-mc.idp.ldap.add) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap disable` | [`mc idp ldap disable`](/zh/reference/minio-mc/mc-idp-ldap-disable/#command-mc.idp.ldap.disable) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap enable` | [`mc idp ldap enable`](/zh/reference/minio-mc/mc-idp-ldap-enable/#command-mc.idp.ldap.enable) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap info` | [`mc idp ldap info`](/zh/reference/minio-mc/mc-idp-ldap-info/#command-mc.idp.ldap.info) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap ls` | [`mc idp ldap ls`](/zh/reference/minio-mc/mc-idp-ldap-ls/#command-mc.idp.ldap.ls) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap policy` | [`mc idp ldap policy`](/zh/reference/minio-mc/mc-idp-ldap-policy/#command-mc.idp.ldap.policy) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap rm` | [`mc idp ldap rm`](/zh/reference/minio-mc/mc-idp-ldap-rm/#command-mc.idp.ldap.rm) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap update` | [`mc idp ldap update`](/zh/reference/minio-mc/mc-idp-ldap-update/#command-mc.idp.ldap.update) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid add` | [`mc idp openid add`](/zh/reference/minio-mc/mc-idp-openid/#mc.idp.openid.add) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid disable` | [`mc idp openid disable`](/zh/reference/minio-mc/mc-idp-openid/#mc.idp.openid.disable) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid enable` | [`mc idp openid enable`](/zh/reference/minio-mc/mc-idp-openid/#mc.idp.openid.enable) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid info` | [`mc idp openid info`](/zh/reference/minio-mc/mc-idp-openid/#mc.idp.openid.info) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid ls` | [`mc idp openid ls`](/zh/reference/minio-mc/mc-idp-openid/#mc.idp.openid.ls) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid rm` | [`mc idp openid rm`](/zh/reference/minio-mc/mc-idp-openid/#mc.idp.openid.rm) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid update` | [`mc idp openid update`](/zh/reference/minio-mc/mc-idp-openid/#mc.idp.openid.update) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin policy add` | [`mc admin policy create`](/zh/reference/minio-mc-admin/mc-admin-policy-create/#command-mc.admin.policy.create) | mc RELEASE.2023-03-20T17-17-53Z |
| `mc admin policy set` | [`mc admin policy attach`](/zh/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach) | mc RELEASE.2023-03-20T17-17-53Z |
| `mc admin policy unset` | [`mc admin policy detach`](/zh/reference/minio-mc-admin/mc-admin-policy-detach/#command-mc.admin.policy.detach) | mc RELEASE.2023-03-20T17-17-53Z |
| `mc admin policy update` | [`mc admin policy attach`](/zh/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach) 或 [`mc admin policy detach`](/zh/reference/minio-mc-admin/mc-admin-policy-detach/#command-mc.admin.policy.detach) | mc RELEASE.2023-03-20T17-17-53Z |
| `mc admin profile` | [`mc support profile`](/zh/reference/minio-mc/mc-support-profile/#command-mc.support.profile) | mc RELEASE.2023-04-06T16-51-10Z |
| `mc admin replicate edit` | [`mc admin replicate update`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.update) | mc RELEASE.2023-01-11T03-14-16Z |
| `mc admin replicate remove` | [`mc admin replicate rm`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.rm) | mc RELEASE.2023-01-11T03-14-16Z |
| `mc admin speedtest` | [`mc support perf`](/zh/reference/minio-mc/mc-support-perf/#command-mc.support.perf) | mc RELEASE.2022-07-24T02-25-13Z |
| `mc admin tier add` | [`mc ilm tier add`](/zh/reference/minio-mc/mc-ilm-tier-add/#command-mc.ilm.tier.add) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin tier edit` | [`mc ilm tier update`](/zh/reference/minio-mc/mc-ilm-tier-update/#command-mc.ilm.tier.update) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin tier ls` | [`mc ilm tier ls`](/zh/reference/minio-mc/mc-ilm-tier-ls/#command-mc.ilm.tier.ls) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin top` | [`mc support top`](/zh/reference/minio-mc/mc-support-top/#command-mc.support.top) | mc RELEASE.2022-08-11T00-30-48Z |

---
title: "Deprecated Commands"
url: "/reference/minio-mc-deprecated/"
weight: 40
icon: fa-solid fa-box-archive
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-deprecated.rst
upstream_modified: false
---

<a id="deprecated-commands"></a>

The following table lists the commands deprecated by MinIO. The table includes:

- Deprecated Command
- Replacement command (if applicable)
- Version of deprecation

## Table of Deprecated Commands {#table-of-deprecated-commands}

| Deprecated Command | Replacement Command | Version of Change |
| --- | --- | --- |
| `mc ilm add` | [`mc ilm rule add`](/reference/minio-mc/mc-ilm-rule-add/#command-mc.ilm.rule.add) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc ilm edit` | [`mc ilm rule edit`](/reference/minio-mc/mc-ilm-rule-edit/#command-mc.ilm.rule.edit) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc ilm export` | [`mc ilm rule export`](/reference/minio-mc/mc-ilm-rule-export/#command-mc.ilm.rule.export) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc ilm import` | [`mc ilm rule import`](/reference/minio-mc/mc-ilm-rule-import/#command-mc.ilm.rule.import) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc ilm ls` | [`mc ilm rule ls`](/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc ilm rm` | [`mc ilm rule rm`](/reference/minio-mc/mc-ilm-rule-rm/#command-mc.ilm.rule.rm) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc quota` | None | mc RELEASE.2024-07-31T15-58-33Z |
| `mc quota clear` | None | mc RELEASE.2024-07-31T15-58-33Z |
| `mc quota info` | None | mc RELEASE.2024-07-31T15-58-33Z |
| `mc quota set` | None | mc RELEASE.2024-07-31T15-58-33Z |
| `mc replicate diff` | [`mc replicate backlog`](/reference/minio-mc/mc-replicate-backlog/#command-mc.replicate.backlog) | mc RELEASE.2023-07-18T21-05-38Z |

## Table of Deprecated Admin Commands {#table-of-deprecated-admin-commands}

| Deprecated Command | Replacement Command | Version of Change |
| --- | --- | --- |
| `mc admin bucket remote` | [`mc replicate`](/reference/minio-mc/mc-replicate/#command-mc.replicate) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin bucket remote add` | [`mc replicate add`](/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin bucket remote ls` | [`mc replicate ls`](/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin bucket remote rm` | [`mc replicate rm`](/reference/minio-mc/mc-replicate-rm/#command-mc.replicate.rm) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin bucket remote update` | [`mc replicate update`](/reference/minio-mc/mc-replicate-update/#command-mc.replicate.update) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin bucket quota` | [`mc quota clear`](/reference/deprecated/mc-quota-clear/#command-mc.quota.clear), [`mc quota info`](/reference/deprecated/mc-quota-info/#command-mc.quota.info), [`mc quota set`](/reference/deprecated/mc-quota-set/#command-mc.quota.set) | mc RELEASE.2022-12-13T00-23-28Z |
| `mc admin console` | [`mc admin logs`](/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs) | mc RELEASE.2022-06-26T18-51-48Z |
| `mc admin idp ldap add` | [`mc idp ldap add`](/reference/minio-mc/mc-idp-ldap-add/#command-mc.idp.ldap.add) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap disable` | [`mc idp ldap disable`](/reference/minio-mc/mc-idp-ldap-disable/#command-mc.idp.ldap.disable) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap enable` | [`mc idp ldap enable`](/reference/minio-mc/mc-idp-ldap-enable/#command-mc.idp.ldap.enable) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap info` | [`mc idp ldap info`](/reference/minio-mc/mc-idp-ldap-info/#command-mc.idp.ldap.info) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap ls` | [`mc idp ldap ls`](/reference/minio-mc/mc-idp-ldap-ls/#command-mc.idp.ldap.ls) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap policy` | [`mc idp ldap policy`](/reference/minio-mc/mc-idp-ldap-policy/#command-mc.idp.ldap.policy) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap rm` | [`mc idp ldap rm`](/reference/minio-mc/mc-idp-ldap-rm/#command-mc.idp.ldap.rm) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp ldap update` | [`mc idp ldap update`](/reference/minio-mc/mc-idp-ldap-update/#command-mc.idp.ldap.update) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid add` | [`mc idp openid add`](/reference/minio-mc/mc-idp-openid/#mc.idp.openid.add) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid disable` | [`mc idp openid disable`](/reference/minio-mc/mc-idp-openid/#mc.idp.openid.disable) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid enable` | [`mc idp openid enable`](/reference/minio-mc/mc-idp-openid/#mc.idp.openid.enable) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid info` | [`mc idp openid info`](/reference/minio-mc/mc-idp-openid/#mc.idp.openid.info) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid ls` | [`mc idp openid ls`](/reference/minio-mc/mc-idp-openid/#mc.idp.openid.ls) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid rm` | [`mc idp openid rm`](/reference/minio-mc/mc-idp-openid/#mc.idp.openid.rm) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin idp openid update` | [`mc idp openid update`](/reference/minio-mc/mc-idp-openid/#mc.idp.openid.update) | mc RELEASE.2023-05-26T23-31-54Z |
| `mc admin policy add` | [`mc admin policy create`](/reference/minio-mc-admin/mc-admin-policy-create/#command-mc.admin.policy.create) | mc RELEASE.2023-03-20T17-17-53Z |
| `mc admin policy set` | [`mc admin policy attach`](/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach) | mc RELEASE.2023-03-20T17-17-53Z |
| `mc admin policy unset` | [`mc admin policy detach`](/reference/minio-mc-admin/mc-admin-policy-detach/#command-mc.admin.policy.detach) | mc RELEASE.2023-03-20T17-17-53Z |
| `mc admin policy update` | [`mc admin policy attach`](/reference/minio-mc-admin/mc-admin-policy-attach/#command-mc.admin.policy.attach) or [`mc admin policy detach`](/reference/minio-mc-admin/mc-admin-policy-detach/#command-mc.admin.policy.detach) | mc RELEASE.2023-03-20T17-17-53Z |
| `mc admin profile` | [`mc support profile`](/reference/minio-mc/mc-support-profile/#command-mc.support.profile) | mc RELEASE.2023-04-06T16-51-10Z |
| `mc admin replicate edit` | [`mc admin replicate update`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.update) | mc RELEASE.2023-01-11T03-14-16Z |
| `mc admin replicate remove` | [`mc admin replicate rm`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.rm) | mc RELEASE.2023-01-11T03-14-16Z |
| `mc admin speedtest` | [`mc support perf`](/reference/minio-mc/mc-support-perf/#command-mc.support.perf) | mc RELEASE.2022-07-24T02-25-13Z |
| `mc admin tier add` | [`mc ilm tier add`](/reference/minio-mc/mc-ilm-tier-add/#command-mc.ilm.tier.add) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin tier edit` | [`mc ilm tier update`](/reference/minio-mc/mc-ilm-tier-update/#command-mc.ilm.tier.update) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin tier ls` | [`mc ilm tier ls`](/reference/minio-mc/mc-ilm-tier-ls/#command-mc.ilm.tier.ls) | mc RELEASE.2022-12-24T15-21-38Z |
| `mc admin top` | [`mc support top`](/reference/minio-mc/mc-support-top/#command-mc.support.top) | mc RELEASE.2022-08-11T00-30-48Z |

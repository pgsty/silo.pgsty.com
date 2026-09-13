---
title: "mc license update"
url: "/reference/minio-mc/mc-license-update/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-license-update.rst
upstream_modified: true
---

<a id="mc-license-update"></a>
<a id="command-mc.license.update"></a>
<a id="examples"></a>
<a id="update-the-license-key-for-a-deployment-with-alias-minio1"></a>
<a id="parameters"></a>
<a id="mc.license.update.ALIAS"></a>
<a id="mc.license.update.LICENSE-FILE-WITH-PATH"></a>
<a id="mc.license.update.-airgap"></a>
<a id="global-flags"></a>

## License commands {#description}

SILO uses AGPLv3. License commands preserve legacy command syntax and cannot
purchase or activate a MinIO commercial subscription.

| Command | Behavior |
| --- | --- |
| `mcli license info ALIAS` | Display locally stored license information without SUBNET access |
| `mcli license unregister ALIAS` | Clear local license registration state |
| `mcli license update ALIAS license.key` | Retain the explicit local-file path; acceptance depends on the target server |
| `mcli license update ALIAS` | Online renewal disabled, exit 1 |
| `mcli license register ALIAS` | Registration disabled, exit 1 |

## Syntax {#syntax}

Use `mcli license COMMAND --help` for flags accepted by the installed version.
Legacy `--airgap` and API-key flags cannot re-enable online registration/renewal.
Ordinary object storage and diagnostics do not require SUBNET registration.

See [SILO licensing](/about/license/) and [mcli compatibility](/compatibility/mcli/#subnet).

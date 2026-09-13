---
title: "mc license"
url: "/reference/minio-mc/mc-license/"
weight: 210
icon: fa-solid fa-certificate
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-license.rst
upstream_modified: true
---

<a id="mc-license"></a>
<a id="command-mc.license"></a>
<a id="subcommands"></a>

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

---
title: "mc update"
url: "/reference/minio-mc/mc-update/"
weight: 420
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-update.rst
upstream_modified: true
---

<a id="mc-update"></a>

<a id="command-mc.update"></a>

## Syntax {#syntax}

The Pigsty-maintained client keeps [`mc update`](#command-mc.update) for command-line compatibility, but **self-update is intentionally disabled**. The command does not contact a release feed, download a binary, or replace the installed `mc`/`mcli` executable. It prints an error and exits with status `1`.

Upgrade through [Download & Install](/download/#client), the [Pigsty package repository](https://pigsty.io/docs/repo/infra/list/#object-storage), or [GitHub Releases](https://github.com/pgsty/mc/releases).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command reports that self-update is disabled and exits with status `1`:

```shell
mc update
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] update [--json] [RELEASE-URL]
```

- Brackets `[]` indicate optional parameters.
- `RELEASE-URL` is accepted only for compatibility and is not contacted.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

The non-JSON error text is:

```text
Self-update is disabled in the Pigsty mc fork; upgrade only through the Pigsty package repository or https://github.com/pgsty/mc/releases.
```

### Global Flags {#global-flags}

##### `--json` {#mc.update.-json}

*mc-cmd*

*Optional*

Formats the disabled-update error as one [JSON Lines](https://jsonlines.org/)<a id="json-lines"></a> object. This flag does not enable updating.

For example:

```shell
mc update --json
```

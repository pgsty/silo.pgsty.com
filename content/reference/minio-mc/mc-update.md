---
title: "mc update"
url: "/reference/minio-mc/mc-update/"
weight: 420
minio_origin: true
silo_modified: false
---

<a id="mc-update"></a>

<a id="command-mc.update"></a>

## Syntax {#syntax}

The [`mc update`](#command-mc.update) command automatically updates the **`mc`** binary to the latest stable version.

Running this command is equivalent to manually downloading the latest stable binary and using it to replace the existing `mc` installation on the host machine.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command updates the **`mc`** binary on the local host:

```shell
mc update
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] update
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

Use [`mc update`](#command-mc.update) after updating the **`minio`** server binary to ensure consistent behavior and compatibility.

### Global Flags {#global-flags}

##### `--json` {#mc.update.-json}

*mc-cmd*

*Optional*

Enables [JSON lines](http://jsonlines.org/)<a id="json-lines"></a> formatted output to the console.

For example:

```shell
mc --json COMMAND
```

---
title: "Config Environment Files Are Not Shell Scripts"
linkTitle: "Config Env File Contract"
date: 2026-08-28
lastmod: 2026-09-02
author: "Ruohang Feng"
summary: >
  MINIO_CONFIG_ENV_FILE is parsed directly by SILO, not sourced by a shell. A shell-identifier check therefore rejected valid named configuration targets such as my-hook. This record defines the compatible key grammar, whitespace and quoting rules, failure behavior, security boundary, and regression tests.
tags: [Design, Configuration, Compatibility, Operations]
weight: 16
draft: false
url: "/blog/design/config-env-file/"
---

This record defines the startup contract for `MINIO_CONFIG_ENV_FILE` and explains the compatibility repair committed in SILO as `2aea7fe9c`.

> **Status on 2026-08-28:** implementation, focused tests, the complete `cmd` and `internal` suites, tagged tests, race tests, vet, lint, generated-file checks, rebrand guards, build, and an independent local Fable Max review are complete. The commit was merged into `main` on 2026-08-29 as `2aea7fe9c`; tag, package, image, deployment, and production verification remain separate gates.<br>
> **Scope:** environment-file parsing and named-target discovery only. No configuration key, subsystem, value, precedence, storage format, or client API changes.<br>
> **Compatibility rule:** the file is a SILO input format. Supporting an optional `export` prefix does not make it a POSIX shell program.

## Too Long; Didn't Read (TL;DR) {#tldr}

SILO can load startup variables from a file:

```shell
export MINIO_CONFIG_ENV_FILE=/etc/default/silo
silo server /data
```

The parser accepts assignments such as:

```dotenv
MINIO_ROOT_USER = silo-admin
MINIO_ROOT_PASSWORD = "  significant surrounding spaces  "
MINIO_NOTIFY_WEBHOOK_ENABLE_my-hook = off
MINIO_NOTIFY_WEBHOOK_ENDPOINT_my-hook = https://events.example.com/minio
```

The last two names are important. Multi-target configuration appends the target name verbatim after an underscore. The configuration subsystem does not restrict a target to a shell identifier; names containing `-`, `.`, `:`, digits, or printable Unicode can be discovered and resolved exactly.

A hardening change accidentally validated every key as `[A-Za-z_][A-Za-z0-9_]*`. It made `my-hook` invalid and stopped the server during restart even though the previous loader and the configuration target model accepted it. The repair validates what SILO actually needs instead:

- the name is non-empty, valid UTF-8, and made of visible non-whitespace characters;
- `=` and NUL are not allowed in a name;
- NUL is not allowed in a value;
- invalid input reports file and line without reporting the value;
- the complete file is parsed before any assignment is applied.

## Why the regression was real {#regression}

The environment-file loader calls `os.Setenv` after parsing. An operating-system environment is a list of strings, not a shell variable namespace. Shell assignment syntax is narrower because the shell must tokenize and expand variable names in its own language.

Named SILO configuration targets are built differently:

```text
MINIO_<SUBSYSTEM>_<PARAMETER>_<target>
```

For example:

```text
MINIO_NOTIFY_WEBHOOK_ENABLE_my-hook
MINIO_NOTIFY_WEBHOOK_ENDPOINT_my-hook
```

Target discovery lists variables by the fixed parameter prefix and treats the remaining suffix as the target name. Target lookup reconstructs the same name without uppercasing or sanitizing that suffix. Rejecting `-` in the file parser therefore broke a valid discover-to-resolve path; it did not protect a shell evaluation path because no shell evaluates the file.

The failure is operationally sharp. `MINIO_CONFIG_ENV_FILE` is loaded only at startup. A server can continue running with an old process environment, then fail on its next restart after the file or binary changes. Startup must fail on malformed input, but it must not invent a narrower target grammar than the configuration system.

## The file grammar {#grammar}

### Lines and comments {#lines}

- blank lines are ignored;
- a line whose first non-whitespace character is `#` is ignored;
- an optional standalone `export` followed by whitespace is removed;
- `exportFOO=value` remains the key `exportFOO`; it is not mistaken for the prefix;
- the first `=` separates key and value, so additional `=` characters remain part of the value.

The file is not a shell. It does not perform variable expansion, command substitution, backslash processing, or inline-comment interpretation.

### Keys {#keys}

Surrounding whitespace around the key is removed. The remaining key must:

1. be non-empty valid UTF-8;
2. contain only Unicode graphic characters;
3. contain no whitespace, `=`, NUL, control, or invisible format characters.

This preserves OS-compatible names and multi-target suffixes while rejecting visually empty or structurally ambiguous keys. A key beginning with a digit or punctuation is accepted by the parser; SILO still reads only the exact names used by its configuration and runtime components.

### Values and quoting {#values}

Unquoted values are trimmed. To retain leading or trailing spaces, quote the complete value with matching single or double quotes:

```dotenv
PLAIN = value
SPACED = "  value with significant spaces  "
TOKEN = scheme://user:password@example.com?a=b
EMPTY =
```

The parser removes one matching outer quote pair. It does not interpret escapes inside the quoted value. NUL is always rejected because it cannot be represented in an environment entry.

## Failure and secrecy contract {#failure}

Syntax errors stop startup. Diagnostics include the file path, line number, and the invalid key or error class, but never the value. A password on a malformed line must not be copied into logs.

Parsing is all-or-nothing: a syntax error returns no entries, and assignment starts only after the complete file has parsed. If the operating system rejects a validated assignment, SILO also stops startup and identifies the key and file. Since the process exits, it never serves requests with a partially loaded environment.

The file itself remains a privileged secret-bearing input. Operators must protect it with appropriate ownership and mode; parser validation is not a substitute for filesystem permissions.

## Regression matrix {#tests}

The committed tests cover:

- spaces and tabs around `=`;
- quoted values with significant spaces;
- standalone `export`, including Unicode whitespace after it;
- keys beginning with `_`, a digit, or punctuation;
- named targets using `-`, `.`, `:`, and Unicode;
- exact named-target discovery through the configuration subsystem;
- empty keys, whitespace, NUL, and invisible format characters;
- NUL values;
- multiple `=` characters in URLs and tokens;
- file-and-line diagnostics that redact values;
- all-or-nothing parse results.

The implementation passed the complete local server verification matrix and a read-only adversarial review. Windows-specific `os.Setenv` behavior has not been exercised on a Windows runner; unsupported platform rejection remains fail-fast rather than silent.

## Compatibility and delivery {#compatibility}

No configuration migration is required. Existing ordinary environment names behave unchanged. Files using shell-style whitespace become more predictable, and previously accepted named targets work again.

The visible compatibility changes are intentional:

- invalid or invisible names now fail instead of being silently ignored;
- unquoted surrounding value whitespace is trimmed; quote it when significant;
- malformed input stops startup with a redacted location-aware error;
- a valid punctuation-bearing target is no longer rejected merely because a shell could not assign it with `NAME=value` syntax.

This record describes a source commit, not a delivered release. Until the commit is pushed, tested remotely, merged, tagged, packaged, imaged, and deployed, operators must not assume a public SILO binary contains this parser contract.

## Conclusion {#conclusion}

Configuration compatibility depends on validating the format SILO actually consumes. `MINIO_CONFIG_ENV_FILE` borrows a small amount of dotenv-like syntax for operator convenience, but it is not executed by a shell. The repair restores named-target compatibility while retaining strict NUL, invisibility, redaction, and fail-fast guarantees.

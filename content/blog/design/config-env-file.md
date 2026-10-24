---
title: "Config Environment Files Are Not Shell Scripts"
linkTitle: "Config Env File Contract"
date: 2026-08-28
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  MINIO_CONFIG_ENV_FILE is parsed directly by SILO, not sourced by a shell. A shell-identifier check rejected valid named configuration targets such as my-hook. This note defines the key grammar, whitespace and quoting rules, failure behavior, and the #65 restart trap.
tags: [Design, Configuration, Compatibility, Operations]
weight: 16
draft: false
url: "/blog/design/config-env-file/"
---

This note defines the startup contract for `MINIO_CONFIG_ENV_FILE` and documents the compatibility repair committed as `2aea7fe9c` and shipped in [Server 20260903](/blog/release/silo-20260903/). The file is a SILO input format; supporting an optional `export` prefix for operator convenience does not make it a POSIX shell script.

## Overview {#tldr}

SILO can load startup environment variables from a file:

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

The last two keys illustrate why shell-identifier validation is too narrow. Multi-target configuration appends the target name verbatim after an underscore. The configuration subsystem does not restrict target names to POSIX shell identifiers: names containing `-`, `.`, `:`, digits, or printable Unicode can be discovered and resolved directly.

An earlier hardening change validated every environment-file key against `[A-Za-z_][A-Za-z0-9_]*`. That regex rejected `my-hook` and prevented the server from starting on restart even though the previous loader and the configuration target subsystem accepted it. The repair validates the invariants that SILO and the operating-system environment actually require:

- The key name is non-empty, valid UTF-8, and composed of visible non-whitespace characters.
- `=` and NUL are forbidden in a key name.
- NUL is forbidden in a value.
- Invalid input reports the file path and line number without logging the value.
- The entire file is parsed and validated before any environment assignment is applied.

## Why the Regression Was Real {#regression}

The environment-file loader calls `os.Setenv` after parsing. An operating-system environment block is an array of `KEY=VALUE` strings, not a POSIX shell variable namespace. Shell assignment syntax is narrower only because a shell must tokenize and expand variable references inside its own command language.

Named SILO configuration targets follow the pattern:

```text
MINIO_<SUBSYSTEM>_<PARAMETER>_<target>
```

For example:

```text
MINIO_NOTIFY_WEBHOOK_ENABLE_my-hook
MINIO_NOTIFY_WEBHOOK_ENDPOINT_my-hook
```

Target discovery enumerates environment variables by matching the fixed `MINIO_<SUBSYSTEM>_<PARAMETER>_` prefix and treats the remaining suffix verbatim as the target ID. Target lookup reconstructs the exact environment variable name without uppercasing or sanitizing that suffix. Rejecting `-` in the environment-file parser broke a valid discover-to-resolve path without protecting any shell evaluation path, because no shell ever evaluates `MINIO_CONFIG_ENV_FILE`.

The failure mode is operationally sharp because `MINIO_CONFIG_ENV_FILE` is read only at process startup. A server could continue running with its existing in-memory environment and then fail on its next restart after a binary upgrade or config reload. Startup must fail fast on malformed input, but the file parser must not enforce a narrower target grammar than the configuration subsystem itself.

## File Grammar {#grammar}

### Lines and Comments {#lines}

- Blank lines and whitespace-only lines are ignored.
- Any line whose first non-whitespace character is `#` is ignored as a comment.
- An optional standalone `export` keyword followed by whitespace is stripped before key parsing.
- `exportFOO=value` preserves the key `exportFOO`; it is not mistaken for the `export` prefix.
- The first `=` separates the key from the value; any subsequent `=` characters remain part of the value.

The file is not executed by a shell. It does not perform `$VAR` expansion, command substitution, backslash escape processing, or inline `#` comment stripping inside values.

### Keys {#keys}

Leading and trailing whitespace around the key is trimmed. The remaining key must:

1. Be non-empty valid UTF-8.
2. Contain only Unicode graphic characters (`unicode.IsGraphic`).
3. Contain no whitespace, `=`, NUL, control characters, or invisible Unicode format characters.

This grammar preserves OS-compatible variable names and multi-target suffixes while rejecting visually empty or structurally ambiguous keys. Keys beginning with a digit or punctuation character are accepted by the parser; SILO still reads only the exact configuration names used by its subsystems.

### Values and Quoting {#values}

Unquoted values have leading and trailing whitespace trimmed. To preserve significant leading or trailing spaces, wrap the entire value in matching single or double quotes:

```dotenv
PLAIN = value
SPACED = "  value with significant spaces  "
TOKEN = scheme://user:password@example.com?a=b
EMPTY =
```

The parser strips at most one matching outer quote pair and does not interpret backslash escapes inside quotes. NUL bytes are always rejected because operating-system environment entries are NUL-terminated C strings.

## Failure and Secrecy Contract {#failure}

Syntax errors abort server startup immediately. Diagnostic messages include the file path, 1-based line number, and the invalid key name or error category, but never print the value—ensuring that a secret or password on a malformed line is never copied into startup logs.

Parsing is atomic (all-or-nothing): a syntax error on any line discards all parsed entries, and `os.Setenv` calls begin only after the entire file validates. If the operating system rejects a validated `os.Setenv` call, SILO aborts startup and reports the key name and file path so the process never serves traffic with a partially applied environment.

Because `MINIO_CONFIG_ENV_FILE` carries root credentials, KMS keys, and webhook tokens, operators must still protect the file with strict filesystem ownership and permissions (`0600`).

## Regression Matrix {#tests}

The unit and configuration test suites cover:

- Spaces and tabs around `=`.
- Single- and double-quoted values with significant surrounding spaces.
- Standalone `export` prefixes, including Unicode whitespace after `export`.
- Keys beginning with `_`, a digit, or punctuation.
- Named targets containing `-`, `.`, `:`, and printable Unicode characters.
- End-to-end named-target discovery through the configuration subsystem.
- Empty keys, whitespace inside keys, NUL bytes, and invisible Unicode format characters (such as zero-width spaces).
- NUL bytes inside values.
- Multiple `=` characters in URLs, query strings, and base64 tokens.
- File-and-line diagnostics that redact secret values.
- All-or-nothing parse failure guarantees.

## Compatibility and the Warm-Restart Trap {#compatibility}

No configuration migration is required. Existing standard environment variable names behave identically, files using spaces around `=` parse predictably, and named targets with hyphens or dots work again.

Four visible behaviors are intentional:

- Invalid or invisible key names fail startup immediately instead of being silently ignored.
- Unquoted surrounding value whitespace is trimmed; quote values when leading or trailing spaces are significant.
- Malformed lines stop startup with a redacted, line-numbered diagnostic.
- Valid punctuation-bearing target names are no longer rejected merely because POSIX `sh` cannot assign them with literal `NAME=value` syntax.

The original [#65](https://github.com/pgsty/silo/issues/65) investigation also uncovered a subtle warm-restart trap: the legacy parser split on `=` without trimming key whitespace, storing `KEY = new` as the trailing-space key `KEY `. A `systemd` cold start often masked this bug because `systemd` parses `EnvironmentFile=` itself and strips spaces around `=`. However, when an operator triggered an in-place warm restart (`mcli admin service restart`), the re-executed SILO process inherited `KEY=old` from the parent environment, and the newly parsed `KEY ` entry failed to overwrite `KEY`. The server could therefore restart and continue running with stale root credentials, KMS settings, or identity provider configuration. With key trimming restored in [Server 20260903](/blog/release/silo-20260903/), `KEY = new` overwrites `KEY` on both cold start and warm restart; operators who had space-padded assignments in `MINIO_CONFIG_ENV_FILE` should verify that those values match their intended active configuration before upgrading.

## Conclusion {#conclusion}

Restoring `config.ReadEnvFile` in `silo-pkg/v3` (`1a0d788`) and updating the server (`a643483be`) aligns `MINIO_CONFIG_ENV_FILE` parsing across cold starts and warm restarts while preserving full backward compatibility with standard shell-style environment files.

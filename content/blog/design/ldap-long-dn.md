---
title: "LDAP Long DNs: Restoring Login Without Hiding Revocation Errors"
linkTitle: "LDAP Long DNs"
date: 2026-10-23
lastmod: 2026-10-26
author: "Ruohang Feng"
summary: "Why LDAP DN normalization exposed an IAM filename limit, how parent-revision reads turned it into a login regression, and why the fix classifies only impossible ASCII path components as absent."
tags: [Design, LDAP, IAM, Operations]
weight: 8
draft: false
url: "/blog/design/ldap-long-dn/"
---

**Release status:** This fix shipped in [Server 20261026](/blog/release/silo-20261026/#server-20261026). The design and validation below retain their original source scope.

[Server PR #250](https://github.com/pgsty/silo/pull/250) (merged at [`d43adc0f2`](https://github.com/pgsty/silo/commit/d43adc0f2bf1c2cfd174fbcb63bfa3ed443680b0)) fixes a login failure affecting LDAP users whose normalized Distinguished Name (DN) exceeds the 255-byte single-component filename limit of the object-storage IAM backend, while preserving read errors that protect the [durable IAM revocation boundary](/blog/design/iam-revocations/).

The initial bug report, patch ([`9faeb7a11`](https://github.com/pgsty/silo/commit/9faeb7a1147435aa7ebc02bb997837ddfbdd2a81)), and long-DN regression tests were contributed by [`@910patin`](https://github.com/910patin). During design review prior to merge, maintainers narrowed the error-classification guard to ensure that full-path length errors or unreadable multibyte records on disk can never mask an existing revocation record.

## Problem and Impact {#problem}

An enterprise LDAP user can have a long Distinguished Name (DN), especially when user names and multi-level organizational units (`ou=`) contain non-ASCII UTF-8 characters (such as Chinese or Cyrillic text). Even when a user derives all permissions from LDAP group memberships and has no directly attached user policy or local parent-identity record, SILO's login flow still probes those optional IAM records.

On the object-storage IAM backend, the normalized DN is embedded directly as a directory or filename component. When that component exceeds 255 bytes, the filesystem returns a filename-length error (`ENAMETOOLONG` / `ObjectNameInvalid`) that aborts an otherwise valid LDAP login, STS token request, or service-account lookup.

## Why DN Normalization Triples Non-ASCII Byte Length {#normalization}

An LDAP DN identifies a full directory entry (for example, `cn=张三,ou=研发,dc=example,dc=com`). Under [RFC 4514 §2.4](https://www.rfc-editor.org/rfc/rfc4514.html#section-2.4), syntax characters must be escaped, and arbitrary bytes may be escaped using `\xx` (a backslash followed by two hexadecimal digits per byte). While RFC 4514 allows UTF-8 text to remain literal, the upstream `go-ldap` library's `DN.String()` serializer hex-escapes every non-ASCII UTF-8 byte.

SILO's `NormalizeDN` parses the DN returned by the LDAP server and formats it via `DN.String()` so attribute-type names and escape sequences have a canonical string representation:

| Representation | Byte Length |
| :--- | ---: |
| Single UTF-8 character `张` | 3 bytes |
| Serialized by `DN.String()` as `\e5\bc\a0` | 9 ASCII bytes |
| `cn=` + 40 copies of `张` + `,dc=example,dc=com` (raw UTF-8) | 141 bytes |
| The same complete DN after `NormalizeDN` | 381 ASCII bytes |

Because each 3-byte UTF-8 character expands into 9 ASCII characters (`\xx\xx\xx`), a 141-byte UTF-8 DN expands to 381 ASCII bytes on disk.

This lookup-result normalization was introduced upstream on March 27, 2024 in [`minio/pkg efb73fa5`](https://github.com/minio/pkg/commit/efb73fa5d52fc1f217c58d51544f448e3862ab61) ([MinIO PR #19358](https://github.com/minio/minio/pull/19358), by Aditya Manthramurthy / `@donatello`) so that the server uses the authoritative DN returned by the LDAP directory rather than trusting the user's raw login input spelling (for example, when a user inputs a Unicode fullwidth period that the directory resolves to an ASCII period).

## How the Login Regression Arose {#cause}

The object-storage IAM backend stores per-user records at paths constructed from the normalized DN:

```text
config/iam/users/<normalized-DN>/identity.json
config/iam/policydb/sts-users/<normalized-DN>.json
```

POSIX filesystems enforce a 255-byte limit on each individual `/`‑delimited path component (`NAME_MAX`). When the normalized DN is used as the filename in `sts-users/<normalized-DN>.json`, the 5-byte `.json` suffix shares the same component budget: a 250-byte escaped DN (`250 + 5 = 255`) fits, whereas a 251-byte escaped DN (`251 + 5 = 256`) fails with `ENAMETOOLONG`.

Two historical behaviors shaped how this failure surfaced:

1. **Unix backslash omission in `checkPathLength`**: SILO's pre-flight `checkPathLength` helper does not count backslash (`\`) characters on Unix. In reproduction testing, a 271-byte hex-escaped DN was counted as 197 bytes by `checkPathLength`, bypassing pre-flight validation and failing only when the OS filesystem attempted the lookup.
2. **Ancestor directory existence sensitivity**: When the parent prefix directory (`config/iam/users/`) did not exist yet on disk, the kernel returned `ENOENT` while resolving the missing parent directory—before reaching the overlong `<normalized-DN>` component—allowing login to succeed (`HTTP 200`). Once any user record created the `config/iam/users/` prefix directory, the kernel reached the 271-byte component and returned `ENAMETOOLONG`, causing login to fail with `HTTP 500`.

| Commit | Role in the Failure Chain |
| :--- | :--- |
| MinIO [`ee9077db`](https://github.com/minio/minio/commit/ee9077db7d5f23de17cedbb6d7e7c99b1638ad6e) (May 2020) | Introduced Unix backslash skipping in `checkPathLength`. |
| MinIO [`280526ca`](https://github.com/minio/minio/commit/280526caf7e41881f7cd9a3c97028e1f56df41ef) (Mar 2024) | Propagated policy lookup read errors after a cache miss instead of swallowing them. |
| MinIO [`efb73fa5`](https://github.com/minio/pkg/commit/efb73fa5d52fc1f217c58d51544f448e3862ab61) & [`7e45d84a`](https://github.com/minio/minio/commit/7e45d84acebf9eac5391ec7676c4a7f92e52fd75) (Mar 2024) | Adopted `NormalizeDN` (with `\xx` hex expansion) for LDAP identity and policy-mapping keys. |
| SILO [`709d50a9`](https://github.com/pgsty/silo/commit/709d50a916bf3311eda2b3882ac5f2a0251f4223) (Server 20260916) | Added persistent parent-revision reads (`config/iam/users/<DN>/identity.json`) during login for revocation and replay protection, triggering the read on every LDAP login even when the policy cache hit. |

## The Fix: Narrowly Classify Impossible ASCII Components as Absent {#decision}

The fix is implemented in the shared object-storage IAM reader, [`loadIAMConfigBytesWithMetadata`](https://github.com/pgsty/silo/blob/d43adc0f2bf1c2cfd174fbcb63bfa3ed443680b0/cmd/iam-object-store.go#L137). It attempts the normal storage read first. Only if the read fails does it translate the error to `errConfigNotFound`, and **only when all three conditions hold**:

1. The returned error is `errFileNameTooLong` or `ObjectNameInvalid` (including wrapped errors).
2. The complete object key passes standard bucket and object-name validation (`isValidBucketName` and `isValidObjectName`).
3. At least one `/`-delimited path component consists entirely of ASCII characters (`utf8.RuneCountInString(component) == len(component)`) and exceeds 255 bytes (`len(component) > 255`).

Because a pure-ASCII path component longer than 255 bytes can never be written to the object-storage IAM backend in the first place, no persisted user policy or parent-revision record can exist at that key. Returning `errConfigNotFound` allows the caller to follow its normal record-absent path—for example, authenticating the LDAP user and evaluating permissions strictly from their LDAP group policies—without granting any default permissions or bypassing revocation checks for storable keys.

Writes, deletes, the `etcd` IAM backend, and global object path validation remain unchanged. The production change adds 25 lines in `cmd/iam-object-store.go` accompanied by 318 lines of regression tests, with zero extra I/O on normal reads.

## Why the Initial Error Classification Required Narrowing {#safety}

The initial patch treated any `ObjectNameInvalid` / `errFileNameTooLong` error on a syntactically valid key as `errConfigNotFound`. Design review identified two concrete counterexamples where a length error does **not** prove that the record never existed on disk:

1. **Full-path length overflow (`PATH_MAX`) hiding an existing revocation**: Suppose an administrator revokes an identity whose individual path components are $\le 255$ bytes (so the revocation tombstone is successfully written to disk), and the server's data directory is later mounted or moved under a deeper parent path on macOS. A read can then fail due to the total path length limit even though the revocation record exists on disk. Treating that error as `errConfigNotFound` would hide the revocation tombstone and allow a revoked parent identity to pass verification. Checking `len(component) > 255` on individual `/`-delimited components ensures full-path overflow errors still fail closed.
2. **Multibyte UTF-8 filenames on character-counted filesystems (macOS APFS/HFS+)**: On macOS, filesystem component limits are enforced in UTF-16 code units / characters (up to 255 characters) rather than raw UTF-8 bytes. In filesystem boundary testing on macOS, a single component consisting of 100 copies of `界` occupies **300 UTF-8 bytes** (`len(component) == 300`, `RuneCount == 100`) and **can** be created and persisted on disk. If the guard checked only `len(component) > 255`, an existing 300-byte Unicode record could be misclassified as impossible. Requiring `utf8.RuneCountInString(component) == len(component)` restricts the absence classification to pure-ASCII components (which includes all `\xx`-escaped DNs), where 1 character is always 1 byte on every platform.

The resulting safety invariant is exact: **only a path component that is provably uncreatable may take the `errConfigNotFound` branch; any potentially existing record that cannot be read must fail closed.**

## Alternatives Considered {#alternatives}

| Candidate Approach | Decision and Rationale |
| :--- | :--- |
| **Narrow ASCII component (> 255 B) classification in `loadIAMConfigBytesWithMetadata`** | **Selected.** Restores LDAP login and STS lookup across all callers using the shared IAM reader while failing closed on full-path errors and storable Unicode names. |
| **Treat every `ObjectNameInvalid` on a valid key as `errConfigNotFound`** | **Rejected.** Full-path (`PATH_MAX`) errors on deep mount points could hide an existing revocation tombstone on disk. |
| **Count decoded UTF-8 characters or ignore `\xx` escape overhead** | **Rejected.** The OS filesystem stores the literal `\xx`-expanded ASCII string, not the unescaped UTF-8 runes. |
| **Fix only Unix backslash counting in `checkPathLength`** | **Insufficient.** Counting backslashes in `checkPathLength` would merely reject the same long DN earlier (with `ObjectNameInvalid`) without restoring login. |
| **Change `NormalizeDN` to preserve raw UTF-8 instead of `\xx` hex escapes** | **Deferred.** Would incompatibly alter existing persisted LDAP identity and policy-mapping keys on disk, and still would not eliminate component limits for genuinely long DNs. |
| **Skip parent-revision checks for LDAP or revert `709d50a9`** | **Rejected.** Would sacrifice durable revocation and replay protection while leaving the older March 2024 policy-mapping read failure (`sts-users/<DN>.json`) unfixed. |
| **Hash overlong DNs into fixed-length storage keys** | **Separate feature scope.** Full write support for arbitrary-length DNs requires a new storage schema across lookup, listing, import/export, site replication, and mixed-version upgrades. |

## Verification Matrix {#verification}

| Test Suite / Probe | Coverage and Results |
| :--- | :--- |
| **Unit & boundary tests** ([`cmd/iam-revision_test.go`](https://github.com/pgsty/silo/blob/d43adc0f2bf1c2cfd174fbcb63bfa3ed443680b0/cmd/iam-revision_test.go#L103)) | Covers escaped 271-byte and 384-byte DNs, exact 255/256-byte component boundaries, `.json` suffix accounting, multibyte Unicode components, wrapped errors, invalid object names, and existing revocation records moved under deep directory paths. |
| **End-to-end LDAP STS login** ([`cmd/sts-handlers_test.go`](https://github.com/pgsty/silo/blob/d43adc0f2bf1c2cfd174fbcb63bfa3ed443680b0/cmd/sts-handlers_test.go#L3300)) | Verifies STS login, signed S3 access, and service-account operations for a group-authorized user with a 384-byte normalized DN across 8 object/etcd configurations. |
| **Cross-platform filesystem probes** | Tested 72 physical filename shapes on macOS (49 creatable) and Linux `tmpfs` (32 creatable): zero storable filenames were classified as impossible. Verified 105 error-propagation assertions (5 parent-name classes $\times$ 7 storage errors $\times$ 3 entry points) per platform. |
| **CI & Toolchain VulnCheck** | All 11 PR CI jobs on [`3df51549bbbd6e57a6a5f11ac77535390517db65`](https://github.com/pgsty/silo/commit/3df51549bbbd6e57a6a5f11ac77535390517db65) (merged as [`a07d655dc69cf04b130c2634d9fa5301078af546`](https://github.com/pgsty/silo/commit/a07d655dc69cf04b130c2634d9fa5301078af546)) and 7 post-merge `main` jobs passed on [`d43adc0f2`](https://github.com/pgsty/silo/commit/d43adc0f2bf1c2cfd174fbcb63bfa3ed443680b0) ([Go CI](https://github.com/pgsty/silo/actions/runs/39894613094), [VulnCheck](https://github.com/pgsty/silo/actions/runs/39894613091)), alongside raising the minimum toolchain to Go 1.27.3 for `GO-2026-6809`. |

## Operational Boundaries and Guidance {#limits}

- **Read vs. Write asymmetry**: This fix restores **read/login** paths when optional per-user IAM records do not exist. It does **not** enable the object-storage IAM backend to **write** files whose component length exceeds 255 bytes. Attaching a policy directly to a >250-byte normalized user DN (`sts-users/<DN>.json`) or writing a persistent parent-revision tombstone (`users/<DN>/identity.json`) on the object backend will still fail with a filename-length error.
- **Recommended LDAP authorization pattern**: For LDAP users with long or non-ASCII DNs on object-backed IAM deployments, grant permissions through **LDAP group mappings** (where the group DN itself fits within 250 ASCII bytes after normalization) rather than direct per-user policy attachments.
- **No migration required**: Upgrading requires no on-disk data migration. Never delete `.minio.sys/config/iam/` directories manually to work around path-length errors; follow the standard [IAM upgrade and recovery guide](/operations/replication/iam-upgrade/).

---
title: "LDAP Long DNs: Restoring Login Without Hiding Revocation Errors"
linkTitle: "LDAP Long DNs"
date: 2026-10-23
lastmod: 2026-10-23
author: "Ruohang Feng"
summary: "Why LDAP DN normalization exposed an IAM filename limit, how a parent-revision read turned it into a login regression, and why the repair narrowly classifies impossible records as absent."
tags: [Design, LDAP, IAM, Operations]
weight: 8
draft: false
url: "/blog/design/ldap-long-dn/"
---

**Decision, 2026-10-23:** [Server PR #250](https://github.com/pgsty/silo/pull/250)
is merged at [`d43adc0f2`](https://github.com/pgsty/silo/commit/d43adc0f2bf1c2cfd174fbcb63bfa3ed443680b0).
The repair restores the tested long-DN LDAP login paths while preserving errors
that could hide an existing IAM revocation. This is a source acceptance record;
it does not announce a Server release, image, package or production deployment.

The original report, patch and long-DN regression tests came from
[@910patin](https://github.com/910patin). Their original
[`9faeb7a11`](https://github.com/pgsty/silo/commit/9faeb7a1147435aa7ebc02bb997837ddfbdd2a81)
commit remains in main. The maintainer follow-up narrowed the error classification
and added counterexamples before merging the original PR.

## Problem and significance {#problem}

A valid LDAP account can have a long distinguished name (DN), particularly when
its name and organizational units contain non-ASCII text. A group-authorized
user may need no directly attached user policy and no local parent-identity
record. Nevertheless, login reads those optional records. In the failing path,
the normalized DN becomes a directory or filename component that the object
backend cannot store. A name-length error then aborts an otherwise valid login.

This is not an LDAP rejection of the account's name or password. It is a mismatch
between an external identity and SILO's internal storage key. The same class of
failure can affect STS issuance, service-account creation and credential loading.
The repair matters because restoring availability must not weaken the
[durable IAM revocation boundary](/blog/design/iam-revocations/).

## Why the name becomes longer {#normalization}

A DN identifies an entire directory entry, for example
`cn=张三,ou=研发,dc=example,dc=com`; it is not merely a login name.
The escape notation is **`\xx`**, a backslash followed by two hexadecimal digits
for one byte. It is neither a hyphen notation nor one escape per Unicode character.

[RFC 4514 §2.4](https://www.rfc-editor.org/rfc/rfc4514.html#section-2.4)
requires escaping certain syntax characters and permits escaping others.
Ordinary UTF-8 text can remain literal. The RFC does not require all non-ASCII
characters to be escaped and does not define a unique canonical DN string.

The `go-ldap` library's `DN.String()` chooses to hex-escape non-ASCII UTF-8 bytes.
SILO's `NormalizeDN` parses the DN and uses that serializer. Attribute-type names
and escape spellings become consistent; this is the library's representation,
not a claim that every LDAP equality rule is reducible to string equality.

| Representation | Bytes |
| --- | ---: |
| `张` in UTF-8 | 3 |
| The serialized value `\e5\bc\a0` | 9 |
| `cn=` + 40 copies of `张` + `,dc=example,dc=com` | 141 before serialization |
| The same complete DN after serialization | 381 |

The last two values were checked with the dependency used for acceptance.
The account remains the same; only its representation expands. When that text
is used as a filename, the filesystem sees the expanded bytes. Counting the
decoded Chinese characters cannot make the actual filename fit.

MinIO introduced lookup-result normalization on March 27, 2024 in
[`minio/pkg efb73fa5`](https://github.com/minio/pkg/commit/efb73fa5d52fc1f217c58d51544f448e3862ab61),
authored by Aditya Manthramurthy (@donatello). The related
[MinIO PR #19358](https://github.com/minio/minio/pull/19358) explains the identity
consistency requirement: use the DN returned by the LDAP server instead of
assuming the user's input spelling is the authoritative identity. Its example
uses a Unicode variant of a full stop that the directory resolves to an ordinary
full stop. SILO inherited this normalization path; September's revocation work
did not introduce the escaping.

## How the login regression arose {#cause}

The object IAM backend uses paths such as:

```text
config/iam/users/<normalized-DN>/identity.json
config/iam/policydb/sts-users/<normalized-DN>.json
```

The relevant limit is a **single path component**, not the total DN's character
count. For a DN occupying one component, the mapping's `.json` suffix also counts:
250 ASCII bytes plus the suffix fit 255 bytes; 251 plus the suffix do not.

Two inherited behaviors complicate the symptom. First, `checkPathLength` does
not count backslashes on Unix. A 271-byte escaped DN in the reproduction is
counted as 197, so it passes that check and can fail later in the filesystem.
Second, a missing ancestor directory can produce a missing-file result before
the filesystem reaches the overlong component. Whether an IAM prefix already
exists can therefore change the result. The directory state was part of the
reproduction, not a recommended workaround.

| Change | Contribution to the failure |
| --- | --- |
| MinIO [`ee9077db`](https://github.com/minio/minio/commit/ee9077db7d5f23de17cedbb6d7e7c99b1638ad6e), May 2020 | Introduced the Unix backslash-counting behavior in the path-length precheck. |
| MinIO [`280526ca`](https://github.com/minio/minio/commit/280526caf7e41881f7cd9a3c97028e1f56df41ef), March 2024 | Propagated policy lookup read errors after a cache miss, providing an older failure path. |
| MinIO normalization and [`7e45d84a`](https://github.com/minio/minio/commit/7e45d84acebf9eac5391ec7676c4a7f92e52fd75), March 2024 | Made normalized, potentially expanded DNs the identity/mapping representation. |
| SILO [`709d50a9`](https://github.com/pgsty/silo/commit/709d50a916bf3311eda2b3882ac5f2a0251f4223), shipped in Server 20260916 | Added persistent parent-revision reads for revocation and replay protection, exposing another required read during login. |

The reproduced 271-byte case returned HTTP 200 when the users prefix was absent
and HTTP 500 when it existed on the unfixed implementation. The repaired path
returned HTTP 200 in both states and supported the tested S3 and service-account
operations. A 384-byte DN also exercised the earlier policy-read path.

These are distinct causes with different histories. The September change
introduced the parent-read regression, but reverting to an earlier release does
not establish support for every long DN. Historical attribution was checked
against source and release ancestry; historical release binaries were not run.

## Decision: narrowly classify an impossible record as absent {#decision}

The repair is in the shared object IAM reader,
[`loadIAMConfigBytesWithMetadata`](https://github.com/pgsty/silo/blob/d43adc0f2bf1c2cfd174fbcb63bfa3ed443680b0/cmd/iam-object-store.go#L137).
It attempts the normal read first. Only after a failure does it classify the
lookup as `errConfigNotFound`, and only when **all three** conditions hold:

1. The error is `errFileNameTooLong` or `ObjectNameInvalid`, including recognized wrappers.
2. The complete object key passes the normal bucket/object-name validation.
3. At least one slash-delimited component is entirely ASCII and exceeds 255 bytes.

The implementation checks both `len(component) > 255` and
`utf8.RuneCountInString(component) == len(component)`. The second condition only
establishes that the component is ASCII. **It does not decode `\xx`, count the
original user's characters, or relax the filesystem limit.** Normalized escaped
DNs meet the ASCII condition, and checking the complete key includes suffixes.

For that narrow case, a record cannot have been persisted at the requested
component. The existing caller can handle absence: for example, continue with
group-derived policy instead of requiring a user-specific policy file. LDAP
authentication and authorization still run. This adds no default grant and does
not skip parent-revision checks.

Successful reads retain their existing decryption, parsing and index behavior.
Other errors still propagate. Writes, deletes, the etcd backend and the global
path-length checker are unchanged. The production change adds 25 lines, with
318 lines of regression coverage in the final PR. It adds no storage format,
migration, configuration switch, background task or extra I/O; the additional
name scan occurs only after a failed read and is linear in the path length.

## Why the original classification needed a guard {#safety}

The original PR classified `ObjectNameInvalid` on a syntactically valid key as
absence. That is too broad: a length error does not always prove that a record
could never have existed.

One counterexample writes a real revocation record, then moves the data directory
under a deeper path on macOS. Its individual key components still fit, and a
relative-path read proves that the stored record remains present. The full-path
limit now prevents the usual read. Treating that failure as absence can hide the
revocation and let a parent check succeed. The final guard preserves the error.

Checking only the UTF-8 byte length is also too broad across filesystems. In the
macOS probe, a component containing 100 copies of `界` occupies 300 UTF-8 bytes
yet can be stored. Such an existing record must not be classified as impossible
merely because its byte count exceeds 255. The ASCII restriction avoids making
that inference for Unicode filenames.

The safety rule is therefore precise: **proved absence may use the existing
absence path; an unreadable, potentially existing revocation must remain an
error.** This is why the patch restores login without generally ignoring IAM
storage failures.

## Alternatives considered {#alternatives}

| Approach | Decision and reason |
| --- | --- |
| Narrow classification in the shared object IAM reader | Selected. Covers the relevant callers and preserves genuine failure handling without changing stored keys. |
| Treat every valid-key name error as absence | Rejected. A full-path limit can hide a record that already exists. |
| Count decoded characters or exclude escape overhead | Rejected. The expanded filename is what the filesystem must store. |
| Fix only the global backslash counter | Insufficient for this repair. It would reject the same name earlier and affect ordinary object paths without restoring login. |
| Preserve literal UTF-8 instead of the current serializer output | Deferred. It may shorten some names, but changes established identity/mapping keys and does not remove component limits. |
| Skip parent checks or revert durable revocation | Rejected. It would trade availability for lost revocation and replay protection, while retaining older policy-read failures. |
| Use a short or hashed storage key and keep the full DN in the record | A separate design if full long-identity persistence is needed. It requires lookup, listing, migration, import/export, replication and mixed-version rules. |

Deleting IAM directories to obtain a missing-file result is not a repair. It
destroys state and relies on an incidental lookup order.

## Verification and delivery {#verification}

Acceptance separated source behavior, CI, merge state and deployment:

| Evidence | Result and scope |
| --- | --- |
| [Committed name/revision tests](https://github.com/pgsty/silo/blob/d43adc0f2bf1c2cfd174fbcb63bfa3ed443680b0/cmd/iam-revision_test.go#L103) | Cover escaped 271/384-byte names, 255/256-byte boundaries, `.json` suffixes, Unicode, wrapped errors, invalid names, backend behavior and real records under deep paths. |
| [Committed LDAP scenario](https://github.com/pgsty/silo/blob/d43adc0f2bf1c2cfd174fbcb63bfa3ed443680b0/cmd/sts-handlers_test.go#L3300) | A group-authorized 384-byte normalized DN; the LDAP suite passed across eight object/etcd configurations. |
| Additional isolated adversarial probes | 72 physical filename cases per platform: macOS could create 49; Linux tmpfs could create 32. None of the storable names was classified as impossible. Five parent-name classes × seven storage errors × three entry points gave 105 error-propagation assertions per platform. |
| Post-merge local regression | 62 top-level tests passed, none failed; four tests requiring external OpenID services were skipped. IAM, LDAP, object/etcd revocation and the adversarial probes were included. Build and repository verifiers passed; the optional `typos` tool was unavailable and skipped. |
| [PR Go CI](https://github.com/pgsty/silo/actions/runs/39893124621), [DCO](https://github.com/pgsty/silo/actions/runs/39893124584), [VulnCheck](https://github.com/pgsty/silo/actions/runs/39893124615), [release-pipeline validation](https://github.com/pgsty/silo/actions/runs/39893124499) | All 11 jobs passed on final PR head `3df51549bbbd6e57a6a5f11ac77535390517db65` before merge. The release-pipeline check did not publish a release. |
| [Merged-main Go CI](https://github.com/pgsty/silo/actions/runs/39894613094) and [VulnCheck](https://github.com/pgsty/silo/actions/runs/39894613091) | All seven jobs passed on merge commit `d43adc0f2bf1c2cfd174fbcb63bfa3ed443680b0`. |

The post-merge local run used integration commit
`a07d655dc69cf04b130c2634d9fa5301078af546`
in the maintainer's checkout; the three changed implementation/test files were
byte-identical to the merged PR. That local integration also retained pre-existing
dependency/documentation work, so its broader environment is not presented as
the remote main snapshot. The authoritative public source and CI links above
refer to the remote merge commit.

CI also found a separate Go 1.27.2 certificate-verification vulnerability,
`GO-2026-6809`. A distinct follow-up raised the minimum to Go 1.27.3 and passed
VulnCheck. This was a merge prerequisite, not the cause of the LDAP failure.

The temporary probes supplemented committed regression tests; they are not a
new product interface. Production AD/XFS, Windows execution and a deployed
multi-node cluster were not acceptance targets here. Those environments need
their own artifact and deployment checks.

## Remaining boundary and operating guidance {#limits}

This decision restores the verified login/read paths. It does **not** make the
object backend capable of writing arbitrary-length identity records. Direct
policy mappings and parent-revision records with overlong components still fail
to save. Do not infer support for a parent-wide revocation operation that requires
such a write. The existing per-access-key/token mechanisms are separate; follow
their documented scope and verify rejection at the relevant endpoints.

For affected deployments, use group-based authorization where the group mapping
itself fits, and deploy a Server artifact verified to contain the merge. Before
acceptance, check an affected user's STS login and signed S3 access, service-account
behavior, and old-credential rejection for identities whose revocation records
can be stored. Do not delete IAM metadata or disable revocation checks as a
workaround. No data migration is introduced by this patch, and existing
[upgrade/recovery requirements](/operations/replication/iam-upgrade/) still apply.

The design lesson is to keep external identity syntax separate from internal
storage naming. When a storage constraint leaks into authentication, the repair
must establish what an error proves before changing its meaning. Here, the
smallest sufficient change was a narrowly justified absence classification;
full long-DN persistence remains a different problem.

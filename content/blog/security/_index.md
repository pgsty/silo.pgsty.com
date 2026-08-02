---
title: SILO Security Chronicle
linkTitle: Security Chronicle
description: A chronological account of every application-level CVE investigated by the SILO fork, one incident per article.
weight: 30
icon: fa-solid fa-shield-halved
sidebar_expanded: true
module: [BLOG]
default_featured_image: /images/blog/security.webp
aliases:
  - /security/
---

This is the security chronicle of the SILO community fork. It follows the incidents in the order they were investigated and fixed. Each CVE has its own article: the original threat model, the turns taken during review, the rejected alternatives, the final invariant, the evidence, and the compatibility cost all stay with that incident.

## Chronicle {#chronicle}

| Date       | CVE            | Incident                                                                           | First containing release                 |
|:-----------|:---------------|:-----------------------------------------------------------------------------------|:-----------------------------------------|
| 2026-04-15 | CVE-2026-32285 | [The `jsonparser` advisory that required no patch](/blog/security/cve-2026-32285/) | Already fixed in the dependency graph    |
| 2026-04-15 | CVE-2026-33322 | [OIDC JWT algorithm confusion](/blog/security/cve-2026-33322/)                     | SILO 2026-04-17                          |
| 2026-04-15 | CVE-2026-33419 | [LDAP STS enumeration and throttling](/blog/security/cve-2026-33419/)              | SILO 2026-04-17; completed in 2026-06-18 |
| 2026-04-15 | CVE-2026-34204 | [Replication metadata injection](/blog/security/cve-2026-34204/)                   | SILO 2026-04-17                          |
| 2026-04-15 | CVE-2026-39414 | [Oversized records in S3 Select](/blog/security/cve-2026-39414/)                   | SILO 2026-04-17; completed in 2026-06-18 |
| 2026-04-16 | CVE-2026-40344 | [Snowball auto-extract authentication bypass](/blog/security/cve-2026-40344/)      | SILO 2026-04-17                          |
| 2026-04-16 | CVE-2026-41145 | [Unsigned-trailer query authentication bypass](/blog/security/cve-2026-41145/)     | SILO 2026-04-17                          |
| 2026-06-12 | CVE-2026-42600 | [`ReadMultiple` storage-REST path traversal](/blog/security/cve-2026-42600/)       | SILO 2026-06-18                          |

The articles below are ordered chronologically; incidents investigated on the same day are ordered by CVE number. Dependency-only CVEs remain in the relevant [release notes](/blog/release/) instead of being inflated into application-level incident stories.

----------------
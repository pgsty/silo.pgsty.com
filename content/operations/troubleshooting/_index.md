---
title: "Troubleshooting"
url: "/operations/troubleshooting/"
weight: 100
icon: fa-solid fa-screwdriver-wrench
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/troubleshooting.rst
upstream_modified: true
---

<a id="troubleshooting"></a>

## Overview {#overview}

<a id="public-slack-channel"></a>

Report reproducible SILO problems to the [SILO issue tracker](https://github.com/pgsty/silo/issues). Include the Server and client versions, topology, relevant configuration with secrets removed, error messages, and a minimal reproduction. Report suspected vulnerabilities through the [private security process](/about/security/).

SILO is independently maintained by PGSTY. MinIO SUBNET subscriptions and the former upstream Slack channel are not SILO support channels. Community assistance has no guaranteed response time or recovery SLA.

## Tools {#tools}

The maintained client is distributed as `mcli`; inherited references also use the compatible command name `mc`.

- [`mcli admin info`](/reference/minio-mc-admin/mc-admin-info/) shows deployment information.
- [`mcli admin trace`](/reference/minio-mc-admin/mc-admin-trace/) follows API requests.
- [`mcli admin logs`](/reference/minio-mc-admin/mc-admin-logs/) streams server logs.
- [`mcli support diag`](/reference/minio-mc/mc-support-diag/), [`profile`](/reference/minio-mc/mc-support-profile/), and [`inspect`](/reference/minio-mc/mc-support-inspect/) collect local diagnostics without SUBNET registration or automatic upload.

Inspect diagnostic files before sharing them. They may contain topology, configuration, metadata, or raw object content. See [Encrypting Files](/operations/troubleshooting/encrypting-files/).

## Upgrades and Version Support {#upgrades-and-version-support}

Use [published releases](/download/) and read the intervening [release notes](/blog/release/) and [security advisories](/about/security-advisories/). A source change or a planned release date does not establish public artifact availability.

### Choosing an Upgrade {#recommended-upgrade-schedule}

Prioritize fixes that affect your deployment and test the exact upgrade, workload, and recovery procedure before production. SILO does not promise the inherited upstream six-month support window. Follow the [coordinated upgrade procedure](/operations/deployments/baremetal-upgrade-minio-deployment/); in-place `mcli admin update` and client `mcli update` are disabled for the maintained stack.

### Version Alignment {#version-alignment}

The supported product combination is SILO Server, SILO Console, PGSTY mcli, and `silo-pkg`. KES is an optional, independently released service. Check the [component matrix](/compatibility/versions/) for the selected versions; do not infer compatibility solely from matching release dates. Compatibility with unmodified upstream MinIO/MC is best effort.

The retained [MinIO Operator guides](/operations/deployments/kubernetes/) use the archived `v7.1.1` snapshot. Validate that combination on your Kubernetes platform and pin the SILO image explicitly. Updating the Operator does not upgrade existing Tenant server images.

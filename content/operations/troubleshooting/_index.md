---
title: "Troubleshooting"
url: "/operations/troubleshooting/"
weight: 100
icon: fa-solid fa-screwdriver-wrench
minio_origin: true
silo_modified: false
---

<a id="troubleshooting"></a>

## Overview {#overview}

MinIO users have two options for support.

1. Community support from the [public Slack channel](https://slack.min.io)<a id="public-slack-channel"></a>.

   Community support is best-effort only and has no <abbr title="Service Level Agreement">SLA</abbr> or <abbr title="Service Level Objective">SLO</abbr>.
2. Paid subscribers have access to the MinIO Subscription Network, [SUBNET](https://min.io/pricing?jmp=docs), which provides access to health checks, direct-to-engineering support, and license management.

   For current licensing levels and pricing, refer to the [MinIO SUBNET](https://min.io/pricing?jmp=docs) page.

## Tools {#tools}

The [MinIO Client](/reference/minio-mc/#minio-client) provides several functions to display information about your MinIO deployment or monitor its activity.

- For basic information about your MinIO deployment, use [`mc admin info`](/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info).
- For deeper investigation of S3 calls and responses, use [`mc admin trace`](/reference/minio-mc-admin/mc-admin-trace/#command-mc.admin.trace).
- Use [`mc admin logs`](/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs) to display logs from the command line. The command supports type and quantity filters for further limiting logs output.

## Upgrades and version support {#upgrades-and-version-support}

MinIO regularly releases updates to introduce features, improve performance, address security concerns, or fix bugs. These releases can occur very frequently, and vary by product.

Always test software releases in a development environment before upgrading on a production deployment.

### Recommended upgrade schedule {#recommended-upgrade-schedule}

MinIO recommends always installing the most recent release to obtain security enhancements and improvements. We recognize that such a frequent release schedule may make this impractical for some organizations. In such cases, we recommend using MinIO and our related product releases that are no older than six months.

### Version Alignment {#version-alignment}

As the various MinIO products release separately on their own schedules, we recommend the following version alignment practices:

**MinIO**

> Update to the latest release or a release no older than six months.

**MinIO Client**

> Update to the *mc* release that occurs immediately after the MinIO release, within one or two weeks.

**MinIO Operator**

> Use a MinIO version no earlier than the latest at the time of the Operator release. The MinIO version latest at time of release can be found in the quay.io link in the example tenant kustomization yaml file for the Operator release.
>
> - 4.5.5: MinIO RELEASE.2022-12-07T00-56-37Z or later
> - 4.5.6: MinIO RELEASE.2023-01-02T09-40-09Z or later
> - 4.5.7: MinIO RELEASE.2023-01-12T02-06-16Z or later
> - 4.5.8: MinIO RELEASE.2023-01-12T02-06-16Z or later
>
> When creating a new tenant, the Operator uses either the latest available MinIO release image or the image you specify when creating the tenant.
>
> [Upgrading the Operator](/operations/deployments/k8s-upgrade-minio-operator-kubernetes/#minio-k8s-upgrade-minio-operator) does **not** automatically upgrade existing tenants. [Upgrade existing tenant](/operations/deployments/k8s-upgrade-minio-tenant-on-kubernetes/#minio-k8s-upgrade-minio-tenant) MinIO versions separately.

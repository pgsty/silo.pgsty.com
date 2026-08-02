---
title: "mc admin replicate"
url: "/reference/minio-mc-admin/mc-admin-replicate/"
weight: 140
minio_origin: true
silo_modified: false
---

<a id="mc-admin-replicate"></a>
<a id="minio-mc-admin-replicate"></a>

<a id="command-mc.admin.replicate"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2023-01-11T03-14-16Z**

- `mc admin replicate edit` renamed to [`mc admin replicate update`](#mc.admin.replicate.update)
- `mc admin replicate remove` renamed to [`mc admin replicate rm`](#mc.admin.replicate.rm)
{{% /alert %}}

## Description {#description}

The [`mc admin replicate`](#command-mc.admin.replicate) command creates and manages [site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview) for a set of MinIO peer sites.

Site replication mimics an active-active bucket replication, but for multiple MinIO deployments. Wherever a change occurs to IAM settings, buckets, or objects across the set of sites, the change replicates across all sites in the site replication group.

Where [bucket replication](/administration/bucket-replication/#minio-bucket-replication) manages the mirroring of particular buckets or objects from one location to another within a deployment or across deployments, site replication continuously mirrors an entire MinIO site to other sites.

[`mc admin replicate`](#command-mc.admin.replicate) only supports site replication for [distributed deployments](/operations/deployments/installation/#deploy-minio-distributed) when configuring site replication.

Only one deployment can have any data when initiating a new site replication configuration.

Site replication enforces [bucket versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) on all buckets, including existing buckets and any buckets added after initiating site replication. Site replication fully synchronizes versioned objects, compared to [`mc mirror`](/reference/minio-mc/mc-mirror/#command-mc.mirror) which operates only on the latest version of an object

{{% alert color="info" %}}
**Use `mc admin` on MinIO Deployments Only**

MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.
{{% /alert %}}

The [`mc admin replicate`](#command-mc.admin.replicate) command has the following subcommands:

| Subcommand | Description |
| --- | --- |
| [`mc admin replicate add`](#mc.admin.replicate.add) | Create a new site replication configuration or expand an existing configuration. |
| [`mc admin replicate info`](#mc.admin.replicate.info) | Returns information about site replication configuration. |
| [`mc admin replicate resync`](#mc.admin.replicate.resync) | Resynchronizes content from one site to a second site if the second site has lost data. |
| [`mc admin replicate rm`](#mc.admin.replicate.rm) | Removes an entire site replication configuration or one or more peer sites from participating in site replication. |
| [`mc admin replicate status`](#mc.admin.replicate.status) | Displays the status for [replicable data](/operations/replication/multi-site-replication/#minio-site-replication-what-replicates) across participating sites. |
| [`mc admin replicate update`](#mc.admin.replicate.update) | Modify the endpoint of the specified peer site in the site replication configuration. |

## Syntax {#syntax}

#### `mc admin replicate add` {#mc.admin.replicate.add}

*mc-cmd*

Create or expand a site replication configuration. The configuration uses asynchronous site replication by default, as MinIO recommends.

To enable synchronous site replication, create the replication using this command *first*. Then use [`mc admin replicate update --mode sync`](#mc.admin.replicate.update.-mode) to update the configuration.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLES" %}}
Consider a multi-site MinIO topology with three separate MinIO deployments using the following [aliases](/reference/minio-mc/mc-alias-set/#alias): `minio1`, `minio2`, and `minio3`. All three sites have complete bidirectional network access and low latency between sites.

```shell
mc admin replicate add minio1 minio2 minio3
```

The following command expands an existing site replication that includes peer sites `minio1`, `minio2`, `minio3`, and `minio4` to an additional peer site, `minio5`. `minio5` contains no data. List *all* existing peer sites first. List the site to expand to last.

If any existing sites are unreachable, first remove the unreachable sites with [`mc admin replicate rm`](#mc.admin.replicate.rm), then proceed with the site replication expansion.

```shell
mc admin replicate add minio1 minio2 minio3 minio4 minio5
```

The following command creates a new site replication configuration with ILM expiration rule synchronization between peer sites `minio1`, `minio2`, and `minio3`.

```shell
mc admin replicate add minio1 minio2 minio3 --replicate-ilm-expiry
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin replicate add      \
                            ALIAS1        \
                            ALIAS2        \
                            [ALIAS3 ...]  \
                            [--replicate-ilm-expiry]
```
{{% /tab %}}
{{< /tabpane >}}

#### `ALIAS` {#mc.admin.replicate.add.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to include in site replication.

At least two MinIO deployment aliases are required to create a site replication. Only the first alias can have buckets or objects. The first site can also be empty.

To expand an existing site replication to one more new replication sites, list all existing peer site [aliases](/reference/minio-mc/mc-alias-set/#alias) in the site replication set to expand. Then include one or more additional [aliases](/reference/minio-mc/mc-alias-set/#alias) to add to the existing site replication. The peers being added must be empty.

#### `--replicate-ilm-expiry` {#mc.admin.replicate.add.-replicate-ilm-expiry}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: mc**

RELEASE.2023-12-02T02-03-28Z
{{% /alert %}}

Replicate [ILM expiration](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) rules across peers.

#### `mc admin replicate update` {#mc.admin.replicate.update}

*mc-cmd*

Modifies the endpoint used for an existing peer site participating in site replication.

{{% alert color="info" %}}
**Changed: RELEASE.2023-01-11T03-14-16Z**

`mc admin replicate edit` renamed to `mc admin replicate update`.
{{% /alert %}}

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
```shell
mc admin replicate update                                                   \
                   minio2                                                 \
                   --deployment-id c1758167-4426-454f-9aae-5c3dfdf6df64   \
                   --endpoint https://minio2:9000
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin replicate update                     \
                            ALIAS                           \
                            --deployment-id [deploymentID]  \
                            --endpoint [newEndpoint]        \
                            --mode ["sync" | "async"]       \
                            --enable-ilm-expiry-replication \
                            --disable-ilm-expiry-replication
```
{{% /tab %}}
{{< /tabpane >}}

#### `ALIAS` {#mc.admin.replicate.update.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

#### `--bucket-bandwidth` {#mc.admin.replicate.update.-bucket-bandwidth}

*mc-cmd*

Set default bandwidth limit for bucket in bits per second.

Valid units include:

- `B` for bytes
- `K` for kilobytes
- `M` for megabytes
- `G` for gigabytes
- `T` for terabytes
- `Ki` for kibibytes
- `Mi` for mibibytes
- `Gi` for gibibytes
- `Ti` for tebibytes

For example, the following command limits the replication on the `myminio` deployment to no more than 2 Gigabytes per second.

```shell
mc admin replicate update myminio --deployment-id c1758167-4426-454f-9aae-5c3dfdf6df64 --bucket-bandwidth "2G"
```

#### `--deployment-id` {#mc.admin.replicate.update.-deployment-id}

*mc-cmd*

*Required*

The unique id of the deployment to change.

The deployment ID can be found by running [`mc admin replicate info ALIAS`](#mc.admin.replicate.info.ALIAS)

#### `--disable-ilm-expiry-replication` {#mc.admin.replicate.update.-disable-ilm-expiry-replication}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: mc**

RELEASE.2023-12-02T02-03-28Z
{{% /alert %}}

Stops the replication of ILM expiration rules between peer sites. Existing rules already synchronized across peers are not removed from any peer site.

#### `--enable-ilm-expiry-replication` {#mc.admin.replicate.update.-enable-ilm-expiry-replication}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: mc**

RELEASE.2023-12-02T02-03-28Z
{{% /alert %}}

Start replication of ILM expiration rules between peer sites.

#### `--endpoint` {#mc.admin.replicate.update.-endpoint}

*mc-cmd*

*Required*

The new endpoint or URL to associate with the peer site.

#### `--mode` {#mc.admin.replicate.update.-mode}

*mc-cmd*

*Optional*

Specify whether MinIO performs replication operations to the peer synchronously or asynchronously. Available values are `sync` and `async`.

Defaults to `async`.

#### `--sync` {#mc.admin.replicate.update.-sync}

*mc-cmd*

*Optional*

{{% alert color="warning" %}}
**Important**

The `--sync` flag has been deprecated as of `RELEASE.2023-07-07T05-25-51Z`. Use [`--mode`](#mc.admin.replicate.update.-mode) instead.
{{% /alert %}}

Enable or disable synchronous site replication. Available values are `enable` and `disable`. If not defined, MInIO uses asynchronous site replication.

#### `mc admin replicate rm, remove` {#mc.admin.replicate.rm}

*mc-cmd*

{{% alert color="info" %}}
**Changed: RELEASE.2023-01-11T03-14-16Z**

The `mc admin replicate remove` subcommand renamed to `mc admin replicate rm`.
{{% /alert %}}

Removes one or more sites from a site replication configuration.

Remember, if you intend to re-add the site to a site replication configuration in the future, it must be empty of [replicable data](/operations/replication/multi-site-replication/#minio-site-replication-what-replicates).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLES" %}}
Remove site replication for all connected sites for an existing site replication configuration that includes *minio2*. This deletes the site replication configuration for all participating sites.

```shell
mc admin replicate rm      \
                   minio2  \
                   --all   \
                   --force
```

Remove the sites with alias names `minio5` and `minio6` from an existing site replication configuration that includes *minio2*

```shell
mc admin replicate rm      \
                   minio2  \
                   minio5  \
                   minio6  \
                   --force
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin rm          \
                       TARGET      \
                       ALIAS1      \
                       [ALIAS2...] \
                       --all       \
                       --force
```
{{% /tab %}}
{{< /tabpane >}}

#### `TARGET` {#mc.admin.replicate.rm.TARGET}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of an active MinIO deployment participating in the site replication to target. Do not use an alias of a deployment to be removed, unless removing all sites from site replication.

#### `ALIAS` {#mc.admin.replicate.rm.ALIAS}

*mc-cmd*

*Optional*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of an active MinIO deployment to remove from a site replication configuration. May be repeated to remove additional sites.

#### `--all` {#mc.admin.replicate.rm.-all}

*mc-cmd*

*Optional*

Include this flag to remove all sites configured for site replication and end the site replication configuration.

#### `--force` {#mc.admin.replicate.rm.-force}

*mc-cmd*

*Required*

This flag forces the removal of the specified peer site(s) from the site replication configuration.

#### `mc admin replicate info` {#mc.admin.replicate.info}

*mc-cmd*

Returns information about the sites in the site replication configuration.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
```shell
mc admin replicate info minio1
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
```shell
mc [GLOBALFLAGS] admin replicate info ALIAS
```
{{% /tab %}}
{{< /tabpane >}}

#### `ALIAS` {#mc.admin.replicate.info.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of an active MinIO deployment in the site replication configuration.

#### `mc admin replicate status` {#mc.admin.replicate.status}

*mc-cmd*

Displays the status of the sites, buckets, users, groups, or policies for a site replication configuration.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLES" %}}
Display the overall replication status for a site replication configuration that includes the site `minio1`.

```shell
mc admin replicate status minio1
```

Display the replication status of buckets across sites for a site replication configuration that includes the site `minio1`.

```shell
mc admin replicate status     \
                   minio1     \
                   --buckets
```

Display the site replication status of a bucket called `images` across sites for a site replication configuration that contains the site `minio1`.

```shell
mc admin replicate status           \
                    minio1          \
                    --bucket images
```

Display the site replication status for the setting for a user, `janedoe`, across sites for a site replication configuration that contains the site `minio1`.

```shell
mc admin replicate status         \
                   minio1         \
                   --user janedoe
```

The output of the above examples resembles the following:

```shell
Bucket replication status:
●  30/30 Buckets in sync

Policy replication status:
●  5/5 Policies in sync

User replication status:
●  3/3 Users in sync

Group replication status:
No Groups present

ILM Expiry Rules replication status:
●  5/5 ILM Expiry Rules in sync

Object replication status:
Replication status since 1 day
Summary:
Replicated:    0 objects (0 B)
Queued:        - 0 objects, (0 B) (avg: 0 objects, 0 B; max: 0 objects, 0 B)
Received:      0 objects (0 B)
```

Display the site replication status across sites for the ILM expiration rule with rule ID of `ckok9v5b4dtgofkbi6tg` for a site replication configuration that contains the site `minio1`.

```shell
mc admin replicate status minio1 --ilm-expiry-rule ckok9v5b4dtgofkbi6tg
```

The output resembles the following:

```shell
●  ILM Expiry Rule replication summary for: ckok9v5b4dtgofkbi6tg

ILMExpiryRule   | MINIO1          | MINIO2
ILM Expiry Rule | ✔               | ✔
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
```shell
mc [GLOBALFLAGS] admin replicate status          \
                   TARGET                        \
                   [--all]                       \
                   [--buckets]                   \
                   [--bucket nameOfBucket]       \
                   [--groups]                    \
                   [--group nameOfGroup]         \
                   [--ilm-expiry-rules]          \
                   [--ilm-expiry-rule <rule ID>] \
                   [--policies]                  \
                   [--policy nameOfPolicy]       \
                   [--users]                     \
                   [--user accessKey]
```
{{% /tab %}}
{{< /tabpane >}}

#### `TARGET` {#mc.admin.replicate.status.TARGET}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of an active MinIO deployment in the site replication configuration.

#### `--all` {#mc.admin.replicate.status.-all}

*mc-cmd*

*Optional*

Display all available site replication status information.

#### `--buckets` {#mc.admin.replicate.status.-buckets}

*mc-cmd*

*Optional*

Display the replication status of all buckets.

#### `--bucket` {#mc.admin.replicate.status.-bucket}

*mc-cmd*

*Optional*

Display the replication status of a specific bucket by including the bucket name after the flag.

#### `--groups` {#mc.admin.replicate.status.-groups}

*mc-cmd*

*Optional*

Display the replication status of all groups.

#### `--group` {#mc.admin.replicate.status.-group}

*mc-cmd*

*Optional*

Display the replication status of a specific group by including the group name after the flag.

#### `--ilm-expiry-rules` {#mc.admin.replicate.status.-ilm-expiry-rules}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: mc**

RELEASE.2023-12-02T02-03-28Z
{{% /alert %}}

Display sync information about ILM expiration rules.

Mutually exclusive with [`--ilm-expiry-rule`](#mc.admin.replicate.status.-ilm-expiry-rule)

#### `--ilm-expiry-rule` {#mc.admin.replicate.status.-ilm-expiry-rule}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: mc**

RELEASE.2023-12-02T02-03-28Z
{{% /alert %}}

Display replication status information about the specified ILM expiration rule.

Mutually exclusive with [`--ilm-expiry-rules`](#mc.admin.replicate.status.-ilm-expiry-rules)

#### `--policies` {#mc.admin.replicate.status.-policies}

*mc-cmd*

*Optional*

Display the replication status of all policies.

#### `--policy` {#mc.admin.replicate.status.-policy}

*mc-cmd*

*Optional*

Display the replication status of a specific policy by including the policy name after the flag.

#### `--users` {#mc.admin.replicate.status.-users}

*mc-cmd*

*Optional*

Display the replication status of all users.

#### `--user` {#mc.admin.replicate.status.-user}

*mc-cmd*

*Optional*

Display the replication status of a specific user by including the user name after the flag.

#### `mc admin replicate resync` {#mc.admin.replicate.resync}

*mc-cmd*

Resynchronizes data from one site in the replication configuration to a second site in the replication configuration in the event of lost data.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLES" %}}
The following command starts a resynchronization process to restore `minio2` from `minio1`

```shell
mc admin replicate resync start minio1 minio2
```

The following command shows the status of a resynchronization currently in progress.

```shell
mc admin replicate resync status minio1 minio2
```

The following command stops a resynchronization that is in progress.

```shell
mc admin replicate resync cancel minio1 minio2
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
```shell
mc [GLOBALFLAGS] admin replicate resync start|status|cancel ALIAS1 ALIAS2
```

- Replace `ALIAS1` with the alias for the site that has the data to restore.
- Replace `ALIAS2` with the alias for the site that needs resynched data.
{{% /tab %}}
{{< /tabpane >}}

#### `start` {#mc.admin.replicate.resync.start}

*mc-cmd*

Launches a new resynchronization process from one site with data to a second site that needs synchronization.

#### `status` {#mc.admin.replicate.resync.status}

*mc-cmd*

Shows the status of an existing resynchronization process between two sites configured for site replication.

#### `cancel` {#mc.admin.replicate.resync.cancel}

*mc-cmd*

Ends a resynchronization process currently in progress between two sites configured for site replication.

#### `alias1` {#mc.admin.replicate.resync.alias1}

*mc-cmd*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of an active MinIO deployment in the site replication configuration with the data you want to resync to another site.

#### `alias2` {#mc.admin.replicate.resync.alias2}

*mc-cmd*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of an active MinIO deployment in the site replication configuration that needs data resynced from another site.

## Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

---
title: "Site Replication Overview"
url: "/operations/replication/multi-site-replication/"
weight: 20
icon: fa-solid fa-arrows-rotate
minio_origin: true
silo_modified: true
---

<a id="site-replication-overview"></a>
<a id="minio-site-replication-overview"></a>

Site replication configures multiple independent MinIO deployments as a cluster of replicas called peer sites.

> <figure>
>   <img src="/images/architecture/architecture-load-balancer-multi-site.svg" alt="Diagram of a site replication deployment with two sites" />
>   <figcaption>A site replication deployment with two peer sites.
> A load balancer manages routing operations to either of the two sites.
> Data written to one site automatically replicates to the other peer site.</figcaption>
> </figure>

Site replication assumes the use of either the included MinIO identity provider (IDP) *or* an external IDP. All configured deployments must use the same IDP. Deployments using an external IDP must use the same configuration across sites.

For more information on site replication architecture and deployment concepts, see [Deployment Architecture: Replicated MinIO Deployments](/operations/concepts/architecture/#minio-deployment-architecture-replicated).

MinIO does not recommend using macOS, Windows, or non-orchestrated container deployments for site replication outside of early development, evaluation, or general experimentation. For production, use a supported [Linux](/operations/deployments/baremetal/) or [Kubernetes](/operations/deployments/kubernetes/) deployment and follow the site-replication procedure on this page.

## Overview {#overview}

<a id="minio-site-replication-what-replicates"></a>

### What Replicates Across All Sites {#what-replicates-across-all-sites}

Each MinIO deployment (“peer site”) synchronizes the following changes across the other peer sites:

- Creation, modification, and deletion of buckets and objects, including

  - Bucket and Object Configurations
  - [Policies](/administration/identity-access-management/policy-based-access-control/#minio-policy)
  - [`mc tag set`](/reference/minio-mc/mc-tag-set/#command-mc.tag.set)
  - [Locks](/administration/object-management/object-retention/#minio-object-locking), including retention and legal hold configurations
  - [Encryption settings](/administration/server-side-encryption/#minio-encryption-overview)
- Creation and deletion of IAM users, groups, policies, and policy mappings to users or groups (for LDAP users or groups)
- Creation of Security Token Service (STS) credentials for session tokens verifiable from the local `root` credentials
- Creation and deletion of [access keys](/reference/minio-mc-admin/mc-admin-user-svcacct/#minio-mc-admin-user-svcacct) (except those owned by the `root` user)

Site replication enables [bucket versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) for all new and existing buckets on all replicated sites.

{{% alert color="info" %}}
**Added: mc**

RELEASE.2023-12-02T02-03-28Z
{{% /alert %}}

You can choose to replicate ILM expiration rules across peer sites. For new site replication configurations, use the [`mc admin replicate add`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.add) with the [`--replicate-ilm-expiry`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.add.-replicate-ilm-expiry) flag. For existing site replication configurations, you can enable or disable the behavior using [`mc admin replicate update`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.update) with either the [`--enable-ilm-expiry-replication`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.update.-enable-ilm-expiry-replication) or [`--disable-ilm-expiry-replication`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.update.-disable-ilm-expiry-replication) flag, as appropriate.

### What Does Not Replicate Across Sites {#what-does-not-replicate-across-sites}

MinIO deployments in a site replication configuration do *not* replicate the creation or modification of the following items:

- [Bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications)
- [Lifecycle management (ILM) configurations](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management)
- [Site configuration settings](/reference/minio-mc-admin/mc-admin-config/#minio-mc-admin-config)

### Initial Site Replication Process {#initial-site-replication-process}

After enabling site replication, identity and access management (IAM) settings sync in the following order:

{{< tabpane text=true persist=header >}}
{{% tab header="MinIO IDP" %}}

1. Policies
2. User accounts (for local users)
3. Groups
4. Access Keys

   Access Keys for `root` do not sync.
5. Policy mapping for synced user accounts
6. Policy mapping for [Security Token Service (STS) users](/developers/security-token-service/#minio-security-token-service)
{{% /tab %}}
{{% tab header="OIDC" %}}
1. Policies
2. Access Keys associated to OIDC accounts with a valid [MinIO Policy](/administration/identity-access-management/policy-based-access-control/#minio-policy). `root` access keys do not sync.
3. Policy mapping for synced user accounts
4. Policy mapping for [Security Token Service (STS) users](/developers/security-token-service/#minio-security-token-service)
{{% /tab %}}
{{% tab header="LDAP" %}}
1. Policies
2. Groups
3. Access Keys associated to LDAP accounts with a valid [MinIO Policy](/administration/identity-access-management/policy-based-access-control/#minio-policy). `root` access keys do not sync.
4. Policy mapping for synced user accounts
5. Policy mapping for [Security Token Service (STS) users](/developers/security-token-service/#minio-security-token-service)
{{% /tab %}}
{{< /tabpane >}}

After the initial synchronization of data across peer sites, MinIO continually replicates and synchronizes [replicable data](#minio-site-replication-what-replicates) among all sites as they occur on any site.

### Site Healing {#site-healing}

Any MinIO deployment in the site replication configuration can resynchronize damaged [replica-eligible data](#minio-site-replication-what-replicates) from the peer with the most updated (“latest”) version of that data.

{{% alert color="info" %}}
**Changed: RELEASE.2023-07-18T17-49-40Z**

Site replication operations retry up to three (3) times.

MinIO dequeues replication operations that fail to replicate after three attempts. The [scanner](/operations/concepts/scanner/#minio-concepts-scanner) picks up those affected objects at a later time and requeues them for replication.
{{% /alert %}}

{{% alert color="info" %}}
**Changed: RELEASE.2022-08-11T04-37-28Z**

Failed or pending replications requeue automatically when performing any `GET` or `HEAD` API method. For example, using [`mc stat`](/reference/minio-mc/mc-stat/#command-mc.stat), [`mc cat`](/reference/minio-mc/mc-cat/#command-mc.cat), or [`mc ls`](/reference/minio-mc/mc-ls/#command-mc.ls) commands after a site comes back online prompts healing to requeue.
{{% /alert %}}

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-02T23-48-47Z**

If one site loses data for any reason, resynchronize the data from another healthy site with [`mc admin replicate resync`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.resync). This launches an active process that resynchronizes the data without waiting for the passive [MinIO scanner](/operations/concepts/scanner/#minio-concepts-scanner) to recognize the missing data.
{{% /alert %}}

You can adjust how MinIO balances the scanner performance with read/write operations using either the [`MINIO_SCANNER_SPEED`](/reference/minio-server/settings/core/#envvar.MINIO_SCANNER_SPEED) environment variable or the [`scanner speed`](/reference/minio-server/settings/core/#mc-conf.scanner.speed) configuration setting.

### Synchronous vs Asynchronous Replication {#synchronous-vs-asynchronous-replication}

MinIO supports specifying either asynchronous (default) or synchronous replication for a given remote target.

With asynchronous replication, MinIO completes the originating `PUT` operation *before* placing the object into a [replication queue](/administration/bucket-replication/#minio-replication-process). The originating client may therefore see a successful `PUT` operation *before* the object is replicated. While this may result in stale or missing objects on the remote, it mitigates the risk of slow write operations due to replication load.

With synchronous replication, MinIO attempts to replicate the object *prior* to completing the originating `PUT` operation. MinIO returns a successful `PUT` operation whether or not the replication attempt succeeds. This reduces the risk of slow write operations at a possible cost of stale or missing objects on the remote location.

MinIO strongly recommends using the default asynchronous site replication. Synchronous site replication performance depends strongly on latency between sites, where higher latency can result in lower PUT performance and replication lag. To configure synchronous site replication use [`mc admin replicate update`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.update) with the [`--mode`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.update.-mode) option.

### Proxy to Other Sites {#proxy-to-other-sites}

MinIO peer sites can proxy `GET/HEAD` requests for an object to other peers to check if it exists. This allows a site that is healing or lagging behind other peers to still return an object persisted to other sites.

For example:

1. A client issues `GET("data/invoices/january.xls")` to `Site1`
2. `Site1` cannot locate the object
3. `Site1` proxies the request to `Site2`
4. `Site2` returns the latest version of the requested object
5. `Site1` returns the proxied object to the client

For `GET/HEAD` requests that do *not* include a unique version ID, the proxy request returns the *latest* version of that object on the peer site. This may result in retrieval of a non-current version of an object, such as if the responding peer site is also experiencing replication lag.

MinIO does not proxy `LIST`, `DELETE`, and `PUT` operations.

## Prerequisites {#prerequisites}

### Back Up Cluster Settings First {#back-up-cluster-settings-first}

Use the [`mc admin cluster bucket export`](/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) and [`mc admin cluster iam export`](/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) commands to take a snapshot of the bucket metadata and IAM configurations respectively prior to configuring Site Replication. You can use these snapshots to restore bucket/IAM settings in the event of misconfiguration during site replication configuration.

### One Site with Data at Setup {#one-site-with-data-at-setup}

Only *one* site can have data at the time of setup. The other sites must be empty of buckets and objects.

After configuring site replication, any data on the first deployment replicates to the other sites.

### All Sites Must Use the Same IDP {#all-sites-must-use-the-same-idp}

All sites must use the same [Identity Provider](/administration/identity-access-management/#minio-authentication-and-identity-management). Site replication supports the included MinIO IDP, OIDC, or LDAP.

### All Sites Must use the Same MinIO Server Version {#all-sites-must-use-the-same-minio-server-version}

All sites must have a matching and consistent MinIO Server version. Configuring replication between sites with mismatched MinIO Server versions may result in unexpected or undesired replication behavior.

You should also ensure the [`mc`](/reference/minio-mc/#command-mc) version used to configure replication closely matches the server version.

### Access to the Same Encryption Service {#access-to-the-same-encryption-service}

For [SSE-S3](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3) or [SSE-KMS](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms) encryption via Key Management Service (KMS), all sites must have access to a central KMS deployment.

You can achieve this with a central KES server or multiple KES servers (say one per site) connected via a central supported [key vault server](/administration/server-side-encryption/#minio-sse).

### Replication Requires Versioning {#replication-requires-versioning}

Site replication *requires* [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) and enables it for all created buckets automatically. You cannot disable versioning in site replication deployments.

MinIO cannot replicate objects in prefixes in the bucket that you excluded from versioning.

### Load Balancers Installed on Each Site {#load-balancers-installed-on-each-site}

Specify the URL or IP address of the site’s load balancer, reverse proxy, or similar network control plane component. Requests are automatically routed to nodes in the deployment.

MinIO recommends against using a single node hostname for a peer site. This creates a single point of failure: if that node goes offline, replication fails.

### Switch to Site Replication from Bucket Replication {#switch-to-site-replication-from-bucket-replication}

[Bucket replication](/administration/bucket-replication/#minio-bucket-replication) and multi-site replication are mutually exclusive. You cannot use both replication methods on the same deployments.

If you previously set up bucket replication and wish to now use site replication, you must first delete all of the bucket replication rules on the deployment that has data when initializing site replication. Use [`mc replicate rm`](/reference/minio-mc/mc-replicate-rm/#command-mc.replicate.rm) on the command line to remove bucket replication rules.

Only one site can have data when setting up site replication. All other sites must be empty.

## Tutorials {#tutorials}

<a id="minio-configure-site-replication"></a>

### Configure Site Replication {#configure-site-replication}

The following steps create a new site replication configuration for three [distributed deployments](/operations/deployments/installation/#deploy-minio-distributed). One of the sites contains [replicable data](#minio-site-replication-what-replicates).

The three sites use aliases, `minio1`, `minio2`, and `minio3`, and only `minio1` contains any data.

1. [Deploy](/operations/deployments/installation/#deploy-minio-distributed) three or more separate MinIO sites, using the same [IDP](/administration/identity-access-management/#minio-authentication-and-identity-management)

   Start with empty sites *or* have no more than one site with any [replicable data](#minio-site-replication-what-replicates).
2. Configure an alias for each site

   Specify the URL or IP address of the site’s load balancer, reverse proxy, or similar network control plane component. Requests are automatically routed to nodes in the deployment.

   MinIO recommends against using a single node hostname for a peer site. This creates a single point of failure: if that node goes offline, replication fails.

   For example, for three MinIO sites, you might create aliases `minio1`, `minio2`, and `minio3`.

   Use [`mc alias set`](/reference/minio-mc/mc-alias-set/#command-mc.alias.set) to define the hostname or IP of the load balancer managing connections to the site.

   ```shell
   mc alias set minio1 https://minio1.example.com:9000 adminuser adminpassword
   mc alias set minio2 https://minio2.example.com:9000 adminuser adminpassword
   mc alias set minio3 https://minio3.example.com:9000 adminuser adminpassword
   ```

   or define environment variables

   ```shell
   export MC_HOST_minio1=https://adminuser:adminpassword@minio1.example.com
   export MC_HOST_minio2=https://adminuser:adminpassword@minio2.example.com
   export MC_HOST_minio3=https://adminuser:adminpassword@minio3.example.com
   ```

3. Add site replication configuration

   ```shell
   mc admin replicate add minio1 minio2 minio3
   ```

   If all sites are empty, the order of the aliases does not matter. If one of the sites contains any [replicable data](#minio-site-replication-what-replicates), you must list it first.

   No more than one site can contain any replicable data.
4. Query the site replication configuration to verify

   ```shell
   mc admin replicate info minio1
   ```

   You can use the alias for any peer site in the site replication configuration.
5. Query the site replication status to confirm any initial data has replicated to all peer sites.

   ```shell
   mc admin replicate status minio1
   ```

   You can use the alias for any of the peer sites in the site replication configuration. The output should say that all [replicable data](#minio-site-replication-what-replicates) is in sync.

   The output could resemble the following:

   ```shell
   Bucket replication status:
   ●  1/1 Buckets in sync

   Policy replication status:
   ●  5/5 Policies in sync

   User replication status:
   No Users present

   Group replication status:
   No Groups present
   ```

   For more on reviewing site replication, see the [Site Replication Status tutorial](#minio-site-replication-status-tutorial).

<a id="minio-expand-site-replication"></a>

### Expand Site Replication {#expand-site-replication}

You can add more sites to an existing site replication configuration.

The new site must meet the following requirements:

- Site is fully deployed and accessible by hostname or IP
- Shares the IDP configuration as all other sites in the configuration
- Uses the same root user credentials as other configured sites
- Contains no bucket or object data

1. Deploy the new MinIO peer site(s) following the stated requirements
2. Configure an alias for the new site

   Specify the URL or IP address of the site’s load balancer, reverse proxy, or similar network control plane component. Requests are automatically routed to nodes in the deployment.

   MinIO recommends against using a single node hostname for a peer site. This creates a single point of failure: if that node goes offline, replication fails.

   To check the existing aliases, use [`mc alias list`](/reference/minio-mc/mc-alias-list/#command-mc.alias.list).

   Use [`mc alias set`](/reference/minio-mc/mc-alias-set/#command-mc.alias.set) to define the hostname or IP of the load balancer managing connections to the new site(s).

   ```shell
   mc alias set minio4 https://minio4.example.com:9000 adminuser adminpassword
   ```

   or define environment variables

   ```shell
   export MC_HOST_minio4=https://adminuser:adminpassword@minio4.example.com
   ```

3. Add site replication configuration

   Use the [`mc admin replicate add`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.add) command to expand the site replication configuration with the new peer site. Specify the alias of *all* existing peer sites, then the alias of the new site to add.

   For example, the following command adds the new peer site `minio4` to an existing site replication configuration that includes the existing sites `minio1`, `minio2`, and `minio3`.

   ```shell
   mc admin replicate add minio1 minio2 minio3 minio4
   ```

   {{% alert color="info" %}}
   **Note**

   If any of the sites are unreachable or permanently lost, you **must** first remove the unreachable site(s) with [`mc admin replicate rm`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.rm) before expanding with the new site.
   {{% /alert %}}
4. Query the site replication configuration to verify

   ```shell
   mc admin replicate info minio1
   ```

### Modify a Site’s Endpoint {#modify-a-site-s-endpoint}

If a peer site changes its hostname, you can modify the replication configuration to reflect the new hostname.

1. Obtain the site’s Deployment ID with [`mc admin replicate info`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.info)

   ```shell
   mc admin replicate info <ALIAS>
   ```

2. Update the site’s endpoint with [`mc admin replicate update`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.update)

   ```shell
   mc admin replicate update ALIAS --deployment-id [DEPLOYMENT-ID] --endpoint [NEW-ENDPOINT]
   ```

   Replace \[DEPLOYMENT-ID\] with the deployment ID of the site to update.

   Replace \[NEW-ENDPOINT\] with the new endpoint for the site.

   Specify the URL or IP address of the site’s load balancer, reverse proxy, or similar network control plane component. Requests are automatically routed to nodes in the deployment.

   MinIO recommends against using a single node hostname for a peer site. This creates a single point of failure: if that node goes offline, replication fails.

### Remove a Site from Replication {#remove-a-site-from-replication}

You can remove a site from replication at any time. You can re-add the site at a later date, but you must first completely wipe bucket and object data from the site.

Use [`mc admin replicate rm`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.rm):

```shell
mc admin replicate rm ALIAS PEER_TO_REMOVE --force
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of any peer site in the replication configuration.
- Replace `PEER_TO_REMOVE` with the alias of the peer site to remove.

All healthy peers in the site replication configuration update to remove the specified peer automatically.

MinIO requires the `--force` flag to remove the peer from the site replication configuration.

<a id="minio-site-replication-status-tutorial"></a>

### Review Replication Status {#review-replication-status}

MinIO provides information on replication across the sites for users, groups, policies, or buckets.

The summary information includes the number of **Synced** and **Failed** items for each category.

Use [`mc admin replicate status`](/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.status):

```shell
mc admin replicate status <ALIAS> --<flag> <value>
```

For example:

- `mc admin replicate status minio3 --bucket images`

  Displays the replication status for the `images` bucket on the `minio3` site.

  The output resembles the following:

  ```text
  ●  Bucket config replication summary for: images

  Bucket          | MINIO2          | MINIO3          | MINIO4
  Tags            |                 |                 |
  Policy          |                 |                 |
  Quota           |                 |                 |
  Retention       |                 |                 |
  Encryption      |                 |                 |
  Replication     | ✔               | ✔               | ✔
  ```

- `mc admin replicate status minio3 --all`

  Displays the replication status summary for all replication sites of which `minio3` is part.

  The output resembles the following:

  ```text
  Bucket replication status:
  ●  1/1 Buckets in sync

  Policy replication status:
  ●  5/5 Policies in sync

  User replication status:
  ●  1/1 Users in sync

  Group replication status:
  ●  0/2 Groups in sync

  Group           | MINIO2          | MINIO3          | MINIO4
  ittechs         | ✗  in-sync      |                 | ✗  in-sync
  managers        | ✗  in-sync      |                 | ✗  in-sync
  ```

---
title: "Managing Objects"
url: "/administration/console/managing-objects/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/console/managing-objects.rst
upstream_modified: true
---

> **Console 2.5.1 updates:** The Tasks drawer tracks bounded transfers and bulk operations (canceling a task stops remaining batches without rolling back completed mutations); Text/Markdown/CSV previews display a notice when truncated at `1 MiB`; ZIP preview failures before the first response byte preserve the upstream S3 error status; and sorting, filtering, and Select All operate on the currently loaded page. See the [Console 2.5.1 object workspace notes](/blog/release/console-2.5.1/#objects).

<a id="managing-objects"></a>
<a id="minio-console-managing-objects"></a>

You can use the MinIO Console to perform several of the bucket and object management and interaction functions available in MinIO. Depending on the permissions and IAM policies for the authenticated user, you can:

- [Browse, upload, revert, manage, and interact with objects](#minio-console-object-browser).
- [Browse, create, and manage buckets](#minio-console-buckets).
- [Create or monitor remote tiers](#minio-console-tiers) for object transition rules.

<a id="minio-console-object-browser"></a>

## Object Browser {#object-browser}

In the [Server 20261026](/blog/release/silo-20261026/#server-20261026), Console's `account-info` request reads the live bucket inventory so refreshing after creating or deleting a bucket immediately reflects the updated list (bucket usage totals remain scanner-derived). Server 20261018 serves a cached bucket inventory.

The Object Browser lists the buckets and objects the authenticated user has access to on the deployment.

After logging in or navigating to the tab, the object browser displays a list of the user’s buckets, which the user can filter. Select a bucket to show a list of objects in the bucket.

Select a specific object to display summary information about the object such as name, size, tags, holds, and retention policies that apply. The console also shows the object’s metadata.

The user can perform actions on the bucket’s objects, depending on the policies and permissions that apply. Example actions the user may be able to perform include:

- Rewind to a previous version
- Create prefixes
- View deleted objects
- Upload objects
- Download objects
- Share
- Preview
- Manage legal holds
- Manage retention
- Manage tags
- Inspect
- Display versions
- [Delete](/administration/object-management/object-delete/#minio-object-delete)

> [!NOTE]
> **Added: Console**
>
> v0.24.0
>
> View the status of uploading or downloading objects with the object manager button available on the top right corner of the Console. If you have not uploaded or downloaded any objects during the current session, the button does not appear.

> [!NOTE]
> **Changed: Console**
>
> v0.35.0
>
> If you select multiple objects to download, MinIO creates a ZIP archive of those objects for downloading. You must unzip or uncompress this archive after downloading to access the files.

### Multi-object downloads and sharing {#silo-downloads}

[Console v2.4.1](/blog/release/console-2.4.1/) streams multi-selection ZIPs to a
file writer where supported; other browsers use their native download manager.
Neither path buffers the complete archive in JavaScript. Console identifies
the native handoff explicitly; use the browser download manager for subsequent
progress, cancellation and network errors. Recursive ZIPs normally have no
reliable total and therefore no completion percentage. Selections above 5 GiB
or with unknown size recommend mcli.

Directory listings are paged: sorting, filtering and select-all cover the
current page. Duplicate ZIP tasks are prevented; dismissing a handed-off task
in Console does not cancel the browser download. Public, presigned and
version-specific sharing remains available. The anonymous proxy only accepts
object-content GETs at the configured S3 origin and rejects redirects and system
endpoints. See the [sharing boundary](/reference/minio-server/settings/console/#object-sharing).

<a id="minio-console-admin-buckets"></a>
<a id="minio-console-buckets"></a>

## Buckets {#buckets}

The Console’s **Bucket** section displays all buckets to which the authenticated user has [access](/administration/identity-access-management/policy-based-access-control/#minio-policy). Use this section to create or manage these buckets, depending on your user’s access.

### Creating Buckets {#creating-buckets}

Select **Create Bucket** to create a new bucket on the deployment. MinIO validates bucket names. To see the rules for bucket names, select **View Bucket Naming Rules**.

MinIO does not limit the total number of buckets allowed on a deployment. However, MinIO recommends no more than 500,000 buckets per deployment as a general guideline.

While creating a bucket, you can enable [versioning](/administration/object-management/object-versioning/#minio-bucket-versioning), [object locking](/administration/object-management/object-retention/#minio-object-locking), bucket size (quota) limits, and [retention rules](/administration/object-management/object-retention/#minio-object-locking-retention-modes) (which require versioning).

> [!NOTE]
> **Changed: Console**
>
> v0.35.0
>
> If you enable versioning, you can specify prefixes to exclude from versioning.

You **must** configure replication, locking, and versioning options at the time of bucket creation. You cannot change these settings for the bucket later.

### Managing Buckets {#managing-buckets}

Use the **Search** bar to filter for specific buckets. Select the row for the bucket to display summary information about the bucket.

Form the summary screen, select any of the available tabs to further manage the bucket.

> [!NOTE]
> **Note**
>
> Some management features may not be available if the authenticated user does not have the [required administrative permissions](/administration/identity-access-management/policy-based-access-control/#minio-policy-mc-admin-actions).

When managing a bucket, your access settings may allow you to view or change any of the following:

- The **Summary** section displays a summary of the bucket’s configuration.

  Use this section to view and modify the bucket’s access policy, encryption, quota, and tags.
- Configure alerts in the **Events** section to trigger [notification events](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) when a user uploads, accesses, or deletes matching objects.
- Copy objects to remote locations in the **Replication** section with [Server Side Bucket Replication Rules](/administration/bucket-replication/#minio-bucket-replication-serverside).
- Expire or transition objects in the bucket from the **Lifecycle** section by setting up [Object Lifecycle Management Rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management).
- Review security in the **Access** section by listing the [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) and [users](/administration/identity-access-management/minio-user-management/#minio-users) with access to that bucket.
- Properly secure unauthenticated access with the **Anonymous** section by managing rules for prefixes that unauthenticated users can use to read or write objects.

<a id="minio-console-tiers"></a>

## Tiers {#tiers}

The **Tiering** section provides an interface for adding and managing [remote tiers](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering) to support lifecycle management transition rules. MinIO tiering supports moving objects from the deployment to the remote storage, but does not support automatically restoring them to the deployment.

The tiering tab allows users with the appropriate permissions to:

- Review the status and summary information for all configured remote tiers.
- Create a tier for a new remote target to storage on another MinIO deployment, Google Cloud Storage, Amazon’s AWS S3, or Azure.
- Cycle the access credentials for any of the configured tiers with the tier’s <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-pencil" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M11.013 1.427a1.75 1.75 0 012.474 0l1.086 1.086a1.75 1.75 0 010 2.474l-8.61 8.61c-.21.21-.47.364-.756.445l-3.251.93a.75.75 0 01-.927-.928l.929-3.25a1.75 1.75 0 01.445-.758l8.61-8.61zm1.414 1.06a.25.25 0 00-.354 0L10.811 3.75l1.439 1.44 1.263-1.263a.25.25 0 000-.354l-1.086-1.086zM11.189 6.25L9.75 4.81l-6.286 6.287a.25.25 0 00-.064.108l-.558 1.953 1.953-.558a.249.249 0 00.108-.064l6.286-6.286z"></path></svg> icon.


## Usage scans (development) {#usage-scans}

> **Not yet released:** This section describes the Console work being integrated
> from [PR #70](https://github.com/pgsty/silo-console/pull/70). It is not included
> in Console 2.5.1 or Server 20261026. A Console release and the corresponding
> embedded-Console dependency update in SILO Server are separate delivery steps.
> The supported integration target is `pgsty/silo`; upstream MinIO compatibility
> is best effort.

<!-- Adapted from pgsty/silo-console PR #70, docs/FolderSizes.md.
Copyright (c) 2026 Urbanize. SPDX-License-Identifier: AGPL-3.0-or-later. -->

### Folder sizes

The object browser lists S3 prefixes as folders. S3 does not attach a size to a
prefix. **Calculate folder sizes** performs one recursive metadata scan of the
current directory and fills its immediate folder rows with current-object
sizes. It never downloads object contents. Opening a folder does not start a scan; the folder Refresh button starts one explicitly.
Use a folder's actions menu → **Calculate size** to narrow a large scan.

**Include retained versions** additionally lists older object versions and delete
markers. The Size column continues to show current bytes; retained bytes appear
separately. A latest delete marker contributes no current bytes, while older
versions behind it still contribute retained bytes. Zero-byte directory-marker
objects count as objects. Logical object bytes do not measure physical disk
allocation, compression, erasure coding, filesystem snapshots or replicas.

The panel shows progress, entry counts and calculation time. **Cancel** stops the
request and S3 pagination. Results are local to the current view and session;
navigation clears them. Recalculate after changing objects. Listings are live,
not an atomic snapshot: objects can change while a scan is running.

Only **Completed** means the listing finished. While running, canceled, limited
or failed, values carry a ≥ / Partial label and must not be used as complete
capacity totals. A permission failure, broken connection or interrupted response
never becomes a zero-sized folder. Scan a narrower prefix when limits are hit.
Size sorting uses calculated bytes for folders already included in the scan and
ordinary object metadata for files; as elsewhere, sorting covers loaded rows.

### Permissions and limits

Scanning requires a signed-in Console session with `s3:ListBucket` access to the
requested prefix. Version scans require `s3:ListBucketVersions`. The API always
uses that session's S3 credentials, including STS session tokens. It does not
use server administrator credentials, change objects or expose anonymous scans.

Operators can configure each Console process using these environment variables:

| Variable | Default | Accepted range |
| --- | --- | --- |
| `CONSOLE_PREFIX_USAGE_TIMEOUT` | `10m` | `1s`–`1h` |
| `CONSOLE_PREFIX_USAGE_MAX_ENTRIES` | `10000000` | 1–1000000000000 |
| `CONSOLE_PREFIX_USAGE_MAX_FOLDERS` | `1000` | 1–10000 |
| `CONSOLE_PREFIX_USAGE_MAX_CONCURRENT` | `2` | 1–64 |
| `CONSOLE_PREFIX_USAGE_PROGRESS_INTERVAL` | `1s` | `100ms`–`30s` |

Concurrency is per process. A busy process returns HTTP 429; the UI permits one
active scan per browser view. A time, entry or child-folder limit returns a
terminal partial result and cancels further listing requests. Invalid operator
configuration refuses scans rather than removing their limits.

### API

`GET /api/v1/buckets/{bucket}/prefix-usage?prefix=&versions=false&folders=true`
uses the normal authenticated Console API. Supply `prefix=` for the bucket root,
or a prefix ending in `/`. Set `folders=false` to calculate only this prefix.

The response is `application/x-ndjson`. Each line is a `prefixUsageFrame` defined
in `swagger.yml`: bucket/prefix/mode identity, start/update times, scanned entry
count, aggregate usage and child-folder usage. Byte values are decimal strings
so JavaScript does not round totals larger than 2^53. Frames end in `complete`,
`limited` or `failed`; missing or invalid terminal data is an incomplete result.
Initial listing failures preserve permission/not-found status before streaming.
Consumers should cancel the request when they stop reading.

Run `go test ./api -run TestPrefixUsage`, frontend `yarn typecheck`, and
`yarn exec playwright test --project=unit e2e/prefix-usage.unit.ts` for focused
checks. `e2e/prefix-usage.spec.ts` also runs against a real SILO backend and
Console: it owns a generated fixture bucket, checks pagination and version
accounting, exercises the folder UI, and removes every fixture version/marker.
Use the existing `CONSOLE_TEST_ENDPOINT`, `CONSOLE_TEST_ACCESS_KEY` and
`CONSOLE_TEST_SECRET_KEY` settings, plus `SILO_TEST_ENDPOINT` for the S3 endpoint.
Never point fixture tests at a bucket owned by an operator.


### Bucket refresh and automatic updates

On **Buckets**, **Refresh** requests a new metadata scan for every listed bucket,
including those hidden by the search filter. The table and cards show **Current
size**, retained-version bytes, per-bucket completion time, queued/running state,
and scan progress. Last completed totals stay visible while new work runs. A
queue acceptance is not a completed scan. Unknown totals remain unknown; partial
progress never replaces a completed total. Sorting uses exact integer bytes.

Inside a bucket, **Refresh** refreshes the object listing and calculates the
current directory's immediate folder sizes. **Calculate size** in a folder's
menu narrows that scan. These foreground scans are cancellable and end on
navigation; no background folder scan starts merely by browsing.

#### Optional persistent worker

For durable bucket refresh and automatic updates, provide
`CONSOLE_USAGE_DATABASE_URL` to the Console and run **the same build** as
`console usage-worker`. PostgreSQL is required only for this optional mode. The
worker owns schema migrations and needs CREATE in its dedicated database's
public schema. Browser processes never migrate in response to a request. Use a
verified TLS database URI and a bounded connection pool. Keep worker credentials
out of browser processes.

Both processes use the identical `CONSOLE_MINIO_SERVER` endpoint and database.
Set `CONSOLE_USAGE_S3_ACCESS_KEY`, `CONSOLE_USAGE_S3_SECRET_KEY` and optionally
`CONSOLE_USAGE_S3_SESSION_TOKEN` only on the worker. Its dedicated S3 policy is:

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:ListAllMyBuckets","s3:ListenNotification"],"Resource":["*"]},{"Effect":"Allow","Action":["s3:GetBucketLocation","s3:ListBucket","s3:ListBucketVersions","s3:ListenBucketNotification"],"Resource":["arn:aws:s3:::*"]}]}
```

No object-read, object-write or administrative action is needed. Console API
requests independently probe the caller's root listing permissions before
returning or refreshing any saved aggregate. A denied version-list request omits
retained bytes/counts, delete markers and version scan progress. SILO currently
permits ListBucket as a compatibility fallback for ListBucketVersions; the API
honors the permissions the storage server actually grants. Prefix-restricted
callers cannot retrieve a whole-bucket aggregate. Revocation is checked again
on every status request. API responses are `Cache-Control: no-store`.

The worker subscribes to authenticated storage mutation notifications. Creates,
overwrites, completed multipart uploads and removals invalidate the affected
bucket. Repeated or reordered events coalesce into one queued scan, rather than
adding or subtracting potentially duplicated byte deltas. Changes during a scan
request a follow-up generation. Requests are durable in PostgreSQL, prioritized
for explicit refreshes and claimed with expiring, fenced leases. Workers yield
between bounded time slices; pagination resumes only after a whole object key
and all its versions, so a key spanning multiple version pages is not skipped.

The live notification subscription has **no durable replay guarantee**. Startup
and reconnect invalidate existing totals for reconciliation. Frequent bucket
inventory checks discover new buckets without rescanning unchanged buckets. A
separate full reconciliation covers gaps and changes not represented in the
stream. Coverage is visibly degraded until the connection and its reconciliation
recover. A completed scan is a live listing, not an atomic filesystem snapshot.

Without the database, Refresh performs bounded foreground metadata scans and the
UI explicitly says automatic updates are unconfigured. Navigating away stops
those scans; completed totals are not shared across replicas in this mode.

#### Worker and API settings

All names below start with `CONSOLE_USAGE_`. Durations use Go duration syntax.
Invalid, missing required or incompatible settings fail closed.

| Suffix | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | unset | PostgreSQL URI; opts web processes into persistent mode |
| `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_SESSION_TOKEN` | unset | Dedicated worker identity; token optional |
| `HTTP_ADDRESS` | `:9091` | Internal worker health/metrics listener |
| `POOL_MAX_CONNECTIONS` | 4 | Connections per process |
| `CONCURRENT_SCANS` | 1 | Concurrent worker scan slices |
| `MAX_ENTRIES` | 100000000 | Maximum entries per full bucket scan |
| `SCAN_TIMEOUT` | `30m` | Maximum full-scan elapsed time across slices |
| `SCAN_SLICE` | `5s` | Fair scheduling slice, completed at a whole-key boundary |
| `LEASE` | `2m` | Scan and observer lease lifetime |
| `HEARTBEAT` | `15s` | Lease/coverage heartbeat and operation budget |
| `PROGRESS_INTERVAL` | `1s` | Progress persistence cadence |
| `POLL_INTERVAL` | `1s` | Queue and event flush cadence |
| `EVENT_DEBOUNCE` | `5s` | Combine bursts of mutation events |
| `MIN_SCAN_INTERVAL` | `1m` | Minimum spacing for automatic rescans; manual refresh bypasses it |
| `RECONCILE_INTERVAL` | `15m` | Cheap new-bucket inventory check |
| `FULL_RECONCILE_INTERVAL` | `24h` | Full safety-net scan, independent of immediate event/refresh work |
| `RETRY_INTERVAL`, `MAX_RETRY_INTERVAL` | `30s`, `15m` | Exponential retry bounds |
| `AUTH_CONCURRENCY` | 4 | Caller permission probes per API request |
| `API_MAX_REQUESTS` | 8 | Concurrent usage API requests per Console process |
| `REQUEST_TIMEOUT` | `15s` | Usage API deadline |
| `UI_POLL_INTERVAL` | `2s` | Pending-work status polling; idle views poll at ten times this interval, capped at one minute |
{.wide .expand}

Entry counts, scan duration, concurrency and request budgets have validated
finite ranges; see `pkg/usage/config.go`. Scan limits preserve the last successful
observation and expose `limited`. Automatic retries, change events and
reconciliation do not restart a limited scan, because it would only reach the
same limit again. After raising the configured budget, or to retry at any time,
use **Refresh**: an explicit refresh discards the limited scan's checkpoint and
starts a new scan with a new time and entry budget. A smaller foreground prefix
also works. An error, outage or scan limit is never a zero.

`POST /api/v1/bucket-usage/status` returns saved observations and coverage.
`POST /api/v1/bucket-usage/refresh` queues priority work and returns HTTP 202.
Both accept `{"buckets":["example-bucket"]}` with at most 1000 names. The frontend
batches larger inventories. They use the normal authenticated Console session,
not the worker identity. Exact byte values remain decimal strings.

The internal worker exposes `/health` for process liveness, `/ready` for the
leased event observer and reconciled connection, and `/metrics` for coverage,
queue counts, failures, limits and oldest pending age. These ports must remain
internal. A live process is not necessarily a healthy change observer.

Run the real PostgreSQL tests with `go test -tags=integration ./pkg/usage` and the
native SILO/authorization checks with
`go test -tags=integration,storageintegration ./pkg/usage ./api -run TestNative`.
Set `TEST_USAGE_DATABASE_URL`, `TEST_USAGE_S3_ENDPOINT`,
`TEST_USAGE_S3_ACCESS_KEY` and `TEST_USAGE_S3_SECRET_KEY` to disposable fixtures;
missing setup fails these explicit suites. Fixtures create and remove their own
buckets and IAM identities; never run them against operator data. Frontend
`e2e/bucket-usage-refresh.unit.ts` mounts the real hook and usage components in a
browser and covers queue/progress/completion, errors, navigation and precision.

The design follows [S3 event notification guidance](https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventNotifications.html)
and [event ordering/duplicate handling](https://aws.amazon.com/blogs/storage/manage-event-ordering-and-duplicate-events-with-amazon-s3-event-notifications/):
notifications trigger idempotent work, while reconciliation repairs delivery gaps.

### Creation failures and quota precision (development) {#creation-and-quota}

The unreleased creation handler rejects invalid quota and retention values before
creating a bucket. Retention alone enables object locking and versioning; an
explicit versioning object is optional. Object locking cannot exclude prefixes
or folders from versioning, so a request that combines locking or retention with
versioning exclusions is rejected before any bucket is created. If a requested
post-create setting fails,
the API reports failure and attempts to remove the empty bucket. It never deletes
objects as part of this rollback. If the caller cannot remove the bucket, or the
bucket has become nonempty, the error explicitly says it may still exist. Inspect
its configuration before retrying; an HTTP error is not proof that no bucket was
created.

Console quota writes must be positive and below 8 PiB (at most
9007199254740991 bytes), with at most two decimal places in the selected unit.
Decimal scaling uses integer arithmetic and discards only fractional bytes.
Larger quotas remain supported through mcli and the existing integer API. The
browser does not populate an editable value from a quota outside its exact JSON
integer range, so reopening and saving cannot silently rewrite a rounded value.
The UI still permits clearing that quota or explicitly entering a smaller one.
Display-only capacity totals may be rounded; use mcli when exact large byte
values matter.

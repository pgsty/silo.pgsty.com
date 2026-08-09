---
title: "Object Scanner"
url: "/operations/concepts/scanner/"
weight: 50
minio_origin: true
silo_modified: true
---

<a id="object-scanner"></a>
<a id="minio-concepts-scanner"></a>

## Overview {#overview}

MinIO uses the built-in scanner to check objects for healing and to take any scheduled object actions. Such actions may include:

- calculate data usage on drives
- evaluate and apply configured [lifecycle management](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management) or [object retention](/administration/object-management/object-retention/#minio-object-retention) rules
- perform [bucket](/administration/bucket-replication/#minio-bucket-replication) or [site](/operations/replication/multi-site-replication/#minio-site-replication-overview) replication
- check objects for missing or corrupted data or parity shards and perform [healing](/operations/concepts/healing/#minio-concepts-healing)

The scanner performs these functions at two levels: cluster and bucket. At the cluster level, the scanner splits all buckets into groups and scans one group of buckets at a time. The scanner starts with any new buckets added since the last scan, then randomizes the scanning of other buckets. The scanner completes checks on all bucket groups before starting over with a new set of scans.

At the bucket level, the scanner groups items in buckets and scans selected items from that bucket. The scanner selects objects for a scan based on a hash of the object name. Over a span of 16 scans, MinIO checks every object in the namespace. MinIO fully scans any prefixes known to be new since the last scan.

## Scan Length {#scan-length}

Multiple factors impact the time it takes for a scan to complete.

Some of these factors include:

- Type of drives provided to MinIO
- Throughput and <abbr title="input/output operations per second">iops</abbr> available
- Number and size of objects
- Other activity on the MinIO Server

For example, by default, MinIO pauses the scanner to make I/O operations available for read and write requests. This can lengthen the time it takes for a scan to complete.

MinIO waits between each scan by a factor multiplication of the time it takes each scan operation to complete. By default, the value of this factor is `10.0`, meaning MinIO waits 10x the length of an operation after one scan completes before starting the next scan. The value of this factor changes depending on the configured [scanner speed setting](/reference/minio-server/settings/core/#minio-scanner-speed-options).

## Scanner Performance {#scanner-performance}

Many factors impact the scanner performance. Some of these factors include:

- available node resources
- size of the cluster
- number of erasure sets compared to the number of drives
- complexity of bucket hierarchy (objects and prefixes).

For example, a cluster that starts with 100TB of data and then grows to 200TB of data may require more time to scan the entire namespace of buckets and objects given the same hardware and workload. Likewise, a single erasure set of 16 drives takes longer to scan than the same number of drives split into two erasure sets of 8 drives each.

MinIO treats the scanner as a background task and pauses it in favor of completing read and write requests on the cluster. As the cluster or workload increases, scanner performance decreases as it yields more frequently to ensure priority of normal S3 operations.

You can adjust how MinIO balances the scanner performance with read/write operations using either the [`MINIO_SCANNER_SPEED`](/reference/minio-server/settings/core/#envvar.MINIO_SCANNER_SPEED) environment variable or the [`scanner speed`](/reference/minio-server/settings/core/#mc-conf.scanner.speed) configuration setting.

## Scanner Metrics {#scanner-metrics}

MinIO provides a number of [metrics related to the scanner](https://silo.pgsty.com/operations/monitoring/metrics-v2/#scanner-metrics).

Use `mc admin scanner info` to see the current status of the scanner and the time since the last full scan. This can help in understanding the metrics provided by the scanner operation.

Scanner metrics, including usage metrics, reflect the last completed scan. `PUT` or `DELETE` operations since the last scan do not update in the usage until the next scan of the affected bucket(s).

The output resembles the following:

```text
Overall Statistics
------------------
Last full scan time:   0d0h14m; Estimated 2885.28/month
Current cycle:         70464; Started: 2024-04-19 20:02:34.568479139 +0000 UTC
Active drives:         2

Last Minute Statistics
----------------------
Objects Scanned:       620 objects; Avg: 124.929µs; Rate: 892800/day
Versions Scanned:      620 versions; Avg: 2.801µs; Rate: 892800/day
Versions Heal Checked: 0 versions; Avg: 0ms
Read Metadata:         621 objects; Avg: 88.416µs, Size:
ILM checks:            656 versions; Avg: 663ns
Check Replication:     656 versions; Avg: 1.061µs
Verify Deleted:        0 folders; Avg: 0ms
Yield:                 3.086s total; Avg: 4.705ms/obj
```

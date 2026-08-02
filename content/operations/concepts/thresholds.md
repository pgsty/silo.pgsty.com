---
title: "Thresholds and Limits"
url: "/operations/concepts/thresholds/"
weight: 60
minio_origin: true
silo_modified: false
math: true
---

<a id="thresholds-and-limits"></a>
<a id="minio-server-limits"></a>

This page reflects limits and thresholds that apply to MinIO.

Refer to the [hardware](/operations/checklists/hardware/#minio-hardware-checklist) and [software](/operations/checklists/software/#minio-software-checklists) for related recommendations and requirements.

## S3 API Limits {#s3-api-limits}

<table>
  <thead>
    <tr>
      <th><p>Item</p></th>
      <th><p>Specification</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p>Maximum object size</p></td>
      <td><p>50 TiB</p></td>
    </tr>
    <tr>
      <td><p>Minimum object size</p></td>
      <td><p>0 B</p></td>
    </tr>
    <tr>
      <td><p>Maximum object size per PUT operation</p></td>
      <td>5 TiB for non-multipart upload<br />50 TiB for multipart upload<br /></td>
    </tr>
    <tr>
      <td><p>Maximum number of parts per upload</p></td>
      <td><p>10,000</p></td>
    </tr>
    <tr>
      <td><p>Part size range</p></td>
      <td><p>5 MiB to 5 GiB. Last part can be 0 B to 5 GiB</p></td>
    </tr>
    <tr>
      <td><p>Maximum number of parts returned per list parts request</p></td>
      <td><p>10,000</p></td>
    </tr>
    <tr>
      <td><p>Maximum number of objects returned per list objects request</p></td>
      <td><p>1,000</p></td>
    </tr>
    <tr>
      <td><p>Maximum number of multipart uploads returned per list multipart uploads request</p></td>
      <td><p>1,000</p></td>
    </tr>
    <tr>
      <td><p>Maximum length for bucket names</p></td>
      <td><p>63</p></td>
    </tr>
    <tr>
      <td><p>Maximum length for object names</p></td>
      <td><p>1024</p></td>
    </tr>
    <tr>
      <td><p>Maximum length for each <code>/</code> separated segment of an object name</p></td>
      <td><p>255</p></td>
    </tr>
    <tr>
      <td><p>Maximum number of object versions for a unique object</p></td>
      <td><p>10000 (Configurable)</p></td>
    </tr>
  </tbody>
</table>

## Erasure Code Limits {#erasure-code-limits}

| Item | Specification |
| --- | --- |
| Maximum number of servers per cluster | no limit |
| Minimum number of servers | 1 |
| Minimum number of drives per server when server count is 1 | 1 (for <abbr title="Single-Node Single-Drive">SNSD</abbr> deployments, which do not provide additional reliability or availability) |
| Minimum number of drives per server when server count is 2 or more | 1 |
| Maximum number of drives per server | no limit |
| Read quorum | \(N/2\) |
| Write quorum | \((N/2)+1\) |

## Object Name Limitations {#object-name-limitations}

### Filesystem and Operating System Restrictions {#filesystem-and-operating-system-restrictions}

Object Names in MinIO are restricted primarily by the local operating system and filesystem. Windows and some other operating systems restrict file systems with certain special characters, such as `^`, `*`, `|`, `\`, `/`, `&`, `"`, or `;`.

This list is not exhaustive and may not apply to your operating system and filesystem combination.

On Unix-like operating systems, objects with a path name of `.`, `..`, or `/` return an error of `file access denied`.

Consult your operating system vendor or filesystem documentation for a comprehensive list for your situation.

MinIO recommends using a Linux operating system with an XFS based filesystem for production workloads.

### Conflicting Objects {#conflicting-objects}

Applications must assign non-conflicting, unique keys for all objects. This includes avoiding creating objects where the name can collide with that of a parent or sibling object. MinIO returns an empty set for LIST operations at the location of the collision.

For example, the following operations create a namespace conflicts

```
PUT data/invoices/2024/january/vendors.csv
PUT data/invoices/2024/january <- collides with existing object prefix
```

```
PUT data/invoices/2024/january
PUT data/invoices/2024/january/vendors.csv <- collides with existing object
```

While you can perform GET or HEAD operations against these objects, the name collision causes LIST operations to return an empty result set at the `/invoices/2024/january` path.

---
title: "Core Administration Concepts"
url: "/administration/concepts/"
weight: 180
icon: fa-solid fa-diagram-project
minio_origin: true
silo_modified: false
---

<a id="core-administration-concepts"></a>

The following core concepts are fundamental to the administration of MinIO deployments, including but not limited to object retention, encryption, and access management.

## What Is Object Storage? {#what-is-object-storage}

An [object](/administration/object-management/#objects) is binary data, sometimes referred to as a Binary Large OBject (BLOB). Blobs can be images, audio files, spreadsheets, or even binary executable code. Object Storage platforms like MinIO provide dedicated tools and capabilities for storing, retrieving, and searching for blobs.

MinIO Object Storage uses [buckets](/administration/object-management/#buckets) to organize objects. A bucket is similar to a folder or directory in a filesystem, where each bucket can hold an arbitrary number of objects. MinIO buckets provide the same functionality as AWS S3 buckets.

For example, consider an application that hosts a web blog. The application needs to store a variety of blobs, including rich multimedia like videos and images.

MinIO supports multiple levels of nested directories through the feature of `prefixing` to support even the most dynamic object storage workloads.

## How does MinIO determine access to objects? {#how-does-minio-determine-access-to-objects}

MinIO requires the client perform both authentication and authorization for each new operation. [Identity and access management (IAM)](/administration/identity-access-management/#minio-authentication-and-identity-management) is therefore a critical component of a MinIO configuration.

*Authentication* verifies the identity of a connecting client. MinIO requires clients to authenticate using [AWS Signature Version 4 protocol](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) with support for the deprecated Signature Version 2 protocol. Specifically, clients must present a valid access key and secret key to access any S3 or MinIO administrative API, such as `PUT`, `GET`, and `DELETE` operations.

MinIO then checks that authenticated users or clients have *authorization* to perform actions or use resources on the deployment. MinIO uses [Policy-Based Access Control (PBAC)](/administration/identity-access-management/policy-based-access-control/#minio-policy), where each policy describes one or more rules that outline the permissions of a user or group of users. MinIO supports S3-specific [actions](/administration/identity-access-management/policy-based-access-control/#minio-policy-actions) and [conditions](/administration/identity-access-management/policy-based-access-control/#minio-policy-conditions) when creating policies.

By default, MinIO *denies* access to actions or resources not explicitly referenced in a user’s assigned or inherited policies.

MinIO provides an access management feature as part of the software. Alternatively, you can configure MinIO to authenticate with one of several external IAM providers using either [Active Directory/LDAP](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap) or [OpenID/OIDC](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid).

## How does MinIO secure data? {#how-does-minio-secure-data}

MinIO supports methods that encode objects while on drive (encryption-at-rest) and during transition from one location to another (encryption-in-transit, or “in flight”). When enabled, MinIO utilizes [server-side encryption](/administration/server-side-encryption/#minio-encryption-overview) to write objects in an encrypted state. To retrieve and read an encrypted object, the user must have appropriate access privileges and also provide the object’s decryption key.

MinIO supports **Transport Layer Security** (TLS) versions 1.2 and 1.3 encrypting objects. TLS replaces the previously used Secure Socket Layer (SSL) method that has since been deprecated. The TLS standard, maintained by the Internet Engineering Task Force (IETF), provides the standards used by internet communications to support encryption, authentication, and data integrity.

The process of authenticating a user and verifying access to objects is known as the *TLS Handshake*. Once authenticated, TLS provides the cipher to encrypt and then decrypt the transfer of information from the server to the requesting client.

MinIO supports several methods of [Server-Side Encryption](/administration/server-side-encryption/#minio-encryption-overview).

<a id="minio-admin-concepts-organize-objects"></a>

## Can I organize objects in a folder structure within buckets? {#can-i-organize-objects-in-a-folder-structure-within-buckets}

MinIO utilizes a [prefix](/glossary/#term-prefix) method for each object that mimics a folder structure from traditional file systems. Prefixing involves prepending the name of an object with a fixed string.

With prefixes, you do not manually create folders and subfolders. Instead, MinIO looks for the `/` character in the prefix of an object’s name. Each `/` indicates a new folder or subfolder.

Using the object’s name and prefix, MinIO automatically generates a series of folders and subfolders for stored objects. When you use the same prefix string on multiple objects, MinIO identifies those as similar or grouped objects.

For example, an object named `/articles/john.doe/2022-01-02-MinIO-Object-Storage.md` winds up in the `articles` bucket in a folder labeled `john.doe`.

A MinIO object store might resemble the following structure, with three buckets. MinIO automatically generates two folders in the `articles` bucket based on the prefixes for those objects.

```text
/ #root
/images/
   2022-01-02-MinIO-Diagram.png
   2022-01-03-MinIO-Advanced-Deployment.png
   MinIO-Logo.png
/videos/
   2022-01-04-MinIO-Interview.mp4
/articles/
   /john.doe/
      2022-01-02-MinIO-Object-Storage.md
      2022-01-02-MinIO-Object-Storage-comments.json
   /jane.doe/
      2022-01-03-MinIO-Advanced-Deployment.png
      2022-01-02-MinIO-Advanced-Deployment-comments.json
      2022-01-04-MinIO-Interview.md
```

MinIO itself does not limit the number of objects that any specific prefix can contain. However, hardware and network conditions may show performance impacts with large prefixes.

- Deployments with modest or budget-focused hardware should architect their workloads to target 10,000 objects per prefix as a baseline. Increase this target based on benchmarking and monitoring of real world workloads up to what the hardware can meaningfully handle.
- Deployments with high-performance or enterprise-grade [hardware](/operations/checklists/hardware/#deploy-minio-distributed-recommendations) can typically handle prefixes with millions of objects or more.

[MinIO SUBNET](https://min.io/pricing?jmp=docs) Enterprise accounts can utilize yearly architecture reviews as part of the deployment and maintenance strategy to ensure long-term performance and success of your MinIO-dependent projects.

For a deeper discussion on the benefits of limiting prefix contents, see the article on [optimizing S3 performance](https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance.html).

## How can I backup and restore objects on MinIO? {#how-can-i-backup-and-restore-objects-on-minio}

MinIO provides two types of replication to copy an object, its versions, and its metadata from one location to another. You can configure replication at either the [bucket level](/administration/bucket-replication/#minio-bucket-replication) or at the [site level](/operations/replication/multi-site-replication/#minio-site-replication-overview).

- Bucket level replication can function as either one-way, active-passive replication (such as for archival purposes) or as two-way, active-active replication to keep two buckets in sync with each other.
- Site level replication functions as two-way, active-active replication to keep multiple data locations (such as different geographic data centers) in sync with one another.

Besides replication, MinIO provides a mirroring service. [`mc mirror`](/reference/minio-mc/mc-mirror/#command-mc.mirror) copies only the actual object to any other S3 compatible data store, including other MinIO stores. However, versions and metadata do not back up with the [`mc mirror`](/reference/minio-mc/mc-mirror/#command-mc.mirror) command.

{{% alert color="info" %}}
**Exclusive access to drives**

MinIO **requires** *exclusive* access to the drives or volumes provided for object storage. No other processes, software, scripts, or persons should perform *any* actions directly on the drives or volumes provided to MinIO or the objects or files MinIO places on them.

Unless directed by MinIO Engineering, do not use scripts or tools to directly modify, delete, or move any of the data shards, parity shards, or metadata files on the provided drives, including from one drive or node to another. Such operations are very likely to result in widespread corruption and data loss beyond MinIO’s ability to heal.
{{% /alert %}}

## What tools does MinIO provide to manage objects based on speed and frequency of access? {#what-tools-does-minio-provide-to-manage-objects-based-on-speed-and-frequency-of-access}

[Tiering rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering) allow frequently accessed objects to store on hot or warm storage, which is typically more expensive but provides better performance.

Less frequently accessed objects can move to cold storage. Cold storage often exchanges slower performance for a cheaper price.

## How does MinIO protect objects from accidental overwrite or deletion? {#how-does-minio-protect-objects-from-accidental-overwrite-or-deletion}

### Locking {#locking}

Locks, a Write Once Read Many (WORM) mechanism, prevent the deletion or modification of an object. When locked, MinIO retains the objects indefinitely until someone removes the lock or the lock expires.

MinIO provides:

- [legal holds](/administration/object-management/object-retention/#minio-object-locking-legalhold) locks for indefinite retention by all users
- [compliance holds](/administration/object-management/object-retention/#minio-object-locking-compliance) for time-based restrictions for all users
- [governing locks](/administration/object-management/object-retention/#minio-object-locking-governance) for time-based rules for non-privileged users

### Versioning {#versioning}

By default, objects written with the same name (including prefix) overwrite an existing object of the same name. MinIO provides a configuration option to create buckets with versioning enabled. [Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) provides access to various iterations of a uniquely named object as it changes over time. When enabled, MinIO writes mutated objects to a different version than the original, allowing access to both the original object and the newer, changed object.

Additional configurations on the MinIO bucket determine how long to retain older versions of each object in the bucket.

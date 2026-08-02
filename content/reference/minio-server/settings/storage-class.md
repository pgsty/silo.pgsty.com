---
title: "Erasure Code Settings"
url: "/reference/minio-server/settings/storage-class/"
weight: 40
minio_origin: true
silo_modified: false
math: true
---

<a id="erasure-code-settings"></a>
<a id="minio-ec-storage-class"></a>
<a id="minio-server-envvar-storage-class"></a>

This page covers settings that configure the [Erasure Code](/operations/concepts/erasure-coding/#minio-erasure-coding) [parity](/operations/concepts/erasure-coding/#minio-ec-parity) to use for objects written to the MinIO cluster. This impacts how MinIO uses the space on the drive(s) and how MinIO can recover objects stored on lost drives or similar issues.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

<a id="minio-ec-storage-class-standard"></a>

## Standard Storage Class {#standard-storage-class}

{{% alert color="info" %}}
**Note**

*MinIO Storage Classes* are distinct from *AWS Storage Classes*.

AWS Storage Classes refer to the specific storage tier on which to store a given object, such as `hot` or `glacier` storage. MinIO Storage Classes affect the erasure code parity setting used and relate to [Availability and Resiliency](/operations/concepts/availability-and-resiliency/#minio-availability-resiliency) of objects.

For tiering from one type of storage to another, such as for cost management purposes, see [Object Transition (“Tiering”)](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering).
{{% /alert %}}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
#### `MINIO_STORAGE_CLASS_STANDARD` {#envvar.MINIO_STORAGE_CLASS_STANDARD}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
#### `storage_class standard` {#mc-conf.storage_class.standard}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The [parity level](/operations/concepts/erasure-coding/#minio-ec-parity) for the deployment. MinIO shards objects written with the default `STANDARD` storage class using this parity value.

MinIO references the `x-amz-storage-class` header in request metadata for determining which storage class to assign an object. The specific syntax or method for setting headers depends on your preferred method for interfacing with the MinIO server.

Specify the value using `EC:M` notation, where `M` refers to the number of parity blocks to create for the object.

The following table lists the default values based on the [erasure set size](/operations/concepts/erasure-coding/#minio-ec-erasure-set) of the initial server pool in the deployment:

| Erasure Set Size | Default Parity (EC:N) |
| --- | --- |
| 1 | EC:0 |
| 2-3 | EC:1 |
| 4-5 | EC:2 |
| 6 - 7 | EC:3 |
| 8 - 16 | EC:4 |

The minimum supported value is `0`, which indicates no erasure coding protections. These deployments rely entirely on the storage controller or resource for availability / resiliency.

The maximum value depends on the erasure set size of the initial server pool in the deployment, where the upper bound is \(\frac{\text{ERASURE\_SET\_SIZE}}{2}\). For example, a deployment with erasure set stripe size of 16 has a maximum standard parity of 8.

You can change this value after startup to any value between `0` and the upper bound for the erasure set size. MinIO only applies the changed parity to newly written objects. Existing objects retain the parity value in place at the time of their creation.

## Reduced Redundancy Storage Class {#reduced-redundancy-storage-class}

{{% alert color="info" %}}
**Note**

*MinIO Storage Classes* are distinct from *AWS Storage Classes*.

AWS Storage Classes refer to the specific storage tier on which to store a given object, such as `hot` or `glacier` storage. MinIO Storage Classes affect the erasure code parity setting used and relate to [Availability and Resiliency](/operations/concepts/availability-and-resiliency/#minio-availability-resiliency) of objects.

For tiering from one type of storage to another, such as for cost management purposes, see [Object Transition (“Tiering”)](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering).
{{% /alert %}}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
#### `MINIO_STORAGE_CLASS_RRS` {#envvar.MINIO_STORAGE_CLASS_RRS}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
#### `storage_class rrs` {#mc-conf.storage_class.rrs}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The [parity level](/operations/concepts/erasure-coding/#minio-ec-parity) for objects written with the `REDUCED` storage class.

MinIO references the `x-amz-storage-class` header in request metadata for determining which storage class to assign an object. The specific syntax or method for setting headers depends on your preferred method for interfacing with the MinIO server.

Specify the value using `EC:M` notation, where `M` refers to the number of parity blocks to create for the object.

This value **must be** less than or equal to [`MINIO_STORAGE_CLASS_STANDARD`](#envvar.MINIO_STORAGE_CLASS_STANDARD).

You cannot set this value for deployments with an erasure set size less than 2. Defaults to `EC:1` for deployments with erasure set size greater than 1. Defaults to `EC:0` for deployments of erasure set size of 1.

## Parity Retention Optimization {#parity-retention-optimization}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
#### `MINIO_STORAGE_CLASS_OPTIMIZE` {#envvar.MINIO_STORAGE_CLASS_OPTIMIZE}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
#### `storage_class optimize` {#mc-conf.storage_class.optimize}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

MinIO by default automatically “upgrades” parity for an object if the destination erasure set maintains write quorum *but* has one or more drives offline. This behavior helps ensure that the given object maintains the same availability as objects written to the healthy erasure set.

Specify `capacity` to this setting to direct MinIO to not create any additional parity for the object. This prioritizes the overall capacity of the cluster at the cost of potentially reduced object availability in the event more drives in that erasure set fail.

## Comment {#comment}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
#### `MINIO_STORAGE_CLASS_COMMENT` {#envvar.MINIO_STORAGE_CLASS_COMMENT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

Adds a comment to the storage class settings.

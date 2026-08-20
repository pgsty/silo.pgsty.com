---
title: "Root Access Settings"
url: "/reference/minio-server/settings/root-credentials/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-server/settings/root-credentials.rst
upstream_modified: true
---

<a id="root-access-settings"></a>
<a id="minio-server-envvar-root"></a>

This page covers settings that control root (superuser) access for the MinIO process. The root user has complete access and permissions to perform operations on the MinIO deployment.

Root User and Root Password are required even if you use the [MinIO Key Encryption Service](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/_index.md) or other key management utility.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

> [!WARNING]
> **Important**
>
> Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.

## Root User {#root-user}

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_ROOT_USER` {#envvar.MINIO_ROOT_USER}

*envvar*

The access key for the [root](/administration/identity-access-management/minio-user-management/#minio-users-root) user.

> [!CAUTION]
> **Warning**
>
> If [`MINIO_ROOT_USER`](#envvar.MINIO_ROOT_USER) is unset, [`minio`](/reference/minio-server/#command-minio) defaults to `minioadmin`.
>
> **NEVER** use the default credentials in production environments. MinIO strongly recommends specifying a unique, long, and random [`MINIO_ROOT_USER`](#envvar.MINIO_ROOT_USER) value for all environments.
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration variable setting. Use the Environment Variable instead.
{{< /tab >}}
{{< /tabs >}}

## Root Password {#root-password}

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_ROOT_PASSWORD` {#envvar.MINIO_ROOT_PASSWORD}

*envvar*

The secret key for the [root](/administration/identity-access-management/minio-user-management/#minio-users-root) user.

> [!CAUTION]
> **Warning**
>
> If [`MINIO_ROOT_PASSWORD`](#envvar.MINIO_ROOT_PASSWORD) is unset, [`minio`](/reference/minio-server/#command-minio) defaults to `minioadmin`.
>
> **NEVER** use the default credentials in production environments. MinIO strongly recommends specifying a unique, long, and random [`MINIO_ROOT_PASSWORD`](#envvar.MINIO_ROOT_PASSWORD) value for all environments.
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration variable setting. Use the Environment Variable instead.
{{< /tab >}}
{{< /tabs >}}

<a id="minio-disable-root-access"></a>

## Root Access {#root-access}

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_API_ROOT_ACCESS` {#envvar.MINIO_API_ROOT_ACCESS}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
#### `api root-access` {#mc-conf.api.root-access}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

> [!NOTE]
> **Added: MinIO**
>
> Server RELEASE.2023-05-04T21-44-30Z

Specify `on` to enable and `off` to disable the [root](/administration/identity-access-management/minio-user-management/#minio-users-root) user account. Disabling the root service account also disables all service accounts associated with root, excluding those used by site replication. Defaults to `on`.

> [!WARNING]
> **Important**
>
> If you disable root API access with this setting, you **must** still set a root user and a root password for internal use.

Ensure you have at least one other admin user, such as one with the [`consoleAdmin`](/administration/identity-access-management/policy-based-access-control/#userpolicy.consoleAdmin) policy, before disabling the root account. If you do not have another admin user, disabling the root account locks administrative access to the deployment.

You can use this variable to temporarily override the configuration setting and re-enable root access to the deployment.

To reset after an unintentional lock, set [`MINIO_API_ROOT_ACCESS`](#envvar.MINIO_API_ROOT_ACCESS) `on` to override this setting and temporarily re-enable the root account. You can then change this setting to `on` *or* make the necessary user/policy changes to ensure normal administrative access through other non-root accounts.

## Unique Root Credentials {#unique-root-credentials}

> [!NOTE]
> **Added: Server**
>
> RELEASE.2024-03-03T17-50-39Z
>
> MinIO automatically generates unique root credentials if all of the following conditions are true:
>
> - [KES](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/tutorials/getting-started.md) Release 2024-03-01T18-06-46Z or later running
> - **Have not** defined:
>
>   - `MINIO_ROOT_USER` variable
>   - `MINIO_ROOT_PASSWORD` variable
> - **Have**:
>
>   - set up KES with a [supported KMS target](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/_index.md#supported-kms-targets)
>   - disabled root access with the [MinIO environment variable](#minio-disable-root-access)
>
> When those conditions are met at startup, MinIO uses the KMS to generate unique root credentials for the deployment using a [hash-based message authentication code (HMAC)](https://en.wikipedia.org/wiki/HMAC).
>
> If MinIO generates such credentials, the key used to generate the credentials **must** remain the same *and* continue to exist. All data on the deployment is encrypted with this key!
>
> To rotate the generated root credentials, generate a new key in the KMS, then update the value of the [`MINIO_KMS_KES_KEY_NAME`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME) with the new key.

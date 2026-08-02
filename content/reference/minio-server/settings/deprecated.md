---
title: "Deprecated Settings"
url: "/reference/minio-server/settings/deprecated/"
weight: 120
minio_origin: true
silo_modified: false
---

<a id="deprecated-settings"></a>
<a id="minio-server-envvar-deprecated"></a>

This page covers deprecated settings that control core behavior of the MinIO process.

Settings on this page may be removed at any time. Users should migrate to the recommended replacement at the earliest opportunity.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

## Environment Variables {#environment-variables}

The following *environment variables* are deprecated. They are listed here for historical reference only.

#### `MINIO_SECRET_KEY` {#envvar.MINIO_SECRET_KEY}

*envvar*

{{% alert color="danger" %}}
**Deprecated: RELEASE.2021-04-22T15-44-28Z**

{{% /alert %}}

The secret key for the [root](/administration/identity-access-management/minio-user-management/#minio-users-root) user.

This environment variable is *deprecated* in favor of the [`MINIO_ROOT_PASSWORD`](/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_PASSWORD) environment variable.

{{% alert color="danger" %}}
**Warning**

If [`MINIO_SECRET_KEY`](#envvar.MINIO_SECRET_KEY) is unset, [`minio`](/reference/minio-server/#command-minio) defaults to `minioadmin`.

**NEVER** use the default credentials in production environments. MinIO strongly recommends specifying a unique, long, and random [`MINIO_ACCESS_KEY`](#envvar.MINIO_ACCESS_KEY) value for all environments.
{{% /alert %}}

#### `MINIO_ACCESS_KEY` {#envvar.MINIO_ACCESS_KEY}

*envvar*

{{% alert color="danger" %}}
**Deprecated: RELEASE.2021-04-22T15-44-28Z**

{{% /alert %}}

The access key for the [root](/administration/identity-access-management/minio-user-management/#minio-users-root) user.

> This environment variable is *deprecated* in favor of the [`MINIO_ROOT_USER`](/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_USER) environment variable.

{{% alert color="danger" %}}
**Warning**

If [`MINIO_ACCESS_KEY`](#envvar.MINIO_ACCESS_KEY) is unset, [`minio`](/reference/minio-server/#command-minio) defaults to `minioadmin`.

**NEVER** use the default credentials in production environments. MinIO strongly recommends specifying a unique, long, and random [`MINIO_ACCESS_KEY`](#envvar.MINIO_ACCESS_KEY) value for all environments.
{{% /alert %}}

#### `MINIO_ACCESS_KEY_OLD` {#envvar.MINIO_ACCESS_KEY_OLD}

*envvar*

{{% alert color="danger" %}}
**Deprecated: RELEASE.2021-04-22T15-44-28Z**

{{% /alert %}}

To perform root credential rotation, modify the [`MINIO_ROOT_USER`](/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_USER) and [`MINIO_ROOT_PASSWORD`](/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_PASSWORD) environment variables.

#### `MINIO_OPERATOR_DEPLOYMENT_NAME` {#envvar.MINIO_OPERATOR_DEPLOYMENT_NAME}

*envvar*

{{% alert color="danger" %}}
**Deprecated: Operator**

6.0.4
{{% /alert %}}

Specifies the namespace to create and use for Operator.

When not specified, the default value is `minio-operator`.

#### `MINIO_SECRET_KEY_OLD` {#envvar.MINIO_SECRET_KEY_OLD}

*envvar*

{{% alert color="danger" %}}
**Deprecated: RELEASE.2021-04-22T15-44-28Z**

{{% /alert %}}

To perform root credential rotation, modify the [`MINIO_ROOT_USER`](/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_USER) and [`MINIO_ROOT_PASSWORD`](/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_PASSWORD) environment variables.

#### `MINIO_SERVER_URL` {#envvar.MINIO_SERVER_URL}

*envvar*

{{% alert color="danger" %}}
**Deprecated: RELEASE.2024-05-10T01-41-38Z**

{{% /alert %}}

The [fully qualified domain name](https://en.wikipedia.org/wiki/Fully_qualified_domain_name) (FQDN) the MinIO Console uses for connecting to the MinIO Server.

For the Console to function correctly, the MinIO server URL *must* be the FQDN of the host, resolveable, and reachable.

If the specified value does not resolve to the MinIO server, logins via the MinIO Console fail and return a network error after a wait period. Older versions of the Console may return a generic ‘Invalid Login’ error instead. Unset the value *or* address the FQDN resolution issue to allow Console logins to proceed. This setting may be required if:

- The MinIO Server uses a TLS certificate that does not include the host local IP(s) in the certificate Subject Alternative Name (SAN).

or

- The Console must use a specific hostname to connect or reference the MinIO Server, such as due to a reverse proxy or similar configuration.

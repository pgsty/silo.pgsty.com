---
title: "Silo Console"
url: "/administration/minio-console/"
weight: 110
icon: fa-solid fa-display
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/minio-console.rst
upstream_modified: true
---

<a id="minio-console"></a>
<a id="id1" data-td-print-local></a>

The MinIO Console is a rich graphical user interface that provides similar functionality to the [`mc`](/reference/minio-mc/#command-mc) command line tool.

![Silo Console Landing Page provides a view of the Object Browser for the authenticated user](/images/silo-console/console-object-browser.webp){width="600"}

This page provides an overview of the MinIO Console and describes configuration options and instructions for logging in.

## Overview {#overview}

You can use the MinIO Console for administration tasks like Identity and Access Management, Metrics and Log Monitoring, or Server Configuration.

[SILO 20261109](/blog/release/silo-20261109/) embeds [Console v2.7.0](/blog/release/console-2.7.0/) (`4e91ae506e70`). The [Silo Console repository](https://github.com/pgsty/silo-console) documents the downstream source, releases, and compatibility changes; standalone deployment is an advanced integration path and must use a Console version compatible with the target server release.

In [Console v2.7.0](/blog/release/console-2.7.0/), the Console UI provides ten languages (English, Simplified Chinese, French, German, Russian, Spanish, Brazilian Portuguese, Japanese, Arabic with a right-to-left layout, and Turkish), selectable from the language menu or the command palette ([design record](/blog/design/console-languages/)). Console serves interactive API documentation with Redoc 3 at `/api/v1/docs`, where `/swagger.json` routes directly to the API instead of the frontend SPA fallback. Standalone `docker.io/pgsty/silo-console:v2.7.0` includes the UBI system CA bundle (`/etc/ssl/certs/ca-certificates.crt`) and a writable `/tmp` directory (`1777`) for outbound HTTPS and temporary file operations.

### Supported Browsers {#supported-browsers}

MinIO Console runs on a variety of current, stable release browsers.

For the best experience in the MinIO Console, use the latest stable release of your preferred browser. Some browsers that are supported include:

- Chrome
- Edge
- Safari
- Firefox
- Opera

This list is *not* exhaustive and is subject to change.

For a full list of browsers and versions for running MinIO Console, see the [Browserslist](https://browsersl.ist/#q=%3E0.2%25%2Cnot+dead+and+not+op_mini+all) website.

> [!NOTE]
> **Tip**
>
> MinIO Console does *not* support Opera Mini.

## Configuration {#configuration}

The MinIO Console inherits the majority of its configuration settings from the MinIO Server. The following environment variables enable specific behavior in the MinIO Console:

<table>
  <thead>
    <tr>
      <th><p>Environment Variable</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-server/settings/console/#envvar.MINIO_PROMETHEUS_URL"><code>MINIO_PROMETHEUS_URL</code></a></p></td>
      <td><p>The URL for a Prometheus server configured to scrape metrics from the
MinIO deployment. The MinIO Console uses this server for populating the
metrics dashboard.</p><p>See <a href="/operations/monitoring/collect-minio-metrics-using-prometheus/#minio-metrics-collect-using-prometheus">Monitoring and Alerting using Prometheus</a> for a tutorial on
configuring Prometheus to collect metrics from MinIO.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-server/settings/console/#envvar.MINIO_BROWSER_REDIRECT_URL"><code>MINIO_BROWSER_REDIRECT_URL</code></a></p></td>
      <td><p>The externally resolvable hostname for the MinIO Console used by the
configured <a href="/administration/identity-access-management/#minio-authentication-and-identity-management">external identity manager</a> for returning the
authentication response.</p><p>This variable is typically necessary when using a reverse proxy,
load balancer, or similar system to expose the MinIO Console to the
public internet. Specify an externally reachable hostname that resolves
to the MinIO Console.</p></td>
    </tr>
  </tbody>
</table>

<a id="minio-console-port-assignment"></a>

### Static vs Dynamic Port Assignment {#static-vs-dynamic-port-assignment}

MinIO by default selects a random port for the MinIO Console on each server startup. Browser clients accessing the MinIO Server are automatically redirected to the MinIO Console on its dynamically selected port. This behavior emulates the legacy web browser behavior while reducing the risk of a port collision on systems which were running MinIO *before* the embedded Console update.

You can select an explicit static port by passing the [`silo server --console-address`](/reference/minio-server/#minio.server.-console-address) commandline option when starting each MinIO Server in the deployment.

For example, the following command starts a distributed MinIO deployment using a static port assignment of `9001` for the MinIO Console. This deployment would respond to S3 API operations on the default MinIO server port `:9000` and browser access on the MinIO Console port `:9001`.

```shell
silo server https://minio-{1...4}.example.net/mnt/drive-{1...4} \
      --console-address ":9001"
```

Deployments behind network routing components which require static ports for routing rules may require setting a static MinIO Console port. For example, load balancers, reverse proxies, or Kubernetes ingress may by default block or exhibit unexpected behavior with the dynamic redirection behavior.

You must also ensure that the host system firewall grants access to the configured Console port.

<a id="minio-console-play-login"></a>

## Logging In {#logging-in}

> [!NOTE]
> **Changed: RELEASE.2023-03-09T23-16-13Z**

The MinIO Console displays a login screen for unauthenticated users. The Console defaults to providing a username and password prompt for a [MinIO-managed user](/administration/identity-access-management/minio-identity-management/#minio-internal-idp).

For deployments configured with multiple [identity managers](/administration/identity-access-management/#minio-authentication-and-identity-management), select the **Other Authentication Methods** dropdown to select one of the other configured identity providers. You can also log in using credentials generated using a [Security Token Service (STS)](/developers/security-token-service/#minio-security-token-service) API.

> [!NOTE]
> **Evaluate the Console locally with `docker.io/pgsty/silo`**
>
> Run a disposable local container to test the embedded Console:
>
> ```shell
> docker run --rm -p 9000:9000 -p 9001:9001 \
>   -e MINIO_ROOT_USER=silo-admin \
>   -e MINIO_ROOT_PASSWORD=change-me-strong-secret \
>   docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z \
>   server /data --console-address ":9001"
> ```
>
> Open `http://127.0.0.1:9001` in a browser and sign in with the configured root credentials. You can also connect [`mc`](/reference/minio-mc/#command-mc) (`mcli`) to `http://127.0.0.1:9000`.

## Documentation {#documentation}

The **Documentation** link opens this documentation site in a separate browser tab using locale-aware routing: Simplified Chinese opens `/zh/` pages, and all other UI languages open the English documentation. Console also exposes Redoc 3 API documentation at `/api/v1/docs` (backed by `/swagger.json`).

## Available Tasks {#available-tasks}

Once logged in to the MinIO Console, users can perform many kinds of tasks.

- [Manage objects](/administration/console/managing-objects/#minio-console-managing-objects) by browsing or uploading objects, managing bucket settings, or creating tiers.
- [Review or modify identity and security](/administration/console/security-and-access/#minio-console-security-access) with access keys, policies, and Identity Provider settings.
- [Monitor the health and activities](/administration/console/managing-deployment/#minio-console-managing-deployment) with metrics, notifications, or site replication.
- [Run local diagnostics and download health reports](/administration/console/subnet-registration/#minio-console-subscription) without external telemetry or commercial subscription registration.

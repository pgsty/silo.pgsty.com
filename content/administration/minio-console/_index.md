---
title: "Silo Console"
url: "/administration/minio-console/"
weight: 110
icon: fa-solid fa-display
minio_origin: true
silo_modified: true
---

<a id="minio-console"></a>
<a id="id1"></a>

The MinIO Console is a rich graphical user interface that provides similar functionality to the [`mc`](/reference/minio-mc/#command-mc) command line tool.

<img src="/images/silo-console/console-object-browser.webp" alt="MinIO Console Landing Page provides a view of the Object Browser for the authenticated user" style="max-width: 600px; height: auto;" />

This page provides an overview of the MinIO Console and describes configuration options and instructions for logging in.

## Overview {#overview}

You can use the MinIO Console for administration tasks like Identity and Access Management, Metrics and Log Monitoring, or Server Configuration.

SILO embeds the maintained Silo Console in the server. The [Silo Console repository](https://github.com/pgsty/silo-console) documents the downstream source, releases, and compatibility changes; standalone deployment is an advanced integration path and must use a Console version compatible with the target server release.

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

{{% alert color="secondary" %}}
**Tip**

MinIO Console does *not* support Opera Mini.
{{% /alert %}}

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

You can select an explicit static port by passing the [`minio server --console-address`](/reference/minio-server/#minio.server.-console-address) commandline option when starting each MinIO Server in the deployment.

For example, the following command starts a distributed MinIO deployment using a static port assignment of `9001` for the MinIO Console. This deployment would respond to S3 API operations on the default MinIO server port `:9000` and browser access on the MinIO Console port `:9001`.

```shell
minio server https://minio-{1...4}.example.net/mnt/drive-{1...4} \
      --console-address ":9001"
```

Deployments behind network routing components which require static ports for routing rules may require setting a static MinIO Console port. For example, load balancers, reverse proxies, or Kubernetes ingress may by default block or exhibit unexpected behavior with the dynamic redirection behavior.

You must also ensure that the host system firewall grants access to the configured Console port.

<a id="minio-console-play-login"></a>

## Logging In {#logging-in}

{{% alert color="info" %}}
**Changed: RELEASE.2023-03-09T23-16-13Z**

{{% /alert %}}

The MinIO Console displays a login screen for unauthenticated users. The Console defaults to providing a username and password prompt for a [MinIO-managed user](/administration/identity-access-management/minio-identity-management/#minio-internal-idp).

For deployments configured with multiple [identity managers](/administration/identity-access-management/#minio-authentication-and-identity-management), select the **Other Authentication Methods** dropdown to select one of the other configured identity providers. You can also log in using credentials generated using a [Security Token Service (STS)](/developers/security-token-service/#minio-security-token-service) API.

{{% alert color="info" %}}
**Try out the Console using MinIO’s Play testing environment**

You can explore the Console using [https://play.min.io:9443](https://play.min.io:9443). Log in with the following credentials:

- Username: `Q3AM3UQ867SPQQA43P2F`
- Password: `zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG`

The Play Console connects to the MinIO Play deployment at [https://play.min.io](https://play.min.io). You can also access this deployment using [`mc`](/reference/minio-mc/#command-mc) and using the `play` alias.
{{% /alert %}}

## Documentation {#documentation}

The **Documentation** tab opens this documentation site in a separate browser window or tab.

## Available Tasks {#available-tasks}

Once logged in to the MinIO Console, users can perform many kinds of tasks.

- [Manage objects](/administration/console/managing-objects/#minio-console-managing-objects) by browsing or uploading objects, managing bucket settings, or creating tiers.
- [Review or modify identity and security](/administration/console/security-and-access/#minio-console-security-access) with access keys, policies, and Identity Provider settings.
- [Monitor the health and activities](/administration/console/managing-deployment/#minio-console-managing-deployment) with metrics, notifications, or site replication
- [Manage your deployment’s license](/administration/console/subnet-registration/#minio-console-subscription)

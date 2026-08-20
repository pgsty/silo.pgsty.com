---
title: "mc support proxy"
url: "/reference/minio-mc/mc-support-proxy/"
weight: 60
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-proxy.rst
upstream_modified: false
---

<a id="mc-support-proxy"></a>

<a id="command-mc.support.proxy"></a>

## Description {#description}

Use the [`mc support proxy`](#command-mc.support.proxy) command to configure a proxy to use to communicate with [MinIO SUBNET](https://min.io/pricing?jmp=docs).

## Examples {#examples}

### Set a Proxy URL {#set-a-proxy-url}

Define the proxy URL to use when the deployment `minio1` communicates to SUBNET. The proxy URL in the example is `http://my.proxy`.

```shell
mc support proxy set minio1 http://my.proxy
```

### Remove the Proxy URL Configured for a Deployment {#remove-the-proxy-url-configured-for-a-deployment}

The following command removes the URL configured as the proxy for the alias `minio1`.

```shell
mc support proxy remove minio1
```

### Disable `callhome` Logs {#disable-callhome-logs}

The following command shows the URL configured as the proxy for the alias `minio1`.

```shell
mc support proxy show minio1
```

## Syntax {#syntax}

#### `mc support proxy set` {#mc.support.proxy.set}

*mc-cmd*

Create a proxy URL for the MinIO deployment to use when communicating with [MinIO SUBNET](https://min.io/pricing?jmp=docs).

```shell
mc support proxy set ALIAS PROXY_URL
```

#### `mc support proxy show` {#mc.support.proxy.show}

*mc-cmd*

Display the current proxy URL configured for communicating with [MinIO SUBNET](https://min.io/pricing?jmp=docs).

```shell
mc support proxy show ALIAS
```

#### `mc support proxy remove` {#mc.support.proxy.remove}

*mc-cmd*

Remove the proxy URL configured for communicating with [MinIO SUBNET](https://min.io/pricing?jmp=docs).

```shell
mc support proxy remove ALIAS
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

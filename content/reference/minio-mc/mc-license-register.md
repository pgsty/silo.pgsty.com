---
title: "mc license register"
url: "/reference/minio-mc/mc-license-register/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="mc-license-register"></a>

<a id="command-mc.support.register"></a>

<a id="command-mc.license.register"></a>

{{% alert color="warning" %}}
**Important**

`mc license register` requires [MinIO Client](/reference/minio-mc/#minio-client) version `RELEASE.2023-11-20T16-30-59Z` or later. While not strictly required, best practice keeps the [MinIO Client version](/reference/minio-mc/#mc-client-versioning) in alignment with the MinIO Server version.
{{% /alert %}}

## Description {#description}

The [`mc license register`](#command-mc.license.register) command connects your deployment with your [MinIO SUBNET](https://min.io/pricing?jmp=docs) account.

After registration, you can upload deployment health reports directly to SUBNET using the [`mc support diag`](/reference/minio-mc/mc-support-diag/#command-mc.support.diag) command.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
> The following example registers the `minio` [alias](/reference/minio-mc/mc-alias-set/#alias) with [MinIO SUBNET](https://min.io/pricing?jmp=docs):

```shell
mc license register minio
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] license register ALIAS                      \
                         [--airgap]                          \
                         [--api-key <string>]                \
                         [--license <path to license file>]  \
                         [--name <value>]
```
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.license.register.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

##### `--airgap` {#mc.license.register.-airgap}

*mc-cmd*

*Optional*

Use in environments without network access to SUBNET (for example, airgapped, firewalled, or similar configuration).

For instructions, see the [airgap example](#minio-license-register-airgap).

If the deployment is airgapped, but the local device where you are using the [minio client](/reference/minio-mc/#minio-client) has network access, you do not need to use the `--airgap` flag.

##### `--api-key` {#mc.license.register.-api-key}

*mc-cmd*

API key of the account on SUBNET.

Corresponds with the `MC_SUBNET_API_KEY` environment variable.

To find the API key:

1. Log in to [MinIO SUBNET](https://min.io/pricing?jmp=docs)
2. Go to the **Deployments** tab
3. Select the **API Key** button near the top of the page on the right side of the account statistics information box
4. Select copy button to the right of the key field to copy the key value to your clipboard

##### `--license` {#mc.license.register.-license}

*mc-cmd*

*Optional*

Path to the license file to use for registering the deployment.

You must first download the license file for the account from [MinIO SUBNET](https://min.io/pricing?jmp=docs).

1. Log in to [MinIO SUBNET](https://min.io/pricing?jmp=docs)
2. Go to the **Deployments** tab
3. Select the **License** button near the top of the page on the right side of the account statistics information box
4. Select the copy button to the right of the license field to copy the key value to your clipboard or select the **Download** button to save a txt file of the license locally

##### `--name` {#mc.license.register.-name}

*mc-cmd*

*Optional*

Specify a name other than the alias to associate to the MinIO deployment in SUBNET.

Use `--name <value>` replacing `<value>` with the name you want to use for the deployment on SUBNET.

## Examples {#examples}

### Register a Deployment Using the Deployment’s Name {#register-a-deployment-using-the-deployment-s-name}

Register the MinIO deployment at alias `minio1` on SUBNET, using `minio1` as the deployment name:

```shell
mc license register minio1
```

If not already registered, a prompt asks for SUBNET credentials for the deployment.

### Register a Deployment Using the Account’s License File {#register-a-deployment-using-the-account-s-license-file}

Register a new MinIO deployment at alias `minio5` on SUBNET, using the license file downloaded for the account:

```shell
mc license register minio5 /path/to/minio.license
```

If not already downloaded, you can download the license file from SUBNET.

1. Log in to [MinIO SUBNET](https://min.io/pricing?jmp=docs)
2. Go to the **Deployments** tab
3. Select the **License** button near the top of the page on the right side of the account statistics information box
4. Select the **Download** button to save a txt file of the license locally

### Register a Deployment with a Different Deployment Name {#register-a-deployment-with-a-different-deployment-name}

Register a MinIO deployment at alias `minio2` on SUBNET, using `second-deployment` as the name:

```shell
mc license register minio2 --name second-deployment
```

<a id="minio-license-register-airgap"></a>

### Register a Deployment Without Direct Internet Access {#register-a-deployment-without-direct-internet-access}

Register a MinIO deployment at alias `minio3` on SUBNET that does not have direct Internet access due to a firewall, airgap, or the like.

{{% alert color="info" %}}
**Changed: mc**

RELEASE.2022-07-29T19-17-16Z

The airgap registration process works with MinIO Client version `RELEASE.2022-07-29T19-17-16Z` or later. Earlier versions of the MinIO Client cannot register an airgapped deployment.
{{% /alert %}}

```shell
mc license register minio3 --airgap
```

1. Run the command to return a registration link with token
2. Open the copied registration link in a web browser and sign in to SUBNET
3. Select the **?** button to the right of the **License** number for the deployment
4. In the popup, select the download link and save the key to a path you have access to
5. In the command line, run the following command

   ```shell
   mc license update minio3 <path-to-file>
   ```

   Replace `<path-to-file>` with the path to the file you downloaded from SUBNET.

## Syntax {#syntax}

The command has the following syntax:

```shell
mc [GLOBALFLAGS] license register       \
                         ALIAS          \
                         [--name value] \
                         [--airgap]
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### Automatic License Updates {#automatic-license-updates}

{{% alert color="info" %}}
**Added: RELEASE.2023-01-18T04-36-38Z**

{{% /alert %}}

Once registered for [MinIO SUBNET](https://min.io/pricing?jmp=docs), MinIO automatically checks for and updates the license every month.

In airgapped or other environments where the server does not have direct access to the internet, use [`mc license update`](/reference/minio-mc/mc-license-update/#command-mc.license.update) with the path to the file to update the registration.

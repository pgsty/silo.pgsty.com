---
title: "MinIO Client"
url: "/reference/minio-mc/"
weight: 10
icon: fa-solid fa-terminal
minio_origin: true
silo_modified: false
---

<a id="minio-client"></a>
<a id="id1"></a>

- [Introduction to the MinIO Client (MC) Commands](https://www.youtube.com/watch?v=pukQgDdXfqA)
- [Installing and Running MinIO on Linux](https://www.youtube.com/watch?v=74usXkZpNt8&list=PLFOIsHSSYIK1BnzVY66pCL-iJ30Ht9t1o)

<a id="command-mc"></a>

The MinIO Client [`mc`](#command-mc) command line tool provides a modern alternative to UNIX commands like `ls`, `cat`, `cp`, `mirror`, and `diff` with support for both filesystems and Amazon S3-compatible cloud storage services.

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

[`mc`](#command-mc) has the following syntax:

```shell
mc [GLOBALFLAGS] COMMAND --help
```

See [Command Quick Reference](#minio-mc-commands) for a list of supported commands.

<a id="mc-client-versioning"></a>

## Version Alignment with MinIO Server {#version-alignment-with-minio-server}

The MinIO Client releases separately from the MinIO Server.

For best functionality and compatibility, use a MinIO Client version released closely to your MinIO Server version. For example, a MinIO Client released the same day or later than your MinIO Server version.

You can install a version of the MinIO Client that is more recent than the MinIO Server version. However, if the MinIO Client version skews too far from the MinIO Server version, you may see increased warnings or errors as a result of the differences. For example, while core S3 APIs around copying ([`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp)) may remain unchanged, some features or flags may only be available or stable if the client and server versions are aligned.

<a id="mc-install"></a>

## Quickstart {#quickstart}

### 1) Install `mc` {#install-mc}

Install the **`mc`** command line tool onto the host machine. Click the tab that corresponds to the host machine operating system or environment:

{{< tabpane text=true persist=header >}}
{{% tab header="Linux" %}}
The following commands add a *temporary* extension to your system PATH for running the `mc` utility. Defer to your operating system instructions for making permanent modifications to your system PATH.

Alternatively, execute `mc` by navigating to the parent folder and running `./mc --help`

**64-bit Intel**

```shell
curl https://dl.min.io/client/mc/release/linux-amd64/mc \
  --create-dirs \
  -o $HOME/minio-binaries/mc

chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries/

mc --help
```

**64-bit PPC**

```shell
curl https://dl.min.io/client/mc/release/linux-ppc64le/mc \
  --create-dirs \
  -o ~/minio-binaries/mc

chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries/

mc --help
```

**ARM64**

```shell
curl https://dl.min.io/client/mc/release/linux-arm64/mc \
  --create-dirs \
  -o ~/minio-binaries/mc

chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries/

mc --help
```

{{% alert color="info" %}}
**Install from the MinIO Download Page**

MinIO does not officially publish its binaries to common Linux repositories or package managers (Ubuntu, RHEL, Archlinux/AUR). The only official source of MinIO binaries is the [MinIO Download Page](https://dl.min.io/client/mc/release/).

MinIO does not recommend installation through a package manager, as upstream repositories may install the incorrect package or a renamed package.

All documentation assumes the installation of the *official* `mc` client binary through the download page *only*, with no changes to binary naming.
{{% /alert %}}
{{% /tab %}}
{{% tab header="macOS" %}}
```shell
brew install minio/stable/mc
mc --help
```
{{% /tab %}}
{{% tab header="Windows" %}}
Open the following file in a browser:

[https://dl.min.io/client/mc/release/windows-amd64/mc.exe](https://dl.min.io/client/mc/release/windows-amd64/mc.exe)

Execute the file by double clicking on it, *or* by running the following in the command prompt or powershell:

```powershell
\path\to\mc.exe --help
```
{{% /tab %}}
{{% tab header="Source" %}}
Installation from source is intended for developers and advanced users and requires a working Golang environment. See [How to install Golang](https://golang.org/doc/install).

Run the following commands in a terminal environment to install `mc` from source:

```shell
go install github.com/minio/mc@latest
```

[`mc update`](/reference/minio-mc/mc-update/#command-mc.update) does not support source-based installations.
{{% /tab %}}
{{< /tabpane >}}

### 2) Create an Alias for the S3-Compatible Service {#create-an-alias-for-the-s3-compatible-service}

{{% alert color="warning" %}}
**Important**

The following example temporarily disables the bash history to mitigate the risk of authentication credentials leaking in plain text. This is a basic security measure and does not mitigate all possible attack vectors. Defer to security best practices for your operating system for inputting sensitive information on the command line.
{{% /alert %}}

Use the [`mc alias set`](/reference/minio-mc/mc-alias-set/#command-mc.alias.set) command to add an Amazon S3-compatible service to the [`mc`](#command-mc) [configuration](#mc-configuration).

```shell
bash +o history
mc alias set ALIAS HOSTNAME ACCESS_KEY SECRET_KEY
bash -o history
```

- Replace `ALIAS` with a name to associate to the S3 service. [`mc`](#command-mc) commands typically require `ALIAS` as an argument for identifying which S3 service to execute against.
- Replace `HOSTNAME` with the URL endpoint or IP address of the S3 service.
- Replace `ACCESS_KEY` and `SECRET_KEY` with the access and secret keys for a user on the S3 service.

Replace each argument with the required values. If you omit the `ACCESS_KEY` and `SECRET_KEY`, the command prompts you to enter those values in the CLI.

Each of the following tabs contains a provider-specific example:

{{< tabpane text=true persist=header >}}
{{% tab header="MinIO Server" %}}
```shell
mc alias set myminio https://minioserver.example.net ACCESS_KEY SECRET_KEY
```
{{% /tab %}}
{{% tab header="AWS S3 Storage" %}}
```shell
mc alias set myS3 https://s3.{your-region-code}.amazonaws.com/endpoint ACCESS_KEY SECRET_KEY
```
{{% /tab %}}
{{% tab header="Google Cloud Storage" %}}
```shell
mc alias set myGCS https://storage.googleapis.com/endpoint ACCESS_KEY SECRET_KEY
```
{{% /tab %}}
{{< /tabpane >}}

### 3) Test the Connection {#test-the-connection}

Use the [`mc admin info`](/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info) command to test the connection to the newly added MinIO deployment:

```shell
mc admin info myminio
```

The command returns information on the S3 service if successful. If unsuccessful, check each of the following:

- The host machine has connectivity to the S3 service URL (i.e. using `ping` or `traceroute`).
- The specified `ACCESSKEY` and `SECRETKEY` correspond to a user on the S3 service. The user must have permission to perform actions on the service.

  For MinIO deployments, see [Access Management](/administration/identity-access-management/#minio-access-management) for more information on user access permissions. For other S3-compatible services, defer to the documentation for that service.

<a id="minio-mc-commands"></a>

## Command Quick Reference {#command-quick-reference}

The following table lists [`mc`](#command-mc) commands:

{{% alert color="info" %}}
**Note**

The MinIO Client also includes an administration extension for managing MinIO deployments. See [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) for more complete documentation.

The below table does not include those commands.
{{% /alert %}}

<table>
  <thead>
    <tr>
      <th><p>Command</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="/reference/minio-mc/mc-alias-list/#command-mc.alias.list"><code>mc alias list</code></a><br /><a href="/reference/minio-mc/mc-alias-remove/#command-mc.alias.remove"><code>mc alias remove</code></a><br /><a href="/reference/minio-mc/mc-alias-set/#command-mc.alias.set"><code>mc alias set</code></a><br /><a href="/reference/minio-mc/mc-alias-import/#command-mc.alias.import"><code>mc alias import</code></a><br /><a href="/reference/minio-mc/mc-alias-export/#command-mc.alias.export"><code>mc alias export</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-alias/#command-mc.alias"><code>mc alias</code></a> commands provide a convenient interface for managing the list of S3-compatible hosts that <a href="#command-mc"><code>mc</code></a> can connect to and run operations against.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-anonymous-get/#command-mc.anonymous.get"><code>mc anonymous get</code></a><br /><a href="/reference/minio-mc/mc-anonymous-get-json/#command-mc.anonymous.get-json"><code>mc anonymous get-json</code></a><br /><a href="/reference/minio-mc/mc-anonymous-links/#command-mc.anonymous.links"><code>mc anonymous links</code></a><br /><a href="/reference/minio-mc/mc-anonymous-list/#command-mc.anonymous.list"><code>mc anonymous list</code></a><br /><a href="/reference/minio-mc/mc-anonymous-set/#command-mc.anonymous.set"><code>mc anonymous set</code></a><br /><a href="/reference/minio-mc/mc-anonymous-set-json/#command-mc.anonymous.set-json"><code>mc anonymous set-json</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-anonymous/#command-mc.anonymous"><code>mc anonymous</code></a> command supports setting or removing anonymous <a href="/administration/identity-access-management/policy-based-access-control/#minio-policy">policies</a> to a bucket and its contents.
Buckets with anonymous policies allow public access where clients can perform any action granted by the policy without <a href="/administration/identity-access-management/#minio-authentication-and-identity-management">authentication</a>.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-batch-describe/#command-mc.batch.describe"><code>mc batch describe</code></a><br /><a href="/reference/minio-mc/mc-batch-generate/#command-mc.batch.generate"><code>mc batch generate</code></a><br /><a href="/reference/minio-mc/mc-batch-list/#command-mc.batch.list"><code>mc batch list</code></a><br /><a href="/reference/minio-mc/mc-batch-start/#command-mc.batch.start"><code>mc batch start</code></a><br /><a href="/reference/minio-mc/mc-batch-status/#command-mc.batch.status"><code>mc batch status</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch/#command-mc.batch"><code>mc batch</code></a> commands allow you to run one or more job tasks on a MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-cat/#command-mc.cat"><code>mc cat</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-cat/#command-mc.cat"><code>mc cat</code></a> command concatenates the contents of a file or
object to another file or object. You can also use the command to
display the contents of the specified file or object to <code>STDOUT</code>.
<a href="/reference/minio-mc/mc-cat/#command-mc.cat"><code>cat</code></a> has similar functionality to <code>cat</code>.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-cp/#command-mc.cp"><code>mc cp</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-cp/#command-mc.cp"><code>mc cp</code></a> command copies objects to or from a MinIO deployment, where
the source can MinIO <em>or</em> a local filesystem.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-diff/#command-mc.diff"><code>mc diff</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-diff/#command-mc.diff"><code>mc diff</code></a> mc computes the differences between two filesystem directories
or MinIO buckets. <a href="/reference/minio-mc/mc-diff/#command-mc.diff"><code>mc diff</code></a> lists only those objects which are missing or
which differ in size. <a href="/reference/minio-mc/mc-diff/#command-mc.diff"><code>mc diff</code></a> does <strong>not</strong> compare the contents of
objects.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-du/#command-mc.du"><code>mc du</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-du/#command-mc.du"><code>mc du</code></a> command summarizes the disk usage of buckets and folders.
You can also use <a href="/reference/minio-mc/mc-du/#command-mc.du"><code>du</code></a> against the local filesystem to produce similar results as the <code>du</code> command.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-encrypt-clear/#command-mc.encrypt.clear"><code>mc encrypt clear</code></a><br /><a href="/reference/minio-mc/mc-encrypt-info/#command-mc.encrypt.info"><code>mc encrypt info</code></a><br /><a href="/reference/minio-mc/mc-encrypt-set/#command-mc.encrypt.set"><code>mc encrypt set</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-encrypt/#command-mc.encrypt"><code>mc encrypt</code></a> commands set, update, or disable the default bucket Server-Side Encryption (SSE) mode.
MinIO automatically encrypts objects using the specified SSE mode.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-event-add/#command-mc.event.add"><code>mc event add</code></a><br /><a href="/reference/minio-mc/mc-event-list/#command-mc.event.ls"><code>mc event ls</code></a><br /><a href="/reference/minio-mc/mc-event-remove/#command-mc.event.rm"><code>mc event rm</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-event/#command-mc.event"><code>mc event</code></a> command supports adding, removing, and listing bucket event notifications.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-find/#command-mc.find"><code>mc find</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-find/#command-mc.find"><code>mc find</code></a> command supports searching for objects on a MinIO deployment.
You can also use the command to search for files on a filesystem.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-get/#command-mc.get"><code>mc get</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-get/#command-mc.get"><code>mc get</code></a> command downloads an object from a target S3 deployment to the local file system.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-head/#command-mc.head"><code>mc head</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-head/#command-mc.head"><code>mc head</code></a> command displays the first <code>n</code> lines of an object,
where <code>n</code> is an argument specified to the command.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-idp-ldap-accesskey/#command-mc.idp.ldap.accesskey"><code>mc idp ldap accesskey</code></a><br /><a href="/reference/minio-mc/mc-idp-ldap-accesskey-create-with-login/#command-mc.idp.ldap.accesskey.create-with-login"><code>mc idp ldap accesskey create-with-login</code></a><br /><a href="/reference/minio-mc/mc-idp-ldap-add/#command-mc.idp.ldap.add"><code>mc idp ldap add</code></a><br /><a href="/reference/minio-mc/mc-idp-ldap-disable/#command-mc.idp.ldap.disable"><code>mc idp ldap disable</code></a><br /><a href="/reference/minio-mc/mc-idp-ldap-enable/#command-mc.idp.ldap.enable"><code>mc idp ldap enable</code></a><br /><a href="/reference/minio-mc/mc-idp-ldap-info/#command-mc.idp.ldap.info"><code>mc idp ldap info</code></a><br /><a href="/reference/minio-mc/mc-idp-ldap-ls/#command-mc.idp.ldap.ls"><code>mc idp ldap ls</code></a><br /><a href="/reference/minio-mc/mc-idp-ldap-policy/#command-mc.idp.ldap.policy"><code>mc idp ldap policy</code></a><br /><a href="/reference/minio-mc/mc-idp-ldap-rm/#command-mc.idp.ldap.rm"><code>mc idp ldap rm</code></a><br /><a href="/reference/minio-mc/mc-idp-ldap-update/#command-mc.idp.ldap.update"><code>mc idp ldap update</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap"><code>mc idp ldap</code></a> commands allow you to manage configurations to 3rd party <a href="/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap">Active Directory or LDAP Identity and Access Management (IAM) integrations</a>.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-idp-openid/#mc.idp.openid.add"><code>mc idp openid add</code></a><br /><a href="/reference/minio-mc/mc-idp-openid/#mc.idp.openid.disable"><code>mc idp openid disable</code></a><br /><a href="/reference/minio-mc/mc-idp-openid/#mc.idp.openid.enable"><code>mc idp openid enable</code></a><br /><a href="/reference/minio-mc/mc-idp-openid/#mc.idp.openid.info"><code>mc idp openid info</code></a><br /><a href="/reference/minio-mc/mc-idp-openid/#mc.idp.openid.ls"><code>mc idp openid ls</code></a><br /><a href="/reference/minio-mc/mc-idp-openid/#mc.idp.openid.rm"><code>mc idp openid rm</code></a><br /><a href="/reference/minio-mc/mc-idp-openid/#mc.idp.openid.update"><code>mc idp openid update</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid"><code>mc idp openid</code></a> commands allow you to manage configurations to 3rd party <a href="/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid">OpenID Identity and Access Management (IAM) integrations</a>.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-idp-ldap-policy-attach/#command-mc.idp.ldap.policy.attach"><code>mc idp ldap policy attach</code></a><br /><a href="/reference/minio-mc/mc-idp-ldap-policy-detach/#command-mc.idp.ldap.policy.detach"><code>mc idp ldap policy detach</code></a><br /><a href="/reference/minio-mc/mc-idp-ldap-policy-entities/#command-mc.idp.ldap.policy.entities"><code>mc idp ldap policy entities</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-idp-ldap-policy/#command-mc.idp.ldap.policy"><code>mc idp ldap policy</code></a> commands show the mapping relationships between policies and the associated groups or users.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-ilm-restore/#command-mc.ilm.restore"><code>mc ilm restore</code></a><br /><a href="/reference/minio-mc/mc-ilm-rule-add/#command-mc.ilm.rule.add"><code>mc ilm rule add</code></a><br /><a href="/reference/minio-mc/mc-ilm-rule-edit/#command-mc.ilm.rule.edit"><code>mc ilm rule edit</code></a><br /><a href="/reference/minio-mc/mc-ilm-rule-export/#command-mc.ilm.rule.export"><code>mc ilm rule export</code></a><br /><a href="/reference/minio-mc/mc-ilm-rule-import/#command-mc.ilm.rule.import"><code>mc ilm rule import</code></a><br /><a href="/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls"><code>mc ilm rule ls</code></a><br /><a href="/reference/minio-mc/mc-ilm-rule-rm/#command-mc.ilm.rule.rm"><code>mc ilm rule rm</code></a><br /><a href="/reference/minio-mc/mc-ilm-tier-add/#command-mc.ilm.tier.add"><code>mc ilm tier add</code></a><br /><a href="/reference/minio-mc/mc-ilm-tier-check/#command-mc.ilm.tier.check"><code>mc ilm tier check</code></a><br /><a href="/reference/minio-mc/mc-ilm-tier-info/#command-mc.ilm.tier.info"><code>mc ilm tier info</code></a><br /><a href="/reference/minio-mc/mc-ilm-tier-ls/#command-mc.ilm.tier.ls"><code>mc ilm tier ls</code></a><br /><a href="/reference/minio-mc/mc-ilm-tier-rm/#command-mc.ilm.tier.rm"><code>mc ilm tier rm</code></a><br /><a href="/reference/minio-mc/mc-ilm-tier-update/#command-mc.ilm.tier.update"><code>mc ilm tier update</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-ilm/#command-mc.ilm"><code>mc ilm</code></a> commands manage <a href="/administration/object-management/object-lifecycle-management/#minio-lifecycle-management">object lifecycle management rules</a> and tiering on a MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-legalhold-clear/#command-mc.legalhold.clear"><code>mc legalhold clear</code></a><br /><a href="/reference/minio-mc/mc-legalhold-info/#command-mc.legalhold.info"><code>mc legalhold info</code></a><br /><a href="/reference/minio-mc/mc-legalhold-set/#command-mc.legalhold.set"><code>mc legalhold set</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-legalhold/#command-mc.legalhold"><code>mc legalhold</code></a> command sets, removes, or retrieves the <a href="/administration/object-management/object-retention/#minio-object-locking-legalhold">object legal hold (WORM)</a> settings for object(s).</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-license-info/#command-mc.license.info"><code>mc license info</code></a><br /><a href="/reference/minio-mc/mc-license-register/#command-mc.license.register"><code>mc license register</code></a><br /><a href="/reference/minio-mc/mc-license-update/#command-mc.license.update"><code>mc license update</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-license/#command-mc.license"><code>mc license</code></a> commands work with cluster registration for <a href="https://min.io/pricing?jmp=docs">MinIO SUBNET</a>.
Use the commands to register a deployment, display information about the cluster’s current license, or update the license key for a cluster.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ls/#command-mc.ls"><code>mc ls</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ls/#command-mc.ls"><code>mc ls</code></a> command lists buckets and objects on MinIO or another
S3-compatible service.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-mb/#command-mc.mb"><code>mc mb</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-mb/#command-mc.mb"><code>mc mb</code></a> command creates a new bucket or directory at the
specified path.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-mirror/#command-mc.mirror"><code>mc mirror</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-mirror/#command-mc.mirror"><code>mc mirror</code></a> command synchronizes content to MinIO deployment, similar to the <code>rsync</code> utility.
<a href="/reference/minio-mc/mc-mirror/#command-mc.mirror"><code>mc mirror</code></a> supports filesystems, MinIO deployments, and other S3-compatible hosts as the synchronization source.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-mv/#command-mc.mv"><code>mc mv</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-mv/#command-mc.mv"><code>mc mv</code></a> command moves an object from source to the target, such as
between MinIO deployments <em>or</em> between buckets on the same MinIO deployment.
<a href="/reference/minio-mc/mc-mv/#command-mc.mv"><code>mc mv</code></a> also supports moving objects between a local filesystem and MinIO.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-od/#command-mc.od"><code>mc od</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-od/#command-mc.od"><code>mc od</code></a> command copies a local file to a remote location in a specified number of parts and part sizes.
The command outputs the time it took to upload the file.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ping/#command-mc.ping"><code>mc ping</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ping/#command-mc.ping"><code>mc ping</code></a> command performs a liveness check on a specified target.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-pipe/#command-mc.pipe"><code>mc pipe</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-pipe/#command-mc.pipe"><code>mc pipe</code></a> command streams content from <a href="https://www.gnu.org/software/libc/manual/html_node/Standard-Streams.html">STDIN</a> to a target object.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-put/#command-mc.put"><code>mc put</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-put/#command-mc.put"><code>mc put</code></a> uploads an object from the local file system to a bucket on a target S3 deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-rb/#command-mc.rb"><code>mc rb</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-rb/#command-mc.rb"><code>mc rb</code></a> command removes one or more buckets on MinIO <em>or</em>
another S3-compatible service.</p><p>To remove only the contents of a bucket, use <a href="/reference/minio-mc/mc-rm/#command-mc.rm"><code>mc rm</code></a> instead.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ready/#command-mc.ready"><code>mc ready</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-ready/#command-mc.ready"><code>mc ready</code></a> command checks the status of a cluster and whether the cluster has <code>read</code> and <code>write</code> quorum.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add"><code>mc replicate add</code></a><br /><a href="/reference/minio-mc/mc-replicate-backlog/#command-mc.replicate.backlog"><code>mc replicate backlog</code></a><br /><a href="/reference/minio-mc/mc-replicate-export/#command-mc.replicate.export"><code>mc replicate export</code></a><br /><a href="/reference/minio-mc/mc-replicate-import/#command-mc.replicate.import"><code>mc replicate import</code></a><br /><a href="/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls"><code>mc replicate ls</code></a><br /><a href="/reference/minio-mc/mc-replicate-resync/#command-mc.replicate.resync"><code>mc replicate resync</code></a><br /><a href="/reference/minio-mc/mc-replicate-rm/#command-mc.replicate.rm"><code>mc replicate rm</code></a><br /><a href="/reference/minio-mc/mc-replicate-status/#command-mc.replicate.status"><code>mc replicate status</code></a><br /><a href="/reference/minio-mc/mc-replicate-update/#command-mc.replicate.update"><code>mc replicate update</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add"><code>mc replicate</code></a> command configures and manages the <a href="/administration/bucket-replication/#minio-bucket-replication-serverside">Server-Side Bucket Replication</a> for a MinIO deployment, including <a href="/administration/bucket-replication/enable-server-side-two-way-bucket-replication/#minio-bucket-replication-serverside-twoway">active-active replication configurations</a> and <a href="/administration/bucket-replication/#minio-replication-behavior-resync">resynchronization</a>.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-retention-clear/#command-mc.retention.clear"><code>mc retention clear</code></a><br /><a href="/reference/minio-mc/mc-retention-info/#command-mc.retention.info"><code>mc retention info</code></a><br /><a href="/reference/minio-mc/mc-retention-set/#command-mc.retention.set"><code>mc retention set</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-retention/#command-mc.retention"><code>mc retention</code></a> command configures the <a href="/administration/object-management/object-retention/#minio-object-locking">Write-Once Read-Many (WORM) locking</a> settings for an object or object(s) in a bucket.
You can also set the default object lock settings for a bucket, where all objects without explicit object lock settings inherit the bucket default.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-rm/#command-mc.rm"><code>mc rm</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-rm/#command-mc.rm"><code>mc rm</code></a> command <a href="/administration/object-management/object-delete/#minio-object-delete">removes objects</a> from a bucket on a MinIO deployment.
To completely remove a bucket, use <a href="/reference/minio-mc/mc-rb/#command-mc.rb"><code>mc rb</code></a> instead.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-share-download/#command-mc.share.download"><code>mc share download</code></a><br /><a href="/reference/minio-mc/mc-share-list/#command-mc.share.ls"><code>mc share ls</code></a><br /><a href="/reference/minio-mc/mc-share-upload/#command-mc.share.upload"><code>mc share upload</code></a><br /></td>
      <td><p>Use the <a href="/reference/minio-mc/mc-share/#command-mc.share"><code>mc share</code></a> commands to manage presigned URLs for downloading and uploading objects to a MinIO bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-sql/#command-mc.sql"><code>mc sql</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-sql/#command-mc.sql"><code>mc sql</code></a> command provides an S3 Select interface for performing sql queries on objects in the specified MinIO deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-stat/#command-mc.stat"><code>mc stat</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-stat/#command-mc.stat"><code>mc stat</code></a> command displays information on objects in a MinIO bucket, including object metadata.
You can also use it to retrieve bucket metadata.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-support-callhome/#command-mc.support.callhome"><code>mc support callhome</code></a><br /><a href="/reference/minio-mc/mc-support-diag/#command-mc.support.diag"><code>mc support diag</code></a><br /><a href="/reference/minio-mc/mc-support-inspect/#command-mc.support.inspect"><code>mc support inspect</code></a><br /><a href="/reference/minio-mc/mc-support-perf/#command-mc.support.perf"><code>mc support perf</code></a><br /><a href="/reference/minio-mc/mc-support-profile/#command-mc.support.profile"><code>mc support profile</code></a><br /><a href="/reference/minio-mc/mc-support-proxy/#command-mc.support.proxy"><code>mc support proxy</code></a><br /><a href="/reference/minio-mc/mc-support-top-api/#command-mc.support.top.api"><code>mc support top api</code></a><br /><a href="/reference/minio-mc/mc-support-top-disk/#command-mc.support.top.disk"><code>mc support top disk</code></a><br /><a href="/reference/minio-mc/mc-support-top-locks/#command-mc.support.top.locks"><code>mc support top locks</code></a><br /><a href="/reference/minio-mc/mc-support-upload/#command-mc.support.upload"><code>mc support upload</code></a><br /></td>
      <td><p>The MinIO Client <a href="/reference/minio-mc/mc-support/#command-mc.support"><code>mc support</code></a> commands provides tools for analyzing deployment health or performance and for running diagnostics.
You can also upload generated health reports for further analysis by MinIO engineering.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-tag-list/#command-mc.tag.list"><code>mc tag list</code></a><br /><a href="/reference/minio-mc/mc-tag-remove/#command-mc.tag.remove"><code>mc tag remove</code></a><br /><a href="/reference/minio-mc/mc-tag-set/#command-mc.tag.set"><code>mc tag set</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-tag/#command-mc.tag"><code>mc tag</code></a> command adds, removes, and lists tags associated to a bucket or object.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-tree/#command-mc.tree"><code>mc tree</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-tree/#command-mc.tree"><code>mc tree</code></a> command lists all prefixes inside a MinIO bucket in a tree
format. The command optionally supports listing all objects inside of bucket
at each prefix, including the bucket root.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-undo/#command-mc.undo"><code>mc undo</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-undo/#command-mc.undo"><code>mc undo</code></a> command reverses changes due to either a <code>PUT</code> or <code>DELETE</code> operation at a specified path.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-update/#command-mc.update"><code>mc update</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-update/#command-mc.update"><code>mc update</code></a> command automatically updates the <strong>mc</strong> binary to
the latest stable version.</p></td>
    </tr>
    <tr>
      <td><a href="/reference/minio-mc/mc-version-enable/#command-mc.version.enable"><code>mc version enable</code></a><br /><a href="/reference/minio-mc/mc-version-info/#command-mc.version.info"><code>mc version info</code></a><br /><a href="/reference/minio-mc/mc-version-suspend/#command-mc.version.suspend"><code>mc version suspend</code></a><br /></td>
      <td><p>The <a href="/reference/minio-mc/mc-version/#command-mc.version"><code>mc version</code></a> commands enable, disable, and retrieve the <a href="/administration/object-management/object-versioning/#minio-bucket-versioning">versioning</a> status for a MinIO bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-watch/#command-mc.watch"><code>mc watch</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-watch/#command-mc.watch"><code>mc watch</code></a> command watches for events on the specified MinIO bucket or
local filesystem path. For S3 services, use <a href="/reference/minio-mc/mc-event-add/#command-mc.event.add"><code>mc event add</code></a> to configure
bucket event notifications on S3-compatible services.</p></td>
    </tr>
  </tbody>
</table>

<a id="mc-configuration"></a>

## Configuration File {#configuration-file}

[`mc`](#command-mc) uses a `JSON` formatted configuration file used for storing certain kinds of information, such as the [`aliases`](/reference/minio-mc/mc-alias/#command-mc.alias) for each configured S3-compatible service.

For Linux and macOS, the default configuration file location is `~/.mc/config.json`.

For Windows, [`mc`](#command-mc) attempts to construct a default file path by trying specific environment variables. If a variable is unset, [`mc`](#command-mc) moves to the next variable. If all attempts fail, [`mc`](#command-mc) returns an error. The following list describes each possible file path location in the order [`mc`](#command-mc) checks them:

1. `HOME\.mc\config.json`
2. `USERPROFILE\.mc\config.json`
3. `HOMEDRIVE+HOMEPATH\.mc\config.json`

You can use the `--config-dir`

<a id="minio-mc-certificates"></a>

## Certificates {#certificates}

The MinIO Client stores certificates and CAs for deployments to the following paths:

Linux, macOS, and other Unix-like systems:

```shell
~/.mc/certs/ # certificates
~/.mc/certs/CAs/ # Certificate Authorities
```

Windows systems:

```shell
C:\Users\[username]\mc\certs\ # certificates
C:\Users\[username]\mc\certs\CAs\ # Certificate Authorities
```

When creating a new [alias](/reference/minio-mc/mc-alias-set/#minio-mc-alias), the MinIO Client fetches the peer certificate, computes the public key fingerprint, and asks the user whether to accept the deployment’s certificate. If you decide to trust the certificate, the MinIO Client adds the certificate to the certificate authority path listed above.

{{% alert color="info" %}}
**Note**

In testing environments, you can bypass the certificate check for selected MinIO Client commands by passing the `--insecure` flag.
{{% /alert %}}

<a id="minio-wildcard-matching"></a>

## Pattern Matching {#pattern-matching}

Some commands and flags allow for pattern matching. When enabled, a pattern can include either of these wildcards for character replacement:

- `*` to represent a string of characters to match, either in the middle or end.
- `?` to represent a single character.

For example, refer to the following examples for wildcard uses and their results.

| Pattern | Text | Match Result |
| --- | --- | --- |
| `abc*` | ab | Match |
| `abc*` | abd | Not a match |
| `abc*c` | abcd | Match |
| `ab*??d` | abxxc | Match |
| `ab*??d` | abxc | Match |
| `ab??d` | abxc | Match |
| `ab??d` | abc | Match |
| `ab??d` | abcxdd | Not a match |

<a id="minio-mc-global-options"></a>

## Global Options {#global-options}

All [commands](#minio-mc-commands) support the following global options. You can also define some of these options using [Environment Variables](/reference/minio-mc/minio-client-settings/#minio-server-envvar-mc).

#### `--config-dir` {#cmdoption-mc-config-dir}

*option*

The path to a `JSON` formatted configuration file that **`mc`** uses for storing data. See [Configuration File](#mc-configuration) for more information on how **`mc`** uses the configuration file.

Alternatively, set the environment variable [`MC_CONFIG_DIR`](/reference/minio-mc/minio-client-settings/#envvar.MC_CONFIG_DIR).

#### `--debug` {#cmdoption-mc-debug}

*option*

Enables verbose output to the console.

For example, the following operation adds verbose output to the [`mc ls`](/reference/minio-mc/mc-ls/#command-mc.ls) command:

```shell
mc --debug ls play
```

Alternatively, set the environment variable [`MC_DEBUG`](/reference/minio-mc/minio-client-settings/#envvar.MC_DEBUG).

<a id="cmdoption-mc-dp"></a>

#### `--disable-pager --dp` {#cmdoption-mc-disable-pager}

*option*

{{% alert color="info" %}}
**Added: mc**

RELEASE.2024-04-29T09-56-05Z
{{% /alert %}}

Disable the pager functionality of the MinIO Client in the CLI. When used, output prints to raw `STDOUT` instead.

#### `--insecure` {#cmdoption-mc-insecure}

*option*

Disables TLS/SSL certificate verification. Allows TLS connectivity to servers with invalid certificates. Exercise caution when using this option against untrusted S3 hosts.

Alternatively, set the environment variable [`MC_INSECURE`](/reference/minio-mc/minio-client-settings/#envvar.MC_INSECURE).

#### `--json` {#cmdoption-mc-json}

*option*

Enables [JSON lines](http://jsonlines.org/)<a id="json-lines"></a> formatted output to the console.

For example, the following operation adds JSON Lines output to the [`mc ls`](/reference/minio-mc/mc-ls/#command-mc.ls) command:

```shell
mc --json ls play
```

Alternatively, set the environment variable [`MC_JSON`](/reference/minio-mc/minio-client-settings/#envvar.MC_JSON).

#### `--no-color` {#cmdoption-mc-no-color}

*option*

Disables the built-in color theme for console output. Useful for dumb terminals.

Alternatively, set the environment variable [`MC_NO_COLOR`](/reference/minio-mc/minio-client-settings/#envvar.MC_NO_COLOR).

#### `--quiet` {#cmdoption-mc-quiet}

*option*

Suppresses console output.

Alternatively, set the environment variable [`MC_QUIET`](/reference/minio-mc/minio-client-settings/#envvar.MC_QUIET).

#### `--resolve` {#cmdoption-mc-resolve}

*option*

{{% alert color="info" %}}
**Added: mc**

RELEASE.2024-08-13T05-33-17Z
{{% /alert %}}

Creates a custom DNS mapping to resolve a HOST to a specified IP address.

Use the following syntax:

```text
--resolve HOST[:PORT]=IP
```

For example:

```shell
mc alias set --resolve myminio.example.com:9000=192.168.188.118 'myminio' 'https://myminio.example.com:9000' 'miniouser' 'miniosecret'
```

Repeat the flag multiple times to add additional custom DNS mappings.

#### `--version` {#cmdoption-mc-version}

*option*

Displays the current version of [`mc`](#command-mc).

#### `--help` {#mc.-help}

*mc-cmd*

*Optional*

Displays a summary of command usage on the terminal.

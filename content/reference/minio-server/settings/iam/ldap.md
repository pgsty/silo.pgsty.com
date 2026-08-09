---
title: "Active Directory / LDAP Settings"
url: "/reference/minio-server/settings/iam/ldap/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="active-directory-ldap-settings"></a>
<a id="minio-ldap-config-settings"></a>
<a id="minio-server-envvar-external-identity-management-ad-ldap"></a>

This page documents settings for enabling external identity management using an Active Directory or LDAP service. See [Configure MinIO for Authentication using Active Directory / LDAP](/operations/external-iam/configure-ad-ldap-external-identity-management/#minio-authenticate-using-ad-ldap-generic) for a tutorial on using these settings.

{{% alert color="warning" %}}
**Important**

New in version `RELEASE.2023-05-26T23-31-54Z`:

[`mc idp ldap`](/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap) commands are preferred over using configuration settings to configure MinIO to use Active Directory or LDAP for identity management.

MinIO recommends using the [`mc idp ldap`](/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap) commands for LDAP management operations. These commands offer better validation and additional features, while providing the same settings as the `identity_ldap` configuration key. See [Configure MinIO for Authentication using Active Directory / LDAP](/operations/external-iam/configure-ad-ldap-external-identity-management/#minio-authenticate-using-ad-ldap-generic) for a tutorial on using [`mc idp ldap`](/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap).
{{% /alert %}}

The `identity_ldap` configuration settings remains available for existing scripts and other tools.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

## Examples {#examples}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

```shell
MINIO_IDENTITY_LDAP_SERVER_ADDR="ldapserver.com:636"
```

{{% alert color="info" %}}
**Note**

`srv_record_name` automatically identifies the port.

If your AD/LDAP server uses `DNS SRV Records`, do *not* append the port number to your `server_addr` value. SRV requests automatically include port numbers when returning the list of available servers.
{{% /alert %}}
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

#### `identity_ldap` {#mc-conf.identity_ldap}

*mc-conf*

The following settings are required when defining LDAP using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set):

- `enabled`
- `server_addr`
- `lookup_bind_dn`
- `lookup_bind_dn_password`
- `user_dn_search_base_dn`
- `user_dn_search_filter`

```shell
mc admin config set identity_ldap                        \
   enabled="true"                                        \
   server_addr="ad-ldap.example.net/"                    \
   lookup_bind_dn="cn=miniolookupuser,dc=example,dc=net" \
   lookup_bind_dn_password="userpassword"                \
   user_dn_search_base_dn="dc=example,dc=net"            \
   user_dn_search_filter="(&(objectCategory=user)(sAMAccountName=%s))"
```

{{% /tab %}}
{{< /tabpane >}}

## Settings {#settings}

### Server Address {#server-address}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_SERVER_ADDR` {#envvar.MINIO_IDENTITY_LDAP_SERVER_ADDR}

*envvar*

Specify the hostname for the Active Directory / LDAP server. For example:

```shell
ldapserver.com:636
```

{{% alert color="info" %}}
**[`srv_record_name`](/reference/minio-mc/mc-idp-ldap-add/#mc.idp.ldap.add.srv_record_name) automatically identifies the port**

If your AD/LDAP server uses [`DNS SRV Records`](/reference/minio-mc/mc-idp-ldap-add/#mc.idp.ldap.add.srv_record_name), do *not* append the port number to your [`server_addr`](/reference/minio-mc/mc-idp-ldap-add/#mc.idp.ldap.add.server_addr) value. SRV requests automatically include port numbers when returning the list of available servers.
{{% /alert %}}
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap server_addr` {#mc-conf.identity_ldap.server_addr}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the hostname for the Active Directory / LDAP server. For example:

```shell
ldapserver.com:636
```

{{% alert color="info" %}}
**[`srv_record_name`](/reference/minio-mc/mc-idp-ldap-add/#mc.idp.ldap.add.srv_record_name) automatically identifies the port**

If your AD/LDAP server uses [`DNS SRV Records`](/reference/minio-mc/mc-idp-ldap-add/#mc.idp.ldap.add.srv_record_name), do *not* append the port number to your [`server_addr`](/reference/minio-mc/mc-idp-ldap-add/#mc.idp.ldap.add.server_addr) value. SRV requests automatically include port numbers when returning the list of available servers.
{{% /alert %}}

### Lookup Bind DN {#lookup-bind-dn}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_LOOKUP_BIND_DN` {#envvar.MINIO_IDENTITY_LDAP_LOOKUP_BIND_DN}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap lookup_bind_dn` {#mc-conf.identity_ldap.lookup_bind_dn}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the Distinguished Name (DN) for an AD/LDAP account MinIO uses when querying the AD/LDAP server. Enables [Lookup-Bind](/operations/external-iam/#minio-external-identity-management-ad-ldap-lookup-bind) authentication to the AD/LDAP server.

The DN account should be a read-only access keys with sufficient privileges to support querying performing user and group lookups.

### Lookup Bind Password {#lookup-bind-password}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_LOOKUP_BIND_PASSWORD` {#envvar.MINIO_IDENTITY_LDAP_LOOKUP_BIND_PASSWORD}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap lookup_bind_password` {#mc-conf.identity_ldap.lookup_bind_password}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the password for the [Lookup-Bind](/operations/external-iam/#minio-external-identity-management-ad-ldap-lookup-bind) user account.

{{% alert color="info" %}}
**Changed: RELEASE.2023-06-23T20-26-00Z**

MinIO redacts this value when returned as part of [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get).
{{% /alert %}}

### User DN Search Base DN {#user-dn-search-base-dn}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_USER_DN_SEARCH_BASE_DN` {#envvar.MINIO_IDENTITY_LDAP_USER_DN_SEARCH_BASE_DN}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap user_dn_search_base_dn` {#mc-conf.identity_ldap.user_dn_search_base_dn}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the base Distinguished Name (DN) MinIO uses when querying for user credentials matching those provided by an authenticating client.

Separate multiple DNs with a semicolon (`;`).

For example:

```shell
cn=miniousers,dc=myldapserver,dc=net;ou=swengg,dc=min,dc=io
```

Supports [Lookup-Bind](/operations/external-iam/#minio-external-identity-management-ad-ldap-lookup-bind) mode.

### User DN Search Filter {#user-dn-search-filter}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_USER_DN_SEARCH_FILTER` {#envvar.MINIO_IDENTITY_LDAP_USER_DN_SEARCH_FILTER}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap user_dn_search_filter` {#mc-conf.identity_ldap.user_dn_search_filter}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the AD/LDAP search filter MinIO uses when querying for user credentials matching those provided by an authenticating client.

Use the `%s` substitution character to insert the client-specified username into the search string. For example:

```shell
(userPrincipalName=%s)
```

### User DN Attributes {#user-dn-attributes}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_USER_DN_ATTRIBUTES` {#envvar.MINIO_IDENTITY_LDAP_USER_DN_ATTRIBUTES}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap user_dn_attributes` {#mc-conf.identity_ldap.user_dn_attributes}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

{{% alert color="info" %}}
**Added: RELEASE.2024-06-06T09-36-42Z**

{{% /alert %}}

Comma-separated list of user DN attributes.

Some valid values include, `uid,cn,mail,sshPublicKey`.

To enable public authentication for LDAP users, pass `sshPublicKey` as a DN attribute. The user can then use the passed SSH Public Key to log in to SFTP servers.

```text
mc idp ldap update ALIAS user_dn_attributes=sshPublicKey
```

### Enabled {#enabled}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
This setting does not have an environment variable option. Use the configuration setting instead.
{{% /tab %}}
{{% tab header="Configuration Setting" selected=true %}}

##### `identity_ldap enabled` {#mc-conf.identity_ldap.enabled}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Set to `false` to disable the AD/LDAP configuration.

If `false`, applications cannot generate STS credentials or otherwise authenticate to MinIO using the configured provider.

Defaults to `true` or “enabled”.

### Group Search Filter {#group-search-filter}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_GROUP_SEARCH_FILTER` {#envvar.MINIO_IDENTITY_LDAP_GROUP_SEARCH_FILTER}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap group_search_filter` {#mc-conf.identity_ldap.group_search_filter}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify an AD/LDAP search filter for performing group lookups for the authenticated user

Use the `%s` substitution character to insert the client-specified username into the search string. Use the `%d` substitution character to insert the Distinguished Name of the client-specified username into the search string.

For example:

```shell
(&(objectclass=groupOfNames)(memberUid=%s))
```

When providing an AD/LDAP group search filter, configure a filter that returns the minimum number of relevant groups for the purpose of supporting authentication. Filters that return large group assignments increase the size of associated calls and resources. Functions sensitive to large request or response bodies may exhibit unexpected behaviors as a result.

When providing an AD/LDAP group search filter, configure a filter that returns the minimum number of relevant groups for the purpose of supporting authentication. Filters that return large group assignments increase the size of associated calls and resources. Functions sensitive to large request or response bodies may exhibit unexpected behaviors as a result.

### Group Search Base DN {#group-search-base-dn}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_GROUP_SEARCH_BASE_DN` {#envvar.MINIO_IDENTITY_LDAP_GROUP_SEARCH_BASE_DN}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap group_search_base_dn` {#mc-conf.identity_ldap.group_search_base_dn}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify a semicolon-separated (`;`) list of group search base [Distinguished Names](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ldap/distinguished-names) MinIO uses when performing group lookups.

For example:

```shell
cn=miniogroups,dc=myldapserver,dc=net;ou=swengg,dc=min,dc=io
```

### TLS Skip Verify {#tls-skip-verify}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_TLS_SKIP_VERIFY` {#envvar.MINIO_IDENTITY_LDAP_TLS_SKIP_VERIFY}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap tls_skip_verify` {#mc-conf.identity_ldap.tls_skip_verify}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify `on` to trust the AD/LDAP server TLS certificates without verification. This option may be required if the AD/LDAP server TLS certificates are signed by an untrusted Certificate Authority (e.g. self-signed).

Defaults to `off`

### Server Insecure {#server-insecure}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_SERVER_INSECURE` {#envvar.MINIO_IDENTITY_LDAP_SERVER_INSECURE}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap server_insecure` {#mc-conf.identity_ldap.server_insecure}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify `on` to allow unsecured (non-TLS encrypted) connections to the AD/LDAP server.

MinIO sends AD/LDAP user credentials in plain text to the AD/LDAP server, such that enabling TLS is *required* to prevent reading credentials over the wire. Using this option presents a security risk where any user with access to network traffic can observe the unencrypted plaintext credentials.

Defaults to `off`.

### Server Start TLS {#server-start-tls}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_SERVER_STARTTLS` {#envvar.MINIO_IDENTITY_LDAP_SERVER_STARTTLS}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap server_starttls` {#mc-conf.identity_ldap.server_starttls}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify `on` to enable `StartTLS` connections to an AD/LDAP server.

Defaults to `off`

For more about `StartTLS`, refer to section 4.14 of the [LDAP RFC 4511 specification](https://docs.ldap.com/specs/rfc4511.txt).

### SRV Record Name {#srv-record-name}

*Optional*

{{% alert color="info" %}}
**Added: RELEASE.2022-12-12T19-27-27Z**

{{% /alert %}}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_SRV_RECORD_NAME` {#envvar.MINIO_IDENTITY_LDAP_SRV_RECORD_NAME}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap srv_record_name` {#mc-conf.identity_ldap.srv_record_name}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the appropriate value to enable MinIO to select an AD/LDAP server using a [DNS SRV record](https://ldap.com/dns-srv-records-for-ldap) request.

When enabled, MinIO selects an AD/LDAP server by:

- Constructing the target SRV record name following standard naming conventions.
- Requesting a list of available AD/LDAP servers.
- Choosing an appropriate target based on priority and weight.

The configuration examples below presume the AD/LDAP server address is set to `example.com` and the SRV record protocol is `_tcp`.

For SRV record names beginning with `_ldap`, specify `ldap`. The constructed DNS SRV record name resembles the following:

```shell
_ldap._tcp.example.com
```

For SRV record names with beginning with `_ldaps`, specify `ldaps`. The constructed DNS SRV record name resembles the following:

```shell
_ldaps._tcp.example.com
```

If your DNS SRV record name uses alternate service or protocol names, specify `on` and provide the full record name as your LDAP server address. Example: `_ldapserver._specialtcp.example.com`

For more about DNS SRV records, see [DNS SRV Records for LDAP](https://ldap.com/dns-srv-records-for-ldap).

{{% alert color="info" %}}
**Server address for DNS SRV record configurations**

The specified server name **must not** include a port number. This is different from a standard AD/LDAP configuration, where the port number is required.

See [`server_addr`](#mc-conf.identity_ldap.server_addr) or [`MINIO_IDENTITY_LDAP_SERVER_ADDR`](#envvar.MINIO_IDENTITY_LDAP_SERVER_ADDR) for more about configuring an AD/LDAP server address.
{{% /alert %}}

### Comment {#comment}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_LDAP_COMMENT` {#envvar.MINIO_IDENTITY_LDAP_COMMENT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_ldap identity_ldap comment` {#mc-conf.identity_ldap.identity_ldap.comment}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify a comment to associate to the AD/LDAP configuration.

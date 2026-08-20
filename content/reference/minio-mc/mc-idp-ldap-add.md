---
title: "mc idp ldap add"
url: "/reference/minio-mc/mc-idp-ldap-add/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-idp-ldap-add.rst
upstream_modified: false
---

<a id="mc-idp-ldap-add"></a>
<a id="minio-mc-idp-ldap-add"></a>

<a id="command-mc.idp.ldap.add"></a>

## Description {#description}

The [`mc idp ldap add`](#command-mc.idp.ldap.add) command creates an AD/LDAP IDP server configuration.

MinIO supports no more than *one* (1) AD/LDAP provider per deployment.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example sets the AD/LDAP configuration settings for the `myminio` deployment.

```shell
mc idp ldap add                                                            \
            myminio                                                        \
            server_addr=myldapserver:636                                   \
            lookup_bind_dn=cn=admin,dc=min,dc=io                           \
            lookup_bind_password=somesecret                                \
            user_dn_search_base_dn=dc=min,dc=io                            \
            user_dn_search_filter="(uid=%s)"                               \
            group_search_base_dn=ou=swengg,dc=min,dc=io                    \
            group_search_filter="(&(objectclass=groupofnames)(member=%d))"
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp ldap add               \
                          ALIAS             \
                          [CFG_PARAM1]      \
                          [CFG_PARAM2]...
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to create for AD/LDAP integration.
- Replace the `[CFG_PARAM#]` with each of the [configuration setting](/reference/minio-server/settings/iam/ldap/#minio-ldap-config-settings) key-value pairs in the format of `PARAMETER="value"`.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.idp.ldap.add.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment on which to add an AD/LDAP integration.

For example:

```text
mc idp ldap add myminio                               \
                server_addr=myldapserver:636          \
                lookup_bind_dn=cn=admin,dc=min,dc=io  \
                lookup_bind_password=somesecret       \
                user_dn_search_base_dn=dc=min,dc=io   \
                user_dn_search_filter="(uid=%s)"      \
```

##### `server_addr` {#mc.idp.ldap.add.server_addr}

*mc-cmd*

*Required*

Specify the hostname for the Active Directory / LDAP server. For example:

```shell
ldapserver.com:636
```

> [!NOTE]
> **[`srv_record_name`](#mc.idp.ldap.add.srv_record_name) automatically identifies the port**
>
> If your AD/LDAP server uses [`DNS SRV Records`](#mc.idp.ldap.add.srv_record_name), do *not* append the port number to your [`server_addr`](#mc.idp.ldap.add.server_addr) value. SRV requests automatically include port numbers when returning the list of available servers.

This parameter corresponds with the [`MINIO_IDENTITY_LDAP_SERVER_ADDR`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_SERVER_ADDR) environment variable.

##### `lookup_bind_dn` {#mc.idp.ldap.add.lookup_bind_dn}

*mc-cmd*

*Required*

Specify the Distinguished Name (DN) for an AD/LDAP account MinIO uses when querying the AD/LDAP server. Enables [Lookup-Bind](/operations/external-iam/#minio-external-identity-management-ad-ldap-lookup-bind) authentication to the AD/LDAP server.

The DN account should be a read-only access keys with sufficient privileges to support querying performing user and group lookups.

This parameter corresponds with the [`MINIO_IDENTITY_LDAP_LOOKUP_BIND_DN`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_LOOKUP_BIND_DN) environment variable.

##### `lookup_bind_password` {#mc.idp.ldap.add.lookup_bind_password}

*mc-cmd*

*Required*

Specify the password for the [Lookup-Bind](/operations/external-iam/#minio-external-identity-management-ad-ldap-lookup-bind) user account.

> [!NOTE]
> **Changed: RELEASE.2023-06-23T20-26-00Z**
>
> MinIO redacts this value when returned as part of [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get).

This parameter corresponds with the [`MINIO_IDENTITY_LDAP_LOOKUP_BIND_PASSWORD`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_LOOKUP_BIND_PASSWORD) environment variable.

##### `user_dn_attributes` {#mc.idp.ldap.add.user_dn_attributes}

*mc-cmd*

*Optional*

> [!NOTE]
> **Added: RELEASE.2024-06-06T09-36-42Z**

Comma-separated list of user DN attributes.

Some valid values include, `uid,cn,mail,sshPublicKey`.

To enable public authentication for LDAP users, pass `sshPublicKey` as a DN attribute. The user can then use the passed SSH Public Key to log in to SFTP servers.

```text
mc idp ldap update ALIAS user_dn_attributes=sshPublicKey
```

##### `user_dn_search_base_dn` {#mc.idp.ldap.add.user_dn_search_base_dn}

*mc-cmd*

*Required*

Specify the base Distinguished Name (DN) MinIO uses when querying for user credentials matching those provided by an authenticating client.

Separate multiple DNs with a semicolon (`;`).

For example:

```shell
cn=miniousers,dc=myldapserver,dc=net;ou=swengg,dc=min,dc=io
```

Supports [Lookup-Bind](/operations/external-iam/#minio-external-identity-management-ad-ldap-lookup-bind) mode.

This parameter corresponds with the [`MINIO_IDENTITY_LDAP_USER_DN_SEARCH_BASE_DN`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_USER_DN_SEARCH_BASE_DN) environment variable.

##### `user_dn_search_filter` {#mc.idp.ldap.add.user_dn_search_filter}

*mc-cmd*

*Required*

Specify the AD/LDAP search filter MinIO uses when querying for user credentials matching those provided by an authenticating client.

Use the `%s` substitution character to insert the client-specified username into the search string. For example:

```shell
(userPrincipalName=%s)
```

This parameter corresponds with the [`MINIO_IDENTITY_LDAP_USER_DN_SEARCH_FILTER`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_USER_DN_SEARCH_FILTER) environment variable.

##### `comment` {#mc.idp.ldap.add.comment}

*mc-cmd*

*Optional*

Specify a comment to associate to the AD/LDAP configuration.

This parameter corresponds with the [`MINIO_IDENTITY_LDAP_COMMENT`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_COMMENT) environment variable.

##### `enabled` {#mc.idp.ldap.add.enabled}

*mc-cmd*

*Optional*

Set to `false` to disable the AD/LDAP configuration.

If `false`, applications cannot generate STS credentials or otherwise authenticate to MinIO using the configured provider.

Defaults to `true` or “enabled”.

##### `group_search_base_dn` {#mc.idp.ldap.add.group_search_base_dn}

*mc-cmd*

*Optional*

Specify a semicolon-separated (`;`) list of group search base [Distinguished Names](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ldap/distinguished-names) MinIO uses when performing group lookups.

For example:

```shell
cn=miniogroups,dc=myldapserver,dc=net;ou=swengg,dc=min,dc=io
```

This parameter corresponds with the [`MINIO_IDENTITY_LDAP_GROUP_SEARCH_BASE_DN`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_GROUP_SEARCH_BASE_DN) environment variable.

##### `group_search_filter` {#mc.idp.ldap.add.group_search_filter}

*mc-cmd*

*Optional*

Specify an AD/LDAP search filter for performing group lookups for the authenticated user

Use the `%s` substitution character to insert the client-specified username into the search string. Use the `%d` substitution character to insert the Distinguished Name of the client-specified username into the search string.

For example:

```shell
(&(objectclass=groupOfNames)(memberUid=%s))
```

When providing an AD/LDAP group search filter, configure a filter that returns the minimum number of relevant groups for the purpose of supporting authentication. Filters that return large group assignments increase the size of associated calls and resources. Functions sensitive to large request or response bodies may exhibit unexpected behaviors as a result.

This parameter corresponds with the [`MINIO_IDENTITY_LDAP_GROUP_SEARCH_FILTER`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_GROUP_SEARCH_FILTER) environment variable.

##### `server_insecure` {#mc.idp.ldap.add.server_insecure}

*mc-cmd*

*Optional*

Specify `on` to allow unsecured (non-TLS encrypted) connections to the AD/LDAP server.

MinIO sends AD/LDAP user credentials in plain text to the AD/LDAP server, such that enabling TLS is *required* to prevent reading credentials over the wire. Using this option presents a security risk where any user with access to network traffic can observe the unencrypted plaintext credentials.

Defaults to `off`.

This parameter corresponds with the [`MINIO_IDENTITY_LDAP_SERVER_INSECURE`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_SERVER_INSECURE) environment variable.

##### `server_starttls` {#mc.idp.ldap.add.server_starttls}

*mc-cmd*

*Optional*

Specify `on` to enable `StartTLS` connections to an AD/LDAP server.

Defaults to `off`

For more about `StartTLS`, refer to section 4.14 of the [LDAP RFC 4511 specification](https://docs.ldap.com/specs/rfc4511.txt).

This parameter corresponds with the [`MINIO_IDENTITY_LDAP_SERVER_STARTTLS`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_SERVER_STARTTLS) environment variable.

##### `srv_record_name` {#mc.idp.ldap.add.srv_record_name}

*mc-cmd*

*Optional*

> [!NOTE]
> **Added: RELEASE.2022-12-12T19-27-27Z**

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

> [!NOTE]
> **Server address for DNS SRV record configurations**
>
> The specified server name **must not** include a port number. This is different from a standard AD/LDAP configuration, where the port number is required.
>
> See [`server_addr`](/reference/minio-server/settings/iam/ldap/#mc-conf.identity_ldap.server_addr) or [`MINIO_IDENTITY_LDAP_SERVER_ADDR`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_SERVER_ADDR) for more about configuring an AD/LDAP server address.

This parameter corresponds with the [`MINIO_IDENTITY_LDAP_SRV_RECORD_NAME`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_SRV_RECORD_NAME) environment variable.

##### `tls_skip_verify` {#mc.idp.ldap.add.tls_skip_verify}

*mc-cmd*

*Optional*

Specify `on` to trust the AD/LDAP server TLS certificates without verification. This option may be required if the AD/LDAP server TLS certificates are signed by an untrusted Certificate Authority (e.g. self-signed).

Defaults to `off`

This parameter corresponds with the [`MINIO_IDENTITY_LDAP_TLS_SKIP_VERIFY`](/reference/minio-server/settings/iam/ldap/#envvar.MINIO_IDENTITY_LDAP_TLS_SKIP_VERIFY) environment variable.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

---
title: "Active Directory / LDAP Access Management"
url: "/administration/identity-access-management/ad-ldap-access-management/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/identity-access-management/ad-ldap-access-management.rst
upstream_modified: true
---

<a id="active-directory-ldap-access-management"></a>
<a id="minio-external-identity-management-ad-ldap"></a>

MinIO supports configuring a single Active Directory or LDAP (AD/LDAP) service for external management of user identities. Enabling AD/LDAP external identity management disables the [MinIO internal IDP](/administration/identity-access-management/minio-identity-management/#minio-internal-idp) for ordinary users, while the [`root` user](/administration/identity-access-management/minio-user-management/#minio-users-root) remains active. Since [SILO 20261109](/blog/release/silo-20261109/) ([#272](https://github.com/pgsty/silo/issues/272)), the `root` user can also sign in to the embedded Console when AD/LDAP is enabled.

For identities managed by the external AD/LDAP provider, SILO looks up the existing policies explicitly attached to the user’s Distinguished Name (DN). Policy names do not need to match the DN.

If the AD/LDAP configuration includes the necessary settings to query the user’s AD/LDAP group membership, SILO also includes policies attached to the returned group DNs.

MinIO by default denies access to all actions or resources not explicitly allowed by a user’s assigned or inherited [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy). An administrator attaches existing SILO policies to LDAP users or groups with `mcli idp ldap policy attach`. If no policies match either the user DN or group DNs, MinIO blocks all access to actions and resources on the deployment.

The specific AD/LDAP queries MinIO issues to authenticate the user and retrieve its group membership are configured as part of [deploying the cluster with Active Directory / LDAP identity management](/operations/external-iam/#minio-external-iam-ad-ldap). This page covers creation of SILO policies and their explicit association with returned Distinguished Names.

## Authentication and Authorization Flow {#authentication-and-authorization-flow}

The login flow for an application using Active Directory / LDAP credentials is as follows:

1. Specify the AD/LDAP credentials to the MinIO Security Token Service (STS) [AssumeRoleWithLDAPIdentity](/developers/security-token-service/AssumeRoleWithLDAPIdentity/#minio-sts-assumerolewithldapidentity) API endpoint.
2. MinIO verifies the provided credentials against the AD/LDAP server.
3. SILO loads the [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) explicitly attached to the user DN.

   If configured to perform group queries, MinIO also queries for a list of AD/LDAP groups in which the user has membership. SILO includes policies explicitly attached to each returned group DN.
4. MinIO returns temporary credentials in the STS API response in the form of an access key, secret key, and session token. The credentials have permissions matching those policies attached to either the authenticated user DN *or* a group DN.

Since [SILO 20261109](/blog/release/silo-20261109/) ([#275](https://github.com/pgsty/silo/issues/275)), `AssumeRoleWithLDAPIdentity` reports invalid LDAP credentials as `InvalidParameterValue` (`HTTP 400`, counted against per-source login throttling) and reports upstream LDAP directory failures as `InternalError` (`HTTP 500`, logged on the server without consuming login-throttle tokens).

SILO provides an example Go application [ldap.go](https://github.com/pgsty/silo/blob/RELEASE.2026-11-09T00-00-00Z/docs/sts/ldap.go) that handles the full login flow.

AD/LDAP users can alternatively create [access keys](/administration/identity-access-management/minio-user-management/#minio-idp-service-account) associated to their AD/LDAP user Distinguished Name. Access Keys are long-lived credentials which inherit their privileges from the parent user. The parent user can further restrict those privileges while creating the access keys. Use either of the following methods to create a new access key:

Use the [`mc admin user svcacct add`](/reference/minio-mc-admin/mc-admin-user-svcacct-add/#command-mc.admin.user.svcacct.add) command to create the access keys. Specify the user Distinguished Name as the username to which to associate the access keys.

## Mapping Policies to User DN {#mapping-policies-to-user-dn}

The following commands use [`mc idp ldap policy attach`](/reference/minio-mc/mc-idp-ldap-policy-attach/#command-mc.idp.ldap.policy.attach) to associate an existing MinIO [policy](/administration/identity-access-management/policy-based-access-control/#minio-policy) to an AD/LDAP User DN.

```shell
mc idp ldap policy attach myminio consoleAdmin \
  --user='cn=sisko,cn=users,dc=example,dc=com'

mc idp ldap policy attach myminio readwrite diagnostics \
  --user='cn=dax,cn=users,dc=example,dc=com'
```

- MinIO would assign an authenticated user with DN matching `cn=sisko,cn=users,dc=example,dc=com` the [`consoleAdmin`](/administration/identity-access-management/policy-based-access-control/#userpolicy.consoleAdmin) policy, granting complete access to the MinIO server.
- MinIO would assign an authenticated user with DN matching `cn=dax,cn=users,dc=example,dc=com` both the [`readwrite`](/administration/identity-access-management/policy-based-access-control/#userpolicy.readwrite) and [`diagnostics`](/administration/identity-access-management/policy-based-access-control/#userpolicy.diagnostics) policies, granting general read/write access to the MinIO server *and* access to diagnostic administrative operations.
- MinIO would assign no policies to an authenticated user with DN matching `cn=quark,cn=users,dc=example,dc=com` and deny all access to API operations.

## Mapping Policies to Group DN {#mapping-policies-to-group-dn}

The following commands use [`mc idp ldap policy attach`](/reference/minio-mc/mc-idp-ldap-policy-attach/#command-mc.idp.ldap.policy.attach) to associate an existing MinIO [policy](/administration/identity-access-management/policy-based-access-control/#minio-policy) to an AD/LDAP Group DN.

```shell
mc idp ldap policy attach myminio consoleAdmin \
  --group='cn=ops,cn=groups,dc=example,dc=com'

mc idp ldap policy attach myminio diagnostics \
  --group='cn=engineering,cn=groups,dc=example,dc=com'
```

- MinIO would assign any authenticating user with membership in the `cn=ops,cn=groups,dc=example,dc=com` AD/LDAP group the [`consoleAdmin`](/administration/identity-access-management/policy-based-access-control/#userpolicy.consoleAdmin) policy, granting complete access to the MinIO server.
- MinIO would assign any authenticating user with membership in the `cn=engineering,cn=groups,dc=example,dc=com` AD/LDAP group the [`diagnostics`](/administration/identity-access-management/policy-based-access-control/#userpolicy.diagnostics) policy, granting access to diagnostic administrative operations.

## Long Distinguished Names {#long-distinguished-names}

[SILO 20261026](/blog/release/silo-20261026/#server-20261026) introduced the [LDAP long-DN fix](/blog/design/ldap-long-dn/), and [SILO 20261109](/blog/release/silo-20261109/) (`RELEASE.2026-11-09T00-00-00Z`, [#271](https://github.com/pgsty/silo/issues/271)) extends it to multi-drive erasure-set deployments. When a user relies on group policies and has a normalized DN whose pure-ASCII filename component exceeds 255 bytes on the object IAM backend, the server treats the resulting filename-length error as an absent user-policy mapping and proceeds to evaluate group policies. Full-path length limits (`PATH_MAX`), unreadable revocation records, and storage failures still fail closed, and writing overlong path records remains unsupported on the object backend.

### Stored Identity Record Group Refresh {#stored-record-group-refresh}

Since [SILO 20261109](/blog/release/silo-20261109/) (`RELEASE.2026-11-09T00-00-00Z`), when an LDAP user authenticates or refreshes through a stored identity record (`fromStored`), the server re-queries LDAP group membership once the cached group list is older than 1 hour (`ldapStoredGroupRefreshInterval = 1h`) and fails closed if the refresh fails. Group refreshes write directly to the persisted identity record ([#321](https://github.com/pgsty/silo/issues/321)–[#323](https://github.com/pgsty/silo/issues/323)) so stale peer caches cannot resurrect removed group memberships, while running batch jobs survive LDAP refreshes that retain the submitter's credential ([#318](https://github.com/pgsty/silo/issues/318)–[#320](https://github.com/pgsty/silo/issues/320)). See [LDAP Long Distinguished Names](/blog/design/ldap-long-dn/).

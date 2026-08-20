---
title: "Silo External Identity Management Plugin"
url: "/administration/identity-access-management/pluggable-authentication/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/identity-access-management/pluggable-authentication.rst
upstream_modified: true
---

<a id="minio-external-identity-management-plugin"></a>
<a id="id1"></a>

## Overview {#overview}

The MinIO Identity Management Plugin provides a REST interface for offloading authentication to an external identity manager through a webhook service.

Once enabled, client applications use the `AssumeRoleWithCustomToken` STS API extension to generate access tokens for MinIO. MinIO verifies this token by making a POST request to the configured plugin endpoint and uses the returned response to determine the authentication status of the client.

## Configuration Settings {#configuration-settings}

You can configure the MinIO Identity Management Plugin using the following environment variables or configuration settings:

{{< tabs group="environment-variables-configuration-settings" >}}
{{< tab label="Environment Variables" value="environment-variables" >}}
Specify the following [environment variables](/reference/minio-server/settings/iam/minio-identity-plugin/#minio-server-envvar-external-identity-management-plugin) to each MinIO server in the deployment:

```shell
MINIO_IDENTITY_PLUGIN_URL="https://external-auth.example.net:8080/auth"
MINIO_IDENTITY_PLUGIN_ROLE_POLICY="consoleAdmin"

# All other envvars are optional
MINIO_IDENTITY_PLUGIN_TOKEN="Bearer TOKEN"
MINIO_IDENTITY_PLUGIN_ROLE_ID="external-auth-provider"
MINIO_IDENTITY_PLUGIN_COMMENT="External Identity Management using PROVIDER"
```
{{< /tab >}}
{{< tab label="Configuration Settings" value="configuration-settings" >}}
Set the following configuration settings using the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command:

```shell
mc admin config set identity_plugin \
   url="https://external-auth.example.net:8080/auth" \
   role_policy="consoleAdmin" \

   # All other config settings are optional
   token="Bearer TOKEN" \
   role_id="external-auth-provider" \
   comment="External Identity Management using PROVIDER"
```
{{< /tab >}}
{{< /tabs >}}

## Authentication and Authorization Flow {#authentication-and-authorization-flow}

The login flow for an application is as follows:

1. Make a POST request using the [AssumeRoleWithCustomToken](/developers/security-token-service/AssumeRoleWithCustomToken/#minio-sts-assumerolewithcustomtoken) API.

   The request includes a token used by the configured external identity manager for authenticating the client.
2. MinIO makes a POST call to the configured identity plugin URL using the token specified to the STS API.
3. On successful authentication, the identity manager returns a `200 OK` response with an `application/json` content-type and body with the following structure:

   ```json
   {
      "user": "<string>",
      "maxValiditySeconds": 3600,
      "claims": {"KEY": "VALUE", ...}
   }
   ```

   <table>
     <tbody>
       <tr>
         <td><p><code>user</code></p></td>
         <td><p>The owner of the requested credentials</p></td>
       </tr>
       <tr>
         <td><p><code>maxValiditySeconds</code></p></td>
         <td><p>The maximum allowed expiry duration for the returned credentials</p></td>
       </tr>
       <tr>
         <td><p><code>claims</code></p></td>
         <td><p>A JSON string of <code>&quot;key&quot;: &quot;value&quot;</code> pair claims associated with the requested credentials.
   MinIO reserves and ignores the <code>exp</code>, <code>parent</code>, and <code>sub</code> claims objects if present.</p></td>
       </tr>
     </tbody>
   </table>
4. MinIO returns a response to the STS API request that includes temporary credentials for use with making authenticated requests.

If the identity manager rejects the authentication request or otherwise encounters an error, the response *must* return a `403 FORBIDDEN` HTTP status code with an `application/json` content-type and body with the following structure:

```json
{
     "reason": "<string>"
}
```

The `"reason"` field should include the reason for the 403.

## Creating Policies to Match Claims {#creating-policies-to-match-claims}

Use the [`mc admin policy`](/reference/minio-mc-admin/mc-admin-policy/#command-mc.admin.policy) command to create policies that match one or more claim values.

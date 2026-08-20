---
title: "Configure Silo Authentication with Keycloak"
url: "/operations/external-iam/configure-keycloak-identity-management/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/external-iam/configure-keycloak-identity-management.rst
upstream_modified: true
---

<a id="configure-minio-for-authentication-using-keycloak"></a>
<a id="minio-authenticate-using-keycloak"></a>

## Overview {#overview}

This procedure configures MinIO to use [Keycloak](https://www.keycloak.org/) as an external IDentity Provider (IDP) for authentication of users via the OpenID Connect (OIDC) protocol.

This page has procedures for configuring OIDC for MinIO deployments in Kubernetes and Baremetal infrastructures.

Select the tab corresponding to your infrastructure to switch between instruction sets.

{{< tabs group="kubernetes-baremetal" >}}
{{< tab label="Kubernetes" value="kubernetes" >}}
For MinIO Tenants deployed using the [MinIO Kubernetes Operator](/operations/deployments/kubernetes/#minio-kubernetes), this procedure covers:

- Configure Keycloak for use with MinIO authentication and authorization
- Configure a new or existing MinIO Tenant to use Keycloak as the OIDC provider
- Create policies to control access of Keycloak-authenticated users
- Log into the MinIO Tenant Console using SSO and a Keycloak-managed identity
- Generate temporary S3 access credentials using the `AssumeRoleWithWebIdentity` Security Token Service (STS) API
{{< /tab >}}
{{< tab label="Baremetal" value="baremetal" >}}
For MinIO deployments on baremetal infrastructure, this procedure covers:

- Configure Keycloak for use with MinIO authentication and authorization
- Configure a new or existing MinIO cluster to use Keycloak as the OIDC provider
- Create policies to control access of Keycloak-authenticated users
- Log into the MinIO Console using SSO and a Keycloak-managed identity
- Generate temporary S3 access credentials using the `AssumeRoleWithWebIdentity` Security Token Service (STS) API
{{< /tab >}}
{{< /tabs >}}

This procedure was written and tested against Keycloak `21.0.0`. The provided instructions may work against other Keycloak versions. This procedure assumes you have prior experience with Keycloak and have reviewed [their documentation](https://www.keycloak.org/documentation) for guidance and best practices in deploying, configuring, and managing the service.

## Prerequisites {#prerequisites}

### Keycloak Deployment and Realm Configuration {#keycloak-deployment-and-realm-configuration}

This procedure assumes an existing Keycloak deployment to which you have administrative access. Specifically, you must have permission to create and configure Realms, Clients, Client Scopes, Realm Roles, Users, and Groups on the Keycloak deployment.

{{< tabs group="kubernetes-baremetal" >}}
{{< tab label="Kubernetes" value="kubernetes" >}}
For Keycloak deployments within the same Kubernetes cluster as the MinIO Tenant, this procedure assumes bidirectional access between the Keycloak and MinIO pods/services. For Keycloak deployments external to the Kubernetes cluster, this procedure assumes an existing Ingress, Load Balancer, or similar Kubernetes network control component that manages network access to and from the MinIO Tenant.
{{< /tab >}}
{{< tab label="Baremetal" value="baremetal" >}}
The MinIO deployment must have bidirectional access to the target OIDC service.
{{< /tab >}}
{{< /tabs >}}

Ensure each user identity intended for use with MinIO has the appropriate [claim](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid-access-control) configured such that MinIO can associate a [policy](/administration/identity-access-management/policy-based-access-control/#minio-policy) to the authenticated user. An OpenID user with no assigned policy has no permission to access any action or resource on the MinIO cluster.

### Access to MinIO Cluster {#access-to-minio-cluster}

{{< tabs group="kubernetes-baremetal" >}}
{{< tab label="Kubernetes" value="kubernetes" >}}
You must have access to the MinIO Operator Console web UI. You can either expose the MinIO Operator Console service using your preferred Kubernetes routing component, or use temporary port forwarding to expose the Console service port on your local machine.
{{< /tab >}}
{{< tab label="Baremetal" value="baremetal" >}}
This procedure uses [`mc`](/reference/minio-mc/#command-mc) for performing operations on the MinIO cluster. Install `mc` on a machine with network access to the cluster. See the `mc` [Installation Quickstart](/reference/minio-mc/#mc-install) for instructions on downloading and installing `mc`.

This procedure assumes a configured [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) for the MinIO cluster.
{{< /tab >}}
{{< /tabs >}}

<a id="minio-external-identity-management-keycloak-configure"></a>

## Configure MinIO for Keycloak Identity Management {#configure-minio-for-keycloak-identity-management}

{{< tabs group="kubernetes-baremetal" >}}
{{< tab label="Kubernetes" value="kubernetes" >}}
1. Configure or Create a Client for Accessing Keycloak

   Authenticate to the Keycloak **Administrative Console** and navigate to **Clients**.

   Select **Create client** and follow the instructions to create a new Keycloak client for MinIO. Fill in the specified inputs as follows:

   <table>
     <tbody>
       <tr>
         <td><p>Client ID</p></td>
         <td><p>Set to a unique identifier for MinIO (<code>minio</code>)</p></td>
       </tr>
       <tr>
         <td><p>Client type</p></td>
         <td><p>Set to <code>OpenID Connect</code></p></td>
       </tr>
       <tr>
         <td><p>Always display in console</p></td>
         <td><p>Toggle to <code>On</code></p></td>
       </tr>
       <tr>
         <td><p>Client authentication</p></td>
         <td><p>Toggle to <code>On</code></p></td>
       </tr>
       <tr>
         <td><p>Authentication flow</p></td>
         <td><p>Toggle on <code>Standard flow</code></p></td>
       </tr>
       <tr>
         <td><p>(Optional) Authentication flow</p></td>
         <td><p>Toggle on <code>Direct access grants</code> (API testing)</p></td>
       </tr>
     </tbody>
   </table>

   Keycloak deploys the client with a default set of configuration values. Modify these values as necessary for your Keycloak setup and desired behavior. The following table provides a baseline of settings and values to configure:

   <table>
     <tbody>
       <tr>
         <td><p>Root URL</p></td>
         <td><p>Set to <code>${authBaseUrl}</code></p></td>
       </tr>
       <tr>
         <td><p>Home URL</p></td>
         <td><p>Set to the Realm you want MinIO to use (<code>/realms/master/account/</code>)</p></td>
       </tr>
       <tr>
         <td><p>Valid Redirect URI</p></td>
         <td><p>Set to <code>*</code></p></td>
       </tr>
       <tr>
         <td><p>Keys -&gt; Use JWKS URL</p></td>
         <td><p>Toggle to <code>On</code></p></td>
       </tr>
       <tr>
         <td><p>Advanced -&gt; Advanced Settings -&gt; Access Token Lifespan</p></td>
         <td><p>Set to <code>1 Hour</code>.</p></td>
       </tr>
     </tbody>
   </table>
2. Create Client Scope for MinIO Client

   Client scopes allow Keycloak to map user attributes as part of the JSON Web Token (JWT) returned in authentication requests. This allows MinIO to reference those attributes when assigning policies to the user. This step creates the necessary client scope to support MinIO authorization after successful Keycloak authentication.

   Navigate to the **Client scopes** view and create a new client scope for MinIO authorization:

   <table>
     <tbody>
       <tr>
         <td><p>Name</p></td>
         <td><p>Set to any recognizable name for the policy (<code>minio-authorization</code>)</p></td>
       </tr>
       <tr>
         <td><p>Include in token scope</p></td>
         <td><p>Toggle to <code>On</code></p></td>
       </tr>
     </tbody>
   </table>

   Once created, select the scope from the list and navigate to **Mappers**.

   Select **Configure a new mapper** to create a new mapping:

   <table>
     <tbody>
       <tr>
         <td><p>User Attribute</p></td>
         <td><p>Select the Mapper Type</p></td>
       </tr>
       <tr>
         <td><p>Name</p></td>
         <td><p>Set to any recognizable name for the mapping (<code>minio-policy-mapper</code>)</p></td>
       </tr>
       <tr>
         <td><p>User Attribute</p></td>
         <td><p>Set to <code>policy</code></p></td>
       </tr>
       <tr>
         <td><p>Token Claim Name</p></td>
         <td><p>Set to <code>policy</code></p></td>
       </tr>
       <tr>
         <td><p>Add to ID token</p></td>
         <td><p>Set to <code>On</code></p></td>
       </tr>
       <tr>
         <td><p>Claim JSON Type</p></td>
         <td><p>Set to <code>String</code></p></td>
       </tr>
       <tr>
         <td><p>Multivalued</p></td>
         <td><p>Set to <code>On</code></p><p>This allows setting multiple <code>policy</code> values in the single claim.</p></td>
       </tr>
       <tr>
         <td><p>Aggregate attribute values</p></td>
         <td><p>Set to <code>On</code></p><p>This allows users to inherit any <code>policy</code> set in their Groups</p></td>
       </tr>
     </tbody>
   </table>

   Once created, assign the Client Scope to the MinIO client.

   1. Navigate to **Clients** and select the MinIO client.
   2. Select **Client scopes**, then select **Add client scope**.
   3. Select the previously created scope and set the **Assigned type** to `default`.
3. Apply the Necessary Attribute to Keycloak Users/Groups

   You must assign an attribute named `policy` to the Keycloak Users or Groups. Set the value to any [policy](/administration/identity-access-management/policy-based-access-control/#minio-policy) on the MinIO deployment.

   For Users, navigate to **Users** and select or create the User:

   <table>
     <tbody>
       <tr>
         <td><p>Credentials</p></td>
         <td><p>Set the user password to a permanent value if not already set</p></td>
       </tr>
       <tr>
         <td><p>Attributes</p></td>
         <td><p>Create a new attribute with key <code>policy</code> and value of any <a href="/administration/identity-access-management/policy-based-access-control/#minio-policy">policy</a> (<code>consoleAdmin</code>)</p></td>
       </tr>
     </tbody>
   </table>

   For Groups, navigate to **Groups** and select or create the Group:

   <table>
     <tbody>
       <tr>
         <td><p>Attributes</p></td>
         <td><p>Create a new attribute with key <code>policy</code> and value of any <a href="/administration/identity-access-management/policy-based-access-control/#minio-policy">policy</a> (<code>consoleAdmin</code>)</p></td>
       </tr>
     </tbody>
   </table>

   You can assign users to groups such that they inherit the specified `policy` attribute. If you set the Mapper settings to enable **Aggregate attribute values**, Keycloak includes the aggregated array of policies as part of the authenticated user’s JWT token. MinIO can use this list of policies when authorizing the user.

   You can test the configured policies of a user by using the Keycloak API:

   ```shell
   curl -d "client_id=minio" \
        -d "client_secret=secretvalue" \
        -d "grant_type=password" \
        -d "username=minio-user-1" \
        -d "password=minio-user-1-password" \
        http://keycloak-service.keycloak-namespace.svc.cluster-domain.example/realms/REALM/protocol/openid-connect/token
   ```

   If successful, the `access_token` contains the JWT necessary to use the MinIO [AssumeRoleWithWebIdentity](/developers/security-token-service/AssumeRoleWithWebIdentity/#minio-sts-assumerolewithwebidentity) STS API and generate S3 credentials.

   You can use a JWT decoder to review the payload and ensure it contains the `policy` key with one or more MinIO policies listed.
4. Configure MinIO for Keycloak Authentication

You can use the [`mc idp openid add`](/reference/minio-mc/mc-idp-openid/#mc.idp.openid.add) command to create a new configuration for the Keycloak service. The command takes all supported [OpenID Configuration Settings](/reference/minio-server/settings/iam/openid/#minio-open-id-config-settings):

```shell
mc idp openid add ALIAS PRIMARY_IAM \
   client_id=MINIO_CLIENT \
   client_secret=MINIO_CLIENT_SECRET \
   config_url="https://keycloak-service.keycloak-namespace.svc.cluster-domain.example/realms/REALM/.well-known/openid-configuration" \
   display_name="SSO_IDENTIFIER"
   scopes="openid,email,preferred_username" \
   redirect_uri_dynamic="on"
```

<table>
  <tbody>
    <tr>
      <td><p><code>PRIMARY_IAM</code></p></td>
      <td><p>Set to a unique identifier for the Keycloak service, such as <code>keycloak_primary</code></p></td>
    </tr>
    <tr>
      <td><code>MINIO_CLIENT</code><br /><code>MINIO_CLIENT_SECRET</code><br /></td>
      <td><p>Set to the Keycloak client ID and secret configured in Step 1</p></td>
    </tr>
    <tr>
      <td><p><code>config_url</code></p></td>
      <td><p>Set to the address of the Keycloak OpenID configuration document (keycloak-url.example.net:8080)</p></td>
    </tr>
    <tr>
      <td><p><code>display_name</code></p></td>
      <td><p>Set to a user-facing name the MinIO Console displays as part of the Single-Sign On (SSO) workflow for the configured Keycloak service</p></td>
    </tr>
    <tr>
      <td><p><code>scopes</code></p></td>
      <td><p>Set to a list of OpenID scopes you want to include in the JWT, such as <code>preferred_username</code> or <code>email</code></p></td>
    </tr>
    <tr>
      <td><p><code>redirect_uri_dynamic</code></p></td>
      <td><p>Set to <code>on</code></p><p>Substitutes the MinIO Console address used by the client as part of the Keycloak redirect URI.
Keycloak returns authenticated users to the Console using the provided URI.</p><p>For MinIO Console deployments behind a reverse proxy, load balancer, or similar network control plane, you can instead use the <a href="/reference/minio-server/settings/console/#envvar.MINIO_BROWSER_REDIRECT_URL"><code>MINIO_BROWSER_REDIRECT_URL</code></a> variable to set the redirect address for Keycloak to use.</p></td>
    </tr>
  </tbody>
</table>

Restart the MinIO deployment for the changes to apply.

Check the MinIO logs and verify that startup succeeded with no errors related to the OIDC configuration.

1. Generate Application Credentials using the Security Token Service (STS)

   Applications using an S3-compatible SDK must specify credentials in the form of an access key and secret key. The MinIO [AssumeRoleWithWebIdentity](/developers/security-token-service/AssumeRoleWithWebIdentity/#minio-sts-assumerolewithwebidentity) API returns the necessary temporary credentials, including a required session token, using a JWT returned by Keycloak after authentication.

   You can test this workflow using the following sequence of HTTP calls and the `curl` utility:

   1. Authenticate as a Keycloak user and retrieve the JWT token

      ```shell
      curl -X POST "https://keycloak-service.keycloak-namespace.svc.cluster-domain.example/realms/REALM/protocol/openid-connect/token" \
           -H "Content-Type: application/x-www-form-urlencoded" \
           -d "username=USER" \
           -d "password=PASSWORD" \
           -d "grant_type=password" \
           -d "client_id=CLIENT" \
           -d "client_secret=SECRET"
      ```

      - Replace the `USER` and `PASSWORD` with the credentials of a Keycloak user on the `REALM`.
      - Replace the `CLIENT` and `SECRET` with the client ID and secret for the MinIO-specific Keycloak client on the `REALM`

      You can process the results using `jq` or a similar JSON-formatting utility. Extract the `access_token` field to retrieve the necessary access token. Pay attention to the `expires_in` field to note the number of seconds before the token expires.
   2. Generate MinIO Credentials using the `AssumeRoleWithWebIdentity` API

      ```shell
      curl -X POST "https://minio.minio-tenant.svc.cluster-domain.example" \
           -H "Content-Type: application/x-www-form-urlencoded" \
           -d "Action=AssumeRoleWithWebIdentity" \
           -d "Version=2011-06-15" \
           -d "DurationSeconds=86000" \
           -d "WebIdentityToken=TOKEN"
      ```

      Replace the `TOKEN` with the `access_token` value returned by Keycloak.

      The API returns an XML document on success containing the following keys:

      - `Credentials.AccessKeyId` - the Access Key for the Keycloak User
      - `Credentials.SecretAccessKey` - the Secret Key for the Keycloak User
      - `Credentials.SessionToken` - the Session Token for the Keycloak User
      - `Credentials.Expiration` - the Expiration Date for the generated credentials
   3. Test the Credentials

      Use your preferred S3-compatible SDK to connect to MinIO using the generated credentials.

      For example, the following Python code using the MinIO [Python SDK](/developers/python/minio-py/#minio-python-quickstart) connects to the MinIO deployment and returns a list of buckets:

      ```python
      from minio import Minio

      client = MinIO(
         "minio.minio-tenant.svc.cluster-domain.example",
         access_key = "ACCESS_KEY",
         secret_key = "SECRET_KEY",
         session_token = "SESSION_TOKEN"
         secure = True
      )

      client.list_buckets()
      ```

2. Next Steps

Applications should implement the [STS AssumeRoleWithWebIdentity](/developers/security-token-service/AssumeRoleWithWebIdentity/#minio-sts-assumerolewithwebidentity) flow using their [SDK](/developers/minio-drivers/#minio-drivers) of choice. When STS credentials expire, applications should have logic in place to regenerate the JWT token, STS token, and MinIO credentials before retrying and continuing operations.

Alternatively, users can generate [access keys](/administration/identity-access-management/minio-user-management/#minio-id-access-keys) through the MinIO Console for the purpose of creating long-lived API-key like access using their Keycloak credentials.
{{< /tab >}}
{{< tab label="Baremetal" value="baremetal" >}}
1. Configure or Create a Client for Accessing Keycloak

   Authenticate to the Keycloak **Administrative Console** and navigate to **Clients**.

   Select **Create client** and follow the instructions to create a new Keycloak client for MinIO. Fill in the specified inputs as follows:

   <table>
     <tbody>
       <tr>
         <td><p>Client ID</p></td>
         <td><p>Set to a unique identifier for MinIO (<code>minio</code>)</p></td>
       </tr>
       <tr>
         <td><p>Client type</p></td>
         <td><p>Set to <code>OpenID Connect</code></p></td>
       </tr>
       <tr>
         <td><p>Always display in console</p></td>
         <td><p>Toggle to <code>On</code></p></td>
       </tr>
       <tr>
         <td><p>Client authentication</p></td>
         <td><p>Toggle to <code>On</code></p></td>
       </tr>
       <tr>
         <td><p>Authentication flow</p></td>
         <td><p>Toggle on <code>Standard flow</code></p></td>
       </tr>
       <tr>
         <td><p>(Optional) Authentication flow</p></td>
         <td><p>Toggle on <code>Direct access grants</code> (API testing)</p></td>
       </tr>
     </tbody>
   </table>

   Keycloak deploys the client with a default set of configuration values. Modify these values as necessary for your Keycloak setup and desired behavior. The following table provides a baseline of settings and values to configure:

   <table>
     <tbody>
       <tr>
         <td><p>Root URL</p></td>
         <td><p>Set to <code>${authBaseUrl}</code></p></td>
       </tr>
       <tr>
         <td><p>Home URL</p></td>
         <td><p>Set to the Realm you want MinIO to use (<code>/realms/master/account/</code>)</p></td>
       </tr>
       <tr>
         <td><p>Valid Redirect URI</p></td>
         <td><p>Set to <code>*</code></p></td>
       </tr>
       <tr>
         <td><p>Keys -&gt; Use JWKS URL</p></td>
         <td><p>Toggle to <code>On</code></p></td>
       </tr>
       <tr>
         <td><p>Advanced -&gt; Advanced Settings -&gt; Access Token Lifespan</p></td>
         <td><p>Set to <code>1 Hour</code>.</p></td>
       </tr>
     </tbody>
   </table>
2. Create Client Scope for MinIO Client

   Client scopes allow Keycloak to map user attributes as part of the JSON Web Token (JWT) returned in authentication requests. This allows MinIO to reference those attributes when assigning policies to the user. This step creates the necessary client scope to support MinIO authorization after successful Keycloak authentication.

   Navigate to the **Client scopes** view and create a new client scope for MinIO authorization:

   <table>
     <tbody>
       <tr>
         <td><p>Name</p></td>
         <td><p>Set to any recognizable name for the policy (<code>minio-authorization</code>)</p></td>
       </tr>
       <tr>
         <td><p>Include in token scope</p></td>
         <td><p>Toggle to <code>On</code></p></td>
       </tr>
     </tbody>
   </table>

   Once created, select the scope from the list and navigate to **Mappers**.

   Select **Configure a new mapper** to create a new mapping:

   <table>
     <tbody>
       <tr>
         <td><p>User Attribute</p></td>
         <td><p>Select the Mapper Type</p></td>
       </tr>
       <tr>
         <td><p>Name</p></td>
         <td><p>Set to any recognizable name for the mapping (<code>minio-policy-mapper</code>)</p></td>
       </tr>
       <tr>
         <td><p>User Attribute</p></td>
         <td><p>Set to <code>policy</code></p></td>
       </tr>
       <tr>
         <td><p>Token Claim Name</p></td>
         <td><p>Set to <code>policy</code></p></td>
       </tr>
       <tr>
         <td><p>Add to ID token</p></td>
         <td><p>Set to <code>On</code></p></td>
       </tr>
       <tr>
         <td><p>Claim JSON Type</p></td>
         <td><p>Set to <code>String</code></p></td>
       </tr>
       <tr>
         <td><p>Multivalued</p></td>
         <td><p>Set to <code>On</code></p><p>This allows setting multiple <code>policy</code> values in the single claim.</p></td>
       </tr>
       <tr>
         <td><p>Aggregate attribute values</p></td>
         <td><p>Set to <code>On</code></p><p>This allows users to inherit any <code>policy</code> set in their Groups</p></td>
       </tr>
     </tbody>
   </table>

   Once created, assign the Client Scope to the MinIO client.

   1. Navigate to **Clients** and select the MinIO client.
   2. Select **Client scopes**, then select **Add client scope**.
   3. Select the previously created scope and set the **Assigned type** to `default`.
3. Apply the Necessary Attribute to Keycloak Users/Groups

   You must assign an attribute named `policy` to the Keycloak Users or Groups. Set the value to any [policy](/administration/identity-access-management/policy-based-access-control/#minio-policy) on the MinIO deployment.

   For Users, navigate to **Users** and select or create the User:

   <table>
     <tbody>
       <tr>
         <td><p>Credentials</p></td>
         <td><p>Set the user password to a permanent value if not already set</p></td>
       </tr>
       <tr>
         <td><p>Attributes</p></td>
         <td><p>Create a new attribute with key <code>policy</code> and value of any <a href="/administration/identity-access-management/policy-based-access-control/#minio-policy">policy</a> (<code>consoleAdmin</code>)</p></td>
       </tr>
     </tbody>
   </table>

   For Groups, navigate to **Groups** and select or create the Group:

   <table>
     <tbody>
       <tr>
         <td><p>Attributes</p></td>
         <td><p>Create a new attribute with key <code>policy</code> and value of any <a href="/administration/identity-access-management/policy-based-access-control/#minio-policy">policy</a> (<code>consoleAdmin</code>)</p></td>
       </tr>
     </tbody>
   </table>

   You can assign users to groups such that they inherit the specified `policy` attribute. If you set the Mapper settings to enable **Aggregate attribute values**, Keycloak includes the aggregated array of policies as part of the authenticated user’s JWT token. MinIO can use this list of policies when authorizing the user.

   You can test the configured policies of a user by using the Keycloak API:

   ```shell
   curl -d "client_id=minio" \
        -d "client_secret=secretvalue" \
        -d "grant_type=password" \
        -d "username=minio-user-1" \
        -d "password=minio-user-1-password" \
        http://keycloak-url.example.net:8080/realms/REALM/protocol/openid-connect/token
   ```

   If successful, the `access_token` contains the JWT necessary to use the MinIO [AssumeRoleWithWebIdentity](/developers/security-token-service/AssumeRoleWithWebIdentity/#minio-sts-assumerolewithwebidentity) STS API and generate S3 credentials.

   You can use a JWT decoder to review the payload and ensure it contains the `policy` key with one or more MinIO policies listed.
4. Configure MinIO for Keycloak Authentication

   MinIO supports multiple methods for configuring Keycloak authentication:

   - Using a terminal/shell and the [`mc idp openid`](/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid) command
   - Using environment variables set prior to starting MinIO

   {{< tabs group="cli-environment-variables" >}}
   {{< tab label="CLI" value="cli" >}}
   You can use the [`mc idp openid add`](/reference/minio-mc/mc-idp-openid/#mc.idp.openid.add) command to create a new configuration for the Keycloak service. The command takes all supported [OpenID Configuration Settings](/reference/minio-server/settings/iam/openid/#minio-open-id-config-settings):

   ```shell
   mc idp openid add ALIAS PRIMARY_IAM \
      client_id=MINIO_CLIENT \
      client_secret=MINIO_CLIENT_SECRET \
      config_url="https://keycloak-url.example.net:8080/realms/REALM/.well-known/openid-configuration" \
      display_name="SSO_IDENTIFIER"
      scopes="openid,email,preferred_username" \
      redirect_uri_dynamic="on"
   ```

   <table>
     <tbody>
       <tr>
         <td><p><code>PRIMARY_IAM</code></p></td>
         <td><p>Set to a unique identifier for the Keycloak service, such as <code>keycloak_primary</code></p></td>
       </tr>
       <tr>
         <td><code>MINIO_CLIENT</code><br /><code>MINIO_CLIENT_SECRET</code><br /></td>
         <td><p>Set to the Keycloak client ID and secret configured in Step 1</p></td>
       </tr>
       <tr>
         <td><p><code>config_url</code></p></td>
         <td><p>Set to the address of the Keycloak OpenID configuration document (keycloak-url.example.net:8080)</p></td>
       </tr>
       <tr>
         <td><p><code>display_name</code></p></td>
         <td><p>Set to a user-facing name the MinIO Console displays as part of the Single-Sign On (SSO) workflow for the configured Keycloak service</p></td>
       </tr>
       <tr>
         <td><p><code>scopes</code></p></td>
         <td><p>Set to a list of OpenID scopes you want to include in the JWT, such as <code>preferred_username</code> or <code>email</code></p></td>
       </tr>
       <tr>
         <td><p><code>redirect_uri_dynamic</code></p></td>
         <td><p>Set to <code>on</code></p><p>Substitutes the MinIO Console address used by the client as part of the Keycloak redirect URI.
   Keycloak returns authenticated users to the Console using the provided URI.</p><p>For MinIO Console deployments behind a reverse proxy, load balancer, or similar network control plane, you can instead use the <a href="/reference/minio-server/settings/console/#envvar.MINIO_BROWSER_REDIRECT_URL"><code>MINIO_BROWSER_REDIRECT_URL</code></a> variable to set the redirect address for Keycloak to use.</p></td>
       </tr>
     </tbody>
   </table>
   {{< /tab >}}
   {{< tab label="Environment Variables" value="environment-variables" >}}
   Set the following [environment variables](/reference/minio-server/settings/iam/openid/#minio-server-envvar-external-identity-management-openid) prior to starting the container using the `-e ENVVAR=VALUE` flag.

   The following example code sets the minimum required environment variables related to configuring Keycloak as an external identity management provider.

   ```shell
   MINIO_IDENTITY_OPENID_CONFIG_URL_PRIMARY_IAM="https://keycloak-url.example.net:8080/realms/REALM/.well-known/openid-configuration"
   MINIO_IDENTITY_OPENID_CLIENT_ID_PRIMARY_IAM="MINIO_CLIENT"
   MINIO_IDENTITY_OPENID_CLIENT_SECRET_PRIMARY_IAM="MINIO_CLIENT_SECRET"
   MINIO_IDENTITY_OPENID_DISPLAY_NAME_PRIMARY_IAM="SSO_IDENTIFIER"
   MINIO_IDENTITY_OPENID_SCOPES_PRIMARY_IAM="openid,email,preferred_username"
   MINIO_IDENTITY_OPENID_REDIRECT_URI_DYNAMIC_PRIMARY_IAM="on"
   ```

   <table>
     <tbody>
       <tr>
         <td><p><code>_PRIMARY_IAM</code></p></td>
         <td><p>Replace the suffix <code>_PRIMARY_IAM</code> with a unique identifier for this Keycloak configuration.
   For example, <code>MINIO_IDENTITY_OPENID_CONFIG_URL_KEYCLOAK_PRIMARY</code>.</p><p>You can omit the suffix if you intend to only configure a single OIDC provider for the deployment.</p></td>
       </tr>
       <tr>
         <td><p><a href="/reference/minio-server/settings/iam/openid/#envvar.MINIO_IDENTITY_OPENID_CONFIG_URL"><code>CONFIG_URL</code></a></p></td>
         <td><p>Specify the address of the Keycloak OpenID configuration document (keycloak-url.example.net:8080)</p><p>Ensure the <code>REALM</code> matches the Keycloak realm you want to use for authenticating users to MinIO</p></td>
       </tr>
       <tr>
         <td><a href="/reference/minio-server/settings/iam/openid/#envvar.MINIO_IDENTITY_OPENID_CLIENT_ID"><code>CLIENT_ID</code></a><br /><a href="/reference/minio-server/settings/iam/openid/#envvar.MINIO_IDENTITY_OPENID_CLIENT_SECRET"><code>CLIENT_SECRET</code></a><br /></td>
         <td><p>Specify the Keycloak client ID and secret configured in Step 1</p></td>
       </tr>
       <tr>
         <td><p><a href="/reference/minio-server/settings/iam/openid/#envvar.MINIO_IDENTITY_OPENID_DISPLAY_NAME"><code>DISPLAY_NAME</code></a></p></td>
         <td><p>Specify the user-facing name the MinIO Console displays as part of the Single-Sign On (SSO) workflow for the configured Keycloak service</p></td>
       </tr>
       <tr>
         <td><p><a href="/reference/minio-server/settings/iam/openid/#envvar.MINIO_IDENTITY_OPENID_SCOPES"><code>OPENID_SCOPES</code></a></p></td>
         <td><p>Specify the OpenID scopes you want to include in the JWT, such as <code>preferred_username</code> or <code>email</code></p></td>
       </tr>
       <tr>
         <td><p><a href="/reference/minio-server/settings/iam/openid/#envvar.MINIO_IDENTITY_OPENID_REDIRECT_URI_DYNAMIC"><code>REDIRECT_URI_DYNAMIC</code></a></p></td>
         <td><p>Set to <code>on</code></p><p>Substitutes the MinIO Console address used by the client as part of the Keycloak redirect URI.
   Keycloak returns authenticated users to the Console using the provided URI.</p><p>For MinIO Console deployments behind a reverse proxy, load balancer, or similar network control plane, you can instead use the <a href="/reference/minio-server/settings/console/#envvar.MINIO_BROWSER_REDIRECT_URL"><code>MINIO_BROWSER_REDIRECT_URL</code></a> variable to set the redirect address for Keycloak to use.</p></td>
       </tr>
     </tbody>
   </table>

   For complete documentation on these variables, see [OpenID Identity Management Settings](/reference/minio-server/settings/iam/openid/#minio-server-envvar-external-identity-management-openid)
   {{< /tab >}}
   {{< /tabs >}}

   Restart the MinIO deployment for the changes to apply.

   Check the MinIO logs and verify that startup succeeded with no errors related to the OIDC configuration.

   If you attempt to log in with the Console, you should now see an (SSO) button using the configured **Display Name**.

   Specify a configured user and attempt to log in. MinIO should automatically redirect you to the Keycloak login entry. Upon successful authentication, Keycloak should redirect you back to the MinIO Console using either the originating Console URL *or* the **Redirect URI** if configured.
5. Generate Application Credentials using the Security Token Service (STS)

   Applications using an S3-compatible SDK must specify credentials in the form of an access key and secret key. The MinIO [AssumeRoleWithWebIdentity](/developers/security-token-service/AssumeRoleWithWebIdentity/#minio-sts-assumerolewithwebidentity) API returns the necessary temporary credentials, including a required session token, using a JWT returned by Keycloak after authentication.

   You can test this workflow using the following sequence of HTTP calls and the `curl` utility:

   1. Authenticate as a Keycloak user and retrieve the JWT token

      ```shell
      curl -X POST "https://keycloak-url.example.net:8080/realms/REALM/protocol/openid-connect/token" \
           -H "Content-Type: application/x-www-form-urlencoded" \
           -d "username=USER" \
           -d "password=PASSWORD" \
           -d "grant_type=password" \
           -d "client_id=CLIENT" \
           -d "client_secret=SECRET"
      ```

      - Replace the `USER` and `PASSWORD` with the credentials of a Keycloak user on the `REALM`.
      - Replace the `CLIENT` and `SECRET` with the client ID and secret for the MinIO-specific Keycloak client on the `REALM`

      You can process the results using `jq` or a similar JSON-formatting utility. Extract the `access_token` field to retrieve the necessary access token. Pay attention to the `expires_in` field to note the number of seconds before the token expires.
   2. Generate MinIO Credentials using the `AssumeRoleWithWebIdentity` API

      ```shell
      curl -X POST "https://minio-url.example.net:9000" \
           -H "Content-Type: application/x-www-form-urlencoded" \
           -d "Action=AssumeRoleWithWebIdentity" \
           -d "Version=2011-06-15" \
           -d "DurationSeconds=86000" \
           -d "WebIdentityToken=TOKEN"
      ```

      Replace the `TOKEN` with the `access_token` value returned by Keycloak.

      The API returns an XML document on success containing the following keys:

      - `Credentials.AccessKeyId` - the Access Key for the Keycloak User
      - `Credentials.SecretAccessKey` - the Secret Key for the Keycloak User
      - `Credentials.SessionToken` - the Session Token for the Keycloak User
      - `Credentials.Expiration` - the Expiration Date for the generated credentials
   3. Test the Credentials

      Use your preferred S3-compatible SDK to connect to MinIO using the generated credentials.

      For example, the following Python code using the MinIO [Python SDK](/developers/python/minio-py/#minio-python-quickstart) connects to the MinIO deployment and returns a list of buckets:

      ```python
      from minio import Minio

      client = MinIO(
         "minio-url.example.net:9000",
         access_key = "ACCESS_KEY",
         secret_key = "SECRET_KEY",
         session_token = "SESSION_TOKEN"
         secure = True
      )

      client.list_buckets()
      ```

6. Next Steps

   Applications should implement the [STS AssumeRoleWithWebIdentity](/developers/security-token-service/AssumeRoleWithWebIdentity/#minio-sts-assumerolewithwebidentity) flow using their [SDK](/developers/minio-drivers/#minio-drivers) of choice. When STS credentials expire, applications should have logic in place to regenerate the JWT token, STS token, and MinIO credentials before retrying and continuing operations.

   Alternatively, users can generate [access keys](/administration/identity-access-management/minio-user-management/#minio-id-access-keys) through the MinIO Console for the purpose of creating long-lived API-key like access using their Keycloak credentials.
{{< /tab >}}
{{< /tabs >}}

## Enable the Keycloak Admin REST API {#enable-the-keycloak-admin-rest-api}

MinIO supports using the Keycloak Admin REST API for checking if an authenticated user exists *and* is enabled on the Keycloak realm. This functionality allows MinIO to more quickly remove access from previously authenticated Keycloak users. Without this functionality, the earliest point in time that MinIO could disable access for a disabled or removed user is when the last retrieved authentication token expires.

This procedure assumes an existing MinIO deployment configured with Keycloak as an external identity manager.

### 1) Create the Necessary Client Scopes {#create-the-necessary-client-scopes}

Navigate to the **Client scopes** view and create a new scope:

<table>
  <tbody>
    <tr>
      <td><p>Name</p></td>
      <td><p>Set to a recognizable name for the scope (<code>minio-admin-API-access</code>)</p></td>
    </tr>
    <tr>
      <td><p>Mappers</p></td>
      <td><p>Select Configure a new mapper</p></td>
    </tr>
    <tr>
      <td><p>Audience</p></td>
      <td><p>Set the Name to any recognizable name for the mapping (<code>minio-admin-api-access-mapper</code>)</p></td>
    </tr>
    <tr>
      <td><p>Included Client Audience</p></td>
      <td><p>Set to <code>security-admin-console</code>.</p></td>
    </tr>
  </tbody>
</table>

Navigate to **Clients** and select the MinIO client

1. From **Service account roles**, select **Assign role** and assign the `admin` role
2. From **Client scopes**, select **Add client scope** and add the previously created scope

Navigate to **Settings** and ensure **Authentication flow** includes `Service accounts roles`.

### 2) Validate Admin API Access {#validate-admin-api-access}

You can validate the functionality by using the Admin REST API with the MinIO client credentials to retrieve a bearer token and user data:

1. Retrieve the bearer token:

   ```shell
   curl -d "client_id=minio" \
        -d "client_secret=secretvalue" \
        -d "grant_type=password" \
        http://keycloak-url:port/admin/realms/REALM/protocol/openid-connect/token
   ```

2. Use the value returned as the `access_token` to access the Admin API:

   ```shell
   curl -H "Authentication: Bearer ACCESS_TOKEN_VALUE" \
        http://keycloak-url:port/admin/realms/REALM/users/UUID
   ```

   Replace `UUID` with the unique ID for the user which you want to retrieve. The response should resemble the following:

   ```json
   {
      "id": "954de141-781b-4eaf-81bf-bf3751cdc5f2",
      "createdTimestamp": 1675866684976,
      "username": "minio-user-1",
      "enabled": true,
      "totp": false,
      "emailVerified": false,
      "firstName": "",
      "lastName": "",
      "attributes": {
         "policy": [
            "readWrite"
         ]
      },
      "disableableCredentialTypes": [],
      "requiredActions": [],
      "notBefore": 0,
      "access": {
         "manageGroupMembership": true,
         "view": true,
         "mapRoles": true,
         "impersonate": true,
         "manage": true
      }
   }
   ```

   MinIO would revoke access for an authenticated user if the returned value has `enabled: false` or `null` (user was removed from Keycloak).

### 3) Enable Keycloak Admin Support on MinIO {#enable-keycloak-admin-support-on-minio}

MinIO supports multiple methods for configuring Keycloak Admin API Support:

- Using a terminal/shell and the [`mc idp openid`](/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid) command
- Using environment variables set prior to starting MinIO

{{< tabs group="cli-environment-variables" >}}
{{< tab label="CLI" value="cli" >}}
You can use the [`mc idp openid update`](/reference/minio-mc/mc-idp-openid/#mc.idp.openid.update) command to modify the configuration settings for an existing Keycloak service. You can alternatively include the following configuration settings when setting up Keycloak for the first time. The command takes all supported [OpenID Configuration Settings](/reference/minio-server/settings/iam/openid/#minio-open-id-config-settings):

```shell
mc idp openid update ALIAS KEYCLOAK_IDENTIFIER \
   vendor="keycloak" \
   keycloak_admin_url="https://keycloak-url:port/admin"
   keycloak_realm="REALM"
```

- Replace `KEYCLOAK_IDENTIFIER` with the name of the configured Keycloak IDP. You can use [`mc idp openid ls`](/reference/minio-mc/mc-idp-openid/#mc.idp.openid.ls) to view all configured IDP configurations on the MinIO deployment
- Specify the Keycloak admin URL in the [`keycloak_admin_url`](/reference/minio-server/settings/iam/openid/#mc-conf.identity_openid.keycloak_admin_url) configuration setting
- Specify the Keycloak Realm name in the [`keycloak_realm`](/reference/minio-server/settings/iam/openid/#mc-conf.identity_openid.keycloak_realm)
{{< /tab >}}
{{< tab label="Environment Variables" value="environment-variables" >}}
Set the following [environment variables](/reference/minio-server/settings/iam/openid/#minio-server-envvar-external-identity-management-openid) in the appropriate configuration location, such as `/etc/default/minio`.

The following example code sets the minimum required environment variables related to enabling the Keycloak Admin API for an existing Keycloak configuration. Replace the suffix `_PRIMARY_IAM` with the unique identifier for the target Keycloak configuration.

```shell
MINIO_IDENTITY_OPENID_VENDOR_PRIMARY_IAM="keycloak"
MINIO_IDENTITY_OPENID_KEYCLOAK_ADMIN_URL_PRIMARY_IAM="https://keycloak-url:port/admin"
MINIO_IDENTITY_OPENID_KEYCLOAK_REALM_PRIMARY_IAM="REALM"
```

- Specify the Keycloak admin URL in the [`MINIO_IDENTITY_OPENID_KEYCLOAK_ADMIN_URL`](/reference/minio-server/settings/iam/openid/#envvar.MINIO_IDENTITY_OPENID_KEYCLOAK_ADMIN_URL)
- Specify the Keycloak Realm name in the [`MINIO_IDENTITY_OPENID_KEYCLOAK_REALM`](/reference/minio-server/settings/iam/openid/#envvar.MINIO_IDENTITY_OPENID_KEYCLOAK_REALM)
{{< /tab >}}
{{< /tabs >}}

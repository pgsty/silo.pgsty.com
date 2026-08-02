---
title: "mc anonymous"
url: "/reference/minio-mc/mc-anonymous/"
weight: 30
icon: fa-solid fa-user-secret
minio_origin: true
silo_modified: false
---

<a id="mc-anonymous"></a>

<a id="command-mc.anonymous"></a>

## Description {#description}

The [`mc anonymous`](#command-mc.anonymous) command supports setting or removing anonymous [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) to a bucket and its contents. Buckets with anonymous policies allow public access where clients can perform any action granted by the policy without [authentication](/administration/identity-access-management/#minio-authentication-and-identity-management).

## Subcommands {#subcommands}

[`mc anonymous`](#command-mc.anonymous) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-anonymous-get/#command-mc.anonymous.get"><code>get</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-anonymous-get/#command-mc.anonymous.get"><code>mc anonymous get</code></a> command gets the anonymous (i.e. unauthenticated or
public) access <a href="/administration/identity-access-management/policy-based-access-control/#minio-policy">policies</a> for a bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-anonymous-get-json/#command-mc.anonymous.get-json"><code>get-json</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-anonymous-get-json/#command-mc.anonymous.get-json"><code>mc anonymous get-json</code></a> command gets anonymous (i.e. unauthenticated or
public) access <a href="/administration/identity-access-management/policy-based-access-control/#minio-policy">policies</a> for a bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-anonymous-links/#command-mc.anonymous.links"><code>links</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-anonymous-links/#command-mc.anonymous.links"><code>mc anonymous links</code></a> retrieves the HTTP URL for anonymous (i.e.
unauthenticated or public) access to a bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-anonymous-list/#command-mc.anonymous.list"><code>list</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-anonymous-list/#command-mc.anonymous.list"><code>mc anonymous list</code></a> retrieves all anonymous (i.e. unauthenticated or
public) access policies for a bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-anonymous-set/#command-mc.anonymous.set"><code>set</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-anonymous-set/#command-mc.anonymous.set"><code>mc anonymous set</code></a> command sets anonymous (i.e. unauthenticated or public)
access <a href="/administration/identity-access-management/policy-based-access-control/#minio-policy">policies</a> for a bucket.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-anonymous-set-json/#command-mc.anonymous.set-json"><code>set-json</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-anonymous-set-json/#command-mc.anonymous.set-json"><code>mc anonymous set-json</code></a> command sets anonymous (i.e. unauthenticated or
public) access <a href="/administration/identity-access-management/policy-based-access-control/#minio-policy">policies</a> for a bucket using using an IAM
<a href="https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-iam-policies">JSON policy document</a>.</p></td>
    </tr>
  </tbody>
</table>

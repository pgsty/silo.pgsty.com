---
title: "SUBNET"
url: "/administration/console/subnet-registration/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/53e14984e3cacacd5a0206822693f15442186bb8/source/administration/console/subnet-registration.rst
upstream_modified: false
---

<a id="subnet"></a>
<a id="minio-console-subscription"></a>

You can use the MinIO Console to perform several of the license and subscription related functions available in MinIO, such as:

- View the license you are currently using for your MinIO deployment.
- Subscribe to a commercial license, which includes access to [MinIO SUBNET](https://min.io/pricing?jmp=docs).
- Manage the deployment’s Enterprise license.
- Access Support tools for sharing with MinIO Engineering.
- Review differences between license options.

## License {#license}

MinIO offers three licensing options:

1. Open source with the [GNU AGPLv3 license](https://github.com/minio/mc/blob/master/LICENSE)
2. Enterprise Lite, a [commercial license](https://min.io/pricing?ref=docs) with included support direct from MinIO Engineers
3. Enterprise Plus, a [commercial license](https://min.io/pricing?ref=docs) with included support direct from MinIO Engineers, longer release cycle, shorter SLA, and other benefits

The **License** page shows the current license status of the deployment. You can also begin the registration process to sign up for a paid subscription or add the deployment to an existing subscription.

Deployments licensed under AGPLv3 must comply to the terms of the license. MinIO cannot make the determination as to whether your application’s usage of MinIO is in compliance with the AGPLv3 license requirements. You should instead rely on your own legal counsel or licensing specialists to audit and ensure your application is in compliance with the licenses of MinIO and all other open-source projects with which your application integrates or interacts.

MinIO Commercial Licensing is the best option for applications which trigger AGPLv3 obligations (for example, open sourcing your application). Applications using MinIO—or any other OSS-licensed code—without validating their usage do so at their own risk.

## Health {#health}

The **Health** section provides an interface for running a health diagnostic for the MinIO Deployment. For clusters connected to the Internet, the report uploads automatically to SUBNET.

The resulting health report is intended for use by MinIO Engineering via [MinIO SUBNET](https://min.io/pricing?jmp=docs) and may contain internal or private data points such as hostnames. Exercise caution before sending a health report to a third party or posting the health report in a public forum.

If desired, you can download the latest report from the page.

## Performance {#performance}

The **Performance** section provides an interface for running a performance test of the deployment. The resulting test can provide a general guideline of deployment performance under S3 `GET` and `PUT` requests.

For more complete performance testing, consider using a combination of load-testing using your staging application environments and the MinIO [WARP](https://github.com/minio/warp) tool.

## Profile {#profile}

The **Profile** section provides an interface for running system profiling of the deployment. The results can provide insight into the MinIO server process running on a given node.

The resulting report is intended for use by MinIO Engineering via [MinIO SUBNET](https://min.io/pricing?jmp=docs). Independent or third-party use of these profiles for diagnostics and remediation is done at your own risk.

## Inspect {#inspect}

The **Inspect** section provides an interface for capturing the erasure-coded metadata associated to an object or objects. MinIO Engineering may request this output as part of diagnostics in [MinIO SUBNET](https://min.io/pricing?jmp=docs).

The resulting object may be read using MinIO’s [debugging tool](https://github.com/minio/minio/tree/master/docs/debugging#decoding-metadata). Independent or third-party use of the output for diagnostics or remediation is done at your own risk. You can optionally encrypt the object such that it can only be read if the generated encryption key is included as part of the debugging toolchain.

## Call Home {#call-home}

> [!NOTE]
> **Added: Console**
>
> v0.24.0

Call Home is an optional feature where a deployment registered for [MinIO SUBNET](https://min.io/pricing?jmp=docs) can automatically send daily health diagnostic reports or real-time error logs to SUBNET. Having these reports equips engineering support with a record of diagnostics, logs, or both when responding to support requests.

MinIO installs with Call Home options disabled by default.

> [!WARNING]
> **Important**
>
> Call Home requires an active Enterprise license.

Use the **Call Home** section to enable or disable uploading either once-per-day health diagnostic reports or real-time error logs to SUBNET. The health reports and real-time logs are separate functions you can enable or disable separately. You can enable both diagnostics and logs at the same time, if desired.

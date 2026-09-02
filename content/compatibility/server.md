---
title: "Silo vs. MinIO Server Compatibility"
linkTitle: "Silo Server"
description: "A code-verified compatibility audit of the Silo server fork: binaries, configuration, S3 and admin behavior, storage internals, packaging, containers, and Helm."
url: "/compatibility/server/"
weight: 10
type: docs
icon: fa-solid fa-server
---

Silo is a maintained fork of the MinIO server. It preserves MinIO's S3-facing and on-disk compatibility, but it is **not a byte-for-byte, operationally invisible rename**. This page is the compatibility contract for moving from the upstream baseline to the Silo source prepared on 2026-08-06.

> [!WARNING]
> **Read this before replacing a MinIO deployment.** The binary, package, service account, systemd unit, default local configuration directory, container path, Helm resource names, embedded Console, update behavior, several authorization decisions, and some error responses changed. Data disks and the `MINIO_*` configuration namespace did not receive a matching rename.

## Audit scope and method {#scope}

This is a source audit, not a compilation of release-note claims.

| Boundary          | Audited value                                                                                                                                        |
|:------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------|
| Upstream baseline | [`minio/minio@7aac2a2c5b7c882e68c1ce017d8256be2feea27f`](https://github.com/minio/minio/commit/7aac2a2c5b7c882e68c1ce017d8256be2feea27f), 2026-02-11 |
| Silo snapshot     | `pgsty/silo@219670d3176a5b27ded60914390d5ee7e763cf58`, 2026-08-06                                                                                    |
| Commit set        | `7aac2a2c..219670d3`: 96 reachable commits; 93 were on `origin/main` and the final three were committed locally at audit time                        |
| Net source diff   | 523 files, 36,715 insertions, 21,450 deletions                                                                                                       |
| Interpretation    | The behavior of the final snapshot. Intermediate changes later replaced or removed are not presented as current behavior                             |

Every commit in the range was inspected. Release and security posts were used as an index of intended changes, then checked against the final implementation, tests, dependency graph, build recipes, package payloads, container entrypoint, and rendered Helm manifests. The [complete commit ledger](#ledger) prevents a documentation-only or CI-only commit from silently falling out of scope.

The range is defined by Git reachability, not author-date sorting. It therefore contains `d4cd4b433`, authored in December 2025 but joined into the post-baseline graph later; this is not an extra undocumented baseline.

The tagged [`RELEASE.2026-08-04T00-00-00Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) ends at `d88f46cce`, 18 commits before this audit head. Accordingly, this page records the **2026-08-06 prepared source state**; it does not claim that the last 18 changes were already present in a public package, image, tag, or deployed website.

## Executive compatibility matrix {#matrix}

| Surface                         | Status                                | Practical result                                                                                                                                                                                                             |
|:--------------------------------|:--------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| S3 wire API                     | Compatible with documented exceptions | Routes, XML/JSON schemas, SigV4, S3 headers, ports, and ordinary error codes retain the MinIO contract. Security and correctness fixes below deliberately reject some requests previously accepted                           |
| Data disks                      | Compatible                            | `.minio.sys`, erasure metadata, bucket/object layout, healing, replication, and encryption formats keep their names and schemas. Poisoned or unusable metadata is now rejected earlier                                       |
| Configuration                   | Mostly compatible                     | Existing `MINIO_*` variables, config keys, KMS/KES, IAM, notification, and storage settings remain. The default per-user directory becomes `~/.silo`, with a deterministic `~/.minio` fallback                               |
| Metrics and automation APIs     | Compatible                            | `minio_*` Prometheus metrics, `/minio/*` routes, `x-minio-*` headers, admin/S3 error identifiers, and release tag syntax stay unchanged                                                                                      |
| Binary and distribution         | Renamed                               | `minio` becomes `silo`; package, unit, image, chart, archives, checksums, and paths move to the Silo identity. There is no installed server-binary alias                                                                     |
| Runtime identity                | Changed                               | CLI text, banners, HTTP `Server`, User-Agent application names, FTP banner, log names, support links, and some human-readable errors say Silo                                                                                |
| Upstream network services       | Disabled                              | In-place update, update polling, callhome, SUBNET registration, and diagnostic uploads do not contact MinIO services                                                                                                         |
| Authorization/security          | Intentionally stricter                | OIDC HMAC tokens, unsafe LDAP failures, forged replication metadata, object-only grants for protected bucket writes, shadowed policy inputs, ambiguous version IDs, and several malformed internode requests change behavior |
| Embedded UI and Go dependencies | Forked behind compatible import paths | Silo Console, MCLI, and Silo Pkg are selected with `replace` directives while `github.com/minio/...` module/import paths remain                                                                                              |
| Mixed-version cluster           | Not supported for this transition     | The private `ReadMultiple` storage-REST operation was removed without bumping storage REST v63. Upgrade all nodes as one build                                                                                               |

## What deliberately stays compatible {#same}

### Protocol, storage, and configuration names {#stable-contract}

The following MinIO identifiers are compatibility identifiers, not unfinished branding work, and must remain visible:

- the Go module path `github.com/minio/minio` and the inherited `github.com/minio/...` imports;
- the `MINIO_*` environment namespace, including `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_VOLUMES`, `MINIO_OPTS`, and notification variables;
- S3 and admin routes under `/minio/*`, `x-minio-*` headers, MinIO-specific S3 extensions, and established API error codes;
- Prometheus metric names under `minio_*`;
- the `.minio.sys` internal volume and all existing disk metadata names;
- the default S3 port `9000`, existing `--address` / `--console-address` flags, and release tags of the form `RELEASE.YYYY-MM-DDTHH-MM-SSZ`;
- configuration KV formats, IAM data, KMS/KES configuration, encryption metadata, bucket metadata, replication state, and healing state.

The automated rebrand baseline records 137 compatible imports, 437 environment names, 19 metric namespaces, 84 headers, 334 routes, one internal root, three Grid namespaces, 15 storage-REST identifiers, 58 policy identifiers, and 9,014 exported symbols. The guard treats an unreviewed change to that manifest as a compatibility failure.

No data copy or metadata rewrite is required when the same disks move from MinIO to Silo. This does not mean every malformed historical object is accepted: the storage hardening described below rejects unsafe paths, invalid erasure geometry, negative part sizes, and poisoned metadata that older code could carry farther into the stack.

### Source compatibility {#source-compatibility}

The server module remains `github.com/minio/minio`. Silo selects maintained forks without forcing callers to rewrite imports:

```go
replace github.com/minio/console => github.com/pgsty/silo-console ...
replace github.com/minio/mc      => github.com/pgsty/mc ...
replace github.com/minio/pkg/v3  => github.com/pgsty/silo-pkg/v3 v3.11.0
```

This preserves most source compatibility, but it is not an assertion that every private or exported Go symbol is frozen. The internal `ReadMultiple` storage interface was removed, and the selected `silo-pkg` release has several developer-visible fixes described in [Dependencies](#dependencies).

The maintained source remote is `github.com/pgsty/silo` on branch `main`; the former `minio` branch is archived. `go install github.com/minio/minio@...` still resolves the upstream project, not Silo, so clone the Silo repository or use an explicit module `replace`. Contributions no longer require MinIO's CLA, but commits require DCO sign-off (`git commit -s`).

## Identity, binary, and outbound-service changes {#identity}

| Surface                    | Upstream baseline                                                   | Silo snapshot                                                                                                     | Compatibility consequence                                                                                             |
|:---------------------------|:--------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------|
| Server executable          | `minio` / `minio.exe`                                               | `silo` / `silo.exe`                                                                                               | Scripts and absolute paths must change. Archives, packages, and images do not install a `/usr/bin/minio` server alias |
| Version output             | MinIO identity                                                      | Silo release/commit/runtime, AGPL, upstream copyright, PGSTY modification copyright, and MinIO technology lineage | Parsers should rely on stable fields, not grep for `MinIO` prose                                                      |
| Local config home          | `~/.minio`                                                          | `~/.silo` for a new home                                                                                          | See the fallback rules below; data disks are unrelated                                                                |
| HTTP identity              | `Server: MinIO` and MinIO application UAs                           | `Server: Silo`; internal batch/fan-out/perf UAs use `silo-*` / Silo names                                         | Protocol headers such as `x-minio-*` remain unchanged; identity-sensitive monitoring may need an update               |
| Human text                 | MinIO banner, help, errors, examples, FTP greeting, support links   | Silo identity; examples prefer `mysilo`                                                                           | Exact-string log parsers and snapshots may change, not status/error codes unless listed elsewhere                     |
| Integration-visible labels | MinIO NATS/Redis connection names and Veeam model                   | NATS name `Silo Notification`, Redis `CLIENT SETNAME Silo`, Veeam model `"Silo <release>"`                        | Broker dashboards, connection-name filters, and Veeam inventory display can change                                    |
| KMS validation prose       | MinIO-branded conflict messages                                     | Brand-neutral “both KMS/KES/static-key configuration” messages                                                    | Configuration rules are the same; exact-text automation can change                                                    |
| Updater                    | Release polling and in-place update paths                           | Permanently disabled                                                                                              | `MINIO_UPDATE` is parsed but cannot re-enable it; admin update routes remain and fail stably instead of disappearing  |
| Callhome/SUBNET            | Registration, callhome, support uploads, embedded MinIO support key | Configuration is accepted for migration but forced off; no registration/upload/post; no fallback encryption key   | Remove automation that expects MinIO-operated services. Requester-key inspect encryption remains                      |
| Embedded Console           | Upstream snapshot had the Console stripped                          | Silo Console v2.1.1, English/Chinese UI, Metrics V3, no SUBNET UI                                                 | Browser behavior and assets change; the S3/Admin API boundary remains the server contract                             |
| Bundled client in OCI      | No maintained fork contract                                         | `/usr/bin/mcli` plus `/usr/bin/mc -> mcli`                                                                        | This `mc` is the client compatibility alias, never a server alias                                                     |
| Warm-tier probe            | Temporary object contains `MinIO`                                   | Same-length probe contains `Silo!`                                                                                | Only observable through backend inspection or a failed cleanup; protocol semantics do not change                      |
| Log rotation default       | `minio-*.log`                                                       | `silo-*.log`                                                                                                      | Log collectors matching filenames must change                                                                         |

The deleted `/api/health/upload` reference was an **outbound SUBNET URL path**, not a local Silo HTTP endpoint. The compatibility change is that Silo no longer issues that POST; it is incorrect to describe this as removal of a server route.

### Default configuration-directory selection {#config-dir}

Unless `--config-dir` is explicit, Silo makes one decision at startup:

| Home-directory state     | Selected directory | Message                                         |
|:-------------------------|:-------------------|:------------------------------------------------|
| Neither directory exists | `~/.silo`          | none                                            |
| Only `~/.silo` exists    | `~/.silo`          | none                                            |
| Only `~/.minio` exists   | `~/.minio`         | informational legacy notice; no files are moved |
| Both exist               | `~/.silo`          | ambiguity warning                               |

`--config-dir` always wins. Unless `--certs-dir` is also supplied, the certificate directory follows the selected configuration directory. For deterministic automation, set `--config-dir` instead of depending on filesystem discovery.

The fork adds only three server configuration controls that materially change compatibility behavior; there is no parallel `SILO_*` replacement namespace:

| Setting                                                                    | Purpose                                                         | Default                                    |
|:---------------------------------------------------------------------------|:----------------------------------------------------------------|:-------------------------------------------|
| `MINIO_API_TRUSTED_PROXIES`                                                | General source-address trust boundary                           | unset: exact historical trust-any behavior |
| `MINIO_IDENTITY_LDAP_STS_TRUSTED_PROXIES` / LDAP key `sts_trusted_proxies` | Source buckets used by LDAP STS failure limiting                | no trusted proxy; use the socket peer      |
| `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH`                                   | Temporary rollback for the protected bucket/object IAM boundary | off                                        |

Notification KV registration fixes do not rename their existing environment variables. `MINIO_UPDATE`, SUBNET, and callhome inputs are retained only as ignored/migration-compatible inputs as described next. `SILO_OPTS` appears only inside the generated inspect helper, not as a general replacement for `MINIO_OPTS`.

### Updater, callhome, SUBNET, and inspect {#offline-services}

- Startup never polls `dl.min.io`; the release URL and upstream minisign root are absent.
- `MINIO_UPDATE` values that request updates produce a warning and are ignored. Public and peer admin update handlers remain registered, returning `MethodNotAllowed` or the stable “in-place updates are disabled” error.
- Legacy `subnet` and `callhome` keys remain parseable so an old config can start. Registration state is always false, Console SUBNET variables are unset, callhome is forced off, and no diagnostic or license payload is posted.
- Inspect output is encrypted only for a requester-provided public key. It no longer falls back to MinIO's built-in support key. The helper is `start-silo.sh`, invokes `silo`, and includes `cluster.info` only in the requester-key flow.
- Upgrade through a package manager, an image rollout, or an orchestrator. Do not call `mc admin update` / `mcli admin update` against Silo as an upgrade mechanism.

## Installation and deployment compatibility {#delivery}

### RPM, DEB, and APK {#packages}

The package is `silo` for Linux amd64/arm64. Its relevant payload is:

```text
/usr/bin/silo
/usr/lib/systemd/system/silo.service
/etc/default/silo                 (config, noreplace)
/usr/lib/sysusers.d/silo.conf
/usr/share/doc/silo/LICENSE
/usr/share/doc/silo/NOTICE
```

The package creates a system `silo:silo` account without a home. It does **not** chown existing data, migrate ownership, stop a running MinIO service during installation, or declare package-manager `Provides`, `Obsoletes`, `Replaces`, or `Conflicts` against the `minio` package. Both packages can therefore be installed, but their services cannot run together through the shipped units.

`silo.service` has `Conflicts=minio.service`, runs as `silo:silo`, and reads `/etc/default/minio` first and `/etc/default/silo` second. The shipped Silo file has no active assignments, so a legacy file continues to work until an administrator overrides it in the later file. It starts:

```text
/usr/bin/silo server $MINIO_OPTS $MINIO_VOLUMES
```

Before switching the unit, make every data, certificate, KMS credential, and environment-file path readable by `silo` and every writable path writable by it. An old deployment owned by `minio:minio` will otherwise fail at startup. Package removal stops/disables `silo.service`; package upgrades do not deliberately stop the running service in the pre-remove hook.

### Container image {#container}

The source repository is `github.com/pgsty/silo`; the intended image name is `docker.io/pgsty/silo`. There is no registry-level promise that `pgsty/minio` redirects to it.

- The server exists only at `/usr/bin/silo`; an explicit `/usr/bin/minio ...` command breaks.
- The entrypoint translates a first argv word of `minio` to `silo`, and prepends `silo` when argv starts with `server`, `fmt-gen`, or an option. Consequently the common `command: minio server /data` form continues to work.
- An explicitly requested shell or utility is left alone.
- Every privilege path uses `exec`, so the server becomes PID 1 and receives `SIGTERM` for graceful shutdown instead of timing out behind the entrypoint.
- `HOME=/tmp` is the image default and is normalized to a writable directory for arbitrary-UID and legacy `MINIO_USERNAME` drop-user execution.
- Port `9000`, `/data`, and the `MINIO_*` interface remain. The amd64/arm64 image manifest also contains checksummed MCLI `RELEASE.2026-08-04T00-00-00Z` and the client-only `mc` symlink.
- OCI license material is under `/licenses/{LICENSE,NOTICE,CREDITS}`.

### Helm chart {#helm}

The inherited `helm/minio` chart, `helm-releases`, root chart index, and reindex helper were removed. The maintained chart is `helm/silo`, chart version `7.0.0`.

Most values deliberately keep their established names, including `minioAPIPort`, `minioConsolePort`, and all `MINIO_*` environment settings. The changes that matter during migration are:

- image repositories become `pgsty/silo`;
- generated resource names and labels follow chart name `silo`;
- default service account becomes `silo-sa`;
- certificate/client mount paths move from `/etc/minio/{certs,mc}` to `/etc/silo/{certs,mc}`;
- no insecure `console/console123` user is created by default (`users: []`);
- post-job examples prefer alias `mysilo`, while `myminio` is also registered so inherited `customCommands` can still resolve it;
- the new chart executes `silo`, so an image-only rollback to an old MinIO image is not safe.

To preserve the old Kubernetes object identities while adopting the new chart, start from the exact old values and set at least:

```yaml
nameOverride: minio
fullnameOverride: <the-old-full-release-name>   # for example my-release-minio
serviceAccount:
  name: minio-sa
image:
  repository: pgsty/silo
mcImage:
  repository: pgsty/silo
```

Render both charts and compare Services, selectors, StatefulSets/Deployments, PVC templates, Secrets, service account, storage mounts, environment, and ports before applying. Roll back **chart and image together**.

### Archives, provenance, and legal files {#artifacts}

Release archives are named `silo_<version>_<os>_<arch>` and contain the executable, README, LICENSE, and NOTICE. The checksum manifest is `silo_<version>_checksums.txt`; each archive receives an SPDX JSON SBOM, and the checksum set is accompanied by a keyless Sigstore bundle. Static, CGO-disabled, `kqueue`-tagged binaries are published only for Linux, macOS, and Windows on amd64/arm64; formerly compile-checked but unshipped architectures are no longer release gates. RPM/DEB/APK are built for Linux amd64/arm64, with timestamp package versions such as `YYYYMMDDHHMMSS.0.0` (RPM release `1`) and a separate package checksum manifest. Normal builds no longer stamp the build host's GOPATH/GOROOT, improving reproducibility and removing path leakage.

Unlike the upstream baseline Docker recipe, which downloaded and verified a prebuilt `dl.min.io` server, the Silo release image consumes the exact source-built, attested release archive at the selected tag. Image publication is a separate, explicitly dispatched workflow after a GitHub release; build success alone does not publish it.

`CREDITS` is regenerated from the modules actually linked into the server and guarded in CI. It is included in the OCI image; it is intentionally omitted from packages and archives because of its size. Upstream AGPL and copyright notices remain, alongside PGSTY's modification notice.

## Runtime and security behavior changes {#runtime}

These are user-visible changes even when they close a vulnerability. “Stricter” means a request, policy, token, configuration, or corrupted internal message that formerly succeeded or failed differently can now be rejected.

### Authentication, IAM, and request identity {#auth-iam}

| Change                                                                      | Final behavior                                                                                                                                                                                                                                                                                        | Who must act                                                                                                                                                                         |
|:----------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| OIDC JWT verification (`d24f449e0`)                                         | The client secret is no longer a verification key. Only asymmetric JWKS algorithms `RS256/384/512`, `ES256/384/512`, `RS3256/3384/3512`, and `ES3256/3384/3512` are accepted. `HS256/384/512` tokens fail; unknown `kid` still triggers the established JWKS refresh/retry path                       | An IdP signing Silo tokens with HMAC must migrate to an asymmetric JWKS key                                                                                                          |
| LDAP STS errors (`3b950f8fa`)                                               | Unknown user and bad password share one external `InvalidParameterValue` authentication failure. LDAP infrastructure failures remain server errors and are logged                                                                                                                                     | Clients must not distinguish account existence from response text                                                                                                                    |
| LDAP STS rate limiting (`18b712d49`, `9e10f6d9a`, `f44110890`, `5e40665ac`) | Per-source, per-node in-memory bucket: burst 10, refill one per 6 seconds, idle TTL 15 minutes. Only authentication failures consume tokens; success and infrastructure failures refund them. Exhaustion returns HTTP 429, `ThrottlingException`, `Retry-After: 6`                                    | Proxies should configure `MINIO_IDENTITY_LDAP_STS_TRUSTED_PROXIES`; it is separate from the general source-address setting                                                           |
| LDAP trusted-proxy source                                                   | For an allow-listed socket peer, clean `X-Real-IP` is preferred; otherwise XFF is walked right-to-left past trusted hops. RFC 7239 `Forwarded` is ignored. A proxy **must overwrite** X-Real-IP                                                                                                       | Review ingress header sanitation; the limiter is not a distributed account lockout                                                                                                   |
| LDAP service-account lookup                                                 | “User DN not found” matching is case-insensitive, preserving the intended Admin no-such-user / login-name error classification across dependency message capitalization                                                                                                                               | Only brittle clients that depended on the accidental misclassification see a difference                                                                                              |
| Bucket/object IAM boundary (`97b7d2804`)                                    | Twelve protected bucket-write actions no longer inherit an Allow from only `arn:aws:s3:::bucket/*`; the bare bucket ARN is required. Deny/NotResource and built-in `*` policies retain their semantics                                                                                                | Add `arn:aws:s3:::bucket` to custom policies that legitimately perform protected bucket writes, or use the temporary global escape hatch `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` |
| Protected actions                                                           | Delete/ForceDelete bucket; put/delete bucket policy; put replication, lifecycle, object-lock, versioning, or CORS; delete CORS; put bucket QoS or inventory configuration                                                                                                                             | Read/list, create bucket, tags, encryption, and notifications keep the inherited matching behavior                                                                                   |
| Effective policy inputs (`2f55347f7`)                                       | Server-derived conditions cannot be shadowed by a same-named header/query parameter. Exact keys win in the policy package. Existing/request tags, storage class, content/copy/checksum, object-lock, signature age, and list parameters are sourced from the value actually consumed by the operation | Policies that accidentally depended on attacker-controlled shadow values stop matching                                                                                               |
| Request tags                                                                | PutObject, CreateMultipartUpload, and PutObjectTagging bind `s3:RequestObjectTag/*` to the parsed input. ExistingObjectTag comes only from stored metadata. Other operation paths keep the inherited header fallback                                                                                  | Re-test tag-conditioned write policies                                                                                                                                               |
| `s3:signatureAge`                                                           | Present only for verified presigned SigV4 requests                                                                                                                                                                                                                                                    | Raw `x-amz-signature-age` injection no longer creates the condition                                                                                                                  |
| `s3:versionid` (`744a9dcd7`)                                                | Absent means absent, whitespace is normalized, and DeleteObject/MultiDelete uses the effective per-object version. A URL version cannot decoy a different XML version                                                                                                                                 | Re-test version-conditioned delete policies and any policy relying on Null                                                                                                           |
| Replication metadata (`56fa63bfd`)                                          | Ordinary PUT/COPY cannot inject internal replication status/time metadata. An authenticated replica request must have `ReplicateObjectAction`; multipart and Snowball replication flows retain their legitimate metadata                                                                              | Custom replication callers must use the authorized replication path                                                                                                                  |

The bucket-boundary escape hatch is startup-global and all-or-nothing. It exists for migration, not as a permanent mixed-policy mode. An empty or unparseable LDAP source is deliberately not placed into one shared limiter bucket; it is not throttled until a usable source can be derived.

### General source-address trust {#trusted-proxies}

`fe6dc4780` adds `MINIO_API_TRUSTED_PROXIES`, because the chosen client address feeds `aws:SourceIp`, audit `remotehost`, event `Host`, admin trace, and node-to-node forwarding.

| Value           | Result                                                                                                                                                                        |
|:----------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| unset           | Exact inherited behavior: trust source headers from any peer; left-most XFF, then X-Real-IP, then `Forwarded`                                                                 |
| `none` or `off` | Ignore all three source-address headers and use the TCP peer                                                                                                                  |
| IP/CIDR list    | Trust headers only when the TCP peer is listed; walk XFF right-to-left past trusted hops (maximum 100), then use the last X-Real-IP line, then walk `Forwarded` right-to-left |

Malformed entries, a non-empty list naming no proxy, or a remote `env://` read failure fail closed and stop startup rather than reverting to trust-any. Invalid values inside a received chain are skipped; no usable address falls back to the peer. Loopback is implicitly trusted only for the FTP/SFTP peer bridge, not skipped as an arbitrary hop inside a client chain.

The inherited `_MINIO_API_XFF_HEADER=off` retains its exact old semantics and initialization timing: it disables only XFF parsing, not X-Real-IP or `Forwarded`, and therefore is not a security boundary. Configure every cluster peer that legitimately forwards requests and ensure edge proxies overwrite or strip client-provided source headers.

### S3 request and response behavior {#s3-behavior}

| Area                           | Change and compatibility effect                                                                                                                                                                                                                                                          |
|:-------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Presigned streaming auth       | A query/presigned SigV4 request declaring `STREAMING-UNSIGNED-PAYLOAD-TRAILER` is rejected with `SignatureVersionNotSupported`; it cannot fall through to anonymous authorization. Header SigV4 is verified before body processing                                                       |
| Snowball                       | Authorization happens before tar extraction; the streaming-trailer bypass cannot write objects before a later failure                                                                                                                                                                    |
| S3 Select record limits        | CSV input, JSON Lines input, and output records over 1 MiB return an `OverMaxRecordSize` event. JSON Lines always uses the bounded reader (possibly slower on SIMD-capable CPUs), JSON parse errors use `JSONParsingError`, and already completed records can precede the terminal error |
| Streaming responses            | The tracking writer implements `Flush`; Write/Flush records an implicit HTTP 200. ListenBucketNotification/watch streams and S3 Select keepalives reach clients, while audit/status metrics record the committed status correctly                                                        |
| Multipart full-object checksum | FULL_OBJECT CRC32/CRC32C/CRC64NVME completion may omit every per-part checksum. If any are supplied they are still checked; COMPOSITE still requires every part. Explicit completion type is validated even without an object checksum value: mismatch is `BadDigest`, unknown type is `InvalidArgument`. CRC64NVME canonicalization is unchanged. A zero-byte multipart object's checksum is retained correctly |
| CopyObject checksum response | CopyObject XML and HTTP headers report the committed checksum using destination encryption context. SSE-C source key A and destination key B remain separate; same-object key rotation reports checksum fields under the new key. Stored data and checksum format are unchanged |
| Multipart part ordering        | Duplicate or non-increasing part numbers fail with `InvalidPartOrder` before assembly. Gaps and a first part other than 1 remain legal; the upload stays available for retry                                                                                                             |
| Erasure read pooling           | Correct shard-buffer ownership is restored, avoiding loss of pooling and a wrong-buffer association that could cause hangs, corruption, or severe performance loss                                                                                                                       |
| Update buffers                 | Returned download buffers are owned correctly; the public updater was subsequently disabled, so no current supported upgrade path exercises this code                                                                                                                                    |

### Distributed storage and private APIs {#storage-rest}

These changes are normally invisible to an S3 client but are compatibility changes for mixed clusters, custom internal callers, corrupted disks, and adversarial peers.

- `ReadMultiple` and its private storage-REST `/rmpl` endpoint, client method, exported Go types, and metric were removed. External S3 List/Get operations are unchanged. `storageRESTVersion` remains v63, so do not infer mixed-node compatibility from the version number.
- Every remote StorageAPI path field, nested metadata name, and raw-volume sink is validated at the storage boundary, including peer-S3 Grid messages. Lexical traversal, volume-root aliases, and Windows separator/drive forms are rejected.
- Erasure geometry, non-positive blocks, negative part sizes, and unusable stored erasure metadata are rejected at all decoded sinks and during CheckParts/VerifyFile.
- Internode allocation declarations are bounded: AppendFile caps preallocation at 1 MiB while still accepting the body; DeleteVersions grows as it decodes and rejects negative declarations; legacy ReadFile is capped at 5 GiB.
- Deadline-bounded work converts worker panics into errors and logs a bounded stack instead of taking down the process.
- `ReadParts` keeps the actual backend error across keepalive frames. An empty part list returns a successful empty result without a trace panic or leaked goroutine.
- HTTP stream helpers left orphaned by `ReadMultiple` were deleted later; that cleanup creates no additional public behavior change.

This containment is lexical. It does not resolve filesystem symlinks, and native Windows server CI was not available for the audit. Upgrade every node together and keep untrusted clients away from the internode port even though root credentials and validation protect it.

### Notification configuration and audit output {#notify-audit}

- NATS now registers parser-consumed `user_credentials`, `nkey_seed`, and `tls_handshake_first`; AMQP registers `immediate`. Existing environment variable names stay unchanged.
- The old literal `MINIO_NOTIFY_NATS_USER_CREDENTIALS` remains accepted for NATS only. Precedence is environment, new key, then old migration key.
- AMQP legacy migration maps `immediate` correctly. Invalid notification errors identify names but no longer echo credential values.
- PostgreSQL and MySQL notification configuration uses the canonical `connection_string` or `dsn_string`; explicit strings pass through unchanged. The retained internal PostgreSQL fallback builder quotes values and uses the correct `user` keyword, but discrete fields are not a supported KV input.
- Dangling-object deletion audit events once again include per-drive errors under `merrs`.

The inherited database-notification migration risk is closed by `f1ba68358`: migration no longer writes unregistered discrete connection keys. An enabled pre-KV target without `connection_string` or `dsn_string` now stops startup with a credential-free error. Convert, disable, or remove such targets before upgrading; diagnostic bundles exported before this fix may contain a historical plaintext database password and should be treated accordingly.

## Toolchain, dependencies, and embedded components {#dependencies}

The build declaration moved from Go 1.24 plus a 1.24.8 toolchain to `go 1.26.5`. That can change TLS, HTTP, DNS, scheduler, garbage-collector, and standard-library edge behavior even where no Silo source line changed. Security-sensitive dependencies were also advanced, including Go-Jose, OpenTelemetry, Go crypto/network modules, cloud SDKs, etcd, NATS, and compression libraries.

Observable edge corrections inherited through those updates include Go TLS/X.509/URL/archive fixes; MQTT oversized UTF-8 packet encoding; malformed Azure NTLM challenge handling; Thrift framed transport and 32-bit compilation; NATS authentication, authorization, identity, and denial-of-service fixes; and Prometheus remote-read/write and UI hardening. They are dependency behavior changes, not a promise that every advisory path is reachable from Silo. The jsonparser CVE-2026-32285 investigation produced no patch: the resolved v1.1.2 already contained the fix and no vulnerable reachable symbol was found, so it creates no compatibility delta in this range.

Important deliberate dependency decisions are:

| Component       | Final selection                                               | Compatibility rationale / effect                                                                                                                 |
|:----------------|:--------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------|
| Console         | `pgsty/silo-console` v2.1.1 behind `github.com/minio/console` | Restores the embedded UI, applies Silo branding and bilingual text, adds Metrics V3, removes SUBNET flows, and fixes untranslated metric legends |
| Client library  | `pgsty/mc` behind `github.com/minio/mc`                       | Keeps Console's import path while consuming the maintained MCLI fork                                                                             |
| Shared package  | `pgsty/silo-pkg/v3` v3.11.0 behind `github.com/minio/pkg/v3`  | Supplies the IAM exact-match half, LDAP TLS/StartTLS/deadline/close fixes, certificate-watcher cleanup, and RNG fixes                            |
| Kafka           | Sarama 1.45.1                                                 | Pinned to avoid a breaking broker-negotiation drift                                                                                              |
| PostgreSQL      | lib/pq 1.10.9                                                 | Pinned to avoid a nil-`[]byte` / PostgreSQL-before-14 behavior regression; generated DSN quoting is fixed in server code                         |
| Compression     | klauspost/compress 1.18.7                                     | Explicit security/correctness upgrade                                                                                                            |
| Thrift          | 0.24.0                                                        | Fixes 32-bit builds                                                                                                                              |
| systemd library | require 22.7, replace with 22.6                               | Retains NetBSD compilation until the monotonic-clock regression is fixed upstream                                                                |

The LDAP package now honors TLS fields for `ldaps://`, keeps StartTLS active even with `server_insecure`, avoids a nil-TLS panic, applies a StartTLS deadline, and closes a connection after failed StartTLS. Certificate-watcher shutdown no longer leaks; on Windows, polling can delay reload by up to about ten seconds. RNG subkey entropy/reset behavior is corrected, although the server does not exercise the reset path.

For external Go consumers of `silo-pkg`, two changes are broader than this server's own call paths: `xtime.Duration` JSON moves from integer nanoseconds to duration strings, and some AIStor action vocabulary / protected-action helpers differ from upstream. In particular, `Policy.IsAllowedActions` can disagree on protected actions; the server does not call it. The server stores the relevant state through YAML/msgp and does not call the differing AIStor/action helper paths, so no server data migration or authorization delta was found from those library changes.

Generated `String()` files were regenerated under the new toolchain. Valid enum output remains the same; the diff is generator provenance and invalid-value formatting machinery, not a separately claimed S3 behavior change.

## Changes since the 2026-08-06 audit {#since-20260806}

The sections above describe the `219670d3` snapshot. The table below records the behavior changes merged to `main` after it, up to `6586fbfd0` and the pre-release cleanup that followed; the next release audit folds them into the sections above.

| Area | Change | Where |
|:-----|:-------|:------|
| Authorization | Explicit version deletes are authorized as `s3:DeleteObjectVersion` and `DeleteObjects` authorizes each entry; user and group status changes require the action matching the target status; policy writes reject bare ARN prefixes | [#104](https://github.com/pgsty/silo/pull/104), `58735ee38`, `229fe2b3c`, `eee05a17c` (SN-2026-005, -009, -010) |
| Replication trust | Replication-only headers grant replication semantics only with the exact marker and `s3:ReplicateObject` / `s3:ReplicateDelete`; otherwise they are removed after signature verification | [#101](https://github.com/pgsty/silo/pull/101) (SN-2026-008) |
| SSE-C | Zero-byte objects and `GetObjectAttributes` authenticate the customer key; null-version and in-place key-rotation copies no longer rewrite objects into unreadable ciphertext; CopyObject reports checksums under the destination key | `b73581b05`, `474cd5801`, `05df6e70d`, `ffb70eb37`, `e73436c99` (SN-2026-006, -007) |
| Checksums | Server-side part checksums, federated `UploadPartCopy`, `ChecksumType` in `CompleteMultipartUpload`, AWS-aligned completion errors, rejection of unknown algorithms and of `CRC64NVME` with `COMPOSITE` | `7fea6d5a5`, `8d76a255c`, `d014a12cf`, `5d152416d`, `7c103389f`, `d28885d0e` |
| Listing | `ListObjects` on a missing bucket returns `NoSuchBucket` on the shortcut paths that previously returned an empty listing | `e9c5340be` |
| Per-bucket CORS | Real `?cors` API; a bucket configuration overrides the global policy; the pre-authentication lookup reads resident metadata only and otherwise applies the global policy; site replication converges CORS with a last-writer-wins register | [#71](https://github.com/pgsty/silo/pull/71), [#80](https://github.com/pgsty/silo/pull/80), [#101](https://github.com/pgsty/silo/pull/101) |
| Bucket metadata | `metadata.lock` serializes every bucket-configuration writer; `ForceCreate` and site adoption keep existing configuration; a locked bucket always carries plain Enabled versioning | [#103](https://github.com/pgsty/silo/pull/103), `dd3bdb808` |
| Site replication | Object Lock configuration replicates in its own field (the legacy `Tags` carrier is still accepted); status is accounted per site; validity probes verify permissions under the rule prefix | `3861f33cb`, `fb406fdc9`, `c9ad74673`, `5db7be4ee` |
| Configuration | Legacy database notification targets require a DSN; `MINIO_CONFIG_ENV_FILE` uses a dedicated parser that keeps named targets | `f1ba68358`, `6b0998157`, `2aea7fe9c` |
| Toolchain and components | Go 1.27.0; upstream `minio-go` `v7.3.1-0.20260828` (the same pre-release the Console and `mcli` stacks require; the `silo-go` fork is retired); `silo-pkg` v3.12.3 pre-release pin and Console `43f8447fd` (see the [Console page](/compatibility/console/)); bundled `mcli` 20260901 | `43f4bb7ed`, `4d6e1ea8e`, pre-release cleanup |

## Known residual risks and non-fixes {#limits}

This audit does not turn inherited limitations into claims of compatibility:

1. **Source IP is still forgeable by default.** Unset `MINIO_API_TRUSTED_PROXIES` deliberately retains upstream trust-any behavior. Set `none` for direct deployments or an exact proxy allowlist for proxied deployments.
2. **Some version-condition gaps remain.** MultiDelete governance-bypass reauthorization still consults the query/absent version rather than each XML entry, and Snowball reads the PAX `minio.versionId` after per-file authorization. Empty `username`, `userid`, `signatureversion`, and `authType` condition keys are also still inserted, so `Null` on them has present-empty semantics.
3. **Multipart parser defense is not complete.** Handler-level ordering is fixed, but the object layer has no independent uniqueness defense; XML-root validation and the inherited nonnumeric-part error mapping were not changed.
4. **Legacy notification migration remains risky.** Review it as described above.
5. **Storage path validation is lexical.** Symlinks are not resolved; native Windows execution was not independently covered.
6. **Private APIs are not a stable compatibility promise.** `ReadMultiple` proves that a same-numbered storage REST protocol can still lose an operation. Do not run a rolling mixed build across this boundary.
7. **A source result is not a released artifact.** This page does not assert that GitHub tags, packages, OCI manifests, signatures, or the public site contain the three audit-head-only commits until each channel is verified separately.
8. **Informational HTTP responses remain imperfectly tracked.** The response-tracking layer treats a 1xx response as final. The Flush/implicit-200 change did not introduce this behavior and does not claim to fix it.

## Migration checklist {#migration}

For a MinIO-to-Silo move, use this order:

1. Record the exact MinIO binary/tag, chart and values, image digest, package payload, service unit, environment files, config directory, data ownership, IAM policies, OIDC/LDAP settings, notification targets, and proxy topology.
2. Back up configuration and IAM metadata. Silo reads existing disks in place, but a rollback still needs the old executable/config/chart and unchanged data ownership available.
3. Replace invocations of the server binary with `silo`; do not assume `/usr/bin/minio` exists. In containers, argv-level `minio server` is translated, but the absolute path is not.
4. Decide the config directory explicitly. Reuse `--config-dir ~/.minio` or let the legacy-only fallback select it; do not create an empty `~/.silo` accidentally and then wonder why the old configuration is ignored.
5. For packages, grant `silo:silo` access to data, certificates, secrets, and logs. Move deliberate overrides into `/etc/default/silo`; understand that it overrides `/etc/default/minio`.
6. For Helm, render the old and new charts with the complete old values, preserve names with `nameOverride` / `fullnameOverride` / `serviceAccount.name` where required, and change chart plus image atomically.
7. Remove updater, callhome, SUBNET-registration, and support-upload automation. Replace it with package/image/orchestrator rollout and your own diagnostic transfer path.
8. Change HMAC-signed OIDC tokens to asymmetric JWKS. Exercise success, bad-password, unknown-user, backend-failure, and rate-limit LDAP paths.
9. Add bare bucket ARNs for the twelve protected actions. Test effective tag, signature-age, source-IP, and per-version delete conditions. Use the legacy bucket switch only as a temporary rollback lever.
10. Set `MINIO_API_TRUSTED_PROXIES=none` or an exact allowlist, sanitize all three source-address headers, and include cluster peers that forward authenticated requests.
11. Test oversized S3 Select records, streaming notifications, unsigned-trailer rejection, multipart full-object checksums, duplicate parts, replication, healing, KMS, every notification target, audit ingestion, and graceful container shutdown.
12. Upgrade all distributed nodes as one build. Keep the old chart and image paired for rollback; never roll back only one of them.

## Verification evidence {#verification}

The audit used the final source, not prose alone. At the recorded snapshot:

| Check                       | Result / boundary                                                                                                                                                                                                                         |
|:----------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Commit enumeration          | 96/96 commits classified in the ledger below; `origin/main` accounted for 93 and the local prepared head for three more                                                                                                                   |
| Net diff review             | All 523 changed paths classified across server runtime, internal protocol, dependency, delivery, documentation, tests, or superseded changes                                                                                              |
| Rebrand compatibility guard | Passed; compatibility manifest and delivery/runtime assertions unchanged, including Docker argv tests                                                                                                                                     |
| Go test suite               | Full `go test ./...` passed against `219670d31`, including `cmd`, OIDC, LDAP, notify, event targets, Grid, handlers, hash, and all S3 Select packages                                                                                     |
| Helm migration              | `buildscripts/verify-helm-migration.sh` passed: lint, render, legacy upgrade, archive, and identity comparison across seven rendered resources                                                                                            |
| Package lifecycle           | `buildscripts/package/lifecycle_test.sh` passed; package payload/provenance assertions cover empty DEB conflict metadata, unit/default paths, and legal files                                                                             |
| Site                        | Strict `make check` passed: module verification, warning-fatal Hugo render (617 EN / 615 ZH pages), and 388,962 internal references across 1,084 HTML files; `git diff --check`, bilingual anchors, and 96/96 commit coverage also passed |

Security articles contain deeper threat models and test vectors, but their historical “released/unreleased” labels describe their publication date. Where they conflict with the final snapshot, this page's audited boundary is authoritative.

## Complete commit coverage ledger {#ledger}

The hashes are in graph order. Merge, documentation, test, and CI commits are included because delivery behavior and the strength of a compatibility claim are themselves user-relevant; “no independent runtime delta” means exactly that, not “not reviewed.”

| Class                                        | Commits                                                                                                                                                                                                                                                            | Verified net effect                                                                                                                                                                                                                                                                                |
|:---------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Initial fork, Console, CI, dependency base   | `d4cd4b433`, `8630937e7`, `68521b37f`, `00f3cf74f`, `5abd9a80f`, `377fc616d`, `f2f9a40dc`, `ee55e5391`, `ce1c537eb`, `68e0ba997`, `1869bd30b`, `ff58df949`, `e4fa06394`                                                                                            | Go/SDK evolution; embedded Console restoration/fork; MCLI in OCI; replacement CI; LDAP TLS regression fix; security dependency upgrades. The two merge commits add no delta beyond their parents                                                                                                   |
| April security series                        | `d24f449e0`, `3b950f8fa`, `56fa63bfd`, `3252d5b7f`, `f444b6f37`, `efb6e5b00`, `db4c0fd5e`, `18b712d49`, `9e10f6d9a`, `f44110890`, `f48dbe777`                                                                                                                      | OIDC, LDAP STS, replication metadata, S3 Select, unsigned-trailer/Snowball, Go 1.26.2, limiter accounting/source hardening, and security documentation                                                                                                                                             |
| May–June reliability and private API         | `65795ee1f`, `5e40665ac`, `fd69c89d0`, `73ac52472`, `df627ff89`, `3e61b1d3a`, `d495d30d5`                                                                                                                                                                          | HTTP Flush, final LDAP bucketing, full S3 Select bound, ReadMultiple removal, Go 1.26.4/dependency update, and documentation-link change                                                                                                                                                           |
| Pre-August component integration             | `ce01ccbdc`, `4dfc27ce3`, `b7f52ca43`, `7babc0c39`, `c1aec0518`, `15fcc3c8a`, `3f192f3f0`                                                                                                                                                                          | Historical chart image switch, security dependency upgrade, notification-stream merge, portable dependency pins, compression, MCLI replacement, Console v2.0                                                                                                                                       |
| August runtime correctness/security          | `c8590413f`, `3e14733f1`, `924717926`, `89d346bf5`, `8069a32ac`, `a36fd8fff`, `ca7baa670`, `80e8eaa42`, `b6f70ab08`, `1af351a70`, `38366f654`, `22c1e41fd`, `97b7d2804`, `2f55347f7`, `744a9dcd7`, `fe6dc4780`, `162ded343`, `0c14d8151`, `9dd1dc172`, `2602177ef` | Multipart, erasure buffers, response commits, panic containment, path/metadata/allocation/ReadParts containment, orphan cleanup, IAM/effective values/version ID/source trust, notification/libpq, and audit details                                                                               |
| Chart hardening and audit documentation      | `dfe669862`, `5f4513fd4`, `b42ee4e8a`, `8eae745ab`                                                                                                                                                                                                                 | Secure chart user default, portal/doc routing, maintainer ignore rules, and advisories; only the chart default changes runtime delivery behavior                                                                                                                                                   |
| Release engineering through the 20260804 tag | `9c799f42d`, `10c7670b8`, `cf7df097b`, `32863c852`, `632ade111`, `1814ae52f`, `475236c79`, `11d79fddc`, `3b8a55dee`, `ca674a696`, `4c185d5a6`, `2ca4971d9`, `e064b5555`, `aa5139369`, `021110b45`, `d88f46cce`                                                     | RPM/DEB/APK, provenance, OCI publishing gates, pinned lint/generation, S3 Select test-race fix, broad CI, PID-1 signal fix, published-target cross-builds, safe release dispatch, reproducibility, stale-config removal, systemd location, honest gates, and runtime-image shutdown assertion      |
| Silo cutover and 2026-08-06 prepared head    | `15def34dc`, `77bdc4c0c`, `15ab10833`, `30749911b`, `e071bb77e`, `bd8df5166`, `6613c2a3c`, `fd2ca1c6d`, `c46b16ec6`, `c47733abc`, `f1c77d5a2`, `62717d7bf`, `6740e6978`, `b57275be3`, `05be686b8`, `a6d6d9b02`, `6bd9cf77e`, `219670d31`                           | Removes unpublished MinIO delivery residue; Silo runtime identity/offline boundary; renamed packages, OCI and Helm with migration guards; pinned fixtures; docs/repository cutover; Console 2.1.0 then 2.1.1; Node 24 actions; DCO/legal/docs polish; regenerated CREDITS; LICENSE/NOTICE delivery |

The ledger totals 96 unique commits. Changes replaced inside the range—such as Console 2.0 → 2.1.0 → 2.1.1, the historical `pgsty/minio` image/chart state, and updater-buffer code after the updater was disabled—are described only where they leave a final compatibility consequence.

## See also {#see-also}

- [MCLI](/compatibility/mcli/) — client artifact, config-directory, update, SUBNET, and command compatibility
- [Silo 20260804 release notes](/blog/release/silo-20260804/) — the earlier tagged release boundary, not the full 2026-08-06 audit head
- [Silo Pkg 3.11.0](/blog/release/pkg-3.11.0/) — shared IAM, LDAP, watcher, RNG, and developer-facing changes
- [OIDC JWT hardening](/blog/security/cve-2026-33322/), [LDAP STS hardening](/blog/security/cve-2026-33419/), [replication metadata](/blog/security/cve-2026-34204/), [S3 Select limits](/blog/security/cve-2026-39414/), and [ReadMultiple removal](/blog/security/cve-2026-42600/)
- [Unsigned-trailer query auth](/blog/security/cve-2026-41145/), [Snowball authentication](/blog/security/cve-2026-40344/), and the [jsonparser no-change finding](/blog/security/cve-2026-32285/)
- [Internode path containment](/blog/security/internode-path-containment/), [duplicate multipart parts](/blog/security/duplicate-part-numbers/), [bucket/object IAM boundary](/blog/security/object-grant-bucket-reach/), [version-ID conditions](/blog/security/s3-versionid-conditions/), [source-address trust](/blog/security/source-address-trust/), and [notification key registration](/blog/security/notify-keyspace-registration/)

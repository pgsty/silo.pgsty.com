---
title: "Native Health Checks and the Distroless Image"
linkTitle: "Healthcheck"
description: "Why the silo binary grows a healthcheck subcommand, why mc ready had to be retired as a probe, and how the single-binary distroless image is planned."
url: "/compatibility/feature/healthcheck/"
weight: 10
type: docs
icon: fa-solid fa-heart-pulse
---

> **Status**: P1 (subcommand, `2ff594f4b`) and P2 (distroless image + CI gate, `4c34d2309`) implemented in `pgsty/silo`; P3 (Helm probes) and P4 (docs) pending · **Decided**: 2026-08-06 · **Owner**: [`pgsty/silo`](https://github.com/pgsty/silo) (command, images, Helm chart), this site (docs)

Silo is getting a native `silo healthcheck` subcommand and, alongside the existing container image, a new **distroless** image variant that contains exactly one file that matters: the `silo` binary. This note records the reasoning and the design decisions before implementation, so the code has a specification to be checked against — and so that "why is it built this way?" has a permanent answer.

## Background {#background}

Today's release image (`docker.io/pgsty/silo`) is built on `ubi-micro` and ships four moving parts: the `silo` server, the `mcli` client (with an `mc` alias), a statically linked `curl`, and a POSIX-shell entrypoint script. The compose examples check container health with the bundled client:

```yaml
healthcheck:
  test: ["CMD", "mc", "ready", "local"]
```

That arrangement is inherited from upstream MinIO, and its fragility is a matter of record: when `mc` was briefly missing from the image, users found their health checks failing "with no option but to disable" ([#9](https://github.com/pgsty/silo/issues/9)). Upstream's own history rhymes — when MinIO moved to `ubi-micro` in 2023 and lost `curl`, the maintainers' answer was to lean harder on `mc ready local` (minio/minio#18373, #18389), and upstream `minio/minio` has since been archived with `server` as the only subcommand its binary ever had. Nobody upstream is going to fix this.

A distroless image forces the question. There is no shell, no `curl`, no `mc` — by design. The only program guaranteed to exist inside the container is the server binary itself. If Docker-level health checking is to exist at all in that image, the binary has to provide it.

## Why `mc ready` had to be retired as a probe {#why}

Reading the actual `mc` implementation (`cmd/ready-main.go`) shows the current health check works by accident, not by design. Four independent defects:

1. **It never fails on its own.** `mc ready` is a wait-until-ready loop: it retries every 5 seconds forever and only ever exits zero, on success. Connection refused does not break the loop. As a Docker healthcheck, the "unhealthy" verdict is produced entirely by Docker's `timeout` killing the process — the probe semantics are a side effect of SIGKILL.
2. **It checks the wrong scope.** `mc ready` requests `/minio/health/cluster` — cluster-wide write quorum. Every container's "health" therefore reflects the state of the whole cluster, which is precisely the cascading-failure anti-pattern the Kubernetes documentation warns about: lose quorum, and every node is marked unhealthy simultaneously.
3. **It has hidden failure modes.** It requires a writable `~/.mc` config directory (on a read-only rootfs or an arbitrary OpenShift UID, the probe fails while the server is perfectly healthy), it prints config-creation noise on first run, and its built-in `local` alias is hardcoded to `http://localhost:9000` — wrong the moment TLS is enabled or the port changes, a limitation users complained about upstream.
4. **It is the last functional reason to bundle a second binary.** Both `mcli` and the pinned static `curl` carry ongoing supply-chain and maintenance cost (the curl pin is stuck on v8.11.0 because a later release dropped the aarch64 build) for what a subcommand of the existing binary can do in ~150 lines.

## The decisions {#decisions}

Three tracks, deliberately decoupled:

| # | Decision |
| --- | ---------- |
| **D1** | The `silo` binary gains a `healthcheck` subcommand — a thin, anonymous HTTP client for the server's existing `/minio/health/*` endpoints. It ships in every build, so every image and bare-metal install gains the capability. |
| **D2** | The **existing image does not change**. It keeps `mcli`, `curl`, the shell entrypoint, and the `mc ready local` examples. Users of the current image who want the new probe can opt in by overriding their `healthcheck.test` — nothing is taken away and no default behavior moves. |
| **D3** | A **new distroless variant** is published alongside it, as a pilot: single binary, no shell, native `HEALTHCHECK` baked in. If the pilot proves out, it becomes the recommended default later and the switch completes; the classic image remains for compatibility either way. |

D2 and D3 answer the obvious "why not just slim the main image?" — because the main image's contents are a compatibility surface. [#9](https://github.com/pgsty/silo/issues/9) exists because that surface was changed underneath people once before. The distroless image is a new name with a new contract, so nobody's existing healthcheck, `docker exec mc` habit, or entrypoint assumption breaks while it is evaluated.

## The `silo healthcheck` command {#command}

```text
silo healthcheck [FLAGS] [CHECK]

CHECK — positional, maps 1:1 onto /minio/health/<path>:
  live          the process is serving (default; touches no external system)
  ready         live + KMS and etcd reachable, when configured
  cluster       cluster-wide write quorum
  cluster-read  cluster-wide read quorum

FLAGS:
  --address value   target host:port  (EnvVar: MINIO_ADDRESS; default ":9000",
                    an empty host is completed to 127.0.0.1)
  --url value       full base URL override (http[s]://host:port); wins over
                    --address and TLS auto-detection (EnvVar: MINIO_HEALTHCHECK_URL)
  --maintenance     cluster only: appends ?maintenance=true — asks "is it safe
                    to take this node down?" (HTTP 412 = no, it would break HA)
  --timeout value   overall deadline; defaults: 5s for live/ready, 15s for cluster*
  plus the inherited global flags: --certs-dir, --config-dir, --json, --quiet

EXIT CODE:  0 = healthy / safe to proceed · 1 = anything else
OUTPUT:     one line, e.g.
  live: ok (200, 2ms)
  cluster: unhealthy (503) server-status=iam-offline write-quorum=3 healing-drives=2
```

The design principles behind that shape:

1. **Thin client, single source of truth.** The command is only ever an HTTP client of the canonical health API. It never re-implements a check in-process, so the semantics of "healthy" live in exactly one place: the server handlers.
2. **CLI vocabulary = API vocabulary.** The check names are the endpoint paths. No new concepts to learn, nothing to keep in sync.
3. **Share the server's own configuration.** The port comes from the same `--address`/`MINIO_ADDRESS` contract the server uses, and http-vs-https is decided by the same certificate check the server itself performs at startup (`public.crt` + `private.key` in the certs directory). This is the Traefik `healthcheck` pattern — the closest prior art, which resolves its ping endpoint from the same static configuration as its server — with the TLS handling Traefik left as a `// TODO` actually implemented. It is also the direct fix for `mc ready`'s port-guessing defect.
4. **The default check is node-local.** `live` answers "is this process serving," which is the only question a per-container health status should answer. Cluster-scope checks exist, but only behind explicit arguments, mirroring `mc ready`'s `--cluster-read`/`--maintenance` so the operational vocabulary carries over.
5. **Exit codes are 0 and 1, nothing else.** The Dockerfile reference explicitly reserves exit code 2 (`vault status`, which uses 2 for "sealed", is the cautionary tale). Rich diagnostics belong in the single output line instead — Docker stores the first 4096 bytes of probe output in `docker inspect`, and the command decodes the server's diagnostic headers (`x-minio-server-status`, `x-minio-write-quorum`, `x-minio-healing-drives`) into it, which is exactly the detail a bare `curl -f` throws away.
6. **Skip TLS certificate verification, with no opt-out in v1.** This is a loopback self-probe of an anonymous endpoint carrying no data — and the kubelet's documented behavior for HTTPS `httpGet` probes is precisely the same. Matching it means one TLS deployment produces one verdict across Docker and Kubernetes; verifying by default would only manufacture false negatives, since self-signed server certs rarely carry a `127.0.0.1` SAN.

Two implementation constraints, discovered in the source, that are load-bearing rather than stylistic:

- **The request must be strictly anonymous.** The health routes are exempted from the reserved-path guard only for requests the server classifies as anonymous; attaching an `Authorization` header reclassifies the request and gets it *rejected* (`ErrAllAccessDisabled`) instead of answered.
- **The HTTP transport must set `Proxy: nil`.** Containers routinely inherit `HTTP_PROXY` without a `NO_PROXY` entry for `127.0.0.1`; a loopback probe must never route through a corporate proxy. (Traefik's healthcheck does this deliberately, for the same reason.)

And one number that looks arbitrary but is not: the 15-second default timeout for cluster checks exists because the server evaluates cluster health under its own 10-second `cluster_deadline` — a client that gives up at 5s abandons the request before the server delivers its considered 503, losing every diagnostic header with it. Two details were added after adversarial review: `--url` is environment-backed (`MINIO_HEALTHCHECK_URL`) because a probe process cannot see the server's command line — it is the documented way to point a baked-in `HEALTHCHECK` at a server whose address or TLS setup comes from CLI arguments; and any outer (Docker) timeout must exceed the probe's own deadline, or the probe is SIGKILLed before it can print its diagnostic line.

## What the endpoints really do {#endpoints}

The table below is verified against the handler source, not quoted from documentation — and it corrects a common misreading:

| Endpoint | Returns 200 when… | Fails with… | Notes |
| --- | --- | --- | --- |
| `/minio/health/live` | almost always — **even before the object layer is initialized** (that state is only signaled via the `x-minio-server-status: offline` header) | 503 when the request queue is saturated | touches no external system; the only endpoint quiet enough for high-frequency probing |
| `/minio/health/ready` | as `live`, **plus** KMS can generate a key and etcd answers a read — each only if configured | KMS/etcd failure; queue saturation | **without KMS or etcd, `ready` and `live` are the same code path** |
| `/minio/health/cluster` | object layer, bucket metadata and IAM are initialized, **and every erasure set** has write quorum | 503 with quorum diagnostic headers; with `?maintenance=true`, failure is **412** | each failed evaluation writes a server-side log line — do not poll it tightly |
| `/minio/health/cluster/read` | the read-quorum version of the above | as above | |

Consequences worth spelling out: `live` and `ready` are *liveness*-grade signals — they do not tell you the node can serve objects; only the `cluster` pair does. That is exactly why the cluster pair must stay out of per-container probes (scope, log noise, cascading restarts) and why it is the right tool for operational questions like "may I take this node down?" (`--maintenance`, where 200 means safe and 412 means you would lose HA).

## The distroless variant {#distroless}

**Base**: `gcr.io/distroless/static-debian12` — which is sufficient because `silo` builds with `CGO_ENABLED=0`. The base ships the four things the server actually needs from a rootfs: CA certificates (for KMS/webhook/STS egress), tzdata, `/tmp`, and an `/etc/passwd` with `root`/`nonroot` entries. It ships no shell, no package manager, no libc.

Sketch of the contract:

```dockerfile
FROM gcr.io/distroless/static-debian12:latest
COPY silo /usr/bin/silo
COPY LICENSE NOTICE CREDITS /licenses/
ENV HOME=/tmp
# /data is created in the image layer, world-writable — see issue #55:
# there is no entrypoint left to repair ownership at runtime.
VOLUME ["/data"]
EXPOSE 9000
HEALTHCHECK --interval=30s --timeout=10s --start-period=2m --start-interval=2s --retries=3 \
  CMD ["/usr/bin/silo", "healthcheck", "ready"]
ENTRYPOINT ["/usr/bin/silo"]
```

The decisions folded into that sketch:

- **`ENTRYPOINT` is the binary itself.** `docker run pgsty/silo:distroless server /data` — no argv-translation script, because there is no shell to run one. The classic image's `MINIO_USERNAME`/`MINIO_GROUPNAME` privilege-drop path (which needs GNU `chroot` and a writable `/etc/passwd`) is **not supported** in this variant; the supported mechanism is `--user` / Kubernetes `runAsUser`.
- **`/data` is created in the layer, mode 0777, and the default user stays root for the pilot.** Issue [#55](https://github.com/pgsty/silo/issues/55) demonstrated that declaring `VOLUME ["/data"]` without creating it breaks *every* non-root invocation, and that no entrypoint can repair it after the fact — in distroless there is no entrypoint at all. Creating it world-writable in the layer is the one option that makes all privilege modes work (`--user` included), keeps drop-in parity with the classic image, and its exposure is bounded by the image running a single process. A nonroot-by-default posture (uid 65532) was considered and deferred: it would break the documented bind-mount workflow on UID mismatch, and the pilot's job is to measure friction, not maximize it. Revisit at promotion time, possibly as a `-nonroot` tag.
- **The health check is baked in, exec-form.** Shell-form `HEALTHCHECK` strings need `/bin/sh` and are impossible here; the JSON-array form is mandatory. Compose inherits an image's `HEALTHCHECK` automatically (with `disable: true` as the escape hatch), so compose users of this variant get working `depends_on: condition: service_healthy` with zero configuration. `ready` rather than `live` because Docker's health status feeds *gating* (start ordering), which is readiness semantics — and the two are identical anyway unless KMS/etcd are configured.
- **One release-blocking verification**: `HEALTHCHECK` is a Docker extension, absent from the OCI image spec (opencontainers/image-spec#749 is still open), and OCI-media-type builds drop it silently. The publish pipeline must assert `docker inspect` shows the `Health` config on the pushed manifest, or adjust the build's media types until it does.
- **Naming**: `docker.io/pgsty/silo:<RELEASE>-distroless`, plus a rolling `distroless` tag. A new `Dockerfile.distroless` in the server repo — which, having no download stages, is fully offline and can therefore be built and asserted in CI on every release, closing the "the gate tests a synthetic image, not the shipped one" coverage gap that #55 documented for the classic Dockerfile.

What a user gives up in the variant, stated honestly in its docs: no `docker exec <container> sh` debugging (use `docker debug` / `kubectl debug` ephemeral containers), no in-image `mc` (use the `pgsty/mc` image or a host-installed `mcli`), no `MINIO_USERNAME` path (use `--user`).

## Kubernetes needs no image support at all {#kubernetes}

Worth stating explicitly, because it bounds the problem: Kubernetes **ignores** Dockerfile `HEALTHCHECK` entirely — kubelet probes are configured in the pod spec and executed from outside the container as `httpGet` requests. Both image variants are therefore probed identically:

```yaml
startupProbe:            # boot budget: 5s × 60 = 5 minutes for large IAM loads
  httpGet: { path: /minio/health/live, port: 9000 }
  periodSeconds: 5
  failureThreshold: 60
livenessProbe:           # when to restart: process-level signal only
  httpGet: { path: /minio/health/live, port: 9000 }
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3
readinessProbe:          # when to unroute: may include hard dependencies (KMS/etcd)
  httpGet: { path: /minio/health/ready, port: 9000 }
  periodSeconds: 15
  timeoutSeconds: 5
  failureThreshold: 3
```

Three cautions that belong next to any such config: the `cluster` endpoints must never appear in probes (liveness would restart the whole fleet on quorum loss; readiness would tangle with bootstrap — the chart's headless service correctly sets `publishNotReadyAddresses: true` for exactly that reason); `live` deliberately returns 503 under sustained request-queue saturation, so a saturated node restarts after ~90s by design; and with `scheme: HTTPS` the kubelet skips certificate verification, so self-signed deployments need nothing extra.

The Silo Helm chart currently ships **no probes at all** (neither does upstream's, despite its docs). Adding the three probes above to the chart is planned as an independent follow-up — it depends on neither image track, and it is a differentiator over upstream rather than a compatibility risk.

## Rollout {#rollout}

| Phase | Scope | Repo |
| --- | --- | --- |
| **P1** | `silo healthcheck` subcommand + tests; ships in the next release binary (all images inherit the capability, no image behavior changes) | `pgsty/silo` |
| **P2** | `Dockerfile.distroless` + CI build/health gate + publish `-distroless` tags as a pilot | `pgsty/silo` |
| **P3** | Helm chart: add the three probes; refresh the stale default image tag | `pgsty/silo` |
| **P4** | Docs: command reference, probe guide, distroless migration notes; pilot feedback → decide on promoting distroless to the recommended default | this site |

Compatibility promises across all phases: the classic image's contents and examples do not change; `mc ready local` keeps working everywhere it works today; the health HTTP API is untouched (the subcommand is purely additive); and the `/minio/health/*` paths remain frozen as compatibility surface, same as every other `/minio/*` route in the fork.

## Deferred decisions {#deferred}

Recorded so they are not re-litigated from scratch:

- **`--wait` mode** (block-until-healthy, the one thing `mc ready`'s loop is genuinely for): deferred — no in-repo consumer needs it yet, and adding it later is backward-compatible. The flag namespace is reserved.
- **Nonroot-by-default for the distroless image**: deferred to promotion time, as above.
- **JSON output schema** for `--json`: follows the global-flag convention; the exact schema is fixed at implementation time and documented in the command reference.

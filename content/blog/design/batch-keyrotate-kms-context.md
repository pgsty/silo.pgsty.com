---
title: "Batch Key Rotation: Persisting KMS Associated-Data Context and Guarding UTF-8 Round-Trips"
linkTitle: "Batch KeyRotate KMS Context"
date: 2026-11-11
lastmod: 2026-11-11
author: "PGSTY SILO Maintainers"
summary: >
  Why SSE-KMS batch key rotation silently dropped encryption.context on every object since upstream MinIO introduced keyrotate in 2023, why changing Validate() to a pointer receiver would still fail across retries and restarts, and why invalid UTF-8 must be rejected before sealing KMS keys.
tags: [Design, Batch, KMS, Encryption, Reliability]
weight: 10
draft: false
url: "/blog/design/batch-keyrotate-kms-context/"
---

This record covers an upstream-inherited SSE-KMS associated-data bug in `cmd/batch-rotate.go`, tracked under [#346](https://github.com/pgsty/silo/issues/346).

**Status:** Shipped in **[SILO 20261112](/blog/release/silo-20261112/)** (`RELEASE.2026-11-12T00-00-00Z`; commits [`467ce760e`](https://github.com/pgsty/silo/commit/467ce760ed2d77099e8c89cd57514b830acf8780) and [`4a9bdb540`](https://github.com/pgsty/silo/commit/4a9bdb54072dbd7e95dd303a190cda7237ce4fcd)). `SILO Server 20261109` and earlier—as well as all upstream MinIO releases since `RELEASE.2023-04-07T05-28-58Z`—are affected.

## Short Answer {#tldr}

In the batch framework's `keyrotate` job (`cmd/batch-rotate.go`), operators can supply `encryption.context`—a base64-encoded JSON map of string key-value pairs—to bind rotated SSE-KMS data-encryption keys (DEKs) to authenticated associated data (AAD), such as `{"tenant":"acme","compliance":"pci"}`.

Since the feature landed in upstream MinIO in April 2023, `func (e BatchJobKeyRotateEncryption) Validate() error` decoded `e.Context` into `e.kmsContext` on a **value receiver**. Go discarded that stack copy as soon as `Validate()` returned, leaving `r.Encryption.kmsContext` permanently `nil` when `KeyRotate` sealed new DEKs. Every SSE-KMS `keyrotate` job therefore silently dropped `encryption.context` and re-encrypted objects under an **empty** KMS context—and even if the receiver had been a pointer, `kmsContext` was marked `msg:"-"` (unpersisted across manifest reloads, retries, and node restarts). Furthermore, once `encryption.context` actually reaches KMS, `jsoniter` accepts raw invalid UTF-8 bytes inside base64-decoded JSON strings while metadata serialization replaces invalid UTF-8 with `U+FFFD`, creating an irreversible AEAD associated-data mismatch that would leave rotated objects undecryptable.

The repair deletes the unpersisted `kmsContext` cache completely, decodes a fresh UTF-8-validated `kms.Context` directly from the persisted `e.Context` string on validation, execution, retry, and restart, and clones the map before inserting the `"MinIO batch API": "batchrotate"` validation probe key.

## Classification {#assessment}

| Aspect              | Assessment                                                                                                                                                                                                                                                                          |
| :------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Nature**          | Value-receiver assignment + unpersisted derived field (`msg:"-"`) dropping `encryption.context`, compounded by UTF-8 normalization drift between `jsoniter` and metadata serialization. Inherited from upstream MinIO.                                                              |
| **Upstream origin** | Introduced in [`3158f2d12`](https://github.com/pgsty/silo/commit/3158f2d12e427a22fb0fea05d19cece4d41559cf) (`2023-04-04`, [minio/minio#16844](https://github.com/minio/minio/pull/16844), *"Add support for batch key rotation"*), first shipped in `RELEASE.2023-04-07T05-28-58Z`. |
| **Affected scope**  | Any `keyrotate` batch job targeting `encryption.type: sse-kms` with a non-empty `encryption.context`. `sse-s3` rotations and `sse-kms` rotations without `encryption.context` are unaffected.                                                                                       |
| **Impact**          | Rotated objects are silently sealed and stored with an empty KMS context `{}` instead of the configured `encryption.context`, omitting intended AAD bindings from KMS key-generation requests and object metadata.                                                                  |
| **Data safety**     | Previously rotated objects remain readable because `GET` reads the stored (empty) context from `xl.meta`; re-running `keyrotate` after upgrading re-seals them under the intended `encryption.context`.                                                                             |
{.wide .expand}

---

## 1. Upstream Provenance and Root Causes {#root-cause}

### 1.1 Value-Receiver Loss and Unpersisted Derived State (`3158f2d12`) {#value-receiver}

Upstream commit [`3158f2d12`](https://github.com/pgsty/silo/commit/3158f2d12e427a22fb0fea05d19cece4d41559cf) defined `BatchJobKeyRotateEncryption` with an unexported derived field `kmsContext kms.Context` tagged `msg:"-"` and populated it inside `Validate()`:

```go
type BatchJobKeyRotateEncryption struct {
    Type       BatchKeyRotationType `yaml:"type" json:"type"`
    Key        string               `yaml:"key" json:"key"`
    Context    string               `yaml:"context" json:"context"`
    kmsContext kms.Context          `msg:"-"`
}

func (e BatchJobKeyRotateEncryption) Validate() error {
    // ... decodes e.Context into ctx ...
    e.kmsContext = kms.Context{}
    maps.Copy(e.kmsContext, ctx)
    ctx["MinIO batch API"] = "batchrotate"
    // ... probes GlobalKMS.GenerateKey ...
}
```

During execution, `(*BatchJobKeyRotateV1).KeyRotate` ran:

```go
if err = r.Encryption.Validate(); err != nil {
    return err
}
newKeyID = strings.TrimPrefix(r.Encryption.Key, crypto.ARNPrefix)
newKeyContext = r.Encryption.kmsContext
```

Three design flaws interacted on this path:

1. **Discarded value-receiver mutation:** Because `Validate()` received `BatchJobKeyRotateEncryption` by value, `e.kmsContext = ...` mutated only `Validate`'s local stack frame. On return, `r.Encryption.kmsContext` was unconditionally `nil`, so `rotateKey` always sealed the new DEK with an empty KMS context (defaulting only to the bucket/object baseline when applicable, never the configured `encryption.context`).
2. **Unpersisted `msg:"-"` cache across restarts and retries:** Batch job definitions are serialized to msgpack/YAML in `.minio.sys` so jobs survive retries, coordinator handoffs, and server restarts. Any derived field tagged `msg:"-"` disappears on reload, and mutating a cached map on a shared job struct across concurrent object workers introduces a data race.
3. **In-place validation probe mutation:** `Validate()` inserted `ctx["MinIO batch API"] = "batchrotate"` directly into the decoded map to mark its test `GenerateKey` call. Keeping probe metadata in the same map risks leaking internal probe keys into persisted object encryption contexts if map copying is ever reordered.

### 1.2 Invalid UTF-8 Associated-Data Drift Between KMS Seal and Metadata Save {#utf8-drift}

Restoring `encryption.context` propagation exposed a second hazard at the boundary between JSON decoding and metadata persistence:

- `jsoniter.ConfigCompatibleWithStandardLibrary.Unmarshal` accepts raw invalid UTF-8 byte sequences inside JSON string keys and values (when decoded from raw base64 bytes rather than `\uXXXX` escapes). If passed directly to `GlobalKMS.GenerateKey`, the KMS seals the DEK using those exact invalid UTF-8 bytes as AEAD associated data.
- When `rotateKey` subsequently serializes the KMS context to store it in object metadata (`X-Minio-Internal-Server-Side-Encryption-S3-Kms-Context`), standard JSON marshaling coerces invalid UTF-8 byte sequences to the Unicode replacement character `U+FFFD` (`\xef\xbf\xbd`). Even worse, two distinct malformed keys in the same JSON object (such as `{"\xff":"1","\xfe":"2"}`) collapse onto the single key `"\ufffd"` upon serialization!
- On a later `GET` or `HEAD`, SILO reads the `U+FFFD`-normalized context back from `xl.meta` and asks the KMS to unseal the DEK—which fails permanently because the stored associated data no longer matches the raw bytes used during `GenerateKey`.

---

## 2. Solution Design: Stateless Decoding and Upfront UTF-8 Validation {#fix}

Commits [`467ce760e`](https://github.com/pgsty/silo/commit/467ce760ed2d77099e8c89cd57514b830acf8780) and [`4a9bdb540`](https://github.com/pgsty/silo/commit/4a9bdb54072dbd7e95dd303a190cda7237ce4fcd) replace cached struct state with stateless, validated decoding from the persisted `Context` string:

1. **Eliminate `kmsContext` and decode deterministically (`batchKeyRotateContext`):**
   `BatchJobKeyRotateEncryption` keeps only the persisted `Type`, `Key`, and `Context` fields. `batchKeyRotateContext(encoded)` decodes `encoded` via `base64.StdEncoding.DecodeString`, verifies `utf8.Valid(b)` (returning `errInvalidArgument` on invalid UTF-8), and unmarshals into a fresh `kms.Context` (`map[string]string`), normalizing empty input, `{}`, and JSON `null` to an empty non-nil `kms.Context{}`.
2. **Isolate validation probe associated data (`validate`):**
   `func (e BatchJobKeyRotateEncryption) validate() (kms.Context, error)` decodes `ctx` via `batchKeyRotateContext(e.Context)`, clones it into `probe := maps.Clone(ctx)`, adds `probe["MinIO batch API"] = "batchrotate"` **only** to `probe` for the `GlobalKMS.GenerateKey` check, and returns the untainted `ctx` directly to `KeyRotate`.
3. **Validate both submissions and reloaded manifests before rotating:**
   `Validate()` delegates to `validate()`, rejecting malformed base64, invalid UTF-8, non-object JSON, or non-string values at job submission time, and re-validating persisted job manifests on reload/execution before any object's encryption metadata is modified.

### Why This Is Necessary and Sufficient {#sufficiency}

- **Necessary:**
  - Changing `Validate()` from a value receiver to a pointer receiver (`func (e *BatchJobKeyRotateEncryption) Validate()`) would still lose `kmsContext` across `.minio.sys` manifest reloads or share a mutable map across concurrent rotation workers.
  - Rejecting `!utf8.Valid(b)` before `Unmarshal` is required because any byte sequence that cannot round-trip losslessly through UTF-8 JSON string serialization would seal a DEK under associated data that `xl.meta` cannot faithfully persist.
- **Sufficient:** `e.Context` is persisted in every YAML/JSON/msgpack representation of a `keyrotate` job. Decoding a fresh `kms.Context` from `e.Context` guarantees byte-for-byte identical associated data across submission validation, initial rotation, transient KMS retries, coordinator restarts, `xl.meta` storage, and subsequent S3 `GET` decryption (`cmd/batch-rotate-context_test.go`).

---

## 3. Trade-Offs, Caveats, and Operational Costs {#tradeoffs}

| Dimension                                           | Engineering Trade-Off & Operational Cost                                                                                                                                                                                                                                                                                                                                                                            |
| :-------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Per-object base64 + JSON decode**                 | Each rotated version decodes the stored context again. This adds decoding work while avoiding reliance on a mutable cache that is not serialized in the job manifest; no benchmark-derived latency bound is claimed here.                                                                                                                                                                                           |
| **Upfront rejection of invalid UTF-8 contexts**     | Submission returns `400 XMinioAdminInvalidArgument` when decoded context bytes are not valid UTF-8. Execution from a persisted manifest also rejects the context before changing the object key. Valid Unicode, including `U+FFFD` encoded as valid UTF-8, remains supported.                                                                                                                                       |
| **Remediation for previously rotated SSE-KMS data** | On the old path that discarded the requested context and encrypted with an empty context, decryption uses the empty context recorded in `xl.meta`. Those objects remain readable while the original key is available; this is not a recovery guarantee for unrelated metadata or key damage. After upgrading, re-run the `keyrotate` job if KMS policies or audit trails require the intended `encryption.context`. |
{.wide .expand}

## Verification {#verification}

`cmd/batch-rotate-context_test.go` verifies SSE-KMS context preservation across direct execution, `.minio.sys` manifest reload, transient KMS retry recovery, probe-key isolation (`"MinIO batch API"` absent from object metadata), malformed-UTF-8 key collision and value rejection, valid Unicode preservation, and end-to-end authenticated readback against the built-in KMS. See also [Batch Key Rotation Administration](/administration/batch-framework-job-keyrotate/#candidate-context) and [Server Compatibility Notes](/compatibility/server/#candidate-after-20261109).

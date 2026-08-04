---
title: "Absent Is Not Empty: A Blank versionid and the Fail-Open It Invites"
linkTitle: "s3:versionid Conditions"
date: 2026-08-04
author: "Ruohang Feng"
description: "A policy that allowed deletes only when no version was named denied every one of them. The obvious one-line fix would have turned that fail-closed annoyance into a fail-open bypass on Multi-Delete. The condition value had to become the version the server actually acts on."
tags: [Security, Version ID]
weight: 100
draft: false
url: "/blog/security/s3-versionid-conditions/"
---

**Status:** Fixed on the local `pgsty/minio` branch as `744a9dcd7`, **unreleased**
**Classification:** Policy-enforcement correctness — a fail-**closed** report, a fail-**open** trap avoided, and one narrow trim bypass closed. **Not a headline CVE** — see [How we classify this](#not-a-cve)
**Affected scope:** Any deployment with a bucket/IAM policy using `Null` or `StringEquals` on `s3:versionid`; the reported break is on `DeleteObject`/`DeleteObjects`
**Tracking:** upstream `minio/minio` issue #21735 (reporter iTrooz, 2026-01-10); upstream repository archived read-only since 2026-04-25

> This article documents an unreleased fix and two unfixed same-class residuals in neighbouring paths ([governance-bypass and Snowball](#boundary)). Hold publication until the fix ships and the residuals are triaged.

## Conclusions first {#summary}

- The policy engine decides `Null` by **slice length**, not by content. MinIO wrote `"versionid": {""}` into the condition map **unconditionally**, so a request that named no version still presented a length-1 slice. `Null:{s3:versionid:true}` — "match only when the key is absent" — could therefore **never** match, and `Null:false` **always** matched. The reporter's "allow deletes only of the current object" policy denied every current-object delete (HTTP 200 envelope, per-object `AccessDenied`).
- **The one-line fix is a trap.** "Write the key only when it is non-empty" fixes the report and simultaneously opens something worse. `DeleteObjects` carries each object's version in the **XML body**; the condition builder reads only the **query string**. Drop the empty key and a body version simply vanishes from the map — read as absent, i.e. as null — so a policy meant to protect old versions would **authorize deleting a specific one**. Fail-closed defect, meet fail-open bypass.
- The real fix has two parts: write the key only when a version is named, **and** bind it, for `DeleteObject`, to the **effective server-resolved version** (`ReqInfo.VersionID`) — the per-entry body value that the DeleteObjects loop already resolves — rather than to whatever the query string happened to carry.
- A third, adjacent hole closed on the way: the builder read the version **untrimmed** while the object layer trims it, so a padded `?versionId=V%20` let a `Deny StringEquals s3:versionid "V"` be sidestepped on the read/tag/copy paths.
- **Inherited from upstream, and unfixable there.** `minio/minio` is archived read-only, so the fix lives in the fork; this is the same `getConditionValues` we hardened in the [condition-source work](#source).

## Absent is not empty {#the-defect}

A condition key in a MinIO policy resolves to a lowercase name in a `map[string][]string`, and the engine answers `Null` by asking how long that slice is (`silo-pkg .../policy/condition/nullfunc.go`):

```go
func (f nullFunc) evaluate(values map[string][]string) bool {
	rvalues := getValuesByKey(values, f.k)
	if f.value { // Null:true — "the key must be absent"
		return len(rvalues) == 0
	}
	return len(rvalues) != 0 // Null:false — "the key must be present"
}
```

The content of the strings is never read. A slice `{""}` has length 1. To this function, a **present-but-empty** value is indistinguishable from a real version ID, and both are the opposite of **absent**.

Now the value that fed it, as inherited (`cmd/bucket-policy.go`, `getConditionValues`):

```go
args := map[string][]string{
	// ...
	"versionid": {vid}, // vid == "" for any request that names no version
	// ...
}
```

`vid` is the request's `?versionId`, empty on the overwhelming majority of calls. So every request, versioned or not, arrived at the engine carrying `versionid: [""]` — permanently length-1, permanently "present."

The two `Null` directions then invert:

| Request | Map state | `Null:true` (want absent) | `Null:false` (want present) |
| :-- | :-- | :-- | :-- |
| no version named | `{""}` (len 1) | **false** — never matches | **true** — always matches |
| `?versionId=abc` | `{"abc"}` (len 1) | false | true |
| *(correct behaviour)* no version | *absent* (len 0) | **true** | **false** |

The reporter wrote the canonical "let clients delete current objects but not roll back versions" policy — `Allow s3:DeleteObject` with `Condition {"Null": {"s3:versionid": "true"}}` — and watched every version-less delete return `AccessDenied`. The `Allow` never fired because its condition tested "no version named" and the map insisted a version was always named. `StringEquals` cannot see the difference either (`{""}` and absent both fail to intersect a non-empty policy value); only `Null` and `ForAllValues:*` are sensitive to it, which is why `Null` is where it surfaced.

## The fail-open next door {#the-trap}

The obvious fix writes the key only when it is non-empty, and for a single `DeleteObject` that is completely correct: no version → absent → `Null:true` matches. Ship that alone, though, and Multi-Delete turns it into an authorization bypass.

`DeleteObjects` (`POST /{bucket}?delete`) does not put versions in the query. Each object carries its own optional version **in the request body**:

```xml
<Delete>
  <Object><Key>photo.jpg</Key><VersionId>a1b2…</VersionId></Object>
  <Object><Key>notes.txt</Key></Object>
</Delete>
```

The condition builder reads `r.Form` — the **query string** — and nothing merges an XML body into it. So under the naive fix, an entry that names version `a1b2…` in the body produces an **empty** query version, the key is omitted, and the engine sees **absent** — null. A policy written to allow only null-version deletes now matches, and the specific old version the operator meant to protect is deleted. The fail-closed nuisance from the report has become a fail-open on exactly the operation that most needs to be scoped per object.

This is the crux the reporter's simple case hides: the condition value must be the version **the server will actually act on for this object**, and for Multi-Delete that value lives on a channel the condition builder never looked at.

## The fix: the effective version, not a convenient one {#the-fix}

Two mechanisms, because either alone is wrong.

**1 — Represent absence honestly** (`cmd/bucket-policy.go`). Write the key only when the request names a version, so "no version" becomes a length-0 read:

```go
if vid != "" {
	args["versionid"] = []string{vid}
}
```

**2 — Bind DeleteObject to the effective version** (`cmd/auth-handler.go`, `authorizeRequestWithTags`). The DeleteObjects loop already resolves each entry's body version into `ReqInfo.VersionID` (via `checkRequestAuthTypeWithVID`, `cmd/bucket-handlers.go:502`, a sequential loop — no shared-state race). Authorization rebinds the condition value to that server-resolved string, and deletes the key when it is empty:

```go
conditionValuesForAuth := func(lc string, cred auth.Credentials) map[string][]string {
	values := getConditionValuesWithTags(r, lc, cred, existingTags, requestTags)
	if action == policy.DeleteObjectAction {
		// DeleteObjects carries the effective version in each XML object,
		// not in the request query. Keep authorization scoped to that entry.
		if versionID == "" {
			delete(values, "versionid")
		} else {
			values["versionid"] = []string{versionID}
		}
	}
	return values
}
```

An end-to-end test drives a **`&versionId=query-level-decoy`** on the DeleteObjects URL and asserts it never reaches any entry's decision — the per-entry body value wins, the decoy is stripped.

**Why `DeleteObjectAction` only, and not a blanket `ReqInfo` rebind.** The tempting simplification — "always use `ReqInfo.VersionID`" — breaks copy. For a `CopyObject`, the source read is authorized as `GetObject` against the source's version, which travels in the `x-amz-copy-source` header, and `getConditionValues` already extracts it there; `ReqInfo.VersionID` for a copy holds the *destination* query (usually empty). A blanket rebind would overwrite the correct copy-source version with the wrong one. Every non-delete version-aware operation (Get, Head, tagging, retention, copy-source read) carries its version in the query or the copy-source header, both of which the builder reads, and both of which *are* the effective version for a single object. Only Multi-Delete diverges. So the override is precisely as wide as the divergence, and no wider.

## The version the server acts on is the trimmed one {#trim}

One gap remained once the delete paths were correct. The builder read the version raw:

```go
vid := r.Form.Get(xhttp.VersionID) // untrimmed
```

while every path that actually *uses* the version trims it first — `newContext` (`cmd/utils.go:806`) and `getOpts` (`cmd/object-api-options.go:101`) both `strings.TrimSpace`. So on non-delete version-aware actions, a padded `?versionId=V%20` presented `"V "` to the policy engine while the object layer read, tagged, or retained version `"V"`. A `Deny` keyed on `StringEquals s3:versionid "V"` — "protect this exact version" — saw `"V "`, failed to match, and did not fire; the operation on `"V"` proceeded. A narrow bypass (the attacker must know the version and that a space changes nothing downstream), but a real one.

The fix trims both reads, aligning the condition value with the effective version:

```go
vid := strings.TrimSpace(r.Form.Get(xhttp.VersionID))
// ... and the copy-source fallback likewise
```

`DeleteObjectAction` was already immune, because it uses the already-trimmed `ReqInfo.VersionID`. Trimming introduces no new allow: it can only make the condition value equal the version actually operated on, which tightens `Deny` and corrects `Allow` in the same direction. We proved it is load-bearing by removing only the trim and watching the padded test case go red.

## What it affected {#impact}

The reported break is on delete, but the underlying key is read by many actions. After the fix, every version-aware chain evaluates `s3:versionid` against the version the server resolves for that operation:

| Call chain | `s3:versionid` source | Effective |
| :-- | :-- | :-- |
| Single `DeleteObject` | `ReqInfo.VersionID` = trimmed query, via override | ✓ |
| `DeleteObjects`, per entry | `ReqInfo.VersionID` = XML-body version, via override | ✓ — the fail-open closed |
| `GetObject` / `HeadObject` / Select | query, now trimmed | ✓ |
| Object tagging / retention / legal-hold | query, now trimmed | ✓ |
| `CopyObject` / `CopyObjectPart` source read | `x-amz-copy-source` version, now trimmed | ✓ |
| Anonymous 404-vs-403 probes | query (read-only) | ✓ |
| Admin / KMS / metrics / STS | no version concept | ✓ |

A forgery route was already closed by the earlier condition-source work and is worth restating: `versionid` is a reserved internal key (both the `versionid` and canonical `Versionid` spellings), so a client cannot inject a second copy through the header/query merge loops. The wire parameter is spelled `versionId` (capital I) and lands in an inert `args["versionId"]` the engine never reads.

Two directions of impact, kept distinct because they have different severities:

- **Functional (the report):** version-less deletes were wrongly *denied*. Fail-closed — an availability and usability defect, not a grant.
- **Security (the trap and the trim):** the naive fix would have *granted* deletes of protected versions on Multi-Delete (fail-open); and the untrimmed value permitted a narrow `Deny` bypass on read/tag/copy. The fix closes the first before it can exist and the second where it already did.

## How we classify this {#not-a-cve}

We are not minting a CVE for this, and the honest reasons are worth stating.

The behaviour the reporter filed is fail-**closed**: MinIO denied operations the policy meant to allow. A system that is too strict leaks nothing and grants nothing; it is a correctness and usability defect, and inflating a false-deny into a vulnerability would cheapen every real entry in [this chronicle](/blog/security/), whose neighbours are authentication bypasses and path traversals.

What carries genuine security weight is not the report but its vicinity. The fail-open on Multi-Delete is real, but it is a hazard **we would have introduced**, not one that shipped — the value of the two-part design is that the dangerous version never existed in a build. The trim bypass *did* exist, but it is narrow: it requires a `Deny` keyed on an exact `s3:versionid`, an attacker who knows the version, and it only ever affected non-delete paths. We closed it because it was in reach, not because it was a headline.

So: policy-enforcement correctness, filed here because that is where we keep silent enforcement failures, with the security interest recorded plainly rather than dressed up.

## The boundaries we did not cross {#boundary}

Two same-class residuals remain, recorded rather than silently left:

- **Governance-bypass in Multi-Delete.** When an entry carries object-lock, `enforceRetentionBypassForDelete` re-authorizes under `BypassGovernanceRetentionAction` (`cmd/bucket-object-lock.go:153`). That action is not `DeleteObjectAction`, so the effective-version override does not apply, and its `s3:versionid` is still the query value — absent in a normal Multi-Delete — rather than the per-entry version whose lock is being bypassed.
- **Snowball tar extraction.** `PutObjectExtract` takes each member's version from the tar PAX record `minio.versionId` **after** the per-file authorization, so a named version can be written that never appeared in any condition value.

Both are narrow, both are pre-existing, and both would widen the change from "fix the reported key" into "re-plumb every action's version into `ReqInfo`." We scoped to the reported surface and wrote the IOUs down here, for the same reason the [previous article](/blog/security/duplicate-part-numbers/) recorded its object-layer omission: a deliberate omission that is not written down is indistinguishable from an oversight six months later.

A related decision, declined: the sibling keys `username`, `userid`, `signatureversion`, and `authType` are still written **unconditionally empty**, carrying exactly the present-but-empty defect `versionid` just shed — `Null:{aws:username:true}` is always false, including for the anonymous caller it should match. Fixing them is a one-liner each and a forty-caller blast radius, and some (`principaltype` is never empty) do not share the bug at all. We did not bundle a broad presence sweep into a versionid fix; it is named here as the next thread to pull.

## Falsification {#verification}

Three experiments, in the discipline that a test you have not watched fail is not yet a test.

- **Revert both source files to `HEAD`.** The end-to-end DeleteObjects test turned red with every version-less entry returning `AccessDenied` — a faithful reproduction of issue #21735 — and the unit test caught the `{""}` key directly ("an absent versionId was exposed to policy evaluation"). Reapply, green.
- **Remove only the `TrimSpace`.** The padded case went red on the exact assertion — `got [7f4b6b5f-…dd8 ]` — proving the trim is not decoration. Restore, green.
- **The decoy.** The Multi-Delete test appends `&versionId=query-level-decoy` to the URL and asserts it reaches no entry's decision, which is what distinguishes "reads the query" from "reads the effective per-entry version."

The change touched only five files (`cmd/bucket-policy.go`, `cmd/auth-handler.go`, two tests, one doc example), committed with explicit paths in a working tree that had concurrent unrelated work in it, so nothing from the neighbouring efforts was swept in.

## Source and lineage {#source}

The report is upstream `minio/minio#21735`, opened 2026-01-10 against `RELEASE.2025-09-07T16-13-09Z`: a `Null:{s3:versionid:true}` policy denying version-less `DeleteObjects`. The upstream repository went archived and read-only on 2026-04-25, so there is no upstream fix to wait for and no maintainer to coordinate with — the fork is the only venue, and the record here is the resolution.

The defect is old and inherited. `getConditionValues` has written `versionid` unconditionally for as long as the key has existed; the length-based `Null` semantics are upstream's, in the policy package the fork consumes via `silo-pkg`. This is the same function and the same lineage as the earlier condition-source hardening that stopped client input from shadowing server-derived condition values — a related read of "what a policy condition is allowed to believe about a request," continued here into "and it must believe the version the server will actually act on."

## Closing {#closing}

Absent is not empty. A map that cannot say "no version" by leaving the key out will say it by leaving the value blank, and a `Null` that counts length will believe a version was named on every request that named none.

If one sentence survives: **a fail-closed bug is the dangerous kind to fix, because the obvious repair flips it to fail-open** — so bind the condition to the value the server actually acts on, from the same channel the operation reads, not the channel that was convenient; and when you stop at the reported surface, write down the versions you left on the wrong channel, rather than trusting the next person to find them.

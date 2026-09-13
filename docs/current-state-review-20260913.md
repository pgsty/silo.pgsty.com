# Documentation state review — 2026-09-13

The review uses the public releases and accepted source commits, not the
version names inferred from a working checkout. The published component matrix
is maintained in `content/compatibility/versions.md` and its Chinese translation.

## Scope and evidence

The initial inventory covered 1,141 tracked documentation/text/layout files:
7 in pkg, 9 in MC, 36 in Console, 122 in Server and 967 in this website.
Version, current-release, dependency-path, publication-state and password-action
claims were searched across that inventory, then checked against `go.mod`,
release metadata, commit reachability and the owning workflow/source. This is a
release-state documentation review, not a new runtime audit of every inherited
reference command or every historical investigation.

| Repository | Source baseline | Documentation PR |
| --- | --- | --- |
| pkg | `827f8109ff11bf6239a35d8d6d137cb5738539c3` | [pkg #8](https://github.com/pgsty/silo-pkg/pull/8) |
| MC | `4f609a4da3bb8548446715867b68ab6c2d53a097` | [MC #43](https://github.com/pgsty/mc/pull/43) |
| Console | `449c185a8d145a11f93b597b8989594d268ab9b4` | [Console #55](https://github.com/pgsty/silo-console/pull/55) |
| Server | `5d955b5b7444f8a3ab550ce92713607998f89c0d` | [Server #182](https://github.com/pgsty/silo/pull/182) |
| Website | `004581d8296dcc8e921fc3087712dd7625f21135` | This change |

Public releases remain Server 20260903, Console v2.4.0, MC 20260913 and pkg
v3.14.0. The tagged Server's Console source is `464a59d73ada` with a v2.3.0
version identity; it must not be confused with a newer standalone Console.
The new password split and SN-2026-011 Server fix are not in a published Server.

## Corrections

- Add current pkg/MC/Console release posts, source-versus-release tables,
  coordinated dependency order and a bilingual password migration guide.
- Synchronize component changelogs, READMEs, embedding, systemd and release
  procedures with the owning source. The Console tag workflow does not promote
  latest; post-publication verification does.
- Update download inputs and current client references; preserve historical
  Server dependencies and dated test evidence. Mark the old v3.13.0 migration
  record as completed rather than rewriting its original release history.
- Correct old security articles whose fixes shipped in 20260804 but were still
  labelled unreleased. Add the current SN-2026-011 publication boundary.
- Replace obsolete SUBNET registration/upload instructions with the maintained
  local diagnostic and disabled-network-command contracts, retaining old anchors.
- Restore navigation for the Console and new compatibility pages. Count visible
  release/security articles directly instead of displaying frozen editorial
  counts. Refresh stars and combined historical/current Docker pulls through
  `bin/metrics.py`; retain the historical pgsty/minio card destination.
- Remove the unverified claim that downloadable artifacts are the same versions
  running in a particular production deployment; document version-specific
  metadata/rollback boundaries and best-effort upstream compatibility instead.

## Validation

- `go mod verify` and warning-strict `make check` passed.
- internal link check passed: 492450 rendered internal references across 1451 HTML files
- All 26 distinct download-page artifact URLs match the current GitHub release
  attachment catalog. Windows archives really are `.tar.gz` in these releases.
- All changed site content has its matching English/Chinese page.
- Browser checks cover Chinese/English release presentation, client download
  tab selection, version tables and navigation; the rendered table keeps calendar
  version labels intact.
- Console replacement-contract and structural dependency-release checks passed.
  Component changes contain documentation only; remote PR gates remain visible
  in each repository rather than being inferred from this local review.

Original development worktrees and their unrelated uncommitted work were not
used for this update. No new application tag or production infrastructure
rollout is implied by documentation publication. GitHub release-note edits and
the website deployment are verified separately during delivery.

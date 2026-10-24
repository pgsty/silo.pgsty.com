# Silo Documentation

[English](README.md) · [简体中文](README_ZH.md)

This repository contains the bilingual documentation for **Silo**, a community fork of MinIO. It uses [Hugo](https://gohugo.io/) and [OINK 1.3.2](https://github.com/pgsty/oink/tree/v1.3.2), pinned to the exact release in `go.mod`, with English at `/` and Simplified Chinese at `/zh/`.

## Release state and publication

The current public release is **SILO Server 20261018** (`RELEASE.2026-10-18T00-00-00Z`, package `20261018000000.0.0`), source `0cd388c666f8211f552604ae73448a066e9c25ce`. Its GitHub assets and Docker Hub images were verified on 2026-10-19. The selected graph is Console v2.4.2, mcli 20261018, Server pkg v3.14.3 and upstream minio-go v7.4.1; standalone Console/mcli still declare pkg v3.14.2.

Optional PGSTY KES 20261018 is published separately. The October batch includes
paired release notes for Server, Console, mcli, pkg v3.14.2/v3.14.3 and KES,
with deployment and recovery design records linked from each relevant note.
The Server's exact-source local artifact acceptance is recorded in its release
note. Public release and deployment to a particular production environment remain separate steps.

Review the paired [English](content/blog/release/silo-20261018.md) / [Chinese](content/blog/release/silo-20261018.zh.md) release notes and security notes before upgrading. `data/releases.yaml` drives the homepage and download templates: `server.published: true` enables public asset links; `published_server` records the current public release. For future releases, keep the flag false until the matching Server assets and Docker images are publicly verified, and update both languages together.

The [component matrix](https://silo.pgsty.com/compatibility/versions/) separates
published artifacts from accepted main-branch source. Update both languages,
component changelogs and GitHub release notes together. Download artifact inputs
live in `data/releases.yaml`; historical articles retain their original version
numbers and receive a dated follow-up when status changes.

`windows_archive_format` records each component's published Windows archive
format. Keep `tar.gz` for Server, mcli and KES 20261018, and `zip` for Console
v2.4.2. When publishing a subsequent ZIP release, update that component's
version and format together after verifying its assets; do not rewrite old
release links. Linux and macOS archives continue to use `tar.gz`.

Before publishing, run `python3 bin/metrics.py`, review its generated metrics
diff, then run `make check`. Cloudflare Pages deploys the `main` branch; verify
its commit check and the live English/Chinese pages after publication.

## Local development

Use Hugo Extended 0.168.0, Go 1.27.3, Git, and Python 3.10 or newer with `venv` support. Hugo's built-in LibSass compiles the styles, and OINK vendors the browser and styling assets. No separate Sass compiler or Node.js toolchain is needed.

CI uses Go 1.27.3 and Hugo Extended 0.168.0; use the same versions on Cloudflare Pages. Keep this build combination until a theme upgrade preserves the build without a separate Sass compiler. Keep diagnostics visible and review them; Hugo 0.168's upstream LibSass deprecation warning is accepted.

The Make targets use the published OINK version in `go.mod`, with local module replacements and workspaces disabled.

```bash
make dev
```

Build the static site with:

```bash
make build
```

Run the module verification and production build with:

```bash
make check
```

The first check creates `.venv-check` and installs the pinned test dependencies
from `bin/requirements-test.txt`. Subsequent checks reuse that environment.
`make test` runs the link-checker and replica-audit regression tests without
rebuilding the site.

OINK is pinned as a Hugo Module in `go.mod`. Its wordmark, featured-image cascade, and Markdown-first steps are configured or used directly by this site. The project keeps only Silo-specific layouts and styles: the product homepage, download matrix, shared product footer, provenance notice, and imported-document ordering. Documentation chrome, search, content components, blog feeds, and blocks come from the theme. The theme's footer entry point renders the same SILO footer on every page, with language-specific links in `data/footer/en.yaml` and `data/footer/zh.yaml`.

The appearance menu offers Paper (default), Slate, Ink, and Terminal in both languages, independently of light/dark mode. Configure the default and available styles through `params.ui.preset` and `params.ui.preset_menu` in `hugo.yaml`.

## Content convention

### Contributor records

The reviewed roster in `data/home/contributors.yaml` drives the homepage and
generates both contributor pages, all four software repositories' `CONTRIBUTORS.md`
files, and their README sections. Include every human issue / PR author, in any
state; retain acknowledged security disclosures and distinguish incorporated
work from the original PR's merge status. Preserve historical release credits.

Refresh the complete paginated GitHub records for every repository listed in
the data file (`gh api --paginate --slurp 'repos/pgsty/REPO/issues?state=all&per_page=100'`).
Review descriptions, adoption evidence, account deduplication, bot exclusions,
status lists, repository totals, ordering, and the audit date together. Then,
with sibling software checkouts present and Python's PyYAML package available:

```bash
python3 bin/contributors.py
python3 bin/contributor_avatars.py
python3 bin/contributors.py --check
make check
```

Use `--workspace /path/to/checkouts` for a different sibling-checkout location.
Publish new site pages and avatar assets before publishing source-repository
updates that reference their public URLs.

### Bilingual content

English is the default language. Keep translations next to each other:

```text
content/operations/concepts/_index.md
content/operations/concepts/_index.zh.md
```

The product homepage lives at `/`; the documentation overview lives at `/docs/`. The migrated content tree preserves the established MinIO documentation URL families:

```text
/
├── operations/
├── administration/
├── developers/
├── reference/
├── integrations/
└── glossary/
```

Silo-specific migration and compatibility guidance lives in `content/compatibility/`,
the advisory ledger in `content/about/security-advisories.*`, and design,
security investigations written for readers, and release articles in `content/blog/`.
Raw investigation plans, prompts, session transcripts, execution logs, and private
security evidence stay outside both this checkout and the server checkout.
When retiring server-side documents, preserve useful knowledge here, repair
incoming links, and publish new routes before publishing the source cleanup.
Repository maintenance rules are in [AGENTS.md](AGENTS.md); `CLAUDE.md` imports
that same guide.

The English and Chinese corpus was converted deterministically from frozen Sphinx RST/MyST source. The upstream revisions it was frozen from are recorded in [NOTICE.md](NOTICE.md).

## URL policy

Use `https://silo.pgsty.com/` as the canonical public origin for Silo pages. English pages live at the site root and Chinese pages use the `/zh/` prefix. Within this repository, prefer root-relative links for site content so local previews and both language trees remain portable; use absolute `https://silo.pgsty.com/...` URLs in downloadable examples, repository READMEs, service metadata, and other content consumed outside the rendered site.

Do not rewrite primary external sources as Silo URLs. AWS specifications, SDK API references, source repositories, releases, and third-party products should continue to link to their authoritative upstream locations.

## Page provenance

Pages carried over from the MinIO documentation declare their source in front matter, which drives the attribution notice rendered at the bottom of the page:

```yaml
upstream_link: https://github.com/minio/docs # material this page is derived from
upstream_modified: false # set true when Silo changes substance beyond the format conversion
```

`upstream_link` identifies the source and `upstream_modified` records whether its substance has changed. Shared attribution metadata — the work's name, the copyright notice, the license, and the attribution page — is declared once in `hugo.yaml` (`upstream_name`, `upstream_copyright`, `upstream_license`, `upstream_notice`); the theme fails the build if a page names a source without that metadata.

Set `upstream_modified: true` when you change the substance of a MinIO-derived page. The notice then links to that file's change history. Pages written from scratch by Silo — the blog, download and release pages, Silo-specific content — carry neither field. A page under a section that cascades the upstream keys opts out with `upstream_link: ""`.

## Attribution and license

All documentation content is licensed under the [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/) license (CC BY 4.0), the same license as upstream. Portions of it are derived from the [MinIO Object Storage Documentation](https://github.com/minio/docs), © 2020–Present MinIO, Inc., and have been modified.

See [LICENSE](LICENSE) for the full license text and [NOTICE.md](NOTICE.md) for the copyright stack, frozen upstream revisions, material changes, translation notice, and trademark notice.

The same notices are published for readers under `content/about/`, rendered at [/about/](https://silo.pgsty.com/about/):

| Page | Covers |
| :-- | :-- |
| [/about/license/](https://silo.pgsty.com/about/license/) | AGPLv3 for the software, CC BY 4.0 for the documentation |
| [/about/trademark/](https://silo.pgsty.com/about/trademark/) | How the MinIO name is used, and the non-affiliation statement |
| [/about/attribution/](https://silo.pgsty.com/about/attribution/) | Copyright stack, derivation, translation notice, credit line |
| [/about/security/](https://silo.pgsty.com/about/security/) | How to report a vulnerability, and where fixes are published |

# Silo Documentation

This repository contains the bilingual documentation for **Silo**, a community fork of MinIO. It uses [Hugo](https://gohugo.io/) and [Docsy](https://www.docsy.dev/), with English at `/` and Simplified Chinese at `/zh/`.

## Local development

Install Hugo Extended, Go, Node.js, and npm. Install the pinned PostCSS toolchain once, then run the local server:

```bash
npm ci
```

```bash
make dev
```

Build the static site with:

```bash
make build
```

Run the module verification and warning-strict production build with:

```bash
make check
```

Docsy is pinned as a Hugo Module. Project-specific layouts and SCSS extend the theme without vendoring its source.

## Content convention

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

The English and Chinese corpus was converted deterministically from frozen Sphinx RST/MyST source. The upstream revisions it was frozen from are recorded in [NOTICE.md](NOTICE.md).

## Page provenance

Pages carried over from the MinIO documentation declare it in their front matter, which drives the attribution notice rendered at the bottom of the page:

```yaml
minio_origin: true # page is derived from the MinIO documentation
silo_modified: false # page has been changed by Silo beyond the format conversion
```

Set `silo_modified: true` when you change the substance of a MinIO-derived page. The notice then links to that file's change history. Pages written from scratch by Silo — the blog, download and release pages, Silo-specific content — carry neither field.

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

#!/usr/bin/env python3
"""Download contributor avatars from GitHub into the site's static assets.

Reads the handles listed in data/home/contributors.yaml and writes one square
WebP per contributor to static/images/contributors/<handle>.webp, matching how
static/images/voices/ already stores its faces. Existing files are left alone
unless --force is given, so a rerun after adding a contributor only fetches the
new avatar.

Also writes self-contained SVG avatars for the GitHub README and contributor
record. Significant contributions get the same gold ring as the website.
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "home" / "contributors.yaml"
OUTPUT_DIR = REPO_ROOT / "static" / "images" / "contributors"

# Resolve the account's current avatar through GitHub's API. The old
# github.com/<handle>.png redirect is convenient but intermittently stalls;
# avatars.githubusercontent.com is reliable once the canonical URL is known.
PROFILE_URL = "https://api.github.com/users/{handle}"
SOURCE_SIZE = 200
RENDER_SIZE = 96
WEBP_QUALITY = 82
TIMEOUT_SECONDS = 20

HANDLE_RE = re.compile(r"^\s*-\s*handle:\s*\"([^\"]+)\"", re.MULTILINE)


def read_contributors() -> list[tuple[str, bool]]:
    """Collect handles and featured flags from the contributor entry blocks."""
    text = DATA_FILE.read_text(encoding="utf-8")
    matches = list(HANDLE_RE.finditer(text))
    contributors: list[tuple[str, bool]] = []
    seen: set[str] = set()
    for index, match in enumerate(matches):
        handle = match.group(1)
        if handle.lower() in seen:
            sys.exit(f"duplicate contributor: {handle}")
        seen.add(handle.lower())
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        featured = bool(re.search(r"^    featured: true$", text[match.end():end], re.MULTILINE))
        contributors.append((handle, featured))
    if not contributors:
        sys.exit(f"no handles found in {DATA_FILE}")
    return contributors


def write_svg(source: Path, featured: bool) -> None:
    """Wrap the local avatar in a circular, portable GitHub image."""
    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    ring = (
        '<circle cx="54" cy="54" r="51" fill="none" stroke="#e0a35c" stroke-opacity=".16" stroke-width="6"/>\n'
        '<circle cx="54" cy="54" r="47" fill="none" stroke="#e0a35c" stroke-width="4"/>'
        if featured else
        '<circle cx="54" cy="54" r="47.5" fill="none" stroke="#94b0d2" stroke-opacity=".32"/>'
    )
    muted = '' if featured else ' filter="url(#muted)" opacity=".86"'
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">\n'
        '<defs><clipPath id="face"><circle cx="54" cy="54" r="48"/></clipPath>'
        '<filter id="muted"><feColorMatrix type="saturate" values=".55"/></filter></defs>\n'
        f'<image x="6" y="6" width="96" height="96" clip-path="url(#face)"{muted} href="data:image/webp;base64,{encoded}"/>\n'
        f'{ring}\n</svg>\n'
    )
    source.with_suffix(".svg").write_text(svg, encoding="utf-8")


def fetch(handle: str) -> bytes:
    profile_request = urllib.request.Request(
        PROFILE_URL.format(handle=handle),
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "silo-site-avatars",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(profile_request, timeout=TIMEOUT_SECONDS) as response:
        profile = json.load(response)

    avatar_url = profile.get("avatar_url")
    if not avatar_url:
        raise OSError(f"GitHub profile for {handle} has no avatar_url")
    separator = "&" if "?" in avatar_url else "?"
    request = urllib.request.Request(
        f"{avatar_url}{separator}s={SOURCE_SIZE}",
        headers={"User-Agent": "silo-site-avatars"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def convert(raw: bytes, destination: Path) -> None:
    """Square-crop to RENDER_SIZE and encode as WebP via cwebp."""
    with tempfile.NamedTemporaryFile(suffix=".src") as source:
        source.write(raw)
        source.flush()
        subprocess.run(
            [
                "cwebp", "-quiet",
                "-q", str(WEBP_QUALITY),
                "-resize", str(RENDER_SIZE), str(RENDER_SIZE),
                source.name,
                "-o", str(destination),
            ],
            check=True,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download avatars that already exist")
    args = parser.parse_args(argv)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    contributors = read_contributors()
    fetched = skipped = 0
    failures: list[str] = []

    for handle, featured in contributors:
        destination = OUTPUT_DIR / f"{handle}.webp"
        if destination.exists() and not args.force:
            write_svg(destination, featured)
            skipped += 1
            continue
        try:
            convert(fetch(handle), destination)
            write_svg(destination, featured)
        except (urllib.error.URLError, subprocess.CalledProcessError, OSError) as error:
            failures.append(f"{handle}: {error}")
            continue
        fetched += 1
        print(f"{handle} -> {destination.relative_to(REPO_ROOT)}")

    print(f"\n{fetched} fetched, {skipped} already present, {len(failures)} failed")
    for failure in failures:
        print(f"  {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

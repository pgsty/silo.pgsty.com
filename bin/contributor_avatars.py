#!/usr/bin/env python3
"""Download contributor avatars from GitHub into the site's static assets.

Reads the handles listed in data/home/contributors.yaml and writes one square
WebP per contributor to static/images/contributors/<handle>.webp, matching how
static/images/voices/ already stores its faces. Existing files are left alone
unless --force is given, so a rerun after adding a contributor only fetches the
new avatar.
"""

from __future__ import annotations

import argparse
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


def read_handles() -> list[str]:
    """Collect handles in file order, dropping duplicates."""
    text = DATA_FILE.read_text(encoding="utf-8")
    handles: list[str] = []
    for handle in HANDLE_RE.findall(text):
        if handle not in handles:
            handles.append(handle)
    if not handles:
        sys.exit(f"no handles found in {DATA_FILE}")
    return handles


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
    handles = read_handles()
    fetched = skipped = 0
    failures: list[str] = []

    for handle in handles:
        destination = OUTPUT_DIR / f"{handle}.webp"
        if destination.exists() and not args.force:
            skipped += 1
            continue
        try:
            convert(fetch(handle), destination)
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

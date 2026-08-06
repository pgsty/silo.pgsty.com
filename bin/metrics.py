#!/usr/bin/env python3
"""Fetch pgsty/silo metrics and optionally update Hugo's data file."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.request
from typing import Any, Sequence


GITHUB_API = "https://api.github.com/repos/pgsty/silo"

# GitHub carried the stars across the pgsty/minio -> pgsty/silo rename; Docker Hub
# did not. The pull history lives in the archived pgsty/minio repository, which the
# landing page keeps reporting while linking to the current pgsty/silo image.
DOCKER_HUB_API = "https://hub.docker.com/v2/namespaces/pgsty/repositories/minio"
TIMEOUT_SECONDS = 15
USER_AGENT = "pgsty-metrics/1.0"
REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS_FILE = REPO_ROOT / "data" / "home" / "metrics.yaml"


class MetricsError(RuntimeError):
    """Raised when metrics cannot be fetched, validated, or written."""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print pgsty/silo GitHub stars and Docker Hub pulls."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("update",),
        help="update data/home/metrics.yaml after fetching both metrics",
    )
    return parser.parse_args(argv)


def build_opener() -> urllib.request.OpenerDirector:
    """Build an HTTP opener that also honors macOS system proxy settings."""
    proxies = urllib.request.getproxies()

    # A lone NO_PROXY environment variable makes urllib ignore macOS system
    # proxies. Merge them back when no HTTP(S) proxy was explicitly provided.
    if sys.platform == "darwin" and not {"http", "https", "all"} & proxies.keys():
        get_system_proxies = getattr(
            urllib.request, "getproxies_macosx_sysconf", None
        )
        if get_system_proxies is not None:
            proxies = {**get_system_proxies(), **proxies}

    return urllib.request.build_opener(urllib.request.ProxyHandler(proxies))


def fetch_json(
    opener: urllib.request.OpenerDirector,
    url: str,
    headers: dict[str, str],
) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers)

    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        raise MetricsError(f"{url}: HTTP {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise MetricsError(f"{url}: {exc.reason}") from exc
    except (TimeoutError, json.JSONDecodeError) as exc:
        raise MetricsError(f"{url}: {exc}") from exc

    if not isinstance(payload, dict):
        raise MetricsError(f"{url}: expected a JSON object")
    return payload


def read_counter(payload: dict[str, Any], key: str, source: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MetricsError(f"{source}: invalid {key!r} value: {value!r}")
    return value


def fetch_metrics() -> tuple[int, int]:
    opener = build_opener()
    github_headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if github_token:
        github_headers["Authorization"] = f"Bearer {github_token}"

    github = fetch_json(opener, GITHUB_API, github_headers)
    docker_hub = fetch_json(
        opener,
        DOCKER_HUB_API,
        {"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    return (
        read_counter(github, "stargazers_count", GITHUB_API),
        read_counter(docker_hub, "pull_count", DOCKER_HUB_API),
    )


def replace_yaml_counter(content: str, key: str, value: int) -> str:
    pattern = re.compile(
        rf"^(?P<prefix>{re.escape(key)}:[ \t]*)(?P<value>[0-9]+)"
        r"(?P<suffix>[ \t]*(?:#.*)?)$",
        re.MULTILINE,
    )
    updated, replacements = pattern.subn(
        lambda match: f"{match.group('prefix')}{value}{match.group('suffix')}",
        content,
    )
    if replacements != 1:
        raise MetricsError(
            f"{METRICS_FILE}: expected exactly one integer {key!r} entry"
        )
    return updated


def update_metrics_file(github_stars: int, docker_pulls: int) -> bool:
    temporary_path: Path | None = None

    try:
        if not METRICS_FILE.is_file():
            raise MetricsError(f"{METRICS_FILE}: metrics data file does not exist")

        content = METRICS_FILE.read_text(encoding="utf-8")
        updated = replace_yaml_counter(content, "github_stars", github_stars)
        updated = replace_yaml_counter(updated, "docker_pulls", docker_pulls)
        if updated == content:
            return False

        mode = METRICS_FILE.stat().st_mode & 0o777
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=METRICS_FILE.parent,
            prefix=f".{METRICS_FILE.name}.",
            delete=False,
        ) as temporary:
            temporary.write(updated)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)

        temporary_path.chmod(mode)
        os.replace(temporary_path, METRICS_FILE)
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise MetricsError(f"{METRICS_FILE}: {exc}") from exc

    return True


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    github_stars, docker_pulls = fetch_metrics()

    print(f"github_stars={github_stars}")
    print(f"docker_pulls={docker_pulls}")

    if args.command == "update":
        changed = update_metrics_file(github_stars, docker_pulls)
        status = "updated" if changed else "unchanged"
        print(f"{status}={METRICS_FILE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MetricsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

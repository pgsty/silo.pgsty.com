#!/usr/bin/env python3
"""Fetch pgsty/silo metrics and update Hugo's data file."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.request
from typing import Any, Sequence


GITHUB_REPO = "pgsty/silo"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}"

# GitHub carried the stars across the pgsty/minio -> pgsty/silo rename; Docker Hub
# did not. The pull history stays on the archived pgsty/minio repository while
# pgsty/silo collects everything published after the rename, so the landing page
# reports the sum of both.
DOCKER_NAMESPACE = "pgsty"
DOCKER_REPOS = ("minio", "silo")
DOCKER_HUB_API = "https://hub.docker.com/v2/namespaces/{namespace}/repositories/{repo}"

TIMEOUT_SECONDS = 15
USER_AGENT = "pgsty-metrics/1.0"
REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS_FILE = REPO_ROOT / "data" / "home" / "metrics.yaml"


class MetricsError(RuntimeError):
    """Raised when metrics cannot be fetched, validated, or written."""


@dataclass(frozen=True)
class Metrics:
    """Remote counters mirrored into data/home/metrics.yaml."""

    github_stars: int
    docker_pulls_by_repo: dict[str, int]

    @property
    def docker_pulls(self) -> int:
        return sum(self.docker_pulls_by_repo.values())


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch pgsty/silo GitHub stars and Docker Hub pulls "
            f"({', '.join(f'{DOCKER_NAMESPACE}/{repo}' for repo in DOCKER_REPOS)} "
            "combined), then refresh data/home/metrics.yaml."
        )
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="update",
        choices=("update", "show"),
        help="update (default) writes data/home/metrics.yaml; show only prints",
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


def fetch_github_stars(opener: urllib.request.OpenerDirector) -> int:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = fetch_json(opener, GITHUB_API, headers)
    return read_counter(payload, "stargazers_count", GITHUB_API)


def fetch_docker_pulls(opener: urllib.request.OpenerDirector) -> dict[str, int]:
    """Return the pull count of every tracked Docker Hub repository."""
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    pulls: dict[str, int] = {}

    for repo in DOCKER_REPOS:
        url = DOCKER_HUB_API.format(namespace=DOCKER_NAMESPACE, repo=repo)
        payload = fetch_json(opener, url, headers)
        pulls[f"{DOCKER_NAMESPACE}/{repo}"] = read_counter(payload, "pull_count", url)

    return pulls


def fetch_metrics() -> Metrics:
    opener = build_opener()
    return Metrics(
        github_stars=fetch_github_stars(opener),
        docker_pulls_by_repo=fetch_docker_pulls(opener),
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


def update_metrics_file(metrics: Metrics) -> bool:
    temporary_path: Path | None = None

    try:
        if not METRICS_FILE.is_file():
            raise MetricsError(f"{METRICS_FILE}: metrics data file does not exist")

        content = METRICS_FILE.read_text(encoding="utf-8")
        updated = replace_yaml_counter(content, "github_stars", metrics.github_stars)
        updated = replace_yaml_counter(updated, "docker_pulls", metrics.docker_pulls)
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
    metrics = fetch_metrics()

    print(f"github_stars={metrics.github_stars}")
    for repo, pulls in metrics.docker_pulls_by_repo.items():
        print(f"docker_pulls[{repo}]={pulls}")
    print(f"docker_pulls={metrics.docker_pulls}")

    if args.command == "update":
        changed = update_metrics_file(metrics)
        status = "updated" if changed else "unchanged"
        print(f"{status}={METRICS_FILE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MetricsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

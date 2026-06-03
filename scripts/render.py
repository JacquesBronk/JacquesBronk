#!/usr/bin/env python3
"""Render README.md from templates/README.md.tmpl + data/ + NuGet API.

Stdlib only. Run from repo root: python3 scripts/render.py
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "templates" / "README.md.tmpl"
LAB_STATUS = REPO_ROOT / "data" / "lab-status.json"
NUGET_CACHE = REPO_ROOT / "data" / "nuget-cache.json"
README = REPO_ROOT / "README.md"

SAST = timezone(timedelta(hours=2))
STALE_AFTER = timedelta(hours=24)
NUGET_PACKAGE = "SARS.TaxCalculator"
NUGET_API = "https://azuresearch-usnc.nuget.org/query?q=packageid:{}"

QUIP_FRESH = "if this is stale, the lab is probably on fire"
QUIP_STALE = "it's stale. the lab might actually be on fire"

RAW = "https://raw.githubusercontent.com/JacquesBronk/JacquesBronk/output"
# marker filename on the output branch -> (header command, dark svg, light svg)
ARCADE_GAMES = {
    "github-snake.svg": (
        "$ ./snake --feed=commits",
        "github-snake.svg", "github-snake-light.svg"),
    "commit-invaders.svg": (
        "$ ./invaders --source=contributions",
        "commit-invaders-dark.svg", "commit-invaders.svg"),
    "pacman-contribution-graph.svg": (
        "$ ./pacman --maze=contributions",
        "pacman-contribution-graph-dark.svg", "pacman-contribution-graph.svg"),
    "breakout-contribution-graph.svg": (
        "$ ./breakout --bricks=commits",
        "breakout-contribution-graph-dark.svg", "breakout-contribution-graph.svg"),
}
ARCADE_OFFLINE = ("### `$ ./arcade`\n\n"
                  "```text\ninsert coin — machine rebooting, check back tomorrow\n```")


def load_lab_status(path=LAB_STATUS):
    """Return parsed lab-status dict, or None if missing/unreadable."""
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None


def is_stale(updated_at, now):
    """True if updated_at (ISO string) is older than STALE_AFTER."""
    try:
        ts = datetime.fromisoformat(updated_at)
    except (TypeError, ValueError):
        return True
    return now - ts > STALE_AFTER


def render_lab_table(status, now):
    """Render the fixed-width lab table + sync metadata.

    Returns (table_text, last_sync_text, quip).
    """
    if status is None:
        return ("COMPONENT       STATUS    DETAIL\n"
                "homelab         Unknown   no status received yet"), "never", QUIP_STALE

    stale = is_stale(status.get("updated_at"), now)
    lines = [f"{'COMPONENT':<16}{'STATUS':<10}DETAIL"]
    for row in status.get("rows", []):
        stat = "Unknown" if stale else row["status"]
        lines.append(f"{row['component']:<16}{stat:<10}{row['detail']}")

    try:
        ts = datetime.fromisoformat(status["updated_at"]).astimezone(SAST)
        last_sync = ts.strftime("%Y-%m-%d %H:%M SAST")
    except (KeyError, TypeError, ValueError):
        last_sync = "unknown"

    return "\n".join(lines), last_sync, (QUIP_STALE if stale else QUIP_FRESH)


def fetch_nuget(package=NUGET_PACKAGE, cache_path=NUGET_CACHE):
    """Fetch download count + version from NuGet; fall back to cache on failure."""
    cache_path = Path(cache_path)
    try:
        with urllib.request.urlopen(NUGET_API.format(package), timeout=10) as resp:
            data = json.load(resp)["data"][0]
        result = {"version": data["version"], "totalDownloads": data["totalDownloads"]}
        cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        cache[package] = result
        cache_path.write_text(json.dumps(cache, indent=2) + "\n")
        return result
    except Exception:
        cache = json.loads(cache_path.read_text())
        return cache[package]


def list_output_branch():
    """Return filenames on the output branch, or None on failure."""
    url = "https://api.github.com/repos/JacquesBronk/JacquesBronk/contents/?ref=output"
    headers = {"User-Agent": "profile-render"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return [f["name"] for f in json.load(resp)]
    except Exception:
        return None


def render_arcade_section(filenames):
    """Render the arcade section for whichever game is on the output branch."""
    for marker, (header, dark, light) in ARCADE_GAMES.items():
        if filenames and marker in filenames:
            return (f"### `{header}`\n\n"
                    "<picture>\n"
                    f'  <source media="(prefers-color-scheme: dark)" srcset="{RAW}/{dark}">\n'
                    f'  <source media="(prefers-color-scheme: light)" srcset="{RAW}/{light}">\n'
                    f'  <img alt="arcade game played across the contribution graph" src="{RAW}/{light}" width="100%">\n'
                    "</picture>")
    return ARCADE_OFFLINE


def render(template_text, lab_status, nuget, now, arcade_files=None):
    """Substitute all template placeholders; return README text."""
    table, last_sync, quip = render_lab_table(lab_status, now)
    return (template_text
            .replace("{{NUGET_DOWNLOADS}}", f"{nuget['totalDownloads']:,}")
            .replace("{{NUGET_VERSION}}", nuget["version"])
            .replace("{{LAB_TABLE}}", table)
            .replace("{{LAST_SYNC}}", last_sync)
            .replace("{{LAB_QUIP}}", quip)
            .replace("{{ARCADE_SECTION}}", render_arcade_section(arcade_files)))


def main():
    now = datetime.now(SAST)
    readme = render(TEMPLATE.read_text(), load_lab_status(), fetch_nuget(), now,
                    arcade_files=list_output_branch())
    README.write_text(readme)
    print(f"README.md rendered ({len(readme)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

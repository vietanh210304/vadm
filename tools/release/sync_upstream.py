#!/usr/bin/env python3
"""Filter and cherry-pick non-torrent commits from upstream/main into VADM."""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

STATE_FILE = pathlib.Path(".github/upstream-sync-sha")
SUMMARY_FILE = pathlib.Path("SYNC_SUMMARY.md")

TORRENT_PATH_RE = re.compile(
    r"(^crates/torrent/|/torrent/|/(?:torrent|torrents|rss)(?:\.[^/]+)?$)",
    re.IGNORECASE,
)
TORRENT_SUBJECT_RE = re.compile(
    r"\b(torrent|torrents|bittorrent|magnet|libtorrent|dht|tracker|trackers|rss)\b",
    re.IGNORECASE,
)


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a subprocess capturing UTF-8 output."""
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def is_torrent_commit(sha: str, subject: str) -> tuple[bool, str]:
    """Return whether a commit is torrent/RSS-related and why."""
    files = run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha]).stdout.splitlines()
    torrent_files = [f for f in files if TORRENT_PATH_RE.search(f)]
    if torrent_files and len(torrent_files) == len(files):
        return True, f"only touches torrent/RSS files ({torrent_files[0]})"
    if TORRENT_SUBJECT_RE.search(subject):
        return True, "commit title targets torrent/RSS"
    if torrent_files:
        return True, f"modifies torrent/RSS paths ({', '.join(torrent_files[:3])})"
    return False, ""


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: sync_upstream.py <upstream_ref>", file=sys.stderr)
        return 2

    upstream_ref = sys.argv[1]
    base_sha = STATE_FILE.read_text(encoding="utf-8").strip()
    upstream_head = run(["git", "rev-parse", upstream_ref]).stdout.strip()

    if base_sha == upstream_head:
        print("No new upstream commits.")
        return 0

    commits_raw = run(
        ["git", "log", "--no-merges", "--reverse", "--format=%H\t%s", f"{base_sha}..{upstream_head}"]
    ).stdout.splitlines()

    if not commits_raw:
        STATE_FILE.write_text(f"{upstream_head}\n", encoding="utf-8", newline="\n")
        print("Upstream moved only with merge/empty commits.")
        return 0

    applied: list[tuple[str, str]] = []
    skipped: list[tuple[str, str, str]] = []
    conflicted: list[tuple[str, str]] = []
    already_present: list[tuple[str, str]] = []

    for line in commits_raw:
        sha, subject = line.split("\t", 1)
        short = sha[:8]
        skip, reason = is_torrent_commit(sha, subject)
        if skip:
            skipped.append((short, subject, reason))
            continue

        cp = run(["git", "cherry-pick", "-x", sha], check=False)
        if cp.returncode == 0:
            applied.append((short, subject))
            continue

        status = run(["git", "status", "--porcelain"], check=False).stdout
        if not status.strip():
            # Empty cherry-pick (already in tree)
            run(["git", "cherry-pick", "--skip"], check=False)
            already_present.append((short, subject))
        else:
            run(["git", "cherry-pick", "--abort"], check=False)
            conflicted.append((short, subject))

    STATE_FILE.write_text(f"{upstream_head}\n", encoding="utf-8", newline="\n")

    lines = [
        f"Upstream sync from `{base_sha[:8]}` to `{upstream_head[:8]}`.",
        "",
        f"### Applied non-torrent commits ({len(applied)})",
    ]
    lines.extend([f"- `{s}` {subj}" for s, subj in applied] or ["- None"])

    lines.extend(["", f"### Skipped torrent/RSS commits ({len(skipped)})"])
    lines.extend([f"- `{s}` {subj} ({why})" for s, subj, why in skipped] or ["- None"])

    if already_present:
        lines.extend(["", f"### Already present ({len(already_present)})"])
        lines.extend([f"- `{s}` {subj}" for s, subj in already_present])

    if conflicted:
        lines.extend(["", f"### Conflicted — manual cherry-pick needed ({len(conflicted)})"])
        lines.extend([f"- `{s}` {subj}" for s, subj in conflicted])

    SUMMARY_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Sync summary: {len(applied)} applied, {len(skipped)} skipped, {len(conflicted)} conflicted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

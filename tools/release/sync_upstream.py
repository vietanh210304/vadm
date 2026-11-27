#!/usr/bin/env python3
"""Filter, cherry-pick, and bump versions for non-torrent upstream syncs."""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

STATE_FILE = pathlib.Path(".github/upstream-sync-sha")
SUMMARY_FILE = pathlib.Path("SYNC_SUMMARY.md")
CARGO_TOML = pathlib.Path("Cargo.toml")
CARGO_LOCK = pathlib.Path("Cargo.lock")
VADM_ISS = pathlib.Path("tools/installer/vadm.iss")

TORRENT_PATH_RE = re.compile(
    r"(^crates/torrent/|/torrent/|/(?:torrent|torrents|rss)(?:\.[^/]+)?$)",
    re.IGNORECASE,
)
TORRENT_SUBJECT_RE = re.compile(
    r"\b(torrent|torrents|bittorrent|magnet|libtorrent|dht|tracker|trackers|rss)\b",
    re.IGNORECASE,
)
WORKSPACE_CRATE_RE = re.compile(
    r'(\[\[package\]\]\s+name = "(?:mdm-[^"]+|vadm)"\s+version = ")([^"]+)(")',
    re.MULTILINE,
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


def set_github_output(values: dict[str, str]) -> None:
    """Append key=value pairs to GITHUB_OUTPUT when running in GitHub Actions."""
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a", encoding="utf-8", newline="\n") as f:
        for k, v in values.items():
            f.write(f"{k}={v}\n")


def parse_semver(version: str) -> tuple[int, int, int]:
    """Parse X.Y.Z semver tuple."""
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version.strip())
    if not m:
        raise ValueError(f"Expected X.Y.Z version, got {version!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def bump_version(previous_version: str | None = None) -> int:
    """Ensure workspace version strictly advances past `previous_version` and update files."""
    cargo_text = CARGO_TOML.read_text(encoding="utf-8")
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', cargo_text)
    if not m:
        raise RuntimeError("Could not locate version in Cargo.toml")
    current = m.group(1)

    if previous_version:
        cur_tuple = parse_semver(current)
        prev_tuple = parse_semver(previous_version)
        if cur_tuple > prev_tuple:
            next_ver = current
        else:
            next_ver = f"{prev_tuple[0]}.{prev_tuple[1]}.{prev_tuple[2] + 1}"
    else:
        cur_tuple = parse_semver(current)
        next_ver = f"{cur_tuple[0]}.{cur_tuple[1]}.{cur_tuple[2] + 1}"

    new_cargo, n = re.subn(
        r'(?m)^(version\s*=\s*")[^"]+(")',
        rf"\g<1>{next_ver}\2",
        cargo_text,
        count=1,
    )
    assert n == 1
    CARGO_TOML.write_text(new_cargo, encoding="utf-8", newline="\n")

    if CARGO_LOCK.is_file():
        lock_text = CARGO_LOCK.read_text(encoding="utf-8")
        new_lock = WORKSPACE_CRATE_RE.sub(rf"\g<1>{next_ver}\3", lock_text)
        CARGO_LOCK.write_text(new_lock, encoding="utf-8", newline="\n")

    if VADM_ISS.is_file():
        iss_text = VADM_ISS.read_text(encoding="utf-8")
        new_iss = re.sub(
            r'(?m)^(\s*#define\s+AppVersion\s+")[^"]+(")',
            rf"\g<1>{next_ver}\2",
            iss_text,
            count=1,
        )
        VADM_ISS.write_text(new_iss, encoding="utf-8", newline="\n")

    set_github_output({"version": next_ver, "tag": f"v{next_ver}"})
    print(f"Bumped version -> {next_ver} (tag v{next_ver})")
    return 0


def sync_upstream(upstream_ref: str) -> int:
    """Cherry-pick clean non-torrent commits since STATE_FILE and classify outcomes."""
    base_sha = STATE_FILE.read_text(encoding="utf-8").strip()
    upstream_head = run(["git", "rev-parse", upstream_ref]).stdout.strip()

    if base_sha == upstream_head:
        print("No new upstream commits.")
        set_github_output(
            {
                "action": "noop",
                "applied": "0",
                "skipped": "0",
                "conflicted": "0",
            }
        )
        return 0

    commits_raw = run(
        ["git", "log", "--no-merges", "--reverse", "--format=%H\t%s", f"{base_sha}..{upstream_head}"]
    ).stdout.splitlines()

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

    if conflicted:
        action = "pr"
    elif applied:
        action = "auto_verify"
    else:
        action = "marker_only"

    set_github_output(
        {
            "action": action,
            "applied": str(len(applied)),
            "skipped": str(len(skipped)),
            "conflicted": str(len(conflicted)),
            "already_present": str(len(already_present)),
            "upstream_head": upstream_head[:8],
        }
    )
    print(
        f"Sync summary ({action}): {len(applied)} applied, {len(skipped)} skipped, "
        f"{len(already_present)} already present, {len(conflicted)} conflicted"
    )
    return 0


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--bump-version":
        prev = sys.argv[2] if len(sys.argv) >= 3 else None
        return bump_version(prev)
    if len(sys.argv) < 2:
        print("Usage: sync_upstream.py <upstream_ref> | --bump-version [prev_version]", file=sys.stderr)
        return 2
    return sync_upstream(sys.argv[1])


if __name__ == "__main__":
    raise SystemExit(main())

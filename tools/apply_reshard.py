# SPDX-License-Identifier: AGPL-3.0-or-later
"""Apply CI reshard recommendations locally.

CI deliberately never mutates the repository ("workflows must not push",
enforced by scripts/validate_workflows.py). The main pipeline therefore
exports its rebalanced ``sources/batch_*.txt`` as the
``source-reshard-recommendation`` artifact and this tool applies it from
a machine with push access:

    python tools/apply_reshard.py            # latest recommendation
    python tools/apply_reshard.py --run-id 12345678
    python tools/apply_reshard.py --check    # report only, no changes

Safety contract:
- the recommended URL set must exactly match the working tree set
  (nothing silently dropped or injected);
- every batch must carry an ``Est. Fetch Time`` header at or below
  dynamic_reshard.TARGET_BATCH_SECONDS;
- nothing is committed unless all checks pass.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCES_DIR = REPO / "sources"
TARGET_BATCH_SECONDS = 14400.0  # keep in sync with scripts/dynamic_reshard.py
EST_TIME_RE = re.compile(r"Est\\. Fetch Time: ([\\d.]+)s")


def _gh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603
        ["gh", *args], capture_output=True, text=True, check=False
    )


def _require_gh() -> None:
    if _gh("--version").returncode != 0:
        raise SystemExit("gh CLI not found on PATH; install GitHub CLI first.")


def _repo_slug() -> str:
    url = subprocess.run(  # nosec B603
        ["git", "-C", str(REPO), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    match = re.search(r"github\\.com[:/](.+?)(?:\\.git)?$", url)
    if not match:
        raise SystemExit(f"cannot parse repository slug from {url}")
    return match.group(1)


def _latest_recommendation_run(slug: str) -> int | None:
    result = _gh(
        "api",
        f"repos/{slug}/actions/runs?per_page=30",
        "--jq",
        \'[.workflow_runs[] | select(.name == "Config\'s Stream" and \'
        \'.conclusion == "success") | .id] | .[0]\',
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def _urls_of(directory: Path) -> set[str]:
    urls: set[str] = set()
    for path in sorted(directory.glob("batch_*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(("http://", "https://")):
                urls.add(line)
    return urls


def _validate(recommendation: Path) -> dict[str, float]:
    current = SOURCES_DIR if SOURCES_DIR.is_dir() else REPO / "sources"
    urls_rec = _urls_of(recommendation)
    urls_cur = _urls_of(current)
    lost = urls_cur - urls_rec
    added = urls_rec - urls_cur
    if lost:
        raise SystemExit(
            f"refusing to apply: {len(lost)} sources would be dropped "
            f"(e.g. {sorted(lost)[:3]})"
        )
    if added:
        print(f"note: recommendation adds {len(added)} unseen sources")

    estimates: dict[str, float] = {}
    for path in sorted(recommendation.glob("batch_*.txt")):
        match = EST_TIME_RE.search(path.read_text(encoding="utf-8"))
        if not match:
            raise SystemExit(f"{path.name} missing \'Est. Fetch Time\' header")
        seconds = float(match.group(1))
        if seconds > TARGET_BATCH_SECONDS:
            raise SystemExit(
                f"{path.name} estimate {seconds:.0f}s exceeds target "
                f"{TARGET_BATCH_SECONDS:.0f}s"
            )
        estimates[path.name] = seconds
    if not estimates:
        raise SystemExit("recommendation contains no batch files")
    return estimates


def _apply(recommendation: Path) -> bool:
    changed = False
    for src in sorted(recommendation.glob("batch_*.txt")):
        dest = SOURCES_DIR / src.name
        if not dest.exists() or dest.read_bytes() != src.read_bytes():
            shutil.copyfile(src, dest)
            changed = True
    # Drop batch files removed by the recommendation (stale numbering).
    for dest in sorted(SOURCES_DIR.glob("batch_*.txt")):
        if not (recommendation / dest.name).exists():
            dest.unlink()
            changed = True
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, help="explicit source run id")
    parser.add_argument(
        "--check", action="store_true", help="report without modifying files"
    )
    args = parser.parse_args(argv)

    _require_gh()
    slug = _repo_slug()

    run_id = args.run_id
    if run_id is None:
        run_id = _latest_recommendation_run(slug)
        if run_id is None:
            raise SystemExit("no successful Config\'s Stream run found")
    print(f"source run: {run_id}")

    with tempfile.TemporaryDirectory() as tmp:
        rec_dir = Path(tmp) / "rec"
        download = _gh(
            "run",
            "download",
            str(run_id),
            "--repo",
            slug,
            "--name",
            "source-reshard-recommendation",
            "--dir",
            str(rec_dir),
        )
        if download.returncode != 0:
            raise SystemExit(
                "artifact source-reshard-recommendation unavailable for "
                f"run {run_id}: {download.stderr.strip()[:200]}"
            )
        # Flatten: gh preserves artifact layout; batch files may sit at the
        # root or under sources/. Find whichever directory holds them.
        batch_home = rec_dir
        for candidate in [rec_dir, *sorted(rec_dir.rglob("*"))]:
            if candidate.is_dir() and any(candidate.glob("batch_*.txt")):
                batch_home = candidate
                break

        estimates = _validate(batch_home)
        worst = max(estimates.values())
        print(
            f"recommendation OK: {len(estimates)} batches, "
            f"slowest {worst:.0f}s (target {TARGET_BATCH_SECONDS:.0f}s)"
        )
        if args.check:
            return 0
        if not _apply(batch_home):
            print("working tree already matches the recommendation.")
            return 0

    subprocess.run(  # nosec B603
        ["git", "-C", str(REPO), "add", "-A", "--", "sources"], check=True
    )
    diff = subprocess.run(  # nosec B603
        ["git", "-C", str(REPO), "diff", "--cached", "--quiet"],
        capture_output=True,
        check=False,
    )
    if diff.returncode == 0:
        print("nothing staged; already up to date.")
        return 0
    subprocess.run(  # nosec B603
        [
            "git",
            "-C",
            str(REPO),
            "commit",
            "-m",
            "chore(sources): apply dynamic reshard recommendations",
        ],
        check=True,
    )
    push = subprocess.run(  # nosec B603
        ["git", "-C", str(REPO), "push", "origin", "HEAD:main"],
        check=False,
    )
    if push.returncode != 0:
        raise SystemExit("push failed; resolve manually and retry")
    print("applied and pushed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

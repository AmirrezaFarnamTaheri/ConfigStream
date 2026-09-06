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
import hashlib
import json
import re
import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCES_DIR = REPO / "sources"
TARGET_BATCH_SECONDS = 14400.0
EST_TIME_RE = re.compile(r"Est\. Fetch Time: ([\d.]+)s")
TIMING_WEIGHTS_FILENAME = "source_timing_weights.json"


def _resolve_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise SystemExit(f"{name} CLI not found on PATH; install it first.")
    return executable


def _gh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603
        [_resolve_executable("gh"), *args], capture_output=True, text=True, check=False
    )


def _require_gh() -> None:
    if _gh("--version").returncode != 0:
        raise SystemExit("gh CLI is not executable; reinstall GitHub CLI.")


def _repo_slug() -> str:
    url = subprocess.run(  # nosec B603
        [_resolve_executable("git"), "-C", str(REPO), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    if not match:
        raise SystemExit(f"cannot parse repository slug from {url}")
    return match.group(1)


def _latest_recommendation_run(slug: str) -> int | None:
    """Return newest workflow run containing a usable recommendation artifact."""
    result = _gh("api", f"repos/{slug}/actions/runs?per_page=30")
    if result.returncode != 0:
        return None
    try:
        runs = json.loads(result.stdout).get("workflow_runs", [])
    except (json.JSONDecodeError, AttributeError):
        return None
    for run in runs:
        if not isinstance(run, dict) or run.get("name") != "Config's Stream":
            continue
        try:
            run_id = int(run["id"])
        except (KeyError, TypeError, ValueError):
            continue
        artifacts = _gh("api", f"repos/{slug}/actions/runs/{run_id}/artifacts?per_page=100")
        if artifacts.returncode != 0:
            continue
        try:
            payload = json.loads(artifacts.stdout)
        except json.JSONDecodeError:
            continue
        if any(
            isinstance(a, dict)
            and a.get("name") == "source-reshard-recommendation"
            and not a.get("expired", False)
            for a in payload.get("artifacts", [])
        ):
            return run_id
    return None


def _urls_of(directory: Path) -> set[str]:
    urls: set[str] = set()
    for path in sorted(directory.glob("batch_*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(("http://", "https://")):
                urls.add(line)
    return urls


def _validate_timing_weights(recommendation: Path, urls: set[str]) -> None:
    path = recommendation / TIMING_WEIGHTS_FILENAME
    if not path.is_file():
        raise SystemExit(f"recommendation missing {TIMING_WEIGHTS_FILENAME}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: {exc}") from exc
    expected = hashlib.sha256(("\n".join(sorted(urls)) + "\n").encode()).hexdigest()
    if payload.get("schema_version") != 1 or payload.get("unit") != "deciseconds":
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: unsupported schema")
    if payload.get("source_set_sha256") != expected:
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: source-set mismatch")


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
        raise SystemExit(
            f"refusing to apply: {len(added)} unreviewed sources would be added "
            f"(e.g. {sorted(added)[:3]})"
        )
    _validate_timing_weights(recommendation, urls_rec)

    estimates: dict[str, float] = {}
    for path in sorted(recommendation.glob("batch_*.txt")):
        match = EST_TIME_RE.search(path.read_text(encoding="utf-8"))
        if not match:
            raise SystemExit(f"{path.name} missing 'Est. Fetch Time' header")
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
    sidecar = recommendation / TIMING_WEIGHTS_FILENAME
    sidecar_dest = SOURCES_DIR / TIMING_WEIGHTS_FILENAME
    if not sidecar_dest.exists() or sidecar_dest.read_bytes() != sidecar.read_bytes():
        shutil.copyfile(sidecar, sidecar_dest)
        changed = True
    for dest in sorted(SOURCES_DIR.glob("batch_*.txt")):
        if not (recommendation / dest.name).exists():
            dest.unlink()
            changed = True
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, help="explicit source run id")
    parser.add_argument("--check", action="store_true", help="report without modifying files")
    args = parser.parse_args(argv)

    _require_gh()
    slug = _repo_slug()
    run_id = args.run_id or _latest_recommendation_run(slug)
    if run_id is None:
        raise SystemExit(
            "no recent Config's Stream run contains an unexpired "
            "source-reshard-recommendation artifact"
        )
    print(f"source run: {run_id}")

    with tempfile.TemporaryDirectory() as tmp:
        rec_dir = Path(tmp) / "rec"
        download = _gh(
            "run", "download", str(run_id), "--repo", slug,
            "--name", "source-reshard-recommendation", "--dir", str(rec_dir),
        )
        if download.returncode != 0:
            raise SystemExit(
                "artifact source-reshard-recommendation unavailable for "
                f"run {run_id}: {download.stderr.strip()[:200]}"
            )
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

    git = _resolve_executable("git")
    subprocess.run([git, "-C", str(REPO), "add", "-A", "--", "sources"], check=True)  # nosec B603
    diff = subprocess.run(  # nosec B603
        [git, "-C", str(REPO), "diff", "--cached", "--quiet"],
        capture_output=True,
        check=False,
    )
    if diff.returncode == 0:
        print("nothing staged; already up to date.")
        return 0

    branch = f"chore/apply-reshard-{run_id}"
    subprocess.run([git, "-C", str(REPO), "switch", "-c", branch], check=True)  # nosec B603
    subprocess.run(  # nosec B603
        [git, "-C", str(REPO), "commit", "-m", "chore(sources): apply dynamic reshard recommendations"],
        check=True,
    )
    push = subprocess.run(  # nosec B603
        [git, "-C", str(REPO), "push", "--set-upstream", "origin", branch],
        capture_output=True,
        text=True,
        check=False,
    )
    if push.returncode != 0:
        raise SystemExit(f"push failed: {push.stderr.strip()[:200]}")
    pr = _gh(
        "pr", "create", "--repo", slug, "--base", "main", "--head", branch,
        "--title", "chore(sources): apply dynamic reshard recommendation",
        "--body", f"Applies validated source-reshard-recommendation from workflow run {run_id}.",
    )
    if pr.returncode != 0:
        raise SystemExit("branch pushed but PR creation failed")
    print(f"applied and opened review PR: {pr.stdout.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

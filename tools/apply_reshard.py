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
- each canonical upstream fetch identity may appear only once in the
  recommendation;
- the timing sidecar must match that exact source set and contain only
  positive integer weights for known opaque source IDs;
- every batch must carry an ``Est. Fetch Time`` header that matches the timing
  sidecar and remains at or below dynamic_reshard.TARGET_BATCH_SECONDS;
- mutation requires a clean worktree so unrelated local changes cannot be
  overwritten or included in the generated commit;
- a review branch is created before any source mutation;
- source-layout publication is staged and rolls back if the directory handoff
  fails;
- nothing is committed unless all checks pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from configstream.source_admission import normalize_source_locator

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
        artifacts = _gh(
            "api", f"repos/{slug}/actions/runs/{run_id}/artifacts?per_page=100"
        )
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


def _source_lines(path: Path) -> list[str]:
    return [
        line
        for raw_line in path.read_text(encoding="utf-8").splitlines()
        if (line := raw_line.strip())
        and line.startswith(("http://", "https://"))
    ]


def _source_entries(directory: Path) -> list[str]:
    entries: list[str] = []
    for path in sorted(directory.glob("batch_*.txt")):
        entries.extend(_source_lines(path))
    return entries


def _urls_of(directory: Path) -> set[str]:
    return set(_source_entries(directory))


def _canonical_source_urls(urls: set[str]) -> set[str]:
    return {normalize_source_locator(url) for url in urls}


def _source_set_sha256(urls: set[str]) -> str:
    canonical_urls = _canonical_source_urls(urls)
    return hashlib.sha256(
        ("\n".join(sorted(canonical_urls)) + "\n").encode("utf-8")
    ).hexdigest()


def _source_timing_id(url: str) -> str:
    canonical = normalize_source_locator(url)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require_unique_fetch_identities(recommendation: Path) -> None:
    seen: dict[str, str] = {}
    for url in _source_entries(recommendation):
        source_id = _source_timing_id(url)
        previous = seen.get(source_id)
        if previous is not None:
            raise SystemExit(
                "refusing to apply: recommendation repeats canonical source fetch "
                f"identity ({previous!r}, {url!r})"
            )
        seen[source_id] = url


def _validate_timing_weights(
    recommendation: Path, urls: set[str]
) -> tuple[dict[str, int], int]:
    path = recommendation / TIMING_WEIGHTS_FILENAME
    if not path.is_file():
        raise SystemExit(f"recommendation missing {TIMING_WEIGHTS_FILENAME}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: expected object")

    expected = _source_set_sha256(urls)
    if payload.get("schema_version") != 1 or payload.get("unit") != "deciseconds":
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: unsupported schema")
    if payload.get("source_set_sha256") != expected:
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: source-set mismatch")

    default_weight = payload.get("default_weight")
    raw_weights = payload.get("weights", {})
    if (
        not isinstance(default_weight, int)
        or isinstance(default_weight, bool)
        or default_weight < 1
        or not isinstance(raw_weights, dict)
    ):
        raise SystemExit(f"invalid {TIMING_WEIGHTS_FILENAME}: malformed weights")

    allowed_ids = {_source_timing_id(url) for url in urls}
    weights: dict[str, int] = {}
    for key, value in raw_weights.items():
        if (
            not isinstance(key, str)
            or len(key) != 64
            or any(char not in "0123456789abcdef" for char in key.lower())
            or key not in allowed_ids
            or not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise SystemExit(
                f"invalid {TIMING_WEIGHTS_FILENAME}: invalid source weight"
            )
        weights[key] = value
    return weights, default_weight


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
    _require_unique_fetch_identities(recommendation)
    timing_weights, default_weight = _validate_timing_weights(recommendation, urls_rec)

    estimates: dict[str, float] = {}
    for path in sorted(recommendation.glob("batch_*.txt")):
        match = EST_TIME_RE.search(path.read_text(encoding="utf-8"))
        if not match:
            raise SystemExit(f"{path.name} missing 'Est. Fetch Time' header")
        declared_seconds = float(match.group(1))
        computed_seconds = sum(
            timing_weights.get(_source_timing_id(url), default_weight)
            for url in _source_lines(path)
        ) / 10.0
        if abs(declared_seconds - computed_seconds) > 0.05:
            raise SystemExit(
                f"{path.name} estimate {declared_seconds:.1f}s does not match "
                f"timing sidecar ({computed_seconds:.1f}s)"
            )
        if computed_seconds > TARGET_BATCH_SECONDS:
            raise SystemExit(
                f"{path.name} estimate {computed_seconds:.0f}s exceeds target "
                f"{TARGET_BATCH_SECONDS:.0f}s"
            )
        estimates[path.name] = computed_seconds
    if not estimates:
        raise SystemExit("recommendation contains no batch files")
    return estimates


def _require_clean_worktree() -> None:
    git = _resolve_executable("git")
    status = subprocess.run(  # nosec B603
        [git, "-C", str(REPO), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode != 0:
        raise SystemExit("cannot verify clean worktree before applying recommendation")
    if status.stdout.strip():
        raise SystemExit(
            "refusing to apply with local changes; commit or stash the worktree first"
        )


def _layout_matches(recommendation: Path) -> bool:
    current_batches = {path.name: path for path in SOURCES_DIR.glob("batch_*.txt")}
    recommended_batches = {
        path.name: path for path in recommendation.glob("batch_*.txt")
    }
    if set(current_batches) != set(recommended_batches):
        return False
    if any(
        current_batches[name].read_bytes() != recommended_batches[name].read_bytes()
        for name in current_batches
    ):
        return False

    current_sidecar = SOURCES_DIR / TIMING_WEIGHTS_FILENAME
    recommended_sidecar = recommendation / TIMING_WEIGHTS_FILENAME
    return (
        current_sidecar.is_file()
        and recommended_sidecar.is_file()
        and current_sidecar.read_bytes() == recommended_sidecar.read_bytes()
    )


def _apply(recommendation: Path) -> bool:
    """Publish a validated source layout with rollback-safe directory handoff."""

    if _layout_matches(recommendation):
        return False

    transaction_root = Path(
        tempfile.mkdtemp(prefix=".reshard-transaction-", dir=SOURCES_DIR.parent)
    )
    staged_sources = transaction_root / "next"
    backup_sources = transaction_root / "previous"
    old_moved = False

    try:
        shutil.copytree(SOURCES_DIR, staged_sources, symlinks=True)
        for stale in staged_sources.glob("batch_*.txt"):
            stale.unlink()
        staged_sidecar = staged_sources / TIMING_WEIGHTS_FILENAME
        if staged_sidecar.exists():
            staged_sidecar.unlink()

        for src in sorted(recommendation.glob("batch_*.txt")):
            shutil.copy2(src, staged_sources / src.name)
        shutil.copy2(
            recommendation / TIMING_WEIGHTS_FILENAME,
            staged_sources / TIMING_WEIGHTS_FILENAME,
        )

        os.replace(SOURCES_DIR, backup_sources)
        old_moved = True
        try:
            os.replace(staged_sources, SOURCES_DIR)
        except BaseException:
            try:
                os.replace(backup_sources, SOURCES_DIR)
                old_moved = False
            except BaseException as rollback_exc:
                raise RuntimeError(
                    "source-layout publication failed and rollback could not restore "
                    "the previous sources directory"
                ) from rollback_exc
            raise

        old_moved = False
        return True
    finally:
        if old_moved and backup_sources.exists() and not SOURCES_DIR.exists():
            try:
                os.replace(backup_sources, SOURCES_DIR)
            except OSError as rollback_exc:
                raise RuntimeError(
                    "source-layout transaction exited without a live sources "
                    "directory and rollback failed"
                ) from rollback_exc
        shutil.rmtree(transaction_root, ignore_errors=True)


def _create_review_branch(git: str, branch: str) -> None:
    result = subprocess.run(  # nosec B603
        [git, "-C", str(REPO), "switch", "-c", branch],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            "cannot create review branch before applying recommendation: "
            f"{result.stderr.strip()[:200]}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, help="explicit source run id")
    parser.add_argument(
        "--check", action="store_true", help="report without modifying files"
    )
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
    branch = f"chore/apply-reshard-{run_id}"
    git = _resolve_executable("git")

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
        _require_clean_worktree()
        if _layout_matches(batch_home):
            print("working tree already matches the recommendation.")
            return 0
        _create_review_branch(git, branch)
        if not _apply(batch_home):
            raise RuntimeError("validated source layout changed before publication")

    subprocess.run(  # nosec B603
        [git, "-C", str(REPO), "add", "-A", "--", "sources"], check=True
    )
    diff = subprocess.run(  # nosec B603
        [git, "-C", str(REPO), "diff", "--cached", "--quiet"],
        capture_output=True,
        check=False,
    )
    if diff.returncode == 0:
        print("nothing staged; already up to date.")
        return 0

    subprocess.run(  # nosec B603
        [
            git,
            "-C",
            str(REPO),
            "commit",
            "-m",
            "chore(sources): apply dynamic reshard recommendations",
        ],
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
        "pr",
        "create",
        "--repo",
        slug,
        "--base",
        "main",
        "--head",
        branch,
        "--title",
        "chore(sources): apply dynamic reshard recommendation",
        "--body",
        f"Applies validated source-reshard-recommendation from workflow run {run_id}.",
    )
    if pr.returncode != 0:
        raise SystemExit("branch pushed but PR creation failed")
    print(f"applied and opened review PR: {pr.stdout.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

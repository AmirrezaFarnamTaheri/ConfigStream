# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate immutable container bases and target separation."""

from __future__ import annotations
import json
import re
from pathlib import Path

FROM_RE = re.compile(r"(?m)^FROM\s+([^\s]+)(?:\s+AS\s+([\w-]+))?\s*$", re.I)
DIGEST_RE = re.compile(r"@sha256:[0-9a-f]{64}$")


def validate(root: Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    manifest = json.loads(
        (root / "config/container-images.json").read_text(encoding="utf-8")
    )
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (root / ".dockerignore").read_text(encoding="utf-8")
    refs = {
        match.group(1)
        for match in FROM_RE.finditer(dockerfile)
        if match.group(1) not in {"app-base"}
    }
    refs.update(re.findall(r"--from=([^\s]+)", dockerfile))
    expected = {
        f"{item['reference']}@{item['digest']}" for item in manifest["images"].values()
    }
    missing = sorted(expected - refs)
    if missing:
        errors.extend(f"Dockerfile missing pinned image {ref}" for ref in missing)
    for ref in refs:
        if ":latest" in ref:
            errors.append(f"mutable latest tag: {ref}")
        if ref.startswith(
            ("golang:", "node:", "python:", "ghcr.io/")
        ) and not DIGEST_RE.search(ref):
            errors.append(f"external image not digest-pinned: {ref}")
    if (
        "FROM app-base AS runtime" not in dockerfile
        or "FROM app-base AS ci-runner" not in dockerfile
    ):
        errors.append("Dockerfile must expose distinct runtime and ci-runner targets")
    if "uv pip install --no-cache-dir --no-deps ." not in dockerfile:
        errors.append(
            "application install must not re-resolve pinned production dependencies"
        )
    runtime_tail = dockerfile.split("FROM app-base AS runtime", 1)[-1]
    if "/usr/local/lib/node_modules" in runtime_tail:
        errors.append("production runtime target must not copy Node/npm")
    if "apt-get purge -y curl unzip" not in runtime_tail:
        errors.append("production runtime target must remove build/network utilities")
    if "rm -rf /var/lib/apt/lists/* /bin/uv /bin/uvx" not in runtime_tail:
        errors.append("production runtime target must remove package-manager tooling")
    if "sources/" not in dockerignore and "sources/*" not in dockerignore:
        errors.append("container context must exclude canonical source batches")
    if not (root / "src/configstream/data/source-admission.json").is_file():
        errors.append("bundled source-admission.json is missing from package data")
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    if 'configstream = ["data/*.json"]' not in pyproject:
        errors.append("pyproject must include ConfigStream JSON package data")
    workflow = (root / ".github/workflows/main.yml").read_text(encoding="utf-8")
    if "target: ci-runner" not in workflow:
        errors.append("pipeline container build must target ci-runner")
    render = (root / "render.yaml").read_text(encoding="utf-8")
    if "dockerCommand: python -m configstream.server" not in render:
        errors.append("Render Docker service must explicitly start the HTTP server")
    return errors


def main() -> int:
    errors = validate(Path("."))
    if errors:
        print("ERROR: container pin validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: container images and build targets are immutable and separated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate direct-dependency and update-automation evidence."""
from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path

import yaml

_GO_LINE = re.compile(r"^\s*([^\s()]+)\s+v([^\s]+)(?:\s+//.*)?$")
_REQUIRED_COVERAGE = {
    ("github-actions", "/"),
    ("pip", "/"),
    ("npm", "/"),
    ("docker", "/"),
    ("gomod", "/src/go/tester"),
    ("gomod", "/src/go/utls_client"),
    ("cargo", "/src/rust/ss_checker"),
}


def _python(root: Path) -> list[dict[str, str]]:
    payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    result: list[dict[str, str]] = []
    groups = [
        (payload["project"].get("dependencies", []), "runtime"),
        (payload["project"].get("optional-dependencies", {}).get("dev", []), "development"),
    ]
    for values, scope in groups:
        for raw in values:
            name = re.split(r"[<>=!~;\[]", str(raw), maxsplit=1)[0].strip()
            result.append(
                {
                    "name": name,
                    "constraint": str(raw),
                    "source": "pyproject.toml",
                    "scope": scope,
                }
            )
    for raw_line in (root / "requirements-publish.txt").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^;\s]+)$", line)
        if match:
            result.append(
                {
                    "name": match.group(1),
                    "constraint": "==" + match.group(2),
                    "source": "requirements-publish.txt",
                    "scope": "publisher",
                }
            )
    return result


def _npm(root: Path) -> list[dict[str, str]]:
    payload = json.loads((root / "package.json").read_text(encoding="utf-8"))
    result = []
    for section in ("dependencies", "devDependencies"):
        for name, constraint in sorted(payload.get(section, {}).items()):
            result.append(
                {"name": name, "constraint": str(constraint), "source": "package.json", "scope": section}
            )
    return result


def _go_module(path: Path, root: Path) -> list[dict[str, str]]:
    result = []
    in_block = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "require (":
            in_block = True
            continue
        if in_block and stripped == ")":
            in_block = False
            continue
        if not in_block and not stripped.startswith("require "):
            continue
        candidate = stripped.removeprefix("require ")
        if "// indirect" in candidate:
            continue
        match = _GO_LINE.match(candidate)
        if match:
            result.append(
                {
                    "name": match.group(1),
                    "constraint": "v" + match.group(2),
                    "source": path.relative_to(root).as_posix(),
                }
            )
    return result


def _cargo(root: Path) -> list[dict[str, str]]:
    path = root / "src/rust/ss_checker/Cargo.toml"
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    result = []
    for name, raw in sorted(payload.get("dependencies", {}).items()):
        constraint = raw if isinstance(raw, str) else raw.get("version", "unversioned")
        result.append(
            {"name": str(name), "constraint": str(constraint), "source": path.relative_to(root).as_posix()}
        )
    return result


def _containers(root: Path) -> list[dict[str, str]]:
    payload = json.loads((root / "config/container-images.json").read_text(encoding="utf-8"))
    images = payload.get("images", payload)
    result = []
    for name, value in sorted(images.items()):
        if isinstance(value, dict):
            reference = str(value.get("reference") or value.get("image") or "")
        else:
            reference = str(value)
        result.append({"name": str(name), "constraint": reference, "source": "config/container-images.json"})
    return result


def _dependabot(root: Path) -> tuple[list[dict[str, str]], list[str]]:
    path = root / ".github/dependabot.yml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    coverage: list[dict[str, str]] = []
    errors: list[str] = []
    observed: set[tuple[str, str]] = set()
    for item in payload.get("updates", []):
        ecosystem = str(item.get("package-ecosystem", ""))
        directories = item.get("directories") or [item.get("directory")]
        for directory in directories:
            pair = (ecosystem, str(directory))
            observed.add(pair)
            coverage.append({"ecosystem": pair[0], "directory": pair[1]})
        schedule = item.get("schedule", {})
        if schedule.get("interval") not in {"daily", "weekly", "monthly", "quarterly", "semiannually", "yearly", "cron"}:
            errors.append(f"invalid or missing Dependabot schedule for {ecosystem}:{directories}")
    for ecosystem, directory in sorted(_REQUIRED_COVERAGE - observed):
        errors.append(f"missing Dependabot coverage: {ecosystem}:{directory}")
    return sorted(coverage, key=lambda item: (item["ecosystem"], item["directory"])), errors


def build(root: Path) -> tuple[dict[str, object], list[str]]:
    coverage, errors = _dependabot(root)
    ecosystems = {
        "python": _python(root),
        "npm": _npm(root),
        "go-tester": _go_module(root / "src/go/tester/go.mod", root),
        "go-utls": _go_module(root / "src/go/utls_client/go.mod", root),
        "cargo": _cargo(root),
        "container": _containers(root),
    }
    payload = {
        "schema_version": 1,
        "evidence_basis": "Direct declarations from checked-in manifests; latest-version resolution is delegated to Dependabot and is not inferred offline.",
        "ecosystem_count": len(ecosystems),
        "direct_dependency_count": sum(len(values) for values in ecosystems.values()),
        "dependabot_coverage": coverage,
        "ecosystems": ecosystems,
    }
    return payload, errors


def _markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Direct dependency inventory",
        "",
        str(payload["evidence_basis"]),
        "",
        f"Ecosystems: **{payload['ecosystem_count']}**",
        f"Direct declarations: **{payload['direct_dependency_count']}**",
        "",
        "## Dependabot coverage",
        "",
        "| Ecosystem | Directory |",
        "|---|---|",
    ]
    for item in payload["dependabot_coverage"]:
        lines.append(f"| `{item['ecosystem']}` | `{item['directory']}` |")
    lines.extend(["", "## Direct declarations", "", "| Group | Name | Constraint | Source |", "|---|---|---|---|"])
    for group, items in payload["ecosystems"].items():
        for item in items:
            constraint = str(item["constraint"]).replace("|", "\\|")
            lines.append(f"| {group} | `{item['name']}` | `{constraint}` | `{item['source']}` |")
    return "\n".join(lines) + "\n"


def generate(root: Path, *, check: bool = False) -> list[str]:
    root = Path(root)
    payload, errors = build(root)
    targets = {
        root / "docs/generated/dependency-inventory.json": json.dumps(payload, indent=2, sort_keys=True) + "\n",
        root / "docs/generated/dependency-inventory.md": _markdown(payload),
    }
    for path, content in targets.items():
        if check:
            try:
                current = path.read_text(encoding="utf-8")
            except OSError:
                errors.append(f"missing dependency inventory: {path.relative_to(root)}")
                continue
            if current != content:
                errors.append(f"generated dependency inventory is stale: {path.relative_to(root)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    errors = generate(Path("."), check=args.check)
    if errors:
        print("ERROR: dependency inventory/update coverage is invalid")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: dependency inventory and update coverage are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

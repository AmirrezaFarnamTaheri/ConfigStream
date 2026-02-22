# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check dependency drift between pyproject and lock-style requirement files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class ProjectDependency:
    name: str
    specifier: str


_PROJECT_DEPS_BLOCK_RE = re.compile(
    r"(?ms)^\[project\].*?^dependencies\s*=\s*\[(.*?)^\]",
)
_REQ_PIN_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*==\s*([^\s;#]+)\s*$")
_DEP_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?")


def _normalize_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def _extract_project_dependencies(pyproject_text: str) -> List[str]:
    match = _PROJECT_DEPS_BLOCK_RE.search(pyproject_text)
    if not match:
        return []

    block = match.group(1)
    entries: List[str] = []
    for raw_line in block.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.endswith(","):
            line = line[:-1].strip()
        if len(line) >= 2 and line[0] in ("'", '"') and line[-1] == line[0]:
            line = line[1:-1]
        if line:
            entries.append(line)
    return entries


def _parse_project_dependency(entry: str) -> Optional[ProjectDependency]:
    dep_part = entry.split(";", 1)[0].strip()
    if not dep_part:
        return None
    name_match = _DEP_NAME_RE.match(dep_part)
    if not name_match:
        return None
    raw_name = name_match.group(1)
    name = _normalize_name(raw_name)
    specifier = dep_part[name_match.end() :].strip()
    return ProjectDependency(name=name, specifier=specifier)


def _parse_requirements_pins(text: str) -> Dict[str, str]:
    pins: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            continue
        match = _REQ_PIN_RE.match(line)
        if not match:
            continue
        name, version = match.groups()
        pins[_normalize_name(name)] = version.strip()
    return pins


def _minimum_version_from_specifier(specifier: str) -> Optional[str]:
    if not specifier:
        return None
    compact = specifier.replace(" ", "")
    if compact.startswith(">="):
        return compact[2:]
    if compact.startswith("~="):
        return compact[2:]
    if compact.startswith("=="):
        return compact[2:]
    return None


def _version_tuple(value: str) -> Tuple[int, ...]:
    parts: List[int] = []
    for token in re.split(r"[.\-+]", value):
        if not token:
            continue
        match = re.match(r"(\d+)", token)
        if not match:
            break
        parts.append(int(match.group(1)))
    return tuple(parts)


def _is_version_at_least(pinned: str, minimum: str) -> bool:
    p = _version_tuple(pinned)
    m = _version_tuple(minimum)
    if not p or not m:
        return True
    length = max(len(p), len(m))
    p_ext = p + (0,) * (length - len(p))
    m_ext = m + (0,) * (length - len(m))
    return p_ext >= m_ext


def check_dependency_drift(
    *,
    pyproject_path: Path,
    requirements_prod_path: Path,
    requirements_dev_path: Optional[Path] = None,
) -> List[str]:
    errors: List[str] = []
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    req_prod_text = requirements_prod_path.read_text(encoding="utf-8")
    req_dev_text = (
        requirements_dev_path.read_text(encoding="utf-8")
        if requirements_dev_path and requirements_dev_path.exists()
        else ""
    )

    dep_entries = _extract_project_dependencies(pyproject_text)
    deps = [d for d in (_parse_project_dependency(e) for e in dep_entries) if d]
    req_prod = _parse_requirements_pins(req_prod_text)
    req_dev = _parse_requirements_pins(req_dev_text)

    for dep in deps:
        pinned_prod = req_prod.get(dep.name)
        if not pinned_prod:
            errors.append(f"requirements-prod.txt missing pin for '{dep.name}'")
            continue
        pinned_dev = req_dev.get(dep.name)
        if req_dev_text and not pinned_dev:
            errors.append(f"requirements.txt missing pin for '{dep.name}'")
        minimum = _minimum_version_from_specifier(dep.specifier)
        if minimum and not _is_version_at_least(pinned_prod, minimum):
            errors.append(
                f"requirements-prod.txt pin for '{dep.name}' ({pinned_prod}) "
                f"is below pyproject minimum ({minimum})"
            )
        if minimum and pinned_dev and not _is_version_at_least(pinned_dev, minimum):
            errors.append(
                f"requirements.txt pin for '{dep.name}' ({pinned_dev}) "
                f"is below pyproject minimum ({minimum})"
            )

    return errors


def _render_errors(errors: Iterable[str]) -> str:
    return "\n".join(f"- {e}" for e in errors)


def main() -> None:
    root = Path(".")
    pyproject_path = root / "pyproject.toml"
    requirements_prod_path = root / "requirements-prod.txt"
    requirements_dev_path = root / "requirements.txt"

    missing_files = [
        str(p)
        for p in (pyproject_path, requirements_prod_path, requirements_dev_path)
        if not p.exists()
    ]
    if missing_files:
        raise SystemExit("Missing dependency files:\n" + _render_errors(missing_files))

    errors = check_dependency_drift(
        pyproject_path=pyproject_path,
        requirements_prod_path=requirements_prod_path,
        requirements_dev_path=requirements_dev_path,
    )
    if errors:
        raise SystemExit("Dependency drift detected:\n" + _render_errors(errors))
    print("Dependency drift check passed.")


if __name__ == "__main__":
    main()

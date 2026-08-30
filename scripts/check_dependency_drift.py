# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check dependency drift between pyproject and lock-style requirement files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


@dataclass(frozen=True)
class ProjectDependency:
    name: str
    specifier: str


_PROJECT_DEPS_BLOCK_RE = re.compile(
    r"(?ms)^\[project\].*?^dependencies\s*=\s*\[(.*?)^\]",
)
_OPTIONAL_DEV_DEPS_BLOCK_RE = re.compile(
    r"(?ms)^\[project\.optional-dependencies\].*?^dev\s*=\s*\[(.*?)^\]",
)
_REQ_PIN_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*==\s*([^\s;#]+)\s*$")
_DEP_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?")


def _normalize_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def _load_project_table(pyproject_text: str) -> dict:
    payload = tomllib.loads(pyproject_text)
    project = payload.get("project", {})
    return project if isinstance(project, dict) else {}


def _extract_build_dependencies(pyproject_text: str) -> List[str]:
    payload = tomllib.loads(pyproject_text)
    build_system = payload.get("build-system", {})
    if not isinstance(build_system, dict):
        return []
    values = build_system.get("requires", [])
    return [str(value) for value in values] if isinstance(values, list) else []


def _extract_project_dependencies(pyproject_text: str) -> List[str]:
    values = _load_project_table(pyproject_text).get("dependencies", [])
    return [str(value) for value in values] if isinstance(values, list) else []


def _extract_dev_dependencies(pyproject_text: str) -> List[str]:
    optional = _load_project_table(pyproject_text).get("optional-dependencies", {})
    if not isinstance(optional, dict):
        return []
    values = optional.get("dev", [])
    return [str(value) for value in values] if isinstance(values, list) else []


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


def _load_requirements_pins(
    path: Path, seen: Optional[set[Path]] = None
) -> Dict[str, str]:
    """Load exact pins from a requirements file and its local ``-r`` includes."""
    resolved = path.resolve()
    visited = set() if seen is None else seen
    if resolved in visited:
        return {}
    visited.add(resolved)
    text = path.read_text(encoding="utf-8")
    pins = _parse_requirements_pins(text)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith(("-r ", "--requirement ")):
            continue
        include_name = line.split(maxsplit=1)[1].strip()
        include_path = (path.parent / include_name).resolve()
        pins.update(_load_requirements_pins(include_path, visited))
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
    req_dev_text = (
        requirements_dev_path.read_text(encoding="utf-8")
        if requirements_dev_path and requirements_dev_path.exists()
        else ""
    )

    dep_entries = _extract_project_dependencies(pyproject_text)
    deps = [d for d in (_parse_project_dependency(e) for e in dep_entries) if d]
    req_prod = _load_requirements_pins(requirements_prod_path)
    req_dev = (
        _load_requirements_pins(requirements_dev_path)
        if requirements_dev_path and requirements_dev_path.exists()
        else {}
    )

    dev_entries = _extract_dev_dependencies(pyproject_text)
    dev_deps = [d for d in (_parse_project_dependency(e) for e in dev_entries) if d]
    build_entries = _extract_build_dependencies(pyproject_text)
    build_deps = [d for d in (_parse_project_dependency(e) for e in build_entries) if d]

    for dep in deps:
        pinned_prod = req_prod.get(dep.name)
        if not pinned_prod:
            errors.append(f"requirements-prod.txt missing pin for '{dep.name}'")
            continue
        pinned_dev = req_dev.get(dep.name)
        if req_dev_text and not pinned_dev:
            errors.append(f"requirements-dev.txt missing pin for '{dep.name}'")
        minimum = _minimum_version_from_specifier(dep.specifier)
        if minimum and not _is_version_at_least(pinned_prod, minimum):
            errors.append(
                f"requirements-prod.txt pin for '{dep.name}' ({pinned_prod}) "
                f"is below pyproject minimum ({minimum})"
            )
        if minimum and pinned_dev and not _is_version_at_least(pinned_dev, minimum):
            errors.append(
                f"requirements-dev.txt pin for '{dep.name}' ({pinned_dev}) "
                f"is below pyproject minimum ({minimum})"
            )

    for dep in dev_deps:
        pinned_dev = req_dev.get(dep.name)
        if not pinned_dev:
            errors.append(
                f"requirements-dev.txt missing pin for optional dev dependency '{dep.name}'"
            )
            continue
        minimum = _minimum_version_from_specifier(dep.specifier)
        if minimum and not _is_version_at_least(pinned_dev, minimum):
            errors.append(
                f"requirements-dev.txt pin for optional dev dependency '{dep.name}' "
                f"({pinned_dev}) is below pyproject minimum ({minimum})"
            )

    for dep in build_deps:
        if not dep.specifier.startswith("=="):
            errors.append(
                f"pyproject build dependency '{dep.name}' must use an exact pin"
            )
            continue
        expected = dep.specifier[2:].strip()
        pinned_dev = req_dev.get(dep.name)
        if pinned_dev != expected:
            errors.append(
                f"requirements-dev.txt build dependency '{dep.name}' must match "
                f"pyproject pin {expected}; found {pinned_dev or 'missing'}"
            )

    return errors


def _render_errors(errors: Iterable[str]) -> str:
    return "\n".join(f"- {e}" for e in errors)


_REQUIRED_PUBLISHER_PACKAGES = {
    "huggingface-hub",
    "google-api-python-client",
    "google-auth",
}


def check_publisher_pins(path: Path) -> List[str]:
    """Require an exact, reviewed publisher lock without duplicating its versions."""
    if not path.exists():
        return ["Missing dependency file: requirements-publish.txt"]

    text = path.read_text(encoding="utf-8")
    pins = _parse_requirements_pins(text)
    errors: List[str] = []

    for name in sorted(_REQUIRED_PUBLISHER_PACKAGES):
        if name not in pins:
            errors.append(
                f"requirements-publish.txt must exact-pin required publisher package '{name}'"
            )

    unexpected = sorted(set(pins) - _REQUIRED_PUBLISHER_PACKAGES)
    if unexpected:
        errors.append(
            "requirements-publish.txt contains unreviewed packages: "
            + ", ".join(unexpected)
        )

    non_comment_entries = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    malformed = [line for line in non_comment_entries if not _REQ_PIN_RE.match(line)]
    if malformed:
        errors.append(
            "requirements-publish.txt contains non-exact dependency entries: "
            + ", ".join(malformed)
        )
    return errors


def check_workflow_dependency_installs(workflow_dir: Path) -> List[str]:
    """Reject ad hoc dependency resolution in GitHub workflows."""
    errors: List[str] = []
    workflow_text = {
        path: path.read_text(encoding="utf-8")
        for path in sorted(workflow_dir.glob("*.yml"))
    }
    forbidden = {
        "pip install -e .[dev]": "install requirements-dev.txt then use --no-deps",
        'pip install -e ".[dev]"': "install requirements-dev.txt then use --no-deps",
        "pip install huggingface_hub": "install requirements-publish.txt",
        "pip install google-api-python-client": "install requirements-publish.txt",
        "pip install google-auth": "install requirements-publish.txt",
        "pip install pyinstaller": "install requirements-dev.txt",
        "pip install build": "install requirements-dev.txt",
        "pip install jsonschema": "install requirements-dev.txt",
    }
    for path, text in workflow_text.items():
        for needle, guidance in forbidden.items():
            if needle in text:
                errors.append(f"{path}: ad hoc '{needle}'; {guidance}")

    required_dev = {
        "ci.yml",
        "main.yml",
        "release.yml",
        "replay-release-preparation.yml",
        "retest.yml",
    }
    for name in sorted(required_dev):
        path = workflow_dir / name
        if path.exists() and "requirements-dev.txt" not in workflow_text[path]:
            errors.append(f"{path}: missing requirements-dev.txt installation")

    for name in ("replay-release-preparation.yml",):
        path = workflow_dir / name
        if path.exists() and "requirements-publish.txt" not in workflow_text[path]:
            errors.append(f"{path}: missing requirements-publish.txt installation")
    return errors


def main() -> None:
    root = Path(".")
    pyproject_path = root / "pyproject.toml"
    requirements_prod_path = root / "requirements-prod.txt"
    requirements_dev_path = root / "requirements-dev.txt"
    requirements_publish_path = root / "requirements-publish.txt"

    compatibility_path = root / "requirements.txt"
    expected_compatibility = (
        "# SPDX-License-Identifier: AGPL-3.0-or-later\n"
        "# Compatibility entry point for a complete development environment.\n"
        "# Runtime-only installs use requirements-prod.txt directly.\n"
        "-r requirements-dev.txt\n"
    )
    if not compatibility_path.exists():
        raise SystemExit("Missing dependency file: requirements.txt")
    if compatibility_path.read_text(encoding="utf-8") != expected_compatibility:
        raise SystemExit(
            "requirements.txt must remain a compatibility include for requirements-dev.txt"
        )

    missing_files = [
        str(p)
        for p in (
            pyproject_path,
            requirements_prod_path,
            requirements_dev_path,
            requirements_publish_path,
        )
        if not p.exists()
    ]
    if missing_files:
        raise SystemExit("Missing dependency files:\n" + _render_errors(missing_files))

    errors = check_dependency_drift(
        pyproject_path=pyproject_path,
        requirements_prod_path=requirements_prod_path,
        requirements_dev_path=requirements_dev_path,
    )
    errors.extend(check_publisher_pins(requirements_publish_path))
    errors.extend(check_workflow_dependency_installs(root / ".github" / "workflows"))
    if errors:
        raise SystemExit("Dependency drift detected:\n" + _render_errors(errors))
    print("Dependency drift check passed.")


if __name__ == "__main__":
    main()

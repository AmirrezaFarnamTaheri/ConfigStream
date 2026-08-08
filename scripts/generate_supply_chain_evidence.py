# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate deterministic multi-ecosystem SBOM and license evidence."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility
    import tomli as tomllib

_REQUIREMENT = re.compile(r"^([A-Za-z0-9_.-]+)==([^;\s]+)")
_GO_REQUIREMENT = re.compile(r"^\s*([^\s()]+)\s+v([^\s]+)(?:\s+//\s+indirect)?\s*$")


@dataclass(frozen=True)
class Component:
    ecosystem: str
    name: str
    version: str
    scope: str
    licenses: tuple[str, ...] = ()
    source: str = ""

    @property
    def purl(self) -> str:
        kind = {"python": "pypi", "npm": "npm", "go": "golang", "cargo": "cargo"}[
            self.ecosystem
        ]
        return f"pkg:{kind}/{quote(self.name, safe='@/')}@{quote(self.version, safe='.+_-')}"

    @property
    def bom_ref(self) -> str:
        return self.purl


def _python_components(root: Path) -> list[Component]:
    components: list[Component] = []
    path = root / "requirements-prod.txt"
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _REQUIREMENT.match(line.strip())
        if match:
            components.append(
                Component(
                    "python",
                    match.group(1),
                    match.group(2),
                    "required",
                    source="requirements-prod.txt",
                )
            )
    return components


def _npm_name(package_path: str, payload: dict[str, object]) -> str | None:
    explicit = payload.get("name")
    if isinstance(explicit, str) and explicit:
        return explicit
    prefix = "node_modules/"
    if not package_path.startswith(prefix):
        return None
    remainder = package_path[len(prefix) :]
    if remainder.startswith("@"):
        parts = remainder.split("/")
        return "/".join(parts[:2]) if len(parts) >= 2 else None
    return remainder.split("/", 1)[0]


def _license_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    if isinstance(value, list):
        return tuple(sorted({str(item).strip() for item in value if str(item).strip()}))
    return ()


def _npm_components(root: Path) -> list[Component]:
    lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
    packages = lock.get("packages", {})
    if not isinstance(packages, dict):
        return []
    components: list[Component] = []
    for package_path, raw in packages.items():
        if not package_path or not isinstance(raw, dict):
            continue
        name = _npm_name(str(package_path), raw)
        version = raw.get("version")
        if not name or not isinstance(version, str):
            continue
        scope = (
            "optional"
            if raw.get("optional")
            else ("development" if raw.get("dev") else "required")
        )
        components.append(
            Component(
                "npm",
                name,
                version,
                scope,
                _license_tuple(raw.get("license")),
                "package-lock.json",
            )
        )
    return components


def _go_components(root: Path) -> list[Component]:
    lines = (root / "src/go/tester/go.mod").read_text(encoding="utf-8").splitlines()
    components: list[Component] = []
    in_require = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped == "require (":
            in_require = True
            continue
        if in_require and stripped == ")":
            in_require = False
            continue
        candidate = (
            stripped.removeprefix("require ")
            if stripped.startswith("require ")
            else stripped
        )
        if not in_require and not stripped.startswith("require "):
            continue
        match = _GO_REQUIREMENT.match(candidate)
        if not match:
            continue
        scope = "development" if "// indirect" in raw_line else "required"
        components.append(
            Component(
                "go",
                match.group(1),
                match.group(2),
                scope,
                source="src/go/tester/go.mod",
            )
        )
    return components


def _cargo_components(root: Path) -> list[Component]:
    path = root / "src/rust/ss_checker/Cargo.toml"
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    components: list[Component] = []
    for section, scope in (
        ("dependencies", "required"),
        ("dev-dependencies", "development"),
    ):
        deps = payload.get(section, {})
        if not isinstance(deps, dict):
            continue
        for name, raw in deps.items():
            if isinstance(raw, str):
                version = raw
            elif isinstance(raw, dict):
                version = str(raw.get("version") or "unversioned")
            else:
                continue
            components.append(
                Component(
                    "cargo",
                    str(name),
                    version,
                    scope,
                    source="src/rust/ss_checker/Cargo.toml",
                )
            )
    return components


def build_components(root: Path) -> list[Component]:
    components = (
        _python_components(root)
        + _npm_components(root)
        + _go_components(root)
        + _cargo_components(root)
    )
    unique: dict[tuple[str, str, str], Component] = {}
    for component in components:
        key = (component.ecosystem, component.name.lower(), component.version)
        previous = unique.get(key)
        if previous is None or (
            previous.scope == "development" and component.scope == "required"
        ):
            unique[key] = component
    return sorted(
        unique.values(),
        key=lambda item: (item.ecosystem, item.name.lower(), item.version),
    )


def _project_version(root: Path) -> str:
    payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload.get("project")
    if not isinstance(project, dict) or not isinstance(project.get("version"), str):
        raise ValueError("pyproject.toml must define project.version")
    return str(project["version"])


def _sbom(root: Path, components: list[Component]) -> dict[str, object]:
    rendered = []
    for component in components:
        item: dict[str, object] = {
            "type": "library",
            "bom-ref": component.bom_ref,
            "name": component.name,
            "version": component.version,
            "scope": "required" if component.scope == "required" else "optional",
            "purl": component.purl,
            "properties": [
                {"name": "configstream:ecosystem", "value": component.ecosystem},
                {"name": "configstream:dependency-scope", "value": component.scope},
                {"name": "configstream:source-manifest", "value": component.source},
            ],
        }
        if component.licenses:
            item["licenses"] = [
                {"license": {"id": license_name}} for license_name in component.licenses
            ]
        rendered.append(item)
    return {
        "$schema": "https://cyclonedx.org/schema/bom-1.6.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "ConfigStream",
                "version": _project_version(root),
                "licenses": [{"license": {"id": "AGPL-3.0-or-later"}}],
            },
            "properties": [
                {
                    "name": "configstream:generation-mode",
                    "value": "offline-manifest-derived",
                },
                {
                    "name": "configstream:license-confidence",
                    "value": "manifest-declared-only",
                },
            ],
        },
        "components": rendered,
    }


def _license_report(components: list[Component]) -> dict[str, object]:
    rendered = [
        {
            "ecosystem": item.ecosystem,
            "name": item.name,
            "version": item.version,
            "scope": item.scope,
            "source": item.source,
            "licenses": list(item.licenses),
            "license_status": "declared" if item.licenses else "unknown",
        }
        for item in components
    ]
    return {
        "schema_version": 1,
        "evidence_basis": "Only licenses declared in checked-in package manifests/locks are reported. Unknown does not imply unlicensed.",
        "component_count": len(rendered),
        "known_license_count": sum(bool(item.licenses) for item in components),
        "unknown_license_count": sum(not item.licenses for item in components),
        "components": rendered,
    }


def _license_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Dependency license evidence",
        "",
        str(payload["evidence_basis"]),
        "",
        f"Components: **{payload['component_count']}**",
        f"Manifest-declared licenses: **{payload['known_license_count']}**",
        f"Unknown licenses requiring external resolution: **{payload['unknown_license_count']}**",
        "",
        "| Ecosystem | Package | Version | Scope | License evidence |",
        "|---|---|---|---|---|",
    ]
    components = payload.get("components")
    if not isinstance(components, list):
        raise TypeError("dependency license components must be a list")
    for item in components:
        if not isinstance(item, dict):
            raise TypeError("dependency license component entries must be objects")
        licenses = item["licenses"]
        license_text = (
            ", ".join(f"`{value}`" for value in licenses) if licenses else "unknown"
        )
        lines.append(
            f"| {item['ecosystem']} | `{item['name']}` | `{item['version']}` | {item['scope']} | {license_text} |"
        )
    return "\n".join(lines) + "\n"


def generate(root: Path, *, check: bool = False) -> list[str]:
    root = Path(root)
    components = build_components(root)
    sbom_text = json.dumps(_sbom(root, components), indent=2, sort_keys=True) + "\n"
    licenses = _license_report(components)
    license_json = json.dumps(licenses, indent=2, sort_keys=True) + "\n"
    targets = {
        root / "docs/generated/sbom.cdx.json": sbom_text,
        root / "docs/generated/dependency-licenses.json": license_json,
        root / "docs/generated/dependency-licenses.md": _license_markdown(licenses),
    }
    errors: list[str] = []
    for path, content in targets.items():
        if check:
            try:
                current = path.read_text(encoding="utf-8")
            except OSError:
                errors.append(
                    f"missing supply-chain evidence: {path.relative_to(root)}"
                )
            else:
                if current != content:
                    errors.append(
                        f"stale supply-chain evidence: {path.relative_to(root)}"
                    )
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    errors = generate(args.root, check=args.check)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "OK: supply-chain evidence is current"
        if args.check
        else "OK: supply-chain evidence generated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

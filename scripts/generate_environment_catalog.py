# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate an environment-variable catalog from executable declarations."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

SENSITIVE_MARKERS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PRIVATE_KEY",
    "API_KEY",
    "LICENSE_KEY",
    "STEGO_KEY",
)


@dataclass
class Variable:
    name: str
    declared_in_settings: bool = False
    type: str | None = None
    default: object | None = None
    required: bool = False
    sensitive: bool = False
    sources: set[str] = field(default_factory=set)

    def payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "declared_in_settings": self.declared_in_settings,
            "type": self.type,
            "default": None if self.sensitive else self.default,
            "required": self.required,
            "sensitive": self.sensitive,
            "sources": sorted(self.sources),
        }


def _is_sensitive(name: str) -> bool:
    upper = name.upper()
    return any(marker in upper for marker in SENSITIVE_MARKERS)


def _literal(node: ast.AST | None) -> object | None:
    if node is None:
        return None
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return "<computed>"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple, dict)):
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=False)
        return value if len(encoded) <= 200 else "<structured default>"
    return repr(value)


def _settings_variables(path: Path) -> dict[str, Variable]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    variables: dict[str, Variable] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "AppSettings":
            continue
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign) or not isinstance(
                statement.target, ast.Name
            ):
                continue
            name = statement.target.id
            if not name.isupper():
                continue
            type_name = ast.unparse(statement.annotation)
            default = _literal(statement.value)
            required = statement.value is None
            variable = Variable(
                name=name,
                declared_in_settings=True,
                type=type_name,
                default=default,
                required=required,
                sensitive=_is_sensitive(name),
                sources={f"{path.as_posix()}:{statement.lineno}"},
            )
            variables[name] = variable
    return variables


def _constant_string(node: ast.AST) -> str | None:
    return (
        node.value
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        else None
    )


def _direct_environment_references(paths: list[Path]) -> dict[str, set[str]]:
    references: dict[str, set[str]] = {}
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            name: str | None = None
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                owner = node.func.value
                if (
                    node.func.attr in {"get", "setdefault", "pop"}
                    and isinstance(owner, ast.Attribute)
                    and isinstance(owner.value, ast.Name)
                    and owner.value.id == "os"
                    and owner.attr == "environ"
                    and node.args
                ):
                    name = _constant_string(node.args[0])
                elif (
                    node.func.attr == "getenv"
                    and isinstance(owner, ast.Name)
                    and owner.id == "os"
                    and node.args
                ):
                    name = _constant_string(node.args[0])
            elif isinstance(node, ast.Subscript):
                owner = node.value
                if (
                    isinstance(owner, ast.Attribute)
                    and isinstance(owner.value, ast.Name)
                    and owner.value.id == "os"
                    and owner.attr == "environ"
                ):
                    name = _constant_string(node.slice)
            if name and isinstance(node, (ast.Call, ast.Subscript)):
                references.setdefault(name, set()).add(
                    f"{path.as_posix()}:{node.lineno}"
                )
    return references


def build_catalog(root: Path) -> dict[str, object]:
    root = Path(root)
    config_path = root / "src/configstream/config.py"
    variables = _settings_variables(
        config_path.relative_to(root) if False else config_path
    )
    # Convert absolute-looking source locations to repository-relative paths.
    for variable in variables.values():
        variable.sources = {
            str(Path(source.rsplit(":", 1)[0]).relative_to(root)).replace("\\", "/")
            + ":"
            + source.rsplit(":", 1)[1]
            for source in variable.sources
        }

    scan_paths = sorted(
        path
        for base in (root / "src", root / "scripts")
        if base.exists()
        for path in base.rglob("*.py")
        if "__pycache__" not in path.parts
    )
    direct = _direct_environment_references(scan_paths)
    for name, sources in direct.items():
        variable = variables.setdefault(
            name,
            Variable(name=name, sensitive=_is_sensitive(name)),
        )
        variable.sources.update(
            f"{path.relative_to(root).as_posix()}:{line}"
            for source in sources
            for path, line in [
                (Path(source.rsplit(":", 1)[0]), source.rsplit(":", 1)[1])
            ]
        )

    payloads = [variables[name].payload() for name in sorted(variables)]
    source_digest = hashlib.sha256(
        json.dumps(
            payloads,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": 1,
        "source_digest": source_digest,
        "variable_count": len(payloads),
        "variables": payloads,
    }


def render_markdown(payload: dict[str, object]) -> str:
    variables = payload.get("variables")
    if not isinstance(variables, list):
        raise TypeError("environment catalog variables must be a list")
    lines = [
        "# Environment variable catalog",
        "",
        "Generated from `AppSettings` and direct Python `os.environ`/`os.getenv` references.",
        "Sensitive defaults are never rendered.",
        "",
        f"Variables: **{payload['variable_count']}**",
        "",
        "| Variable | Settings field | Type | Default | Required | Sensitive | Sources |",
        "|---|---:|---|---|---:|---:|---|",
    ]
    for item in variables:
        if not isinstance(item, dict):
            raise TypeError("environment catalog variable entries must be objects")
        default = item["default"]
        if item["sensitive"]:
            default_text = "`<redacted>`"
        elif default is None:
            default_text = ""
        else:
            default_text = (
                f"`{json.dumps(default, ensure_ascii=False, sort_keys=True)}`"
            )
        sources = "<br>".join(f"`{source}`" for source in item["sources"])
        lines.append(
            "| `{name}` | {settings} | `{type}` | {default} | {required} | {sensitive} | {sources} |".format(
                name=item["name"],
                settings="yes" if item["declared_in_settings"] else "no",
                type=item["type"] or "direct-only",
                default=default_text,
                required="yes" if item["required"] else "no",
                sensitive="yes" if item["sensitive"] else "no",
                sources=sources,
            )
        )
    return "\n".join(lines) + "\n"


def generate(root: Path, *, check: bool = False) -> list[str]:
    root = Path(root)
    payload = build_catalog(root)
    json_text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    markdown = render_markdown(payload)
    output_dir = root / "docs/generated"
    targets = {
        output_dir / "environment-variables.json": json_text,
        output_dir / "environment-variables.md": markdown,
    }
    errors: list[str] = []
    for path, content in targets.items():
        if check:
            try:
                current = path.read_text(encoding="utf-8")
            except OSError:
                errors.append(f"missing generated catalog: {path.relative_to(root)}")
            else:
                if current != content:
                    errors.append(
                        f"generated catalog is stale: {path.relative_to(root)}"
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
        "OK: environment catalog is current"
        if args.check
        else "OK: environment catalog generated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

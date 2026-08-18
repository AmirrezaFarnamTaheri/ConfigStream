# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build the static architecture dashboard shell from its canonical template."""

from __future__ import annotations

from pathlib import Path

try:
    from scripts.generate_comprehensive_topology import load_topology
except ModuleNotFoundError:  # direct execution: python scripts/build_...py
    from generate_comprehensive_topology import load_topology  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY_PATH = ROOT / "system_topology.json"
TEMPLATE_PATH = ROOT / "assets" / "architecture.template.html"
OUTPUT_PATH = ROOT / "architecture.html"


def generate_architecture_html() -> None:
    """Validate topology data, then copy the canonical dashboard template."""
    load_topology(TOPOLOGY_PATH)
    if not TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f"Architecture template not found: {TEMPLATE_PATH}")

    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    required_refs = (
        "assets/architecture-dashboard.css",
        "assets/architecture-dashboard.js",
    )
    missing_refs = [ref for ref in required_refs if ref not in html]
    if missing_refs:
        raise ValueError(
            "Architecture template is missing required references: "
            + ", ".join(missing_refs)
        )

    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(
        f"Successfully compiled {OUTPUT_PATH.relative_to(ROOT)} "
        f"({len(html.splitlines())} lines, {len(html)} bytes)"
    )


if __name__ == "__main__":
    generate_architecture_html()

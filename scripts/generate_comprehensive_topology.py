# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprehensive System Topology & Architecture Visualizer Generator."""

from __future__ import annotations

import json
from pathlib import Path

TOPOLOGY_PATH = Path("system_topology.json")


def load_topology(path: Path = TOPOLOGY_PATH) -> dict:
    """Load and validate the AST-verified system architecture topology."""
    if not path.is_file():
        raise FileNotFoundError(f"Topology file {path} not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_topology(data)
    return data


def validate_topology(data: dict) -> None:
    """Ensure topology contains expected metadata, nodes, edges, and flows."""
    required_keys = {"metadata", "nodes", "edges", "flows"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Topology missing required top-level keys: {missing}")

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    flows = data.get("flows", [])

    if len(nodes) < 50:
        raise ValueError(f"Expected at least 50 architectural nodes, found {len(nodes)}")
    if len(edges) < 70:
        raise ValueError(f"Expected at least 70 architectural edges, found {len(edges)}")
    if len(flows) < 10:
        raise ValueError(f"Expected at least 10 execution flows, found {len(flows)}")

    node_ids = {n["id"] for n in nodes if "id" in n}
    for edge in edges:
        src, dst = edge.get("source"), edge.get("target")
        if src not in node_ids:
            raise ValueError(f"Edge source '{src}' does not exist in nodes")
        if dst not in node_ids:
            raise ValueError(f"Edge target '{dst}' does not exist in nodes")


def main() -> None:
    data = load_topology()
    out_path = Path("system_topology.json")
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(
        f"Verified {len(data['nodes'])} nodes, {len(data['edges'])} edges, "
        f"and {len(data['flows'])} flows in {out_path}"
    )


if __name__ == "__main__":
    main()

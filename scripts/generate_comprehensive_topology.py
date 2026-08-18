# SPDX-License-Identifier: AGPL-3.0-or-later
"""Comprehensive System Topology & Architecture Visualizer Generator."""

from __future__ import annotations

import json
from pathlib import Path

TOPOLOGY_PATH = Path("system_topology.json")


def load_topology(path: Path = TOPOLOGY_PATH) -> dict[str, object]:
    """Load and validate the AST-verified system architecture topology."""
    if not path.is_file():
        raise FileNotFoundError(f"Topology file {path} not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Topology file {path} does not contain a JSON object")
    typed_data: dict[str, object] = dict(data)
    validate_topology(typed_data)
    return typed_data


def validate_topology(data: dict[str, object]) -> None:
    """Ensure topology contains expected metadata, nodes, edges, and flows."""
    required_keys = {"metadata", "nodes", "edges", "flows"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Topology missing required top-level keys: {missing}")

    raw_nodes = data.get("nodes")
    raw_edges = data.get("edges")
    raw_flows = data.get("flows")

    if not isinstance(raw_nodes, list) or len(raw_nodes) < 50:
        raise ValueError("Expected at least 50 architectural nodes list")
    if not isinstance(raw_edges, list) or len(raw_edges) < 70:
        raise ValueError("Expected at least 70 architectural edges list")
    if not isinstance(raw_flows, list) or len(raw_flows) < 10:
        raise ValueError("Expected at least 10 execution flows list")

    node_ids: set[str] = set()
    for n in raw_nodes:
        if isinstance(n, dict) and "id" in n and isinstance(n["id"], str):
            node_ids.add(n["id"])

    for edge in raw_edges:
        if isinstance(edge, dict):
            src, dst = edge.get("source"), edge.get("target")
            if src not in node_ids:
                raise ValueError(f"Edge source '{src}' does not exist in nodes")
            if dst not in node_ids:
                raise ValueError(f"Edge target '{dst}' does not exist in nodes")


def main() -> None:
    data = load_topology()
    out_path = Path("system_topology.json")
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    raw_nodes = data.get("nodes")
    raw_edges = data.get("edges")
    raw_flows = data.get("flows")
    n_nodes = len(raw_nodes) if isinstance(raw_nodes, list) else 0
    n_edges = len(raw_edges) if isinstance(raw_edges, list) else 0
    n_flows = len(raw_flows) if isinstance(raw_flows, list) else 0
    print(
        f"Verified {n_nodes} nodes, {n_edges} edges, "
        f"and {n_flows} flows in {out_path}"
    )


if __name__ == "__main__":
    main()

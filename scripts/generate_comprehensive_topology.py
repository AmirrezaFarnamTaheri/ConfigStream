# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validate the comprehensive architecture topology and its executable flow graph."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY_PATH = ROOT / "system_topology.json"
ALLOWED_LAYERS = {
    "infrastructure",
    "presentation",
    "application",
    "domain",
    "persistence",
}


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


def _non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def validate_topology(data: dict[str, object]) -> None:
    """Validate node, edge, and flow schemas plus all graph references."""
    required_keys = {"metadata", "nodes", "edges", "flows"}
    missing = required_keys - set(data)
    if missing:
        raise ValueError(f"Topology missing required top-level keys: {sorted(missing)}")
    if not isinstance(data.get("metadata"), dict):
        raise ValueError("Topology metadata must be a JSON object")

    raw_nodes = data.get("nodes")
    raw_edges = data.get("edges")
    raw_flows = data.get("flows")

    if not isinstance(raw_nodes, list) or len(raw_nodes) < 50:
        raise ValueError("Expected at least 50 architectural nodes")
    if not isinstance(raw_edges, list) or len(raw_edges) < 70:
        raise ValueError("Expected at least 70 architectural edges")
    if not isinstance(raw_flows, list) or len(raw_flows) < 10:
        raise ValueError("Expected at least 10 execution flows")

    node_ids: set[str] = set()
    for index, node in enumerate(raw_nodes):
        if not isinstance(node, dict):
            raise ValueError(f"Node entry {index} is not a JSON object")
        node_id = _non_empty_string(node.get("id"), f"Node {index} id")
        if node_id in node_ids:
            raise ValueError(f"Duplicate node id: {node_id}")
        node_ids.add(node_id)
        _non_empty_string(node.get("name"), f"Node {node_id} name")
        layer = _non_empty_string(node.get("layer"), f"Node {node_id} layer")
        if layer not in ALLOWED_LAYERS:
            raise ValueError(f"Node {node_id} uses unknown layer: {layer}")

    edge_ids: set[str] = set()
    for index, edge in enumerate(raw_edges):
        if not isinstance(edge, dict):
            raise ValueError(f"Edge entry {index} is not a JSON object")
        edge_id = _non_empty_string(edge.get("id"), f"Edge {index} id")
        if edge_id in edge_ids:
            raise ValueError(f"Duplicate edge id: {edge_id}")
        edge_ids.add(edge_id)
        source = _non_empty_string(edge.get("source"), f"Edge {edge_id} source")
        target = _non_empty_string(edge.get("target"), f"Edge {edge_id} target")
        if source not in node_ids:
            raise ValueError(f"Edge source '{source}' does not exist in nodes")
        if target not in node_ids:
            raise ValueError(f"Edge target '{target}' does not exist in nodes")

    flow_ids: set[str] = set()
    for index, flow in enumerate(raw_flows):
        if not isinstance(flow, dict):
            raise ValueError(f"Flow entry {index} is not a JSON object")
        flow_id = _non_empty_string(flow.get("id"), f"Flow {index} id")
        if flow_id in flow_ids:
            raise ValueError(f"Duplicate flow id: {flow_id}")
        flow_ids.add(flow_id)
        _non_empty_string(flow.get("name"), f"Flow {flow_id} name")
        steps = flow.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError(f"Flow {flow_id} must contain a non-empty steps list")

        for expected_number, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                raise ValueError(
                    f"Flow {flow_id} step {expected_number} is not a JSON object"
                )
            if step.get("step_number") != expected_number:
                raise ValueError(
                    f"Flow {flow_id} step numbering must be contiguous from 1"
                )
            source = _non_empty_string(
                step.get("from"), f"Flow {flow_id} step {expected_number} from"
            )
            target = _non_empty_string(
                step.get("to"), f"Flow {flow_id} step {expected_number} to"
            )
            if source not in node_ids:
                raise ValueError(
                    f"Flow {flow_id} step {expected_number} source '{source}' does not exist"
                )
            if target not in node_ids:
                raise ValueError(
                    f"Flow {flow_id} step {expected_number} target '{target}' does not exist"
                )
            _non_empty_string(
                step.get("action"), f"Flow {flow_id} step {expected_number} action"
            )


def main() -> None:
    data = load_topology()
    nodes = data.get("nodes")
    edges = data.get("edges")
    flows = data.get("flows")
    if (
        not isinstance(nodes, list)
        or not isinstance(edges, list)
        or not isinstance(flows, list)
    ):
        raise RuntimeError("Validated topology lost its collection invariants")
    print(
        f"Verified {len(nodes)} nodes, {len(edges)} edges, "
        f"and {len(flows)} flows in {TOPOLOGY_PATH.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()

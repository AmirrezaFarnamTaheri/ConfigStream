# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.generate_comprehensive_topology import validate_topology


def _topology() -> dict[str, object]:
    payload = json.loads(Path("system_topology.json").read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_repository_topology_is_valid() -> None:
    validate_topology(_topology())


def test_duplicate_node_id_is_rejected() -> None:
    data = copy.deepcopy(_topology())
    nodes = data["nodes"]
    assert isinstance(nodes, list)
    assert isinstance(nodes[0], dict)
    assert isinstance(nodes[1], dict)
    nodes[1]["id"] = nodes[0]["id"]

    with pytest.raises(ValueError, match="Duplicate node id"):
        validate_topology(data)


def test_malformed_edge_is_rejected() -> None:
    data = copy.deepcopy(_topology())
    edges = data["edges"]
    assert isinstance(edges, list)
    edges[0] = "not-an-edge"

    with pytest.raises(ValueError, match="not a JSON object"):
        validate_topology(data)


def test_flow_step_dangling_node_is_rejected() -> None:
    data = copy.deepcopy(_topology())
    flows = data["flows"]
    assert isinstance(flows, list)
    assert isinstance(flows[0], dict)
    steps = flows[0]["steps"]
    assert isinstance(steps, list)
    assert isinstance(steps[0], dict)
    steps[0]["to"] = "missing-node"

    with pytest.raises(ValueError, match="target 'missing-node' does not exist"):
        validate_topology(data)


def test_non_contiguous_flow_step_numbers_are_rejected() -> None:
    data = copy.deepcopy(_topology())
    flows = data["flows"]
    assert isinstance(flows, list)
    assert isinstance(flows[0], dict)
    steps = flows[0]["steps"]
    assert isinstance(steps, list)
    assert isinstance(steps[0], dict)
    steps[0]["step_number"] = 99

    with pytest.raises(ValueError, match="step numbering must be contiguous"):
        validate_topology(data)

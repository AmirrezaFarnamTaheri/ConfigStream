#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""RepoTopology — Zero-dependency repository topology engine v7.0.0-self-sufficient.

Generates dependency graphs, audits, diffs, and lease management artifacts
using only the Python standard library. Intended for architectural reasoning,
blast-radius analysis, and swarm-aware concurrent code mutation.

Usage:
    python3 scripts/repo_topology.py build <path>
    python3 scripts/repo_topology.py audit <path> <target>
    python3 scripts/repo_topology.py threshold <path>
    python3 scripts/repo_topology.py query <path> <target>
    python3 scripts/repo_topology.py blast <path> <target>
    python3 scripts/repo_topology.py trace <path> [--from-type TYPE] --to <target>
    python3 scripts/repo_topology.py diff <path>
    python3 scripts/repo_topology.py reflect <path> --session-summary "..."
    python3 scripts/repo_topology.py lease <path> acquire|release --cluster ID --owner ID [--target NODE]
"""

from __future__ import annotations
import logging

import argparse
import json
import os
import re
import shutil
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OUT_DIR = "repo-topology-out"

# Protection vocabulary for taint analysis
PROTECTION_VOCABULARY = {
    "auth", "authenticate", "authorize", "authorization", "guard", "middleware",
    "sanitize", "validate", "validator", "schema", "permission", "acl", "csrf",
    "rate-limit", "escape", "parameterize", "allowlist", "normalize", "tenant",
    "ownership", "scope", "jail", "safe",
}

# Sink patterns for security taint analysis
SINK_PATTERNS = {
    "sql": re.compile(r"(execute|executemany|raw_query|session\.execute)", re.I),
    "filesystem": re.compile(r"(open\(|write\(|read\(|shutil\.|pathlib\.)", re.I),
    "subprocess": re.compile(r"(subprocess\.|os\.system|os\.popen|sh\.)", re.I),
    "deserialize": re.compile(r"(pickle\.load|json\.loads|yaml\.load\b|eval\()", re.I),
}


# ---------------------------------------------------------------------------
# Path Normalization
# ---------------------------------------------------------------------------
def normalize_path(value: Any) -> str:
    if not value:
        return ""
    value = str(value).replace("\\", "/")
    # Strip drive letters (Windows)
    if len(value) >= 2 and value[1] == ":":
        value = value[2:]
    while value.startswith("./"):
        value = value[2:]
    value = value.lstrip("/")
    while "//" in value:
        value = value.replace("//", "/")
    if not value.startswith("repo://"):
        value = "repo://" + value
    return value


def detect_workspace_roots(repo_path: Path) -> list[Path]:
    """Detect workspace roots from common markers."""
    markers = [
        "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
        "pom.xml", "build.gradle", "setup.py", "Makefile",
    ]
    roots = []
    for marker in markers:
        path = repo_path / marker
        if path.exists():
            roots.append(repo_path)
            break
    # Check for monorepo workspaces
    for sub in repo_path.iterdir():
        if sub.is_dir():
            for marker in markers:
                if (sub / marker).exists():
                    roots.append(sub)
                    break
    return roots if roots else [repo_path]


# ---------------------------------------------------------------------------
# File Discovery
# ---------------------------------------------------------------------------
def discover_files(repo_path: Path, exclude_dirs: set[str] | None = None) -> list[Path]:
    """Discover all source files in the repository."""
    if exclude_dirs is None:
        exclude_dirs = {
            ".git", "node_modules", "venv", ".venv", "__pycache__",
            "build", "dist", ".mypy_cache", ".pytest_cache", ".hypothesis",
            "frontend-dist", ".github", "repo-topology-out",
        }
    files = []
    for root, dirs, filenames in os.walk(repo_path):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
        for f in filenames:
            path = Path(root) / f
            # Skip binary and large files
            if f.endswith((".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe")):
                continue
            if path.stat().st_size > 500_000:  # Skip files > 500KB
                continue
            files.append(path)
    return files


LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".rs": "rust",
    ".go": "golang",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp",
    ".php": "php",
    ".rb": "ruby",
    ".swift": "swift",
    ".scala": "scala",
    ".mjs": "javascript", ".cjs": "javascript",
    ".html": "html", ".css": "css", ".scss": "scss",
    ".yaml": "yaml", ".yml": "yaml", ".json": "json", ".toml": "toml",
    ".md": "markdown", ".rst": "rst",
}


def file_language(path: Path) -> str:
    return LANGUAGE_EXTENSIONS.get(path.suffix.lower(), "unknown")


# ---------------------------------------------------------------------------
# Python Import Parsing (ast-based)
# ---------------------------------------------------------------------------
def parse_python_imports(content: str) -> list[str]:
    """Extract import statements from Python source using ast."""
    imports = []
    try:
        import ast
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                    for alias in node.names:
                        imports.append(f"{node.module}.{alias.name}")
    except SyntaxError:
        pass
    return imports


# ---------------------------------------------------------------------------
# Generic Import Parsing (regex-based)
# ---------------------------------------------------------------------------
IMPORT_PATTERNS: dict[str, list[re.Pattern]] = {
    "javascript": [
        re.compile(r'(?:import\s+(?:(?:\{[^}]*\}|[^;{]+)\s+from\s+)?["\']([^"\']+)["\'])'),
        re.compile(r'(?:require\(["\']([^"\']+)["\']\))'),
    ],
    "typescript": [
        re.compile(r'(?:import\s+(?:(?:\{[^}]*\}|[^;{]+)\s+from\s+)?["\']([^"\']+)["\'])'),
        re.compile(r'(?:require\(["\']([^"\']+)["\']\))'),
    ],
    "rust": [
        re.compile(r'^use\s+([^;]+);', re.MULTILINE),
        re.compile(r'^extern\s+crate\s+(\w+);', re.MULTILINE),
    ],
    "golang": [
        re.compile(r'"(?:[^"]*\/)?([^"/]+)"'),
    ],
    "java": [
        re.compile(r'^import\s+(?:static\s+)?([\w.]+);', re.MULTILINE),
    ],
}


def parse_imports(content: str, language: str) -> list[str]:
    """Parse imports from source content based on language."""
    if language == "python":
        return parse_python_imports(content)
    imports = []
    patterns = IMPORT_PATTERNS.get(language, [])
    for pat in patterns:
        imports.extend(pat.findall(content))
    return imports


# ---------------------------------------------------------------------------
# Tagging: Entry Points, Config, Tests, Sinks
# ---------------------------------------------------------------------------
def tag_node(path: Path, language: str, content: str) -> set[str]:
    """Tag a file based on its path, name, and content."""
    tags: set[str] = set()
    name = path.name
    str_path = str(path.as_posix())

    # Entry points
    if name == "main.py" or name == "__main__.py" or name == "cli.py":
        tags.add("entry_point")
    if name == "main.go" or name == "main.rs":
        tags.add("entry_point")
    if re.search(r'(if\s+__name__\s*==\s*["\']__main__["\'])', content):
        tags.add("entry_point")

    # Tests
    if "test_" in name or name.endswith("_test.py") or name.endswith("_test.go"):
        tags.add("test")
    if str_path.startswith("tests/") or "/tests/" in str_path:
        tags.add("test")

    # Configuration
    if name in ("package.json", "pyproject.toml", "Cargo.toml", "go.mod",
                "Dockerfile", "docker-compose.yml", ".gitignore", "Makefile"):
        tags.add("configuration")

    # Migrations
    if "migration" in str_path.lower() or "migrate" in str_path.lower():
        tags.add("migration")

    # Sink detection
    for sink_type, pattern in SINK_PATTERNS.items():
        if pattern.search(content):
            tags.add(f"sink:{sink_type}")

    # Protection vocabulary
    for word in PROTECTION_VOCABULARY:
        if re.search(rf'\b{re.escape(word)}\b', content, re.I):
            tags.add(f"protect:{word}")

    return tags


# ---------------------------------------------------------------------------
# Graph Building
# ---------------------------------------------------------------------------
def build_graph(repo_path: Path) -> dict[str, Any]:
    """Build the complete topology graph from repository files."""
    files = discover_files(repo_path)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    file_to_rel: dict[str, str] = {}
    node_map: dict[str, dict[str, Any]] = {}

    for fpath in files:
        rel_path = fpath.relative_to(repo_path).as_posix()
        norm_path = normalize_path(rel_path)
        lang = file_language(fpath)
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            logging.getLogger(__name__).debug("Suppressed broad exception", exc_info=True)
            content = ""

        tags = tag_node(fpath, lang, content)
        imports = parse_imports(content, lang)
        complexity = _estimate_complexity(content)

        node: dict[str, Any] = {
            "id": norm_path,
            "path": rel_path,
            "name": fpath.name,
            "type": lang,
            "language": lang,
            "tags": list(tags),
            "lines": len(content.splitlines()) if content else 0,
            "cyclomatic_complexity": complexity,
            "centrality": 0.0,  # Will be calculated later
            "imports": imports,
            "file_size": fpath.stat().st_size,
        }
        nodes.append(node)
        node_map[norm_path] = node
        file_to_rel[rel_path] = norm_path

    # Build edges from imports
    for node in nodes:
        source = node["id"]
        for imp in node.get("imports", []):
            # Try to resolve the import to a local file
            target = _resolve_import(imp, file_to_rel)
            if target and target != source:
                edges.append({
                    "source": source,
                    "target": target,
                    "type": "import",
                })

    # Add edges from package.json scripts
    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        _add_package_json_edges(pkg_json, file_to_rel, edges)

    # Calculate centrality (in-degree / out-degree based)
    in_degree: dict[str, int] = defaultdict(int)
    out_degree: dict[str, int] = defaultdict(int)
    for edge in edges:
        in_degree[edge["target"]] += 1
        out_degree[edge["source"]] += 1

    total_nodes = len(nodes)
    for node in nodes:
        nid = node["id"]
        deg = in_degree.get(nid, 0) + out_degree.get(nid, 0)
        node["centrality"] = deg / max(total_nodes, 1)
        node["in_degree"] = in_degree.get(nid, 0)
        node["out_degree"] = out_degree.get(nid, 0)

    # Clustering (connected components)
    clusters = _compute_clusters(nodes, edges)
    for node in nodes:
        nid = node["id"]
        node["cluster_id"] = clusters.get(nid, "cluster-000")

    # Density
    max_edges = total_nodes * (total_nodes - 1)
    density = len(edges) / max(max_edges, 1)

    graph: dict[str, Any] = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "density": round(density, 6),
            "workspace_roots": [str(p) for p in detect_workspace_roots(repo_path)],
            "excluded_dirs": list(exclude_dirs_default()),
        },
        "nodes": nodes,
        "edges": edges,
    }
    return graph


def exclude_dirs_default() -> set[str]:
    return {
        ".git", "node_modules", "venv", ".venv", "__pycache__",
        "build", "dist", ".mypy_cache", ".pytest_cache", ".hypothesis",
        "frontend-dist", ".github", "repo-topology-out",
    }


def _estimate_complexity(content: str) -> int:
    """Estimate cyclomatic complexity from source content."""
    complexity = 1
    # Count decision points (excluding 'else' which pairs with 'if')
    for pattern in [r'\bif\b', r'\belif\b', r'\bfor\b', r'\bwhile\b',
                    r'\bcase\b', r'\bcatch\b', r'\bexcept\b', r'\bwith\b',
                    r'\band\b', r'\bor\b', r'\bnot\b', r'\?', r'\|\|', r'&&']:
        complexity += len(re.findall(pattern, content))
    return complexity


def _resolve_import(imp: str, file_to_rel: dict[str, str]) -> Optional[str]:
    """Resolve an import string to a normalized file path.
    Handles Python (.py), JavaScript/TypeScript (.js/.ts), Go (.go),
    and Rust (.rs) file extensions.
    """
    # Normalize the import path (dotted to slash)
    imp_path_base = imp.replace(".", "/")
    
    # Try common source extensions
    for ext in [".py", "/__init__.py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs"]:
        test_path = imp_path_base + ext
        if test_path in file_to_rel:
            return normalize_path(file_to_rel[test_path])
    
    return None


def _add_package_json_edges(pkg_path: Path, file_to_rel: dict[str, str], edges: list[dict[str, Any]]) -> None:
    """Add edges from package.json script references."""
    try:
        data = json.loads(pkg_path.read_text())
        pkg_rel = pkg_path.name
        pkg_norm = normalize_path(pkg_rel)
        scripts = data.get("scripts", {})
        for _name, cmd in scripts.items():
            if isinstance(cmd, str):
                # Look for file references in commands
                for part in cmd.split():
                    if part in file_to_rel:
                        target = normalize_path(file_to_rel[part])
                        edges.append({
                            "source": pkg_norm,
                            "target": target,
                            "type": "script_ref",
                        })
    except (json.JSONDecodeError, OSError):
        pass


def _compute_clusters(nodes: list[dict], edges: list[dict]) -> dict[str, str]:
    """Compute connected components (clusters) using BFS."""
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        s = edge.get("source", "")
        t = edge.get("target", "")
        if s and t:
            adj[s].append(t)
            adj[t].append(s)

    all_nodes = {n["id"] for n in nodes}
    cluster_map: dict[str, str] = {}
    cluster_id = 0

    for nid in all_nodes:
        if nid in cluster_map:
            continue
        cluster_id += 1
        cid = f"cluster-{cluster_id:03d}"
        queue = [nid]
        while queue:
            current = queue.pop(0)
            if current in cluster_map:
                continue
            cluster_map[current] = cid
            for neighbor in adj.get(current, []):
                if neighbor not in cluster_map:
                    queue.append(neighbor)

    # Assign unconnected nodes to their own clusters
    for nid in all_nodes:
        if nid not in cluster_map:
            cluster_id += 1
            cluster_map[nid] = f"cluster-{cluster_id:03d}"

    return cluster_map


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
def run_audit(graph: dict[str, Any], target: str = "") -> list[dict[str, Any]]:
    """Run structural audit on the graph."""
    findings: list[dict[str, Any]] = []
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_map = {n["id"]: n for n in nodes}

    target_norm = normalize_path(target) if target else ""

    # Orphan detection (sweep 1)
    targets = {e.get("target", "") for e in edges}
    for node in nodes:
        nid = node["id"]
        if target_norm and target_norm not in nid:
            continue
        if nid not in targets:
            tags = set(node.get("tags", []))
            if not any(t in tags for t in ["entry_point", "test", "configuration", "migration"]):
                findings.append({
                    "id": f"AUDIT-{len(findings)+1:03d}",
                    "type": "orphan_node",
                    "node_path": nid,
                    "risk": "Low",
                    "confidence": "Medium",
                    "evidence": "Graph",
                    "action": "Review for dead code (zero incoming edges)",
                })

    # God node detection (sweep 3)
    values = [n.get("centrality", 0) for n in nodes if n.get("centrality", 0) > 0]
    threshold = _compute_threshold(values, graph.get("metadata", {}).get("density", 0.02))

    for node in nodes:
        nid = node["id"]
        if target_norm and target_norm not in nid:
            continue
        cent = node.get("centrality", 0)
        comp = node.get("cyclomatic_complexity", 0)
        if cent >= threshold and comp > 15:
            findings.append({
                "id": f"AUDIT-{len(findings)+1:03d}",
                "type": "god_node",
                "node_path": nid,
                "risk": "High",
                "confidence": "High",
                "evidence": "Graph",
                "action": f"Refactor: centrality={cent:.3f}, complexity={comp}",
            })

    # Cross-cluster cycles (sweep 2)
    edge_pairs = {(e.get("source"), e.get("target")) for e in edges}
    for src, tgt in edge_pairs:
        if not src or not tgt:
            continue
        if (tgt, src) in edge_pairs:
            src_cluster = node_map.get(src, {}).get("cluster_id")
            tgt_cluster = node_map.get(tgt, {}).get("cluster_id")
            if src_cluster and tgt_cluster and src_cluster != tgt_cluster:
                findings.append({
                    "id": f"AUDIT-{len(findings)+1:03d}",
                    "type": "cross_cluster_cycle",
                    "node_path": f"{src} <-> {tgt}",
                    "risk": "High",
                    "confidence": "High",
                    "evidence": "Graph",
                    "action": "Design abstraction boundary between clusters",
                })

    # Sink taint analysis
    for node in nodes:
        nid = node["id"]
        if target_norm and target_norm not in nid:
            continue
        tags = node.get("tags", [])
        sinks = [t for t in tags if t.startswith("sink:")]
        has_protection = any(t.startswith("protect:") for t in tags)
        if sinks and not has_protection:
            findings.append({
                "id": f"AUDIT-{len(findings)+1:03d}",
                "type": "unprotected_sink",
                "node_path": nid,
                "risk": "Critical",
                "confidence": "Medium",
                "evidence": "Source",
                "action": f"Add protection vocabulary to sink ({', '.join(sinks)})",
            })

    return findings


def _compute_threshold(values: list[float], density: float) -> float:
    """Compute dynamic centrality threshold."""
    if len(values) >= 2:
        return statistics.mean(values) + 1.5 * statistics.stdev(values)
    if density > 0.10:
        return 0.85
    elif density >= 0.02:
        return 0.70
    return 0.45


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------
def query_nodes(graph: dict[str, Any], target: str) -> list[dict[str, Any]]:
    """Query graph for nodes matching target."""
    target_norm = normalize_path(target)
    results = []
    for node in graph.get("nodes", []):
        nid = node.get("id", "")
        if target_norm in nid or target in nid or target_norm.replace("repo://", "") in nid:
            results.append(node)
    return results


# ---------------------------------------------------------------------------
# Blast Radius
# ---------------------------------------------------------------------------
def blast_radius(graph: dict[str, Any], target: str) -> dict[str, Any]:
    """Compute blast radius for a target node."""
    target_norm = normalize_path(target)
    upstream = []
    downstream = []

    for edge in graph.get("edges", []):
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        if target_norm in tgt or target_norm.replace("repo://", "") in tgt:
            upstream.append(src)
        if target_norm in src or target_norm.replace("repo://", "") in src:
            downstream.append(tgt)

    return {
        "upstream_breakage": list(set(upstream)),
        "downstream_cascade": list(set(downstream)),
        "incoming_count": len(set(upstream)),
        "outgoing_count": len(set(downstream)),
    }


# ---------------------------------------------------------------------------
# Trace (entry points to sink paths)
# ---------------------------------------------------------------------------
def trace_paths(graph: dict[str, Any], target: str, from_type: str = "entry_point") -> list[dict[str, Any]]:
    """Trace paths from entry points to a target sink node."""
    target_norm = normalize_path(target)
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # Build adjacency list
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adj[edge.get("source", "")].append(edge.get("target", ""))

    # Find entry points
    entry_points = [
        n["id"] for n in nodes
        if from_type in n.get("tags", []) or n.get("name") in ("main.py", "cli.py", "main.go")
    ]

    # BFS from each entry point to find paths to target
    paths = []
    for ep in entry_points:
        visited = set()
        queue = [(ep, [ep])]
        while queue:
            current, path = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if target_norm in current:
                paths.append({"entry": ep, "path": path, "target": current})
                continue
            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

    return paths


# ---------------------------------------------------------------------------
# Graph Diff
# ---------------------------------------------------------------------------
def compute_diff(graph_path: Path) -> dict[str, Any]:
    """Compute diff between current graph and previous version."""
    current_path = graph_path
    prev_path = graph_path.parent / "graph.json.prev"

    if not current_path.exists():
        return {"error": "No current graph found"}

    with open(current_path) as f:
        current = json.load(f)

    if not prev_path.exists():
        # First run — save current as prev and return empty diff
        shutil.copy2(current_path, prev_path)
        return {"status": "first_run", "node_count": len(current.get("nodes", []))}

    with open(prev_path) as f:
        previous = json.load(f)

    current_ids = {n["id"] for n in current.get("nodes", [])}
    prev_ids = {n["id"] for n in previous.get("nodes", [])}

    added = current_ids - prev_ids
    removed = prev_ids - current_ids

    current_edges = {(e["source"], e["target"]) for e in current.get("edges", [])}
    prev_edges = {(e["source"], e["target"]) for e in previous.get("edges", [])}

    edges_added = current_edges - prev_edges
    edges_removed = prev_edges - current_edges

    diff = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nodes_added": len(added),
        "nodes_removed": len(removed),
        "edges_added": len(edges_added),
        "edges_removed": len(edges_removed),
        "added_nodes": sorted(list(added))[:50],
        "removed_nodes": sorted(list(removed))[:50],
        "added_edges": [list(e) for e in list(edges_added)[:50]],
        "removed_edges": [list(e) for e in list(edges_removed)[:50]],
    }

    # Save current as prev for next diff
    shutil.copy2(current_path, prev_path)
    return diff


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------
def generate_report(graph: dict[str, Any], audit: list[dict[str, Any]]) -> str:
    """Generate human-readable GRAPH_REPORT.md."""
    lines = []
    meta = graph.get("metadata", {})
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    lines.append("# RepoTopology Report")
    lines.append(f"Generated: {meta.get('generated_at', 'unknown')}")
    lines.append(f"Nodes: {meta.get('node_count', 0)} | Edges: {meta.get('edge_count', 0)} | Density: {meta.get('density', 0):.4f}")
    lines.append("")

    # Clusters
    clusters: dict[str, list[dict]] = defaultdict(list)
    for node in nodes:
        cid = node.get("cluster_id", "unknown")
        clusters[cid].append(node)

    lines.append("## Clusters")
    for cid in sorted(clusters.keys()):
        cluster_nodes = clusters[cid]
        lines.append(f"### {cid} ({len(cluster_nodes)} nodes)")
        for n in sorted(cluster_nodes, key=lambda x: x.get("centrality", 0), reverse=True)[:5]:
            lines.append(f"- {n['id']} (centrality: {n.get('centrality', 0):.3f}, complexity: {n.get('cyclomatic_complexity', 0)})")
    lines.append("")

    # Centrality threshold
    values = [n.get("centrality", 0) for n in nodes if n.get("centrality", 0) > 0]
    threshold = _compute_threshold(values, meta.get("density", 0.02))
    lines.append(f"## Centrality Threshold: T = {threshold:.4f}")
    lines.append("")

    # Top nodes by centrality
    lines.append("## Top 15 Nodes by Centrality")
    sorted_nodes = sorted(nodes, key=lambda x: x.get("centrality", 0), reverse=True)[:15]
    for n in sorted_nodes:
        lines.append(f"- {n['id']}: centrality={n.get('centrality', 0):.3f}, complexity={n.get('cyclomatic_complexity', 0)}, cluster={n.get('cluster_id', '')}")
    lines.append("")

    # Audit findings
    lines.append(f"## Audit Findings ({len(audit)})")
    for finding in audit:
        lines.append(f"- [{finding.get('risk', '?')}] {finding.get('type', '?')}: {finding.get('node_path', '?')}")
        lines.append(f"  - {finding.get('action', '')} (confidence: {finding.get('confidence', '?')})")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Lease Management
# ---------------------------------------------------------------------------
LEASE_FILE = Path(OUT_DIR) / ".leases.json"
LEASE_LOCK = Path(OUT_DIR) / ".leases.json.lock"


def _lease_mutex_acquire(max_retries: int = 10, wait_ms: int = 500) -> bool:
    """Acquire lease-file mutex."""
    for _ in range(max_retries):
        try:
            LEASE_LOCK.touch(exist_ok=False)
            return True
        except FileExistsError:
            time.sleep(wait_ms / 1000)
    return False


def _lease_mutex_release() -> None:
    """Release lease-file mutex."""
    try:
        LEASE_LOCK.unlink()
    except FileNotFoundError:
        pass


def lease_acquire(cluster: str, owner: str, target: str = "") -> dict[str, Any]:
    """Acquire a lease on a cluster."""
    if not _lease_mutex_acquire():
        return {"status": "error", "message": "Could not acquire mutex"}
    try:
        Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
        leases: dict[str, Any] = {"clusters": {}}
        if LEASE_FILE.exists():
            leases = json.loads(LEASE_FILE.read_text())

        if cluster in leases.get("clusters", {}):
            existing = leases["clusters"][cluster]
            if existing.get("status") == "active":
                _lease_mutex_release()
                return {"status": "blocked", "message": f"Cluster {cluster} is actively leased by {existing.get('owner')}"}

        leases.setdefault("clusters", {})[cluster] = {
            "owner": owner,
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "target": target,
            "status": "active",
        }
        # Atomic write
        tmp = LEASE_FILE.with_suffix(".tmp.json")
        tmp.write_text(json.dumps(leases, indent=2))
        tmp.replace(LEASE_FILE)
        return {"status": "acquired", "cluster": cluster, "owner": owner}
    finally:
        _lease_mutex_release()


def lease_release(cluster: str, owner: str) -> dict[str, Any]:
    """Release a lease on a cluster."""
    if not _lease_mutex_acquire():
        return {"status": "error", "message": "Could not acquire mutex"}
    try:
        if not LEASE_FILE.exists():
            return {"status": "error", "message": "No lease file found"}
        leases = json.loads(LEASE_FILE.read_text())
        if cluster in leases.get("clusters", {}):
            leases["clusters"][cluster]["status"] = "released"
            leases["clusters"][cluster]["released_at"] = datetime.now(timezone.utc).isoformat()
        tmp = LEASE_FILE.with_suffix(".tmp.json")
        tmp.write_text(json.dumps(leases, indent=2))
        tmp.replace(LEASE_FILE)
        return {"status": "released", "cluster": cluster}
    finally:
        _lease_mutex_release()


# ---------------------------------------------------------------------------
# Reflect (Persist Lessons)
# ---------------------------------------------------------------------------
def reflect(lesson: str) -> None:
    """Append a lesson to LESSONS.md."""
    lessons_path = Path(OUT_DIR) / "LESSONS.md"
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

    entry = (
        f"\n### [{datetime.now(timezone.utc).isoformat()}] Lesson\n"
        f"* **Summary:** {lesson}\n"
        f"* **Confidence:** High\n"
    )
    if lessons_path.exists():
        lessons_path.write_text(lessons_path.read_text() + entry)
    else:
        lessons_path.write_text("# RepoTopology Lessons\n" + entry)
    print(f"Lesson recorded: {lesson}")


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="RepoTopology — Zero-dependency repository topology engine")
    subparsers = parser.add_subparsers(dest="command")

    # build
    build_p = subparsers.add_parser("build", help="Build topology graph")
    build_p.add_argument("path", help="Repository path")

    # audit
    audit_p = subparsers.add_parser("audit", help="Run structural audit")
    audit_p.add_argument("path", help="Repository path")
    audit_p.add_argument("target", nargs="?", default="", help="Target node filter")

    # threshold
    thr_p = subparsers.add_parser("threshold", help="Compute centrality threshold")
    thr_p.add_argument("path", help="Repository path")

    # query
    q_p = subparsers.add_parser("query", help="Query graph nodes")
    q_p.add_argument("path", help="Repository path")
    q_p.add_argument("target", help="Target to search for")

    # blast
    b_p = subparsers.add_parser("blast", help="Compute blast radius")
    b_p.add_argument("path", help="Repository path")
    b_p.add_argument("target", help="Target node")

    # trace
    t_p = subparsers.add_parser("trace", help="Trace entry-to-sink paths")
    t_p.add_argument("path", help="Repository path")
    t_p.add_argument("--from-type", default="entry_point", help="Entry point type")
    t_p.add_argument("--to", required=True, help="Target sink node")

    # diff
    d_p = subparsers.add_parser("diff", help="Compute graph diff")
    d_p.add_argument("path", help="Repository path")

    # reflect
    r_p = subparsers.add_parser("reflect", help="Record a lesson")
    r_p.add_argument("path", help="Repository path")
    r_p.add_argument("--session-summary", required=True, help="Lesson text")

    # lease
    l_p = subparsers.add_parser("lease", help="Manage cluster leases")
    l_p.add_argument("path", help="Repository path")
    l_p.add_argument("action", choices=["acquire", "release"])
    l_p.add_argument("--cluster", required=True)
    l_p.add_argument("--owner", required=True)
    l_p.add_argument("--target", default="")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    repo_path = Path(args.path).resolve()
    if not repo_path.exists():
        print(f"ERROR: path not found: {repo_path}")
        return 1

    out_dir = repo_path / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.command == "build":
        print(f"Building topology for {repo_path}...")
        graph = build_graph(repo_path)
        # Write graph.json
        (out_dir / "graph.json").write_text(json.dumps(graph, indent=2))
        print(f"  Nodes: {graph['metadata']['node_count']}")
        print(f"  Edges: {graph['metadata']['edge_count']}")
        print(f"  Clusters: {len(set(n.get('cluster_id','') for n in graph['nodes']))}")
        # Run audit
        findings = run_audit(graph)
        (out_dir / "audit.json").write_text(json.dumps(findings, indent=2))
        print(f"  Audit findings: {len(findings)}")
        # Generate report
        report = generate_report(graph, findings)
        (out_dir / "GRAPH_REPORT.md").write_text(report)
        print(f"  Report: {out_dir}/GRAPH_REPORT.md")
        print("Build complete.")

    elif args.command == "audit":
        graph_path = out_dir / "graph.json"
        if not graph_path.exists():
            print("ERROR: run 'build' first")
            return 1
        graph = json.loads(graph_path.read_text())
        findings = run_audit(graph, args.target)
        print(json.dumps(findings, indent=2))

    elif args.command == "threshold":
        graph_path = out_dir / "graph.json"
        if not graph_path.exists():
            print("ERROR: run 'build' first")
            return 1
        graph = json.loads(graph_path.read_text())
        values = [n.get("centrality", 0) for n in graph.get("nodes", []) if n.get("centrality", 0) > 0]
        threshold = _compute_threshold(values, graph.get("metadata", {}).get("density", 0.02))
        result = {
            "threshold": round(threshold, 4),
            "density": graph.get("metadata", {}).get("density", 0),
            "node_count": len(graph.get("nodes", [])),
        }
        print(json.dumps(result, indent=2))

    elif args.command == "query":
        graph_path = out_dir / "graph.json"
        if not graph_path.exists():
            print("ERROR: run 'build' first")
            return 1
        graph = json.loads(graph_path.read_text())
        results = query_nodes(graph, args.target)
        print(json.dumps(results, indent=2) if results else "No matches found.")

    elif args.command == "blast":
        graph_path = out_dir / "graph.json"
        if not graph_path.exists():
            print("ERROR: run 'build' first")
            return 1
        graph = json.loads(graph_path.read_text())
        result = blast_radius(graph, args.target)
        print(json.dumps(result, indent=2))

    elif args.command == "trace":
        graph_path = out_dir / "graph.json"
        if not graph_path.exists():
            print("ERROR: run 'build' first")
            return 1
        graph = json.loads(graph_path.read_text())
        paths = trace_paths(graph, args.to, args.from_type)
        print(json.dumps(paths, indent=2) if paths else "No paths found.")

    elif args.command == "diff":
        graph_path = out_dir / "graph.json"
        if not graph_path.exists():
            print("ERROR: run 'build' first")
            return 1
        diff = compute_diff(graph_path)
        report_path = out_dir / "graph_diff.json"
        report_path.write_text(json.dumps(diff, indent=2))
        print(f"Diff written to {report_path}")
        print(json.dumps(diff, indent=2))

    elif args.command == "reflect":
        reflect(args.session_summary)

    elif args.command == "lease":
        if args.action == "acquire":
            result = lease_acquire(args.cluster, args.owner, args.target)
        else:
            result = lease_release(args.cluster, args.owner)
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())

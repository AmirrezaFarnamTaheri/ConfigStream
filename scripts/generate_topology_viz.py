#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate an interactive D3.js force-directed graph from repo-topology-out/graph.json."""

import json
from pathlib import Path

GRAPH_FILE = Path("repo-topology-out/graph.json")
OUTPUT_FILE = Path("repo-topology-out/graph.html")

data = json.loads(GRAPH_FILE.read_text())

# Filter: nodes with edges OR top centrality (top 60 by edges+centrality)
node_map = {}
for n in data.get("nodes", []):
    nid = n.get("id", "")
    node_map[nid] = n

edges = data.get("edges", [])


def _norm(p):
    # Normalize all repo:// variants: repo://repo:/ -> repo://
    if p.startswith("repo://"):
        p = p.removeprefix("repo://")
        p = p.removeprefix("repo:")
        p = p.removeprefix("/")
        return "repo://" + p
    return p


connected_ids = set()
for e in edges:
    src = e.get("source", "")
    tgt = e.get("target", "")
    for raw in [src, tgt]:
        connected_ids.add(_norm(raw))

# Get centrality-ranked nodes beyond connected ones
all_nodes_sorted = sorted(
    data.get("nodes", []),
    key=lambda n: n.get("centrality", 0)
    * (n.get("out_degree", 0) + n.get("in_degree", 0) + 1),
    reverse=True,
)

# Include all connected nodes + top 50 by metric
vis_ids = set(connected_ids)
for n in all_nodes_sorted:
    nid = n.get("id", "")
    if nid not in vis_ids:
        vis_ids.add(nid)
    if len(vis_ids) >= 200:
        break

# Build visualization nodes
vis_nodes = []
for nid in vis_ids:
    n = node_map.get(nid)
    if not n:
        continue
    vis_nodes.append(
        {
            "id": nid,
            "label": n.get("name", nid.split("/")[-1]),
            "path": nid.replace("repo://", ""),
            "centrality": n.get("centrality", 0),
            "complexity": n.get("cyclomatic_complexity", 0),
            "cluster": n.get("cluster_id", "cluster-unknown"),
            "type": n.get("language", "unknown"),
            "imports": n.get("imports", []),
            "in_degree": n.get("in_degree", 0),
            "out_degree": n.get("out_degree", 0),
        }
    )

# Build edges with resolved indices
node_id_to_idx = {n["id"]: i for i, n in enumerate(vis_nodes)}
vis_edges = []
for e in edges:
    src = _norm(e.get("source", ""))
    tgt = _norm(e.get("target", ""))
    if src in node_id_to_idx and tgt in node_id_to_idx:
        vis_edges.append({"source": node_id_to_idx[src], "target": node_id_to_idx[tgt]})

# Assign colors by cluster
all_clusters = sorted(set(n["cluster"] for n in vis_nodes))
cluster_colors = {}
palette = [
    "#e6194b",
    "#3cb44b",
    "#ffe119",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#46f0f0",
    "#f032e6",
    "#bcf60c",
    "#fabebe",
    "#008080",
    "#e6beff",
    "#9a6324",
    "#fffac8",
    "#800000",
    "#aaffc3",
    "#808000",
    "#ffd8b1",
    "#000075",
    "#808080",
    "#e6194b",
    "#3cb44b",
    "#ffe119",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#46f0f0",
    "#f032e6",
    "#bcf60c",
    "#fabebe",
]
for i, c in enumerate(all_clusters):
    cluster_colors[c] = palette[i % len(palette)]

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ConfigStream — RepoTopology Graph</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; overflow: hidden; }
  #container { width: 100vw; height: 100vh; position: relative; }
  svg { width: 100%; height: 100%; }
  .node circle { stroke: #fff; stroke-width: 1.5px; cursor: pointer; }
  .node:hover circle { stroke: #ffd700; stroke-width: 2.5px; }
  .link { stroke: #30363d; stroke-opacity: 0.6; }
  .node-label { font-size: 9px; fill: #8b949e; pointer-events: none; text-shadow: 0 1px 3px #0d1117; }
  #tooltip {
    position: absolute; display: none; background: #161b22; border: 1px solid #30363d;
    border-radius: 8px; padding: 12px 16px; font-size: 13px; pointer-events: none;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4); z-index: 100; max-width: 400px;
  }
  #tooltip .tt-path { color: #58a6ff; font-size: 11px; word-break: break-all; margin-bottom: 4px; }
  #tooltip .tt-name { color: #f0f6fc; font-size: 14px; font-weight: 600; margin-bottom: 6px; }
  #tooltip .tt-stat { color: #8b949e; font-size: 12px; line-height: 1.6; }
  #tooltip .tt-stat span { color: #d2a8ff; }
  #legend {
    position: absolute; bottom: 20px; left: 20px; background: #161b22; border: 1px solid #30363d;
    border-radius: 8px; padding: 12px 16px; font-size: 11px; max-height: 300px; overflow-y: auto; max-width: 280px;
  }
  #legend h3 { color: #f0f6fc; font-size: 12px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
  .legend-row { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; }
  .legend-swatch { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .legend-label { color: #8b949e; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  #title {
    position: absolute; top: 16px; left: 20px; z-index: 10;
  }
  #title h1 { font-size: 20px; font-weight: 600; color: #f0f6fc; }
  #title p { font-size: 12px; color: #8b949e; margin-top: 4px; }
  #stats {
    position: absolute; top: 16px; right: 20px; z-index: 10; text-align: right;
  }
  #stats h2 { font-size: 16px; font-weight: 600; color: #58a6ff; }
  #stats p { font-size: 11px; color: #8b949e; }
  .controls { position: absolute; bottom: 20px; right: 20px; z-index: 10; display: flex; gap: 8px; }
  .controls button {
    background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 8px 14px;
    border-radius: 6px; cursor: pointer; font-size: 12px; transition: all 0.2s;
  }
  .controls button:hover { background: #30363d; border-color: #58a6ff; }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #0d1117; }
  ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
</style>
</head>
<body>
<div id="container">
  <div id="title">
    <h1>ConfigStream · Topology</h1>
    <p>Dependency graph · 992 nodes · 57 edges</p>
  </div>
  <div id="stats">
    <h2 id="node-count">{node_count}</h2>
    <p>displayed / {total_nodes} total</p>
  </div>
  <svg id="graph"></svg>
  <div id="tooltip"></div>
  <div id="legend">
    <h3>Clusters</h3>
    {legend_rows}
  </div>
  <div class="controls">
    <button onclick="zoomToFit()">⟷ Fit</button>
    <button onclick="toggleLabels()">Aa Labels</button>
  </div>
</div>
<script>
const nodeData = {json_nodes};
const edgeData = {json_edges};
const clusterColors = {json_colors};

const width = window.innerWidth, height = window.innerHeight;
const svg = d3.select("#graph");
const g = svg.append("g");

svg.on("click", () => { d3.select("#tooltip").style("display", "none"); });

const simulation = d3.forceSimulation(nodeData)
  .force("link", d3.forceLink(edgeData).id(d => d.id).distance(80).strength(0.3))
  .force("charge", d3.forceManyBody().strength(-120))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collision", d3.forceCollide().radius(d => 4 + Math.sqrt(d.centrality * 200)));

const zoom = d3.zoom()
  .scaleExtent([0.1, 8])
  .on("zoom", (event) => { g.attr("transform", event.transform); });
svg.call(zoom);

const link = g.append("g").selectAll("line")
  .data(edgeData).join("line")
  .attr("class", "link")
  .attr("stroke-width", 0.5);

const node = g.append("g").selectAll("g")
  .data(nodeData).join("g")
  .attr("class", "node")
  .call(d3.drag()
    .on("start", (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
    .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
    .on("end", (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
  );

node.append("circle")
  .attr("r", d => 3 + Math.sqrt(d.centrality * 150))
  .attr("fill", d => clusterColors[d.cluster] || "#808080")
  .attr("stroke-width", d => d.centrality > 0.001 ? 2 : 1);

node.append("text")
  .attr("class", "node-label")
  .attr("dx", d => 5 + Math.sqrt(d.centrality * 150))
  .attr("dy", 3)
  .text(d => {
    if (d.centrality > 0.001 || d.out_degree > 0 || d.in_degree > 0) return d.label;
    return "";
  });

node.on("mouseover", (event, d) => {
  const tt = d3.select("#tooltip");
  tt.style("display", "block")
    .html(`<div class="tt-name">${d.label}</div><div class="tt-path">${d.path}</div><div class="tt-stat">
      Cluster: <span>${d.cluster}</span> · Centrality: <span>${d.centrality.toFixed(4)}</span><br>
      Complexity: <span>${d.complexity}</span> · Language: <span>${d.type}</span><br>
      Imports: <span>${d.imports ? d.imports.length : 0}</span> · In: <span>${d.in_degree}</span> · Out: <span>${d.out_degree}</span>
    </div>`)
    .style("left", (event.pageX + 15) + "px")
    .style("top", (event.pageY - 10) + "px");
})
.on("mouseout", () => { d3.select("#tooltip").style("display", "none"); });

simulation.on("tick", () => {
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("transform", d => `translate(${d.x},${d.y})`);
});

window.zoomToFit = () => {
  const bounds = g.node().getBBox();
  const scale = Math.min(width / bounds.width, height / bounds.height, 2);
  const transform = d3.zoomIdentity.translate(width/2 - bounds.x*scale - bounds.width*scale/2, height/2 - bounds.y*scale - bounds.height*scale/2).scale(scale);
  svg.transition().duration(500).call(zoom.transform, transform);
};

let labelsVisible = true;
window.toggleLabels = () => {
  labelsVisible = !labelsVisible;
  d3.selectAll(".node-label").attr("opacity", labelsVisible ? 1 : 0);
};

setTimeout(zoomToFit, 500);
</script>
</body>
</html>
"""

# Build legend rows (show top 15 clusters by count)
from collections import Counter

cluster_counts = Counter(n["cluster"] for n in vis_nodes)
legend_rows = ""
for c, count in cluster_counts.most_common(15):
    color = cluster_colors.get(c, "#808080")
    display_name = c.replace("cluster-", "#")
    legend_rows += f'<div class="legend-row"><div class="legend-swatch" style="background:{color}"></div><div class="legend-label">{display_name} ({count})</div></div>'

if len(cluster_counts) > 15:
    legend_rows += f'<div class="legend-row"><div class="legend-label" style="color:#58a6ff">+{len(cluster_counts)-15} more clusters</div></div>'

html = html.replace("{node_count}", str(len(vis_nodes)))
html = html.replace("{total_nodes}", str(len(data.get("nodes", []))))
html = html.replace("{json_nodes}", json.dumps(vis_nodes))
html = html.replace("{json_edges}", json.dumps(vis_edges))
html = html.replace("{json_colors}", json.dumps(cluster_colors))
html = html.replace("{legend_rows}", legend_rows)

OUTPUT_FILE.write_text(html)
print(
    f"Written {OUTPUT_FILE} — {len(vis_nodes)} nodes, {len(vis_edges)} edges in visualization"
)

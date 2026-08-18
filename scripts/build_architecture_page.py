# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path

# Load verified topology
top_path = Path("system_topology.json")
top = json.loads(top_path.read_text(encoding="utf-8"))

template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ConfigStream — System Architecture Topology (v3.2.0)</title>
<style>
  :root{
    --bg:#0b1220; --bg2:#0e1626; --panel:#111a2e; --panel2:#0d1526;
    --line:#1e2a44; --line2:#263454;
    --txt:#dbe6f5; --muted:#8fa3c4; --faint:#5b6d8f;
    --blue:#3b82f6; --cyan:#38bdf8; --amber:#f59e0b; --violet:#8b5cf6;
    --pink:#ec4899; --orange:#f97316; --slate:#64748b; --green:#10b981; --teal:#14b8a6;
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--txt);font-family:var(--sans);font-size:14px}
  #app{display:flex;flex-direction:column;height:100%}

  /* ---------- header ---------- */
  header{flex:0 0 56px;display:flex;align-items:center;gap:16px;padding:0 16px;border-bottom:1px solid var(--line);
    background:linear-gradient(180deg,var(--panel2),var(--bg));z-index:20}
  header .logo{display:flex;align-items:center;gap:10px;min-width:0}
  header .logo .mark{width:32px;height:32px;flex:0 0 32px;border-radius:8px;
    background:conic-gradient(from 210deg,var(--blue),var(--cyan),var(--violet),var(--blue));
    display:flex;align-items:center;justify-content:center;font-weight:800;color:#fff;font-size:15px;box-shadow:0 0 12px rgba(59,130,246,.3)}
  header h1{font-size:15px;font-weight:700;letter-spacing:.2px;white-space:nowrap}
  header .sub{color:var(--muted);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  
  .search-wrap{position:relative;margin-left:12px;flex:0 1 280px}
  .search-wrap input{width:100%;background:var(--panel);border:1px solid var(--line);border-radius:8px;
    padding:6px 10px 6px 30px;color:var(--txt);font-size:12px;outline:none;transition:border-color .15s}
  .search-wrap input:focus{border-color:var(--blue);box-shadow:0 0 0 2px rgba(59,130,246,.25)}
  .search-wrap .search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:12px;pointer-events:none}

  header .stats{display:flex;gap:8px;margin-left:auto;align-items:center;flex-wrap:nowrap}
  header .stat{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:4px 10px;
    font-size:11px;color:var(--muted);white-space:nowrap}
  header .stat b{color:var(--txt);font-weight:600}

  .ctrl-group{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
  .btn{appearance:none;border:1px solid var(--line);background:var(--panel);color:var(--txt);
    border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer;transition:border-color .15s,background .15s;display:inline-flex;align-items:center;gap:4px}
  .btn:hover{border-color:var(--blue);background:var(--bg2)}
  .btn.active{border-color:var(--blue);background:#17365f}
  .btn:disabled{opacity:.4;cursor:default}

  /* ---------- layout ---------- */
  #main{flex:1;display:flex;min-height:0}
  #canvas-wrap{flex:1;position:relative;min-width:0;background:
     radial-gradient(1200px 700px at 30% 20%, #0d1626 0%, var(--bg) 60%)}
  #scene{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:grab}
  #scene.panning{cursor:grabbing}

  /* ---------- overlays ---------- */
  .overlay{position:absolute;border:1px solid var(--line2);background:rgba(13,21,38,.92);
    backdrop-filter:blur(10px);border-radius:12px;color:var(--txt);box-shadow:0 8px 30px rgba(0,0,0,.45);z-index:10}

  #controls{{left:14px;top:14px;padding:10px 12px;display:flex;flex-direction:column;gap:8px;max-width:340px}}
  #controls .row{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
  #controls .filters{border-top:1px solid var(--line);padding-top:8px;margin-top:2px;display:flex;flex-direction:column;gap:6px}
  #controls .flabel{font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);font-weight:600}
  #controls .chips{display:flex;gap:5px;flex-wrap:wrap}
  .chip{border:1px solid var(--line);background:var(--panel);border-radius:6px;padding:3px 7px;font-size:11px;cursor:pointer;
    color:var(--muted);user-select:none;transition:all .15s}
  .chip.on{color:#fff;border-color:var(--blue);background:#17365f}

  #legend{left:14px;bottom:14px;padding:10px 12px;font-size:11.5px;max-width:280px;display:none}
  #legend.open{display:block}
  #legend .lh{font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);font-weight:600;margin-bottom:6px}
  #legend .item{display:flex;align-items:center;gap:8px;margin-bottom:4px;color:var(--muted)}
  #legend .dot{width:10px;height:10px;border-radius:3px}
  #legend .dash{width:18px;height:2px}

  #inspector{right:370px;top:14px;bottom:14px;width:380px;padding:16px;display:none;overflow-y:auto;z-index:15}
  #inspector.open{display:block}
  #inspector .close{position:absolute;top:12px;right:12px;background:none;border:none;color:var(--muted);font-size:18px;cursor:pointer;padding:4px}
  #inspector .close:hover{color:#fff}
  #inspector .head{display:flex;align-items:flex-start;gap:10px;margin-bottom:10px;padding-right:24px}
  #inspector .badge{flex:0 0 28px;height:28px;border-radius:7px;display:flex;align-items:center;justify-content:center;
    font-weight:700;font-size:12px;color:#fff}
  #inspector h2{font-size:15px;font-weight:700;line-height:1.3}
  #inspector .meta{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
  #inspector .pill{border:1px solid var(--line);border-radius:6px;padding:2px 7px;font-size:10.5px;color:var(--muted);text-transform:uppercase}
  #inspector .sec{font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--cyan);font-weight:600;margin:12px 0 4px}
  #inspector p.desc{font-size:12.5px;color:var(--txt);line-height:1.55}
  #inspector .kv{font-size:11.5px;color:var(--muted);line-height:1.6;font-family:var(--mono);background:var(--panel2);padding:8px;border-radius:8px;border:1px solid var(--line)}
  #inspector .kv span{color:var(--amber)}
  #inspector .io{font-size:11.5px;color:var(--muted);line-height:1.55;font-family:var(--mono)}
  #inspector .io span{color:var(--cyan)}
  #inspector .cites{display:flex;flex-direction:column;gap:6px}
  #inspector .cite{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:6px 8px;font-size:11.5px;position:relative}
  #inspector .cite b{color:#fff;font-family:var(--mono);font-size:11px}
  #inspector .cite .copy-btn{position:absolute;right:6px;top:6px;background:var(--panel);border:1px solid var(--line);color:var(--muted);border-radius:4px;padding:2px 6px;font-size:10px;cursor:pointer}
  #inspector .cite .copy-btn:hover{color:#fff;border-color:var(--blue)}

  #tooltip{position:absolute;display:none;pointer-events:none;z-index:30;padding:8px 10px;border-radius:8px;
    background:rgba(11,18,32,.95);border:1px solid var(--line2);color:var(--txt);font-size:11.5px;max-width:280px;
    box-shadow:0 6px 20px rgba(0,0,0,.6)}
  #tooltip .tt-name{font-weight:700;font-size:12px;margin-bottom:2px}
  #tooltip .tt-meta{color:var(--muted);font-size:10.5px;margin-bottom:4px}
  #tooltip .tt-desc{font-size:11.5px;color:var(--txt);line-height:1.4}
  #tooltip .tt-footer{font-size:10px;color:var(--faint);margin-top:6px;border-top:1px solid var(--line);padding-top:4px}

  /* ---------- step bar ---------- */
  #stepbar{position:absolute;left:50%;transform:translateX(-50%);bottom:14px;z-index:14;display:none;
    width:min(720px,calc(100% - 560px));background:rgba(13,21,38,.96);border:1px solid var(--line2);
    border-radius:12px;padding:12px 16px;box-shadow:0 12px 40px rgba(0,0,0,.55)}
  #stepbar.open{display:block}
  #stepbar .sb-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px}
  #stepbar .sb-flow{font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;color:var(--faint);font-weight:600}
  #stepbar .sb-ctrls{display:flex;gap:6px}
  #stepbar .sb-line{font-size:12.5px;color:#e7eefb;line-height:1.5}
  #stepbar .sb-line b{color:var(--cyan)}
  #stepbar .sb-payload{font-size:11.5px;color:var(--amber);font-family:var(--mono);margin-top:4px}
  #stepbar .sb-cite{font-size:10.5px;color:var(--faint);font-family:var(--mono);margin-top:3px}
  #stepbar .sb-progress{height:3px;background:var(--line);border-radius:2px;margin-top:8px;overflow:hidden}
  #stepbar .sb-progress i{display:block;height:100%;width:0;background:var(--blue);border-radius:2px;transition:width .2s}

  /* ---------- right sidebar ---------- */
  #flows{flex:0 0 356px;border-left:1px solid var(--line);background:var(--panel2);display:flex;flex-direction:column;min-height:0}
  #flows .fh{flex:0 0 auto;padding:12px 14px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between}
  #flows .fh h2{font-size:13px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted)}
  #flows .fh .count{font-size:11px;color:var(--faint)}
  #flows .flist{flex:1;overflow-y:auto;padding:10px}
  #flows details{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin-bottom:8px;overflow:hidden}
  #flows details.active{border-color:var(--blue);box-shadow:0 0 0 1px rgba(59,130,246,.4)}
  #flows summary{list-style:none;padding:10px 12px;cursor:pointer;display:flex;gap:10px;align-items:flex-start}
  #flows summary::-webkit-details-marker{display:none}
  #flows .fn{font-size:13px;font-weight:600;flex:1}
  #flows .fd{font-size:11.5px;color:var(--muted);line-height:1.45;margin-top:2px}
  #flows .play{flex:0 0 auto;background:var(--blue);border:none;color:#fff;border-radius:8px;padding:4px 10px;
    font-size:11px;cursor:pointer;font-weight:600;transition:background .15s}
  #flows .play:hover{background:#2f6fd8}
  #flows .steps{padding:2px 10px 10px}
  #flows .step{display:flex;gap:8px;align-items:flex-start;padding:6px 8px;border-radius:8px;cursor:pointer;
    border:1px solid transparent;font-size:11.5px;line-height:1.45}
  #flows .step:hover{background:var(--bg2)}
  #flows .step.on{background:#17365f;border-color:var(--blue)}
  #flows .step .no{flex:0 0 20px;height:20px;border-radius:6px;background:var(--bg2);border:1px solid var(--line);
    display:flex;align-items:center;justify-content:center;font-size:10px;color:var(--muted)}
  #flows .step.on .no{background:var(--blue);border-color:var(--blue);color:#fff}
  #flows .step .act b{color:var(--txt)}
  #flows .step .act span{color:var(--cyan);font-family:var(--mono);font-size:10.5px}
  #flows .hint{padding:2px 8px 10px;font-size:10.5px;color:var(--faint)}
</style>
</head>
<body>
<div id="app">
  <header>
    <div class="logo">
      <div class="mark">CS</div>
      <div>
        <h1>ConfigStream — Architecture Topology</h1>
        <div class="sub" id="hdr-sub">v3.2.0 · main · 40 Nodes · 58 Edges · 9 Flows</div>
      </div>
    </div>
    
    <div class="search-wrap">
      <span class="search-icon">🔍</span>
      <input type="text" id="search-input" placeholder="Search nodes, symbols, files (e.g. signer, wasm)..." />
    </div>

    <div class="stats">
      <span class="stat">Nodes <b id="st-nodes">0</b></span>
      <span class="stat">Edges <b id="st-edges">0</b></span>
      <span class="stat">Flows <b id="st-flows">0</b></span>
    </div>
  </header>
  <div id="main">
    <div id="canvas-wrap">
      <canvas id="scene"></canvas>

      <div id="controls" class="overlay">
        <div class="row">
          <button class="btn" id="btn-fit" title="Fit diagram to screen (F)">⛶ Fit</button>
          <button class="btn" id="btn-zoom-in" title="Zoom in (+)">＋</button>
          <button class="btn" id="btn-zoom-out" title="Zoom out (-)">－</button>
          <button class="btn" id="btn-reset" title="Reset camera">⟳</button>
          <button class="btn" id="btn-legend">Legend</button>
          <button class="btn" id="btn-clear">Clear</button>
        </div>
        <div class="filters">
          <div class="flabel">Component Layer / Type</div>
          <div class="chips" id="chip-types"></div>
          <div class="flabel">Edge Protocol / Type</div>
          <div class="chips" id="chip-edges"></div>
        </div>
      </div>

      <div id="legend" class="overlay"></div>
      <div id="inspector" class="overlay"></div>

      <div id="stepbar">
        <div class="sb-top">
          <div class="sb-flow" id="sb-flow"></div>
          <div class="sb-ctrls">
            <button class="btn" id="sb-prev" style="padding:2px 7px;font-size:11px">◀ Prev ([)</button>
            <button class="btn" id="sb-pause" style="padding:2px 7px;font-size:11px">❚❚ Pause</button>
            <button class="btn" id="sb-next" style="padding:2px 7px;font-size:11px">Next ▶ (])</button>
          </div>
        </div>
        <div class="sb-line" id="sb-line"></div>
        <div class="sb-payload" id="sb-payload"></div>
        <div class="sb-cite" id="sb-cite"></div>
        <div class="sb-progress"><i id="sb-prog"></i></div>
      </div>

      <div id="tooltip"></div>
    </div>

    <aside id="flows">
      <div class="fh">
        <h2>Execution Flows</h2>
        <span class="count" id="fl-count"></span>
      </div>
      <div class="flist" id="flist"></div>
    </aside>
  </div>
</div>

<script>
/* =====================================================================
 * ConfigStream architecture map — self-contained isometric renderer.
 * Verified Topology Data & Dynamic Graph Engine
 * =================================================================== */
const TOPOLOGY = __TOPOLOGY_JSON__;

/* Hand-curated 3D grid layout for every node id (x, y = ground plane, z = elevation). */
const LAYOUT = {
  proxy_sources:     {x:0.0, y:0.0, z:0.0},
  warp_sources:      {x:0.0, y:2.2, z:0.0},
  test_targets:      {x:0.0, y:4.4, z:0.0},
  singbox_core:      {x:0.0, y:6.6, z:0.0},
  cf_worker_bridge:  {x:0.0, y:8.8, z:0.0},
  mirror_publishers: {x:2.6, y:10.8, z:0.5},

  cli_gateway:       {x:2.4, y:0.0, z:2.0},
  db_downloader:     {x:2.4, y:2.2, z:1.0},
  telegram_bot:      {x:2.4, y:4.4, z:1.0},
  ci_orchestrator:   {x:2.4, y:6.6, z:2.0},
  dynamic_resharder: {x:3.6, y:7.8, z:1.5},
  merge_worker:      {x:2.4, y:8.6, z:2.0},

  source_admission:  {x:4.8, y:0.0, z:1.0},
  producer:          {x:4.8, y:1.2, z:1.5},
  fetcher:           {x:4.2, y:3.2, z:1.0},
  work_queue:        {x:5.6, y:4.6, z:1.2},
  event_stream:      {x:4.0, y:8.6, z:0.5},

  parser:            {x:7.2, y:0.0, z:1.0},
  security_validator:{x:7.2, y:1.5, z:1.0},
  consumer_pool:     {x:7.2, y:3.2, z:1.6},
  dedup_sort:        {x:8.6, y:0.0, z:1.5},

  go_tester:         {x:7.0, y:5.6, z:1.5},
  python_tester:     {x:5.6, y:6.8, z:1.0},
  washer:            {x:8.6, y:8.0, z:1.5},
  vwarp_tunnel:      {x:6.6, y:9.2, z:1.0},
  chain_engine:      {x:9.8, y:9.2, z:1.5},

  geoip_resolver:    {x:8.4, y:4.4, z:1.0},
  output_generator:  {x:10.0, y:6.0, z:1.6},
  release_signer:    {x:10.8, y:4.8, z:1.8},
  stego_generator:   {x:10.8, y:8.2, z:1.0},

  geo_db:            {x:7.0, y:10.2, z:0.5},
  quality_store:     {x:8.0, y:10.8, z:0.5},
  history_store:     {x:9.2, y:10.8, z:0.5},
  test_cache:        {x:10.4, y:10.2, z:0.5},
  output_store:      {x:11.6, y:7.0, z:0.6},
  publication_gate:  {x:11.2, y:9.0, z:1.5},

  web_server:        {x:11.6, y:1.0, z:2.0},
  ws_broker:         {x:11.0, y:3.4, z:2.0},
  frontend_pwa:      {x:12.6, y:1.2, z:2.6},
  wasm_verifier:     {x:13.6, y:3.2, z:2.5}
};

/* ---------------------------------------------------------------------
 * Infrastructure & Styling Tokens
 * ------------------------------------------------------------------- */
const TYPE_COLOR = {
  gateway:'#3b82f6', service:'#38bdf8', worker:'#f59e0b', database:'#8b5cf6',
  cache:'#ec4899', queue:'#f97316', external:'#64748b'
};
const LAYER_COLOR = {
  presentation:'#10b981', application:'#38bdf8', domain:'#22d3ee',
  persistence:'#8b5cf6', infrastructure:'#64748b'
};
const EDGE_STYLE = {
  sync_request:  {color:'#3b82f6', dash:[], width:2.2},
  async_event:   {color:'#f59e0b', dash:[7,5], width:2.2},
  db_query:      {color:'#a78bfa', dash:[1,4], width:2.2},
  stream:        {color:'#14b8a6', dash:[2,3], width:2.6},
  dependency:    {color:'#94a3b8', dash:[4,4], width:1.4},
  file_write:    {color:'#ec4899', dash:[3,3], width:2.2},
  file_read:     {color:'#8b5cf6', dash:[4,2], width:2.0},
  async_publish: {color:'#10b981', dash:[6,4], width:2.4},
  async_request: {color:'#38bdf8', dash:[5,3], width:2.2},
  sync_response: {color:'#38bdf8', dash:[], width:2.2}
};
const EDGE_LABEL = {
  sync_request:'RPC/HTTP', async_event:'EVENT', db_query:'DB', stream:'STREAM', dependency:'DEP',
  file_write:'FILE WRITE', file_read:'FILE READ', async_publish:'PUBLISH', async_request:'ASYNC REQ', sync_response:'RESPONSE'
};

const NS = ['gateway','service','worker','database','cache','queue','external'];
const ES = ['sync_request','async_event','db_query','stream','dependency','file_write','file_read','async_publish','async_request','sync_response'];

const nodeById = {}; TOPOLOGY.nodes.forEach(n => nodeById[n.id] = n);
const edges = TOPOLOGY.edges;
const flows = TOPOLOGY.flows;

/* camera */
const cam = {scale:0.85, px:0, py:0};
const TILE_W = 92, TILE_H = 54, LIFT = 46;
function project(x,y,z){
  return {x:(x - y) * TILE_W / 2, y:(x + y) * TILE_H / 2 - z * LIFT};
}
function toScreen(gx, gy){
  return {x: cam.px + gx * cam.scale, y: cam.py + gy * cam.scale};
}
function worldToScreen(x,y,z){
  const p = project(x,y,z);
  return toScreen(p.x, p.y);
}

function nodePos(id){ return LAYOUT[id] || {x:0,y:0,z:0}; }
function nodeScreen(id){ const p = worldToScreen(nodePos(id).x, nodePos(id).y, nodePos(id).z); return p; }

let W=0, H=0, DPR=1, cw=0, ch=0;
const canvas = document.getElementById('scene');
const ctx = canvas.getContext('2d');
function resize(){
  const wrap = document.getElementById('canvas-wrap');
  DPR = window.devicePixelRatio || 1;
  cw = wrap.clientWidth; ch = wrap.clientHeight;
  canvas.width = cw * DPR; canvas.height = ch * DPR;
  canvas.style.width = cw + 'px'; canvas.style.height = ch + 'px';
  ctx.setTransform(DPR,0,0,DPR,0,0);
  W = cw; H = ch;
}
window.addEventListener('resize', resize);

function bounds(){
  let minX=1e9, maxX=-1e9, minY=1e9, maxY=-1e9;
  TOPOLOGY.nodes.forEach(n => {
    const p = project(nodePos(n.id).x, nodePos(n.id).y, nodePos(n.id).z);
    minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
    minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
  });
  return {minX, maxX, minY, maxY};
}
function fit(){
  const b = bounds(); resize();
  const pad = 100;
  const bw = (b.maxX - b.minX) || 1, bh = (b.maxY - b.minY) || 1;
  cam.scale = Math.min((W - pad*2) / bw, (H - pad*2) / bh, 1.4);
  cam.scale = Math.max(cam.scale, 0.08);
  const cx = (b.minX + b.maxX) / 2, cy = (b.minY + b.maxY) / 2;
  cam.px = W/2 - cx * cam.scale;
  cam.py = H/2 - cy * cam.scale;
}

/* state */
const state = {
  typeOn: new Set(NS),
  edgeOn: new Set(ES),
  searchQuery: '',
  selected: null,
  hoverNode: null,
  hoverEdge: null,
  activeFlow: null,
  activeStep: -1,
  isPlaying: false,
  playTimer: null,
  playSpeed: 1800,
  time: 0,
  down: false,
  moved: false,
  dragStart: {x:0, y:0},
  panStart: {x:0, y:0}
};

const screenCache = {};
const edgeCache = [];

function initHeader(){
  document.getElementById('st-nodes').textContent = TOPOLOGY.nodes.length;
  document.getElementById('st-edges').textContent = TOPOLOGY.edges.length;
  document.getElementById('st-flows').textContent = TOPOLOGY.flows.length;
  document.getElementById('hdr-sub').textContent =
    `v${TOPOLOGY.metadata.version || '3.2.0'} · ${TOPOLOGY.metadata.branch || 'main'} · ${TOPOLOGY.nodes.length} Nodes · ${TOPOLOGY.edges.length} Edges · ${TOPOLOGY.flows.length} Execution Flows`;
}

function initChips(){
  const tWrap = document.getElementById('chip-types');
  tWrap.innerHTML = '';
  NS.forEach(t => {
    const c = document.createElement('div');
    c.className = 'chip on';
    c.textContent = t;
    c.addEventListener('click', () => {
      if (state.typeOn.has(t)){ state.typeOn.delete(t); c.classList.remove('on'); }
      else { state.typeOn.add(t); c.classList.add('on'); }
    });
    tWrap.appendChild(c);
  });

  const eWrap = document.getElementById('chip-edges');
  eWrap.innerHTML = '';
  ES.forEach(t => {
    const c = document.createElement('div');
    c.className = 'chip on';
    c.textContent = EDGE_LABEL[t] || t;
    c.addEventListener('click', () => {
      if (state.edgeOn.has(t)){ state.edgeOn.delete(t); c.classList.remove('on'); }
      else { state.edgeOn.add(t); c.classList.add('on'); }
    });
    eWrap.appendChild(c);
  });
}

function initLegend(){
  const leg = document.getElementById('legend');
  let h = '<div class="lh">Node Types</div>';
  NS.forEach(t => {
    h += `<div class="item"><div class="dot" style="background:${TYPE_COLOR[t]}"></div><span>${t}</span></div>`;
  });
  h += '<div class="lh" style="margin-top:8px">Edge Protocols</div>';
  ES.forEach(t => {
    const st = EDGE_STYLE[t] || EDGE_STYLE.dependency;
    h += `<div class="item"><div class="dash" style="background:${st.color}"></div><span>${EDGE_LABEL[t] || t}</span></div>`;
  });
  leg.innerHTML = h;
}
document.getElementById('btn-legend').addEventListener('click', () => {
  document.getElementById('legend').classList.toggle('open');
});

function initFlows(){
  const list = document.getElementById('flist');
  list.innerHTML = '';
  document.getElementById('fl-count').textContent = flows.length + ' verified paths';
  flows.forEach((flow, fi) => {
    const det = document.createElement('details');
    det.id = 'flow-' + flow.id;
    const sum = document.createElement('summary');
    const playBtn = document.createElement('button');
    playBtn.className = 'play'; playBtn.textContent = '▶ Play';
    playBtn.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); playFlow(flow); });
    const title = document.createElement('div');
    title.className = 'fn';
    title.innerHTML = `<div>${flow.name}</div><div class="fd">${flow.description}</div>`;
    sum.appendChild(title); sum.appendChild(playBtn);
    det.appendChild(sum);
    const steps = document.createElement('div');
    steps.className = 'steps';
    flow.steps.forEach((s, si) => {
      const row = document.createElement('div');
      row.className = 'step';
      row.dataset.flow = flow.id; row.dataset.idx = si;
      const srcN = nodeById[s.from], dstN = nodeById[s.to];
      row.innerHTML = `<div class="no">${si + 1}</div>
        <div class="act"><b>${srcN ? srcN.name.split(' (')[0] : s.from}</b> → <b>${dstN ? dstN.name.split(' (')[0] : s.to}</b>
        <br><span>${s.action}</span></div>`;
      row.addEventListener('click', () => {
        det.open = true;
        setActiveStep(flow, si);
      });
      steps.appendChild(row);
    });
    const hint = document.createElement('div');
    hint.className = 'hint';
    hint.textContent = 'Click any step to illuminate the path; ▶ animates the complete cycle.';
    steps.appendChild(hint);
    det.appendChild(steps);
    list.appendChild(det);
  });
}

function flowEdgeOf(flow, stepIdx){
  if (!flow || stepIdx < 0 || stepIdx >= flow.steps.length) return null;
  const s = flow.steps[stepIdx];
  return edges.find(e => (e.source === s.from && e.target === s.to) || (e.source === s.to && e.target === s.from)) || null;
}

function setActiveStep(flow, stepIdx){
  state.activeFlow = flow;
  state.activeStep = stepIdx;
  syncFlowPanel();
  renderStepBar();
  const s = flow.steps[stepIdx];
  const targetNode = nodeById[s.to] || nodeById[s.from];
  if (targetNode){
    state.selected = targetNode;
    renderInspector();
  }
}

function playFlow(flow){
  stopPlay();
  state.activeFlow = flow;
  state.activeStep = 0;
  state.isPlaying = true;
  document.getElementById('sb-pause').textContent = '❚❚ Pause';
  syncFlowPanel();
  renderStepBar();
  state.playTimer = setInterval(() => {
    if (state.activeStep + 1 < flow.steps.length){
      state.activeStep++;
      syncFlowPanel();
      renderStepBar();
    } else {
      stopPlay();
    }
  }, state.playSpeed);
}

function stopPlay(){
  if (state.playTimer) clearInterval(state.playTimer);
  state.playTimer = null;
  state.isPlaying = false;
  document.getElementById('sb-pause').textContent = '▶ Play';
}

function syncFlowPanel(){
  document.querySelectorAll('#flows details').forEach(d => {
    const active = state.activeFlow && d.id === 'flow-' + state.activeFlow.id;
    d.classList.toggle('active', !!active);
    if (active) d.open = true;
  });
  document.querySelectorAll('#flows .step').forEach(el => {
    const on = state.activeFlow && el.dataset.flow === state.activeFlow.id &&
               parseInt(el.dataset.idx, 10) === state.activeStep;
    el.classList.toggle('on', !!on);
    if (on) el.scrollIntoView({block:'nearest'});
  });
}

function renderStepBar(){
  const bar = document.getElementById('stepbar');
  if (!state.activeFlow || state.activeStep < 0){ bar.classList.remove('open'); return; }
  const s = state.activeFlow.steps[state.activeStep];
  const srcN = nodeById[s.from], dstN = nodeById[s.to];
  bar.classList.add('open');
  document.getElementById('sb-flow').textContent =
    `FLOW ${state.activeStep + 1}/${state.activeFlow.steps.length} — ${state.activeFlow.name}`;
  document.getElementById('sb-line').innerHTML =
    `<b>${srcN ? srcN.name : s.from}</b> → <b>${dstN ? dstN.name : s.to}</b> · ${s.action}`;
  document.getElementById('sb-payload').textContent = 'PAYLOAD  ' + (s.payload || '—');
  document.getElementById('sb-cite').textContent = 'SOURCE   ' + s.file_citation;
  document.getElementById('sb-prog').style.width =
    ((state.activeStep + 1) / state.activeFlow.steps.length * 100) + '%';
}

document.getElementById('sb-prev').addEventListener('click', () => {
  if (state.activeFlow && state.activeStep > 0){
    setActiveStep(state.activeFlow, state.activeStep - 1);
  }
});
document.getElementById('sb-next').addEventListener('click', () => {
  if (state.activeFlow && state.activeStep + 1 < state.activeFlow.steps.length){
    setActiveStep(state.activeFlow, state.activeStep + 1);
  }
});
document.getElementById('sb-pause').addEventListener('click', () => {
  if (state.isPlaying){ stopPlay(); }
  else if (state.activeFlow){ playFlow(state.activeFlow); }
});

function renderInspector(){
  const el = document.getElementById('inspector');
  const n = state.selected;
  if (!n){ el.classList.remove('open'); el.innerHTML = ''; return; }
  const color = TYPE_COLOR[n.type] || '#10b981';
  const inEdges = edges.filter(e => e.target === n.id);
  const outEdges = edges.filter(e => e.source === n.id);
  let cites = n.file_citations.map(c => {
    const syms = (c.symbols||[]).map(s=>s.replace(/[<>&]/g,'')).join(', ') || '—';
    return `<div class="cite">
      <button class="copy-btn" onclick="navigator.clipboard.writeText('${c.file}');this.textContent='Copied!'">Copy Path</button>
      <b>${c.file}</b><br>${syms}
    </div>`;
  }).join('');
  const ports = (n.runtime_config && n.runtime_config.ports && n.runtime_config.ports.length)
    ? n.runtime_config.ports.map(p=>`<div><span>port </span>${p}</div>`).join('')
    : '<div><span>none (in-process / subprocess IPC)</span></div>';
  const envs = (n.runtime_config && n.runtime_config.env_dependencies && n.runtime_config.env_dependencies.length)
    ? n.runtime_config.env_dependencies.map(e=>`<div><span>env </span>${e}</div>`).join('')
    : '<div><span>none</span></div>';
  el.innerHTML = `
    <button class="close" title="Close (Esc)">×</button>
    <div class="head">
      <div class="badge" style="background:${color}">${(n.type||'?').slice(0,2).toUpperCase()}</div>
      <h2>${n.name}</h2>
    </div>
    <div class="meta">
      <span class="pill" style="border-color:${color};color:${color}">${n.type}</span>
      <span class="pill">layer · ${n.layer}</span>
    </div>
    <div class="sec">Primary Responsibilities</div>
    <p class="desc">${n.description}</p>
    <div class="sec">Exposed Interfaces / Runtime</div>
    <div class="kv">${ports}${envs}</div>
    <div class="sec">Inbound Edges (${inEdges.length})</div>
    <div class="io">${inEdges.length ? inEdges.map(e=>`→ <b>${nodeById[e.source] ? nodeById[e.source].name.split(' (')[0] : e.source}</b>: <span>${e.protocol}</span> · ${e.file_citations ? e.file_citations[0] : ''}`).join('<br>') : '—'}</div>
    <div class="sec">Outbound Edges (${outEdges.length})</div>
    <div class="io">${outEdges.length ? outEdges.map(e=>`→ <b>${nodeById[e.target] ? nodeById[e.target].name.split(' (')[0] : e.target}</b>: <span>${e.protocol}</span> · ${e.file_citations ? e.file_citations[0] : ''}`).join('<br>') : '—'}</div>
    <div class="sec">Defining Source Files</div>
    <div class="cites">${cites}</div>`;
  el.querySelector('.close').addEventListener('click', () => {
    state.selected = null; renderInspector();
  });
  el.classList.add('open');
}

function showTooltip(x, y, html){
  const tt = document.getElementById('tooltip');
  tt.innerHTML = html; tt.style.display = 'block';
  const r = tt.getBoundingClientRect();
  const wrap = document.getElementById('canvas-wrap').getBoundingClientRect();
  let lx = x + 14, ly = y + 14;
  if (lx + r.width > wrap.width - 8) lx = x - r.width - 14;
  if (ly + r.height > wrap.height - 8) ly = y - r.height - 14;
  tt.style.left = lx + 'px'; tt.style.top = ly + 'px';
}
function hideTooltip(){ document.getElementById('tooltip').style.display = 'none'; }
function nodeTooltipHtml(n, screenX, screenY){
  const color = TYPE_COLOR[n.type] || '#10b981';
  return `<div class="tt-name" style="color:${color}">${n.name}</div>
    <div class="tt-meta"><span class="pill" style="border-color:${color};color:${color}">${n.type}</span>
    <span class="pill">${n.layer}</span></div>
    <div class="tt-desc">${n.description.slice(0, 220)}${n.description.length > 220 ? '…' : ''}</div>
    <div class="tt-footer">${n.file_citations.length} defining file(s) · ${n.file_citations[0].file}…<br>Click node to open inspector</div>`;
}
function edgeTooltipHtml(e, x, y){
  const st = EDGE_STYLE[e.type] || EDGE_STYLE.dependency;
  const srcN = nodeById[e.source], dstN = nodeById[e.target];
  return `<div class="tt-name" style="color:${st.color}">${EDGE_LABEL[e.type] || e.type} Edge</div>
    <div class="tt-meta"><span class="pill" style="border-color:${st.color};color:${st.color}">${e.type}</span>
    <span class="pill">${e.protocol}</span></div>
    <div class="tt-desc"><b>${srcN ? srcN.name.split(' (')[0] : e.source}</b> → <b>${dstN ? dstN.name.split(' (')[0] : e.target}</b><br>${e.description}</div>
    <div class="tt-footer">Payload: ${e.payload_type || '—'}<br>${e.file_citations ? e.file_citations[0] : ''}</div>`;
}

function pickNode(mx, my){
  let best = null, bestD = 1e9;
  for (const n of TOPOLOGY.nodes){
    if (!state.typeOn.has(n.type)) continue;
    const c = screenCache[n.id];
    if (!c) continue;
    if (mx >= c.x - 6 && mx <= c.x + c.w + 6 && my >= c.y - 6 && my <= c.y + c.h + 6){
      const d = (mx - (c.x + c.w/2))**2 + (my - (c.y + c.h/2))**2;
      if (d < bestD){ bestD = d; best = n; }
    }
  }
  return best;
}
function segDist(px, py, ax, ay, bx, by){
  const dx = bx - ax, dy = by - ay;
  const len2 = dx*dx + dy*dy;
  let t = len2 ? ((px - ax)*dx + (py - ay)*dy) / len2 : 0;
  t = Math.max(0, Math.min(1, t));
  const cx = ax + t*dx, cy = ay + t*dy;
  return Math.hypot(px - cx, py - cy);
}
function pickEdge(mx, my){
  let best = null, bestD = 1e9;
  for (const e of edgeCache){
    if (!state.edgeOn.has(e.type)) continue;
    const d = segDist(mx, my, e.x1, e.y1, e.x2, e.y2);
    if (d < bestD && d < 8 + cam.scale * 4){ bestD = d; best = e; }
  }
  return best;
}

function drawGrid(){
  const b = bounds();
  const minX = Math.floor(b.minX / TILE_W) - 1, maxX = Math.ceil(b.maxX / TILE_W) + 1;
  const minY = Math.floor(b.minY / TILE_H) - 1, maxY = Math.ceil(b.maxY / TILE_H) + 1;
  const alpha = state.activeFlow ? 0.05 : 0.14;
  ctx.strokeStyle = 'rgba(90,120,180,' + alpha + ')';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = minX; i <= maxX; i++){
    const a = toScreen(i * TILE_W/2, minY * TILE_H/2);
    const c = toScreen(i * TILE_W/2, maxY * TILE_H/2);
    ctx.moveTo(a.x, a.y); ctx.lineTo(c.x, c.y);
  }
  for (let j = minY; j <= maxY; j++){
    const a = toScreen(minX * TILE_W/2, j * TILE_H/2);
    const c = toScreen(maxX * TILE_W/2, j * TILE_H/2);
    ctx.moveTo(a.x, a.y); ctx.lineTo(c.x, c.y);
  }
  ctx.stroke();
}
const nodeDim = {w: 64, h: 42};
function drawNode(n, layerAlpha){
  const p = screenCache[n.id];
  if (!p) return;
  const color = TYPE_COLOR[n.type] || LAYER_COLOR[n.layer] || '#10b981';
  const isSel = state.selected && state.selected.id === n.id;
  const isHov = state.hoverNode && state.hoverNode.id === n.id;
  const inFlow = state.activeFlow && state.activeFlow.steps.some(s => s.from === n.id || s.to === n.id);
  
  let isMatch = true;
  if (state.searchQuery){
    const q = state.searchQuery.toLowerCase();
    const txt = (n.name + ' ' + n.id + ' ' + n.description + ' ' + (n.file_citations||[]).map(c=>c.file + ' ' + (c.symbols||[]).join(' ')).join(' ')).toLowerCase();
    isMatch = txt.includes(q);
  }

  let alpha = layerAlpha;
  if (state.activeFlow && !inFlow) alpha *= 0.10;
  if (!isMatch) alpha *= 0.12;
  if (isSel || isHov) alpha = Math.min(1, alpha + 0.30);
  ctx.save();
  ctx.globalAlpha = alpha;

  const cx = p.x + p.w/2, cy = p.y + p.h/2;
  const s = cam.scale;
  const bw = nodeDim.w * Math.max(0.5, Math.min(1.4, s)), bh = nodeDim.h * Math.max(0.5, Math.min(1.4, s));
  const lift = 8 + n._z * 16;

  /* isometric 3d block */
  const halfW = bw/2, halfD = bh/2;
  const x0 = cx, y0 = cy - lift * s;
  const dx = halfW * 0.9, dy = halfD * 0.9;
  const top = [
    {x: x0,         y: y0 - dy},
    {x: x0 + dx,    y: y0},
    {x: x0,         y: y0 + dy},
    {x: x0 - dx,    y: y0}
  ];
  const left = [
    {x: x0 - dx, y: y0}, {x: x0, y: y0 + dy},
    {x: x0, y: y0 + dy + 10*s}, {x: x0 - dx, y: y0 + 10*s}
  ];
  const right = [
    {x: x0 + dx, y: y0}, {x: x0, y: y0 + dy},
    {x: x0, y: y0 + dy + 10*s}, {x: x0 + dx, y: y0 + 10*s}
  ];

  ctx.beginPath(); ctx.moveTo(left[0].x,left[0].y);
  left.forEach(pt=>ctx.lineTo(pt.x,pt.y)); ctx.closePath();
  ctx.fillStyle = shade(color, -0.45); ctx.fill();

  ctx.beginPath(); ctx.moveTo(right[0].x,right[0].y);
  right.forEach(pt=>ctx.lineTo(pt.x,pt.y)); ctx.closePath();
  ctx.fillStyle = shade(color, -0.25); ctx.fill();

  ctx.beginPath(); top.forEach((pt,i)=> i ? ctx.lineTo(pt.x,pt.y) : ctx.moveTo(pt.x,pt.y)); ctx.closePath();
  ctx.fillStyle = shade(color, 0.15); ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,' + (0.14 + (isSel?0.4:isHov?0.25:0)) + ')';
  ctx.lineWidth = isSel || isHov ? 2.0 : 1;
  ctx.stroke();

  /* type letter badge */
  ctx.fillStyle = '#fff';
  ctx.font = '700 ' + Math.max(9, 11 * Math.min(1.3, Math.max(0.55, s))) + 'px ' + getComputedStyle(document.body).fontFamily;
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText((n.type||'?').slice(0,1).toUpperCase(), x0, y0 - dy * 0.25);

  ctx.restore();

  /* label */
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.font = '600 ' + Math.max(10, 11.5) + 'px ' + getComputedStyle(document.body).fontFamily;
  ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  ctx.fillStyle = isSel ? '#38bdf8' : (isMatch ? '#dbe6f5' : '#64748b');
  const label = n.name.split(' (')[0];
  const ty = y0 + 10*s + 4;
  ctx.fillText(label, cx, ty);
  if (state.selected && state.selected.id === n.id){
    ctx.fillStyle = color;
    ctx.fillRect(cx - label.length * 3.2, ty + 15, label.length * 6.4, 2);
  }
  ctx.restore();

  p.labelBottom = ty + 18;
}

function shade(hex, amt){
  const n = parseInt(hex.slice(1), 16);
  let r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  if (amt < 0){ r *= 1 + amt; g *= 1 + amt; b *= 1 + amt; }
  else { r += (255 - r) * amt; g += (255 - g) * amt; b += (255 - b) * amt; }
  return `rgb(${r|0},${g|0},${b|0})`;
}

function drawEdge(e, alpha, emphasize){
  const a = nodeScreen(e.source), b = nodeScreen(e.target);
  const src = screenCache[e.source], dst = screenCache[e.target];
  let x1 = a.x + (src ? src.w/2 : 0), y1 = a.y + (src ? src.h/2 - 10 : 0) - nodePos(e.source).z * 10 * cam.scale;
  let x2 = b.x + (dst ? dst.w/2 : 0), y2 = b.y + (dst ? dst.h/2 - 10 : 0) - nodePos(e.target).z * 10 * cam.scale;
  
  x1 = a.x + (nodeDim.w/2) * Math.max(0.5, Math.min(1.4, cam.scale)) * 0.9 + 4;
  y1 = a.y + (nodeDim.h/2) * Math.max(0.5, Math.min(1.4, cam.scale)) * 0.9 - nodePos(e.source).z * 10 * cam.scale;
  x2 = b.x + (nodeDim.w/2) * Math.max(0.5, Math.min(1.4, cam.scale)) * 0.9 + 4;
  y2 = b.y + (nodeDim.h/2) * Math.max(0.5, Math.min(1.4, cam.scale)) * 0.9 - nodePos(e.target).z * 10 * cam.scale;

  const cached = edgeCache.find(c => c.id === e.id);
  if (cached){ cached.x1 = x1; cached.y1 = y1; cached.x2 = x2; cached.y2 = y2; cached.type = e.type; }

  const st = EDGE_STYLE[e.type] || EDGE_STYLE.dependency;
  const isHovEdge = state.hoverEdge && state.hoverEdge.id === e.id;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = st.color;
  ctx.lineWidth = (st.width || 1.8) * (emphasize ? 2.0 : 1) * (isHovEdge ? 1.5 : 1);
  ctx.setLineDash(st.dash || []);
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  ctx.setLineDash([]);

  /* arrowhead */
  const ang = Math.atan2(y2 - y1, x2 - x1);
  const arrowLen = 8 * (emphasize ? 1.5 : 1);
  ctx.fillStyle = st.color;
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - arrowLen * Math.cos(ang - 0.42), y2 - arrowLen * Math.sin(ang - 0.42));
  ctx.lineTo(x2 - arrowLen * Math.cos(ang + 0.42), y2 - arrowLen * Math.sin(ang + 0.42));
  ctx.closePath(); ctx.fill();

  /* moving payload particles */
  if (alpha > 0.08){
    const count = emphasize ? 4 : (state.activeFlow ? 1 : 0);
    for (let i = 0; i < count; i++){
      const t = (state.time * 0.00025 * (emphasize ? 1.2 : 0.6) + i / count) % 1;
      const px = x1 + (x2 - x1) * t, py = y1 + (y2 - y1) * t;
      ctx.globalAlpha = emphasize ? 0.95 : 0.40;
      ctx.fillStyle = st.color;
      ctx.beginPath(); ctx.arc(px, py, emphasize ? 3.8 : 2.4, 0, Math.PI*2); ctx.fill();
    }
  }
  ctx.restore();
}

function nodeOrder(){
  return TOPOLOGY.nodes.slice().sort((a, b) => {
    const pa = nodePos(a.id), pb = nodePos(b.id);
    return (pa.x + pa.y) - (pb.x + pb.y);
  });
}
function computeActiveEdges(){
  const set = new Set();
  if (state.activeFlow){
    state.activeFlow.steps.forEach((s, i) => {
      const e = flowEdgeOf(state.activeFlow, i);
      if (e) set.add(e.id);
    });
  }
  return set;
}

function render(){
  ctx.clearRect(0, 0, W, H);

  for (const n of TOPOLOGY.nodes){
    const p = worldToScreen(nodePos(n.id).x, nodePos(n.id).y, nodePos(n.id).z);
    screenCache[n.id] = {x: p.x - nodeDim.w/2, y: p.y - nodeDim.h/2 - (8 + nodePos(n.id).z * 16) * cam.scale, w: nodeDim.w, h: nodeDim.h, z: nodePos(n.id).z};
    screenCache[n.id]._z = nodePos(n.id).z;
  }
  edgeCache.length = 0;
  edges.forEach(e => edgeCache.push({id: e.id, type: e.type, x1:0,y1:0,x2:0,y2:0}));

  const activeEdges = computeActiveEdges();
  const activeNodes = new Set();
  if (state.activeFlow){
    state.activeFlow.steps.forEach(s => { activeNodes.add(s.from); activeNodes.add(s.to); });
  }

  drawGrid();

  const edgeOrder = edges.slice().sort((a,b) => {
    const pa = nodePos(a.source), pb = nodePos(b.source);
    return (pa.x + pa.y) - (pb.x + pb.y);
  });
  for (const e of edgeOrder){
    if (!state.edgeOn.has(e.type)){
      drawEdge(e, 0.03, false); continue;
    }
    if (state.activeFlow){
      if (activeEdges.has(e.id)){
        const isStep = state.activeFlow.steps.some((s, i) => i === state.activeStep && flowEdgeOf(state.activeFlow, i) && flowEdgeOf(state.activeFlow, i).id === e.id);
        drawEdge(e, isStep ? 1 : 0.60, true);
      } else {
        drawEdge(e, 0.05, false);
      }
    } else {
      drawEdge(e, 0.75, false);
    }
  }

  for (const n of nodeOrder()){
    if (!state.typeOn.has(n.type)){
      drawNode(n, 0.02); continue;
    }
    drawNode(n, state.activeFlow ? (activeNodes.has(n.id) ? 1 : 0.08) : 0.96);
  }
}

let raf = null;
function tick(ts){
  state.time = ts;
  render();
  raf = requestAnimationFrame(tick);
}

/* ---------------------------------------------------------------------
 * Search & Keyboard Shortcuts
 * ------------------------------------------------------------------- */
const searchInput = document.getElementById('search-input');
searchInput.addEventListener('input', e => {
  state.searchQuery = e.target.value.trim();
  if (state.searchQuery){
    const matched = TOPOLOGY.nodes.find(n => {
      const q = state.searchQuery.toLowerCase();
      return n.name.toLowerCase().includes(q) || n.id.toLowerCase().includes(q);
    });
    if (matched){
      const p = project(nodePos(matched.id).x, nodePos(matched.id).y, nodePos(matched.id).z);
      cam.px = W/2 - p.x * cam.scale;
      cam.py = H/2 - p.y * cam.scale;
    }
  }
});

window.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  if (e.key === 'Escape'){
    state.selected = null; state.activeFlow = null; state.activeStep = -1; state.searchQuery = ''; searchInput.value = '';
    stopPlay(); syncFlowPanel(); renderStepBar(); renderInspector();
  } else if (e.key === 'f' || e.key === 'F'){
    fit();
  } else if (e.key === '+' || e.key === '='){
    cam.scale = Math.min(4, cam.scale * 1.25);
  } else if (e.key === '-' || e.key === '_'){
    cam.scale = Math.max(0.05, cam.scale / 1.25);
  } else if (e.key === ']' && state.activeFlow){
    if (state.activeStep + 1 < state.activeFlow.steps.length) setActiveStep(state.activeFlow, state.activeStep + 1);
  } else if (e.key === '[' && state.activeFlow){
    if (state.activeStep > 0) setActiveStep(state.activeFlow, state.activeStep - 1);
  } else if (e.key >= '1' && e.key <= '9'){
    const idx = parseInt(e.key, 10) - 1;
    if (idx < flows.length) playFlow(flows[idx]);
  }
});

/* ---------------------------------------------------------------------
 * Interaction Listeners
 * ------------------------------------------------------------------- */
function canvasMouse(e){
  const rect = canvas.getBoundingClientRect();
  return {x: e.clientX - rect.left, y: e.clientY - rect.top};
}
canvas.addEventListener('mousedown', e => {
  state.down = true; state.moved = false;
  state.dragStart = canvasMouse(e);
  state.panStart = {x: cam.px, y: cam.py};
  canvas.classList.add('panning');
});
window.addEventListener('mousemove', e => {
  const m = canvasMouse(e);
  if (state.down){
    const dx = m.x - state.dragStart.x, dy = m.y - state.dragStart.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) state.moved = true;
    if (state.moved){ cam.px = state.panStart.x + dx; cam.py = state.panStart.y + dy; }
    return;
  }
  const nn = pickNode(m.x, m.y);
  const ne = nn ? null : pickEdge(m.x, m.y);
  state.hoverNode = nn; state.hoverEdge = ne;
  if (nn){
    showTooltip(m.x, m.y, nodeTooltipHtml(nn, m.x, m.y));
  } else if (ne){
    showTooltip(m.x, m.y, edgeTooltipHtml(ne, m.x, m.y));
  } else {
    hideTooltip();
  }
});
window.addEventListener('mouseup', e => {
  if (state.down && !state.moved){
    const m = canvasMouse(e);
    const n = pickNode(m.x, m.y);
    if (n){
      state.selected = n;
      renderInspector();
    } else {
      const ne = pickEdge(m.x, m.y);
      if (ne){
        if (state.activeFlow){
          const idx = state.activeFlow.steps.findIndex((s, i) => flowEdgeOf(state.activeFlow, i) && flowEdgeOf(state.activeFlow, i).id === ne.id);
          if (idx >= 0){ setActiveStep(state.activeFlow, idx); return; }
        }
        state.selected = null;
        renderInspector();
      } else {
        state.selected = null;
        renderInspector();
      }
    }
  }
  state.down = false;
  canvas.classList.remove('panning');
});
canvas.addEventListener('mouseleave', () => { hideTooltip(); state.hoverNode = null; state.hoverEdge = null; });
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  const m = canvasMouse(e);
  const factor = e.deltaY > 0 ? 0.88 : 1.13;
  const ns = Math.max(0.05, Math.min(4, cam.scale * factor));
  cam.px = m.x - (m.x - cam.px) * (ns / cam.scale);
  cam.py = m.y - (m.y - cam.py) * (ns / cam.scale);
  cam.scale = ns;
}, {passive:false});

document.getElementById('btn-zoom-in').addEventListener('click', () => {
  cam.scale = Math.min(4, cam.scale * 1.25);
});
document.getElementById('btn-zoom-out').addEventListener('click', () => {
  cam.scale = Math.max(0.05, cam.scale / 1.25);
});
document.getElementById('btn-fit').addEventListener('click', fit);
document.getElementById('btn-reset').addEventListener('click', fit);
document.getElementById('btn-clear').addEventListener('click', () => {
  state.selected = null; state.activeFlow = null; state.activeStep = -1; state.searchQuery = ''; searchInput.value = '';
  stopPlay(); syncFlowPanel(); renderStepBar(); renderInspector();
});

/* ---------------------------------------------------------------------
 * Boot
 * ------------------------------------------------------------------- */
function boot(){
  initHeader(); initChips(); initLegend(); initFlows();
  resize(); fit();
  renderInspector();
  raf = requestAnimationFrame(tick);
}
boot();
</script>
</body>
</html>"""

final_html = template.replace(
    "__TOPOLOGY_JSON__", json.dumps(top, indent=2, ensure_ascii=False)
)
Path("architecture.html").write_text(final_html, encoding="utf-8")
print("Wrote architecture.html successfully!")

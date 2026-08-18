(() => {
  'use strict';

  const TOPOLOGY_URL = 'system_topology.json';
  const LAYER_CONFIG = {
    infrastructure: {
      title: '1. Infrastructure & External Endpoints',
      desc: 'External feeds, network targets, native cores, and distribution infrastructure.',
      color: '#06b6d4',
      glow: 'rgba(6, 182, 212, .12)',
    },
    presentation: {
      title: '2. Presentation & User Interfaces',
      desc: 'CLI, bot, web, and browser-facing entry points into the platform.',
      color: '#8b5cf6',
      glow: 'rgba(139, 92, 246, .12)',
    },
    application: {
      title: '3. Application Orchestration',
      desc: 'Pipeline workers, queues, CI orchestration, merging, and runtime coordination.',
      color: '#f59e0b',
      glow: 'rgba(245, 158, 11, .12)',
    },
    domain: {
      title: '4. Domain Validation & Transformation',
      desc: 'Admission, parsing, security, testing, ranking, washing, and generation logic.',
      color: '#10b981',
      glow: 'rgba(16, 185, 129, .12)',
    },
    persistence: {
      title: '5. Persistence & Evidence Stores',
      desc: 'Caches, history, generated artifacts, evidence, and durable runtime state.',
      color: '#3b82f6',
      glow: 'rgba(59, 130, 246, .12)',
    },
  };

  const state = {
    topology: null,
    selectedNode: null,
    view: 'swimlanes',
    flowIndex: 0,
    flowStep: 0,
  };

  const byId = (id) => document.getElementById(id);

  function requireTopologyShape(topology) {
    if (!topology || typeof topology !== 'object') throw new Error('Topology is not a JSON object.');
    if (!Array.isArray(topology.nodes)) throw new Error('Topology nodes must be an array.');
    if (!Array.isArray(topology.edges)) throw new Error('Topology edges must be an array.');
    if (!Array.isArray(topology.flows)) throw new Error('Topology flows must be an array.');

    const nodeIds = new Set();
    topology.nodes.forEach((node, index) => {
      if (!node || typeof node !== 'object' || typeof node.id !== 'string' || !node.id) {
        throw new Error(`Node ${index} has no valid id.`);
      }
      if (nodeIds.has(node.id)) throw new Error(`Duplicate node id: ${node.id}`);
      nodeIds.add(node.id);
      if (!Object.hasOwn(LAYER_CONFIG, node.layer)) {
        throw new Error(`Unknown topology layer: ${String(node.layer)} (${node.id})`);
      }
    });

    topology.edges.forEach((edge, index) => {
      if (!edge || typeof edge !== 'object') throw new Error(`Edge ${index} is malformed.`);
      if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
        throw new Error(`Edge ${edge.id || index} has a dangling endpoint.`);
      }
    });

    topology.flows.forEach((flow, flowIndex) => {
      if (!flow || typeof flow !== 'object' || !Array.isArray(flow.steps)) {
        throw new Error(`Flow ${flowIndex} is malformed.`);
      }
      flow.steps.forEach((step, stepIndex) => {
        if (!step || typeof step !== 'object') throw new Error(`Flow ${flow.id || flowIndex} step ${stepIndex + 1} is malformed.`);
        if (!nodeIds.has(step.from) || !nodeIds.has(step.to)) {
          throw new Error(`Flow ${flow.id || flowIndex} step ${stepIndex + 1} has a dangling node reference.`);
        }
      });
    });
  }

  function textElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = text;
    return element;
  }

  function clearChildren(element) {
    element.replaceChildren();
  }

  function updateStats() {
    const topology = state.topology;
    byId('statNodes').textContent = String(topology.nodes.length);
    byId('statEdges').textContent = String(topology.edges.length);
    byId('statFlows').textContent = String(topology.flows.length);
    byId('statLayers').textContent = String(Object.keys(LAYER_CONFIG).length);
    byId('nodeSearch').placeholder = `Search ${topology.nodes.length} components…`;
  }

  function nodeTag(node) {
    const file = node.file_citations?.[0]?.file || '';
    if (file.endsWith('.go')) return 'GO';
    if (file.endsWith('.ts') || file.endsWith('.tsx')) return 'TS/PWA';
    if (file.endsWith('.js')) return 'JS/PWA';
    if (node.type === 'external') return 'EXTERNAL';
    return 'PYTHON';
  }

  function createNodeCard(node, layerConfig) {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'node-card';
    card.id = `node-${node.id}`;
    card.dataset.nodeId = node.id;
    card.style.setProperty('--lane-color', layerConfig.color);
    card.addEventListener('click', () => {
      if (state.view === 'blast') {
        simulateFailure(node.id);
      } else {
        openDrawer(node);
      }
    });

    const top = document.createElement('div');
    top.className = 'node-top';
    top.append(
      textElement('span', 'node-name', node.name || node.id),
      textElement('span', 'node-tag', nodeTag(node)),
    );

    const description = textElement('p', 'node-desc', node.description || 'No description.');
    const inbound = state.topology.edges.filter((edge) => edge.target === node.id).length;
    const outbound = state.topology.edges.filter((edge) => edge.source === node.id).length;
    const firstPort = node.runtime_config?.ports?.[0] || 'internal';
    const footer = document.createElement('div');
    footer.className = 'node-footer';
    footer.append(
      textElement('span', '', `↓ ${inbound} in`),
      textElement('span', '', `↑ ${outbound} out`),
      textElement('span', '', String(firstPort)),
    );
    card.append(top, description, footer);
    return card;
  }

  function renderSwimlanes() {
    const container = byId('swimlanesContainer');
    clearChildren(container);

    const grouped = Object.fromEntries(Object.keys(LAYER_CONFIG).map((key) => [key, []]));
    for (const node of state.topology.nodes) {
      if (!Object.hasOwn(grouped, node.layer)) {
        throw new Error(`Unknown topology layer: ${node.layer} (${node.id})`);
      }
      grouped[node.layer].push(node);
    }

    for (const [layerKey, config] of Object.entries(LAYER_CONFIG)) {
      const lane = document.createElement('section');
      lane.className = 'layer-lane';
      lane.dataset.layer = layerKey;
      lane.style.setProperty('--lane-color', config.color);
      lane.style.setProperty('--lane-glow', config.glow);

      const header = document.createElement('div');
      header.className = 'layer-header';
      const heading = document.createElement('div');
      heading.className = 'layer-heading';
      heading.append(textElement('span', 'layer-badge', layerKey.toUpperCase()));
      const copy = document.createElement('div');
      copy.append(textElement('h2', 'layer-title', config.title), textElement('p', 'layer-desc', config.desc));
      heading.append(copy);
      header.append(heading, textElement('span', 'layer-count', `${grouped[layerKey].length} components`));

      const grid = document.createElement('div');
      grid.className = 'node-grid';
      grouped[layerKey].forEach((node) => grid.append(createNodeCard(node, config)));
      lane.append(header, grid);
      container.append(lane);
    }
  }

  function setDrawerOpen(open) {
    const drawer = byId('nodeDrawer');
    drawer.classList.toggle('open', open);
    drawer.setAttribute('aria-hidden', String(!open));
    byId('backdrop').hidden = !open;
  }

  function openDrawer(node) {
    state.selectedNode = node;
    document.querySelectorAll('.node-card').forEach((card) => card.classList.remove('selected'));
    byId(`node-${node.id}`)?.classList.add('selected');

    byId('drawerBadge').textContent = String(node.layer || '').toUpperCase();
    byId('drawerTitle').textContent = node.name || node.id;
    byId('drawerId').textContent = `ID: ${node.id} (${node.type || 'component'})`;
    byId('drawerDesc').textContent = node.description || 'No description.';

    const citations = byId('drawerCitations');
    clearChildren(citations);
    for (const citation of node.file_citations || []) {
      const item = document.createElement('div');
      item.className = 'citation';
      const fileRow = document.createElement('div');
      fileRow.className = 'citation-file';
      const path = String(citation.file || 'unknown');
      fileRow.append(textElement('strong', '', path));
      const copyButton = textElement('button', 'copy-button', 'Copy path');
      copyButton.type = 'button';
      copyButton.addEventListener('click', async () => {
        try {
          if (!navigator.clipboard?.writeText) throw new Error('Clipboard API unavailable');
          await navigator.clipboard.writeText(path);
          copyButton.textContent = 'Copied';
        } catch (_error) {
          copyButton.textContent = 'Unavailable';
        }
      });
      fileRow.append(copyButton);
      item.append(fileRow);
      if (Array.isArray(citation.symbols) && citation.symbols.length) {
        item.append(textElement('div', 'citation-symbols', citation.symbols.join(', ')));
      }
      citations.append(item);
    }
    if (!citations.children.length) citations.append(textElement('div', 'muted', 'No citations recorded.'));

    const ports = node.runtime_config?.ports?.join(', ') || 'none';
    const env = node.runtime_config?.env_dependencies?.join(', ') || 'none';
    byId('drawerRuntime').textContent = `Ports: ${ports}\nEnvironment: ${env}`;

    const inbound = state.topology.edges.filter((edge) => edge.target === node.id).map((edge) => edge.source);
    const outbound = state.topology.edges.filter((edge) => edge.source === node.id).map((edge) => edge.target);
    const links = byId('drawerLinks');
    clearChildren(links);
    links.append(
      textElement('div', '', `Inbound from: ${inbound.join(', ') || 'none'}`),
      textElement('div', '', `Outbound to: ${outbound.join(', ') || 'none'}`),
    );
    setDrawerOpen(true);
  }

  function closeDrawer() {
    state.selectedNode = null;
    document.querySelectorAll('.node-card').forEach((card) => card.classList.remove('selected'));
    setDrawerOpen(false);
  }

  function handleSearch(query) {
    const normalized = query.trim().toLowerCase();
    document.querySelectorAll('.node-card').forEach((card) => {
      card.hidden = normalized !== '' && !card.textContent.toLowerCase().includes(normalized);
    });
  }

  function setView(view) {
    if (!['swimlanes', 'blast', 'flows'].includes(view)) return;
    state.view = view;
    document.querySelectorAll('.mode-tab').forEach((tab) => {
      tab.classList.toggle('active', tab.dataset.view === view);
    });
    byId('flowPanel').hidden = view !== 'flows';
    byId('blastBanner').hidden = view !== 'blast';
    clearFlowHighlights();
    clearBlast();
    if (view === 'flows') loadSelectedFlow(state.flowIndex);
  }

  function setupFlows() {
    const select = byId('flowSelect');
    clearChildren(select);
    state.topology.flows.forEach((flow, index) => {
      const option = document.createElement('option');
      option.value = String(index);
      option.textContent = `${index + 1}. ${flow.name || flow.id}`;
      select.append(option);
    });
    updateFlowButtons();
  }

  function currentFlow() {
    return state.topology.flows[state.flowIndex] || null;
  }

  function loadSelectedFlow(index) {
    const parsed = Number.parseInt(String(index), 10);
    state.flowIndex = Number.isNaN(parsed) ? 0 : Math.max(0, Math.min(parsed, state.topology.flows.length - 1));
    state.flowStep = 0;
    byId('flowSelect').value = String(state.flowIndex);
    renderFlowSteps();
  }

  function renderFlowSteps() {
    clearFlowHighlights();
    const flow = currentFlow();
    const steps = Array.isArray(flow?.steps) ? flow.steps : [];
    const track = byId('flowStepsTrack');
    clearChildren(track);

    steps.forEach((step, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'flow-step';
      button.classList.toggle('active', index === state.flowStep);
      const number = step.step_number ?? index + 1;
      button.textContent = `${number}. ${String(step.from).replaceAll('_', ' ')} → ${String(step.to).replaceAll('_', ' ')}`;
      button.addEventListener('click', () => setFlowStep(index));
      track.append(button);
    });

    if (!steps.length) {
      byId('flowStepCounter').textContent = 'Step 0 of 0';
      byId('flowStepNotes').textContent = 'This flow has no steps.';
      updateFlowButtons();
      return;
    }
    state.flowStep = Math.min(state.flowStep, steps.length - 1);
    renderActiveFlowStep();
  }

  function setFlowStep(index) {
    const steps = currentFlow()?.steps || [];
    if (!steps.length) return;
    state.flowStep = Math.max(0, Math.min(index, steps.length - 1));
    document.querySelectorAll('.flow-step').forEach((button, buttonIndex) => {
      button.classList.toggle('active', buttonIndex === state.flowStep);
    });
    renderActiveFlowStep();
  }

  function renderActiveFlowStep() {
    clearFlowHighlights();
    const flow = currentFlow();
    const steps = flow?.steps || [];
    const step = steps[state.flowStep];
    if (!step) return;

    byId('flowStepCounter').textContent = `Step ${state.flowStep + 1} of ${steps.length}`;
    [step.from, step.to].forEach((nodeId) => byId(`node-${nodeId}`)?.classList.add('flow-highlight'));
    byId(`node-${step.to}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    const notes = byId('flowStepNotes');
    clearChildren(notes);
    const rows = [
      ['Flow', flow.name || flow.id],
      ['Transition', `${step.from} → ${step.to}`],
      ['Action', step.action || 'n/a'],
      ['Payload', step.payload || 'n/a'],
      ['Source', step.file_citation || 'n/a'],
    ];
    rows.forEach(([label, value]) => {
      const row = document.createElement('div');
      row.append(textElement('strong', '', `${label}: `), document.createTextNode(String(value)));
      notes.append(row);
    });
    if (flow.description) notes.append(textElement('div', 'muted', flow.description));
    updateFlowButtons();
  }

  function updateFlowButtons() {
    const steps = currentFlow()?.steps || [];
    byId('flowPrev').disabled = !steps.length || state.flowStep <= 0;
    byId('flowNext').disabled = !steps.length || state.flowStep >= steps.length - 1;
  }

  function clearFlowHighlights() {
    document.querySelectorAll('.node-card').forEach((card) => card.classList.remove('flow-highlight'));
  }

  function downstreamFrom(rootId) {
    const impacted = new Set([rootId]);
    const queue = [rootId];
    while (queue.length) {
      const current = queue.shift();
      for (const edge of state.topology.edges) {
        if (edge.source === current && !impacted.has(edge.target)) {
          impacted.add(edge.target);
          queue.push(edge.target);
        }
      }
    }
    return impacted;
  }

  function simulateFailure(rootId) {
    setDrawerOpen(false);
    const impacted = downstreamFrom(rootId);
    document.querySelectorAll('.node-card').forEach((card) => {
      card.classList.toggle('blast-impacted', impacted.has(card.dataset.nodeId));
    });
    const percent = Math.round((impacted.size / state.topology.nodes.length) * 100);
    byId('blastDesc').textContent = `Failure point ${rootId}: ${impacted.size} of ${state.topology.nodes.length} nodes impacted (${percent}% cascade).`;
  }

  function clearBlast() {
    document.querySelectorAll('.node-card').forEach((card) => card.classList.remove('blast-impacted'));
    if (byId('blastDesc')) byId('blastDesc').textContent = 'Select a component to trace its downstream dependency cascade.';
  }

  function exportJSON() {
    const blob = new Blob([JSON.stringify(state.topology, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    try {
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'configstream_topology.json';
      anchor.click();
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  function bindEvents() {
    document.querySelectorAll('.mode-tab').forEach((tab) => {
      tab.addEventListener('click', () => setView(tab.dataset.view));
    });
    byId('nodeSearch').addEventListener('input', (event) => handleSearch(event.currentTarget.value));
    byId('flowSelect').addEventListener('change', (event) => loadSelectedFlow(event.currentTarget.value));
    byId('flowPrev').addEventListener('click', () => setFlowStep(state.flowStep - 1));
    byId('flowNext').addEventListener('click', () => setFlowStep(state.flowStep + 1));
    byId('clearBlast').addEventListener('click', clearBlast);
    byId('drawerClose').addEventListener('click', closeDrawer);
    byId('backdrop').addEventListener('click', closeDrawer);
    byId('drawerBlast').addEventListener('click', () => {
      if (!state.selectedNode) return;
      const nodeId = state.selectedNode.id;
      closeDrawer();
      setView('blast');
      simulateFailure(nodeId);
    });
    byId('exportButton').addEventListener('click', exportJSON);
    window.addEventListener('keydown', (event) => {
      if (event.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        event.preventDefault();
        byId('nodeSearch').focus();
      } else if (event.key === 'Escape') {
        closeDrawer();
      }
    });
  }

  async function init() {
    bindEvents();
    try {
      const response = await fetch(TOPOLOGY_URL, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status} while loading ${TOPOLOGY_URL}`);
      const topology = await response.json();
      requireTopologyShape(topology);
      state.topology = topology;
      updateStats();
      renderSwimlanes();
      setupFlows();
      setView('swimlanes');
    } catch (error) {
      const notice = byId('loadError');
      notice.hidden = false;
      byId('loadErrorText').textContent = error instanceof Error ? error.message : String(error);
      byId('swimlanesContainer').append(textElement('div', 'empty-state', 'Architecture data unavailable.'));
    }
  }

  document.addEventListener('DOMContentLoaded', init, { once: true });
})();

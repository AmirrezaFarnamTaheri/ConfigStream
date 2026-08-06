const MAX_RENDERED_ROWS = 250;
const state = { records: [], filtered: [], selected: null };

const byId = (id) => document.getElementById(id);
const stringValue = (value, fallback = 'unknown') => typeof value === 'string' && value.trim() ? value.trim() : fallback;
const sourceOf = (record) => stringValue(record.source_id || record.source || record.provenance?.source_id);
const trustOf = (record) => {
  const value = record.trust_status || record.source_trust || record.provenance?.trust_status;
  if (typeof value === 'string' && value.trim()) return value.trim().toLowerCase();
  if (record.trusted === true) return 'trusted';
  if (record.trusted === false) return 'untrusted';
  return 'unknown';
};
const workingOf = (record) => record.is_working === true ? 'working' : record.is_working === false ? 'not-working' : 'unknown';

function safeRecord(record) {
  return {
    protocol: stringValue(record.protocol),
    endpoint: `${stringValue(record.address)}:${Number.isInteger(record.port) ? record.port : 'unknown'}`,
    source: sourceOf(record),
    trust: trustOf(record),
    working: workingOf(record),
    latency_ms: Number.isFinite(Number(record.latency)) ? Number(record.latency) : null,
  };
}

async function fingerprint(value) {
  const bytes = new TextEncoder().encode(String(value || ''));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

function fillSelect(id, values) {
  const select = byId(id);
  for (const value of [...new Set(values)].sort()) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.append(option);
  }
}

function applyFilters() {
  const protocol = byId('protocolFilter').value;
  const source = byId('sourceFilter').value;
  const trust = byId('trustFilter').value;
  const working = byId('workingFilter').value;
  state.filtered = state.records.filter((record) =>
    (!protocol || stringValue(record.protocol) === protocol) &&
    (!source || sourceOf(record) === source) &&
    (!trust || trustOf(record) === trust) &&
    (!working || workingOf(record) === working));
  renderRows();
}

function renderRows() {
  const body = byId('evidenceRows');
  body.replaceChildren();
  const visible = state.filtered.slice(0, MAX_RENDERED_ROWS);
  for (const record of visible) {
    const safe = safeRecord(record);
    const row = document.createElement('tr');
    for (const value of [safe.protocol, safe.endpoint, safe.source, safe.trust, safe.working]) {
      const cell = document.createElement('td');
      cell.textContent = String(value);
      row.append(cell);
    }
    const action = document.createElement('td');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-secondary';
    button.textContent = 'Inspect';
    button.addEventListener('click', () => selectRecord(record));
    action.append(button);
    row.append(action);
    body.append(row);
  }
  const suffix = state.filtered.length > visible.length ? ` Showing first ${visible.length}.` : '';
  byId('evidenceCount').textContent = `${state.filtered.length} matching records.${suffix}`;
}

async function selectRecord(record) {
  state.selected = record;
  const safe = safeRecord(record);
  const uriFingerprint = await fingerprint(record.config);
  byId('previewBefore').textContent = JSON.stringify({...safe, config_sha256: uriFingerprint}, null, 2);
  renderAfterPreview();
}

function renderAfterPreview() {
  if (!state.selected) return;
  const before = safeRecord(state.selected);
  const label = byId('previewLabel').value.trim() || 'Reviewed ConfigStream record';
  byId('previewAfter').textContent = JSON.stringify({...before, local_label: label, transformation: 'metadata-only; URI unchanged'}, null, 2);
}

async function load() {
  const status = byId('evidenceStatus');
  try {
    const artifact = window.ConfigStreamArtifactState;
    if (!artifact) throw new Error('artifact verifier unavailable');
    await artifact.ready;
    if (!artifact.canDistribute()) throw new Error(artifact.state.reason || 'artifact verification failed');
    const records = await artifact.fetchVerifiedJson('proxies.json');
    if (!Array.isArray(records)) throw new Error('proxies.json must contain a list');
    state.records = records;
    state.filtered = records;
    const metadata = artifact.state.metadata || {};
    const manifest = artifact.state.manifest || {};
    byId('evidenceCommit').textContent = stringValue(manifest.source_commit, 'not declared');
    byId('evidenceGenerated').textContent = stringValue(metadata.last_updated_utc || metadata.generated_at, 'not declared');
    byId('evidenceWorking').textContent = String(Number(metadata.total_working || records.filter((record) => record.is_working === true).length));
    byId('evidenceFiles').textContent = String(Array.isArray(manifest.files) ? manifest.files.length : 0);
    fillSelect('protocolFilter', records.map((record) => stringValue(record.protocol)));
    fillSelect('sourceFilter', records.map(sourceOf));
    fillSelect('trustFilter', records.map(trustOf));
    for (const id of ['protocolFilter', 'sourceFilter', 'trustFilter', 'workingFilter']) byId(id).addEventListener('change', applyFilters);
    byId('previewLabel').addEventListener('input', renderAfterPreview);
    status.textContent = 'Verified artifact loaded. Unknown provenance fields remain explicitly labeled unknown.';
    renderRows();
  } catch (error) {
    status.textContent = `Evidence unavailable: ${error.message || error}`;
    state.records = [];
    state.filtered = [];
    renderRows();
  }
}

document.addEventListener('DOMContentLoaded', load, {once: true});

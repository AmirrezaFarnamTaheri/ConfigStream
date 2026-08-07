/**
 * Fail-closed distribution guard for ConfigStream release artifacts.
 * Public hosts require HTTPS plus a valid signed manifest. Each distributed
 * file is hash-checked against that manifest at the moment of use.
 */
(function initializeArtifactState(global) {
  'use strict';

  const GUARDED_CONTROL_SELECTOR = '[data-file]';
  const REQUIRED_CONTROL_FILES = ['metadata.json', 'health.json'];
  const ARTIFACT_ALIASES = new Map([
    ['api/proxies', 'proxies.json'],
    ['api/stats', 'metadata.json'],
  ]);
  const nativeFetch = global.fetch.bind(global);
  const verifiedFilePromises = new Map();
  const state = {
    status: 'checking',
    canDistribute: false,
    reason: 'Validating release artifact…',
    checkedAt: null,
    metadata: null,
    health: null,
    manifest: null,
  };

  function isLocalHost() {
    const hostname = String(global.location?.hostname || '').replace(/^\[|\]$/g, '').toLowerCase();
    if (!hostname || hostname === 'localhost' || hostname.endsWith('.localhost')) return true;
    if (hostname === '::1') return true;
    const parts = hostname.split('.').map(Number);
    return parts.length === 4 && parts.every(Number.isInteger) && parts[0] === 127;
  }

  function isPublicContext() {
    return !isLocalHost();
  }

  function statusBanner() {
    let banner = document.getElementById('artifactStatusBanner');
    if (banner) return banner;
    banner = document.createElement('div');
    banner.id = 'artifactStatusBanner';
    banner.setAttribute('role', 'status');
    banner.setAttribute('aria-live', 'polite');
    banner.style.cssText = [
      'position:sticky',
      'top:0',
      'z-index:10000',
      'padding:.65rem 1rem',
      'text-align:center',
      'font:600 .875rem/1.4 system-ui,sans-serif',
      'background:#4b5563',
      'color:#fff',
    ].join(';');
    document.body.prepend(banner);
    return banner;
  }

  function applyControlPolicy() {
    const blocked = !state.canDistribute;
    document.querySelectorAll(GUARDED_CONTROL_SELECTOR).forEach((control) => {
      if (blocked) {
        if (!control.dataset.artifactGuarded) {
          control.dataset.artifactGuarded = 'true';
          control.dataset.artifactOriginalTitle = control.getAttribute('title') || '';
          if ('disabled' in control) control.dataset.artifactOriginallyDisabled = String(Boolean(control.disabled));
        }
        control.setAttribute('aria-disabled', 'true');
        control.setAttribute('title', state.reason);
        if ('disabled' in control) control.disabled = true;
      } else if (control.dataset.artifactGuarded === 'true') {
        control.removeAttribute('aria-disabled');
        const originalTitle = control.dataset.artifactOriginalTitle || '';
        if (originalTitle) control.setAttribute('title', originalTitle);
        else control.removeAttribute('title');
        if ('disabled' in control && control.dataset.artifactOriginallyDisabled !== 'true') control.disabled = false;
        delete control.dataset.artifactGuarded;
        delete control.dataset.artifactOriginalTitle;
        delete control.dataset.artifactOriginallyDisabled;
      }
    });
  }

  function renderState() {
    const banner = statusBanner();
    banner.textContent = state.reason;
    banner.dataset.status = state.status;
    banner.style.background = state.canDistribute ? '#166534' : state.status === 'checking' ? '#4b5563' : '#991b1b';
    applyControlPolicy();
    global.dispatchEvent(new CustomEvent('configstream:artifact-state', { detail: { ...state } }));
  }

  function setState(next) {
    Object.assign(state, next, { checkedAt: new Date().toISOString() });
    if (next.status !== 'verified') verifiedFilePromises.clear();
    if (document.body) renderState();
    return { ...state };
  }

  function normalizeArtifactPath(value) {
    if (typeof value !== 'string') throw new Error('artifact path must be a string');
    const path = value.split(/[?#]/, 1)[0].trim();
    if (!path || path.startsWith('/') || path.includes('\\') || path.includes('\0')) {
      throw new Error(`unsafe artifact path: ${value}`);
    }
    const parts = path.split('/');
    if (parts.some((part) => !part || part === '.' || part === '..')) {
      throw new Error(`unsafe artifact path: ${value}`);
    }
    return parts.join('/');
  }

  function artifactUrl(path) {
    const root = global.ROOT_PATH || './';
    return `${root}${path}?cb=${Date.now()}`;
  }

  async function fetchBytes(path, accept = '*/*') {
    const response = await nativeFetch(artifactUrl(path), {
      cache: 'no-store',
      headers: { Accept: accept },
    });
    if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`);
    return {
      bytes: new Uint8Array(await response.arrayBuffer()),
      contentType: response.headers.get('content-type') || 'application/octet-stream',
    };
  }

  function parseJson(bytes, path) {
    try {
      return JSON.parse(new TextDecoder().decode(bytes));
    } catch (error) {
      throw new Error(`${path} is not valid JSON: ${error.message || error}`);
    }
  }

  function validateManifest(manifest) {
    if (!manifest || !Array.isArray(manifest.files)) throw new Error('artifact_manifest.json has no files list');
    const paths = new Set();
    for (const entry of manifest.files) {
      const path = normalizeArtifactPath(entry?.path);
      if (paths.has(path)) throw new Error(`artifact manifest contains duplicate path ${path}`);
      paths.add(path);
    }
    for (const required of REQUIRED_CONTROL_FILES) {
      if (!paths.has(required)) throw new Error(`artifact manifest does not cover ${required}`);
    }
    if (isPublicContext()) {
      if (global.location.protocol !== 'https:') throw new Error('public artifact distribution requires HTTPS');
      if (typeof manifest.source_commit !== 'string' || !/^[0-9a-f]{40}$/.test(manifest.source_commit)) {
        throw new Error('artifact manifest has no valid source commit');
      }
    }
  }

  async function validatePayloadIntegrity(manifest, path, bytes) {
    const entry = manifest.files.find((item) => item && item.path === path);
    if (!entry) throw new Error(`artifact manifest does not cover ${path}`);
    if (!Number.isInteger(entry.size_bytes) || entry.size_bytes !== bytes.byteLength) {
      throw new Error(`${path} size does not match the signed manifest`);
    }
    if (typeof entry.sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(entry.sha256)) {
      throw new Error(`${path} has no valid manifest digest`);
    }
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    const actual = Array.from(new Uint8Array(digest), (number) => number.toString(16).padStart(2, '0')).join('');
    if (actual !== entry.sha256) throw new Error(`${path} hash does not match the signed manifest`);
  }

  function validateHealth(health, metadata) {
    const working = Number(health?.total_working ?? metadata?.total_working ?? 0);
    if (health?.status !== 'ok') throw new Error(`artifact health is ${health?.status || 'unknown'}`);
    if (health?.schema_validated !== true) throw new Error('artifact was not schema validated');
    if (!Number.isFinite(working) || working <= 0) throw new Error('artifact contains no verified working proxies');
  }

  function validateFreshness(metadata) {
    const rawDate = metadata?.last_updated_utc || metadata?.generated_at;
    const generatedAt = new Date(rawDate);
    if (!rawDate || Number.isNaN(generatedAt.getTime())) throw new Error('metadata has no valid generation timestamp');
    const intervalHours = Number(metadata?.update_interval_hours || 4);
    if (!Number.isFinite(intervalHours) || intervalHours <= 0) throw new Error('metadata update interval is invalid');
    const maxAgeHours = Math.min(48, Math.max(12, intervalHours * 2));
    const ageMs = Date.now() - generatedAt.getTime();
    if (ageMs < -30 * 1000) throw new Error('metadata generation timestamp is in the future');
    if (ageMs > maxAgeHours * 60 * 60 * 1000) throw new Error(`artifact is older than ${maxAgeHours} hours`);
  }

  async function validateSignature(manifest) {
    const publicKey = global.CS_CONSTANTS?.PUBLIC_KEY;
    const verifier = global.Verifier;
    const keyConfigured = verifier && typeof verifier._isConfiguredPublicKey === 'function'
      ? verifier._isConfiguredPublicKey(publicKey)
      : false;
    if (!keyConfigured) {
      if (isPublicContext()) throw new Error('artifact signature verification key is not configured');
      return false;
    }
    if (!verifier || typeof verifier.verifyManifestSignature !== 'function') {
      throw new Error('artifact signature verifier is unavailable');
    }
    const result = await verifier.verifyManifestSignature(manifest);
    if (!result || result.verified !== true) throw new Error('artifact manifest is unsigned or invalid');
    return true;
  }

  async function fetchVerified(path) {
    const normalized = normalizeArtifactPath(path);
    if (!state.canDistribute || !state.manifest) throw new Error(state.reason || 'artifact verification failed');
    if (!verifiedFilePromises.has(normalized)) {
      const operation = (async () => {
        const result = await fetchBytes(normalized);
        await validatePayloadIntegrity(state.manifest, normalized, result.bytes);
        return { ...result, path: normalized };
      })().catch((error) => {
        verifiedFilePromises.delete(normalized);
        setState({
          status: 'blocked',
          canDistribute: false,
          reason: `Distribution disabled: ${error.message || error}`,
        });
        throw error;
      });
      verifiedFilePromises.set(normalized, operation);
    }
    return verifiedFilePromises.get(normalized);
  }

  async function fetchVerifiedJson(path) {
    const result = await fetchVerified(path);
    return parseJson(result.bytes, result.path);
  }

  function guardedArtifactPath(input) {
    const rawUrl = typeof input === 'string' || input instanceof URL ? String(input) : input?.url;
    if (!rawUrl) return null;
    let url;
    try {
      url = new URL(rawUrl, global.location.href);
    } catch (_error) {
      return null;
    }
    if (url.origin !== global.location.origin) return null;

    const rootUrl = new URL(global.ROOT_PATH || './', global.location.href);
    if (!url.pathname.startsWith(rootUrl.pathname)) return null;
    const relative = url.pathname.slice(rootUrl.pathname.length).replace(/^\/+/, '');
    if (!relative) return null;

    if (ARTIFACT_ALIASES.has(relative)) return ARTIFACT_ALIASES.get(relative);
    if (relative === 'api/diff/proxies') return '__unsigned_dynamic_proxy_diff__';
    if (['metadata.json', 'health.json', 'proxies.json'].includes(relative)) return relative;
    if (relative.startsWith('data/') && relative.endsWith('.json')) return relative;
    return null;
  }

  async function guardedFetch(input, init = undefined) {
    const method = String(init?.method || input?.method || 'GET').toUpperCase();
    const path = method === 'GET' ? guardedArtifactPath(input) : null;
    if (!path) return nativeFetch(input, init);

    if (state.status === 'checking' && api.ready) {
      await api.ready;
    }

    if (path === '__unsigned_dynamic_proxy_diff__') {
      if (isPublicContext()) {
        throw new Error('Unsigned dynamic proxy diffs are disabled in public artifact mode');
      }
      return nativeFetch(input, init);
    }

    if (!state.canDistribute) {
      if (isPublicContext()) throw new Error(state.reason || 'Artifact verification failed');
      return nativeFetch(input, init);
    }

    const result = await fetchVerified(path);
    return new Response(result.bytes, {
      status: 200,
      headers: {
        'content-type': result.contentType,
        'cache-control': 'no-store',
        'x-configstream-artifact-verified': '1',
      },
    });
  }

  function installVerifiedFetchGuard() {
    if (global.__CONFIGSTREAM_VERIFIED_FETCH_GUARD__) return;
    global.__CONFIGSTREAM_VERIFIED_FETCH_GUARD__ = true;
    global.fetch = guardedFetch;
  }

  async function downloadVerifiedArtifact(control) {
    const path = normalizeArtifactPath(control.dataset.file || '');
    const result = await fetchVerified(path);
    const blobUrl = URL.createObjectURL(new Blob([result.bytes], { type: result.contentType }));
    const anchor = document.createElement('a');
    anchor.href = blobUrl;
    anchor.download = control.getAttribute('download') || path.split('/').pop();
    anchor.hidden = true;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 0);
  }

  async function verify() {
    setState({ status: 'checking', canDistribute: false, reason: 'Validating release artifact…' });
    try {
      const [manifestResult, healthResult, metadataResult] = await Promise.all([
        fetchBytes('artifact_manifest.json', 'application/json'),
        fetchBytes('health.json', 'application/json'),
        fetchBytes('metadata.json', 'application/json'),
      ]);
      const manifest = parseJson(manifestResult.bytes, 'artifact_manifest.json');
      const health = parseJson(healthResult.bytes, 'health.json');
      const metadata = parseJson(metadataResult.bytes, 'metadata.json');
      validateManifest(manifest);
      await validateSignature(manifest);
      await Promise.all([
        validatePayloadIntegrity(manifest, 'health.json', healthResult.bytes),
        validatePayloadIntegrity(manifest, 'metadata.json', metadataResult.bytes),
      ]);
      validateHealth(health, metadata);
      validateFreshness(metadata);
      return setState({
        status: 'verified',
        canDistribute: true,
        reason: `Release controls verified from ${metadata.last_updated_utc || metadata.generated_at}. Files are rechecked when used.`,
        metadata,
        health,
        manifest,
      });
    } catch (error) {
      console.warn('[ArtifactState] Distribution disabled:', error);
      return setState({
        status: 'blocked',
        canDistribute: false,
        reason: `Distribution disabled: ${error.message || error}`,
      });
    }
  }

  document.addEventListener('click', (event) => {
    const control = event.target.closest(GUARDED_CONTROL_SELECTOR);
    if (!control) return;
    if (!state.canDistribute) {
      event.preventDefault();
      event.stopImmediatePropagation();
      setState({ status: 'blocked', canDistribute: false, reason: state.reason });
      return;
    }
    if (control.matches('a[download]')) {
      event.preventDefault();
      event.stopImmediatePropagation();
      downloadVerifiedArtifact(control).catch((error) => {
        console.warn('[ArtifactState] Verified download failed:', error);
      });
    }
  }, true);

  const api = {
    state,
    verify,
    verifyFile: async (path) => Boolean(await fetchVerified(path)),
    fetchVerified,
    fetchVerifiedJson,
    canDistribute: () => state.canDistribute,
    ready: null,
  };
  global.ConfigStreamArtifactState = api;

  const start = () => {
    renderState();
    api.ready = verify();
    installVerifiedFetchGuard();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})(window);

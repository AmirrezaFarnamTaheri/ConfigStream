// SPDX-License-Identifier: AGPL-3.0-or-later
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const guardSource = fs.readFileSync(
  path.join(__dirname, '../../frontend/assets/js/artifact-state.js'),
  'utf8',
);

async function runGuard({ allowUnsigned, signature = null, corruptMetadata = false }) {
  const timestamp = new Date().toISOString();
  const health = { status: 'ok', schema_validated: true, total_working: 1 };
  const metadata = { generated_at: timestamp, update_interval_hours: 4, total_working: 1 };
  const files = {
    'health.json': Buffer.from(JSON.stringify(health)),
    'metadata.json': Buffer.from(JSON.stringify(metadata)),
  };
  const manifest = {
    source_commit: 'a'.repeat(40),
    files: Object.entries(files).map(([filePath, bytes]) => ({
      path: filePath,
      size_bytes: bytes.length,
      sha256: crypto.createHash('sha256').update(bytes).digest('hex'),
    })),
  };
  if (signature !== null) manifest.manifest_signature = signature;
  const responses = {
    ...files,
    'artifact_manifest.json': Buffer.from(JSON.stringify(manifest)),
  };
  if (corruptMetadata) responses['metadata.json'] = Buffer.from('{}');

  const callbacks = new Map();
  const document = {
    readyState: 'loading',
    body: { prepend() {} },
    getElementById() { return null; },
    createElement() {
      return { dataset: {}, style: {}, setAttribute() {} };
    },
    querySelectorAll() { return []; },
    addEventListener(name, callback) { callbacks.set(name, callback); },
  };
  const window = {
    location: {
      hostname: 'pages.example',
      protocol: 'https:',
      origin: 'https://pages.example',
      href: 'https://pages.example/',
    },
    ROOT_PATH: 'https://pages.example/',
    CS_CONSTANTS: { PUBLIC_KEY: '', ALLOW_UNSIGNED_PAGES: allowUnsigned },
    fetch: async (url) => {
      const filePath = new URL(url).pathname.slice(1);
      const bytes = responses[filePath];
      return {
        ok: Boolean(bytes),
        status: bytes ? 200 : 404,
        headers: { get: () => 'application/json' },
        arrayBuffer: async () => Uint8Array.from(bytes || []).buffer,
      };
    },
    dispatchEvent() {},
  };
  vm.runInNewContext(guardSource, {
    window,
    document,
    crypto: crypto.webcrypto,
    CustomEvent: class CustomEvent {},
    TextDecoder,
    Uint8Array,
    URL,
    Response,
    console: { warn() {} },
  });
  callbacks.get('DOMContentLoaded')();
  return window.ConfigStreamArtifactState.ready;
}

test('explicit unsigned Pages policy permits a healthy hash-checked release', async () => {
  const state = await runGuard({ allowUnsigned: true });
  assert.equal(state.canDistribute, true);
  assert.equal(state.signatureVerified, false);
  assert.match(state.reason, /Unsigned release allowed by Pages policy/);
});

test('unsigned release is blocked without explicit policy', async () => {
  const state = await runGuard({ allowUnsigned: false });
  assert.equal(state.canDistribute, false);
  assert.match(state.reason, /verification key is not configured/);
});

test('signed release is blocked without a public key even when unsigned mode is allowed', async () => {
  const state = await runGuard({ allowUnsigned: true, signature: {} });
  assert.equal(state.canDistribute, false);
  assert.match(state.reason, /signed artifact cannot be verified without a public key/);
});

test('unsigned policy does not bypass payload integrity', async () => {
  const state = await runGuard({ allowUnsigned: true, corruptMetadata: true });
  assert.equal(state.canDistribute, false);
  assert.match(state.reason, /metadata\.json size does not match the artifact manifest/);
});

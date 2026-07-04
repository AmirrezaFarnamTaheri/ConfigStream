# SPDX-License-Identifier: AGPL-3.0-or-later
"""Browser verifier contract checks."""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_signed_artifacts_fail_closed_without_key_or_webcrypto() -> None:
    script = textwrap.dedent(f"""
        const fs = require('fs');
        const vm = require('vm');
        const verifierJs = fs.readFileSync({str(REPO_ROOT / "frontend/assets/js/verifier.js")!r}, 'utf8');

        async function runCase(hasCrypto, publicKey, signedObj) {{
          const statusEl = {{ textContent: '', style: {{}} }};
          const context = {{
            console,
            TextEncoder,
            Uint8Array,
            window: {{
              atob: (value) => Buffer.from(value, 'base64').toString('binary'),
              crypto: hasCrypto ? {{ subtle: {{}} }} : undefined,
              CS_CONSTANTS: {{ PUBLIC_KEY: publicKey }},
              document: {{ getElementById: () => statusEl }}
            }},
            self: {{}}
          }};
          context.window.window = context.window;
          context.window.self = context.window;
          vm.createContext(context);
          vm.runInContext(verifierJs, context);
          try {{
            const result = await context.window.Verifier.verifyConfig(signedObj);
            return {{ ok: true, result }};
          }} catch (error) {{
            return {{ ok: false, message: error.message }};
          }}
        }}

        (async () => {{
          const signed = {{ content: '{{"ok": true}}', signature: 'abcd' }};
          const unsigned = {{ content: '{{"ok": true}}' }};
          const placeholderKey = 'MCowBQYDK2VwAyEA79e/79e/79e/79e/79e/79e/79e/79e/79e/79e/79e=';

          const noCrypto = await runCase(false, 'real-public-key-material-12345', signed);
          const noKey = await runCase(true, '', signed);
          const placeholder = await runCase(true, placeholderKey, signed);
          const unsignedNoCrypto = await runCase(false, '', unsigned);

          if (noCrypto.ok || !noCrypto.message.includes('Web Crypto API not supported')) {{
            throw new Error('signed artifact did not fail closed without WebCrypto');
          }}
          if (noKey.ok || !noKey.message.includes('Public Key not configured')) {{
            throw new Error('signed artifact did not fail closed without public key');
          }}
          if (placeholder.ok || !placeholder.message.includes('Public Key not configured')) {{
            throw new Error('signed artifact did not fail closed with placeholder public key');
          }}
          if (!unsignedNoCrypto.ok || unsignedNoCrypto.result.ok !== true) {{
            throw new Error('unsigned local content should remain parseable without WebCrypto');
          }}
        }})().catch((error) => {{
          console.error(error.message);
          process.exit(1);
        }});
        """)

    subprocess.run(["node", "-e", script], cwd=REPO_ROOT, check=True)


def test_manifest_verification_fails_closed_on_signature_mismatch() -> None:
    script = textwrap.dedent(f"""
        const fs = require('fs');
        const vm = require('vm');
        const verifierJs = fs.readFileSync({str(REPO_ROOT / "frontend/assets/js/verifier.js")!r}, 'utf8');

        const subtle = {{
          importKey: async () => ({{}}),
          verify: async () => false
        }};
        const context = {{
          console,
          TextEncoder,
          Uint8Array,
          window: {{
            atob: (value) => Buffer.from(value, 'base64').toString('binary'),
            crypto: {{ subtle }},
            CS_CONSTANTS: {{ PUBLIC_KEY: 'MCowBQYDK2VwAyEA6Q2Ff2Q4NBRjEwQ3Wm4N8JjLEzY7D2l3Nw4uYfYjF8Q=' }}
          }},
          self: {{}}
        }};
        context.window.window = context.window;
        context.window.self = context.window;
        vm.createContext(context);
        vm.runInContext(verifierJs, context);

        (async () => {{
          try {{
            await context.window.Verifier.verifyManifestSignature({{
              schema_version: '1.0',
              generated_at: '2026-01-01T00:00:00Z',
              artifact_generated_at: '2026-01-01T00:00:00Z',
              trace_id: '-',
              file_count: 0,
              total_size_bytes: 0,
              files: [],
              manifest_signature: {{
                algorithm: 'ed25519',
                signature: '00'.repeat(64),
                key_id: 'sha256:0123456789abcdef'
              }}
            }});
            throw new Error('Expected manifest verification to fail closed');
          }} catch (error) {{
            if (!String(error.message).includes('signature mismatch')) {{
              throw error;
            }}
          }}
        }})().catch((error) => {{
          console.error(error.message);
          process.exit(1);
        }});
        """)

    subprocess.run(["node", "-e", script], cwd=REPO_ROOT, check=True)

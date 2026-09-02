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


def test_cross_language_signing_and_verification_parity() -> None:
    """Test full Ed25519 signing from Python verified by WebCrypto in Node."""
    import base64
    import json
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    from configstream.signer import Signer

    priv_key = ed25519.Ed25519PrivateKey.generate()
    seed_bytes = priv_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    spki_bytes = priv_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    spki_b64 = base64.b64encode(spki_bytes).decode("ascii")

    signer = Signer(seed_bytes.hex())

    # 1. Sign config / subscription
    content_obj = {"proxies": [{"name": "test-node", "port": 443}], "status": "active"}
    content_str = json.dumps(content_obj)
    signed_sub = signer.sign_subscription(content_str)

    # 2. Sign manifest
    manifest_obj = {
        "version": "3.2.0",
        "generated_at": 1725321600,
        "files": ["proxies.json", "metadata.json"],
        "nested": {"z": 100, "a": 200},
    }
    manifest_sig = signer.sign_manifest(manifest_obj)
    manifest_obj["manifest_signature"] = manifest_sig

    test_payload = {
        "spki_b64": spki_b64,
        "signed_sub": signed_sub,
        "manifest_obj": manifest_obj,
    }

    script = textwrap.dedent(f"""
        const fs = require('fs');
        const vm = require('vm');
        const crypto = require('crypto');
        const verifierJs = fs.readFileSync({str(REPO_ROOT / "frontend/assets/js/verifier.js")!r}, 'utf8');
        const data = {json.dumps(test_payload)};

        const context = {{
          console,
          TextEncoder,
          Uint8Array,
          window: {{
            atob: (val) => Buffer.from(val, 'base64').toString('binary'),
            crypto: crypto.webcrypto,
            CS_CONSTANTS: {{ PUBLIC_KEY: data.spki_b64 }}
          }},
          self: {{}}
        }};
        context.window.window = context.window;
        context.window.self = context.window;
        vm.createContext(context);
        vm.runInContext(verifierJs, context);

        (async () => {{
          // Positive vector 1: verifyConfig
          const verifiedSub = await context.window.Verifier.verifyConfig(data.signed_sub);
          if (!verifiedSub || verifiedSub.status !== 'active') {{
            throw new Error('verifyConfig failed to parse verified content');
          }}

          // Negative vector 1: tampered content in verifyConfig
          let failedTampered = false;
          try {{
            await context.window.Verifier.verifyConfig({{
              content: JSON.stringify({{ proxies: [], status: 'tampered' }}),
              signature: data.signed_sub.signature,
              timestamp: data.signed_sub.timestamp
            }});
          }} catch (e) {{
            failedTampered = true;
          }}
          if (!failedTampered) throw new Error('verifyConfig did not fail on tampered content');

          // Negative vector 2: tampered timestamp in verifyConfig
          let failedTimestamp = false;
          try {{
            await context.window.Verifier.verifyConfig({{
              content: data.signed_sub.content,
              signature: data.signed_sub.signature,
              timestamp: data.signed_sub.timestamp + 500
            }});
          }} catch (e) {{
            failedTimestamp = true;
          }}
          if (!failedTimestamp) throw new Error('verifyConfig did not fail on tampered timestamp');

          // Positive vector 2: verifyManifestSignature
          const manifestRes = await context.window.Verifier.verifyManifestSignature(data.manifest_obj);
          if (!manifestRes.verified) {{
            throw new Error('verifyManifestSignature failed on valid signed manifest');
          }}

          // Negative vector 3: tampered manifest field
          const tamperedManifest = JSON.parse(JSON.stringify(data.manifest_obj));
          tamperedManifest.version = '9.9.9';
          let failedManifest = false;
          try {{
            await context.window.Verifier.verifyManifestSignature(tamperedManifest);
          }} catch (e) {{
            failedManifest = true;
          }}
          if (!failedManifest) throw new Error('verifyManifestSignature did not fail on tampered manifest');

        }})().catch((error) => {{
          console.error(error.message);
          process.exit(1);
        }});
    """)

    subprocess.run(["node", "-e", script], cwd=REPO_ROOT, check=True)


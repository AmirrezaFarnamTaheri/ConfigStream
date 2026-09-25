# Repository secret inventory

Which repository secrets exist, who reads them, and what breaks when one is missing.
Reference this before adding or removing a secret: GitHub cannot return a secret's value
once set, so a rotation means re-entering it.

## Read by CI (referenced from a workflow)

| Secret | Read by | Effect if missing |
| :--- | :--- | :--- |
| `CS_SIGNING_PRIVATE_KEY_HEX` | `main.yml` (manifest signing in the pipeline and the release gate) | Manifests are unsigned, and with `allow_unsigned_pages: false` the deploy is rejected. Publication stops — loudly. |
| `CS_PUBLIC_KEY` | `main.yml`, `deploy-pages.yml` (trust anchor for verification and rollback) | A signed artifact is rejected for having no trust anchor, and `validate_frontend_placeholders.py --strict` fails the artifact. Publication stops. |
| `VT_API_KEY` | VirusTotal lookups during testing | Reputation checks degrade; testing continues. |
| `WARP_KEY_POOL` | WARP key material for the chain generator | Chain generation falls back to a default pool. |
| `CS_IPNS_KEY` | injected into `assets/js/runtime-config.js` only | Optional. `failover.js` logs that IPFS failover is skipped; no publication depends on it. |
| `MAXMIND_LICENSE_KEY` | `update-databases --geoip-only` | Intentional fallback: a sha256-pinned GeoLite mirror release is used instead, and CI still validates the mmdb database type. |
| `GITHUB_TOKEN` | automatic | Never configure manually. |

## Not read by CI (consumed by operator-run scripts only)

These are safe to keep and safe to rotate on your own schedule. As repository secrets they
are unreadable by any workflow, so they document intent rather than enable automation.

| Secret | Consumed by |
| :--- | :--- |
| `STEGO_KEY` | Local/private steganography processing. Must never reach a published artifact — `validate_frontend_placeholders.py` rejects any runtime config containing it. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Operator notification runs, not the release pipeline. |
| `GDRIVE_SA_JSON`, `CLIENT_EMAIL` | `scripts/upload_gdrive.py` (manual mirror upload). |
| `HF_TOKEN`, `HF_REPO_ID` | Manual Hugging Face dataset mirror upload. |
| `GH_PAT` | Operator tooling. Rotate it: a token pasted into a chat, issue, or log is compromised even if the repository is private. |

## Rotation notes

- **Signing key**: `CS_SIGNING_PRIVATE_KEY_HEX` and `CS_PUBLIC_KEY` must always be a
  matching pair; `scripts/preflight_release_inputs.py` fails the run when they disagree.
  Keep an operator-held backup of the seed — losing it means rotating the anchor, and
  clients only trust the `key_id` they were served.
- **PATs and tokens**: revoke on any suspected exposure, then re-issue. A token shared in a
  conversation is public.

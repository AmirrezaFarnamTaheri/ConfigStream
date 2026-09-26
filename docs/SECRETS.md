# Repository secret inventory

Which repository secrets exist, who reads them, and what breaks when one is missing.
Reference this before adding or removing a secret: GitHub cannot return a secret's value
once set, so a rotation means re-entering it.

**Availability contract: no secret below is a hard dependency.** When a secret is present
and valid, the project uses it. When it is absent, malformed, or only half-configured, the
project logs the reason and continues — it never stops publishing because an optional
credential is unavailable. `src/configstream/signing_config.py` implements this for the
signing keypair; the other consumers degrade locally.

## Read by CI (referenced from a workflow)

| Secret | Read by | If missing or invalid |
| :--- | :--- | :--- |
| `CS_SIGNING_PRIVATE_KEY_HEX` | `main.yml` (manifest signing) | Unsigned release; the banner says so. Publication continues. |
| `CS_PUBLIC_KEY` | `main.yml`, `deploy-pages.yml` (trust anchor) | Anchor ignored; unsigned release. A *signed* artifact with no valid anchor is still rejected. |
| `VT_API_KEY` | VirusTotal lookups during testing | Reputation checks degrade to unavailable; testing continues. |
| `WARP_KEY_POOL` | WARP key material for the chain generator | Chain generation falls back to a default pool. |
| `CS_IPNS_KEY` | injected into `assets/js/runtime-config.js` only | Optional. `failover.js` logs that IPFS failover is skipped. |
| `MAXMIND_LICENSE_KEY` | `update-databases --geoip-only` | Falls back to a sha256-pinned GeoLite mirror release; CI still validates the mmdb database type. |
| `GITHUB_TOKEN` | automatic | Never configure manually. |

## Not read by CI (consumed by operator-run scripts only)

These document intent for manual tooling. As repository secrets they are unreadable by any
workflow, so rotating them on your own schedule is safe and nothing in CI changes.

| Secret | Consumed by |
| :--- | :--- |
| `STEGO_KEY` | Local/private steganography processing. Must never reach a published artifact — `validate_frontend_placeholders.py` rejects any runtime config containing it. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Operator notification runs, not the release pipeline. |
| `GDRIVE_SA_JSON`, `CLIENT_EMAIL` | `scripts/upload_gdrive.py` (manual mirror upload). |
| `HF_TOKEN`, `HF_REPO_ID` | Manual Hugging Face dataset mirror upload. |
| `GH_PAT` | Operator tooling. Rotate it: a token pasted into a chat, issue, or log is compromised even if the repository is private. |

## Rotation notes

- **Signing key**: the two signing secrets are only used together, and only when they are
  valid and match. A rotation that goes wrong cannot wedge the release — the worst case is
  one unsigned release that the banner labels as unsigned. Keep an operator-held backup of
  the seed anyway, so a rotation does not silently downgrade trust.
- **PATs and tokens**: revoke on any suspected exposure, then re-issue. A token shared in a
  conversation is public.

# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import os
import httpx  # type: ignore
from pathlib import Path


def _extract_pinata_cid(payload: object) -> str:
    """Extract CID from Pinata legacy or v3 responses."""
    if isinstance(payload, dict):
        legacy_cid = payload.get("IpfsHash")
        if isinstance(legacy_cid, str) and legacy_cid.strip():
            return legacy_cid.strip()
        data = payload.get("data")
        if isinstance(data, dict):
            v3_cid = data.get("cid")
            if isinstance(v3_cid, str) and v3_cid.strip():
                return v3_cid.strip()
    raise RuntimeError("Pinata response missing CID")


def _pin_to_ipfs_legacy(filepath: str, jwt: str) -> str:
    """
    Pin to IPFS using legacy endpoint.
    Used for folder uploads and fallback compatibility.
    """
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    path_obj = Path(filepath)

    if path_obj.is_dir():
        files_payload = []
        open_files = []
        try:
            for item in path_obj.rglob("*"):
                if item.is_file():
                    # Relative path inside the directory
                    # Pinata expects (file, (filename, content))
                    f = open(item, "rb")
                    open_files.append(f)

                    # Construct relative path string for Pinata folder structure
                    rel_path = str(item.relative_to(path_obj.parent))

                    # ('file', (filename, file_object))
                    files_payload.append(("file", (rel_path, f)))

            headers = {"Authorization": f"Bearer {jwt}"}
            # Note: 'files' is a list of tuples for multiple files
            response = httpx.post(
                url, files=files_payload, headers=headers, timeout=300
            )

        finally:
            # Close file handles
            for f in open_files:
                f.close()

    else:
        # Single file
        with open(filepath, "rb") as f:
            single_file_payload = {"file": f}
            headers = {"Authorization": f"Bearer {jwt}"}
            response = httpx.post(
                url, files=single_file_payload, headers=headers, timeout=30
            )

    if response.status_code == 200:
        try:
            return _extract_pinata_cid(response.json())
        except ValueError as exc:
            raise RuntimeError(f"Legacy Pinata JSON parse failed: {exc}") from exc
    else:
        raise RuntimeError(f"Failed to pin to IPFS: {response.text}")


def _pin_single_file_v3(filepath: str, jwt: str) -> str:
    """Pin a single file via Pinata v3 upload API."""
    url = "https://uploads.pinata.cloud/v3/files"
    headers = {"Authorization": f"Bearer {jwt}"}

    with open(filepath, "rb") as f:
        files = {"file": (Path(filepath).name, f)}
        # Use public network so generated CID is directly consumable in gateway URLs.
        data = {"network": "public"}
        response = httpx.post(url, files=files, data=data, headers=headers, timeout=60)

    if response.status_code == 200:
        try:
            return _extract_pinata_cid(response.json())
        except ValueError as exc:
            raise RuntimeError(f"Pinata v3 JSON parse failed: {exc}") from exc
    raise RuntimeError(f"Pinata v3 upload failed: {response.text}")


def pin_to_ipfs(filepath: str, jwt: str) -> str:
    """
    Pins a file or directory to IPFS via Pinata.
    Returns the CID.
    """
    path_obj = Path(filepath)
    if path_obj.is_dir():
        # Pinata v3 upload endpoint currently does not support folder uploads.
        return _pin_to_ipfs_legacy(filepath, jwt)
    try:
        return _pin_single_file_v3(filepath, jwt)
    except Exception:
        # Fallback for backwards compatibility and transient v3 issues.
        return _pin_to_ipfs_legacy(filepath, jwt)


def publish_ipns(cid: str, ipns_key: str) -> None:
    """
    Publishes the new CID to IPNS.
    Requires a running IPFS node with the private key.
    """
    import subprocess  # nosec B404
    import shutil

    ipfs_bin = shutil.which("ipfs")
    if not ipfs_bin:
        print("Warning: 'ipfs' command not found. Skipping IPNS publish.")
        return

    print(f"Publishing {cid} to IPNS key {ipns_key}...")
    try:
        subprocess.run(  # nosec B603
            [ipfs_bin, "name", "publish", "--key", ipns_key, cid],
            check=True,
            timeout=300,
        )
        print("IPNS publish successful.")
    except Exception as e:
        print(f"Failed to publish to IPNS: {e}")


def update_dnslink(cid: str, domain: str, cf_token: str, zone_id: str):
    """
    Updates the DNSLink TXT record on Cloudflare.
    _dnslink.fallback.com -> dnslink=/ipfs/<CID>
    """
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {
        "Authorization": f"Bearer {cf_token}",
        "Content-Type": "application/json",
    }

    # First, find the record ID for _dnslink.<domain>
    params = {"name": f"_dnslink.{domain}", "type": "TXT"}
    resp = httpx.get(url, headers=headers, params=params, timeout=30)
    records = resp.json().get("result", [])

    if not records:
        print(f"No existing DNSLink record found for _dnslink.{domain}")
        return

    record_id = records[0]["id"]

    # Update the record
    update_url = f"{url}/{record_id}"
    payload = {
        "content": f"dnslink=/ipfs/{cid}",
        "name": f"_dnslink.{domain}",
        "type": "TXT",
        "ttl": 60,
    }

    update_resp = httpx.put(update_url, headers=headers, json=payload, timeout=30)
    if update_resp.status_code == 200:
        print(f"Successfully updated DNSLink for {domain} to {cid}")
    else:
        raise RuntimeError(f"Failed to update DNSLink: {update_resp.text}")


def _clean_secret(v: str) -> str:
    """Sanitize secret values by stripping whitespace and quotes."""
    v = v.strip() if isinstance(v, str) else v
    if (
        isinstance(v, str)
        and len(v) >= 2
        and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'"))
    ):
        return v[1:-1]
    return v


def main():
    parser = argparse.ArgumentParser(description="Publish config to IPFS/IPNS")
    parser.add_argument(
        "--file", required=True, help="Path to file or directory to publish"
    )
    parser.add_argument(
        "--pinata-jwt",
        default=os.environ.get("PINATA_JWT"),
        help="Pinata JWT Token (default: env PINATA_JWT)",
    )
    parser.add_argument(
        "--ipns-key",
        default=os.environ.get("IPNS_KEY"),
        help="IPNS Key Name/ID (default: env IPNS_KEY)",
    )
    parser.add_argument(
        "--cf-token",
        default=os.environ.get("CF_TOKEN"),
        help="Cloudflare API Token (default: env CF_TOKEN)",
    )
    parser.add_argument(
        "--cf-zone",
        default=os.environ.get("CF_ZONE_ID"),
        help="Cloudflare Zone ID (default: env CF_ZONE_ID)",
    )
    parser.add_argument("--domain", help="Domain for DNSLink (e.g., fallback.com)")

    # New flags for optional flows
    parser.add_argument(
        "--publish-ipns",
        action="store_true",
        help="Publish the pinned CID to IPNS using --ipns-key",
    )
    parser.add_argument(
        "--update-dnslink",
        action="store_true",
        help="Update DNSLink record using Cloudflare (--cf-token, --cf-zone, --domain)",
    )

    args = parser.parse_args()

    # Validate file/directory existence
    if not os.path.exists(args.file) or not os.access(args.file, os.R_OK):
        print(f"Error: Path not found or not readable: {args.file}")
        return

    # Sanitize secrets
    args.pinata_jwt = (
        _clean_secret(args.pinata_jwt) if args.pinata_jwt else args.pinata_jwt
    )
    args.ipns_key = _clean_secret(args.ipns_key) if args.ipns_key else args.ipns_key
    args.cf_token = _clean_secret(args.cf_token) if args.cf_token else args.cf_token
    args.cf_zone = _clean_secret(args.cf_zone) if args.cf_zone else args.cf_zone

    # Validate Pinata JWT
    if not args.pinata_jwt:
        print(
            "Error: Missing required Pinata JWT. Provide via --pinata-jwt or PINATA_JWT env."
        )
        return

    try:
        print(f"Pinning {args.file} to IPFS...")
        cid = pin_to_ipfs(args.file, args.pinata_jwt)
        print(f"Pinned with CID: {cid}")

        if args.publish_ipns:
            if not args.ipns_key:
                print("Error: --publish-ipns requires --ipns-key or IPNS_KEY env")
                return
            publish_ipns(cid, args.ipns_key)

        if args.update_dnslink:
            if not (args.cf_token and args.cf_zone and args.domain):
                print(
                    "Error: --update-dnslink requires --cf-token, --cf-zone, and --domain"
                )
                return
            update_dnslink(cid, args.domain, args.cf_token, args.cf_zone)

    except Exception as e:
        err_msg = str(e)
        secrets = [args.pinata_jwt, args.cf_token]
        for s in secrets:
            if s and s.strip() and s.strip() in err_msg:
                err_msg = err_msg.replace(s.strip(), "[REDACTED]")
        print(f"Error: {err_msg}")


if __name__ == "__main__":
    main()

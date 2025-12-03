import argparse
import os
import sys
import requests  # type: ignore


def pin_to_ipfs(filepath: str, jwt: str) -> str:
    """
    Pins a file to IPFS via Pinata.
    Returns the IPFS Hash (CID).
    """
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"

    with open(filepath, "rb") as f:
        files = {"file": f}
        headers = {"Authorization": f"Bearer {jwt}"}
        response = requests.post(url, files=files, headers=headers)

    if response.status_code == 200:
        return str(response.json()["IpfsHash"])
    else:
        raise Exception(f"Failed to pin to IPFS: {response.text}")


def publish_ipns(cid: str, ipns_key: str) -> None:
    """
    Publishes the new CID to IPNS.
    Requires a running IPFS node with the private key.
    """
    import subprocess
    import shutil

    if not shutil.which("ipfs"):
        print("Warning: 'ipfs' command not found. Skipping IPNS publish.")
        return

    print(f"Publishing {cid} to IPNS key {ipns_key}...")
    try:
        subprocess.run(
            ["ipfs", "name", "publish", "--key", ipns_key, cid], check=True, timeout=300
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
    resp = requests.get(url, headers=headers, params=params)
    records = resp.json()["result"]

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

    update_resp = requests.put(update_url, headers=headers, json=payload)
    if update_resp.status_code == 200:
        print(f"Successfully updated DNSLink for {domain} to {cid}")
    else:
        raise Exception(f"Failed to update DNSLink: {update_resp.text}")


def main():
    parser = argparse.ArgumentParser(description="Publish config to IPFS/IPNS")
    parser.add_argument("--file", required=True, help="Path to file to publish")
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

    args = parser.parse_args()

    try:
        if args.pinata_jwt:
            print(f"Pinning {args.file} to IPFS...")
            cid = pin_to_ipfs(args.file, args.pinata_jwt)
            print(f"Pinned with CID: {cid}")

            if args.ipns_key:
                publish_ipns(cid, args.ipns_key)

            if args.cf_token and args.cf_zone and args.domain:
                update_dnslink(cid, args.domain, args.cf_token, args.cf_zone)
        else:
            print("No Pinata JWT provided. Skipping IPFS publish.")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

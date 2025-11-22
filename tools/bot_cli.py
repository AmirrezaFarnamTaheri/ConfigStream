import click
import os
import json
import random
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization

@click.group()
def cli():
    """ConfigStream Bot Automation Tools"""
    pass

@cli.command()
@click.option("--count", default=1, help="Number of keys to generate")
def generate_warp(count):
    """Generate Cloudflare WARP keys (Curve25519) for the pool."""
    keys = []
    for _ in range(count):
        # Generate Private Key
        priv = x25519.X25519PrivateKey.generate()
        pub = priv.public_key()

        # Serialize to Base64/Hex as needed by WireGuard
        # WireGuard uses Base64 for keys
        import base64

        priv_bytes = priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_bytes = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        keys.append({
            "private_key": base64.b64encode(priv_bytes).decode('utf-8'),
            "peer_public_key": base64.b64encode(pub_bytes).decode('utf-8'),
            # Note: Real WARP registration requires an API call to Cloudflare to register the pubkey.
            # This generates VALID KEYPAIRS but they need to be registered.
            # The user instructions should clarify this or we implement the API call.
            # For "Zero Budget", we assume user dumps registered keys here or we use a script.
            "reserved": [0, 0, 0]
        })

    print(json.dumps(keys, indent=2))
    click.echo("Copy this JSON to WARP_KEY_POOL secret.")

@cli.command()
@click.argument("output_dir", type=click.Path(exists=True))
def mirror_stats(output_dir):
    """Print stats for the bot to consume."""
    meta_path = Path(output_dir) / "metadata.json"
    if meta_path.exists():
        with open(meta_path) as f:
            data = json.load(f)
        print(f"Active: {data.get('total_working')}")
        print(f"Updated: {data.get('last_updated_utc')}")
    else:
        print("No metadata found.")

if __name__ == "__main__":
    cli()

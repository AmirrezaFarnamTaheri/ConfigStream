import asyncio
import orjson
import subprocess
import os
import sys

async def verify_go_tester():
    # Build a sample proxy config (VMess or similar)
    # Using a dummy config that might fail connection but should be parsed correctly
    sample_config = {
        "type": "vmess",
        "tag": "proxy",
        "server": "example.com",
        "server_port": 443,
        "uuid": "b831381d-6324-4d53-ad4f-8cda48b30811",
        "security": "auto"
    }

    config_str = orjson.dumps(sample_config).decode()

    # NDJSON input
    payload = {
        "id": "test-1",
        "config": config_str,
        "check_honeypot": False
    }

    input_data = orjson.dumps(payload).decode() + "\n"

    # Path to binary
    binary_path = "./src/go/tester/configstream-tester"
    if not os.path.exists(binary_path):
        print(f"Binary not found at {binary_path}")
        return

    print(f"Running binary: {binary_path}")
    process = subprocess.Popen(
        [binary_path, "-workers", "1", "-timeout", "5"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout, stderr = process.communicate(input=input_data)

    print("STDOUT:", stdout)
    print("STDERR:", stderr)

    if not stdout.strip():
        print("No output received!")
        return

    try:
        result = orjson.loads(stdout)
        print("Parsed Result:", result)
        if result["id"] == "test-1":
            print("SUCCESS: ID matched.")
            if "is_working" in result:
                print("SUCCESS: Response structure matches.")
            else:
                print("FAILURE: Missing is_working field.")
        else:
            print(f"FAILURE: ID mismatch. Expected test-1, got {result.get('id')}")
    except Exception as e:
        print(f"JSON Decode Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_go_tester())

import json
from pathlib import Path

schema_path = Path(__file__).parent / "schema" / "proxy.schema.json"

with open(schema_path, "r") as f:
    data = json.load(f)

data["additionalProperties"] = True

with open(schema_path, "w") as f:
    json.dump(data, f, indent=2)

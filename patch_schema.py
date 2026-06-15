import json

with open("schema/proxy.schema.json", "r") as f:
    data = json.load(f)

data["additionalProperties"] = True

with open("schema/proxy.schema.json", "w") as f:
    json.dump(data, f, indent=2)

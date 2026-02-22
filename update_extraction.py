import sys
import re

file_path = "src/configstream/parsers/extraction.py"

with open(file_path, "r") as f:
    content = f.read()

# Update imports
if "from .decoders import safe_b64_decode" in content:
    content = content.replace(
        "from .decoders import safe_b64_decode",
        "from .decoders import safe_b64_decode, validate_b64_input"
    )

# Update Regex
old_regex = r'r"\b(?P<host>(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}):(?P<port>\d{1,5})\b"'
new_regex = r'r"\b(?P<host>(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})|(?:0x[0-9a-fA-F]+)|(?:0[0-7]+)):(?P<port>\d{1,5})\b"'

# Simple string replace might fail due to whitespace/formatting, let's try strict replace first
# Actually, the original file has line break in regex definition?
# Based on `head` output:
# _IPV4_PORT_PATTERN = re.compile(
#     r"\b(?P<host>(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}):(?P<port>\d{1,5})\b"
# )

# I will find the start of definition and replace until the end parenthesis.
start_marker = '_IPV4_PORT_PATTERN = re.compile('
end_marker = ')'

start_idx = content.find(start_marker)
if start_idx != -1:
    end_idx = content.find(end_marker, start_idx) + 1
    # Check if correct block
    if end_idx > start_idx:
        # Construct new block
        new_block = '_IPV4_PORT_PATTERN = re.compile(\n    r"\\b(?P<host>(?:(?:25[0-5]|2[0-4]\\d|1?\\d?\\d)(?:\\.(?:25[0-5]|2[0-4]\\d|1?\\d?\\d)){3})|(?:0x[0-9a-fA-F]+)|(?:0[0-7]+)):(?P<port>\\d{1,5})\\b"\n)'
        content = content[:start_idx] + new_block + content[end_idx:]
    else:
        print("Could not find end of regex definition")
else:
    print("Could not find start of regex definition")

with open(file_path, "w") as f:
    f.write(content)

print("Updated extraction.py")

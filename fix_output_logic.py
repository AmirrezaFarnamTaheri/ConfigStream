lines = []
with open('src/configstream/output_logic.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # Detect the specific broken sequence
    if "total_revived_count = revived_warp + revived_vwarp" in line:
        # Check previous line
        if i > 0 and lines[i-1].strip() == "else:":
            # Indent it
            indent = lines[i-1][:lines[i-1].find("else:")] + "    "
            new_lines.append(indent + line.lstrip())
            continue
    new_lines.append(line)

with open('src/configstream/output_logic.py', 'w') as f:
    f.writelines(new_lines)

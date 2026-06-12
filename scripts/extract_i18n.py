import json
import re
import os

i18n_path = "D:/GitHub/ConfigStream/frontend/assets/js/i18n.js"
output_dir = "D:/GitHub/ConfigStream/frontend/assets/i18n"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

with open(i18n_path, "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
content = re.sub(r"//.*", "", content)

match = re.search(
    r"const translations = (\{.*?\});\s*(?=function|const|let|var|$)",
    content,
    re.DOTALL | re.MULTILINE,
)
if not match:
    match = re.search(r"const translations = (\{.*?\});(?!\s*\{)", content, re.DOTALL)

if match:
    js_obj_str = match.group(1).strip()
    # Remove outer braces
    if js_obj_str.startswith("{") and js_obj_str.endswith("}"):
        js_obj_str = js_obj_str[1:-1].strip()

    # Split by lang: { ... }
    # This is better: find "en: {" and match until the matching "}"

    def find_matching_brace(s, start_index):
        count = 0
        for i in range(start_index, len(s)):
            if s[i] == "{":
                count += 1
            elif s[i] == "}":
                count -= 1
                if count == 0:
                    return i
        return -1

    lang_matches = re.finditer(r"([a-z]{2}):\s*\{", js_obj_str)
    for m in lang_matches:
        lang_code = m.group(1)
        start_idx = m.end() - 1  # at {
        end_idx = find_matching_brace(js_obj_str, start_idx)

        if end_idx != -1:
            dict_str = js_obj_str[start_idx : end_idx + 1]
            # Quote keys
            dict_str = re.sub(
                r"^\s+([a-zA-Z0-9._]+):", r'  "\1":', dict_str, flags=re.MULTILINE
            )
            # Fix trailing commas
            dict_str = re.sub(r",\s*([\]\}])", r"\1", dict_str)

            try:
                json_data = json.loads(dict_str)
                with open(
                    f"{output_dir}/{lang_code}.json", "w", encoding="utf-8"
                ) as out:
                    json.dump(json_data, out, indent=4, ensure_ascii=False)
                print(f"Extracted {lang_code}.json")
            except Exception as e:
                print(f"Failed to parse {lang_code}: {e}")
else:
    print("Could not find translations object")

import json
import sys

from keywords_listener import UNUSED_FILE_PATH

if not UNUSED_FILE_PATH.exists():
    print("No unused_keywords.json found.")
    sys.exit(0)

# Load
with UNUSED_FILE_PATH.open("r", encoding="utf-8") as f:
    data = json.load(f)

if not data:
    print("🎉 All keywords are used!")
    sys.exit(0)

print("## ❗ Unused Robot Framework Keywords\n")
print("| Keyword | Source | Type | Class |")
print("|---------|---------|------|--------|")
for kw_name, info in data.items():
    source = info.get("source", "")
    typ = info.get("type", "")
    cls = info.get("class", "")

    print(f"| {kw_name} | {source} | {typ} | {cls} |")

sys.exit(1)

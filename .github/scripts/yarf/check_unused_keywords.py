"""
This script check any unused keywords and exit the program with code 1 else 0.
"""

import json
import sys
from pathlib import Path

from tabulate import tabulate

UNUSED_FILE_PATH = Path("keywords_coverage.json")

if not UNUSED_FILE_PATH.exists():
    print("No unused_keywords.json found.")
    sys.exit(0)

# Load
with UNUSED_FILE_PATH.open("r", encoding="utf-8") as f:
    data = json.load(f)

if len(data) == 0:
    print("🎉 All keywords are used!")
    sys.exit(0)

print("❗ Unused Robot Framework Keywords\n")
table = []
count = 0
for kw, info in data.items():
    if info.get("is_keyword"):
        table.append(
            [kw, info.get("source"), info.get("type"), info.get("class")]
        )
        count += 1

print(
    tabulate(
        table,
        headers=["Keyword", "Source", "Type", "Class"],
        tablefmt="github",
    )
)

print(f"{count} keyword(s) missed!")

sys.exit(1)

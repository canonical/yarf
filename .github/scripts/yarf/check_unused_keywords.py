"""
This script check any unused keywords and exit the program with code 1 else 0.
"""

import json
import sys
from pathlib import Path

from tabulate import tabulate

UNUSED_FILE_PATH = Path("unused_keywords.json")

if not UNUSED_FILE_PATH.exists():
    print("No unused_keywords.json found.")
    sys.exit(0)

# Load
with UNUSED_FILE_PATH.open("r", encoding="utf-8") as f:
    data = json.load(f)

if not data:
    print("🎉 All keywords are used!")
    sys.exit(0)

print("❗ Unused Robot Framework Keywords\n")
table = [
    [kw, info["source"], info["type"], info["class"]]
    for kw, info in data.items()
]
print(
    tabulate(
        table,
        headers=["Keyword", "Source", "Type", "Class"],
        tablefmt="github",
    )
)

sys.exit(1)

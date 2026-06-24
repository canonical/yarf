"""
Merge per-suite keywords_coverage.json files from a matrix run.

Each suite writes a file listing keywords that were *not* used by that
suite. A keyword is overall unused iff it is unused by every suite, i.e.
the intersection (by key) of all per-suite files.
"""

import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "coverage-artifacts")
files = sorted(root.rglob("keywords_coverage.json"))

if not files:
    print(
        f"No keywords_coverage.json files found under {root}", file=sys.stderr
    )
    sys.exit(1)

print(f"Merging {len(files)} coverage files:")
for f in files:
    print(f"  - {f}")

merged: dict | None = None
for f in files:
    with f.open(encoding="utf-8") as fh:
        data = json.load(fh)
    merged = (
        data
        if merged is None
        else {k: v for k, v in merged.items() if k in data}
    )

with Path("keywords_coverage.json").open("w", encoding="utf-8") as fh:
    json.dump(merged, fh, indent=2, ensure_ascii=False)

print(f"Wrote keywords_coverage.json with {len(merged)} entries.")

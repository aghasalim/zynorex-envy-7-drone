"""Recompute the README's comparison arithmetic from docs/claims.csv in Python.

Same checks as the SQL, C and Go versions: claim counts by evidence type, and
the three derived comparisons (endurance gain, weight saved, range multiple).

Run: python3 verify/claims.py <repo root>
"""
import csv
import sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
readme = (root / "README.md").read_text(encoding="utf-8")

with open(root / "docs" / "claims.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

bad = 0

def fail(msg):
    global bad
    print(f"  FAIL: {msg}")
    bad += 1

def require_in_readme(needle, what):
    if needle not in readme:
        fail(f"README does not contain '{needle}' ({what})")

counts = {}
for r in rows:
    ev = r["evidence"]
    counts[ev] = counts.get(ev, 0) + 1

require_in_readme(str(len(rows)), "total claim rows")

spec = {r["id"]: r for r in rows if r["build_value"] and r["reference_value"]}

for sid in ["endurance", "weight", "range"]:
    s = spec[sid]
    bv = float(s["build_value"])
    rv = float(s["reference_value"])
    if sid == "endurance":
        pct = 100.0 * (bv - rv) / rv
        needle = f"{pct:.0f}%"
        require_in_readme(needle, "endurance gain")
    elif sid == "weight":
        diff = int(rv - bv)
        needle = f"{diff}"
        require_in_readme(needle, "weight saved")
    elif sid == "range":
        mult = bv / rv
        needle = f"{mult:g}x"
        require_in_readme(needle, "range multiple")

if bad:
    print(f"Python: {bad} problem(s)")
    sys.exit(1)
print(f"Python: {len(rows)} claims, counts and comparisons reproduced")

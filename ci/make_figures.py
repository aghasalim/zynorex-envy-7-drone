"""Draw the evidence-status figure for the README.

This repository documents a build. Its headline numbers are design targets from
the build spec, not results re-derived from an attached test log, and the README
says so in prose. This renders that distinction so it cannot be skimmed past.

Nothing here is a measurement. The figure's only job is to state which claims are
backed by what, and every entry is sourced from the README's own status list.

    python ci/make_figures.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

#: Every claim, its value and what backs it, read from the machine readable
#: table the README and this figure are both drawn from. Evidence classes are
#: deliberately coarse: either a number came off a test log, or it came off the
#: build spec. verify/ recomputes this file's counts in five other languages.
CLAIMS = [
    (row["claim"], row["value"], row["evidence"])
    for row in csv.DictReader(
        (ROOT / "docs" / "claims.csv").open(encoding="utf-8")
    )
]

STYLE = {
    "spec": ("#f4a582", "design target from the build spec"),
    "component": ("#9ecae1", "component rating from its datasheet"),
    "documented": ("#1a9850", "written out in this repository"),
    "missing": ("#b2182b", "open item, not yet measured"),
}


def evidence(out: Path) -> Path:
    """Render every claim against what backs it."""
    figure, ax = plt.subplots(figsize=(11, 0.5 * len(CLAIMS) + 2.0))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(CLAIMS) + 1.4)

    for index, (claim, value, kind) in enumerate(reversed(CLAIMS)):
        y = index + 0.5
        colour, _ = STYLE[kind]
        ax.add_patch(plt.Rectangle((0.01, y - 0.28), 0.012, 0.56, color=colour))
        ax.text(0.04, y, claim, va="center", fontsize=10, color="0.15")
        ax.text(0.44, y, value, va="center", fontsize=10, family="monospace",
                color=colour if kind == "missing" else "0.3")
        ax.text(0.70, y, STYLE[kind][1], va="center", fontsize=8.5, color="0.5")

    spec = sum(1 for _, _, k in CLAIMS if k == "spec")
    missing = sum(1 for _, _, k in CLAIMS if k == "missing")
    ax.set_title(
        f"Nothing here has been re-derived from a flight log. "
        f"{spec} headline numbers are design targets\n"
        f"and {missing} items are open. That is the state of the build, "
        "stated rather than implied.",
        fontsize=10, pad=14,
    )
    figure.tight_layout()
    figure.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(figure)
    return out


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    print(f"-> {evidence(DOCS / 'evidence.png').relative_to(ROOT)}")


if __name__ == "__main__":
    main()

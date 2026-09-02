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
import re
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



#: Where each node in the wiring flowchart sits when it is drawn. The positions
#: are a layout choice; the nodes and the edges between them are read out of the
#: README so this figure cannot drift from the diagram it illustrates.
WIRING_POS = {
    "TX":  (0.06, 7.05), "RX":  (0.06, 5.75), "GS":  (0.06, 2.15),
    "FC":  (0.25, 4.55), "ESP": (0.25, 3.05),
    "BAT": (0.72, 7.05), "PDB": (0.72, 5.75), "BEC": (0.40, 5.75),
    "ESC1": (0.50, 4.55), "ESC2": (0.63, 4.55),
    "ESC3": (0.76, 4.55), "ESC4": (0.89, 4.55),
    "M1": (0.50, 3.05), "M2": (0.63, 3.05),
    "M3": (0.76, 3.05), "M4": (0.89, 3.05),
}

WIRING_CLASS = {
    "power": ("#b2182b", ["BAT", "PDB", "BEC", "ESC1", "ESC2", "ESC3", "ESC4",
                          "M1", "M2", "M3", "M4"]),
    "logic": ("#2166ac", ["FC", "ESP"]),
    "radio": ("#4d4d4d", ["TX", "RX", "GS"]),
}


def read_wiring():
    """Pull the node labels and the edges out of the README's flowchart.

    The diagram in the README is the source. If a node is added there and not
    given a position here, this raises rather than drawing a partial diagram.
    """
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    block = re.search(r"```mermaid\n(.*?)```", text, re.S).group(1)

    labels = {}
    for node, label in re.findall(r'^\s*([A-Za-z0-9_]+)\["(.*?)"\]', block, re.M):
        labels[node] = label.replace("<br/>", "\n")

    edges = []
    arrow = r"(==>|-->|<--.*?-->|--.*?-->|-\..*?\.->)"
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z0-9_& ]+?)\s*" + arrow + r"\s*([A-Za-z0-9_& ]+)$",
                     line.strip())
        if not m:
            continue
        kind = "power" if m.group(2) == "==>" else "signal"
        for a in (x.strip() for x in m.group(1).split("&")):
            for b in (x.strip() for x in m.group(3).split("&")):
                edges.append((a, b, kind))

    missing = {n for e in edges for n in e[:2]} - set(WIRING_POS)
    if missing:
        raise SystemExit(f"no drawn position for {sorted(missing)}")
    return labels, edges


def wiring(out: Path) -> Path:
    """Draw the wiring flowchart as a static figure."""
    labels, edges = read_wiring()
    colour = {}
    for _kind, (col, names) in WIRING_CLASS.items():
        for n in names:
            colour[n] = col

    figure, ax = plt.subplots(figsize=(12, 7.6))
    ax.axis("off")
    ax.set_xlim(0, 1.0)
    ax.set_ylim(1.5, 7.7)

    half_w, half_h = 0.058, 0.30

    for a, b, kind in edges:
        x1, y1 = WIRING_POS[a]
        x2, y2 = WIRING_POS[b]
        dy = -half_h if y2 < y1 else (half_h if y2 > y1 else 0)
        rad = 0.0 if kind == "power" else (-0.22 if y2 == y1 else 0.12)
        ax.annotate(
            "", xy=(x2, y2 - dy), xytext=(x1, y1 + dy),
            arrowprops=dict(
                arrowstyle="-|>", shrinkA=2, shrinkB=2,
                connectionstyle=f"arc3,rad={rad}",
                linewidth=2.6 if kind == "power" else 1.0,
                color="#b2182b" if kind == "power" else "#4d4d4d",
                linestyle="-" if kind == "power" else (0, (4, 2)),
                alpha=0.9 if kind == "power" else 0.75,
            ),
        )

    for node, (x, y) in WIRING_POS.items():
        col = colour[node]
        ax.add_patch(plt.Rectangle(
            (x - half_w, y - half_h), half_w * 2, half_h * 2,
            facecolor=col, edgecolor="none", zorder=3))
        ax.text(x, y, labels.get(node, node), ha="center", va="center",
                fontsize=6.6, color="white", zorder=4, linespacing=1.35)

    ax.set_title(
        "Power and signal path, drawn from the flowchart in the README.\n"
        "Solid heavy edges carry current, dashed edges carry signal. "
        "Logic boards come off the BEC, never off the 3S rail.",
        fontsize=10, pad=16)
    figure.tight_layout()
    figure.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(figure)
    return out


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    print(f"-> {evidence(DOCS / 'evidence.png').relative_to(ROOT)}")
    print(f"-> {wiring(DOCS / 'wiring.png').relative_to(ROOT)}")


if __name__ == "__main__":
    main()

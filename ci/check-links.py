"""Check the README's own links: internal anchors and external URLs.

This repository is documentation, so its links are the thing that can rot. Anchor
targets are resolved against the headings actually present, using GitHub's
slugification, and external URLs are fetched.
"""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"
TIMEOUT = 20
# 403 is what several sites return to a scripted user agent; that is not rot.
ACCEPTABLE = {200, 301, 302, 303, 307, 308, 403, 429}


def slug(heading: str) -> str:
    """GitHub's heading -> anchor rule.

    Lowercase, drop punctuation, then replace whitespace characters *one for one*
    with dashes. Collapsing runs instead is the easy mistake: "Wiring & assembly"
    loses the ampersand and keeps two spaces, so the real anchor is
    ``wiring--assembly`` with two dashes, not ``wiring-assembly``.
    """
    text = re.sub(r"[^\w\s-]", "", heading.strip().lower())
    return re.sub(r"\s", "-", text)


def main() -> int:
    text = README.read_text()
    failures: list[str] = []

    headings = {slug(h) for h in re.findall(r"^#{1,6}\s+(.*)$", text, re.M)}
    for anchor in sorted(set(re.findall(r"\]\(#([^)]+)\)", text))):
        status = "ok" if anchor in headings else "MISSING"
        print(f"  anchor #{anchor}: {status}")
        if status == "MISSING":
            failures.append(f"anchor #{anchor} matches no heading")

    for url in sorted(set(re.findall(r"https?://[^\s)\]<>\"]+", text))):
        url = url.rstrip(".,;")
        request = urllib.request.Request(url, headers={"User-Agent": "docs-ci"})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                code = response.status
        except urllib.error.HTTPError as exc:
            code = exc.code
        except Exception as exc:  # DNS, TLS, timeout
            print(f"  {url}: UNREACHABLE ({type(exc).__name__})")
            failures.append(f"{url} unreachable")
            continue
        print(f"  {url}: {code}")
        if code not in ACCEPTABLE:
            failures.append(f"{url} returned {code}")

    if failures:
        print("\nFAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nall links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())

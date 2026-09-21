"""
EN: every relative link in the repository's documentation points at a file that exists.

This replaces the test that required the front door to exist in four languages, which had no object after 2026-09-21:
the documentation is English only, and the four languages live where the researcher reads them while USING the tool
(report, messages, figures, notebook), one fact per key in `i18n.py`. The drift that remains possible is the one this
test catches — a link left pointing at a file that moved or was deleted. It has happened twice: six broken links after
the root was tidied on 2026-09-19, and seven documents removed on 2026-09-21. A broken link fails in silence, which is
what makes it worth a test.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = sorted(ROOT.glob("*.md")) + sorted((ROOT / "docs").glob("*.md"))
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def test_the_documentation_is_english_only():
    """EN: the decision of 2026-09-21 — one contract, one README, one guide, and no translated copies beside them."""
    assert (ROOT / "CONTRACTS.md").exists() and not (ROOT / "CONTRATOS.md").exists()
    traduzidos = [p.name for p in DOCS if re.search(r"\.(es|pt|it)\.md$", p.name)]
    assert not traduzidos, f"documentation is English only; found translated copies: {traduzidos}"


def test_every_relative_link_points_at_a_file_that_exists():
    quebrados = []
    for doc in DOCS:
        for alvo in LINK.findall(doc.read_text(encoding="utf-8")):
            alvo = alvo.split("#", 1)[0].strip()
            if not alvo or alvo.startswith(("http://", "https://", "mailto:")):
                continue
            if not (doc.parent / alvo).resolve().exists():
                quebrados.append(f"{doc.relative_to(ROOT)} → {alvo}")
    assert not quebrados, "broken relative links:\n  " + "\n  ".join(quebrados)

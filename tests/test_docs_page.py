"""EN: the docs page speaks the four languages of the tool. Italian was added to the tool in v0.7 and the page was
left behind for a year — found by the user on 2026-09-18: 60 blocks in en/es/pt and none in it. This test refuses
that drift: every translated block exists in the four languages, and the language selector offers the four."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGS = ("en", "es", "pt", "it")


def _page() -> str:
    return (ROOT / "docs/index.html").read_text(encoding="utf-8")


def test_every_language_has_the_same_number_of_blocks():
    h = _page()
    counts = {l: len(re.findall(rf'data-l="{l}"', h)) for l in LANGS}
    assert len(set(counts.values())) == 1, f"the page left a language behind: {counts}"
    assert min(counts.values()) >= 50, f"too few translated blocks: {counts}"


def test_the_language_selector_offers_the_four():
    h = _page()
    for l in LANGS:
        assert f"setL('{l}'" in h, f"the selector has no button for {l}"

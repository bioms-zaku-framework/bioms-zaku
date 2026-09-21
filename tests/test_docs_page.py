"""EN: the documentation page is English only (decision of 2026-09-21) and its machinery for four languages is gone.

Until that date the page carried 60 blocks in each of en/es/pt/it plus a selector, and the drift it suffered was a
language left behind — Italian was added to the tool in v0.7 and the page stayed in three languages for months. With
one language that drift cannot happen; what this test refuses now is the opposite defect, the leftovers of the removed
machinery: a `data-l` block, a selector, or the CSS rule that hid whatever was not selected, any of which would hide
content from the reader with no error anywhere."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _page() -> str:
    return (ROOT / "docs/index.html").read_text(encoding="utf-8")


def test_no_leftovers_of_the_language_machinery():
    h = _page()
    assert not re.search(r'data-l\s*=', h), "a language block survived: it would be hidden by nothing and shown twice"
    assert "setL(" not in h and 'class="lang"' not in h, "the language selector survived the removal"
    assert "[data-l]{display:none}" not in h, "the CSS that hid unselected blocks survived: it can only hide content now"


def test_the_page_still_carries_its_content_and_points_at_the_contract():
    h = _page()
    assert h.count("<h2") >= 5 and len(h) > 20_000, "the page lost content when the languages were stripped"
    assert "CONTRACTS.md" in h and "CONTRATOS.md" not in h, "the page must link the contract that exists"

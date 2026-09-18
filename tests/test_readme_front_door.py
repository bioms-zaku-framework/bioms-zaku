"""EN: the front door. A researcher who clicks a link and is not a programmer must find, before any formula, what the
tool is, which problem it solves and how to start — in the four languages of the tool (user decision, 2026-09-18).
Guards against the drift of editing one language and forgetting the others."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGS = ("EN", "ES", "PT", "IT")


def _front_door() -> str:
    txt = (ROOT / "README.md").read_text(encoding="utf-8")
    i, j = txt.index("## What is this?"), txt.index("## What it does")
    assert i < j, "the plain-language opening must come BEFORE the technical section"
    return txt[i:j]


def test_the_opening_speaks_the_four_languages_at_a_similar_length():
    block = _front_door()
    marks = {l: block.find(f"**{l}**") for l in LANGS}
    assert all(v > 0 for v in marks.values()), f"a language is missing from the opening: {marks}"
    bounds = sorted(marks.values()) + [len(block)]
    sizes = [len(block[a:b].split()) for a, b in zip(bounds, bounds[1:])]
    assert min(sizes) >= 120, f"too short to answer the four questions: {sizes}"
    assert max(sizes) <= 1.6 * min(sizes), f"one language got much less than the others: {sizes}"


def test_the_opening_carries_no_formula_and_says_no_programming_is_needed():
    block = _front_door()
    for jargon in ("Σ", "aᵀ", "out-of-bag", "bootstrap", "R²", "Spearman"):
        assert jargon not in block, f"the opening must stay free of {jargon}: it is for someone who just arrived"
    assert len(re.findall(r"program", block, re.I)) >= 4, "each language must say that programming is not required"

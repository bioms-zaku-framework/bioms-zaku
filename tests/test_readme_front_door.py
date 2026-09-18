"""EN: the front door, in the four languages of the tool. A researcher who clicks a link and is not a programmer must
find, before any formula, what the tool is, which problem it solves and how to start. One file per language (a reader
should not scroll past three languages to reach their own), with a bar linking the others; README.md is the reference.
The user found on 2026-09-18 that the page had been left in three languages while the tool spoke four: these tests
refuse that drift."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {"en": "README.md", "es": "README.es.md", "pt": "README.pt.md", "it": "README.it.md"}
JARGON = ("Σ", "aᵀ", "out-of-bag", "bootstrap", "R²", "Spearman")


def _text(lang: str) -> str:
    return (ROOT / FILES[lang]).read_text(encoding="utf-8")


def _opening(lang: str) -> str:
    """EN: the plain-language section, which must come before the technical one."""
    t = _text(lang)
    heads = [m.start() for m in re.finditer(r"^## ", t, re.M)]
    assert len(heads) >= 2, f"{FILES[lang]}: no sections"
    return t[heads[0]:heads[1]]


def test_the_four_files_exist_and_link_to_each_other():
    for lang, name in FILES.items():
        t = _text(lang)
        for other, other_name in FILES.items():
            if other == lang:
                continue
            assert f"({other_name})" in t, f"{name} does not link to {other_name}"


def test_the_four_files_have_the_same_sections():
    counts = {l: len(re.findall(r"^## ", _text(l), re.M)) for l in FILES}
    assert len(set(counts.values())) == 1, f"a translation lost or gained sections: {counts}"
    assert min(counts.values()) >= 12, counts


def test_each_opening_answers_the_questions_without_a_formula():
    sizes = {}
    for lang in FILES:
        op = _opening(lang)
        sizes[lang] = len(op.split())
        assert re.search(r"program", op, re.I), f"{FILES[lang]}: the opening must say programming is not required"
        for j in JARGON:
            assert j not in op, f"{FILES[lang]}: the opening must stay free of {j}"
    assert min(sizes.values()) >= 120, f"too short to answer the four questions: {sizes}"
    assert max(sizes.values()) <= 1.6 * min(sizes.values()), f"one language got much less than the others: {sizes}"


def test_the_technical_section_follows_and_is_not_the_front_door():
    for lang in FILES:
        t = _text(lang)
        first = re.search(r"^## (.+)$", t, re.M).group(1)
        assert not any(j in first for j in JARGON), f"{FILES[lang]}: the first section is technical: {first!r}"


# --- the ten-minute guide, same rule: one file per language, kept in step -----------------------------------------
GUIDES = {"en": "GUIDE_10_MINUTES.md", "es": "GUIDE_10_MINUTES.es.md",
          "pt": "GUIDE_10_MINUTES.pt.md", "it": "GUIDE_10_MINUTES.it.md"}


def test_the_four_guides_exist_with_the_same_sections():
    counts = {}
    for lang, name in GUIDES.items():
        p = ROOT / name
        assert p.exists(), f"{name} is missing: the guide must exist in the four languages of the tool"
        counts[lang] = len(re.findall(r"^## ", p.read_text(encoding="utf-8"), re.M))
    assert len(set(counts.values())) == 1, f"a translation of the guide lost or gained sections: {counts}"
    assert min(counts.values()) >= 9, counts


def test_each_guide_links_the_other_three():
    for lang, name in GUIDES.items():
        t = (ROOT / name).read_text(encoding="utf-8")
        for other, other_name in GUIDES.items():
            if other != lang:
                assert f"({other_name})" in t, f"{name} does not link to {other_name}"


def test_each_readme_points_to_the_guide_of_its_own_language():
    for lang, readme in FILES.items():
        t = (ROOT / readme).read_text(encoding="utf-8")
        assert f"({GUIDES[lang]})" in t, f"{readme} must link the guide in its own language"
        for other, guide in GUIDES.items():
            if other != lang:
                assert f"({guide})" not in t, f"{readme} links the guide of another language ({guide})"

"""EN: the English contract is a translation, and a translation that drifts is worse than none. CONTRATOS.md is the
original, written and reviewed in Portuguese, and prevails; CONTRACTS.md must keep its structure, every DOI and every
threshold. Section 6 (the change log) stays only in the original, as a dated record."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOI = re.compile(r"10\.\d{4,9}/[^\s);,]+")
# EN: the numbers a reviewer would check first — if one disappears from the translation, the test fails.
THRESHOLDS = ("0.95", "0.03", "0.90", "0.80", "0.50", "0.05", "2,000", "5 × 50", "70/30",
              "1e-6", "1e-4", "1e-9", "1e-12", "0.632", "max(20, 10 % of B)")


def _bodies() -> tuple[str, str]:
    pt = (ROOT / "CONTRATOS.md").read_text(encoding="utf-8")
    en = (ROOT / "CONTRACTS.md").read_text(encoding="utf-8")
    return pt[:pt.index("## 6. Changelog")], en[:en.index("## 6. Change log")]


def test_same_sections_and_subsections():
    pt, en = _bodies()
    for pattern in (r"^## ", r"^### "):
        a, b = len(re.findall(pattern, pt, re.M)), len(re.findall(pattern, en, re.M))
        assert a == b, f"{pattern!r}: {a} in the original, {b} in the translation"


def test_every_doi_of_the_original_is_in_the_translation():
    pt, en = _bodies()
    missing = sorted(set(DOI.findall(pt)) - set(DOI.findall(en)))
    assert not missing, f"DOIs lost in translation: {missing}"


def test_the_thresholds_survive():
    _, en = _bodies()
    missing = [t for t in THRESHOLDS if t not in en]
    assert not missing, f"thresholds missing from the translation: {missing}"

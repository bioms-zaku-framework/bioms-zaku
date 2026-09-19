"""EN: the front door exists in the four languages of the tool, and the four files stay in step. The user found on
2026-09-18 that the README had been left in three languages while the tool spoke four; this is the one check that
refuses that drift. Editorial rules (length, wording, which words may appear) are not machine-checked on purpose."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READMES = ("README.md", "docs/README.es.md", "docs/README.pt.md", "docs/README.it.md")
GUIDES = ("docs/GUIDE_10_MINUTES.md", "docs/GUIDE_10_MINUTES.es.md", "docs/GUIDE_10_MINUTES.pt.md", "docs/GUIDE_10_MINUTES.it.md")


def test_readme_and_guide_exist_in_four_languages_with_the_same_sections():
    for grupo in (READMES, GUIDES):
        secoes = {}
        for name in grupo:
            p = ROOT / name
            assert p.exists(), f"{name} is missing: the front door must exist in the four languages"
            secoes[name] = len(re.findall(r"^## ", p.read_text(encoding="utf-8"), re.M))
        assert len(set(secoes.values())) == 1, f"a translation lost or gained sections: {secoes}"

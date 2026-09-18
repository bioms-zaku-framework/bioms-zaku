"""EN: one language in the source, four in what the user reads (decision of 2026-09-18). Docstrings and code comments
are English: they are read by whoever reads the code, and the catalogue of user-facing messages (`i18n`) already
carries the four languages. What the researcher reads must NOT follow that rule — the header written into their YAML
is text for them, so it keeps the four languages."""
import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OTHER = re.compile(r"^\s*(ES|PT|IT):", re.M)


def test_docstrings_and_code_comments_are_english_only():
    offenders = {}
    for f in glob.glob(str(ROOT / "src/bioms_zaku/*.py")):
        src = Path(f).read_text(encoding="utf-8")
        # EN: the wizard's HEADER is user-facing text inside a string, not a code comment — excluded below.
        src = src.replace(_header(src), "") if _header(src) else src
        hits = [m.group(0).strip() for m in OTHER.finditer(src)]
        if hits:
            offenders[Path(f).name] = hits[:3]
    assert not offenders, f"translated docstrings/comments left in the source: {offenders}"


def _header(src: str) -> str:
    i = src.find('HEADER = """')
    if i < 0:
        return ""
    j = src.index('"""', i + 12)
    return src[i:j + 3]


def test_the_header_written_into_the_users_yaml_keeps_the_four_languages():
    src = (ROOT / "src/bioms_zaku/wizard.py").read_text(encoding="utf-8")
    header = _header(src)
    assert header, "the generated-YAML header disappeared"
    for tag in ("EN:", "ES:", "PT:", "IT:"):
        assert f"# {tag}" in header, f"the header the researcher reads lost {tag}"

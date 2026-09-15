"""EN: the Zaku method diagram (v0.9) — every text is bound to its box by construction; the generator's own estimate never exceeds the room."""
import re
from pathlib import Path

from bioms_zaku import diagram as D
from bioms_zaku.i18n import LANGS, set_language

ROOT = Path(__file__).resolve().parents[1]
COLS = ((20, 210), (240, 500), (530, 810), (840, 980))          # EN: the four column boxes (x, x + width) drawn by zaku_svg


def _room(x, anchor, left, right):
    if anchor == "start": return right - D.PAD - x
    if anchor == "end": return x - left - D.PAD
    return 2 * min(x - left, right - x) - 2 * D.PAD


def test_every_text_fits_its_box_in_every_language():
    for L in LANGS:
        set_language(L); svg = D.zaku_svg()
        texts = re.findall(r"<text x='([\d.]+)' y='([\d.]+)' font-size='([\d.]+)' font-weight='(\w+)' fill='([^']+)' text-anchor='(\w+)' font-family=\"([^\"]+)\"( textLength='([\d.]+)' lengthAdjust='spacingAndGlyphs')?>([^<]+)</text>", svg)
        assert len(texts) >= 60, L
        for x, y, size, weight, fill, anchor, family, pinned, tl, s in texts:
            x, y, size = float(x), float(y), float(size)
            box = next(((l, r) for l, r in COLS if l <= x <= r and 44 <= y <= 340), None)
            left, right = box if box else (0, D.W)
            k = D.K["mono"] if "monospace" in family else D.K["bold" if weight in ("600", "700", "bold") else "normal"]
            est = len(s) * size * k; room = _room(x, anchor, left, right)
            assert est <= room + 0.05, (L, s, est, room)                         # estimate within the room (reduced font when needed)
            if pinned and fill != "#fff": assert abs(float(tl) - room) < 0.11, (L, s)   # pinned exactly to the room (pill texts are bound to the narrower pill)
    set_language("en")


def test_every_text_call_declares_its_bounds():
    src = (ROOT / "src/bioms_zaku/diagram.py").read_text(encoding="utf-8")
    calls = [m for m in re.findall(r"_txt\([^\n]*", src) if not m.startswith("_txt(x: float")]
    assert calls and all("right=" in c for c in calls), [c for c in calls if "right=" not in c]


def test_diagram_is_deterministic_and_language_bound(tmp_path):
    set_language("pt"); a = D.zaku_svg(); b = D.zaku_svg(); assert a == b and "variáveis medidas" in a
    set_language("en"); assert "measured variables" in D.zaku_svg()
    p = D.write_diagram(tmp_path); assert p.name == "zaku_method.svg" and p.read_text(encoding="utf-8") == D.zaku_svg()

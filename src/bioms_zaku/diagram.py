"""
EN: The Zaku method diagram (v0.9): one fixed SVG, in the current language, drawn without matplotlib so it also works where
    the `[plots]` extra is absent. Content is schematic and fixed — the three example vectors are exact catalogue vectors
    (H²/R, Xc/H, R/H); the Σ cells are illustrative shading, not data. Written to figures/zaku_method.svg and embedded
    inline in the report. Texts come from the i18n catalogue (keys d.*, v.*).
ES: diagrama del método Zaku (SVG fijo, idioma actual).  PT: diagrama do método Zaku (SVG fixo, idioma atual).
IT: diagramma del metodo Zaku (SVG fisso, lingua corrente).
"""
from __future__ import annotations

import html
import math
from pathlib import Path

from .i18n import t

W, H = 1000, 400
INK, INK2, LINE, SURF = "#1d1d1f", "#52514e", "#d9d8d3", "#fcfcfb"
GREEN, VIOLET, BOTH, MUTED = "#22c55e", "#9333ea", "#52514e", "#9a9893"
POS, NEG = "#dbeafe", "#ffedd5"           # EN: same polarity hues as the exponents heatmap (blue positive, orange negative)
FONT = "Inter,'Segoe UI','DejaVu Sans',Arial,sans-serif"
EXAMPLES = (("H²/R", (-1, 0, 2, 0)), ("Xc/H", (0, 1, -1, 0)), ("R/H", (1, 0, -1, 0)))   # EN: exact catalogue vectors (R, Xc, H, W)
SIGMA_SHADE = ((1.0, 0.6, 0.3, 0.4), (0.6, 1.0, 0.2, 0.3), (0.3, 0.2, 1.0, 0.5), (0.4, 0.3, 0.5, 1.0))   # EN: illustrative only


K = {"normal": 0.60, "bold": 0.66, "mono": 0.62}   # EN: conservative average glyph width / font size (DejaVu Sans, Segoe, Inter, Verdana, Menlo)
PAD = 8                                             # EN: minimum distance from a text to the box edge


def _txt(x: float, y: float, s: str, *, size: float = 10.5, weight: str = "normal", color: str = INK, anchor: str = "start",
         family: str = FONT, left: float | None = None, right: float | None = None) -> str:
    """
    EN: one text element. When the enclosing box is given (left/right), the text is guaranteed to stay inside it: the width is
        estimated with a conservative glyph factor; if it would exceed the room, the font is reduced and `textLength` pins the
        rendered length to the room, whatever font the viewer's browser substitutes. Audited in headless Chrome (tools/audit_diagram.py).
    """
    extra = ""
    if right is not None:
        mono = "monospace" in family
        k = K["mono"] if mono else K["bold" if weight in ("600", "700", "bold") else "normal"]
        est = len(s) * size * k
        if anchor == "start":
            room = right - PAD - x
        elif anchor == "end":
            room = x - (left if left is not None else 0) - PAD
        else:                                              # middle
            room = 2 * min(x - (left if left is not None else 0), right - x) - 2 * PAD
        if est > room:
            size = math.floor(size * room / est * 100) / 100           # EN: rounded DOWN so the estimate never exceeds the room
            extra = f" textLength='{room:.1f}' lengthAdjust='spacingAndGlyphs'"
    return f"<text x='{x}' y='{y}' font-size='{size}' font-weight='{weight}' fill='{color}' text-anchor='{anchor}' font-family=\"{family}\"{extra}>{html.escape(s)}</text>"


def _box(x: float, y: float, w: float, h: float) -> str:
    return f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='10' fill='#fff' stroke='{LINE}' stroke-width='1.2'/>"


def _arrow(x1: float, y1: float, x2: float, y2: float) -> str:
    return f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{INK2}' stroke-width='1.4' marker-end='url(#zk-ar)'/>"


def _pill(x: float, y: float, w: float, label: str, color: str) -> str:
    return (f"<rect x='{x}' y='{y}' width='{w}' height='18' rx='9' fill='{color}'/>"
            + _txt(x + w / 2, y + 12.5, label, size=9.5, weight="600", color="#fff", anchor="middle", left=x + 2, right=x + w - 2))


def zaku_svg(*, title: str | None = None) -> str:
    """EN: the whole diagram as an SVG string, in the current i18n language. Deterministic (no dates, no data)."""
    p = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='100%' role='img' aria-label=\"{html.escape(t('fig.zaku_method'), quote=True)}\" style='max-width:{W}px;display:block;background:{SURF}'>",
         "<defs><marker id='zk-ar' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' markerHeight='7' orient='auto'>"
         f"<path d='M0,0 L10,5 L0,10 z' fill='{INK2}'/></marker></defs>"]
    p.append(_txt(20, 24, title or t("fig.zaku_method"), size=14, weight="700", left=0, right=W))
    # ---- column 1: measured variables
    x1, y0, bh = 20, 44, 296
    p.append(_box(x1, y0, 190, bh))
    p.append(_txt(x1 + 12, y0 + 22, t("d.s1"), size=11.5, weight="700", left=20, right=210))
    p.append(_txt(x1 + 95, y0 + 62, "R · Xc · H · W", size=17, weight="700", anchor="middle", left=20, right=210))
    for i, (sym, key) in enumerate((("R", "w.mean.R"), ("Xc", "w.mean.Xc"), ("H", "w.mean.H"), ("W", "d.W"))):
        y = y0 + 98 + i * 22
        p.append(_txt(x1 + 14, y, sym, size=10.5, weight="700", left=20, right=210))
        p.append(_txt(x1 + 40, y, t(key), size=10, color=INK2, left=20, right=210))
    p.append(_txt(x1 + 95, y0 + 214, "ln", size=15, weight="700", anchor="middle", color=VIOLET, left=20, right=210))
    p.append(_txt(x1 + 95, y0 + 234, t("d.s1b"), size=10, anchor="middle", color=INK2, left=20, right=210))
    p.append(_txt(x1 + 95, y0 + 270, "x = (ln R, ln Xc, ln H, ln W)", size=9.5, anchor="middle", color=INK2, family="ui-monospace,Menlo,Consolas,monospace", left=20, right=210))
    # ---- column 2: decomposition (vectors table + Σ)
    x2 = 240
    p.append(_box(x2, y0, 260, bh))
    p.append(_txt(x2 + 12, y0 + 22, t("d.s2"), size=11.5, weight="700", left=240, right=500))
    p.append(_txt(x2 + 12, y0 + 42, t("d.s2a"), size=10.5, left=240, right=500))
    p.append(_txt(x2 + 12, y0 + 58, t("d.s2c"), size=9.5, color=INK2, left=240, right=500))
    # vectors mini-table
    tx, ty, cw = x2 + 12, y0 + 72, 30
    p.append(_txt(tx, ty + 10, t("d.ex"), size=9, color=INK2, left=240, right=500))
    for j, v in enumerate(("R", "Xc", "H", "W")):
        p.append(_txt(tx + 62 + j * cw + cw / 2, ty + 26, v, size=9.5, weight="700", anchor="middle", color=INK2, left=240, right=500))
    for i, (name, vec) in enumerate(EXAMPLES):
        y = ty + 34 + i * 20
        p.append(_txt(tx, y + 13, name, size=10, weight="600", left=240, right=500))
        for j, e in enumerate(vec):
            cx = tx + 62 + j * cw
            fill = POS if e > 0 else NEG if e < 0 else "#f3f3f1"
            p.append(f"<rect x='{cx + 1}' y='{y}' width='{cw - 2}' height='18' rx='3' fill='{fill}'/>")
            p.append(_txt(cx + cw / 2, y + 13, f"{e:+d}" if e else "0", size=9.5, anchor="middle", color=INK if e else MUTED, family="ui-monospace,Menlo,Consolas,monospace", left=240, right=500))
    # Σ matrix (below the table), then the exact identity on its own full-width line
    sx, sy, cs = x2 + 12, y0 + 180, 15
    p.append(_txt(sx, sy - 4, "Σ", size=12, weight="700", left=240, right=500))
    p.append(_txt(sx + 16, sy - 4, t("d.s2b"), size=9.5, color=INK2, left=240, right=500))
    for i in range(4):
        for j in range(4):
            a = 0.12 + 0.55 * SIGMA_SHADE[i][j]
            p.append(f"<rect x='{sx + 18 + j * cs}' y='{sy + 4 + i * cs}' width='{cs - 1}' height='{cs - 1}' fill='{VIOLET}' fill-opacity='{a:.2f}'/>")
    for k, v in enumerate(("R", "Xc", "H", "W")):
        p.append(_txt(sx + 18 + k * cs + cs / 2 - 0.5, sy + 4 + 4 * cs + 10, v, size=8, anchor="middle", color=INK2, left=240, right=500))
        p.append(_txt(sx + 12, sy + 4 + k * cs + 11, v, size=8, anchor="end", color=INK2, left=240, right=500))
    p.append(_txt(sx + 100, sy + 30, t("d.s2d"), size=9.5, color=INK2, left=240, right=500))
    p.append(_txt(sx, y0 + 286, "r(a,b) = aᵀΣb / √(aᵀΣa · bᵀΣb)", size=10, weight="600", family="ui-monospace,Menlo,Consolas,monospace", left=240, right=500))
    # ---- column 3: audit
    x3 = 530
    p.append(_box(x3, y0, 280, bh))
    p.append(_txt(x3 + 12, y0 + 22, t("d.s3"), size=11.5, weight="700", left=530, right=810))
    rows = ((t("d.s3a"), t("d.s3a2"), INK), (t("d.s3b"), t("d.s3b2"), GREEN), (t("d.s3c"), "", INK), (t("d.s3d"), "", VIOLET))
    y = y0 + 50
    for main, sub, col in rows:
        p.append(f"<circle cx='{x3 + 18}' cy='{y - 4}' r='4' fill='{col}'/>")
        p.append(_txt(x3 + 30, y, main, size=10.5, left=530, right=810))
        if sub:
            p.append(_txt(x3 + 30, y + 15, sub, size=10, color=INK2, left=530, right=810)); y += 15
        y += 26
    # S1 / S2 mini bars (schematic)
    by = y0 + 210
    p.append(_txt(x3 + 30, by, "S1", size=9.5, weight="700", color=GREEN, left=530, right=810)); p.append(f"<rect x='{x3 + 52}' y='{by - 9}' width='120' height='9' fill='{GREEN}'/>")
    p.append(_txt(x3 + 30, by + 16, "S2", size=9.5, weight="700", color=VIOLET, left=530, right=810)); p.append(f"<rect x='{x3 + 52}' y='{by + 7}' width='22' height='9' fill='{VIOLET}'/>")
    p.append(f"<line x1='{x3 + 52 + 40}' y1='{by - 14}' x2='{x3 + 52 + 40}' y2='{by + 20}' stroke='{INK2}' stroke-width='1' stroke-dasharray='3 2'/>")
    p.append(_txt(x3 + 52 + 44, by + 30, "margin · CI · P", size=8.5, color=INK2, family="ui-monospace,Menlo,Consolas,monospace", left=530, right=810))
    p.append(_pill(x3 + 190, by - 12, 76, t("v.SPECIFIC"), GREEN))
    p.append(_txt(x3 + 30, y0 + 276, t("d.s3e"), size=9.5, color=INK2, left=530, right=810))
    # ---- column 4: verdicts
    x4 = 840
    p.append(_box(x4, y0, 140, bh))
    p.append(_txt(x4 + 12, y0 + 22, t("d.s4"), size=11.5, weight="700", left=840, right=980))
    for i, (k, col) in enumerate((("v.SPECIFIC", GREEN), ("v.TRACKS_CONTROL", VIOLET), ("v.BOTH", BOTH), ("v.NEITHER", MUTED))):
        p.append(_pill(x4 + 12, y0 + 40 + i * 28, 116, t(k), col))
    p.append(_txt(x4 + 12, y0 + 176, "+", size=12, weight="700", color=INK2, left=840, right=980))
    p.append(_txt(x4 + 12, y0 + 196, t("d.s4a"), size=9.5, color=INK2, left=840, right=980))
    p.append(_txt(x4 + 12, y0 + 212, t("d.s4b"), size=9.5, color=INK2, left=840, right=980))
    p.append(_txt(x4 + 12, y0 + 240, t("d.s4c"), size=10, weight="600", left=840, right=980))
    # ---- arrows and footer
    ym = y0 + bh / 2
    p += [_arrow(210, ym, 238, ym), _arrow(500, ym, 528, ym), _arrow(810, ym, 838, ym)]
    p.append(_txt(500, H - 14, t("d.name"), size=9.5, anchor="middle", color=INK2, left=0, right=W))
    p.append("</svg>")
    return "\n".join(p)


def write_diagram(fig_dir: Path) -> Path:
    fig_dir = Path(fig_dir); fig_dir.mkdir(parents=True, exist_ok=True)
    out = fig_dir / "zaku_method.svg"
    out.write_text(zaku_svg(), encoding="utf-8")
    return out

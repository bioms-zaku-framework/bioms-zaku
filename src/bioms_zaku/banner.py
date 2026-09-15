"""
EN: Terminal welcome (v0.9): the BioMS Zaku letters in the brand gradient (violet → green), the name attribution and the three
    commands. Shown ONLY where a person is looking: `bioms-zaku` with no command, `bioms-zaku --version`, and the start of an
    interactive `init`. Never in `run`, `check`, `render` or `init --map` (their output goes to logs and scripts). Colour only
    when stdout is a terminal, NO_COLOR is unset and TERM is not "dumb" (https://no-color.org); otherwise plain text.
ES: bienvenida en la terminal.  PT: boas-vindas no terminal.  IT: benvenuto nel terminale.
"""
from __future__ import annotations

import os
import sys

from . import __version__
from .i18n import t

ART = (
    "██████╗ ██╗ ██████╗ ███╗   ███╗███████╗    ███████╗ █████╗ ██╗  ██╗██╗   ██╗",
    "██╔══██╗██║██╔═══██╗████╗ ████║██╔════╝    ╚══███╔╝██╔══██╗██║ ██╔╝██║   ██║",
    "██████╔╝██║██║   ██║██╔████╔██║███████╗      ███╔╝ ███████║█████╔╝ ██║   ██║",
    "██╔══██╗██║██║   ██║██║╚██╔╝██║╚════██║     ███╔╝  ██╔══██║██╔═██╗ ██║   ██║",
    "██████╔╝██║╚██████╔╝██║ ╚═╝ ██║███████║    ███████╗██║  ██║██║  ██╗╚██████╔╝",
    "╚═════╝ ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝    ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝",
)
VIOLET, GREEN = (147, 51, 234), (34, 197, 94)     # EN: same hex as the logo and the report (#9333ea, #22c55e)
RESET, DIM, BOLD = "\x1b[0m", "\x1b[2m", "\x1b[1m"


def use_colour(stream=None) -> bool:
    """EN: colour only for a human terminal (tty), respecting NO_COLOR and TERM=dumb."""
    stream = stream or sys.stdout
    try:
        tty = bool(stream.isatty())
    except Exception:
        tty = False
    return tty and "NO_COLOR" not in os.environ and os.environ.get("TERM", "") != "dumb"


def _gradient(line: str) -> str:
    n = max(len(line) - 1, 1)
    out = []
    for i, ch in enumerate(line):
        r, g, b = (int(VIOLET[k] + (GREEN[k] - VIOLET[k]) * i / n) for k in range(3))
        out.append(f"\x1b[38;2;{r};{g};{b}m{ch}")
    return "".join(out) + RESET


def _steps() -> list[str]:
    rows = (("bioms-zaku init dados.csv analise.yaml", t("bn.step1")), ("bioms-zaku check analise.yaml", t("bn.step2")), ("bioms-zaku run analise.yaml", t("bn.step3")))
    cw = max(len(c) for c, _ in rows); dw = max(len(d) for _, d in rows)
    inner = 2 + cw + 5 + dw + 2
    L = []
    for k, (c, d) in enumerate(rows, 1):
        head = f"─ {k} "
        L.append(("┌" if k == 1 else "├") + head + "─" * (inner - len(head)) + ("┐" if k == 1 else "┤"))
        L.append("│  " + c.ljust(cw) + "     " + d.ljust(dw) + "  │")
    L.append("└" + "─" * inner + "┘")
    return L


def banner(*, full: bool = True, colour: bool | None = None) -> str:
    """EN: the welcome text in the current language. `full` adds the three commands; `colour=None` = auto-detect."""
    colour = use_colour() if colour is None else colour
    art = [("  " + (_gradient(l) if colour else l)) for l in ART]
    b = (lambda s: BOLD + s + RESET) if colour else (lambda s: s)
    d = (lambda s: DIM + s + RESET) if colour else (lambda s: s)
    lines = [""] + art + ["", "  " + b(f"BioMS Zaku {__version__}") + " · " + t("bn.tagline"), "  " + d(t("d.name")), ""]
    if full:
        lines += ["  " + l for l in _steps()]
        lines += ["  " + d(t("bn.langs")) + "       " + d(t("bn.example", cmd="bioms-zaku run examples/example_quick.yaml")), ""]
    return "\n".join(lines)

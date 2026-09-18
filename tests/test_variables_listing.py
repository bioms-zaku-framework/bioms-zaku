"""EN: the variables of the file, ONE PER LINE (user decision, 2026-09-18). Every column is listed — sex and strata are
mapped from non-numeric ones, which the old single line hid — and the layout is the same everywhere: no cut-off above
n columns (a threshold with no source) and nothing read from the terminal width."""
import os
import shutil

from bioms_zaku.i18n import LANGS, set_language, t
from bioms_zaku.wizard import print_variables

COLS = ["id", "sexo_txt", "R", "Xc", "grupo"]
NUMERIC = ["id", "R", "Xc"]


def _block(lang: str = "pt") -> list[str]:
    set_language(lang)
    out: list[str] = []
    print_variables(out.append, "dados.csv", COLS, NUMERIC)
    return out


def _names(block: list[str]) -> list[str]:
    return [l.strip().split("  ")[0] for l in block if l.startswith("    ")]


def test_every_column_on_its_own_line_in_file_order():
    assert _names(_block()) == COLS


def test_non_numeric_columns_are_listed_and_marked():
    block, mark = _block(), t("w.vars.text")
    assert [l.strip().split("  ")[0] for l in block if l.startswith("    ") and mark in l] == ["sexo_txt", "grupo"]


def test_header_counts_every_column_not_only_the_numeric_ones():
    assert f" {len(COLS)} " in _block()[1] and str(len(NUMERIC)) not in _block()[1].replace(str(len(COLS)), "")


def test_four_languages_render_header_and_closing_line():
    for lang in LANGS:
        block = _block(lang)
        assert block[1].endswith(":") and block[-1] == t("w.vars.use") and _names(block) == COLS


def test_layout_never_depends_on_the_terminal_width(monkeypatch):
    wide = _block()
    monkeypatch.setattr(shutil, "get_terminal_size", lambda *a, **k: os.terminal_size((20, 24)))
    assert _block() == wide

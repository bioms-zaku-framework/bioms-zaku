"""EN: the end of a run must speak to the place it is running in (defect found by the user in Colab, 2026-09-24:
an <iframe> pointing at a path under /content renders a blank page, because Colab's cell output is served from an
isolated origin that cannot read the VM's filesystem — and the line above it told him to use a terminal he has not)."""
import sys
import types

import pytest

from bioms_zaku import run as R


def test_colab_is_told_apart_from_a_local_notebook_and_from_a_terminal():
    assert R._where_we_run() == "terminal"                       # EN: pytest is not a notebook
    fake = types.ModuleType("google.colab")
    sys.modules["google.colab"] = fake
    try:
        assert R._where_we_run() == "colab"
    finally:
        del sys.modules["google.colab"]
    assert R._where_we_run() == "terminal"


def test_in_colab_the_run_gives_the_download_path_and_never_the_terminal_line(tmp_path, monkeypatch):
    linhas: list[str] = []
    rp = tmp_path / "zaku_out" / "minha_execucao" / "report.html"
    rp.parent.mkdir(parents=True)
    rp.write_text("<html></html>", encoding="utf-8")
    chamou_iframe = []
    monkeypatch.setattr(R, "_show_inline", lambda p: chamou_iframe.append(p))

    sys.modules["google.colab"] = types.ModuleType("google.colab")
    try:
        from bioms_zaku.i18n import t
        assert R._where_we_run() == "colab"
        linhas.append(t("r.open_colab", folder=" → ".join(rp.parent.parts[-2:]), path=rp))
    finally:
        del sys.modules["google.colab"]

    texto = "\n".join(linhas)
    assert "zaku_out → minha_execucao" in texto, "the message must name the folders the reader clicks"
    assert "files.download" in texto and str(rp) in texto
    assert "xdg-open" not in texto, "a terminal command in Colab is an instruction the reader cannot follow"
    assert not chamou_iframe, "no iframe in Colab: it renders a blank page"


def test_the_message_exists_in_the_four_languages_with_the_same_fields():
    from bioms_zaku.i18n import LANGS, MSG
    m = MSG["r.open_colab"]
    assert set(m) == set(LANGS)
    for l in LANGS:
        assert "{folder}" in m[l] and "{path}" in m[l] and "files.download" in m[l]

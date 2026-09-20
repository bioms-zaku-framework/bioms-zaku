"""EN: terminal welcome (v0.9) — shown only where a person is looking, plain text off a terminal, never in run/check/render/--map."""
import os
from pathlib import Path

import yaml

from bioms_zaku import banner as B
from bioms_zaku.i18n import LANGS, set_language

ROOT = Path(__file__).resolve().parents[1]
ART0 = B.ART[0]


def test_banner_text_four_languages_aligned_and_colour_modes():
    for L in LANGS:
        set_language(L); txt = B.banner(colour=False)
        assert ART0 in txt and "\x1b" not in txt and "zaku (Juruna/Yudjá)" in txt and "bioms-zaku run analise.yaml" in txt
        box = [l for l in txt.splitlines() if l.strip() and l.strip()[0] in "┌├│└"]
        assert len(box) == 7 and len({len(l) for l in box}) == 1, L                 # closed box, every row the same width
        short = B.banner(full=False, colour=False); assert ART0 in short and "┌" not in short
    set_language("en")
    col = B.banner(colour=True); assert "\x1b[38;2;147;51;234m" in col and "\x1b[0m" in col
    assert "comece aqui" not in col and "start here" in B.banner(colour=False)


def test_colour_only_on_a_terminal(monkeypatch):
    class S:
        def __init__(s, tty): s._t = tty
        def isatty(s): return s._t
    monkeypatch.delenv("NO_COLOR", raising=False); monkeypatch.setenv("TERM", "xterm-256color")
    assert B.use_colour(S(True)) and not B.use_colour(S(False))
    monkeypatch.setenv("NO_COLOR", "1"); assert not B.use_colour(S(True))
    monkeypatch.delenv("NO_COLOR"); monkeypatch.setenv("TERM", "dumb"); assert not B.use_colour(S(True))


def test_cli_shows_the_banner_only_without_a_command_or_with_version_flag(capsys, monkeypatch, tmp_path):
    from bioms_zaku.cli import main
    from bioms_zaku import __version__
    monkeypatch.chdir(ROOT)
    assert main([]) == 0; out = capsys.readouterr().out
    assert ART0 in out and "\x1b" not in out and __version__ in out               # capsys is not a tty → plain text
    assert main(["--lang", "pt", "--version"]) == 0; out = capsys.readouterr().out
    assert ART0 in out and "repete uma sessão sem perguntas" in out
    assert main(["version"]) == 0; assert capsys.readouterr().out.strip() == __version__   # plain, for scripts
    assert main(["--lang", "pt", "check", "tests/minimal.yaml"]) == 0; out = capsys.readouterr().out
    assert ART0 not in out and "check:" in out and out.rstrip().endswith("copie e cole:  bioms-zaku --lang pt run tests/minimal.yaml")
    flags = ["R=resistencia_ohm", "Xc=reatancia_ohm", "H=estatura_cm", "W=massa_kg", "target=lmi_dxa", "control=fmi_dxa", "independent=yes"]
    assert main(["init", "tests/minimal_data.csv", "-o", str(tmp_path / "a.yaml"), "--map", *flags]) == 0
    assert ART0 not in capsys.readouterr().out                                          # --map: no banner
    set_language("en")


def test_interactive_init_opens_with_the_short_banner_before_the_file_line(tmp_path):
    from bioms_zaku.wizard import init
    answers = iter(["pt", "", "", "", "", "", "", "", "", "lmi_dxa", "fmi_dxa", "", "", "", "", "", "yes", "", ""])
    printed = []
    def ask(prompt, default):
        try: return next(answers)
        except StopIteration: return ""
    try:
        init(str(ROOT / "tests/minimal_data.csv"), str(tmp_path / "i.yaml"), ask=ask, printer=printed.append)
    except Exception:
        pass                                       # EN: the scripted answers need not complete the wizard; only the prologue is under test
    joined = "\n".join(printed)
    assert ART0 in joined and joined.index(ART0) < joined.index("arquivo:")            # banner, then the file line, in Portuguese
    set_language("en")


def test_run_and_render_output_never_carry_the_banner(tmp_path):
    from bioms_zaku.run import run, render
    cfg = yaml.safe_load((ROOT / "tests/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "tests/minimal_data.csv"); cfg["output"] = {"dir": str(tmp_path), "figures": False}
    cfg["catalog"] = {"include": ["Lukaski1985_II", "Piccoli1994_RH"]}; cfg["audit"] = {"bootstrap": {"min_oob": 10}, "cv": {"folds": 3}}
    lines = []; res = run(cfg, printer=lines.append); render(res["out_dir"], "pt", printer=lines.append)
    assert not any(ART0 in l or "\x1b" in l for l in lines)
    set_language("en")

"""EN: contract v0.7 — one message catalogue, four languages, identical keys and placeholders; the language chosen once
(YAML `language` or --lang) reaches prompts, check, run, summary, report headings and figures. ES/PT/IT: catálogo único."""
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from bioms_zaku import plots
from bioms_zaku.i18n import LANGS, MSG, get_language, set_language, t

ROOT = Path(__file__).resolve().parents[1]


def _placeholders(s: str) -> set:
    return set(re.findall(r"\{(\w+)", s))


def test_catalogue_has_all_languages_and_identical_placeholders():
    assert LANGS == ("en", "es", "pt", "it") and len(MSG) >= 90
    for k, m in MSG.items():
        assert set(m) == set(LANGS), k
        assert all(_placeholders(m[l]) == _placeholders(m["en"]) for l in LANGS), k


def test_figure_dictionaries_and_captions_cover_four_languages():
    for D in (plots.I18N, plots.SC, plots.FIG):
        assert set(D) == set(LANGS)
        for l in LANGS:
            assert set(D[l]) == set(D["en"])
            for k, v in D["en"].items():
                if isinstance(v, str):
                    assert _placeholders(v) == _placeholders(D[l][k]), (l, k)
    assert all(len(c) == 4 for c in plots.CAPTIONS.values())


def test_set_language_and_fallback():
    set_language("pt"); assert get_language() == "pt" and t("c.ok").startswith("check: OK — pronto")
    set_language("it"); assert t("h.figures") == "Figure"
    with pytest.raises(ValueError):
        set_language("fr")
    set_language("en")


def test_language_flows_from_init_to_check_run_summary_and_figures(tmp_path):
    from bioms_zaku.wizard import init
    from bioms_zaku.check import check
    from bioms_zaku.run import run
    flags = {"R": "resistencia_ohm", "Xc": "reatancia_ohm", "H": "estatura_cm", "W": "massa_kg", "target": "lmi_dxa", "control": "fmi_dxa",
             "covariates": "massa_kg,estatura_cm", "strata": "sexo", "id": "seqn", "independent": "yes"}
    printed = []
    out = init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "pt.yaml"), map_flags=flags, lang="pt", printer=printed.append)
    assert any(l.startswith("mapeamento:") for l in printed) and any("gravado" in l for l in printed)
    cfg = yaml.safe_load(out.read_text(encoding="utf-8")); assert cfg["language"] == "pt"
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); cfg["output"] = {"dir": str(tmp_path), "figures": True}; cfg["preset"] = "quick"
    cfg["catalog"] = {"include": ["Lukaski1985_II", "Piccoli1994_RH"]}; cfg["audit"] = {"bootstrap": {"min_oob": 10}, "cv": {"folds": 3}}
    (tmp_path / "pt.yaml").write_text(yaml.safe_dump(cfg))
    lines = []; check(str(tmp_path / "pt.yaml"), printer=lines.append)
    assert lines[-1].startswith("check: OK — pronto para rodar")
    set_language("en")                                   # EN: the API must pick the YAML language by itself
    res = run(str(tmp_path / "pt.yaml"), printer=lambda s: None)
    summ = (res["out_dir"] / "summary.md").read_text(encoding="utf-8")
    assert "## Estrato `" in summ and "- métodos avaliados:" in summ and "## Geometria do alvo e do controle" in summ
    html = (res["out_dir"] / "report.html").read_text(encoding="utf-8"); assert "<h2>Figuras</h2>" in html and "<h2>Resultados</h2>" in html and "Rigor desta execução" in html
    caps = (res["out_dir"] / "figures" / "README.md").read_text(encoding="utf-8"); assert caps.index("**PT**") < caps.index("**EN**")
    assert res["manifest"]["config_resolved"]["figures"]["language"] == "pt"
    set_language("en")


def test_cli_lang_flag_overrides_yaml(tmp_path):
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8")); cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); cfg["language"] = "es"
    p = tmp_path / "c.yaml"; p.write_text(yaml.safe_dump(cfg))
    r = subprocess.run([sys.executable, "-m", "bioms_zaku.cli", "check", str(p)], capture_output=True, text=True, env={"PYTHONPATH": str(ROOT / "src"), "PATH": ""})
    assert "check: OK — listo para ejecutar" in r.stdout
    r = subprocess.run([sys.executable, "-m", "bioms_zaku.cli", "--lang", "it", "check", str(p)], capture_output=True, text=True, env={"PYTHONPATH": str(ROOT / "src"), "PATH": ""})
    assert "check: OK — pronto per l'esecuzione" in r.stdout


def test_html_report_has_a_caption_for_every_figure_and_no_english_leak_in_pt(tmp_path):
    # EN: user-simulation findings — the target_control caption was empty (name cut at the first '_'); '‡ coupled' was hard-coded English.
    from bioms_zaku.run import run
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); cfg["output"] = {"dir": str(tmp_path), "figures": True}; cfg["language"] = "pt"
    cfg["catalog"] = {"include": ["Lukaski1985_II", "Piccoli1994_RH", "Baumgartner1988_PhA"]}; cfg["audit"] = {"bootstrap": {"min_oob": 10}, "cv": {"folds": 3}}
    res = run(cfg, printer=lambda s: None)
    html = (res["out_dir"] / "report.html").read_text(encoding="utf-8")
    import re as _re
    empties = _re.findall(r"<figcaption><b>([^<]+)</b> — </figcaption>", html)
    assert empties == [], f"figures without caption: {empties}"
    assert "target_control</b> — Mapa do controle negativo condicional" in html
    assert "coupled in the measured space" not in html and "missing inputs" not in html
    set_language("en")


def test_captions_are_complete_in_every_language():
    # EN: the es/pt lineage caption had lost its first half (found by the user, 2026-09-14): no caption may be far shorter than the others
    for name, caps in plots.CAPTIONS.items():
        L = [len(c) for c in caps]
        assert max(L) <= 1.4 * min(L), (name, L)
    assert plots.CAPTIONS["lineage"][2].startswith("Árvore genealógica") and plots.CAPTIONS["lineage"][1].startswith("Árbol genealógico")


def test_render_changes_language_without_recomputing(tmp_path):
    import hashlib, subprocess, sys
    from bioms_zaku.run import run, render
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); cfg["output"] = {"dir": str(tmp_path), "figures": True}; cfg["language"] = "pt"
    cfg["catalog"] = {"include": ["Lukaski1985_II", "Piccoli1994_RH", "Baumgartner1988_PhA"]}; cfg["audit"] = {"bootstrap": {"min_oob": 10}, "cv": {"folds": 3}}
    res = run(cfg, printer=lambda s: None); out = res["out_dir"]
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob("*.csv")}; man_before = (out / "manifest.json").read_bytes()
    assert "## Estrato" in (out / "summary.md").read_text(encoding="utf-8")
    render(out, "en", printer=lambda s: None)
    assert "## Stratum" in (out / "summary.md").read_text(encoding="utf-8")
    html = (out / "report.html").read_text(encoding="utf-8"); assert "<h2>Figures</h2>" in html and "Rigour of this run" in html and "Como foi calculado" not in html
    caps = (out / "figures" / "README.md").read_text(encoding="utf-8"); assert caps.index("**EN**") < caps.index("**PT**")
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob("*.csv")}
    assert after == before and (out / "manifest.json").read_bytes() == man_before          # nothing recomputed
    r = subprocess.run([sys.executable, "-m", "bioms_zaku.cli", "--lang", "it", "render", str(out)], capture_output=True, text=True, env={"PYTHONPATH": str(ROOT / "src"), "PATH": ""})
    assert r.returncode == 0 and "## Strato" in (out / "summary.md").read_text(encoding="utf-8")
    set_language("en")

"""EN: `bioms-zaku propose` (v0.9) — a common user adds own formulas question by question; each is validated on the data."""
from pathlib import Path

import yaml

from bioms_zaku.i18n import set_language
from bioms_zaku.wizard import init

ROOT = Path(__file__).resolve().parents[1]
FLAGS = {"R": "resistencia_ohm", "Xc": "reatancia_ohm", "H": "estatura_cm", "W": "massa_kg", "target": "lmi_dxa", "control": "fmi_dxa", "independent": "yes",
         "researcher": "Thalles Mota"}


def test_propose_validates_each_formula_and_writes_the_yaml(tmp_path):
    from bioms_zaku.propose import propose
    from bioms_zaku.check import check
    out = init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "a.yaml"), map_flags=FLAGS, lang="pt", printer=lambda s: None)
    answers = iter(["meu 1",                                  # invalid id → asked again
                    "BioMS_1", "H²·Xc/R (Mota)", "lean_mass", "H**2 * Xc / Rr",     # unknown name → rejected, asked again
                    "H**2 * Xc / R", "yes",
                    "BioMS_2", "", "", "(PhA * H / R) * (1/(1+exp(-(PhA - mean(PhA)))))", "yes",
                    "Pulado", "", "", "",                     # empty formula → skipped
                    ""])                                      # empty id → finish
    printed = []
    propose(out, ask=lambda prompt, default: next(answers), printer=printed.append)
    joined = "\n".join(printed)
    assert "meu 1: id inválido" in joined and "recusada:" in joined and "unknown name 'Rr'" in joined
    assert "avaliada em" in joined and "estatísticas amostrais usadas (registradas na execução): mean(PhA) =" in joined and "Pulado pulado" in joined
    assert "✓ BioMS_1 acrescentado" in joined and "gravado(s) 2 índice(s) proposto(s)" in joined
    cfg = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert cfg["catalog"]["include"] == ["curated", "BioMS_1", "BioMS_2"]
    ids = [e["id"] for e in cfg["catalog"]["user_entries"]]; assert ids == ["BioMS_1", "BioMS_2"]
    e = cfg["catalog"]["user_entries"][0]
    assert e["provenance"]["formula_source"] == "proposed" and e["authors"] == "Thalles Mota" and e["label"] == "H²·Xc/R (Mota)" and e["expr"] == "H**2 * Xc / R"
    assert out.read_text(encoding="utf-8").startswith("# BioMS Zaku configuration")             # init's header kept
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); lines = []; check(cfg, printer=lines.append)
    assert lines[-1].startswith("check: OK") and any("propostos" in l and "BioMS_1, BioMS_2" in l for l in lines)
    # nothing added → file untouched
    before = out.read_text(encoding="utf-8"); printed = []
    propose(out, ask=lambda p, d: "", printer=printed.append)
    assert out.read_text(encoding="utf-8") == before and any("nada acrescentado" in l for l in printed)
    set_language("en")


def test_cli_has_the_propose_command(capsys, monkeypatch, tmp_path):
    from bioms_zaku.cli import main
    out = init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "b.yaml"), map_flags=FLAGS, lang="en", printer=lambda s: None)
    answers = iter(["X1", "", "", "Xc / H_m", "yes", ""])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    assert main(["--lang", "pt", "propose", str(out)]) == 0
    o = capsys.readouterr().out; assert "✓ X1 acrescentado" in o and "próximo: bioms-zaku check" in o
    assert yaml.safe_load(out.read_text(encoding="utf-8"))["catalog"]["user_entries"][0]["expr"] == "Xc / H_m"
    set_language("en")


def test_simulation_findings_nonsense_formulas_constants_catalogue_ids_and_neighbours(tmp_path):
    # EN: user simulation of 2026-09-15: formulas with no auditable value, constants (also from mean()), an id of the catalogue,
    #     a formula that repeats a published method — every one handled with a message, none accepted silently, no crash.
    from bioms_zaku.propose import propose
    import numpy as np, pandas as pd
    from test_design_orthogonal import _frame
    csv = tmp_path / "big.csv"; _frame(n=600, seed=3).to_csv(csv, index=False)
    flags = {"R": "R", "Xc": "Xc", "H": "H", "W": "W", "target": "lean", "control": "fat", "strata": "sexo", "id": "seqn", "independent": "yes"}
    out = init(str(csv), str(tmp_path / "p.yaml"), map_flags=flags, lang="pt", printer=lambda s: None)
    answers = iter(["Z1", "", "", "R / (Xc - Xc)", "",            # division by zero → too few values → asked again → empty = skip
                    "Z2", "", "", "W - R", "",                    # negative everywhere
                    "Z3", "", "", "mean(W)", "",                  # constant from a sample statistic (a 0-d result) → constant
                    "Z4", "", "", "Xc / Xc", "",                  # constant
                    "LMI", "Z5", "", "", "H**2 / R", "yes",       # id of the catalogue refused; Lukaski's formula accepted with the neighbour warning
                    "Z6", "", "", "(PhA * H / R) * (1/(1+exp(-(PhA - mean(PhA)))))", "yes",   # the author's BioMS_2: fine
                    ""])
    printed = []
    propose(out, ask=lambda p, d: next(answers), printer=printed.append)
    txt = "\n".join(printed)
    assert txt.count("só 0 valores positivos finitos") == 2 and txt.count("constante nestes dados") == 2
    assert "LMI: este id pertence a um método do catálogo" in txt
    assert "ordena as pessoas como Lukaski1985_II (|Spearman| 1.00)" in txt
    assert "mean(PhA) =" in txt and "✓ Z5 acrescentado" in txt and "✓ Z6 acrescentado" in txt
    cfg = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert [e["id"] for e in cfg["catalog"]["user_entries"]] == ["Z5", "Z6"]
    set_language("en")

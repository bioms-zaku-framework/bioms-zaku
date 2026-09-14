"""EN: init (never guesses silently) and check (blocks what must be blocked). ES/PT: init e check."""
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

from bioms_zaku.check import CheckError, check
from bioms_zaku.io import InputError
from bioms_zaku.wizard import init, suggest

ROOT = Path(__file__).resolve().parents[1]
FLAGS = {"R": "resistencia_ohm", "Xc": "reatancia_ohm", "H": "estatura_cm", "W": "massa_kg", "target": "lmi_dxa", "control": "fmi_dxa",
         "covariates": "massa_kg,estatura_cm", "strata": "sexo", "id": "seqn", "independent": "yes"}


def test_suggest_only_when_unambiguous():
    s = suggest(["resistencia_ohm", "reatancia_ohm", "estatura_cm", "massa_kg", "sexo", "seqn", "lmi_dxa"])
    assert s["R"] == "resistencia_ohm" and s["Xc"] == "reatancia_ohm" and s["H"] == "estatura_cm" and s["W"] == "massa_kg" and s["strata"] == "sexo"
    assert suggest(["peso", "peso_kg", "R"])["W"] is None      # two candidates -> no suggestion


def test_init_from_flags_writes_valid_config_and_check_passes(tmp_path):
    out = init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "c.yaml"), map_flags=FLAGS, printer=lambda s: None)
    cfg = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert cfg["data"]["sep"] == ";" and cfg["data"]["decimal"] == "," and cfg["declarations"]["targets_independent_of_variables"] is True
    cfg["preset"] = "quick"; cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); (tmp_path / "c.yaml").write_text(yaml.safe_dump(cfg))
    rep = check(tmp_path / "c.yaml", printer=lambda s: None)
    assert not rep["errors"] and any("method(s) evaluable" in x for x in rep["info"])


def test_init_rejects_unknown_column_and_missing_required(tmp_path):
    with pytest.raises(InputError, match="not in file"):
        init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "x.yaml"), map_flags={**FLAGS, "R": "nope"}, printer=lambda s: None)
    with pytest.raises(InputError, match="required"):
        init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "x.yaml"), map_flags={k: v for k, v in FLAGS.items() if k != "target"}, printer=lambda s: None)


def test_check_blocks_design_without_declaration(tmp_path):
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); cfg["design"] = {"target": "LMI_DXA"}
    with pytest.raises(CheckError):
        check(cfg, printer=lambda s: None)
    cfg["declarations"] = {"targets_independent_of_variables": True}
    assert not check(cfg, printer=lambda s: None)["errors"]


def test_check_blocks_impossible_bootstrap(tmp_path):
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); cfg["audit"]["bootstrap"]["min_oob"] = 500
    with pytest.raises(CheckError):
        check(cfg, printer=lambda s: None)


def test_cli_init_and_check(tmp_path):
    env = {"PYTHONPATH": str(ROOT / "src"), "HOME": str(tmp_path), "PATH": ""}
    out = tmp_path / "c.yaml"
    r = subprocess.run([sys.executable, "-m", "bioms_zaku.cli", "init", str(ROOT / "examples/minimal_data.csv"), "-o", str(out), "--map"] + [f"{k}={v}" for k, v in FLAGS.items()],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr[-500:]
    r = subprocess.run([sys.executable, "-m", "bioms_zaku.cli", "check", str(out)], capture_output=True, text=True, env=env)
    assert r.returncode == 0 and "ready to run" in r.stdout, r.stdout + r.stderr[-300:]


def test_init_includes_whole_catalog_and_maps_equation_inputs(tmp_path):
    # EN: Colab finding 2026-09-14 — init must not hide the catalogue behind a fixed include list, and must let the user map
    #     the columns the equations need (sex, age, circumferences). check must name what is missing and how to map it.
    from bioms_zaku.wizard import init
    from bioms_zaku.check import check
    out = init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "a.yaml"), map_flags={**FLAGS, "age": "idade_anos"}, printer=lambda s: None)
    cfg = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert cfg["catalog"]["include"] == "curated" and cfg["data"]["columns"]["groups"] == {"sexo": "sexo", "idade": "idade_anos"}   # DESIGN: curated by default
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); (tmp_path / "a.yaml").write_text(yaml.safe_dump(cfg))
    lines = []; rep = check(str(tmp_path / "a.yaml"), printer=lines.append)
    txt = "\n".join(lines)
    assert "include = curated (8 methods" in txt and "non-curated entries exist and are NOT audited" in txt
    assert "catalog: 5 method(s) evaluable" in txt                                                    # II, PhA, R/H, Xc/H, LMI at 50 kHz without circumferences
    assert "need `C_arm`" in txt and "--map arm=<column>" in txt                                     # Rsp/Xcsp: circumferences not mapped, said so
    cfg["catalog"]["include"] = "all"; (tmp_path / "a.yaml").write_text(yaml.safe_dump(cfg)); lines = []; check(str(tmp_path / "a.yaml"), printer=lines.append)
    assert int("\n".join(lines).split("catalog: ")[1].split(" ")[0]) >= 20                          # explicit all: the equations too
    printed = []; init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "c.yaml"), map_flags=FLAGS, printer=printed.append)
    assert any("age" in l and "idade_anos" in l and "[suggested]" in l for l in printed)        # an unambiguous suggestion is applied AND printed
    out2 = init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "b.yaml"), map_flags={**FLAGS, "age": "none"}, printer=lambda s: None)
    cfg2 = yaml.safe_load(out2.read_text(encoding="utf-8")); cfg2["data"]["path"] = str(ROOT / "examples/minimal_data.csv")
    (tmp_path / "b.yaml").write_text(yaml.safe_dump(cfg2)); lines = []; check(str(tmp_path / "b.yaml"), printer=lines.append)
    assert "need `idade`" not in "\n".join(lines)            # curated set needs no age column; the hint appears only with include: all
    cfg2["catalog"]["include"] = "all"; cfg2["data"]["columns"]["groups"] = {"sexo": "sexo"}; (tmp_path / "b.yaml").write_text(yaml.safe_dump(cfg2))
    lines = []; check(str(tmp_path / "b.yaml"), printer=lines.append)
    assert "need `idade`" in "\n".join(lines) and "--map age=<column>" in "\n".join(lines)          # age not mapped: said so


def test_run_refuses_when_check_has_blocking_problems(tmp_path):
    # EN: user-audit finding (60 rows): run must not produce a report with every audit skipped; it stops with the check messages.
    from bioms_zaku.run import run
    from bioms_zaku.check import CheckError
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); cfg["output"]["dir"] = str(tmp_path); cfg["audit"]["bootstrap"]["min_oob"] = 500
    with pytest.raises(CheckError):
        run(cfg, printer=lambda s: None)
    assert not (tmp_path / "minimal" / "audit.csv").exists()


def test_init_explains_encoding_and_records_it(tmp_path):
    # EN: user-audit finding (Brazilian spreadsheet): no traceback on latin-1; the chosen encoding is written to the YAML.
    from bioms_zaku.wizard import init
    from bioms_zaku.io import InputError
    src = pd.read_csv(ROOT / "examples/minimal_data.csv", sep=";", decimal=",")
    p = tmp_path / "planilha.csv"; src.rename(columns={"resistencia_ohm": "resistência_ohm"}).to_csv(p, index=False, sep=";", decimal=",", encoding="latin-1")
    flags = {**FLAGS, "R": "resistência_ohm"}
    with pytest.raises(InputError, match="--encoding latin-1"):
        init(str(p), str(tmp_path / "x.yaml"), map_flags=flags, printer=lambda s: None)
    out = init(str(p), str(tmp_path / "y.yaml"), map_flags=flags, encoding="latin-1", printer=lambda s: None)
    cfg = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert cfg["data"]["encoding"] == "latin-1" and cfg["data"]["sep"] == ";" and cfg["data"]["decimal"] == ","
    from bioms_zaku.check import check
    check(str(out), printer=lambda s: None)          # EN: the YAML written by init passes check as is


def test_interactive_init_reasks_on_typo_refuses_control_equal_to_target_and_prints_independence(tmp_path):
    # EN: terminal-simulation findings (2026-09-14). Scripted answers: a typo for Xc (re-asked), control = target (re-asked).
    from bioms_zaku.wizard import init, suggest
    answers = iter(["", "", "reatancia_50_ohm", "reatancia_ohm", "", "", "", "", "lmi_dxa", "lmi_dxa", "fmi_dxa", "", "", "", "", "", "", "", "", "yes"])   # first answer = language (Enter → en)
    def ask(prompt, default):
        return next(answers)
    printed = []
    out = init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "i.yaml"), ask=ask, printer=printed.append)
    cfg = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert cfg["data"]["columns"]["variables"]["Xc"] == "reatancia_ohm" and cfg["data"]["columns"]["controls"] == {"FMI_DXA": "fmi_dxa"}
    assert any("is not in the file" in l for l in printed) and any("is the target itself" in l for l in printed)
    assert any(l.strip().startswith("independent") and "yes" in l for l in printed) and cfg["declarations"]["targets_independent_of_variables"] is True
    with pytest.raises(InputError, match="same as the target"):
        init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "j.yaml"), map_flags={**FLAGS, "control": FLAGS["target"]}, printer=lambda s: None)
    s = suggest(["id", "reatancia_50k_ohm", "resistencia_50k_ohm", "massa_corporal_kg", "estatura_cm"])
    assert s["Xc"] == "reatancia_50k_ohm" and s["W"] == "massa_corporal_kg" and s["R"] == "resistencia_50k_ohm"


def test_init_shows_language_with_its_origin_and_run_prints_an_open_command(tmp_path):
    from bioms_zaku.wizard import init
    from bioms_zaku.run import run
    printed = []; init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "l.yaml"), map_flags=FLAGS, lang="pt", printer=printed.append)
    assert any(l.strip().startswith("idioma") and "pt" in l and "[opção]" in l for l in printed)
    answers = iter(["it"] + [""] * 6 + ["lmi_dxa", "fmi_dxa"] + [""] * 8 + ["yes"])
    printed = []; init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "m.yaml"), ask=lambda p, d: next(answers), printer=printed.append)
    assert any(l.strip().startswith("lingua") and "it" in l and "[risposta]" in l for l in printed)
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8")); cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv")
    cfg["output"] = {"dir": str(tmp_path), "figures": False}; cfg["catalog"] = {"include": ["Lukaski1985_II"]}; cfg["audit"] = {"bootstrap": {"min_oob": 10}, "cv": {"folds": 3}}; cfg["language"] = "pt"
    lines = []; run(cfg, printer=lines.append)
    assert any(l.startswith("relatório: /") for l in lines) and any("cole isto no terminal:  xdg-open \"/" in l or "cole isto no terminal:  open \"/" in l for l in lines)
    from bioms_zaku.i18n import set_language; set_language("en")

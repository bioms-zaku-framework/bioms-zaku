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
    assert not rep["errors"] and any("methods evaluable" in x for x in rep["info"])


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
    assert cfg["catalog"]["include"] == "all" and cfg["data"]["columns"]["groups"] == {"sexo": "sexo", "idade": "idade_anos"}
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); (tmp_path / "a.yaml").write_text(yaml.safe_dump(cfg))
    lines = []; rep = check(str(tmp_path / "a.yaml"), printer=lines.append)
    txt = "\n".join(lines)
    assert "methods evaluable" in txt and int(txt.split("catalog: ")[1].split(" ")[0]) >= 20      # far more than five
    assert "need `C_arm`" in txt and "--map arm=<column>" in txt                                     # circumferences not mapped: said so
    printed = []; init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "c.yaml"), map_flags=FLAGS, printer=printed.append)
    assert any("age" in l and "idade_anos" in l and "[suggested]" in l for l in printed)        # an unambiguous suggestion is applied AND printed
    out2 = init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "b.yaml"), map_flags={**FLAGS, "age": "none"}, printer=lambda s: None)
    cfg2 = yaml.safe_load(out2.read_text(encoding="utf-8")); cfg2["data"]["path"] = str(ROOT / "examples/minimal_data.csv")
    (tmp_path / "b.yaml").write_text(yaml.safe_dump(cfg2)); lines = []; check(str(tmp_path / "b.yaml"), printer=lines.append)
    assert "need `idade`" in "\n".join(lines) and "--map age=<column>" in "\n".join(lines)          # age not mapped: said so

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

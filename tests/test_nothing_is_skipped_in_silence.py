"""
EN: two skips that used to happen without a word, both found on 2026-09-21 in a real run of the guided path.

1. A label declared for a stratum value that does not occur. The researcher typed `0=F,M=1` at the prompt; the parser
   splits on "=", so it stored a label for the value "M". The stratum 1 kept its raw value, the report said "stratum 1"
   instead of "stratum M", and nothing anywhere said why.
2. The whole geometry block (contract §3.3) skipped. Class labels are never projected, so a pair whose target or
   control is a class has no geometry; with no continuous pair at all, `geometry.csv` and `implicit_vectors.csv` come
   out empty. The run said nothing, and the report showed the section with two empty tables.

Neither was a wrong number: both were silence, which the project refuses.
"""
from pathlib import Path

import yaml

from bioms_zaku.check import check

ROOT = Path(__file__).resolve().parents[1]


def _cfg(tmp_path, **over):
    cfg = yaml.safe_load((ROOT / "tests/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "tests/minimal_data.csv")
    cfg["output"] = {"dir": str(tmp_path), "figures": False}
    cfg["strata"] = "sexo"
    cfg["data"]["columns"]["groups"] = {"sexo": "sexo"}
    cfg.update(over)
    return cfg


def test_a_label_for_a_value_that_does_not_exist_is_reported(tmp_path):
    cfg = _cfg(tmp_path, strata_labels={"0": "F", "M": "1"})          # EN: the exact mistake made on 2026-09-21
    avisos = check(cfg, printer=lambda s: None)["warnings"]
    achado = [w for w in avisos if "strata_labels" in w]
    assert achado, f"a label for an absent value must be reported; warnings: {avisos}"
    assert "'M'" in achado[0] and "0, 1" in achado[0], "the warning must name the bad value and the values present"

    cfg = _cfg(tmp_path, strata_labels={"0": "F", "1": "M"})          # EN: corrected, nothing to say
    assert not [w for w in check(cfg, printer=lambda s: None)["warnings"] if "strata_labels" in w]


def test_geometry_says_when_it_will_not_run(tmp_path):
    """EN: a class target with a continuous control leaves no pair for the geometry; say so before the run costs time."""
    cfg = _cfg(tmp_path, strata=None)            # EN: `diab` has a single class in one sex; the stratum is not the point here
    cfg["data"]["columns"].update({"targets": {"diab": "diab"}, "controls": {"FMI_DXA": "fmi_dxa"}})
    avisos = check(cfg, printer=lambda s: None)["warnings"]
    assert [w for w in avisos if "3.3" in w], f"the skipped geometry must be announced; warnings: {avisos}"

    cfg = _cfg(tmp_path, strata=None)                                 # EN: both sides continuous → geometry runs
    assert not [w for w in check(cfg, printer=lambda s: None)["warnings"] if "3.3" in w]


def test_the_skipped_geometry_reaches_the_manifest_and_the_report(tmp_path):
    """EN: `check` warns before; the manifest records it after, so a finished run carries the reason for the empty table."""
    from bioms_zaku.run import run
    cfg = _cfg(tmp_path, strata=None)
    cfg["data"]["columns"].update({"targets": {"diab": "diab"}, "controls": {"FMI_DXA": "fmi_dxa"}})
    cfg["preset"] = "quick"
    cfg["audit"] = {"bootstrap": {"min_oob": 10, "min_B_eff": 20}, "cv": {"folds": 3}}
    cfg["run_name"] = "sem_geometria"
    res = run(cfg, printer=lambda s: None)
    assert [w for w in res["manifest"]["warnings"] if "3.3" in w], res["manifest"]["warnings"]
    assert res["tables"]["geometry"].empty, "the guard must describe a real skip, not invent one"

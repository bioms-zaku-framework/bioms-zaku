"""EN: study identity (v0.9) — data name and researcher flow from init to YAML, hash, manifest, check and report; never into the tables."""
from pathlib import Path

import yaml

from bioms_zaku.i18n import set_language

ROOT = Path(__file__).resolve().parents[1]


def _cfg(tmp_path, name, **study):
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); cfg["output"] = {"dir": str(tmp_path), "figures": False}; cfg["run_name"] = name
    cfg["catalog"] = {"include": ["Lukaski1985_II", "Piccoli1994_RH"]}; cfg["audit"] = {"bootstrap": {"min_oob": 10}, "cv": {"folds": 3}}; cfg["language"] = "pt"
    if study:
        cfg["study"] = study
    return cfg


def test_init_records_data_name_and_researcher(tmp_path):
    from bioms_zaku.wizard import init
    flags = {"R": "resistencia_ohm", "Xc": "reatancia_ohm", "H": "estatura_cm", "W": "massa_kg", "target": "lmi_dxa", "control": "fmi_dxa", "independent": "yes",
             "data_name": "Amostra NHANES 300", "researcher": "Thalles Mota"}
    printed = []; out = init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "a.yaml"), map_flags=flags, lang="pt", printer=printed.append)
    cfg = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert cfg["study"] == {"data_name": "Amostra NHANES 300", "researcher": "Thalles Mota"}
    assert any(l.strip().startswith("dados") and "Amostra NHANES 300" in l for l in printed) and any(l.strip().startswith("pesquisador") and "Thalles Mota" in l for l in printed)
    flags.pop("data_name"); flags.pop("researcher")
    out = init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "b.yaml"), map_flags=flags, lang="pt", printer=lambda s: None)
    cfg = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert cfg["study"] == {"data_name": "minimal_data", "researcher": None}                 # defaults: file stem, nothing recorded
    set_language("en")


def test_study_reaches_hash_manifest_check_and_report_but_not_the_tables(tmp_path):
    from bioms_zaku.run import run
    from bioms_zaku.check import check
    a = run(_cfg(tmp_path, "a", data_name="Amostra NHANES 300", researcher="Thalles Mota"), printer=lambda s: None)
    b = run(_cfg(tmp_path, "b", data_name="Amostra NHANES 300", researcher="Outra Pessoa"), printer=lambda s: None)
    assert a["manifest"]["study"] == {"data_name": "Amostra NHANES 300", "researcher": "Thalles Mota"}
    assert a["manifest"]["config_sha256"] != b["manifest"]["config_sha256"]                  # the researcher is part of the hashed configuration
    assert a["manifest"]["outputs_sha256"] == b["manifest"]["outputs_sha256"]                # and never changes a table
    txt = (a["out_dir"] / "report.html").read_text(encoding="utf-8")
    assert "<h1><span>Dados:</span> Amostra NHANES 300</h1>" in txt and "<b>Pesquisador:</b> Thalles Mota</p>" in txt
    assert "<title>BioMS Zaku — Amostra NHANES 300</title>" in txt and "<td>Pesquisador</td><td>Thalles Mota</td>" in txt
    lines = []; check(_cfg(tmp_path, "c", data_name="Amostra NHANES 300", researcher="Thalles Mota"), printer=lines.append)
    assert any("dados: Amostra NHANES 300 · pesquisador: Thalles Mota" in l for l in lines)
    c = run(_cfg(tmp_path, "d"), printer=lambda s: None)                                     # no study block: file stem, no researcher line
    txt = (c["out_dir"] / "report.html").read_text(encoding="utf-8")
    assert "<h1><span>Dados:</span> minimal_data</h1>" in txt and "Pesquisador:</b>" not in txt and "<td>Pesquisador</td><td>—</td>" in txt
    set_language("en")

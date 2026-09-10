"""EN: end-to-end on the minimal example; determinism; CLI. ES/PT: ponta a ponta, determinismo, CLI."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _cfg(tmp_path, name="e2e"):
    cfg = yaml.safe_load((ROOT / "examples/minimo.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "examples/sintetico.csv"); cfg["output"]["dir"] = str(tmp_path); cfg["run_name"] = name
    return cfg


def _synthetic_csv(tmp_path, n=240, seed=5):
    rng = np.random.default_rng(seed)
    R = rng.uniform(380, 650, n); Xc = rng.uniform(40, 80, n); H = rng.uniform(150, 190, n); W = rng.uniform(48, 110, n)
    lean = 0.45 * W * (H / 170) ** 0.3 * (500 / R) ** 0.5 * np.exp(rng.normal(0, 0.05, n)); fat = W - lean
    df = pd.DataFrame(dict(seqn=np.arange(n), sexo=rng.integers(0, 2, n), idade_anos=rng.integers(18, 50, n), estatura_cm=H, massa_kg=W,
                           resistencia_ohm=R, reatancia_ohm=Xc, lmi_dxa=lean / (H / 100) ** 2, fmi_dxa=fat / (H / 100) ** 2,
                           diab=(fat / W > np.quantile(fat / W, 0.75)).astype(int)))
    p = tmp_path / "syn.csv"; df.to_csv(p, index=False); return p


def test_end_to_end_minimal_example_writes_all_outputs(tmp_path):
    from bioms_zaku.run import run
    res = run(_cfg(tmp_path), printer=lambda s: None)
    out = res["out_dir"]
    for f in ("algebra.csv", "sigma.csv", "pairs.csv", "redundancy.csv", "audit.csv", "utility.csv", "screening.csv", "manifest.json", "summary.md"):
        assert (out / f).exists(), f
    m = json.loads((out / "manifest.json").read_text())
    assert m["preset"] == "quick" and m["input_sha256"] and m["outputs_sha256"]["audit.csv"] and m["versions"]["sklearn"]
    assert "PRESET `quick`" in (out / "summary.md").read_text(encoding="utf-8")
    for f in ("board_all", "exponents", "predicted_observed"):
        assert (out / "figures" / f"{f}.png").exists() and (out / "figures" / f"{f}.pdf").exists(), f
    assert not any(c.startswith("seqn") for c in pd.read_csv(out / "audit.csv").columns)   # no row-level data


def test_determinism_two_runs_identical_hashes(tmp_path):
    from bioms_zaku.run import run
    m1 = run(_cfg(tmp_path, "a"), printer=lambda s: None)["manifest"]; m2 = run(_cfg(tmp_path, "b"), printer=lambda s: None)["manifest"]
    assert m1["outputs_sha256"] == m2["outputs_sha256"]


def test_strata_transfer_classification_and_design(tmp_path):
    from bioms_zaku.run import run
    p = _synthetic_csv(tmp_path)
    cfg = _cfg(tmp_path, "syn"); cfg["data"]["path"] = str(p); cfg["strata"] = "sexo"; cfg["data"]["min_n"] = 30   # top-level strata is the single source
    cfg["data"]["columns"]["targets"] = {"LMI_DXA": "lmi_dxa"}; cfg["data"]["columns"]["controls"] = {"FMI_DXA": "fmi_dxa"}
    cfg["design"] = {"target": "LMI_DXA", "split": "holdout", "fraction": 0.70, "seed": 42, "id": "designed_LMI"}; cfg["audit"]["bootstrap"]["min_oob"] = 5
    cfg["declarations"] = {"targets_independent_of_variables": True}   # EN: synthetic DXA targets are not computed from R, Xc, H, W
    res = run(cfg, printer=lambda s: None); t = res["tables"]
    assert "sigma_transfer" in t and len(t["sigma_transfer"]) == 4
    assert "designed_LMI" in set(t["algebra"].method_id) and res["manifest"]["design"]["n_audit"] == 72 and set(res["manifest"]["design"]["per_stratum"]) == {"0", "1"}
    assert not (res["out_dir"] / "figures" / "supplementary").exists()   # supplementary off by default
    # classification path: binary target with permuted-null control built in the CSV
    df = pd.read_csv(p); rng = np.random.default_rng(0); df["diab_perm"] = rng.permutation(df["diab"].to_numpy()); df.to_csv(p, index=False)
    cfg2 = _cfg(tmp_path, "cls"); cfg2["data"]["path"] = str(p); cfg2["data"]["columns"]["targets"] = {"DIAB": "diab"}
    cfg2["data"]["columns"]["controls"] = {"DIAB_PERM": "diab_perm"}; cfg2["data"]["min_n"] = 30
    a = run(cfg2, printer=lambda s: None)["tables"]["audit"]
    assert set(a.metric) == {"AUROC"} and (a.score_cv_control.between(0.3, 0.7)).all()


def test_cli_runs(tmp_path):
    cfg = _cfg(tmp_path, "cli"); p = tmp_path / "c.yaml"; p.write_text(yaml.safe_dump(cfg))
    env = {"PYTHONPATH": str(ROOT / "src")}
    r = subprocess.run([sys.executable, "-m", "bioms_zaku.cli", "run", str(p)], capture_output=True, text=True, env={**env, "PATH": ""} | {"HOME": str(tmp_path)})
    assert r.returncode == 0, r.stderr[-800:]
    assert (tmp_path / "cli" / "manifest.json").exists()


def test_strata_conflict_is_an_error(tmp_path):
    from bioms_zaku.run import run
    cfg = _cfg(tmp_path, "conf"); cfg["strata"] = "sexo"; cfg["data"]["columns"]["strata"] = "idade_anos"
    with pytest.raises(ValueError, match="strata declared twice"):
        run(cfg, printer=lambda s: None)


def test_validity_flag_and_strata_labels(tmp_path):
    from bioms_zaku.run import run
    p = _synthetic_csv(tmp_path)
    cfg = _cfg(tmp_path, "val"); cfg["data"]["path"] = str(p); cfg["strata"] = "sexo"; cfg["strata_labels"] = {0: "F", 1: "M"}
    cfg["data"]["min_n"] = 30; cfg["audit"]["bootstrap"]["min_oob"] = 5
    cfg["data"]["columns"]["targets"] = {"LMI_DXA": "lmi_dxa"}; cfg["data"]["columns"]["controls"] = {"FMI_DXA": "fmi_dxa"}
    t = run(cfg, printer=lambda s: None)["tables"]["algebra"]
    assert set(t.stratum) == {"F", "M"}
    lima = t[(t.method_id == "Lima2008_SMM") & (t.stratum == "F")]
    assert len(lima) == 1 and lima.out_of_validity_frac.iloc[0] == 1.0 and "sex" in lima.out_of_validity_fields.iloc[0]


def test_figure_customisation_title_language_palette(tmp_path):
    from bioms_zaku.run import run
    cfg = _cfg(tmp_path, "fig"); cfg["figures"] = {"title": "Meu título", "subtitle": "sub", "language": "pt", "labels": "short",
                                                    "palette": {"specific": "#1f77b4"}, "formats": ["png"], "dpi": 100}
    res = run(cfg, printer=lambda s: None); fd = res["out_dir"] / "figures"
    assert (fd / "board_all.png").exists() and not (fd / "board_all.pdf").exists()
    txt = (fd / "README.md").read_text(encoding="utf-8")
    assert txt.index("**PT**") < txt.index("**EN**")     # chosen language first

"""EN: v1.1 — the audit runs on the logarithmic scale by default (the algebra's scale); the raw scale is reported as sensitivity,
never selected; a non-positive continuous target falls back to raw with a warning; classification labels are never transformed."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bioms_zaku.i18n import set_language
from bioms_zaku.run import scaled_inputs
from test_design_orthogonal import _frame

ROOT = Path(__file__).resolve().parents[1]


def test_scaled_inputs_logs_positive_continuous_inputs_and_falls_back_on_nonpositive():
    vals = {"m": np.array([1.0, np.e, 0.0, np.nan])}; targets = {"t": np.array([1.0, 2.0, 3.0, 4.0])}; controls = {"c": np.array([2.0, 2.0, 2.0, 2.0])}
    cov = np.array([[1.0, 10.0], [2.0, 10.0], [3.0, 10.0], [4.0, 10.0]]); w = []
    sc = scaled_inputs(vals, targets, controls, cov, {"t": "regression", "c": "regression"}, "log", "all", w)
    assert sc["scale"] == "log" and np.allclose(sc["vals"]["m"][:2], [0.0, 1.0]) and np.isnan(sc["vals"]["m"][2]) and np.isnan(sc["vals"]["m"][3])
    assert np.allclose(sc["targets"]["t"], np.log([1, 2, 3, 4])) and np.allclose(sc["cov"][:, 1], np.log(10.0)) and w == []
    sc = scaled_inputs(vals, {"t": np.array([1.0, -2.0, 3.0, 4.0])}, controls, cov, {"t": "regression", "c": "regression"}, "log", "F", w)
    assert sc["scale"] == "raw" and w and "raw scale" in w[0] and "t has non-positive" in w[0]
    lab = {"y": np.array([0, 1, 0, 1])}
    sc = scaled_inputs(vals, lab, {"c": controls["c"]}, None, {"y": "classification", "c": "regression"}, "log", "all", [])
    assert np.array_equal(sc["targets"]["y"], lab["y"]) and sc["scale"] == "log"            # labels untouched
    assert scaled_inputs(vals, targets, controls, cov, {}, "raw", "all", [])["scale"] == "raw"


def _cfg(tmp_path, n=700, **audit):
    p = tmp_path / "s.csv"; _frame(n=n, seed=21).to_csv(p, index=False)
    return {"run_name": "s", "language": "pt", "preset": "quick", "data": {"path": str(p), "columns": {"variables": {"R": "R", "Xc": "Xc", "H": "H", "W": "W"},
            "units": {"H": "cm", "W": "kg"}, "targets": {"lean": "lean"}, "controls": {"fat": "fat"}, "covariates": ["W", "H"], "id": "seqn"}},
            "catalog": {"include": ["Lukaski1985_II", "Piccoli1994_XcH"]}, "output": {"dir": str(tmp_path), "figures": False},
            "audit": {"bootstrap": {"min_oob": 20, "B": 60}, "cv": {"folds": 3, "repeats": 1}, **audit}}


def test_log_scale_is_primary_raw_scale_is_reported_and_never_selected(tmp_path):
    from bioms_zaku.run import run
    cfg = _cfg(tmp_path, sensitivity={"scale": True}); cfg["preset"] = "full"          # EN: the preset overrides audit sizes; 'full' keeps the user's small B and CV here
    res = run(cfg, printer=lambda s: None)
    a = res["tables"]["audit"]; assert set(a.scale) == {"log"} and set(res["tables"]["utility"].scale) == {"log"}
    ss = res["tables"]["sensitivity_scale"]; assert len(ss) == len(a) and set(ss.scale) == {"raw"} and set(ss.scale_primary) == {"log"}
    assert set(ss.verdict_primary) <= {"SPECIFIC", "TRACKS_CONTROL", "BOTH", "NEITHER"} and ((ss.s1_delta == ss.s1_mean - ss.s1_primary).all())
    # the constructed target is a product of powers times lognormal noise: on the log scale Lukaski (H²/R, the lean direction) gains more than on the raw scale
    lk = a[(a.method_id == "Lukaski1985_II") & (a.target == "lean")].iloc[0]; lk_raw = ss[(ss.method_id == "Lukaski1985_II") & (ss.target == "lean")].iloc[0]
    assert lk.verdict == "SPECIFIC" and lk.s1_mean >= lk_raw.s1_mean - 0.05
    summ = (res["out_dir"] / "summary.md").read_text(encoding="utf-8"); txt = (res["out_dir"] / "report.html").read_text(encoding="utf-8")
    assert "Sensibilidade à escala da auditoria" in summ and "Escala primária log" in summ and "entraram na auditoria como logaritmos (log)" in txt
    assert "sensitivity_scale.csv" in res["manifest"]["outputs_sha256"]
    set_language("en")


def test_raw_scale_when_requested_or_forced_and_quick_preset_skips_the_scale_sensitivity(tmp_path):
    from bioms_zaku.run import run
    res = run(_cfg(tmp_path, scale="raw"), printer=lambda s: None)
    assert set(res["tables"]["audit"].scale) == {"raw"} and res["tables"]["sensitivity_scale"].empty       # quick preset: scale sensitivity off by default
    txt = (res["out_dir"] / "report.html").read_text(encoding="utf-8"); assert "escala bruta (raw)" in txt
    df = _frame(n=700, seed=21); df.loc[:4, "fat"] = -1.0; p = tmp_path / "neg.csv"; df.to_csv(p, index=False)
    cfg = _cfg(tmp_path); cfg["data"]["path"] = str(p); cfg["run_name"] = "neg"
    res = run(cfg, printer=lambda s: None)
    assert set(res["tables"]["audit"].scale) == {"raw"} and any("audit on the raw scale — fat has non-positive values" in w for w in res["manifest"]["warnings"])
    set_language("en")


def test_check_prints_the_scale(tmp_path):
    from bioms_zaku.check import check
    lines = []; check(_cfg(tmp_path), printer=lines.append)
    assert any("escala da auditoria: log" in l for l in lines)
    set_language("en")

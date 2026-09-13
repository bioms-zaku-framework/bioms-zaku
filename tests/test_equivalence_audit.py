"""
EN: exact equivalence of the audit with the previous engine (NHANES 2026-09-09, blocks B and E) on a subset of methods,
    with the full article-preset parameters (5×50 CV, B=2000). Skips when the reference data are absent. Slow (~4 min).
ES/PT: equivalência exata da auditoria com o motor anterior (blocos B e E) num subconjunto de métodos.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import rankdata

from bioms_zaku.audit import AuditConfig, audit_method, utility_method
from bioms_zaku.catalog import load_catalog
from bioms_zaku.io import read_table

NH = Path.home() / "Desktop/bioms_2/nhanes"
REF_B = NH / "resultados/B_controle_negativo.csv"; REF_E = NH / "resultados/E_utilidade.csv"
TOL = 1e-9
SUBSET = {"LMI (Levi Micheli 2022)": "LMI", "Schifferli 2011 [FFM]": "Schifferli2011_FFM", "Kyle 2001 [FFM]": "Kyle2001_FFM"}
MAPPING = {"variables": {"R": "R", "Xc": "Xc", "H": "H_cm", "W": "W"}, "units": {"H": "cm", "W": "kg"},
           "targets": {"ALMI_DXA": "ALMI_DXA", "LMI_DXA": "LMI_DXA"}, "controls": {"FMI_DXA": "FMI_DXA"}, "strata": "sexo",
           "groups": {"sexo": "sexo", "idade": "idade"}, "id": "SEQN"}


def _rr(y, x):
    # EN: the previous engine's rank-residual target (LMI adjusted for FMI within stratum)
    ry, rx = rankdata(y), rankdata(x); ry = (ry - ry.mean()) / ry.std(); rx = (rx - rx.mean()) / rx.std()
    return ry - (ry @ rx / len(ry)) * rx


@pytest.fixture(scope="module")
def ref():
    if not REF_B.exists():
        pytest.skip("reference NHANES data not on this machine")
    ds = read_table(NH / "nhanes_limpo.csv", MAPPING); cat = load_catalog()
    return ds, cat, pd.read_csv(REF_B).query("influentes=='com' and estrato=='H'").set_index("metodo"), \
        pd.read_csv(REF_E).query("influentes=='com' and estrato=='H'").set_index("metodo")


@pytest.mark.slow
def test_block_B_specificity_matches_previous_engine(ref):
    ds, cat, B, _ = ref
    frame = ds.frame[ds.frame.sexo == 1].reset_index(drop=True)
    env = {c: frame[c].to_numpy(float) for c in ds.variables + ds.derived + ds.groups}
    targets = {"ALMI_DXA": frame.ALMI_DXA.to_numpy(float), "LMI_DXA": frame.LMI_DXA.to_numpy(float)}
    ctrl = {"FMI_DXA": frame.FMI_DXA.to_numpy(float)}
    targets["LMI_adj"] = _rr(targets["LMI_DXA"], ctrl["FMI_DXA"])
    cfg = AuditConfig(cv_repeats=50, B=2000, min_oob=20, seed_cv=42, seed_bootstrap=42)
    for label, mid in SUBSET.items():
        x = np.asarray(cat[mid].evaluate(env), float)
        rows = {r.target: r for r in audit_method(mid, "H", x, targets, ctrl, {t: "FMI_DXA" for t in targets}, cfg)}
        ref = B.loc[label]
        assert rows["ALMI_DXA"].n == ref.n and rows["ALMI_DXA"].B_eff == ref.B_eff
        assert abs(rows["ALMI_DXA"].score_cv_target - ref.R2_ALMI_DXA) < TOL and abs(rows["LMI_DXA"].score_cv_target - ref.R2_LMI_DXA) < TOL
        assert abs(rows["ALMI_DXA"].score_cv_control - ref.R2_FMI_DXA) < TOL and abs(rows["LMI_adj"].score_cv_target - ref.R2_LMI_adj) < TOL
        for t, k in (("ALMI_DXA", "ALMI"), ("LMI_DXA", "LMI"), ("LMI_adj", "LMIadj")):
            r = rows[t]
            assert abs(r.disc_mean - ref[f"disc_{k}"]) < TOL and abs(r.disc_lo - ref[f"disc_{k}_lo"]) < TOL and abs(r.disc_hi - ref[f"disc_{k}_hi"]) < TOL, (label, t)
            assert abs(r.p_disc - ref[f"P_{k}"]) < TOL
            assert {"SPECIFIC": "ESPECÍFICO", "MEASURES_CONTROL": "MEDE GORDURA", "INCONCLUSIVE": "INCONCLUSIVO"}[r.verdict_marginal] == ref[f"verd_{k}"], (label, t)


@pytest.mark.slow
def test_block_E_utility_matches_previous_engine(ref):
    ds, cat, _, E = ref
    frame = ds.frame[ds.frame.sexo == 1].reset_index(drop=True)
    env = {c: frame[c].to_numpy(float) for c in ds.variables + ds.derived + ds.groups}
    cov = np.column_stack([frame.W.to_numpy(float), frame.H_m.to_numpy(float)])   # previous engine: (W, H_m)
    targets = {"ALMI_DXA": frame.ALMI_DXA.to_numpy(float), "LMI_DXA": frame.LMI_DXA.to_numpy(float), "FMI_DXA": frame.FMI_DXA.to_numpy(float)}
    cfg = AuditConfig(cv_repeats=50, B=2000, min_oob=20, seed_cv=42, seed_bootstrap=42, utility_margin=0.03)
    for label, mid in SUBSET.items():
        x = np.asarray(cat[mid].evaluate(env), float)
        rows = {u.target: u for u in utility_method(mid, "H", x, cov, ["W", "H_m"], targets, cfg)}
        ref = E.loc[label]
        for t in targets:
            u = rows[t]
            assert abs(u.score_base - ref[f"R2A_{t}"]) < TOL and abs(u.score_with - ref[f"R2B_{t}"]) < TOL, (label, t)
            assert abs(u.delta_mean - ref[f"dR2_{t}"]) < TOL and abs(u.delta_lo - ref[f"dR2_{t}_lo"]) < TOL and abs(u.delta_hi - ref[f"dR2_{t}_hi"]) < TOL, (label, t)
            assert abs(u.p_delta - ref[f"P_{t}"]) < TOL and u.useful == bool(ref[f"util_{t}"]), (label, t)

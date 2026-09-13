"""
EN: equivalence of the algebra with the reference NHANES run (2026-09-09): fitted exponents, fit R², redundancy maxima,
    and Σ-transfer statistics. Skips when the reference data are not on this machine.
ES/PT: equivalência da álgebra com a referência NHANES; pula se os dados não estiverem na máquina.
"""
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from bioms_zaku.algebra import (fit_log_linear, log_covariance, pairs_table, compute_vectors, sigma_transfer_table_legacy)
from bioms_zaku.catalog import Catalog, Entry, load_catalog
from bioms_zaku.expr import compile_expr
from bioms_zaku.io import read_table

NH = Path.home() / "Desktop/bioms_2/nhanes"
REF_C = NH / "resultados/C_redundancia.csv"
REF_D = NH / "resultados/D_previsao_sigma.csv"
TOL = 1e-9        # EN: non-rank statistics (fitted exponents, R², Pearson-of-logs)
TOL_RANK = 1e-6   # EN: rank statistics (Spearman): the reference CSV carries 1-ulp differences in derived columns (H_m, II)
                  #     that break/merge ties among 2805 rows and shift Spearman by ~3e-7 (verified 2026-09-10)

# EN: reference method label -> catalog id (28 methods; Segal fat-specific excluded by declared exception §5)
MAP_IDS = {
    "II h²/R (Lukaski 1985)": "Lukaski1985_II", "PhA (Baumgartner 1988)": "Baumgartner1988_PhA", "R/H (Piccoli 1994)": "Piccoli1994_RH",
    "Xc/H (Piccoli 1994)": "Piccoli1994_XcH", "LMI (Levi Micheli 2022)": "LMI", "BMI (Quetelet 1832)": "BMI_test",
    "Rsp (Marini/Buffa 2013)": "Rsp", "Xcsp (Marini/Buffa 2013)": "Xcsp", "Lukaski 1986 [FFM]": "Lukaski1986_FFM",
    "Kushner & Schoeller 1986 [TBW_L]": "Kushner1986_TBW", "Heitmann 1990 [FFM]": "Heitmann1990_FFM", "Deurenberg 1991 [FFM]": "Deurenberg1991_FFM",
    "Kyle 2001 [FFM]": "Kyle2001_FFM", "Macias 2007 [FFM]": "Macias2007_FFM", "Schifferli 2011 [FFM]": "Schifferli2011_FFM",
    "Schifferli 2020 [FFM]": "Schifferli2020_FFM_adj", "Janssen 2000 [SMM]": "Janssen2000_SMM", "Kyle 2003 [ASMM]": "Kyle2003_ASMM",
    "Sergi 2015 [ASMM]": "Sergi2015_ASMM", "Scafoglieri 2017 [ALM]": "Scafoglieri2017_ALM", "Campa 2026 [SMM]": "Campa2026_SMM",
    "Segal 1988 generalizada [LBM]": "Segal1988_gen_LBM", "Segal 1988 específica gordura [LBM]": "SegalSpec_test",
    "Gray 1989 [FFM]": "Gray1989_FFM", "Sun 2003 [FFM]": "Sun2003_FFM", "Sun 2003 [TBW_L]": "Sun2003_TBW",
    "Lima 2008 [SMM] (só homens)": "Lima2008_SMM", "Houtkooper 1992 [FFM] (fora da faixa etária)": "Houtkooper1992_FFM",
}
MAPPING = {"variables": {"R": "R", "Xc": "Xc", "H": "H_cm", "W": "W"}, "units": {"H": "cm", "W": "kg"},
           "targets": {"LMI_DXA": "LMI_DXA"}, "controls": {"FMI_DXA": "FMI_DXA", "FM_DXA_kg": "FM_DXA_kg"}, "strata": "sexo",
           "groups": {"sexo": "sexo", "idade": "idade", "C_arm": "BMXARMC", "C_waist": "BMXWAIST", "C_calf": "BMXCALF"}, "id": "SEQN"}


def _pseudo(cat: Catalog, mid: str, year: int, expr: str | None = None, branches: dict | None = None, branch_group: str | None = None) -> None:
    """EN: test-only entries reproducing the reference run: BMI (Quetelet 1832, anthropometric, not in the BIA catalog) and
    Segal fat-specific selected by DXA fat% (the reference's leakage; forbidden by the framework, reproduced here only to
    prove the algebra is identical)."""
    allowed = ["R", "Xc", "H", "H_m", "W", "PhA", "II", "Z", "sexo", "idade", "fat_class"]
    exprs = {None: compile_expr(expr, allowed)} if expr else {k: compile_expr(v, allowed) for k, v in branches.items()}
    cat.entries.append(Entry(id=mid, label=mid, authors="test", year=year, doi="test", kind="index", target="test", form="composite",
                             frequency_khz=(50.0,), validity={}, provenance={"confidence": "low"}, exprs=exprs, branch_group=branch_group))


@pytest.fixture(scope="module")
def ref():
    if not (NH / "nhanes_limpo.csv").exists() or not REF_C.exists():
        pytest.skip("reference NHANES data not on this machine")
    ds = read_table(NH / "nhanes_limpo.csv", MAPPING)
    cat = load_catalog()
    _pseudo(cat, "BMI_test", 1832, expr="W / H_m**2")
    seg = load_catalog()["Segal1988_spec_LBM"]
    _pseudo(cat, "SegalSpec_test", 1988, branches={k: v.source for k, v in seg.exprs.items()}, branch_group="fat_class")
    C = pd.read_csv(REF_C); D = pd.read_csv(REF_D)
    return ds, cat, C[C.influentes == "com"], D


def _values(ds, cat, frame):
    env = {c: frame[c].to_numpy(float) for c in ds.variables + ds.derived + ds.groups}
    # EN: reference Segal fat-specific branch: DXA fat% (<20 men / <30 women = lean). Test-only reproduction of the leakage.
    fat = 100 * frame["FM_DXA_kg"].to_numpy(float) / env["W"]
    sexm = env["sexo"] == 1
    frame = frame.copy()
    frame["fat_class"] = np.where(sexm, np.where(fat < 20, 1, 2), np.where(fat < 30, 3, 4))
    env["fat_class"] = frame["fat_class"].to_numpy(float)
    vals = {}
    for e in cat.entries:
        if e.form == "closed" or set(e.inputs) - set(env):
            continue
        # EN: Lima 2008 was applied to men only in the reference
        v = e.evaluate(env, frame[e.branch_group].to_numpy() if e.branch_group else None)
        if e.id == "Lima2008_SMM":
            v = np.where(env["sexo"] == 1, v, np.nan)
        vals[e.id] = np.asarray(v, float)
    # EN: the reference excluded Heitmann TBW (invalid transcription); the catalog Segal fat-specific entry is replaced by
    #     the test-only SegalSpec_test (DXA-selected, as in the reference).
    vals.pop("Heitmann1990_TBW", None); vals.pop("Segal1988_spec_LBM", None)
    return vals


def test_fitted_exponents_and_r2_match_reference(ref):
    ds, cat, C, _ = ref
    for stratum, sx in (("H", 1), ("M", 0)):
        frame = ds.frame[ds.frame["sexo"] == sx].reset_index(drop=True)
        vals = _values(ds, cat, frame)
        Cs = C[C.estrato == stratum].set_index("metodo")
        checked = 0
        for label, mid in MAP_IDS.items():
            if mid is None or mid not in vals or label not in Cs.index:
                continue
            beta, r2, n, _ = fit_log_linear(vals[mid], frame, ["R", "Xc", "H", "W"])
            row = Cs.loc[label]
            assert abs(r2 - row.P2_r2) < TOL, (stratum, label, r2, row.P2_r2)
            assert np.allclose(beta, [row.e_R, row.e_Xc, row.e_h, row.e_W], atol=TOL), (stratum, label, beta)
            assert n == row.n, (stratum, label, n, row.n)
            checked += 1
        assert checked >= 25, checked


def test_redundancy_maxima_match_reference_under_reference_rule(ref):
    # EN: the reference used "earlier year" (strict) as the precedence rule; v1 uses year>date>DOI. We check the
    #     observed Spearman maxima under the reference rule to prove the correlations themselves are identical.
    ds, cat, C, _ = ref
    year = {e.id: e.year for e in cat.entries}
    for stratum, sx in (("H", 1), ("M", 0)):
        frame = ds.frame[ds.frame["sexo"] == sx].reset_index(drop=True)
        vals = _values(ds, cat, frame)
        Cs = C[C.estrato == stratum].set_index("metodo")
        checked = 0
        for label, mid in MAP_IDS.items():
            if mid is None or mid not in vals or label not in Cs.index or not np.isfinite(Cs.loc[label].red_max):
                continue
            v = vals[mid]; ok = np.isfinite(v)
            best = -1.0
            for lab2, mid2 in MAP_IDS.items():
                if mid2 is None or mid2 not in vals or year[mid2] >= year[mid]:
                    continue
                o = vals[mid2]; okk = ok & np.isfinite(o)
                if okk.sum() > 30:
                    best = max(best, abs(spearmanr(v[okk], o[okk])[0]))
            if best >= 0:
                assert abs(best - Cs.loc[label].red_max) < TOL_RANK, (stratum, label, best, Cs.loc[label].red_max)
                checked += 1
        assert checked >= 20, checked


def test_sigma_transfer_matches_reference_D(ref):
    ds, cat, _, D = ref
    strata = {"H": ds.frame.sexo == 1, "M": ds.frame.sexo == 0}
    for e_code, name in ((1, "MexAm"), (3, "BrancoNH"), (4, "NegroNH")):
        strata[f"H-{name}"] = (ds.frame.sexo == 1) & (ds.frame.RIDRETH1 == e_code) if "RIDRETH1" in ds.frame else None
    # EN: ethnicity is not in the canonical frame; rebuild from the raw file for this test only.
    raw = pd.read_csv(NH / "nhanes_limpo.csv")
    assert len(raw) == len(ds.frame)
    vecs_by, sig_by, pairs_by = {}, {}, {}
    for sx, lab in ((1, "H"), (0, "M")):
        for e_code, name in ((None, ""), (1, "-MexAm"), (3, "-BrancoNH"), (4, "-NegroNH")):
            mask = (raw.sexo == sx) & ((raw.RIDRETH1 == e_code) if e_code else True)
            frame = ds.frame[mask.to_numpy()].reset_index(drop=True)
            vals = _values(ds, cat, frame)
            vals = {k: v for k, v in vals.items() if k not in ("Rsp", "Xcsp")}
            S, _ = log_covariance(frame, ["R", "Xc", "H", "W"])
            vecs = compute_vectors(cat, vals, frame, ["R", "Xc", "H", "W"], lab + name)
            # EN: declared exception (§5): the reference engine used LINEARISED vectors for PhA (−1, 1, 0, 0) and LMI
            #     (−2, 1, 1, 0), i.e. atan(x) ≈ x. Since catalog 1.1.0 both are composite with fitted vectors (exactness
            #     rule §2.3). To prove the Σ-transfer machinery itself is identical, the reference convention is
            #     reproduced here, test-only, for these two methods.
            # PT: exceção declarada — o motor anterior linearizava PhA e LMI; aqui a convenção antiga é reproduzida só no teste.
            for mid, lin in (("Baumgartner1988_PhA", (-1.0, 1.0, 0.0, 0.0)), ("LMI", (-2.0, 1.0, 1.0, 0.0))):
                if mid in vecs:
                    vecs[mid] = replace(vecs[mid], vector=np.array(lin), source="catalog-linearised (reference convention, test-only)", fit_r2=1.0)
            vecs_by[lab + name] = vecs; sig_by[lab + name] = S
            pairs_by[lab + name] = pairs_table(cat, vecs, vals, S, lab + name, min_pair_n=30)
    # EN: declared exception (§5): the reference used the Spearman conversion and the Fisher-CI fraction; since v0.5 the
    #     official table uses the n-fair metric (median error, tolerance, person bootstrap). The legacy function reproduces
    #     the reference computation exactly and exists only for this test.
    T = sigma_transfer_table_legacy(vecs_by, sig_by, pairs_by, exclude_identity=False)
    checked = 0
    for _, d in D.iterrows():
        t = T[(T.sigma_from == d.Sigma_de) & (T.observed_in == d.observado_em)]
        assert len(t) == 1, (d.Sigma_de, d.observado_em)
        t = t.iloc[0]
        assert t.pairs == d.pares, (d.Sigma_de, d.observado_em, t.pairs, d.pares)
        assert abs(t.median_abs_err_sp - d.erro_mediano) < TOL_RANK and abs(t.max_abs_err_sp - d.erro_max) < TOL_RANK, (d.Sigma_de, d.observado_em)
        # EN: within-CI is a discrete count; a single near-boundary pair may flip with the ~3e-7 rank shift -> allow 1 pair
        assert abs(t.within_ci_frac - d.dentro_IC) <= 1.0 / d.pares + 1e-12, (d.Sigma_de, d.observado_em, t.within_ci_frac, d.dentro_IC)
        checked += 1
    assert checked == len(D)

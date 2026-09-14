"""
EN: the shipped example is a KNOWN TRUTH: (1) it is reproducible byte for byte from its published parameters; (2) its logs
    have the published μ and Σ up to sampling error; (3) the published Σ predicts the observed correlation between
    monomial indices (the central identity of the method) without touching any external data.
ES/PT: o exemplo embarcado é verdade conhecida: reproduzível a partir dos parâmetros publicados; μ e Σ batem; a Σ
    publicada prevê a correlação observada entre índices monomiais.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from bioms_zaku.algebra import predicted_pearson_log

ROOT = Path(__file__).resolve().parents[1]
CSV, PARAMS = ROOT / "examples/example_data.csv", ROOT / "examples/example_data_params.json"


def _load():
    return pd.read_csv(CSV), json.loads(PARAMS.read_text(encoding="utf-8"))


def test_generator_reproduces_shipped_csv_from_published_parameters(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "tools/make_example_data.py"), "--from-params", str(PARAMS), str(tmp_path)],
                   check=True, capture_output=True)
    assert (tmp_path / "example_data.csv").read_bytes() == CSV.read_bytes()


def test_synthetic_example_matches_published_parameters():
    df, P = _load()
    assert len(df) == 2 * P["n_per_sex"] and set(df.sexo) == {0, 1} and P["label"]["name"] in df
    for key, sex in (("F", 0), ("M", 1)):
        L = np.log(df[df.sexo == sex][P["variables"]].to_numpy(float))
        mu, S = np.array(P["per_sex"][key]["mu_log"]), np.array(P["per_sex"][key]["sigma_log"])
        assert np.abs(L.mean(axis=0) - mu).max() < 0.02          # EN: sampling + rounding (age is clipped to integers)
        D = np.abs(np.cov(L.T, ddof=1) - S); ia = P["variables"].index("idade")
        age_mask = np.zeros_like(D, dtype=bool); age_mask[ia, :] = True; age_mask[:, ia] = True
        assert D[~age_mask].max() < 0.005                        # EN: continuous variables: sampling error only
        assert D[age_mask].max() < 0.03                          # EN: age is rounded to whole years and clipped to 18-49
        assert P["per_sex"][key]["n_source"] > 2000
    assert (df[P["variables"]] > 0).all().all()


def test_published_sigma_predicts_observed_correlation_between_monomial_indices():
    # EN: the method's identity ρ_log = aᵀΣb/√(aᵀΣa·bᵀΣb), checked against the PUBLISHED Σ (known truth, not a refit).
    #     With the sample Σ the identity is exact (tests/test_algebra.py); with the published Σ it holds to sampling error.
    df, P = _load(); V = ["R", "Xc", "H_cm", "W"]; idx = [P["variables"].index(v) for v in V]
    vectors = {"II": np.array([-1, 0, 2, 0.]), "R/H": np.array([1, 0, -1, 0.]), "Xc/H": np.array([0, 1, -1, 0.]),
               "W/H2": np.array([0, 0, -2, 1.])}
    for key, sex in (("F", 0), ("M", 1)):
        d = df[df.sexo == sex]; L = np.log(d[V].to_numpy(float))
        S_pub = np.array(P["per_sex"][key]["sigma_log"])[np.ix_(idx, idx)]; S_obs = np.cov(L.T, ddof=1)
        names = list(vectors); worst = 0.0
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = vectors[names[i]], vectors[names[j]]
                rho_obs = np.corrcoef(L @ a, L @ b)[0, 1]
                assert abs(predicted_pearson_log(a, b, S_obs) - rho_obs) < 1e-12          # exact identity
                worst = max(worst, abs(predicted_pearson_log(a, b, S_pub) - rho_obs))     # known truth vs observed
        assert worst < 0.02, f"{key}: published Σ misses observed ρ by {worst:.4f}"


def test_geometry_on_shipped_example_reproduces_hand_numbers_and_identity():
    # EN: contract §3.3 gate — the four Σ-cosines computed by hand on 2026-09-14 (with the same functions, on all rows per sex)
    #     must come out of geometry_tables, and the identity r_log = cos·√R² must be exact on the monomial indices.
    from bioms_zaku.algebra import compute_vectors, geometry_tables
    from bioms_zaku.catalog import load_catalog
    from bioms_zaku.io import read_table
    from bioms_zaku.run import _values
    mapping = {"variables": {"R": "R", "Xc": "Xc", "H": "H_cm", "W": "W"}, "units": {"H": "cm", "W": "kg"},
               "targets": {"LMI_DXA": "LMI_DXA"}, "controls": {"FMI_DXA": "FMI_DXA"}, "pairing": {"LMI_DXA": "FMI_DXA"}, "strata": "sexo",
               "groups": {"sexo": "sexo", "C_arm": "BMXARMC", "C_waist": "BMXWAIST", "C_calf": "BMXCALF"}}   # circumferences: Rsp/Xcsp need them
    ds = read_table(CSV, mapping); cat = load_catalog()
    keep = {"Lukaski1985_II", "Baumgartner1988_PhA", "Piccoli1994_RH", "Piccoli1994_XcH", "LMI", "Rsp", "Xcsp"}
    expected = {"F": (0.899, 0.928), "M": (0.855, 0.909)}          # (cos target–control, cos Rsp–control), hand-computed 2026-09-14
    for sex, name in ((0, "F"), (1, "M")):
        fr = ds.frame[ds.frame["sexo"] == sex]
        vals, _ = _values(cat, ds, fr); vals = {k: v for k, v in vals.items() if k in keep}
        vecs = compute_vectors(cat, vals, fr, ds.variables, name)
        imp, geo = geometry_tables(vecs, vals, fr, ds.variables, {"LMI_DXA": fr["LMI_DXA"].to_numpy(float)},
                                   {"FMI_DXA": fr["FMI_DXA"].to_numpy(float)}, {"LMI_DXA": "FMI_DXA"}, name)
        assert set(geo.method_id) == keep and len(imp) == 2
        g = geo.set_index("method_id")
        assert abs(g.cos_target_control.iloc[0] - expected[name][0]) < 2e-3
        assert abs(g.loc["Rsp", "cos_control"] - expected[name][1]) < 2e-3
        mono = g[g.vector_source == "catalog"]
        assert len(mono) == 3 and mono.r_log_target_gap.abs().max() < 1e-9 and mono.r_log_control_gap.abs().max() < 1e-9
        assert bool(g.loc["Rsp", "flag_parallel_to_control"]) and not bool(g.loc["Lukaski1985_II", "flag_parallel_to_control"])

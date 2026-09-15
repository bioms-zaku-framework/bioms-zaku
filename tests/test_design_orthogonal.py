"""EN: orthogonal design (v0.9) — the designed vector is Σ-orthogonal to the control by construction, several indices share one
partition, and the audit of the cleaned index shows the control gain removed on a constructed case with known truth."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from bioms_zaku.design import DesignError, design_index, holdout_split, orthogonal_fit
from bioms_zaku.i18n import set_language

ROOT = Path(__file__).resolve().parents[1]


def _frame(n=600, seed=7):
    """EN: R, Xc, H, W lognormal; lean = R^-0.5 H^1.5 · noise; fat = W^1.2 H^-1 R^0.3 · noise (both positive, coupled through R and H)."""
    rng = np.random.default_rng(seed)
    R = np.exp(rng.normal(np.log(500), 0.15, n)); Xc = np.exp(rng.normal(np.log(50), 0.20, n))
    H = np.exp(rng.normal(np.log(170), 0.05, n)); W = np.exp(rng.normal(np.log(75), 0.18, n))
    lean = R ** -0.5 * H ** 1.5 * np.exp(rng.normal(0, 0.05, n)); fat = W ** 1.2 * H ** -1.0 * R ** 0.3 * np.exp(rng.normal(0, 0.08, n))
    sexo = rng.integers(0, 2, n)
    return pd.DataFrame({"seqn": np.arange(n), "sexo": sexo, "R": R, "Xc": Xc, "H": H, "W": W, "lean": lean, "fat": fat})


def test_orthogonal_fit_has_zero_cosine_and_is_the_closest_such_vector():
    df = _frame(); LX = np.log(df[["R", "Xc", "H", "W"]].to_numpy()); ly = np.log(df.lean.to_numpy()); lc = np.log(df.fat.to_numpy())
    a, c, r2, r2u, cos = orthogonal_fit(ly, lc, LX)
    Xc_ = LX - LX.mean(axis=0); S = Xc_.T @ Xc_ / (len(LX) - 1)
    assert abs(cos) < 1e-12 and abs(float(a @ S @ c)) < 1e-9                     # exactly Σ-orthogonal to the control's vector
    assert r2 <= r2u + 1e-12 and r2 > 0.5                                        # constrained fit explains less, still informative
    # optimality: any small move along the control direction or any other Σ-orthogonal perturbation cannot improve the residual
    def sse(v):
        pred = LX @ v; pred = pred - pred.mean() + ly.mean(); return float(((ly - pred) ** 2).sum())
    base = sse(a); rng = np.random.default_rng(1)
    for _ in range(50):
        d = rng.normal(size=4); d = d - (float(c @ S @ d) / float(c @ S @ c)) * c   # keep the constraint
        assert sse(a + 1e-3 * d) >= base - 1e-9


def test_design_index_orthogonal_records_control_vector_and_refits(tmp_path):
    df = _frame(); s = holdout_split(df, stratify=df.sexo)
    d = design_index(df, "lean", ["R", "Xc", "H", "W"], s, index_id="lean_clean", orthogonal_to="fat")
    assert d.orthogonal_to == "fat" and d.control_vector is not None and abs(d.cos_control_design) < 1e-12
    assert d.r2_unconstrained >= d.r2_design and d.vector_refit_full is not None and d.n_design == s.n_design
    plain = design_index(df, "lean", ["R", "Xc", "H", "W"], s, index_id="lean_plain")
    assert np.allclose(plain.vector_design, [-0.5, 0.0, 1.5, 0.0], atol=0.08)     # the generating vector, unconstrained
    with pytest.raises(DesignError):
        design_index(df, "lean", ["R", "Xc", "H", "W"], s, index_id="x", orthogonal_to="lean")


def _cfg(tmp_path, df, name, design):
    p = tmp_path / f"{name}.csv"; df.to_csv(p, index=False)
    return {"run_name": name, "language": "pt", "preset": "quick", "data": {"path": str(p), "columns": {"variables": {"R": "R", "Xc": "Xc", "H": "H", "W": "W"},
            "units": {"H": "cm", "W": "kg"}, "targets": {"lean": "lean"}, "controls": {"fat": "fat"}, "covariates": ["W", "H"], "id": "seqn", "groups": {"sexo": "sexo"}}},
            "strata": "sexo", "strata_labels": {0: "F", 1: "M"}, "catalog": {"include": ["Lukaski1985_II", "Piccoli1994_XcH"]},
            "declarations": {"targets_independent_of_variables": True}, "design": design, "output": {"dir": str(tmp_path), "figures": True},
            "audit": {"bootstrap": {"min_oob": 10, "B": 60}, "cv": {"folds": 3, "repeats": 2}}}


def test_ols_vector_is_conditionally_orthogonal_to_the_control_by_construction():
    # EN: the theorem behind the design: with t̂, ĉ the implicit vectors and β = t̂ᵀΣĉ / t̂ᵀΣt̂, the OLS vector a = t̂ satisfies
    #     aᵀΣ(ĉ − βt̂) = 0 exactly — the best predictor of the target carries no information on the control's projection once the
    #     target's projection is given. Hence the plain design is the 'cleaned' index for the conditional negative control.
    df = _frame(); LX = np.log(df[["R", "Xc", "H", "W"]].to_numpy()); ly = np.log(df.lean.to_numpy()); lc = np.log(df.fat.to_numpy())
    from bioms_zaku.design import _ols
    t_hat, _ = _ols(ly, LX); c_hat, _ = _ols(lc, LX)
    Xc_ = LX - LX.mean(axis=0); S = Xc_.T @ Xc_ / (len(LX) - 1)
    beta = float(t_hat @ S @ c_hat) / float(t_hat @ S @ t_hat)
    assert abs(float(t_hat @ S @ (c_hat - beta * t_hat))) < 1e-10
    a_orth, *_ = orthogonal_fit(ly, lc, LX)                          # the marginal-orthogonal vector does NOT satisfy it
    assert abs(float(a_orth @ S @ (c_hat - beta * t_hat))) > 1e-3


def test_designs_share_one_partition_and_the_plain_design_passes_the_conditional_control_while_the_marginal_one_tracks_it(tmp_path):
    from bioms_zaku.run import run
    df = _frame(n=900, seed=11)
    design = [{"target": "lean", "id": "lean_plain"}, {"target": "lean", "orthogonal_to": "fat", "id": "lean_orth"}, {"target": "fat", "id": "fat_plain"}]
    res = run(_cfg(tmp_path, df, "orth", design), printer=lambda s: None)
    m = res["manifest"]["design"]; assert set(m["indices"]) == {"lean_plain", "lean_orth", "fat_plain"} and m["columns_required"] == ["fat", "lean"]
    for did, spec in m["indices"].items():
        for st, ps in spec["per_stratum"].items():
            assert ps["n_audit"] == m["indices"]["lean_plain"]["per_stratum"][st]["n_audit"]             # one partition for all
            if spec["orthogonal_to"]:
                assert abs(ps["cos_control_design"]) < 1e-10 and ps["r2_unconstrained"] >= ps["r2_design"]
    aud = res["tables"]["audit"]; alg = res["tables"]["algebra"]
    assert alg[alg.method_id.isin(m["indices"])].designed.all() and not alg[alg.method_id == "Lukaski1985_II"].designed.any()
    gaps = []
    for st in ("F", "M"):
        plain = aud[(aud.method_id == "lean_plain") & (aud.stratum == st) & (aud.target == "lean")].iloc[0]
        orth = aud[(aud.method_id == "lean_orth") & (aud.stratum == st) & (aud.target == "lean")].iloc[0]
        assert plain.verdict == "SPECIFIC" and plain.s2_mean < 0.03                    # the plain design passes the conditional control out of sample
        assert orth.s2_mean > plain.s2_mean and orth.s1_mean < plain.s1_mean            # the marginal-orthogonal design gives up target signal and gains control signal
        gaps.append(orth.s2_mean - plain.s2_mean)
    assert max(gaps) > 0.1                                                              # and in at least one stratum it clearly tracks the control
    red = res["tables"]["redundancy"]
    assert not red[~red.method_id.isin(m["indices"])].predecessor_id.isin(m["indices"]).any()  # designed never precede published
    txt = (res["out_dir"] / "report.html").read_text(encoding="utf-8"); summ = (res["out_dir"] / "summary.md").read_text(encoding="utf-8")
    assert "3 desenhados △" in txt and "Índices desenhados" in txt and "Σ-ortogonal a fat" in txt and "lean_orth" in txt
    assert "desenhados na partição de desenho" in summ and "lean_orth ← lean Σ-ortogonal a fat (cos_Σ = 0)" in summ
    assert f"<div class='v'>{m['n_audit']}</div><div class='l'>pessoas analisadas</div>" in txt and f"linhas auditadas · {m['n_design']} usadas só no desenho" in txt
    assert f"partição de desenho: {m['n_design']} linhas usadas só para ajustar" in summ
    set_language("en")


def test_init_never_designs_and_start_yes_writes_both_directions(tmp_path):
    from bioms_zaku.wizard import init
    from bioms_zaku.start import start
    flags = {"R": "resistencia_ohm", "Xc": "reatancia_ohm", "H": "estatura_cm", "W": "massa_kg", "target": "lmi_dxa", "control": "fmi_dxa", "independent": "yes", "design": "both"}
    cfg = yaml.safe_load(init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "d.yaml"), map_flags=flags, lang="pt", printer=lambda s: None).read_text(encoding="utf-8"))
    assert "design" not in cfg and "pairing" not in cfg["data"]["columns"] and list(cfg["data"]["columns"]["targets"]) == ["lmi_dxa"]   # init: columns only (v1.0)
    calls = []; printed = []
    p = start(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "s.yaml"), ask=None, map_flags={k: v for k, v in flags.items() if k != "design"} | {"lang": "pt", "strata": "sexo", "labels": "0=F,1=M"},
              yes=True, printer=printed.append, runner=lambda q: calls.append(q))
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "design" not in cfg and len(calls) == 1 and any("não é possível sugerir" in l for l in printed)   # 150 rows: blocked before any suggestion, even with --yes
    big = tmp_path / "big.csv"; _frame(n=900, seed=5).to_csv(big, index=False); calls = []
    p = start(str(big), str(tmp_path / "s2.yaml"), ask=None, map_flags={"R": "R", "Xc": "Xc", "H": "H", "W": "W", "target": "lean", "control": "fat", "independent": "yes", "lang": "pt", "strata": "sexo", "labels": "0=F,1=M"},
              yes=True, printer=lambda s: None, runner=lambda q: calls.append(q))
    cfg2 = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert [d["id"] for d in cfg2["design"]] == ["Zaku_LM", "Zaku_FM"] and cfg2["data"]["columns"]["pairing"] == {"lean": "fat", "fat": "lean"} and len(calls) == 2
    set_language("en")

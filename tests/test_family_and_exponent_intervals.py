"""EN: v1.1 — (C) the verdict rule is per method; the family-level interval 1 − 0.05/k is read on the same resamples and
reported next to it, never selected; (E) designed exponents carry person-bootstrap intervals."""
import numpy as np
import pandas as pd
import pytest

from bioms_zaku.audit import AuditConfig, verdict_sensitivity
from bioms_zaku.design import design_index, exponent_intervals, holdout_split
from bioms_zaku.i18n import set_language
from test_design_orthogonal import _frame


def _cfg(tmp_path, n=700, include=("Lukaski1985_II", "Piccoli1994_XcH", "Piccoli1994_RH", "Baumgartner1988_PhA", "LMI"), **extra):
    p = tmp_path / "f.csv"; _frame(n=n, seed=31).to_csv(p, index=False)
    return {"run_name": "f", "language": "pt", "preset": "quick", "data": {"path": str(p), "columns": {"variables": {"R": "R", "Xc": "Xc", "H": "H", "W": "W"},
            "units": {"H": "cm", "W": "kg"}, "targets": {"lean": "lean"}, "controls": {"fat": "fat"}, "covariates": ["W", "H"], "id": "seqn"}},
            "catalog": {"include": list(include)}, "output": {"dir": str(tmp_path), "figures": False},
            "audit": {"bootstrap": {"min_oob": 20, "B": 80}, "cv": {"folds": 3, "repeats": 1}}, **extra}


def test_family_level_interval_is_wider_reported_and_identical_when_k_is_one(tmp_path):
    from bioms_zaku.run import run
    res = run(_cfg(tmp_path), printer=lambda s: None); a = res["tables"]["audit"]
    assert (a.k_methods == 5).all() and np.allclose(a.ci_family, 1 - 0.05 / 5) and (a.ci_level == 0.95).all()
    assert (a.s1_lo_fam <= a.s1_lo + 1e-12).all() and (a.s1_hi_fam >= a.s1_hi - 1e-12).all() and set(a.verdict_family) <= {"SPECIFIC", "TRACKS_CONTROL", "BOTH", "NEITHER"}
    ts = res["tables"]["threshold_sensitivity"]; fam = ts[np.isclose(ts.ci_level, 1 - 0.05 / 5)]
    assert len(fam) == len(a) and (fam.margin == 0.03).all() and (fam.p_specific == 0.95).all()             # one family row per audit row, declared margin and P
    assert set(ts.ci_level.round(4)) == {0.95, round(1 - 0.05 / 5, 4)}
    txt = (res["out_dir"] / "report.html").read_text(encoding="utf-8")
    assert "Número de métodos: 5 auditados juntos" in txt and "1 − 0,05/k = 0.9900" in txt and "Reportado, nunca escolhido" in txt
    res1 = run(_cfg(tmp_path, include=("Lukaski1985_II",)), printer=lambda s: None); a1 = res1["tables"]["audit"]
    assert (a1.k_methods == 1).all() and np.allclose(a1.ci_family, 0.95) and np.allclose(a1.s1_lo_fam, a1.s1_lo) and (a1.verdict_family == a1.verdict).all()   # k = 1: identical
    set_language("en")


def test_verdict_sensitivity_carries_the_family_row_only_when_present():
    rows = [dict(method_id="A", stratum="F", target="t", control="c", s1_mean=0.2, s1_lo=0.1, s1_hi=0.3, p_s1=1.0, s2_mean=0.0, s2_lo=-0.1, s2_hi=0.1, p_s2=0.5, verdict="SPECIFIC",
                 ci_level=0.95, ci_family=0.99, verdict_family="NEITHER")]
    out = pd.DataFrame(verdict_sensitivity(rows))
    assert len(out) == 10 and out.ci_level.round(3).tolist().count(0.99) == 1
    fam = out[out.ci_level == 0.99].iloc[0]; assert fam.verdict == "NEITHER" and fam.changed and fam.margin == 0.03 and fam.p_specific == 0.95
    rows[0].pop("verdict_family"); rows[0].pop("ci_family"); assert len(verdict_sensitivity(rows)) == 9


def test_exponent_intervals_cover_the_vector_are_deterministic_and_narrow_with_n():
    df = _frame(n=900, seed=5); s = holdout_split(df, stratify=df.sexo)
    d = design_index(df, "lean", ["R", "Xc", "H", "W"], s, index_id="x", B=200, seed=42)
    assert d.vector_lo is not None and (d.vector_lo <= d.vector_design + 1e-9).all() and (d.vector_hi >= d.vector_design - 1e-9).all() and d.B_vector == 200
    assert (d.vector_lo <= np.array([-0.5, 0.0, 1.5, 0.0]) + 0.02).all() and (d.vector_hi >= np.array([-0.5, 0.0, 1.5, 0.0]) - 0.02).all()   # the generating vector inside
    lo2, hi2 = exponent_intervals(df, "lean", ["R", "Xc", "H", "W"], s.design, B=200, seed=42)
    assert np.allclose(lo2, d.vector_lo) and np.allclose(hi2, d.vector_hi)                                   # deterministic
    small = _frame(n=200, seed=5); s2 = holdout_split(small, stratify=small.sexo)
    lo3, hi3 = exponent_intervals(small, "lean", ["R", "Xc", "H", "W"], s2.design, B=200, seed=42)
    assert np.median(hi3 - lo3) > 1.5 * np.median(d.vector_hi - d.vector_lo)
    o = design_index(df, "lean", ["R", "Xc", "H", "W"], s, index_id="o", orthogonal_to="fat", B=100, seed=1)
    assert o.vector_lo is not None and (o.vector_lo <= o.vector_design + 1e-9).all()


def test_intervals_reach_manifest_summary_and_suggestions(tmp_path):
    from bioms_zaku.run import run
    from bioms_zaku.start import suggestions
    cfg = _cfg(tmp_path, include=("Lukaski1985_II",), design=[{"target": "lean", "id": "Zaku_LM"}], declarations={"targets_independent_of_variables": True})
    res = run(cfg, printer=lambda s: None); ps = res["manifest"]["design"]["indices"]["Zaku_LM"]["per_stratum"]["all"]
    assert len(ps["vector_lo"]) == 4 and ps["B_vector"] == 200 and all(l <= v <= h for l, v, h in zip(ps["vector_lo"], ps["vector_design"], ps["vector_hi"]))
    summ = (res["out_dir"] / "summary.md").read_text(encoding="utf-8"); assert "Zaku_LM ← lean: vetor R " in summ and "; " in summ.split("Zaku_LM ← lean")[1][:60]
    printed = []; sg = suggestions({k: v for k, v in cfg.items() if k != "design"}, printed.append)
    assert sg and sg[0]["vector_lo"] is not None
    from bioms_zaku.start import _print_suggestion
    set_language("pt"); _print_suggestion(1, sg[0], printed.append); assert any(l.strip().startswith("estabilidade") for l in printed)
    set_language("en")

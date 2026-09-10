"""EN: audit unit tests on synthetic data. ES/PT: testes unitários da auditoria em dados sintéticos."""
import numpy as np
import pytest
from bioms_zaku.audit import (AuditConfig, audit_method, combination_gain, contrast, cv_score, default_estimator,
                              infer_task, oob_scores, resamples, utility_method, verdict)

QUICK = AuditConfig(cv_repeats=3, B=60, min_oob=5)


def _synthetic(n=300, seed=0):
    rng = np.random.default_rng(seed)
    size = rng.normal(0, 1, n)                     # shared body-size factor
    muscle = size + rng.normal(0, 0.7, n)
    fat = size + rng.normal(0, 0.7, n)
    idx_specific = muscle + rng.normal(0, 0.3, n)   # tracks muscle
    idx_size = size + rng.normal(0, 0.3, n)         # tracks the confounder
    return muscle, fat, idx_specific, idx_size, size


def test_resamples_are_deterministic_and_respect_min_oob():
    tr1, oob1 = resamples(100, 42, 20, 10); tr2, oob2 = resamples(100, 42, 20, 10)
    assert all(np.array_equal(a, b) for a, b in zip(tr1, tr2)) and all(len(o) >= 10 for o in oob1)
    assert not np.array_equal(tr1[0], resamples(100, 43, 20, 10)[0][0])
    for ii, oo in zip(tr1, oob1):
        assert not set(ii) & set(oo)                # OOB rows are never in training


def test_reference_scheme_reproduced_exactly():
    # EN: the previous engine: rng=default_rng(42); ii=rng.integers(0,n,n); oob=setdiff1d(arange(n), unique(ii)); keep if >=20
    n, B = 50, 10
    rng = np.random.default_rng(42); ref = []
    while len(ref) < B:
        ii = rng.integers(0, n, n); oo = np.setdiff1d(np.arange(n), np.unique(ii))
        if len(oo) >= 5: ref.append((ii, oo))
    tr, oob = resamples(n, 42, B, 5)
    assert all(np.array_equal(a, b) and np.array_equal(c, d) for (a, c), b, d in zip(ref, tr, oob))


def test_specific_vs_size_index_verdicts():
    muscle, fat, idx_specific, idx_size, _ = _synthetic()
    rows = audit_method("spec", "all", idx_specific, {"muscle": muscle}, {"fat": fat}, {"muscle": "fat"}, QUICK)
    assert rows[0].verdict == "SPECIFIC" and rows[0].disc_mean > 0 and rows[0].metric == "R2"
    rows = audit_method("size", "all", idx_size, {"muscle": muscle}, {"fat": fat}, {"muscle": "fat"}, QUICK)
    assert rows[0].verdict == "INCONCLUSIVE" and abs(rows[0].disc_mean) < 0.15   # predicts both equally: not specific


def test_pairing_uses_identical_resamples_for_target_and_control():
    muscle, fat, idx_specific, _, _ = _synthetic()
    x = idx_specific.reshape(-1, 1); Y = np.column_stack([muscle, fat])
    st, b_eff, _ = oob_scores({"idx": x}, Y, "regression", default_estimator("regression"), QUICK)
    # EN: scoring the control alone with the same config must give exactly the same column (same resamples)
    st2, _, _ = oob_scores({"idx": x}, fat.reshape(-1, 1), "regression", default_estimator("regression"), QUICK)
    assert np.allclose(st["idx"][:, 1], st2["idx"][:, 0], atol=0, rtol=0)


def test_complete_case_rows_only():
    muscle, fat, idx_specific, _, _ = _synthetic()
    x = idx_specific.copy(); x[:10] = np.nan; m = muscle.copy(); m[10:15] = np.nan
    rows = audit_method("spec", "all", x, {"muscle": m}, {"fat": fat}, {"muscle": "fat"}, QUICK)
    assert rows[0].n == 300 - 15


def test_utility_over_covariates():
    muscle, fat, idx_specific, idx_size, size = _synthetic()
    cov = size.reshape(-1, 1)
    u = utility_method("spec", "all", idx_specific, cov, ["size"], {"muscle": muscle}, QUICK)[0]
    assert u.useful and u.delta_mean > 0.1
    u2 = utility_method("size", "all", idx_size, cov, ["size"], {"muscle": muscle}, QUICK)[0]
    assert not u2.useful                             # a size proxy adds nothing over size itself


def test_combination_gain_is_positive_only_for_new_information():
    muscle, fat, idx_specific, idx_size, _ = _synthetic()
    g = combination_gain("size", "spec", "all", idx_size, idx_specific, {"muscle": muscle}, QUICK, default_estimator("regression"))[0]
    assert g["gain_lo"] > 0
    g2 = combination_gain("spec", "spec2", "all", idx_specific, idx_specific * 2.0 + 1.0, {"muscle": muscle}, QUICK, default_estimator("regression"))[0]
    assert abs(g2["gain_mean"]) < 0.02             # a rescaled copy adds nothing


def test_classification_binary_and_multiclass():
    rng = np.random.default_rng(1); n = 400
    z = rng.normal(0, 1, n); x = z + rng.normal(0, 0.5, n)
    yb = (z > 0).astype(int); ctrl = rng.integers(0, 2, n)
    rows = audit_method("x", "all", x, {"yb": yb}, {"ctrl": ctrl}, {"yb": "ctrl"}, QUICK)
    assert rows[0].task == "classification" and rows[0].metric == "AUROC" and rows[0].verdict == "SPECIFIC"
    y3 = np.digitize(z, [-0.5, 0.5]); ctrl3 = rng.integers(0, 3, n)
    rows3 = audit_method("x", "all", x, {"y3": y3}, {"ctrl3": ctrl3}, {"y3": "ctrl3"}, QUICK)
    assert rows3[0].score_cv_target > 0.8 and rows3[0].verdict == "SPECIFIC"


def test_verdict_rules():
    cfg = AuditConfig()
    assert verdict(dict(mean=0.1, lo=0.02, hi=0.2, p=0.99), cfg) == "SPECIFIC"
    assert verdict(dict(mean=-0.1, lo=-0.2, hi=-0.02, p=0.01), cfg) == "MEASURES_CONTROL"
    assert verdict(dict(mean=0.1, lo=-0.01, hi=0.2, p=0.9), cfg) == "INCONCLUSIVE"


def test_infer_task():
    assert infer_task(np.array([0, 1, 1, 0])) == "classification"
    assert infer_task(np.array([0.1, 2.3, 1.2])) == "regression"

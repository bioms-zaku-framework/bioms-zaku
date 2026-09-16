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
    # EN: the documented resampling scheme (§3): rng=default_rng(seed); ii=rng.integers(0,n,n); oob=setdiff1d(arange(n), unique(ii)); keep if >= min_oob
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
    r = rows[0]
    assert r.verdict_marginal == "SPECIFIC" and r.disc_mean > 0 and r.metric == "R2"
    # v0.5 conditional control: adds to muscle beyond fat (S1 large), adds nothing to fat beyond muscle (S2 ≈ 0)
    assert r.verdict == "SPECIFIC" and r.s1_mean > 0.3 and abs(r.s2_mean) < 0.05, (r.s1_mean, r.s2_mean)
    assert r.score_oob_idx_control_to_target > r.score_oob_control_to_target
    rows = audit_method("size", "all", idx_size, {"muscle": muscle}, {"fat": fat}, {"muscle": "fat"}, QUICK)
    r = rows[0]
    assert r.verdict_marginal == "INCONCLUSIVE" and abs(r.disc_mean) < 0.15   # predicts both equally under the marginal rule
    # the size index carries the shared factor: it adds to BOTH beyond the other → BOTH (not specific)
    assert r.verdict == "BOTH" and r.s1_mean > 0.05 and r.s2_mean > 0.05, (r.verdict, r.s1_mean, r.s2_mean)


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
    assert rows[0].task == "classification" and rows[0].metric == "D_Tjur" and rows[0].verdict == "SPECIFIC" and 0.5 < rows[0].auroc_cv_target_full <= 1.0
    y3 = np.digitize(z, [-0.5, 0.5]); ctrl3 = rng.integers(0, 3, n)
    rows3 = audit_method("x", "all", x, {"y3": y3}, {"ctrl3": ctrl3}, {"y3": "ctrl3"}, QUICK)
    assert rows3[0].score_cv_target > 0.3 and rows3[0].verdict == "SPECIFIC"      # D (macro one-vs-rest), not AUROC


def test_conditional_verdict_rules():
    from bioms_zaku.audit import verdict_conditional
    cfg = AuditConfig(specificity_margin=0.03)
    pos = dict(mean=0.10, lo=0.05, hi=0.15, p=1.0, n=10); nil = dict(mean=0.005, lo=-0.01, hi=0.02, p=0.7, n=10)
    tiny = dict(mean=0.02, lo=0.01, hi=0.03, p=0.99, n=10)   # "significant" but below the margin → absent
    assert verdict_conditional(pos, nil, cfg) == "SPECIFIC"
    assert verdict_conditional(nil, pos, cfg) == "TRACKS_CONTROL"
    assert verdict_conditional(pos, pos, cfg) == "BOTH"
    assert verdict_conditional(nil, nil, cfg) == "NEITHER"
    assert verdict_conditional(tiny, nil, cfg) == "NEITHER"


def test_verdict_rules():
    cfg = AuditConfig()
    assert verdict(dict(mean=0.1, lo=0.02, hi=0.2, p=0.99), cfg) == "SPECIFIC"
    assert verdict(dict(mean=-0.1, lo=-0.2, hi=-0.02, p=0.01), cfg) == "MEASURES_CONTROL"
    assert verdict(dict(mean=0.1, lo=-0.01, hi=0.2, p=0.9), cfg) == "INCONCLUSIVE"


def test_infer_task():
    assert infer_task(np.array([0, 1, 1, 0])) == "classification"
    assert infer_task(np.array([0.1, 2.3, 1.2])) == "regression"


def test_bootstrap_impossible_is_a_clear_error():
    import pytest as _pt
    from bioms_zaku.audit import AuditError
    muscle, fat, idx_specific, _, _ = _synthetic(n=30)
    with _pt.raises(AuditError, match="bootstrap impossible"):
        audit_method("spec", "all", idx_specific, {"muscle": muscle}, {"fat": fat}, {"muscle": "fat"}, AuditConfig(cv_repeats=2, B=20, min_oob=25))


def test_lesson11_conditional_control_by_hand():
    # EN: caderno/licoes_metodo_bioms_a_mao.md, Lição 11 — six centred persons; S1/S2 as differences of in-sample R²
    #     between nested least-squares fits. Numbers as computed by hand (3 decimals).
    x = np.array([-2., -1., 0., 0., 1., 2.]); y = np.array([-3., -1., -1., 1., 1., 3.]); c = np.array([-1., -2., 1., -1., 2., 1.])
    def r2(Y, *cols):
        X = np.column_stack(cols); beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
        return 1 - ((Y - X @ beta) ** 2).sum() / (Y ** 2).sum()
    assert abs(r2(y, c) - 0.242) < 1e-3 and abs(r2(y, c, x) - 0.974) < 1e-3
    assert abs(r2(c, y) - 0.242) < 1e-3 and abs(r2(c, y, x) - 0.889) < 1e-3
    s1, s2 = r2(y, c, x) - r2(y, c), r2(c, y, x) - r2(c, y)
    assert abs(s1 - 0.732) < 1e-3 and abs(s2 - 0.647) < 1e-3
    # EN: the old marginal rule would call it specific: r²(y|x) = 0.89 vs r²(c|x) = 0.53
    assert abs(r2(y, x) - 0.891) < 1e-3 and abs(r2(c, x) - 0.533) < 1e-3
    from bioms_zaku.audit import verdict_conditional
    cfg = AuditConfig()
    # EN: in-sample point values only (no interval here): both gains exceed the margin -> BOTH
    mk = lambda v: dict(mean=v, lo=v, hi=v, p=1.0, n=1)
    assert verdict_conditional(mk(s1), mk(s2), cfg) == "BOTH"
    assert verdict_conditional(mk(s1), mk(0.0), cfg) == "SPECIFIC"

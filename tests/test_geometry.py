"""
EN: contract §3.3 (v0.6) on CONSTRUCTED data: implicit vectors recover a monomial target exactly; the identity
    r_log = cos_Σ·√R² is exact for monomial indices; a control built parallel to the target raises both flags, an
    orthogonal one raises none; a poor projection blocks the flags. ES/PT: geometria alvo↔controle em dados construídos.
"""
import numpy as np
import pandas as pd

from bioms_zaku.algebra import VectorFit, geometry_tables

V = ["R", "Xc", "H", "W"]


def _frame(n=600, seed=3):
    rng = np.random.default_rng(seed)
    L = rng.normal(size=(n, 4)) @ np.array([[1.0, 0.3, 0.0, 0.2], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.5], [0.0, 0.0, 0.0, 1.0]])
    return pd.DataFrame(np.exp(L * 0.1), columns=V), L * 0.1


def _vf(mid, vec, src="catalog"):
    return VectorFit(mid, "all", tuple(V), np.array(vec, float), src, 600, 0, 1.0)


def _run(frame, target, control, vecs, vals, **thr):
    return geometry_tables(vecs, vals, frame, V, {"T": target}, {"C": control}, {"T": "C"}, "all", **thr)


def test_monomial_target_recovered_exactly_and_identity_exact():
    frame, L = _frame(); a = np.array([-1.0, 0.0, 2.0, 0.0])          # H²/R
    target = np.exp(L @ np.array([-0.5, 0.0, 1.0, 0.0]) + 0.3)           # exact monomial, half of a: parallel
    rng = np.random.default_rng(1); control = np.exp(L @ np.array([0.0, 1.0, 0.0, 0.0]) + rng.normal(0, 0.05, len(L)))
    imp, geo = _run(frame, target, control, {"II": _vf("II", a)}, {"II": np.exp(L @ a)})
    t = imp[imp.role == "target"].iloc[0]
    assert np.abs([t.e_R + 0.5, t.e_Xc, t.e_H - 1.0, t.e_W]).max() < 1e-9 and abs(t.fit_r2 - 1.0) < 1e-9
    g = geo.iloc[0]
    assert abs(g.cos_target - 1.0) < 1e-9                                  # a ∥ t^
    assert abs(g.r_log_target_gap) < 1e-9 and abs(g.r_log_control_gap) < 1e-9   # identity exact for a monomial index


def test_parallel_control_raises_flags_and_orthogonal_does_not():
    frame, L = _frame(); a = np.array([-1.0, 0.0, 2.0, 0.0]); rng = np.random.default_rng(2)
    e = rng.normal(0, 0.03, len(L)); X1 = np.column_stack([np.ones(len(L)), L])
    e = e - X1 @ np.linalg.lstsq(X1, e, rcond=None)[0]                     # EN: residual made EXACTLY orthogonal to the log space (as in lesson 12)
    target = np.exp(L @ np.array([-0.5, 0.0, 1.0, 0.0]) + e)
    parallel = np.exp(L @ np.array([-0.25, 0.0, 0.5, 0.0]) - 0.5 * e)   # same direction in the measured space
    imp, geo = _run(frame, target, parallel, {"II": _vf("II", a)}, {"II": np.exp(L @ a)})
    g = geo.iloc[0]
    assert g.fit_r2_target >= 0.5 and g.fit_r2_control >= 0.5 and abs(g.cos_target_control - 1.0) < 1e-9
    assert abs(np.corrcoef(np.log(target), np.log(parallel))[0, 1]) < 0.999   # raw correlation is NOT 1: the coupling is in the measured space
    assert bool(g.flag_coupled_target_control) and bool(g.flag_parallel_to_control) and not g.poor_projection
    # orthogonal under Σ: build the control from the Σ-orthogonal complement of t within the log space
    S = np.cov(L.T, ddof=1); t = np.array([-0.5, 0.0, 1.0, 0.0]); w = np.array([0.0, 1.0, 0.0, 0.0])
    w = w - (t @ S @ w) / (t @ S @ t) * t                                  # Σ-orthogonalised
    orth = np.exp(L @ w + rng.normal(0, 0.01, len(L)))
    imp2, geo2 = _run(frame, target, orth, {"II": _vf("II", a)}, {"II": np.exp(L @ a)})
    g2 = geo2.iloc[0]
    assert abs(g2.cos_target_control) < 0.05 and abs(g2.cos_control) < 0.05
    assert not g2.flag_coupled_target_control and not g2.flag_parallel_to_control


def test_poor_projection_blocks_flags_but_reports_cosines():
    frame, L = _frame(); a = np.array([-1.0, 0.0, 2.0, 0.0]); rng = np.random.default_rng(4)
    target = np.exp(L @ np.array([-0.5, 0.0, 1.0, 0.0]) + rng.normal(0, 0.02, len(L)))
    noise = np.exp(rng.normal(0, 1.0, len(L)))                              # control unrelated to the variables
    imp, geo = _run(frame, target, noise, {"II": _vf("II", a)}, {"II": np.exp(L @ a)})
    g = geo.iloc[0]
    assert g.fit_r2_control < 0.5 and g.poor_projection and np.isfinite(g.cos_control)
    assert not g.flag_parallel_to_control and not g.flag_coupled_target_control


def test_thresholds_are_declared_and_flags_follow_them():
    frame, L = _frame(); a = np.array([-1.0, 0.0, 2.0, 0.0]); rng = np.random.default_rng(5)
    target = np.exp(L @ np.array([-0.5, 0.0, 1.0, 0.0]) + rng.normal(0, 0.03, len(L)))
    control = np.exp(L @ np.array([-0.3, 0.2, 0.6, 0.0]) + rng.normal(0, 0.03, len(L)))
    _, g1 = _run(frame, target, control, {"II": _vf("II", a)}, {"II": np.exp(L @ a)}, coupled_target_control=0.999, parallel_to_control=0.999)
    _, g2 = _run(frame, target, control, {"II": _vf("II", a)}, {"II": np.exp(L @ a)}, coupled_target_control=0.10, parallel_to_control=0.10)
    assert "coupled_target_control>=0.999" in g1.thresholds.iloc[0]
    assert not g1.flag_coupled_target_control.iloc[0] and g2.flag_coupled_target_control.iloc[0]

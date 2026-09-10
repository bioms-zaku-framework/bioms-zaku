import numpy as np
import pandas as pd
import pytest
from bioms_zaku.design import DesignError, by_stratum_split, design_index, holdout_split


def _frame(n=600, seed=3):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"R": rng.uniform(300, 800, n), "Xc": rng.uniform(30, 90, n), "H": rng.uniform(150, 190, n), "W": rng.uniform(45, 120, n),
                       "sexo": rng.integers(0, 2, n)})
    df["vo2"] = 40 * (df.H ** 2 / df.R) ** 0.3 * df.W ** -0.4 * np.exp(rng.normal(0, 0.02, n))
    return df


def test_holdout_is_deterministic_stratified_and_disjoint():
    df = _frame()
    s1 = holdout_split(df, fraction=0.70, seed=42, stratify=df.sexo); s2 = holdout_split(df, fraction=0.70, seed=42, stratify=df.sexo)
    assert np.array_equal(s1.design, s2.design) and not (s1.design & s1.audit).any() and (s1.design | s1.audit).all()
    assert s1.n_design == 420 and s1.n_audit == 180 and s1.design_hash == s2.design_hash
    p_all = df.sexo.mean(); p_d = df.sexo[s1.design].mean()
    assert abs(p_all - p_d) < 0.02


def test_only_declared_fractions():
    with pytest.raises(DesignError):
        holdout_split(_frame(), fraction=0.5)


def test_design_recovers_generating_vector_and_refits():
    df = _frame(); s = holdout_split(df, stratify=df.sexo)
    d = design_index(df, "vo2", ["R", "Xc", "H", "W"], s, index_id="fit_idx")
    assert np.allclose(d.vector_design, [-0.3, 0.0, 0.6, -0.4], atol=0.03) and d.r2_design > 0.9
    assert d.vector_refit_full is not None and d.n_design == 420
    v = d.values(df); assert v.shape == (600,) and np.all(v > 0)


def test_by_stratum_split():
    df = _frame(); s = by_stratum_split(df, "sexo", 1, 0)
    assert s.mode == "by_stratum" and s.n_design + s.n_audit == 600

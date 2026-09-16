"""EN: v1.2 — classification gains in Tjur's coefficient of discrimination D (Tjur 2009; the IDI base of Pencina 2008),
AUROC descriptive (Hanley & McNeil 1982), mixed target/control types, and the per-stratum class check."""
import numpy as np
import pytest

from bioms_zaku.audit import AuditConfig, _auroc, _score, audit_method, default_estimator, make_pipeline, metric_name, utility_method

QUICK = AuditConfig(cv_folds=3, cv_repeats=2, B=60, min_oob=10, seed_bootstrap=1, seed_cv=1, min_B_eff=20)


def _fit(x, y):
    return make_pipeline(default_estimator("classification")).fit(x.reshape(-1, 1), y)


def test_d_is_the_mean_probability_gap_between_cases_and_non_cases_and_lies_in_the_unit_interval():
    rng = np.random.default_rng(0); n = 500
    z = rng.normal(0, 1, n); x = z + rng.normal(0, 0.7, n); y = (z > 0).astype(int)
    m = _fit(x, y); X = x.reshape(-1, 1)
    p = m.predict_proba(X)[:, 1]
    d = _score("classification", y, m, X)
    assert abs(d - (p[y == 1].mean() - p[y == 0].mean())) < 1e-12 and 0.0 < d < 1.0
    assert metric_name("classification") == "D_Tjur" and metric_name("regression") == "R2"
    assert 0.5 < _auroc(y, m, X) < 1.0
    # a model that cannot discriminate (constant predictor) gives D ≈ 0
    m0 = _fit(np.zeros(n) + rng.normal(0, 1e-6, n), y)
    assert abs(_score("classification", y, m0, np.zeros((n, 1)))) < 1e-3


def test_known_signal_passes_the_margin_and_a_permuted_null_does_not():
    rng = np.random.default_rng(2); n = 400
    z = rng.normal(0, 1, n); x = z + rng.normal(0, 0.5, n)
    y = (z > 0).astype(int); ctrl = rng.integers(0, 2, n)
    r = audit_method("x", "all", x, {"y": y}, {"ctrl": ctrl}, {"y": "ctrl"}, QUICK)[0]
    assert r.metric == "D_Tjur" and r.verdict == "SPECIFIC" and r.s1_lo > QUICK.specificity_margin
    xnull = rng.permutation(x)
    r0 = audit_method("xnull", "all", xnull, {"y": y}, {"ctrl": ctrl}, {"y": "ctrl"}, QUICK)[0]
    assert r0.verdict == "NEITHER" and abs(r0.s1_mean) < 0.03


def test_class_target_with_continuous_control_is_audited_with_d_and_r2_on_each_side():
    rng = np.random.default_rng(3); n = 400
    z = rng.normal(0, 1, n); x = z + rng.normal(0, 0.5, n)
    y = (z > 0).astype(int); fat = 0.3 * z + rng.normal(0, 1, n)        # continuous control sharing part of the signal
    r = audit_method("x", "all", x, {"y": y}, {"fat": fat}, {"y": "fat"}, QUICK)[0]
    assert r.task == "classification" and r.metric == "D_Tjur" and r.control_task == "regression" and r.metric_control == "R2"
    assert r.estimator == "LogisticRegression" and np.isfinite(r.s1_mean) and np.isfinite(r.s2_mean)
    assert np.isfinite(r.auroc_cv_target_full) and np.isnan(r.auroc_cv_control_full)
    assert r.verdict in ("SPECIFIC", "BOTH")                               # the index carries y beyond fat
    u = utility_method("x", "all", x, np.column_stack([fat]), ["fat"], {"y": y}, QUICK)[0]
    assert u.metric == "D_Tjur" and np.isfinite(u.auroc_cv_with) and u.delta_lo > 0


def test_check_refuses_a_class_label_that_is_constant_or_too_small_inside_a_stratum(tmp_path):
    import pandas as pd, yaml
    from bioms_zaku.check import check
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1]
    rng = np.random.default_rng(4); n = 200
    sexo = np.repeat([0, 1], n // 2)
    df = pd.DataFrame(dict(id=np.arange(n), sexo=sexo, H=rng.normal(170, 8, n), W=rng.normal(75, 12, n), R=rng.normal(500, 60, n), Xc=rng.normal(55, 8, n),
                           lean=rng.normal(50, 8, n), label=rng.integers(0, 2, n)))
    p = tmp_path / "d.csv"; df.to_csv(p, index=False)
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(p); cfg["data"]["sep"] = ","; cfg["data"]["decimal"] = "."; cfg["output"]["dir"] = str(tmp_path); cfg["run_name"] = "chk"
    cfg["data"]["columns"] = {"variables": {"R": "R", "Xc": "Xc", "H": "H", "W": "W"}, "units": {"H": "cm", "W": "kg"},
                              "targets": {"label": "label"}, "controls": {"sexo": "sexo"}, "id": "id"}
    cfg["strata"] = "sexo"
    cp = tmp_path / "c.yaml"; cp.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    from bioms_zaku.check import CheckError
    with pytest.raises(CheckError) as ei:
        check(str(cp), printer=lambda s: None)
    assert "sexo" in str(ei.value) and "stratum" in str(ei.value)
    cfg["strata"] = None; cp.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    rep2 = check(str(cp), printer=lambda s: None)        # no strata: the same label is a valid control
    assert not rep2["errors"], rep2["errors"]


def test_a_class_label_is_never_designed_and_suggestions_say_so(tmp_path):
    import pandas as pd, yaml
    from pathlib import Path
    from bioms_zaku.start import _too_small_for_design
    from bioms_zaku.check import CheckError, check
    ROOT = Path(__file__).resolve().parents[1]
    rng = np.random.default_rng(5); n = 400
    df = pd.DataFrame(dict(id=np.arange(n), H=rng.normal(170, 8, n), W=rng.normal(75, 12, n), R=rng.normal(500, 60, n), Xc=rng.normal(55, 8, n),
                           fat=rng.normal(20, 6, n).clip(5), label=rng.integers(0, 2, n)))
    p = tmp_path / "d.csv"; df.to_csv(p, index=False)
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(p); cfg["data"]["sep"] = ","; cfg["data"]["decimal"] = "."; cfg["output"]["dir"] = str(tmp_path); cfg["run_name"] = "dc"
    cfg["data"]["columns"] = {"variables": {"R": "R", "Xc": "Xc", "H": "H", "W": "W"}, "units": {"H": "cm", "W": "kg"},
                              "targets": {"label": "label"}, "controls": {"label2": "label"}, "id": "id"}
    cfg["strata"] = None; cfg["declarations"] = {"targets_independent_of_variables": True}
    msgs = _too_small_for_design(cfg)
    assert len(msgs) == 1 and "label" in msgs[0]                              # both are labels: refused with the reason
    cfg["design"] = [{"target": "label", "id": "designed_label"}]
    cp = tmp_path / "c.yaml"; cp.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    with pytest.raises(CheckError, match="design"):
        check(str(cp), printer=lambda s: None)


def test_geometry_skips_pairs_whose_control_is_a_label_and_a_constant_target_never_crashes_the_fit():
    import pandas as pd
    from bioms_zaku import algebra as A
    rng = np.random.default_rng(6); n = 300
    fr = pd.DataFrame(dict(R=rng.normal(500, 60, n), Xc=rng.normal(55, 8, n), H=rng.normal(170, 8, n), W=rng.normal(75, 12, n)))
    fat = (fr.W * 0.3 * np.exp(rng.normal(0, 0.1, n))).to_numpy(); label = rng.integers(0, 2, n).astype(float)
    vec, r2, npos, _ = A.fit_log_linear(np.ones(n), fr[["R", "Xc", "H", "W"]], ["R", "Xc", "H", "W"])
    assert np.isnan(r2) and npos == n
    vecs = {"H2R": np.array([-1.0, 0.0, 2.0, 0.0])}; vals = {"H2R": (fr.H ** 2 / fr.R).to_numpy()}
    imp, geo = A.geometry_tables(vecs, vals, fr, ["R", "Xc", "H", "W"], {"fat": fat}, {}, {"fat": "label"}, "all")
    assert geo.empty                                                        # the pair with a label control is skipped, no crash

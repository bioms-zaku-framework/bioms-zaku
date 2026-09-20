"""
EN: the shipped example is a KNOWN TRUTH. Two guarantees, of very different sharpness, and the docstring says which is
    which so no one mistakes the loose one for a gate:

    (1) SHARP — the method's central identity, ρ_log = aᵀΣb/√(aᵀΣa·bᵀΣb), holds EXACTLY on the shipped rows when Σ is
        the sample covariance of their logs (agreement at 1e-12). This is algebra, and it is checked here on the data a
        researcher actually receives, not on data constructed inside a test.
    (2) LOOSE — the PUBLISHED μ and Σ, from which the base was drawn, are recovered from the rows only up to sampling
        error. The base has 400 people in four cells of 70 and 130, so that error is large: the published Σ misses the
        observed correlation by up to 0.13. The tolerances below were MEASURED on 2026-09-20, not chosen to pass. This
        catches a gross error (wrong parameters, wrong cell, a generator that ignored its input); it cannot catch a
        subtle one, and it is not the gate.

    The hand-calculated gate lives elsewhere and does not depend on any file: tests/test_algebra.py holds the ten
    lessons of the notebook (4 people, computed by hand, 1e-12) and tests/test_geometry.py the exact geometric
    identities on constructed data.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from bioms_zaku.algebra import predicted_pearson_log

ROOT = Path(__file__).resolve().parents[1]
CSV, PARAMS = ROOT / "examples/zaku_exemplo.csv", ROOT / "examples/zaku_exemplo_params.json"

# EN: monomial exponent vectors over (R, Xc, H_cm, W) — the four indices whose algebra is exact by construction.
VARIABLES = ["R", "Xc", "H_cm", "W"]
VECTORS = {"II": np.array([-1, 0, 2, 0.]), "R/H": np.array([1, 0, -1, 0.]),
           "Xc/H": np.array([0, 1, -1, 0.]), "W/H2": np.array([0, 0, -2, 1.])}


def _cells():
    """EN: (cell name, its rows, published μ, published Σ, the published variable order) for the four cells."""
    df, P = pd.read_csv(CSV), json.loads(PARAMS.read_text(encoding="utf-8"))
    for name, c in P["cells"].items():
        rows = df[(df.sexo == c["sexo"]) & (df.diabetes == c["diabetes"])]
        yield name, rows, np.array(c["mu_log"]), np.array(c["sigma_log"]), P["variables"], c["n_source"]


def test_identity_is_exact_on_the_shipped_rows():
    """EN: (1) the sharp one. With the SAMPLE Σ the predicted correlation of logs equals the observed one exactly."""
    for name, rows, _, _, _, _ in _cells():
        L = np.log(rows[VARIABLES].to_numpy(float))
        S = np.cov(L.T, ddof=1)
        names = list(VECTORS)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = VECTORS[names[i]], VECTORS[names[j]]
                observed = np.corrcoef(L @ a, L @ b)[0, 1]
                assert abs(predicted_pearson_log(a, b, S) - observed) < 1e-12, f"{name}: {names[i]} vs {names[j]}"


def test_published_parameters_are_recovered_up_to_sampling_error():
    """EN: (2) the loose one. Measured on 2026-09-20: μ within 0.060, continuous Σ within 0.045, age Σ within 0.037
    (age is rounded to whole years). The tolerances carry a margin over what was measured, and are deliberately not
    tight: with 70 to 130 people per cell, sampling error is the dominant term."""
    for name, rows, mu, S, variables, n_source in _cells():
        L = np.log(rows[variables].to_numpy(float))
        age = variables.index("idade")
        D = np.abs(np.cov(L.T, ddof=1) - S)
        mask = np.zeros_like(D, dtype=bool); mask[age, :] = True; mask[:, age] = True
        assert np.abs(L.mean(axis=0) - mu).max() < 0.08, name
        assert D[~mask].max() < 0.06, name
        assert D[mask].max() < 0.05, name
        assert n_source >= 60                       # EN: every cell was estimated on a real NHANES cell, not invented
        assert (rows[variables] > 0).all().all()    # EN: log-normal draw: strictly positive everywhere


def test_published_sigma_still_points_at_the_observed_correlation():
    """EN: (2) the loose one, continued — a smoke check, NOT a gate. The published Σ misses the observed correlation by
    up to 0.129 on this base (measured 2026-09-20); on the 8000-row base retired on 2026-09-20 the same check held to
    0.02. The difference is n, not a defect. A tolerance of 0.20 still refuses a Σ that is simply wrong."""
    worst = 0.0
    for name, rows, _, S_pub_full, variables, _ in _cells():
        idx = [variables.index(v) for v in VARIABLES]
        L = np.log(rows[VARIABLES].to_numpy(float))
        S_pub = S_pub_full[np.ix_(idx, idx)]
        names = list(VECTORS)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = VECTORS[names[i]], VECTORS[names[j]]
                observed = np.corrcoef(L @ a, L @ b)[0, 1]
                worst = max(worst, abs(predicted_pearson_log(a, b, S_pub) - observed))
    assert worst < 0.20, f"published Σ misses the observed ρ by {worst:.4f}"

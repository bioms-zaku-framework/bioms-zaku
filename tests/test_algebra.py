"""
EN: hand-calculated lessons (caderno/licoes_metodo_bioms_a_mao.md) as unit tests + exactness/invariance properties.
ES: lecciones a mano como pruebas + propiedades de exactitud/invariancia.
PT: lições à mão como testes + propriedades de exatidão/invariância.
"""
import numpy as np
import pandas as pd
import pytest
from bioms_zaku.algebra import (bootstrap_pearson_log_ci, fit_log_linear, log_covariance, pearson_to_spearman, predicted_pearson_log)

# Lição 3: desvios dos logs de 4 pessoas (r, h). Variância/covariância com divisor 4 no caderno; aqui usamos as fórmulas exatas.
R_DEV = np.array([-0.20, 0.10, 0.20, -0.10]); H_DEV = np.array([0.02, 0.01, -0.03, 0.00])


def _sigma_population():
    # EN: population (ddof=0) covariance exactly as in the notebook lesson.
    return np.cov(np.vstack([R_DEV, H_DEV]), ddof=0)


def test_lesson3_sigma():
    S = _sigma_population()
    assert abs(S[0, 0] - 0.025) < 1e-12 and abs(S[1, 1] - 0.00035) < 1e-12 and abs(S[0, 1] - (-0.00225)) < 1e-12
    assert abs(S[0, 1] / np.sqrt(S[0, 0] * S[1, 1]) - (-0.76)) < 0.01


def test_lesson4_variance_two_ways():
    S = _sigma_population(); a = np.array([-1.0, 2.0])
    direct = np.var(-R_DEV + 2 * H_DEV, ddof=0)
    assert abs(float(a @ S @ a) - 0.0354) < 1e-12 and abs(direct - 0.0354) < 1e-12


def test_lesson5_correlation_between_indices():
    S = _sigma_population(); a = np.array([-1.0, 2.0]); b = np.array([1.0, -1.0])
    assert abs(float(b @ S @ b) - 0.02985) < 1e-12
    assert abs(float(a @ S @ b) - (-0.03245)) < 1e-12
    r = predicted_pearson_log(a, b, S)
    lnA = -R_DEV + 2 * H_DEV; lnB = R_DEV - H_DEV
    assert abs(r - np.corrcoef(lnA, lnB)[0, 1]) < 1e-12 and abs(r - (-0.998)) < 5e-4


def test_lesson6_spearman_conversion():
    assert abs(pearson_to_spearman(-0.998) - (-0.998)) < 2e-3
    assert abs(pearson_to_spearman(0.0)) < 1e-12 and abs(pearson_to_spearman(1.0) - 1.0) < 1e-12


def test_lesson7_corollaries_scale_and_power_invariance():
    S = _sigma_population(); a = np.array([-1.0, 2.0]); b = np.array([1.0, -1.0])
    r = predicted_pearson_log(a, b, S)
    assert abs(predicted_pearson_log(3.7 * a, b, S) - r) < 1e-12          # power k>0 leaves correlation unchanged
    assert abs(predicted_pearson_log(-a, b, S) + r) < 1e-12               # negative power flips the sign only


def test_lesson8_9_regression_and_out_of_sample_r2():
    x = np.array([1.0, 2.0, 3.0]); y = np.array([2.0, 4.0, 5.0])
    b1 = np.cov(x, y, ddof=0)[0, 1] / np.var(x, ddof=0); b0 = y.mean() - b1 * x.mean()
    assert abs(b1 - 1.5) < 1e-12 and abs(b0 - 0.6667) < 1e-4
    xt = np.array([4.0, 5.0]); yt = np.array([7.0, 8.0]); pred = b0 + b1 * xt
    r2 = 1 - ((yt - pred) ** 2).sum() / ((yt - yt.mean()) ** 2).sum()
    assert abs(r2 - 0.72) < 0.01


def test_exactness_on_random_data():
    # EN: Pearson of logs predicted from Σ equals the observed Pearson of logs to machine precision, any distribution.
    rng = np.random.default_rng(0); n = 500
    df = pd.DataFrame({"R": rng.lognormal(6, 0.2, n), "Xc": rng.uniform(30, 90, n), "H": rng.normal(170, 8, n), "W": rng.gamma(9, 8, n)})
    S, n_used = log_covariance(df, ["R", "Xc", "H", "W"]); assert n_used == n
    a = np.array([-1.0, 0.0, 2.0, 0.0]); b = np.array([0.0, 0.0, -2.0, 1.0])
    lnA = -np.log(df.R) + 2 * np.log(df.H); lnB = -2 * np.log(df.H) + np.log(df.W)
    assert abs(predicted_pearson_log(a, b, S) - np.corrcoef(lnA, lnB)[0, 1]) < 1e-12


def test_fit_log_linear_recovers_exponents_and_counts_nonpositive():
    rng = np.random.default_rng(1); n = 400
    df = pd.DataFrame({"R": rng.uniform(300, 800, n), "Xc": rng.uniform(30, 90, n), "H": rng.uniform(150, 190, n), "W": rng.uniform(45, 120, n)})
    y = 3.0 * df.H ** 2 / df.R * df.W ** 0.5
    y = y.to_numpy(); y[:5] = -1.0
    beta, r2, n_used, n_nonpos = fit_log_linear(y, df, ["R", "Xc", "H", "W"])
    assert np.allclose(beta, [-1, 0, 2, 0.5], atol=1e-9) and r2 > 1 - 1e-12 and n_used == n - 5 and n_nonpos == 5


def test_bootstrap_interval_for_the_pearson_of_logs_covers_the_truth_and_narrows_with_n():
    # EN: v1.1 — no distributional assumption: rows drawn from a lognormal pair with known Σ; the interval must cover the true
    #     correlation about 95 % of the time (200 repetitions) and narrow with n. Deterministic by seed.
    import numpy as np
    S = np.array([[0.04, 0.02], [0.02, 0.05]]); r_true = S[0, 1] / np.sqrt(S[0, 0] * S[1, 1])
    rng = np.random.default_rng(123); hits = 0; widths = []
    for k in range(200):
        z = rng.multivariate_normal([5.0, 4.0], S, size=120); x, y = np.exp(z[:, 0]), np.exp(z[:, 1])
        lo, hi = bootstrap_pearson_log_ci(x, y, B=200, seed=k, level=0.95); hits += lo <= r_true <= hi; widths.append(hi - lo)
    assert 0.90 <= hits / 200 <= 0.99, hits
    z = rng.multivariate_normal([5.0, 4.0], S, size=3000); lo2, hi2 = bootstrap_pearson_log_ci(np.exp(z[:, 0]), np.exp(z[:, 1]), B=200, seed=1)
    assert (hi2 - lo2) < np.median(widths) / 3
    assert bootstrap_pearson_log_ci(x, y, B=200, seed=7) == bootstrap_pearson_log_ci(x, y, B=200, seed=7)   # deterministic



# ---- Lição 12 (contrato v0.6): vetores implícitos do alvo/controle, cosseno sob Σ, identidade r = cos·√R²
Y_DEV = np.array([0.21, -0.07, -0.08, -0.06]); C_DEV = np.array([0.075, -0.025, -0.155, 0.105])


def test_lesson12_implicit_vectors_and_geometry():
    S = _sigma_population()
    frame = pd.DataFrame({"R": np.exp(R_DEV), "H": np.exp(H_DEV)})       # EN: logs of these are exactly the deviations
    t, r2_t, n, _ = fit_log_linear(np.exp(Y_DEV), frame, ["R", "H"])
    u, r2_c, _, _ = fit_log_linear(np.exp(C_DEV), frame, ["R", "H"])
    assert n == 4
    assert np.abs(t - [-0.5, 1.0]).max() < 1e-9 and np.abs(u - [-0.5, 1.0]).max() < 1e-9      # exercícios 13-14
    assert abs(r2_t - 0.60) < 1e-9 and abs(r2_c - 0.00885 / 0.010325) < 1e-9
    assert abs(predicted_pearson_log(t, u, S) - 1.0) < 1e-12                                    # exercício 15
    assert abs(np.corrcoef(Y_DEV, C_DEV)[0, 1] - 0.478) < 1e-3                                   # correlação bruta 0,48
    a, b = np.array([-1.0, 2.0]), np.array([1.0, -1.0])
    lnA = -R_DEV + 2 * H_DEV
    for y, r2, expected in ((Y_DEV, r2_t, 0.7746), (C_DEV, r2_c, 0.9258)):                    # exercício 16
        ident = predicted_pearson_log(a, t, S) * np.sqrt(r2)
        assert abs(ident - np.corrcoef(lnA, y)[0, 1]) < 1e-12 and abs(ident - expected) < 5e-4
    assert abs(predicted_pearson_log(a, u, S)) >= 0.90 and abs(predicted_pearson_log(t, u, S)) >= 0.80   # exercício 17
    assert abs(predicted_pearson_log(b, u, S) - (-0.998)) < 5e-4

"""
EN: Algebraic part (CONTRATOS.md §2 of the method): exponent vectors, log-covariance Σ, analytic correlation
    between indices, observed correlations, redundancy with precedence, Σ transfer between strata.
ES: Parte algebraica: vectores de exponentes, Σ de logaritmos, correlación analítica entre índices, correlaciones
    observadas, redundancia con precedencia, transferencia de Σ entre estratos.
PT: Parte algébrica: vetores de expoentes, Σ dos logaritmos, correlação analítica entre índices, correlações
    observadas, redundância com precedência, transferência de Σ entre estratos.

Exactness / Exactitud / Exatidão:
  ln I = a·z  (z = logs of the variables)  ⇒  Var(ln I) = aᵀΣa,  Cov(ln I, ln J) = aᵀΣb,
  Pearson(ln I, ln J) = aᵀΣb / sqrt(aᵀΣa · bᵀΣb)  — an identity, no distributional assumption.
  Spearman conversion ρ_s = (6/π)·asin(r/2) assumes bivariate normality of the logs (reported as secondary).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .catalog import Catalog, Entry

# EN: how a derived name in a catalog `vector` maps onto base variables (log-linear identities).
# ES/PT: cómo un nombre derivado del `vector` se expresa en variables base (identidades log-lineales).
_DERIVED_TO_BASE = {"H_m": {"H": 1.0}, "II": {"H": 2.0, "R": -1.0}, "PhA": {"Xc": 1.0, "R": -1.0}, "Z": {"R": 1.0}}


@dataclass
class VectorFit:
    """
    EN: exponent vector of one method in one stratum. `source` = 'catalog' (monomial) or 'fitted' (log-linear OLS).
    ES: vector de exponentes de un método en un estrato. `source` = 'catalog' o 'fitted'.
    PT: vetor de expoentes de um método em um estrato. `source` = 'catalog' ou 'fitted'.
    """
    method_id: str
    stratum: str
    variables: tuple[str, ...]
    vector: np.ndarray            # aligned with `variables`
    source: str
    n: int
    n_nonpositive_pred: int
    fit_r2: float                 # 1.0 for catalog monomials


# ----------------------------------------------------------------------------------------------
def log_covariance(frame: pd.DataFrame, variables: Sequence[str]) -> tuple[np.ndarray, int]:
    """
    EN: Σ = sample covariance (ddof=1) of ln(variables) over complete rows. Returns (Σ, n).
    ES: Σ = covarianza muestral (ddof=1) de ln(variables) sobre filas completas. Devuelve (Σ, n).
    PT: Σ = covariância amostral (ddof=1) de ln(variáveis) nas linhas completas. Retorna (Σ, n).
    """
    X = frame.loc[:, list(variables)].to_numpy(dtype=float)
    ok = np.isfinite(X).all(axis=1)
    L = np.log(X[ok])
    if L.shape[0] < 3:
        raise ValueError("Σ needs at least 3 complete rows")
    return np.cov(L.T, ddof=1), int(ok.sum())


def vector_from_catalog(entry: Entry, variables: Sequence[str]) -> np.ndarray:
    """
    EN: express a catalog monomial vector on the ordered `variables` (derived names re-expressed on base ones).
    ES: expresa el vector monomial del catálogo sobre `variables` (derivados re-expresados en base).
    PT: expressa o vetor monomial do catálogo sobre `variables` (derivados re-expressos nas base).
    """
    if entry.form != "monomial" or not entry.vector:
        raise ValueError(f"{entry.id}: not a catalog monomial")
    acc: dict[str, float] = {}
    for k, v in entry.vector.items():
        v = float(v)
        if v == 0:
            continue
        if k in _DERIVED_TO_BASE:
            for kb, w in _DERIVED_TO_BASE[k].items():
                acc[kb] = acc.get(kb, 0.0) + v * w
        else:
            acc[k] = acc.get(k, 0.0) + v
    missing = set(acc) - set(variables)
    if missing:
        raise ValueError(f"{entry.id}: vector uses {sorted(missing)} which are not among the mapped variables {list(variables)}")
    return np.array([acc.get(v, 0.0) for v in variables], dtype=float)


def fit_log_linear(y: np.ndarray, frame: pd.DataFrame, variables: Sequence[str]) -> tuple[np.ndarray, float, int, int]:
    """
    EN: OLS of ln(y) on ln(variables) with intercept, over rows with finite inputs and y > 0.
        Returns (coefficients, R², n_used, n_nonpositive). R² is the fraction of variance of ln(y) explained.
    ES: MCO de ln(y) sobre ln(variables) con intercepto, en filas con entradas finitas e y > 0.
    PT: MQO de ln(y) sobre ln(variáveis) com intercepto, nas linhas com entradas finitas e y > 0.
    """
    X = frame.loc[:, list(variables)].to_numpy(dtype=float)
    y = np.asarray(y, dtype=float)
    finite = np.isfinite(X).all(axis=1) & np.isfinite(y)
    pos = finite & (y > 0)
    n_nonpos = int((finite & ~(y > 0)).sum())
    if pos.sum() < len(variables) + 2:
        raise ValueError("not enough rows for the log-linear fit")
    A = np.column_stack([np.ones(pos.sum())] + [np.log(X[pos, j]) for j in range(X.shape[1])])
    ly = np.log(y[pos])
    beta, *_ = np.linalg.lstsq(A, ly, rcond=None)
    resid = ly - A @ beta
    r2 = 1.0 - float((resid ** 2).sum()) / float(((ly - ly.mean()) ** 2).sum())
    return beta[1:], r2, int(pos.sum()), n_nonpos


def predicted_pearson_log(a: np.ndarray, b: np.ndarray, sigma: np.ndarray) -> float:
    """EN: aᵀΣb / sqrt(aᵀΣa · bᵀΣb). ES/PT: idem — identidade exata para Pearson dos logs."""
    num = float(a @ sigma @ b)
    den = float(np.sqrt((a @ sigma @ a) * (b @ sigma @ b)))
    return num / den


def pearson_to_spearman(r: float) -> float:
    """EN: (6/π)·asin(r/2), valid under bivariate normality (secondary). ES/PT: conversão sob normalidade bivariada."""
    return float((6.0 / np.pi) * np.arcsin(np.clip(r, -1.0, 1.0) / 2.0))


def fisher_ci(r: float, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """EN: Fisher z interval for a correlation. ES/PT: intervalo de Fisher."""
    from scipy.stats import norm
    z = np.arctanh(np.clip(r, -0.999999, 0.999999)); se = 1.0 / np.sqrt(n - 3); q = norm.ppf(1 - alpha / 2)
    return float(np.tanh(z - q * se)), float(np.tanh(z + q * se))


# ----------------------------------------------------------------------------------------------
def compute_vectors(cat: Catalog, values: dict[str, np.ndarray], frame: pd.DataFrame, variables: Sequence[str],
                    stratum: str, *, extra_log_variables: Sequence[str] = ()) -> dict[str, VectorFit]:
    """
    EN: one VectorFit per evaluable method. Monomials use the catalog vector (source 'catalog'); composites are fitted.
        `values[method_id]` are the method values on `frame` rows (NaN allowed). `extra_log_variables` (e.g. age)
        are appended to the log-linear design when declared.
    ES: un VectorFit por método evaluable. Monomios usan el vector del catálogo; compuestos se ajustan.
    PT: um VectorFit por método avaliável. Monômios usam o vetor do catálogo; compostos são ajustados.
    """
    out: dict[str, VectorFit] = {}
    design = tuple(variables) + tuple(extra_log_variables)
    for e in cat.entries:
        if e.id not in values:
            continue
        y = values[e.id]
        if e.form == "monomial":
            try:
                vec = vector_from_catalog(e, design)
            except ValueError:
                continue
            n = int(np.isfinite(y).sum())
            out[e.id] = VectorFit(e.id, stratum, design, vec, "catalog", n, int((np.isfinite(y) & ~(y > 0)).sum()), 1.0)
        else:
            try:
                beta, r2, n, nnp = fit_log_linear(y, frame, design)
            except ValueError:
                continue
            out[e.id] = VectorFit(e.id, stratum, design, beta, "fitted", n, nnp, r2)
    return out


def pairs_table(cat: Catalog, vecs: dict[str, VectorFit], values: dict[str, np.ndarray], sigma: np.ndarray,
                stratum: str, *, min_pair_n: int = 30, alpha: float = 0.05) -> pd.DataFrame:
    """
    EN: all method pairs in a stratum: predicted Pearson-on-logs (exact), observed Pearson-on-logs, observed Spearman,
        converted Spearman, Fisher CI on the observed Spearman, identity flag.
    ES/PT: todos os pares no estrato com previsto/observado e flag de identidade.
    """
    ids = [e.id for e in cat.entries if e.id in vecs]
    identity = {e.id: e.identity_of for e in cat.entries if e.identity_of}
    rows = []
    for a, b in combinations(ids, 2):
        va, vb = values[a], values[b]
        ok = np.isfinite(va) & np.isfinite(vb) & (va > 0) & (vb > 0)
        n = int(ok.sum())
        if n < min_pair_n:
            continue
        r_pred = predicted_pearson_log(vecs[a].vector, vecs[b].vector, sigma)
        r_obs = float(np.corrcoef(np.log(va[ok]), np.log(vb[ok]))[0, 1])
        rho_obs = float(spearmanr(va[ok], vb[ok])[0])
        lo, hi = fisher_ci(rho_obs, n, alpha)
        # EN: `identity` = the pair is (method, its exact transformation) OR involves a copy (a method with identity_of),
        #     whose pairs duplicate the original's; such pairs are excluded from prediction statistics and figures.
        is_id = identity.get(a) == b or identity.get(b) == a or a in identity or b in identity
        rows.append(dict(a_id=a, b_id=b, stratum=stratum, n_pair=n, r_log_predicted=r_pred, r_log_observed=r_obs,
                         rho_sp_observed=rho_obs, rho_sp_converted=pearson_to_spearman(r_pred), ci_lo=lo, ci_hi=hi,
                         within_ci=bool(lo <= pearson_to_spearman(r_pred) <= hi), abs_err_log=abs(r_pred - r_obs), identity=is_id))
    return pd.DataFrame(rows)


def redundancy_table(cat: Catalog, pairs: pd.DataFrame, stratum: str, *, threshold: float = 0.95) -> pd.DataFrame:
    """
    EN: for each method, the strongest |Spearman| with an earlier-precedence method (§2.2); redundant if ≥ threshold.
        Identities are reported as 'identity' and never as discovered redundancy.
    ES/PT: para cada método, o maior |Spearman| com um antecessor; redundante se ≥ limiar; identidades à parte.
    """
    order = {e.id: i for i, e in enumerate(cat.sorted_by_precedence())}
    year = {e.id: e.year for e in cat.entries}
    identity = {e.id: e.identity_of for e in cat.entries if e.identity_of}
    rows = []
    ids = sorted(set(pairs.a_id) | set(pairs.b_id), key=lambda i: order[i])
    for m in ids:
        cand = pairs[((pairs.a_id == m) | (pairs.b_id == m)) & (~pairs.identity)]
        best = None
        for _, p in cand.iterrows():
            other = p.b_id if p.a_id == m else p.a_id
            if order[other] < order[m]:
                v = abs(p.rho_sp_observed)
                if best is None or v > best[0]:
                    best = (v, other, p.r_log_predicted)
        rows.append(dict(method_id=m, stratum=stratum, rho_sp_max=(best[0] if best else np.nan),
                         predecessor_id=(best[1] if best else None), predecessor_year=(year[best[1]] if best else None),
                         r_log_predicted_with_predecessor=(best[2] if best else np.nan),
                         redundant=bool(best is not None and best[0] >= threshold and m not in identity),
                         identity_of=identity.get(m)))
    return pd.DataFrame(rows)


def sigma_transfer_table(vecs_by_stratum: dict[str, dict[str, VectorFit]], sigma_by_stratum: dict[str, np.ndarray],
                         pairs_by_stratum: dict[str, pd.DataFrame], *, exclude_identity: bool = True) -> pd.DataFrame:
    """
    EN: apply Σ of stratum s (with s's fitted vectors) to predict the correlations observed in stratum t.
        type = 'own' when s == t. Reports median and max absolute error on Pearson-of-logs and Spearman-in-CI fraction.
    ES/PT: aplica Σ do estrato s aos vetores de s e compara com o observado no estrato t.
    """
    rows = []
    for s, vs in vecs_by_stratum.items():
        S = sigma_by_stratum[s]
        for t, pt in pairs_by_stratum.items():
            errs, errs_sp, inci, n = [], [], 0, 0
            for _, p in pt.iterrows():
                if exclude_identity and p.identity:
                    continue
                if p.a_id not in vs or p.b_id not in vs:
                    continue
                r_pred = predicted_pearson_log(vs[p.a_id].vector, vs[p.b_id].vector, S)
                sp_pred = pearson_to_spearman(r_pred)
                errs.append(abs(r_pred - p.r_log_observed)); errs_sp.append(abs(sp_pred - p.rho_sp_observed)); n += 1
                inci += int(p.ci_lo <= sp_pred <= p.ci_hi)
            if n:
                rows.append(dict(sigma_from=s, observed_in=t, type=("own" if s == t else "transfer"), pairs=n,
                                 within_ci_frac=inci / n, median_abs_err=float(np.median(errs)), max_abs_err=float(np.max(errs)),
                                 median_abs_err_sp=float(np.median(errs_sp)), max_abs_err_sp=float(np.max(errs_sp))))
    return pd.DataFrame(rows)

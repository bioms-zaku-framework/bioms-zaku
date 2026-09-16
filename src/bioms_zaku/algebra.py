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
# EN: exact re-expressions only (H_m = H/100, II = H²/R). PhA and Z are not monomials and never reach a catalog vector (§2.3).
_DERIVED_TO_BASE = {"H_m": {"H": 1.0}, "II": {"H": 2.0, "R": -1.0}}


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


def bootstrap_pearson_log_ci(x: np.ndarray, y: np.ndarray, *, B: int = 200, seed: int = 42, level: float = 0.95) -> tuple[float, float]:
    """
    EN: percentile interval for the Pearson correlation of ln x and ln y by resampling PEOPLE (rows) — no distributional
        assumption (the Fisher z interval assumed bivariate normality of the logs, rejected on NHANES; v1.1). Deterministic.
    ES/PT: intervalo por percentis do bootstrap de pessoas para a correlação de Pearson dos logs; sem pressuposto de distribuição.
    """
    lx, ly = np.log(np.asarray(x, float)), np.log(np.asarray(y, float)); n = len(lx)
    rng = np.random.default_rng(seed); rs = np.empty(B)
    for b in range(B):
        i = rng.integers(0, n, n)
        a, c = lx[i], ly[i]
        sa, sc = a.std(), c.std()
        rs[b] = float(np.corrcoef(a, c)[0, 1]) if sa > 0 and sc > 0 else np.nan
    rs = rs[np.isfinite(rs)]
    if len(rs) < max(20, B // 10):
        return float("nan"), float("nan")
    q = (1 - level) / 2 * 100
    return float(np.percentile(rs, q)), float(np.percentile(rs, 100 - q))


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
                stratum: str, *, min_pair_n: int = 30, ci_level: float = 0.95, B: int = 200, seed: int = 42) -> pd.DataFrame:
    """
    EN: all method pairs in a stratum: predicted Pearson-on-logs (exact identity), observed Pearson-on-logs with a person-
        bootstrap percentile interval (descriptive, distribution-free; v1.1), observed Spearman, identity flag. No Spearman
        conversion (v0.5: the identity is stated and checked on the Pearson-of-logs scale only).
    ES/PT: todos os pares no estrato com previsto/observado (intervalo bootstrap) e flag de identidade.
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
        lo, hi = bootstrap_pearson_log_ci(va[ok], vb[ok], B=B, seed=seed, level=ci_level)
        # EN: `identity` = the pair is (method, its exact transformation) OR involves a copy (a method with identity_of),
        #     whose pairs duplicate the original's; such pairs are excluded from prediction statistics and figures.
        is_id = identity.get(a) == b or identity.get(b) == a or a in identity or b in identity
        rows.append(dict(a_id=a, b_id=b, stratum=stratum, n_pair=n, r_log_predicted=r_pred, r_log_observed=r_obs,
                         rho_sp_observed=rho_obs, r_log_lo=lo, r_log_hi=hi, abs_err_log=abs(r_pred - r_obs), identity=is_id))
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
                         values_by_stratum: dict[str, dict[str, np.ndarray]], *, design_by_stratum: dict[str, np.ndarray] | None = None,
                         identity_ids: set[str] | frozenset[str] = frozenset(),
                         tol: float = 0.05, B: int = 200, seed: int = 42, min_pair_n: int = 30) -> pd.DataFrame:
    """
    EN: §4.1 (v0.5) transfer of Σ, in an n-fair metric. For each source stratum s and observed stratum t:
        transfer error = |ρ predicted with Σ_s and s's vectors − ρ observed in t| (Pearson of logs, pair-wise complete case);
        own error = the same with Σ_t and t's vectors (exactly 0 for exact monomials: the identity; > 0 only for fitted
        vectors); excess = transfer − own, pair by pair. Summaries: median, 90th percentile, max, fraction within a fixed
        tolerance `tol` (independent of n), and a percentile bootstrap (B resamples of the PERSONS of t, seed fixed) for
        the median transfer error and the median excess. In each resample Σ_t is recomputed from the resampled rows of
        `design_by_stratum[t]` (log-variables aligned with the values), so the own prediction keeps its identity property
        inside the resample; Σ_s (the transferred one) and all vectors stay fixed. Without `design_by_stratum` the own Σ
        is kept fixed (then the own error carries sampling noise; documented). No Spearman conversion, no Fisher interval.
    ES: transferencia de Σ en métrica justa respecto a n (v0.5). PT: transferência de Σ em métrica justa quanto a n (v0.5).
    """
    rows = []
    rng_master = np.random.default_rng(seed)
    for t, vals_t in values_by_stratum.items():
        vt = vecs_by_stratum[t]; St = sigma_by_stratum[t]
        ids = [m for m in vt if m in vals_t and m not in identity_ids]
        if len(ids) < 2:
            continue
        L = np.column_stack([np.where(np.isfinite(vals_t[m]) & (vals_t[m] > 0), np.log(np.where(vals_t[m] > 0, vals_t[m], 1.0)), np.nan) for m in ids])
        n = L.shape[0]
        pairs = [(i, j) for i in range(len(ids)) for j in range(i + 1, len(ids))
                 if int((np.isfinite(L[:, i]) & np.isfinite(L[:, j])).sum()) >= min_pair_n]
        if not pairs:
            continue
        def observed(Lm: np.ndarray) -> np.ndarray:
            C = pd.DataFrame(Lm).corr(min_periods=min_pair_n).to_numpy()
            return np.array([C[i, j] for i, j in pairs])
        obs = observed(L)
        own_pred = np.array([predicted_pearson_log(vt[ids[i]].vector, vt[ids[j]].vector, St) for i, j in pairs])
        err_own = np.abs(own_pred - obs)
        rng = np.random.default_rng(rng_master.integers(0, 2**32 - 1))
        boot_idx = [rng.integers(0, n, n) for _ in range(B)] if B > 0 else []
        boot_obs = [observed(L[ii]) for ii in boot_idx]
        D = design_by_stratum.get(t) if design_by_stratum else None
        def own_pred_for(ii):
            if D is None:
                return own_pred
            Dr = D[ii]; Dr = Dr[np.isfinite(Dr).all(axis=1)]
            if Dr.shape[0] < 3:
                return own_pred
            Sb = np.cov(Dr.T, ddof=1)
            return np.array([predicted_pearson_log(vt[ids[i]].vector, vt[ids[j]].vector, Sb) for i, j in pairs])
        boot_own = [own_pred_for(ii) for ii in boot_idx]
        for s, vs in vecs_by_stratum.items():
            Ss = sigma_by_stratum[s]
            usable = [k for k, (i, j) in enumerate(pairs) if ids[i] in vs and ids[j] in vs]
            if not usable:
                continue
            pred = np.array([predicted_pearson_log(vs[ids[i]].vector, vs[ids[j]].vector, Ss) for i, j in (pairs[k] for k in usable)])
            o = obs[usable]; eo = err_own[usable]
            err = np.abs(pred - o); exc = err - eo
            finite = np.isfinite(err) & np.isfinite(exc)
            if not finite.any():
                continue
            med_b, exc_b = [], []
            for bo, op in zip(boot_obs, boot_own):
                ob = bo[usable]; eo_b = np.abs(op[usable] - ob)
                e = eo_b if s == t else np.abs(pred - ob)      # EN: own row: Σ_t recomputed in the resample (identity kept)
                f = np.isfinite(e) & np.isfinite(eo_b)
                if f.any():
                    med_b.append(float(np.median(e[f]))); exc_b.append(float(np.median(e[f]) - np.median(eo_b[f])))
            q = lambda a, p: float(np.percentile(a, p)) if len(a) else float("nan")
            rows.append(dict(sigma_from=s, observed_in=t, type=("own" if s == t else "transfer"), pairs=int(finite.sum()),
                             median_abs_err=float(np.median(err[finite])), p90_abs_err=float(np.percentile(err[finite], 90)),
                             max_abs_err=float(np.max(err[finite])), frac_within_tol=float((err[finite] <= tol).mean()), tol=tol,
                             own_median_abs_err=float(np.median(eo[finite])), excess_median=float(np.median(err[finite]) - np.median(eo[finite])),
                             median_abs_err_lo=q(med_b, 2.5), median_abs_err_hi=q(med_b, 97.5),
                             excess_lo=q(exc_b, 2.5), excess_hi=q(exc_b, 97.5), boot_B=len(med_b)))
    return pd.DataFrame(rows)



# ---------------------------------------------------------------------------------------------------------------------
# v0.6 — geometry of target and control in the space of the mapped variables (CONTRATOS §3.3)
# ---------------------------------------------------------------------------------------------------------------------
def _cos_sigma(a: np.ndarray, b: np.ndarray, sigma: np.ndarray) -> float:
    return predicted_pearson_log(a, b, sigma)


def geometry_tables(vecs: dict[str, "VectorFit"], vals: dict[str, np.ndarray], frame: pd.DataFrame, variables: Sequence[str],
                    targets: dict[str, np.ndarray], controls: dict[str, np.ndarray], pairing: dict[str, str], stratum: str, *,
                    parallel_to_control: float = 0.90, coupled_target_control: float = 0.80, min_fit_r2: float = 0.50
                    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    EN: Implicit vectors of every continuous target/control (OLS of ln y on the ln variables, `fit_log_linear`) and, per
        index × target, the Σ-cosines index–target^, index–control^, target^–control^ plus the exact identity
        r_log(index, y) = cos_Σ(index, y^)·√R²_y, which holds when the index is an exact monomial in the variables
        (vector_source 'catalog'); for fitted vectors the gap is reported. Everything for one index is computed on the
        complete-case rows of (index > 0, target > 0, control > 0, finite variables), so the identity is exact by
        construction; the implicit-vector table uses the rows of (target, control, variables). Flags never touch verdicts.
    ES: vectores implícitos y cosenos bajo Σ; identidad exacta para monomios. PT: vetores implícitos e cossenos sob Σ;
        identidade exata para monômios; bandeiras nunca alteram vereditos.
    """
    V = list(variables)
    X = frame.loc[:, V].to_numpy(dtype=float)
    fin = np.isfinite(X).all(axis=1) & (X > 0).all(axis=1)
    thr = f"parallel_to_control>={parallel_to_control};coupled_target_control>={coupled_target_control};min_fit_r2>={min_fit_r2}"
    imp_rows, geo_rows = [], []

    def _fit(y: np.ndarray, rows: np.ndarray) -> tuple[np.ndarray, float]:
        vec, r2, _, _ = fit_log_linear(y[rows], frame.loc[rows, V], V)
        return vec, r2

    for t, c in pairing.items():
        if t not in targets or c not in controls:
            continue
        yt, yc = np.asarray(targets[t], float), np.asarray(controls[c], float)
        base = fin & np.isfinite(yt) & (yt > 0) & np.isfinite(yc) & (yc > 0)
        if base.sum() < len(V) + 2:
            continue
        for role, name, y in (("target", t, yt), ("control", c, yc)):
            vec, r2 = _fit(y, base)
            row = dict(stratum=stratum, role=role, name=name, n=int(base.sum()), fit_r2=r2, poor_projection=bool(r2 < min_fit_r2))
            row.update({f"e_{v}": float(x) for v, x in zip(V, vec)})
            imp_rows.append(row)
        for mid, vf in vecs.items():
            v = np.asarray(vals.get(mid), float) if mid in vals else None
            if v is None or list(vf.variables) != V:
                continue
            rows = base & np.isfinite(v) & (v > 0)
            n = int(rows.sum())
            if n < len(V) + 2:
                continue
            S, _ = log_covariance(frame.loc[rows], V)
            tv, r2t = _fit(yt, rows); cv, r2c = _fit(yc, rows)
            a = np.asarray(vf.vector, float)
            cos_t, cos_c, cos_tc = _cos_sigma(a, tv, S), _cos_sigma(a, cv, S), _cos_sigma(tv, cv, S)
            lv = np.log(v[rows])
            r_t = float(np.corrcoef(lv, np.log(yt[rows]))[0, 1]); r_c = float(np.corrcoef(lv, np.log(yc[rows]))[0, 1])
            id_t, id_c = cos_t * np.sqrt(max(r2t, 0.0)), cos_c * np.sqrt(max(r2c, 0.0))
            ok = (r2t >= min_fit_r2) and (r2c >= min_fit_r2)
            geo_rows.append(dict(method_id=mid, stratum=stratum, target=t, control=c, n=n, vector_source=vf.source,
                                 cos_target=cos_t, cos_control=cos_c, cos_target_control=cos_tc,
                                 r_log_target_observed=r_t, r_log_target_identity=float(id_t), r_log_target_gap=r_t - float(id_t),
                                 r_log_control_observed=r_c, r_log_control_identity=float(id_c), r_log_control_gap=r_c - float(id_c),
                                 fit_r2_target=r2t, fit_r2_control=r2c, poor_projection=bool(not ok),
                                 flag_parallel_to_control=bool(ok and abs(cos_c) >= parallel_to_control),
                                 flag_coupled_target_control=bool(ok and abs(cos_tc) >= coupled_target_control), thresholds=thr))
    return pd.DataFrame(imp_rows), pd.DataFrame(geo_rows)

"""
EN: Index design for a context (CONTRATOS.md §2.7): fit an exponent vector to a target on a design partition; audit on
    the disjoint partition. Deterministic splits recorded for the manifest.
ES: Diseño de índices para un contexto: ajusta un vector de exponentes en la partición de diseño; audita en la otra.
PT: Desenho de índices para um contexto: ajusta um vetor de expoentes na partição de desenho; audita na outra.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from .algebra import fit_log_linear


class DesignError(ValueError):
    """EN/ES/PT: invalid design configuration."""


@dataclass
class Split:
    """EN: row masks for design and audit partitions + provenance. ES/PT: máscaras das partições + procedência."""
    design: np.ndarray
    audit: np.ndarray
    mode: str
    fraction: float | None
    seed: int | None
    stratify_on: str | None
    design_hash: str

    @property
    def n_design(self) -> int: return int(self.design.sum())
    @property
    def n_audit(self) -> int: return int(self.audit.sum())


def holdout_split(frame: pd.DataFrame, *, fraction: float = 0.70, seed: int = 42, stratify: pd.Series | None = None,
                  id_col: str | None = None) -> Split:
    """
    EN: deterministic holdout. `fraction` is the design share; stratified by `stratify` (stratum and/or class) when given;
        grouped by `id_col` when repeated ids exist (all rows of a person on one side).
    ES/PT: holdout determinístico; estratificado; agrupado por id quando há repetição.
    """
    if fraction not in (0.60, 0.70, 0.75):
        raise DesignError("design.fraction must be one of 0.60, 0.70, 0.75 (declared options)")
    n = len(frame)
    if id_col and frame[id_col].duplicated().any():
        ids = frame[id_col].unique()
        rng = np.random.default_rng(seed); rng.shuffle(ids)
        k = int(round(fraction * len(ids)))
        design = frame[id_col].isin(ids[:k]).to_numpy()
    else:
        idx = np.arange(n)
        strat = None if stratify is None else stratify.astype(str).to_numpy()
        d_idx, _ = train_test_split(idx, train_size=fraction, random_state=seed, stratify=strat)
        design = np.zeros(n, dtype=bool); design[d_idx] = True
    audit = ~design
    h = hashlib.sha256(np.packbits(design).tobytes()).hexdigest()[:16]
    return Split(design, audit, "holdout", fraction, seed, None if stratify is None else str(stratify.name), h)


def by_stratum_split(frame: pd.DataFrame, strata_col: str, design_value, audit_value) -> Split:
    """EN: design in one stratum, audit in another (transfer). ES/PT: desenha num estrato, audita em outro."""
    design = (frame[strata_col] == design_value).to_numpy(); audit = (frame[strata_col] == audit_value).to_numpy()
    if not design.any() or not audit.any():
        raise DesignError("by_stratum: empty design or audit partition")
    h = hashlib.sha256(np.packbits(design).tobytes()).hexdigest()[:16]
    return Split(design, audit, "by_stratum", None, None, strata_col, h)


@dataclass
class DesignedIndex:
    """EN: a designed monomial index. ES/PT: um índice monomial desenhado."""
    id: str
    target: str
    variables: tuple[str, ...]
    vector_design: np.ndarray
    r2_design: float
    n_design: int
    vector_refit_full: np.ndarray | None
    r2_refit_full: float | None
    split: Split
    orthogonal_to: str | None = None          # EN: control the vector was made Σ-orthogonal to (v0.9), None = plain fit
    control_vector: np.ndarray | None = None  # EN: implicit vector of the control on the design partition
    cos_control_design: float | None = None   # EN: cos_Σ(vector_design, control_vector) on the design partition (0 by construction)
    r2_unconstrained: float | None = None     # EN: R² of the plain fit, for comparison with r2_design
    vector_lo: np.ndarray | None = None       # EN: v1.1 — percentile 2.5 of each exponent over person-bootstrap resamples of the design rows
    vector_hi: np.ndarray | None = None       # EN: percentile 97.5
    B_vector: int = 0

    def expr(self, use_refit: bool = False) -> str:
        v = self.vector_refit_full if (use_refit and self.vector_refit_full is not None) else self.vector_design
        return " * ".join(f"{name}**({coef:.6f})" for name, coef in zip(self.variables, v))

    def values(self, frame: pd.DataFrame, use_refit: bool = False) -> np.ndarray:
        v = self.vector_refit_full if (use_refit and self.vector_refit_full is not None) else self.vector_design
        X = frame.loc[:, list(self.variables)].to_numpy(float)
        return np.exp(np.log(X) @ v)


def _log_design(frame: pd.DataFrame, cols: Sequence[str], variables: Sequence[str]) -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray]:
    """EN: rows with finite, positive `cols` and finite variables; returns (mask, {col: ln values}, ln X)."""
    X = frame.loc[:, list(variables)].to_numpy(dtype=float)
    ok = np.isfinite(X).all(axis=1) & (X > 0).all(axis=1)
    ys = {}
    for c in cols:
        y = frame[c].to_numpy(dtype=float); ok &= np.isfinite(y) & (y > 0); ys[c] = y
    return ok, {c: np.log(y[ok]) for c, y in ys.items()}, np.log(X[ok])


def _ols(ly: np.ndarray, LX: np.ndarray) -> tuple[np.ndarray, float]:
    A = np.column_stack([np.ones(len(ly)), LX]); beta, *_ = np.linalg.lstsq(A, ly, rcond=None)
    resid = ly - A @ beta
    return beta[1:], 1.0 - float((resid ** 2).sum()) / float(((ly - ly.mean()) ** 2).sum())


def _r2_of(ly: np.ndarray, LX: np.ndarray, a: np.ndarray) -> float:
    """EN: R² of ln(target) explained by the fixed vector `a` (intercept refitted)."""
    pred = LX @ a; pred = pred - pred.mean() + ly.mean()
    return 1.0 - float(((ly - pred) ** 2).sum()) / float(((ly - ly.mean()) ** 2).sum())


def orthogonal_fit(ly: np.ndarray, lc: np.ndarray, LX: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float, float]:
    """
    EN: constrained least squares (v0.9): the vector `a` that best explains ln(target) among those Σ-orthogonal to the control's
        implicit vector ĉ, i.e. aᵀΣĉ = 0 (cos_Σ(a, ĉ) = 0). Closed form: a = a_ols − (ĉᵀΣa_ols / ĉᵀΣĉ)·ĉ, with Σ the covariance of the
        log-variables on the same rows (the Σ-projection of a_ols onto ĉ is removed). Returns (a, ĉ, R²_constrained, R²_unconstrained, cos).
    ES/PT: mínimos quadrados com a restrição de ortogonalidade a ĉ na métrica Σ; forma fechada.
    """
    a_ols, r2_u = _ols(ly, LX); c_hat, _ = _ols(lc, LX)
    Xc = LX - LX.mean(axis=0); S = (Xc.T @ Xc) / max(len(LX) - 1, 1)
    denom = float(c_hat @ S @ c_hat)
    if denom <= 0:
        raise DesignError("orthogonal_to: the control has no variance in the log-variables on the design partition")
    a = a_ols - (float(c_hat @ S @ a_ols) / denom) * c_hat
    cos = float(a @ S @ c_hat) / float(np.sqrt((a @ S @ a) * denom)) if float(a @ S @ a) > 0 else 0.0
    return a, c_hat, _r2_of(ly, LX, a), r2_u, cos


def exponent_intervals(frame: pd.DataFrame, target: str, variables: Sequence[str], mask: np.ndarray, *, orthogonal_to: str | None = None,
                       B: int = 200, seed: int = 42, level: float = 0.95) -> tuple[np.ndarray, np.ndarray]:
    """EN: v1.1 — percentile intervals of the designed exponents by resampling PEOPLE among the design rows (`mask`). Deterministic.
    Tells whether the vector is stable or drifts between resamples; the vector itself stays the fit of the whole partition."""
    d = frame[mask].reset_index(drop=True); n = len(d); rng = np.random.default_rng(seed); vs = []
    cols = [target] + ([orthogonal_to] if orthogonal_to else [])
    for _ in range(B):
        i = rng.integers(0, n, n); db = d.iloc[i]
        try:
            ok, ls, LX = _log_design(db, cols, variables)
            if ok.sum() < len(variables) + 2:
                continue
            if orthogonal_to:
                a, *_ = orthogonal_fit(ls[target], ls[orthogonal_to], LX)
            else:
                a, _ = _ols(ls[target], LX)
            vs.append(a)
        except (ValueError, DesignError, np.linalg.LinAlgError):
            continue
    if len(vs) < max(20, B // 10):
        nan = np.full(len(variables), np.nan); return nan, nan
    V = np.array(vs); q = (1 - level) / 2 * 100
    return np.percentile(V, q, axis=0), np.percentile(V, 100 - q, axis=0)


def design_index(frame: pd.DataFrame, target: str, variables: Sequence[str], split: Split, *, index_id: str,
                 refit_full: bool = True, orthogonal_to: str | None = None, B: int = 200, seed: int = 42) -> DesignedIndex:
    """
    EN: fit ln(target) ~ ln(variables) on the design partition (target must be > 0); optionally refit on all rows for the
        deployable vector. With `orthogonal_to` (a control column), the vector is constrained to cos_Σ = 0 with the control's
        implicit vector on the same rows (v0.9). The audited numbers must come from `split.audit` rows only (enforced by the orchestrator).
    ES/PT: ajusta na partição de desenho; com `orthogonal_to`, restrição de cosseno zero com o controle; reajuste opcional em todas as linhas.
    """
    if orthogonal_to is None:
        y = frame[target].to_numpy(float)
        d = frame[split.design]
        beta, r2, n_used, n_nonpos = fit_log_linear(y[split.design], d, variables)
        if n_nonpos:
            raise DesignError(f"target {target!r} has {n_nonpos} non-positive values in the design partition; a designed monomial needs a positive target")
        vr, r2r = (None, None)
        if refit_full:
            vr, r2r, _, _ = fit_log_linear(y, frame, variables)
        lo, hi = exponent_intervals(frame, target, variables, split.design, B=B, seed=seed)
        return DesignedIndex(index_id, target, tuple(variables), beta, r2, n_used, vr, r2r, split, vector_lo=lo, vector_hi=hi, B_vector=B)
    if orthogonal_to == target:
        raise DesignError("orthogonal_to must differ from the target")
    d = frame[split.design]
    ok, ls, LX = _log_design(d, [target, orthogonal_to], variables)
    if ok.sum() < len(variables) + 2:
        raise DesignError("not enough rows with positive target and control for the orthogonal design")
    a, c_hat, r2, r2_u, cos = orthogonal_fit(ls[target], ls[orthogonal_to], LX)
    vr, r2r = (None, None)
    if refit_full:
        ok_f, ls_f, LX_f = _log_design(frame, [target, orthogonal_to], variables)
        vr, _, r2r, _, _ = orthogonal_fit(ls_f[target], ls_f[orthogonal_to], LX_f)
    lo, hi = exponent_intervals(frame, target, variables, split.design, orthogonal_to=orthogonal_to, B=B, seed=seed)
    return DesignedIndex(index_id, target, tuple(variables), a, r2, int(ok.sum()), vr, r2r, split,
                         orthogonal_to=orthogonal_to, control_vector=c_hat, cos_control_design=cos, r2_unconstrained=r2_u, vector_lo=lo, vector_hi=hi, B_vector=B)

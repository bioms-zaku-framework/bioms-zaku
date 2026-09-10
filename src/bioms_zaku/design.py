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

    def expr(self, use_refit: bool = False) -> str:
        v = self.vector_refit_full if (use_refit and self.vector_refit_full is not None) else self.vector_design
        return " * ".join(f"{name}**({coef:.6f})" for name, coef in zip(self.variables, v))

    def values(self, frame: pd.DataFrame, use_refit: bool = False) -> np.ndarray:
        v = self.vector_refit_full if (use_refit and self.vector_refit_full is not None) else self.vector_design
        X = frame.loc[:, list(self.variables)].to_numpy(float)
        return np.exp(np.log(X) @ v)


def design_index(frame: pd.DataFrame, target: str, variables: Sequence[str], split: Split, *, index_id: str,
                 refit_full: bool = True) -> DesignedIndex:
    """
    EN: fit ln(target) ~ ln(variables) on the design partition (target must be > 0); optionally refit on all rows for the
        deployable vector. The audited numbers must come from `split.audit` rows only (enforced by the orchestrator).
    ES/PT: ajusta na partição de desenho; reajuste opcional em todas as linhas para o vetor de uso prático.
    """
    y = frame[target].to_numpy(float)
    d = frame[split.design]
    beta, r2, n_used, n_nonpos = fit_log_linear(y[split.design], d, variables)
    if n_nonpos:
        raise DesignError(f"target {target!r} has {n_nonpos} non-positive values in the design partition; a designed monomial needs a positive target")
    vr, r2r = (None, None)
    if refit_full:
        vr, r2r, _, _ = fit_log_linear(y, frame, variables)
    return DesignedIndex(index_id, target, tuple(variables), beta, r2, n_used, vr, r2r, split)

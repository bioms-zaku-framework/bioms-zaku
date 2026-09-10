"""
EN: Predictive audit (CONTRATOS.md §3–4): out-of-sample scores, paired OOB bootstrap, negative control, utility over
    covariates, combination gain, verdicts. Every contrast is paired: both sides see the same resamples of the same rows.
ES: Auditoría predictiva: puntajes fuera de muestra, bootstrap OOB pareado, control negativo, utilidad, ganancia por
    combinación, veredictos. Todo contraste es pareado.
PT: Auditoria preditiva: escores fora da amostra, bootstrap OOB pareado, controle negativo, utilidade, ganho por
    combinação, vereditos. Todo contraste é pareado.

Resampling / Reamostragem: for a row set of size n and seed s, the B resamples are a deterministic function of (n, s, B,
min_oob): rng = default_rng(s); repeat ii = rng.integers(0, n, n); oob = rows not drawn; keep if len(oob) ≥ min_oob;
stop at B or after B·max_attempts_factor attempts. Identical row sets ⇒ identical resamples (pairing across methods with
the same complete-case rows); within one contrast the rows are the same by construction.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, Sequence

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score, r2_score, roc_auc_score
from sklearn.model_selection import GroupKFold, RepeatedKFold, RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class AuditError(ValueError):
    """EN: audit configuration/data error. ES/PT: erro de configuração/dados da auditoria."""


# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class AuditConfig:
    task: str = "auto"                    # auto | regression | classification
    estimator: object | None = None       # sklearn estimator; None -> Ridge(alpha=1) / LogisticRegression
    cv_folds: int = 5
    cv_repeats: int = 50
    B: int = 2000
    min_oob: int = 20
    max_attempts_factor: int = 6
    seed_cv: int = 42
    seed_bootstrap: int = 42
    ci: float = 0.95
    p_specific: float = 0.95
    p_control: float = 0.05
    utility_margin: float = 0.03
    impute: bool = False                  # explicit only (§1.4); default complete-case


def default_estimator(task: str):
    """EN/ES/PT: Ridge(α=1) for regression; L2 logistic (C=1, lbfgs, 1000 it.) for classification (§3.2)."""
    if task == "regression":
        return Ridge(alpha=1.0)
    return LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=1000)


def make_pipeline(estimator, impute: bool = False) -> Pipeline:
    """EN: [SimpleImputer(median) →] StandardScaler → estimator. ES/PT: pipeline fixo do contrato."""
    steps = []
    if impute:
        from sklearn.impute import SimpleImputer
        steps.append(("imp", SimpleImputer(strategy="median")))
    steps += [("sc", StandardScaler()), ("est", estimator)]
    return Pipeline(steps)


def infer_task(y: np.ndarray) -> str:
    v = np.unique(y[np.isfinite(y)])
    return "classification" if (len(v) <= 10 and np.all(np.mod(v, 1) == 0)) else "regression"


# ----------------------------------------------------------------------------------------------
def resamples(n: int, seed: int, B: int, min_oob: int, max_attempts_factor: int = 6) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """
    EN: deterministic OOB resamples for a row set of size n (see module docstring). Returns (train_idx, oob_idx) lists.
    ES/PT: reamostras OOB determinísticas para n linhas. Retorna listas (treino, fora-da-amostra).
    """
    rng = np.random.default_rng(seed)
    tr, oob, att = [], [], 0
    idx = np.arange(n)
    while len(tr) < B and att < B * max_attempts_factor:
        att += 1
        ii = rng.integers(0, n, n)
        oo = np.setdiff1d(idx, np.unique(ii))
        if len(oo) < min_oob:
            continue
        tr.append(ii); oob.append(oo)
    return tr, oob


def _score(task: str, y_true: np.ndarray, model, X: np.ndarray) -> float:
    if task == "regression":
        return float(r2_score(y_true, model.predict(X)))
    classes = np.unique(y_true)
    if len(classes) < 2:
        return float("nan")                      # EN: single-class OOB -> dropped by the caller (B_dropped)
    proba = model.predict_proba(X)
    if len(model.classes_) == 2:
        return float(roc_auc_score(y_true, proba[:, 1]))
    # EN: multiclass — AUROC one-vs-rest macro over the classes present in y_true; balanced accuracy reported separately.
    cols = [list(model.classes_).index(c) for c in classes]
    return float(roc_auc_score(y_true, proba[:, cols] / proba[:, cols].sum(axis=1, keepdims=True), multi_class="ovr", average="macro", labels=classes))


def cv_score(X: np.ndarray, y: np.ndarray, task: str, estimator, cfg: AuditConfig, groups: np.ndarray | None = None) -> float:
    """
    EN: repeated K-fold out-of-sample score (mean over folds). Stratified for classification; grouped when `groups` given.
    ES/PT: escore fora da amostra em K-fold repetido; estratificado em classificação; por grupos se houver `groups`.
    """
    pipe = make_pipeline(estimator, cfg.impute)
    if groups is not None:
        splits = []
        rng = np.random.default_rng(cfg.seed_cv)
        for _ in range(cfg.cv_repeats):
            perm = {g: i for i, g in enumerate(rng.permutation(np.unique(groups)))}
            g2 = np.array([perm[g] for g in groups])
            splits += list(GroupKFold(n_splits=cfg.cv_folds).split(X, y, g2))
    elif task == "classification":
        splits = list(RepeatedStratifiedKFold(n_splits=cfg.cv_folds, n_repeats=cfg.cv_repeats, random_state=cfg.seed_cv).split(X, y))
    else:
        splits = list(RepeatedKFold(n_splits=cfg.cv_folds, n_repeats=cfg.cv_repeats, random_state=cfg.seed_cv).split(X))
    scores = []
    for a, b in splits:
        m = clone(pipe).fit(X[a], y[a])
        scores.append(_score(task, y[b], m, X[b]))
    return float(np.nanmean(scores))


def oob_scores(configs: dict[str, np.ndarray], Y: np.ndarray, task: str, estimator, cfg: AuditConfig,
               progress: Callable[[int, int], None] | None = None) -> tuple[dict[str, np.ndarray], int, int]:
    """
    EN: paired OOB bootstrap. `configs` maps a name to a design matrix (same rows); `Y` is (n, k) targets. Returns
        ({name: (B_eff, k) scores}, B_eff, B_dropped). All configs and targets use the same resamples.
    ES/PT: bootstrap OOB pareado; todas as configurações e alvos usam as mesmas reamostras.
    """
    n = Y.shape[0]
    tr, oob = resamples(n, cfg.seed_bootstrap, cfg.B, cfg.min_oob, cfg.max_attempts_factor)
    pipe = make_pipeline(estimator, cfg.impute)
    store = {k: np.full((len(tr), Y.shape[1]), np.nan) for k in configs}
    dropped = 0
    for b, (ii, oo) in enumerate(zip(tr, oob)):
        for k, X in configs.items():
            for t in range(Y.shape[1]):
                if task == "classification" and len(np.unique(Y[oo, t])) < 2:
                    continue
                m = clone(pipe).fit(X[ii], Y[ii, t])
                store[k][b, t] = _score(task, Y[oo, t], m, X[oo])
        if progress and (b + 1) % max(1, len(tr) // 20) == 0:
            progress(b + 1, len(tr))
    if task == "classification":
        keep = ~np.isnan(np.stack([store[k] for k in configs], axis=0)).any(axis=(0, 2))
        dropped = int((~keep).sum())
        store = {k: v[keep] for k, v in store.items()}
    return store, len(tr) - dropped, dropped


# ----------------------------------------------------------------------------------------------
def contrast(d: np.ndarray, cfg: AuditConfig) -> dict:
    """
    EN: paired difference summary: mean, percentile CI, P(d>0). Descriptive (§3.2), not a p-value.
    ES/PT: resumo da diferença pareada: média, IC por percentis, P(d>0). Descritivo, não é valor-p.
    """
    d = d[np.isfinite(d)]
    a = (1 - cfg.ci) / 2 * 100
    lo, hi = np.percentile(d, [a, 100 - a])
    return dict(mean=float(d.mean()), lo=float(lo), hi=float(hi), p=float((d > 0).mean()), n=int(len(d)))


def verdict(c: dict, cfg: AuditConfig) -> str:
    """EN: SPECIFIC / MEASURES_CONTROL / INCONCLUSIVE per §5 rules. ES/PT: veredito conforme as regras fixas."""
    if c["mean"] > 0 and c["lo"] > 0 and c["p"] >= cfg.p_specific:
        return "SPECIFIC"
    if c["mean"] < 0 and c["hi"] < 0 and c["p"] <= cfg.p_control:
        return "MEASURES_CONTROL"
    return "INCONCLUSIVE"


@dataclass
class AuditRow:
    method_id: str
    stratum: str
    target: str
    control: str
    task: str
    metric: str
    estimator: str
    n: int
    B: int
    B_eff: int
    B_dropped: int
    score_cv_target: float
    score_cv_control: float
    score_oob_target_mean: float
    score_oob_control_mean: float
    disc_mean: float
    disc_lo: float
    disc_hi: float
    p_disc: float
    verdict: str


def audit_method(method_id: str, stratum: str, x: np.ndarray, targets: dict[str, np.ndarray], controls: dict[str, np.ndarray],
                 pairing: dict[str, str], cfg: AuditConfig, estimator=None, groups: np.ndarray | None = None,
                 progress: Callable[[int, int], None] | None = None) -> list[AuditRow]:
    """
    EN: specificity audit of ONE index (one column) against each (target, control) pair, on complete-case rows
        (x, target, control all finite). The bootstrap resamples are shared across targets and controls (paired).
    ES/PT: auditoria de especificidade de UM índice contra cada par (alvo, controle), em caso completo.
    """
    rows: list[AuditRow] = []
    names = list(targets) + [c for c in controls if c not in targets]
    Yall = np.column_stack([targets.get(k, controls.get(k)) for k in names])
    ok = np.isfinite(x) & np.isfinite(Yall).all(axis=1)
    if ok.sum() < 30:
        return rows
    X = x[ok].reshape(-1, 1); Y = Yall[ok]; g = groups[ok] if groups is not None else None
    task = cfg.task
    if task == "auto":
        task = infer_task(Y[:, 0])
    est = estimator if estimator is not None else default_estimator(task)
    cv = {k: cv_score(X, Y[:, i], task, est, cfg, g) for i, k in enumerate(names)}
    st, b_eff, b_drop = oob_scores({"idx": X}, Y, task, est, cfg, progress)
    S = st["idx"]
    for t, c in pairing.items():
        it, ic = names.index(t), names.index(c)
        d = S[:, it] - S[:, ic]
        cs = contrast(d, cfg)
        rows.append(AuditRow(method_id, stratum, t, c, task, "R2" if task == "regression" else "AUROC", type(est).__name__,
                             int(ok.sum()), cfg.B, b_eff, b_drop, cv[t], cv[c], float(np.nanmean(S[:, it])), float(np.nanmean(S[:, ic])),
                             cs["mean"], cs["lo"], cs["hi"], cs["p"], verdict(cs, cfg)))
    return rows


@dataclass
class UtilityRow:
    method_id: str
    stratum: str
    target: str
    task: str
    metric: str
    covariates: str
    n: int
    B_eff: int
    score_base: float
    score_with: float
    delta_mean: float
    delta_lo: float
    delta_hi: float
    p_delta: float
    margin: float
    useful: bool


def utility_method(method_id: str, stratum: str, x: np.ndarray, covariates: np.ndarray, cov_names: Sequence[str],
                   targets: dict[str, np.ndarray], cfg: AuditConfig, estimator=None, groups: np.ndarray | None = None) -> list[UtilityRow]:
    """
    EN: added value of the index over covariates: A = covariates, B = covariates + index, same resamples, complete-case
        on the union of columns. Useful if the lower CI bound of (B − A) exceeds the margin (§5).
    ES/PT: valor adicionado do índice sobre as covariáveis; útil se o limite inferior do IC de (B − A) passa a margem.
    """
    names = list(targets)
    Yall = np.column_stack([targets[k] for k in names])
    ok = np.isfinite(x) & np.isfinite(covariates).all(axis=1) & np.isfinite(Yall).all(axis=1)
    if ok.sum() < 30:
        return []
    FA = covariates[ok]; FB = np.column_stack([FA, x[ok]]); Y = Yall[ok]; g = groups[ok] if groups is not None else None
    task = cfg.task if cfg.task != "auto" else infer_task(Y[:, 0])
    est = estimator if estimator is not None else default_estimator(task)
    st, b_eff, _ = oob_scores({"A": FA, "B": FB}, Y, task, est, cfg)
    out = []
    for i, t in enumerate(names):
        d = st["B"][:, i] - st["A"][:, i]
        cs = contrast(d, cfg)
        out.append(UtilityRow(method_id, stratum, t, task, "R2" if task == "regression" else "AUROC", "+".join(cov_names), int(ok.sum()), b_eff,
                              cv_score(FA, Y[:, i], task, est, cfg, g), cv_score(FB, Y[:, i], task, est, cfg, g),
                              cs["mean"], cs["lo"], cs["hi"], cs["p"], cfg.utility_margin, bool(cs["lo"] > cfg.utility_margin)))
    return out


def combination_gain(host_id: str, added_id: str, stratum: str, xh: np.ndarray, xa: np.ndarray, targets: dict[str, np.ndarray],
                     cfg: AuditConfig, estimator, groups: np.ndarray | None = None) -> list[dict]:
    """
    EN: gain of adding index `added` to index `host`: A = [host], B = [host, added]; same resamples; complete-case on both.
    ES/PT: ganho de acrescentar um índice a outro; mesmas reamostras; caso completo nos dois.
    """
    names = list(targets); Yall = np.column_stack([targets[k] for k in names])
    ok = np.isfinite(xh) & np.isfinite(xa) & np.isfinite(Yall).all(axis=1)
    if ok.sum() < 30:
        return []
    A = xh[ok].reshape(-1, 1); Bm = np.column_stack([xh[ok], xa[ok]]); Y = Yall[ok]
    task = cfg.task if cfg.task != "auto" else infer_task(Y[:, 0])
    st, b_eff, _ = oob_scores({"A": A, "B": Bm}, Y, task, estimator, cfg)
    out = []
    for i, t in enumerate(names):
        cs = contrast(st["B"][:, i] - st["A"][:, i], cfg)
        out.append(dict(host_id=host_id, added_id=added_id, stratum=stratum, target=t, n=int(ok.sum()), B_eff=b_eff,
                        score_host=float(np.nanmean(st["A"][:, i])), score_pair=float(np.nanmean(st["B"][:, i])),
                        gain_mean=cs["mean"], gain_lo=cs["lo"], gain_hi=cs["hi"], p_gain=cs["p"]))
    return out


# ----------------------------------------------------------------------------------------------
class Progress:
    """
    EN: real-time progress with ETA, printed from the first unit (project rule).
    ES/PT: progresso em tempo real com estimativa de término, desde a primeira unidade.
    """
    def __init__(self, total: int, label: str = "", printer: Callable[[str], None] = print):
        self.total, self.label, self.printer, self.t0, self.done = total, label, printer, time.time(), 0

    def step(self, what: str = "") -> None:
        self.done += 1
        el = time.time() - self.t0
        eta = el / self.done * (self.total - self.done)
        self.printer(f"[{self.label}] {self.done}/{self.total} {what} | {el:.0f}s elapsed | ETA {eta / 60:.1f} min")

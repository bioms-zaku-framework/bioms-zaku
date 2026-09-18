"""
EN: Predictive audit (CONTRATOS.md §3–4): out-of-sample scores, paired OOB bootstrap, negative control, utility over
    covariates, combination gain, verdicts. Every contrast is paired: both sides see the same resamples of the same rows.

Resampling: for a row set of size n and seed s, the B resamples are a deterministic function of (n, s, B,
min_oob): rng = default_rng(s); repeat ii = rng.integers(0, n, n); oob = rows not drawn; keep if len(oob) ≥ min_oob;
stop at B or after B·max_attempts_factor attempts. Identical row sets ⇒ identical resamples (pairing across methods with
the same complete-case rows); within one contrast the rows are the same by construction.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Callable, Sequence

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import r2_score, roc_auc_score
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
    min_B_eff: int | None = None          # EN: minimum VALID resamples (None → 10 % of B, at least 20, never more than B); below it the audit is refused (v1.0)
    ci_family: float | None = None        # EN: v1.1 — interval level adjusted to the number of methods audited together (1 − 0.05/k); reported, never selected
    k_methods: int = 1
    seed_cv: int = 42
    seed_bootstrap: int = 42
    ci: float = 0.95
    p_specific: float = 0.95
    p_control: float = 0.05
    utility_margin: float = 0.03
    specificity_margin: float = 0.03      # EN: §3.2 (v0.5) — an increment below this is practically nil, however "significant"
    impute: bool = False                  # explicit only (§1.4); default complete-case
    min_n: int = 30                       # minimum complete-case rows for a method to be audited


def default_estimator(task: str):
    """EN/ES/PT: Ridge(α=1) for regression; L2 logistic (C=1, lbfgs, 1000 it.) for classification (§3.2)."""
    if task == "regression":
        return Ridge(alpha=1.0)
    # EN: L2 is the default penalty; naming it (`penalty="l2"`) is deprecated since scikit-learn 1.8 and flooded the terminal with
    #     one FutureWarning per fit (248 500 lines in a 400-row session, 2026-09-16). Version-safe form:
    return LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)


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
    """
    EN: out-of-sample score of a fitted pipeline. Regression: R². Classification (v1.2, citation review of 2026-09-16):
        Tjur's coefficient of discrimination D = mean p̂ among cases − mean p̂ among non-cases (Tjur 2009), the quantity the
        IDI compares between two models (Pencina 2008); asymptotically a fraction of variation explained, so gains in D
        share the R² margin by declared analogy. Multiclass: one-vs-rest macro average of D over the classes present in
        y_true (this tool's extension, declared). ΔAUROC is NOT used as a gain: it is insensitive even to strong markers
        (Pencina 2008); the AUROC is reported alongside by `_auroc` (Hanley & McNeil 1982).
    ES/PT: R² em regressão; D de Tjur em classificação (macro um-contra-todos se multiclasse).
    """
    if task == "regression":
        return float(r2_score(y_true, model.predict(X)))
    classes = np.unique(y_true)
    if len(classes) < 2:
        return float("nan")                      # EN: single-class OOB -> dropped by the caller (B_dropped)
    proba = model.predict_proba(X); mc = list(model.classes_)
    if len(mc) == 2:
        p = proba[:, 1]; pos = mc[1]
        return float(p[y_true == pos].mean() - p[y_true != pos].mean())
    ds = []
    for c in classes:
        if c in mc:
            p = proba[:, mc.index(c)]; ds.append(p[y_true == c].mean() - p[y_true != c].mean())
    return float(np.mean(ds))


def _auroc(y_true: np.ndarray, model, X: np.ndarray) -> float:
    """EN: descriptive AUROC (Hanley & McNeil 1982): binary, or one-vs-rest macro over the classes present in y_true."""
    classes = np.unique(y_true)
    if len(classes) < 2:
        return float("nan")
    proba = model.predict_proba(X)
    if len(model.classes_) == 2:
        return float(roc_auc_score(y_true, proba[:, 1]))
    cols = [list(model.classes_).index(c) for c in classes]
    return float(roc_auc_score(y_true, proba[:, cols] / proba[:, cols].sum(axis=1, keepdims=True), multi_class="ovr", average="macro", labels=classes))


def _resolve_estimator(estimator, task: str):
    """EN: v1.2 — `estimator` may be None (default per task), a fitted-able object (used for every column) or a factory
        `f(task) -> estimator` (one per column task; what `run` passes so a class target can meet a continuous control)."""
    if estimator is None:
        return default_estimator(task)
    if callable(estimator) and not hasattr(estimator, "fit"):
        return estimator(task)
    return estimator


EPV_MIN = 10.0        # EN: Peduzzi et al. 1996 — below 10 events per variable logistic coefficients are biased and unstable
DISTINCT_FRACTION = 0.632   # EN: share of distinct persons in a bootstrap training draw (Efron 1983)


def events_per_variable(y: np.ndarray, n_predictors: int) -> tuple[int, float]:
    """EN: (events = size of the smaller class, EPV in a bootstrap training draw = 0.632·events / predictors). Peduzzi 1996 rule
        applied to what the audit actually fits; reported, never a barrier (decision of 2026-09-16)."""
    _, counts = np.unique(y[np.isfinite(y)], return_counts=True)
    ev = int(counts.min()) if len(counts) else 0
    return ev, float(DISTINCT_FRACTION * ev / max(1, n_predictors))


def metric_name(task: str) -> str:
    """EN: the name written in the tables: 'R2' for regression, 'D_Tjur' for classification."""
    return "R2" if task == "regression" else "D_Tjur"


def cv_score(X: np.ndarray, y: np.ndarray, task: str, estimator, cfg: AuditConfig, groups: np.ndarray | None = None, metric: str = "default") -> float:
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
        scores.append(_auroc(y[b], m, X[b]) if metric == "auroc" else _score(task, y[b], m, X[b]))
    return float(np.nanmean(scores))


def oob_scores(configs: dict[str, np.ndarray], Y: np.ndarray, task: str | Sequence[str], estimator, cfg: AuditConfig,
               progress: Callable[[int, int], None] | None = None, plan: dict[str, list[int]] | None = None) -> tuple[dict[str, np.ndarray], int, int]:
    """
    EN: paired OOB bootstrap. `configs` maps a name to a design matrix (same rows); `Y` is (n, k) targets. Returns
        ({name: (B_eff, k) scores}, B_eff, B_dropped). All configs and targets use the same resamples. `plan` (optional)
        restricts which outcome columns are fitted for each config (unfitted cells stay NaN); default: every config on
        every outcome.
    ES/PT: bootstrap OOB pareado; todas as configurações e alvos usam as mesmas reamostras; `plan` restringe os ajustes.
    """
    n = Y.shape[0]
    tr, oob = resamples(n, cfg.seed_bootstrap, cfg.B, cfg.min_oob, cfg.max_attempts_factor)
    if not tr:
        raise AuditError(f"bootstrap impossible: no resample of n={n} rows leaves >= min_oob={cfg.min_oob} out-of-bag "
                         f"(expected OOB ≈ {0.368 * n:.0f}); lower min_oob or provide more rows")
    # EN: v1.2 — task and estimator may differ per column of Y (a class target paired with a continuous control): a list per column.
    k = Y.shape[1]
    tasks = list(task) if not isinstance(task, str) else [task] * k
    ests = list(estimator) if isinstance(estimator, (list, tuple)) else [estimator] * k
    pipes = [make_pipeline(e, cfg.impute) for e in ests]
    store = {k2: np.full((len(tr), Y.shape[1]), np.nan) for k2 in configs}
    dropped = 0
    for b, (ii, oo) in enumerate(zip(tr, oob)):
        for k, X in configs.items():
            for t in (plan.get(k, range(Y.shape[1])) if plan else range(Y.shape[1])):
                if tasks[t] == "classification" and len(np.unique(Y[oo, t])) < 2:
                    continue
                m = clone(pipes[t]).fit(X[ii], Y[ii, t])
                store[k][b, t] = _score(tasks[t], Y[oo, t], m, X[oo])
        if progress and (b + 1) % max(1, len(tr) // 20) == 0:
            progress(b + 1, len(tr))
    if "classification" in tasks:
        # EN: a resample is dropped when any PLANNED cell is NaN (single-class OOB); unplanned cells are ignored.
        planned = np.stack([np.isnan(store[k][:, list(plan.get(k, range(Y.shape[1])) if plan else range(Y.shape[1]))]).any(axis=1) for k in configs], axis=0)
        keep = ~planned.any(axis=0)
        dropped = int((~keep).sum())
        store = {k: v[keep] for k, v in store.items()}
    b_eff = len(tr) - dropped
    min_b = cfg.min_B_eff if cfg.min_B_eff is not None else min(cfg.B, max(20, int(0.10 * cfg.B)))
    if b_eff < min_b:
        # EN: found on a 33-row audit partition (2026-09-15): ONE valid resample gave zero-width intervals and spurious verdicts.
        raise AuditError(f"bootstrap unreliable: only {b_eff} of {cfg.B} resamples kept >= min_oob={cfg.min_oob} rows out-of-bag (n={n}, "
                         f"expected OOB ≈ {0.368 * n:.0f}); at least {min_b} valid resamples are required — provide more rows")
    return store, b_eff, dropped


# ----------------------------------------------------------------------------------------------
def contrast(d: np.ndarray, cfg: AuditConfig) -> dict:
    """
    EN: paired difference summary: mean, percentile CI, P(d>0). Descriptive (§3.2), not a p-value.
    ES/PT: resumo da diferença pareada: média, IC por percentis, P(d>0). Descritivo, não é valor-p.
    """
    d = d[np.isfinite(d)]
    if len(d) == 0:
        return dict(mean=float("nan"), lo=float("nan"), hi=float("nan"), p=float("nan"), n=0)
    a = (1 - cfg.ci) / 2 * 100
    lo, hi = np.percentile(d, [a, 100 - a])
    return dict(mean=float(d.mean()), lo=float(lo), hi=float(hi), p=float((d > 0).mean()), n=int(len(d)))


def verdict(c: dict, cfg: AuditConfig) -> str:
    """EN: SPECIFIC / MEASURES_CONTROL / INCONCLUSIVE per §5 rules. ES/PT: veredito conforme as regras fixas."""
    if c.get("n", 1) == 0 or not np.isfinite(c["mean"]):
        return "INCONCLUSIVE"
    if c["mean"] > 0 and c["lo"] > 0 and c["p"] >= cfg.p_specific:
        return "SPECIFIC"
    if c["mean"] < 0 and c["hi"] < 0 and c["p"] <= cfg.p_control:
        return "MEASURES_CONTROL"
    return "INCONCLUSIVE"


def _positive(c: dict, cfg: AuditConfig) -> bool:
    """EN: an increment counts as present when its mean exceeds the margin, its CI excludes 0 and P(d>0) ≥ p_specific."""
    return bool(c.get("n", 1) > 0 and np.isfinite(c["mean"]) and c["mean"] > cfg.specificity_margin and c["lo"] > 0 and c["p"] >= cfg.p_specific)


def verdict_conditional(s1: dict, s2: dict, cfg: AuditConfig) -> str:
    """
    EN: §3.2 (v0.5) conditional negative control. s1 = score(target | control + index) − score(target | control):
        signal about the target that the control does not carry. s2 = score(control | target + index) −
        score(control | target): signal about the control that the target does not explain.
        SPECIFIC = s1 present, s2 absent · TRACKS_CONTROL = s2 present, s1 absent · BOTH = both present (the index
        carries information shared by neither, e.g. body size measured better than either) · NEITHER = none.
    """
    a, b = _positive(s1, cfg), _positive(s2, cfg)
    return "SPECIFIC" if a and not b else "TRACKS_CONTROL" if b and not a else "BOTH" if a and b else "NEITHER"


def verdict_sensitivity(rows, margins=(0.02, 0.03, 0.05), p_levels=(0.90, 0.95, 0.99), default_margin: float = 0.03, default_p: float = 0.95) -> list[dict]:
    """
    EN: §3.2 (v0.5.1) threshold sensitivity — re-apply the conditional rule to the stored S1/S2 summaries under a grid of
        margins and P levels. Pure reclassification (no refit): the CI is fixed (95 %), only the margin and the P
        threshold vary. One row per (audit row, margin, p). `changed` = differs from the verdict under the contract defaults.
    ES/PT: sensibilidade aos limiares — reclassifica S1/S2 gravados sob uma grade de margens e níveis de P; sem reajuste.
    """
    out = []
    for r in rows:
        d = r if isinstance(r, dict) else asdict(r)
        if not np.isfinite(d.get("s1_mean", float("nan"))):
            continue
        s1 = dict(mean=d["s1_mean"], lo=d["s1_lo"], hi=d["s1_hi"], p=d["p_s1"], n=1)
        s2 = dict(mean=d["s2_mean"], lo=d["s2_lo"], hi=d["s2_hi"], p=d["p_s2"], n=1)
        lvl = d.get("ci_level", float("nan"))
        for mg in margins:
            for pl in p_levels:
                v = verdict_conditional(s1, s2, AuditConfig(specificity_margin=mg, p_specific=pl))
                out.append(dict(method_id=d["method_id"], stratum=d["stratum"], target=d["target"], control=d["control"], margin=mg, p_specific=pl, ci_level=lvl,
                                verdict=v, verdict_default=d["verdict"], changed=(v != d["verdict"])))
        # EN: v1.1 — the family-level interval (1 − 0.05/k, k methods audited together): declared margin and P, wider interval
        if d.get("verdict_family") and np.isfinite(d.get("ci_family", float("nan"))):
            v = d["verdict_family"]
            out.append(dict(method_id=d["method_id"], stratum=d["stratum"], target=d["target"], control=d["control"], margin=default_margin, p_specific=default_p, ci_level=d["ci_family"],
                            verdict=v, verdict_default=d["verdict"], changed=(v != d["verdict"])))
    return out


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
    verdict: str                          # EN: v0.5 conditional verdict (SPECIFIC / TRACKS_CONTROL / BOTH / NEITHER)
    verdict_marginal: str = "INCONCLUSIVE"   # EN: pre-v0.5 rule on disc = score(target|idx) − score(control|idx); descriptive
    score_oob_control_to_target: float = float("nan")      # EN: score(target | control)
    score_oob_idx_control_to_target: float = float("nan")  # EN: score(target | control + index)
    score_oob_target_to_control: float = float("nan")      # EN: score(control | target)
    score_oob_idx_target_to_control: float = float("nan")  # EN: score(control | target + index)
    control_task: str = ""                                 # EN: v1.2 — task of the control column (may differ from the target's)
    metric_control: str = ""                               # EN: 'R2' or 'D_Tjur' for the S2 side
    auroc_cv_target_full: float = float("nan")             # EN: descriptive AUROC of target | control + index (classification targets)
    auroc_cv_control_full: float = float("nan")            # EN: descriptive AUROC of control | target + index (classification controls)
    events_min_class: int = 0                              # EN: v1.2 — smaller class of the classification column(s) audited
    epv_train: float = float("nan")                        # EN: 0.632·events / 2 predictors (index + control) in a bootstrap draw
    epv_low: bool = False                                  # EN: below 10 (Peduzzi 1996): read the verdict as exploratory
    s1_mean: float = float("nan")
    s1_lo: float = float("nan")
    s1_hi: float = float("nan")
    p_s1: float = float("nan")
    s2_mean: float = float("nan")
    s2_lo: float = float("nan")
    s2_hi: float = float("nan")
    p_s2: float = float("nan")
    ci_level: float = float("nan")         # EN: level of s1_lo/s1_hi/s2_lo/s2_hi (the declared CI)
    k_methods: int = 1                     # EN: methods audited together in this stratum (v1.1)
    ci_family: float = float("nan")        # EN: 1 − 0.05/k — the same resamples read at the family level (v1.1)
    s1_lo_fam: float = float("nan")
    s1_hi_fam: float = float("nan")
    s2_lo_fam: float = float("nan")
    s2_hi_fam: float = float("nan")
    verdict_family: str = ""               # EN: the same rule with the family-level interval; reported next to `verdict`, never selected


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
    if ok.sum() < cfg.min_n:
        raise AuditError(f"only {int(ok.sum())} complete rows (index, targets, controls) < min_n={cfg.min_n}")   # EN: never skipped silently (v1.0)
    X = x[ok].reshape(-1, 1); Y = Yall[ok]; g = groups[ok] if groups is not None else None
    # EN: v1.2 — task per column (a class target may be paired with a continuous control); estimator per column unless one
    #     was given explicitly (then it is used for every column, the caller's responsibility).
    tasks = [cfg.task if cfg.task != "auto" else infer_task(Y[:, i]) for i in range(len(names))]
    ests = [_resolve_estimator(estimator, tk) for tk in tasks]
    cv = {k: cv_score(X, Y[:, i], tasks[i], ests[i], cfg, g) for i, k in enumerate(names)}
    # EN: v0.5 — besides the index alone, fit the control as predictor of the target (and with the index), and the target as
    #     predictor of the control (and with the index), on the SAME resamples. `plan` avoids degenerate fits (y from y).
    configs: dict[str, np.ndarray] = {"idx": X}; plan: dict[str, list[int]] = {"idx": list(range(len(names)))}
    for t, c in pairing.items():
        if t == c:
            continue
        it, ic = names.index(t), names.index(c)
        configs[f"ctrl:{c}"] = Y[:, [ic]]; plan.setdefault(f"ctrl:{c}", []).append(it)
        configs[f"idx+ctrl:{c}"] = np.column_stack([X, Y[:, ic]]); plan.setdefault(f"idx+ctrl:{c}", []).append(it)
        configs[f"tgt:{t}"] = Y[:, [it]]; plan.setdefault(f"tgt:{t}", []).append(ic)
        configs[f"idx+tgt:{t}"] = np.column_stack([X, Y[:, it]]); plan.setdefault(f"idx+tgt:{t}", []).append(ic)
    plan = {k: sorted(set(v)) for k, v in plan.items()}
    st, b_eff, b_drop = oob_scores(configs, Y, tasks, ests, cfg, progress, plan=plan)
    S = st["idx"]
    for t, c in pairing.items():
        it, ic = names.index(t), names.index(c)
        d = S[:, it] - S[:, ic]
        cs = contrast(d, cfg)
        row = AuditRow(method_id, stratum, t, c, tasks[it], metric_name(tasks[it]), type(ests[it]).__name__,
                       int(ok.sum()), cfg.B, b_eff, b_drop, cv[t], cv[c], float(np.nanmean(S[:, it])), float(np.nanmean(S[:, ic])),
                       cs["mean"], cs["lo"], cs["hi"], cs["p"], "INCONCLUSIVE", verdict_marginal=verdict(cs, cfg))
        if t != c:
            ct, ict = st[f"ctrl:{c}"][:, it], st[f"idx+ctrl:{c}"][:, it]
            tc, itc = st[f"tgt:{t}"][:, ic], st[f"idx+tgt:{t}"][:, ic]
            s1, s2 = contrast(ict - ct, cfg), contrast(itc - tc, cfg)
            row.score_oob_control_to_target, row.score_oob_idx_control_to_target = float(np.nanmean(ct)), float(np.nanmean(ict))
            row.score_oob_target_to_control, row.score_oob_idx_target_to_control = float(np.nanmean(tc)), float(np.nanmean(itc))
            row.s1_mean, row.s1_lo, row.s1_hi, row.p_s1 = s1["mean"], s1["lo"], s1["hi"], s1["p"]
            row.s2_mean, row.s2_lo, row.s2_hi, row.p_s2 = s2["mean"], s2["lo"], s2["hi"], s2["p"]
            row.verdict = verdict_conditional(s1, s2, cfg)
            row.ci_level, row.k_methods = cfg.ci, int(cfg.k_methods)
            row.control_task, row.metric_control = tasks[ic], metric_name(tasks[ic])
            cls_cols = [j for j in (it, ic) if tasks[j] == "classification"]
            if cls_cols:
                ev, epv = min((events_per_variable(Y[:, j], 2) for j in cls_cols), key=lambda z: z[1])
                row.events_min_class, row.epv_train, row.epv_low = ev, epv, bool(epv < EPV_MIN)
            if tasks[it] == "classification":
                row.auroc_cv_target_full = cv_score(configs[f"idx+ctrl:{c}"], Y[:, it], "classification", ests[it], cfg, g, metric="auroc")
            if tasks[ic] == "classification":
                row.auroc_cv_control_full = cv_score(configs[f"idx+tgt:{t}"], Y[:, ic], "classification", ests[ic], cfg, g, metric="auroc")
            if cfg.ci_family is not None:
                fam = replace(cfg, ci=cfg.ci_family)
                s1f, s2f = contrast(ict - ct, fam), contrast(itc - tc, fam)
                row.ci_family = cfg.ci_family
                row.s1_lo_fam, row.s1_hi_fam, row.s2_lo_fam, row.s2_hi_fam = s1f["lo"], s1f["hi"], s2f["lo"], s2f["hi"]
                row.verdict_family = verdict_conditional(s1f, s2f, cfg)
        rows.append(row)
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
    auroc_cv_with: float = float("nan")   # EN: v1.2 — descriptive AUROC of target | covariates + index (classification)
    events_min_class: int = 0
    epv_train: float = float("nan")      # EN: 0.632·events / (covariates + 1) predictors
    epv_low: bool = False


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
    if ok.sum() < cfg.min_n:
        raise AuditError(f"only {int(ok.sum())} complete rows (index, covariates, targets) < min_n={cfg.min_n}")
    FA = covariates[ok]; FB = np.column_stack([FA, x[ok]]); Y = Yall[ok]; g = groups[ok] if groups is not None else None
    tasks = [cfg.task if cfg.task != "auto" else infer_task(Y[:, i]) for i in range(len(names))]
    ests = [_resolve_estimator(estimator, tk) for tk in tasks]
    st, b_eff, _ = oob_scores({"A": FA, "B": FB}, Y, tasks, ests, cfg)
    out = []
    for i, t in enumerate(names):
        d = st["B"][:, i] - st["A"][:, i]
        cs = contrast(d, cfg)
        row = UtilityRow(method_id, stratum, t, tasks[i], metric_name(tasks[i]), "+".join(cov_names), int(ok.sum()), b_eff,
                         cv_score(FA, Y[:, i], tasks[i], ests[i], cfg, g), cv_score(FB, Y[:, i], tasks[i], ests[i], cfg, g),
                         cs["mean"], cs["lo"], cs["hi"], cs["p"], cfg.utility_margin, bool(cs["lo"] > cfg.utility_margin))
        if tasks[i] == "classification":
            row.auroc_cv_with = cv_score(FB, Y[:, i], "classification", ests[i], cfg, g, metric="auroc")
            row.events_min_class, row.epv_train = events_per_variable(Y[:, i], FB.shape[1]); row.epv_low = bool(row.epv_train < EPV_MIN)
        out.append(row)
    return out


def combination_gain(host_id: str, added_id: str, stratum: str, xh: np.ndarray, xa: np.ndarray, targets: dict[str, np.ndarray],
                     cfg: AuditConfig, estimator, groups: np.ndarray | None = None) -> list[dict]:
    """
    EN: gain of adding index `added` to index `host`: A = [host], B = [host, added]; same resamples; complete-case on both.
    ES/PT: ganho de acrescentar um índice a outro; mesmas reamostras; caso completo nos dois.
    """
    names = list(targets); Yall = np.column_stack([targets[k] for k in names])
    ok = np.isfinite(xh) & np.isfinite(xa) & np.isfinite(Yall).all(axis=1)
    if ok.sum() < cfg.min_n:
        return []
    A = xh[ok].reshape(-1, 1); Bm = np.column_stack([xh[ok], xa[ok]]); Y = Yall[ok]
    tasks = [cfg.task if cfg.task != "auto" else infer_task(Y[:, i]) for i in range(Y.shape[1])]
    ests = [_resolve_estimator(estimator, tk) for tk in tasks]
    st, b_eff, _ = oob_scores({"A": A, "B": Bm}, Y, tasks, ests, cfg)
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

"""
EN: Orchestrator: config → data → catalog (+designed index) → per stratum: values, Σ, vectors, pairs, redundancy →
    Σ transfer → audit (specificity), utility, combinations → screening → tables, manifest, summary (, figures).
    Progress with ETA from the first method. Row-level data never leave this module.
ES: Orquestador: de la configuración a las salidas. Progreso con ETA desde el primer método.
PT: Orquestrador: da configuração às saídas. Progresso com ETA desde o primeiro método.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits   # EN: ships with scikit-learn

from . import algebra as A
from .audit import verdict_sensitivity, AuditConfig, AuditError, audit_method, combination_gain, default_estimator, utility_method
from .catalog import BUILTIN_PATH, Catalog, build_catalog
from .config import resolve
from .i18n import set_language, t as _t
from .design import design_index, holdout_split, by_stratum_split
from .io import Dataset, read_table
from .report import sha256_file, sha256_obj, write_manifest, write_summary, write_table
from .screen import screening_table


def _estimator(spec: dict, task: str):
    """EN: 'ridge' | 'logistic' | 'hgb' | 'xgboost' | 'module:Class' with params. ES/PT: fábrica de estimadores."""
    name, params = spec.get("estimator"), dict(spec.get("params") or {})
    if name in (None, "ridge", "logistic"):
        est = default_estimator(task)
        if name == "ridge" and task == "regression":
            est.set_params(**params)
        elif name == "logistic" and task == "classification":
            est.set_params(**params)
        return est
    if name == "hgb":
        from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
        cls = HistGradientBoostingRegressor if task == "regression" else HistGradientBoostingClassifier
        return cls(random_state=0, **params)
    if name == "xgboost":
        import xgboost as xgb  # optional dependency
        cls = xgb.XGBRegressor if task == "regression" else xgb.XGBClassifier
        return cls(random_state=0, n_jobs=1, **params)
    mod, _, cls = name.partition(":")
    import importlib
    return getattr(importlib.import_module(mod), cls)(**params)


def _load_catalog(cfg: dict) -> Catalog:
    path = None if cfg["catalog"]["path"] in (None, "builtin") else cfg["catalog"]["path"]
    raw = json.loads(Path(path or BUILTIN_PATH).read_text(encoding="utf-8"))
    raw["entries"] = list(raw["entries"]) + list(cfg["catalog"].get("user_entries") or [])
    cat = build_catalog(raw, source_path=str(path or BUILTIN_PATH))
    inc, exc = cfg["catalog"]["include"], set(cfg["catalog"]["exclude"] or [])
    keep = [e for e in cat.entries if (inc == "all" or (inc == "curated" and e.curated)
                                       or (isinstance(inc, list) and (e.id in inc or ("curated" in inc and e.curated) or ("all" in inc)))) and e.id not in exc]   # EN: [curated, my_id] = curated ∪ ids (v0.9)
    return Catalog(cat.version, cat.conventions, keep, cat.source_path)


def _values(cat: Catalog, ds: Dataset, frame: pd.DataFrame, stats: dict | None = None) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    """EN: index values for every evaluable method on `frame` (one stratum). `stats`, when given, receives
    {method_id: {"mean(PhA)": value, ...}} for methods whose formula uses sample statistics (v0.9)."""
    env = {c: frame[c].to_numpy(float) for c in ds.variables + ds.derived if c in frame}
    for g in ds.groups:
        env[g] = pd.to_numeric(frame[g], errors="coerce").to_numpy(float)
    vals, skipped = {}, {}
    for e in cat.entries:
        if e.status == "excluded":
            skipped[e.id] = f"excluded: {e.exclusion_reason}"; continue
        if e.form == "closed":
            skipped[e.id] = "closed method (no published coefficients)"; continue
        missing = sorted(set(e.inputs) - set(env))
        if missing:
            skipped[e.id] = f"missing inputs {missing}"; continue
        rec: list = []
        v = e.evaluate(env, frame[e.branch_group].to_numpy() if e.branch_group else None, record=rec)
        vals[e.id] = np.broadcast_to(np.asarray(v, float), (len(frame),)).copy()   # EN: a scalar formula (constant) becomes a column, never a 0-d array
        if rec and stats is not None:
            stats[e.id] = {k: float(x) for k, x in rec}
    return vals, skipped


def _audit_one(args):
    """EN: worker for one method (picklable). ES/PT: trabalhador por método."""
    mid, stratum, x, targets, controls, pairing, acfg, est_spec, task, groups, cov, cov_names, utility_targets = args
    est = _estimator(est_spec, task if task != "auto" else ("classification" if len(np.unique(next(iter(targets.values()))[np.isfinite(next(iter(targets.values())))])) <= 10 else "regression"))
    try:
        rows = [asdict(r) for r in audit_method(mid, stratum, x, targets, controls, pairing, acfg, est, groups)]
    except AuditError as e:
        return [], [], f"{stratum}/{mid}: audit skipped — {e}"
    try:
        urows = [asdict(u) for u in utility_method(mid, stratum, x, cov, cov_names, utility_targets, acfg, est, groups)] if cov is not None else []
    except AuditError as e:
        return rows, [], f"{stratum}/{mid}: utility skipped — {e}"
    return rows, urows, None


def run(config: dict | str | Path, *, printer: Callable[[str], None] = print, preflight: bool = True) -> dict:
    """
    EN: execute a full run; returns {"tables": {...}, "manifest": {...}, "out_dir": Path}.
    ES/PT: executa uma rodada completa.
    """
    cfg = resolve(config)
    set_language(cfg["language"])   # EN: API and CLI alike (v0.7)
    # EN: BLAS/OpenMP threads are limited HERE, after import, so that run() called from Python (tests, notebooks, other
    #     packages) behaves exactly like the CLI: no oversubscription on small matrices. Env vars are also set for workers.
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(k, str(cfg["threads"]))
    # EN: the same pre-flight as `bioms-zaku check` runs here too (contract §3.2, 14/09): blocking problems stop the run with the
    #     check messages instead of producing a report with every audit skipped (found on a 60-row sample in the user simulation).
    if preflight:                                      # EN: `start` runs the full check itself and passes preflight=False (no double "check: OK")
        from .check import check as _check
        _check(cfg, printer=lambda s: printer(s) if s.startswith(("  ✗", "  ⚠", "check:")) else None)
    with threadpool_limits(limits=int(cfg["threads"])):
        return _run(cfg, printer=printer)


def render(out_dir: str | Path, lang: str | None = None, *, printer: Callable[[str], None] = print) -> Path:
    """
    EN: re-write summary.md, figures/ and report.html of a FINISHED run in another language, from the saved tables and
        manifest — nothing is recomputed (contract §4.6: the report reads, never calculates). Tables and manifest are untouched.
    ES/PT/IT: regrava resumo, figuras e relatório de uma execução concluída em outro idioma, sem recalcular nada.
    """
    out_dir = Path(out_dir)
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    cfg = manifest["config_resolved"]
    if lang:
        cfg["language"] = lang; cfg.setdefault("figures", {})["language"] = lang
    set_language(cfg.get("language", "en"))
    str_cols = {"stratum": str, "sigma_from": str, "observed_in": str, "a_id": str, "b_id": str, "method_id": str}
    def _read(p: Path) -> pd.DataFrame:
        try:
            return pd.read_csv(p, dtype=str_cols)
        except pd.errors.EmptyDataError:                 # EN: an empty table is written as an empty file
            return pd.DataFrame()
    tables = {p.stem: _read(p) for p in sorted(out_dir.glob("*.csv"))}
    for name, df in tables.items():                       # EN: booleans come back as bools; empty tables stay empty
        for c in df.columns:
            if df[c].dtype == object and set(df[c].dropna().unique()) <= {"True", "False"}:
                df[c] = df[c].map({"True": True, "False": False})
    write_summary(out_dir, cfg, tables, manifest)
    if cfg["output"].get("figures", True):
        from .plots import make_all
        make_all(out_dir, tables, cfg)
    from .html import write_report
    rp = write_report(out_dir, cfg, tables, manifest)
    printer(_t("r.report", path=rp.resolve()))
    return rp


def _show_inline(report: Path) -> None:
    """EN: inside a Jupyter/Colab notebook, display the report inline (iframe); elsewhere do nothing. Never raises."""
    try:
        ip = get_ipython()  # type: ignore[name-defined]  # noqa: F821
    except NameError:
        return
    if ip is None or "IPKernelApp" not in getattr(ip, "config", {}):
        return
    try:
        from IPython.display import HTML, IFrame, display
        # EN: Jupyter serves files only below the folder it was started in. Inside it → IFrame with a RELATIVE path (works in
        #     JupyterLab and Colab); outside it → the whole report embedded in the frame (srcdoc), which works anywhere.
        try:
            rel = report.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            rel = None
        style = "border:1px solid #e6e5e1;border-radius:6px"
        if rel is not None:
            display(IFrame(rel, width="100%", height=720))
        else:
            import html as _html
            display(HTML(f"<iframe srcdoc=\"{_html.escape(report.read_text(encoding='utf-8'), quote=True)}\" width='100%' height='720' style='{style}'></iframe>"))
    except Exception:
        return


def scaled_inputs(vals: dict, targets: dict, controls: dict, cov, target_types: dict, scale: str, stratum: str, warnings: list) -> dict:
    """
    EN: the inputs of the audit on the requested scale (v1.1). "log": natural logarithm of the index values (positive by
        construction; non-positive → NaN, excluded from that audit), of every REGRESSION target/control and of the covariates.
        A regression target/control or a covariate with a non-positive value cannot be logged: the whole stratum falls back
        to "raw" with a warning (recorded as the scale used). Classification labels are never transformed.
    ES/PT: entradas da auditoria na escala pedida; sem valores positivos, volta à escala bruta com aviso.
    """
    if scale == "raw":
        return {"scale": "raw", "vals": vals, "targets": targets, "controls": controls, "cov": cov}
    def _bad(arr):
        a = np.asarray(arr, float); return bool((a[np.isfinite(a)] <= 0).any())
    cont = {k: v for k, v in {**targets, **controls}.items() if target_types.get(k) != "classification"}
    culprit = next((k for k, v in cont.items() if _bad(v)), None)
    if culprit is None and cov is not None and _bad(cov):
        culprit = "covariates"
    if culprit is not None:
        warnings.append(f"{stratum}: audit on the raw scale — {culprit} has non-positive values, so the logarithmic scale is not possible here")
        return {"scale": "raw", "vals": vals, "targets": targets, "controls": controls, "cov": cov}
    def _log(a):
        a = np.asarray(a, float); out = np.full(a.shape, np.nan); ok = np.isfinite(a) & (a > 0); out[ok] = np.log(a[ok]); return out
    return {"scale": "log", "vals": {k: _log(v) for k, v in vals.items()},
            "targets": {k: (_log(v) if k in cont else v) for k, v in targets.items()}, "controls": {k: (_log(v) if k in cont else v) for k, v in controls.items()},
            "cov": None if cov is None else _log(cov)}


def low_resample_warnings(audit_rows: list, stratum: str) -> list[str]:
    """EN: one warning per stratum when any method kept fewer than half of the requested bootstrap resamples (v1.0)."""
    low = sorted({(r["method_id"], int(r["B_eff"]), int(r["B"])) for r in audit_rows if r["stratum"] == stratum and r["B_eff"] < 0.5 * r["B"]})
    if not low:
        return []
    return [f"{stratum}: only {min(x[1] for x in low)}–{max(x[1] for x in low)} of {low[0][2]} bootstrap resamples kept >= min_oob rows out-of-bag "
            f"for {len(low)} method(s); intervals rest on fewer resamples than requested"]


def design_all(cfg: dict, ds, frame: pd.DataFrame, warnings: list, manifest: dict) -> tuple[dict, pd.DataFrame]:
    """
    EN: the design stage (contract §2.7, v0.9): ONE partition for every designed index, vectors fitted per stratum on the design
        rows, everything recorded in `manifest["design"]`. Returns (designed{stratum -> {id -> DesignedIndex}}, audit frame).
        Used by `run` and by the guided flow (`start`), so suggestions and the final run see exactly the same vectors.
    ES/PT: etapa de desenho compartilhada por `run` e `start`.
    """
    designed: dict[str, dict[str, object]] = {}      # EN: stratum key -> {index id -> DesignedIndex}
    if cfg["design"]:
        if (cfg.get("declarations") or {}).get("targets_independent_of_variables") is not True:
            raise ValueError("design requires declarations.targets_independent_of_variables: true (contract v0.4.3: the target must not be computed from any mapped variable)")
        specs = [cfg["design"]] if isinstance(cfg["design"], dict) else list(cfg["design"])
        for dg in specs:
            if dg.get("orthogonal_to") is not None and dg["orthogonal_to"] not in frame:
                raise ValueError(f"design.orthogonal_to {dg['orthogonal_to']!r} is not a mapped column")
        # EN: ONE partition for every designed index (same rows held out), made over rows where every design target and control is
        #     finite, so all designed indices are audited on the same never-seen rows (v0.9). Split parameters come from the first spec.
        need = sorted({dg["target"] for dg in specs} | {dg["orthogonal_to"] for dg in specs if dg.get("orthogonal_to")})
        has_t = np.ones(len(frame), dtype=bool)
        for c in need:
            has_t &= np.isfinite(pd.to_numeric(frame[c], errors="coerce").to_numpy(float))
        sub = frame[has_t].reset_index(drop=True)
        dg0 = specs[0]; tgt0 = dg0["target"]
        if dg0.get("split", "holdout") == "holdout":
            strat = sub[ds.strata] if ds.strata else None
            if ds.target_types.get(tgt0) == "classification":
                strat = (strat.astype(str) + "|" if strat is not None else "") + sub[tgt0].astype(str)
            split = holdout_split(sub, fraction=float(dg0.get("fraction", 0.70)), seed=int(dg0.get("seed", 42)), stratify=strat, id_col=ds.id)
        else:
            split = by_stratum_split(sub, ds.strata, dg0["design_value"], dg0["audit_value"])
        dvars = ds.variables + list(cfg["algebra"]["extra_log_variables"])
        groups_d = sorted(sub[ds.strata].dropna().unique()) if ds.strata else [None]
        man_d = {"mode": split.mode, "fraction": split.fraction, "seed": split.seed, "stratify_on": split.stratify_on, "design_hash": split.design_hash,
                 "n_with_target": int(has_t.sum()), "n_design": split.n_design, "n_audit": split.n_audit, "variables": list(dvars), "columns_required": need, "indices": {}}
        from .design import Split
        for dg in specs:
            tgt = dg["target"]; orth = dg.get("orthogonal_to")
            did = dg.get("id") or (f"designed_{tgt}_not_{orth}" if orth else f"designed_{tgt}")
            if did in man_d["indices"]:
                raise ValueError(f"design: duplicate index id {did!r}")
            entry = {"target": tgt, "orthogonal_to": orth, "per_stratum": {}}
            for g in groups_d:
                mask = np.ones(len(sub), dtype=bool) if g is None else (sub[ds.strata] == g).to_numpy()
                sp = Split(split.design & mask, split.audit & mask, split.mode, split.fraction, split.seed, split.stratify_on, split.design_hash)
                di = design_index(sub, tgt, dvars, sp, index_id=did, orthogonal_to=orth, B=int(cfg["algebra"]["transfer_B"]), seed=int(cfg["seeds"]["bootstrap"]))
                key = "all" if g is None else str(g)
                designed.setdefault(key, {})[did] = di
                lab = {str(k): str(v) for k, v in (cfg.get("strata_labels") or {}).items()}.get(key, key)   # EN: manifest keyed by the stratum LABEL (as the tables)
                entry["per_stratum"][lab] = {"n_design": sp.n_design, "n_audit": sp.n_audit, "vector_design": di.vector_design.tolist(), "r2_design": di.r2_design,
                                             "vector_refit_full": None if di.vector_refit_full is None else di.vector_refit_full.tolist(), "r2_refit_full": di.r2_refit_full,
                                             "control_vector": None if di.control_vector is None else di.control_vector.tolist(),
                                             "cos_control_design": di.cos_control_design, "r2_unconstrained": di.r2_unconstrained,
                                             "vector_lo": None if di.vector_lo is None else [float(x) for x in di.vector_lo], "vector_hi": None if di.vector_hi is None else [float(x) for x in di.vector_hi], "B_vector": di.B_vector}
                if sp.n_audit < 100 and did == next(iter(man_d["indices"]), did):
                    warnings.append(f"design/{lab}: audit partition has n={sp.n_audit} < 100; intervals will be wide")
            man_d["indices"][did] = entry
        manifest["design"] = man_d
        frame = sub[split.audit].reset_index(drop=True)      # EN: everything below runs on the audit partition only
    return designed, frame


def _run(cfg: dict, *, printer: Callable[[str], None]) -> dict:
    t0 = time.time()
    out_dir = Path(cfg["output"]["dir"]) / cfg["run_name"]
    overwrite_note = _t("r.overwrite", dir=out_dir) if (out_dir / "manifest.json").exists() else None   # EN: never replace a previous run silently
    if overwrite_note:
        printer(overwrite_note)
    out_dir.mkdir(parents=True, exist_ok=True)
    d = cfg["data"]
    # EN: single source of truth for strata: top-level `strata` (contract §3); copied into the column mapping.
    cols = d["columns"]
    if cfg["strata"] is not None:
        if cols.get("strata") not in (None, cfg["strata"]):
            raise ValueError(f"strata declared twice and differently: top-level {cfg['strata']!r} vs columns.strata {cols.get('strata')!r}")
        cols = {**cols, "strata": cfg["strata"]}
        d = {**d, "columns": cols}
    ds = read_table(d["path"], d["columns"], sep=d["sep"], decimal=d["decimal"], encoding=d["encoding"],
                    drop_nonpositive=d["drop_nonpositive"], min_n=d["min_n"], min_per_class=d["min_per_class"])
    cat = _load_catalog(cfg)
    warnings = list(ds.info["warnings"])
    notes = [overwrite_note.lstrip("⚠ ")] if overwrite_note else []   # EN: operational, not scientific: manifest + rigour section only
    frame = ds.frame
    manifest = {"run_name": cfg["run_name"], "study": dict(cfg.get("study") or {}), "config_resolved": cfg, "config_sha256": sha256_obj(cfg), "catalog_version": cat.version,
                "catalog_sha256": sha256_file(cat.source_path) if cat.source_path and Path(cat.source_path).exists() else None,
                "input_path": ds.info.get("input_path"), "input_sha256": sha256_file(d["path"]) if isinstance(d["path"], (str, Path)) else None,
                "input_rows": ds.info["rows_in"], "rows_out": ds.info["rows_out"], "sep_used": ds.info.get("sep_used"),
                "decimal_used": ds.info.get("decimal_used"), "encoding_used": ds.info.get("encoding_used"),
                "rows_dropped": ds.info["rows_dropped"], "seeds_used": cfg["seeds"], "preset": cfg["preset"], "threads": cfg["threads"],
                "n_jobs": cfg["n_jobs"], "resampling_scheme": "deterministic per (n rows, seed, B, min_oob): default_rng(seed).integers(0,n,n); OOB>=min_oob",
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}

    # ---- design (optional): designed index audited only on the audit partition (CONTRATOS §2.7)
    #      EN: the split is made over rows with a finite target; the vector is fitted WITHIN each stratum (so a stratum
    #          difference in the target is never absorbed as signal); one vector per stratum, all recorded in the manifest.
    designed, frame = design_all(cfg, ds, frame, warnings, manifest)   # EN: shared with `start` (suggestions = the same vectors)

    # ---- per stratum
    lab_map = {str(k): str(v) for k, v in (cfg.get("strata_labels") or {}).items()}
    strata = [(lab_map.get(str(s), str(s)), frame[frame[ds.strata] == s].reset_index(drop=True)) for s in sorted(frame[ds.strata].dropna().unique())] if ds.strata else [("all", frame)]
    T = {k: [] for k in ("algebra", "sigma", "pairs", "redundancy", "audit", "utility", "combinations", "sensitivity", "sensitivity_scale", "implicit_vectors", "geometry")}
    vecs_by, sig_by, pairs_by, vals_by, design_by, skipped_all = {}, {}, {}, {}, {}, {}
    # EN: target-kind orientation (§2.1 / §3.2): a method whose author-declared kind equals the kind of the CONTROL and
    #     differs from the kind of the TARGET is expected to "track the control" by design; say so before the verdicts.
    # PT: orientação por tipo de alvo: índice de gordura auditado contra alvo de massa magra "acompanha o controle" por desenho.
    kinds = {k: v for k, v in ((cfg.get("declarations") or {}).get("target_kinds") or {}).items()}
    for t, c in ds.pairing.items():
        kt, kc = kinds.get(t), kinds.get(c)
        if kt and kc and kt != kc:
            for e in cat.entries:
                if e.status == "active" and e.target_kind == kc and e.target_kind != kt and not any(w.startswith(f"{e.id}: declared as") for w in warnings):
                    warnings.append(f"{e.id}: declared as a {kc} index by its authors; audited here against a {kt} target with a {kc} control, "
                                    f"so 'tracks control' is its design, not a defect — swap target and control to audit it on its own terms")
    acfg = AuditConfig(task=cfg["audit"]["task"], cv_folds=cfg["audit"]["cv"]["folds"], cv_repeats=cfg["audit"]["cv"]["repeats"],
                       B=cfg["audit"]["bootstrap"]["B"], min_oob=cfg["audit"]["bootstrap"]["min_oob"], max_attempts_factor=cfg["audit"]["bootstrap"]["max_attempts_factor"],
                       seed_cv=cfg["seeds"]["cv"], seed_bootstrap=cfg["seeds"]["bootstrap"], ci=cfg["audit"]["verdict"]["ci"],
                       p_specific=cfg["audit"]["verdict"]["p_specific"], p_control=cfg["audit"]["verdict"]["p_control"],
                       utility_margin=cfg["audit"]["utility_margin"], specificity_margin=cfg["audit"]["verdict"]["margin"], impute=d["impute"], min_n=d["min_n"])
    total = sum(1 for _ in strata) ; done_methods = 0
    for stratum, fr in strata:
        sstats: dict = {}
        vals, skipped = _values(cat, ds, fr, stats=sstats)
        if sstats:
            # EN: a formula with mean/median/sd is evaluated on THIS stratum's rows; the numbers used are recorded here and
            #     warned about, because such an index takes different values in every sample (v0.9).
            manifest.setdefault("sample_statistics", {})[stratum] = sstats
            for mid, used in sstats.items():
                warnings.append(f"{stratum}/{mid}: formula uses sample statistics computed on this stratum ({', '.join(f'{k} = {x:.4g}' for k, x in used.items())}); its values are not comparable across samples")
        raw_key = str(fr[ds.strata].iloc[0]) if ds.strata and len(fr) else "all"
        dis = list((designed.get(raw_key) or {}).values()) if designed else []
        for di in dis:
            vals[di.id] = di.values(fr)
        skipped_all[stratum] = skipped
        # EN: complete-case fraction warning per method
        for mid, v in vals.items():
            frac = 1 - np.isfinite(v).mean()
            if frac > d["max_missing_frac_warn"]:
                warnings.append(f"{stratum}/{mid}: {frac:.0%} of rows lack the index (complete-case)")
        design_vars = ds.variables + list(cfg["algebra"]["extra_log_variables"])
        S, n_sig = A.log_covariance(fr, design_vars)
        dids = {di.id for di in dis}
        vecs = A.compute_vectors(cat, {k: v for k, v in vals.items() if k not in dids}, fr, ds.variables, stratum,
                                 extra_log_variables=cfg["algebra"]["extra_log_variables"])
        for di in dis:
            vecs[di.id] = A.VectorFit(di.id, stratum, tuple(design_vars), di.vector_design, "designed",
                                      int(np.isfinite(vals[di.id]).sum()), 0, di.r2_design)
        conf = {e.id: e.confidence for e in cat.entries}
        oov = {mid: _out_of_validity(cat[mid], fr, ds) for mid in vecs if mid in cat.ids()}
        for mid, vf in vecs.items():
            row = dict(method_id=mid, label=(cat[mid].label if mid in cat.ids() else mid), year=(cat[mid].year if mid in cat.ids() else None),
                       kind=(cat[mid].kind if mid in cat.ids() else "designed"), form=(cat[mid].form if mid in cat.ids() else "monomial"),
                       stratum=stratum, n=vf.n, n_nonpositive_pred=vf.n_nonpositive_pred, fit_r2=vf.fit_r2,
                       poor_monomial=bool(vf.fit_r2 < cfg["algebra"]["min_fit_r2"]), vector_source=vf.source,
                       out_of_validity_frac=oov.get(mid, (0.0, ""))[0], out_of_validity_fields=oov.get(mid, (0.0, ""))[1],
                       provenance_confidence=conf.get(mid, "low"), curated=bool(cat[mid].curated) if mid in cat.ids() else False,
                       proposed=bool(cat[mid].proposed) if mid in cat.ids() else False,
                       uses_sample_stats=bool(cat[mid].uses_sample_stats) if mid in cat.ids() else False,
                       designed=mid not in cat.ids(),
                       target_kind=(cat[mid].target_kind if mid in cat.ids() else None))
            row.update({f"e_{v}": float(x) for v, x in zip(vf.variables, vf.vector)})
            T["algebra"].append(row)
        for i, vi in enumerate(design_vars):
            for j, vj in enumerate(design_vars):
                T["sigma"].append(dict(stratum=stratum, n=n_sig, var_i=vi, var_j=vj, cov_log=float(S[i, j])))
        pcat = Catalog(cat.version, cat.conventions, list(cat.entries) + [_designed_entry(di) for di in dis], cat.source_path)
        pairs = A.pairs_table(pcat, vecs, vals, S, stratum, min_pair_n=cfg["algebra"]["min_pair_n"], ci_level=cfg["algebra"]["pair_ci_level"],
                              B=cfg["algebra"]["transfer_B"], seed=cfg["seeds"]["bootstrap"])
        # EN: with a single evaluable method there are no pairs; the empty table still carries its columns (a one-method run must
        #     not crash downstream — found by a test on 14/09)
        red = (A.redundancy_table(pcat, pairs, stratum, threshold=cfg["algebra"]["redundancy_threshold"]) if not pairs.empty
               else pd.DataFrame(columns=["method_id", "stratum", "rho_sp_max", "predecessor_id", "predecessor_year", "redundant", "identity_of"]))
        T["pairs"].append(pairs); T["redundancy"].append(red)
        vecs_by[stratum], sig_by[stratum], pairs_by[stratum], vals_by[stratum] = vecs, S, pairs, {k: v for k, v in vals.items() if k in vecs}
        design_by[stratum] = np.log(fr.loc[:, list(design_vars)].to_numpy(dtype=float))   # EN: v0.5 Σ-transfer bootstrap recomputes Σ_t per resample
        # ---- geometry target↔control (v0.6, §3.3): continuous targets/controls only; flags annotate, never decide
        gcfg = cfg["geometry"]
        if gcfg["enabled"]:
            cont_t = {t: fr[t].to_numpy(float) for t in ds.targets if ds.target_types.get(t) != "classification"}
            cont_c = {c: fr[c].to_numpy(float) for c in ds.controls}
            imp_df, geo_df = A.geometry_tables(vecs, vals, fr, design_vars, cont_t, cont_c, ds.pairing, stratum,
                                               parallel_to_control=gcfg["parallel_to_control"], coupled_target_control=gcfg["coupled_target_control"],
                                               min_fit_r2=gcfg["min_fit_r2"])
            T["implicit_vectors"].append(imp_df); T["geometry"].append(geo_df)

        # ---- audit
        targets = {t: fr[t].to_numpy(float) for t in ds.targets}
        controls = {c: fr[c].to_numpy(float) for c in ds.controls}
        groups = fr[ds.id].to_numpy() if ds.id and fr[ds.id].duplicated().any() else None
        cov = fr[ds.covariates].to_numpy(float) if ds.covariates else None
        task = cfg["audit"]["task"]
        scale = cfg["audit"]["scale"]
        sc = scaled_inputs(vals, targets, controls, cov, ds.target_types, scale, stratum, warnings)
        from dataclasses import replace as _replace
        k_methods = len(vecs)
        acfg_s = _replace(acfg, ci_family=(1 - (1 - acfg.ci) / max(k_methods, 1)), k_methods=k_methods)   # EN: v1.1 — Bonferroni level for k methods audited together
        jobs = [(mid, stratum, sc["vals"][mid], sc["targets"], sc["controls"], ds.pairing, acfg_s, cfg["audit"]["single"], task, groups, sc["cov"], ds.covariates, sc["targets"])
                for mid in vecs]
        t_s = time.time()
        if cfg["n_jobs"] > 1:
            with ProcessPoolExecutor(max_workers=cfg["n_jobs"]) as ex:
                results = list(ex.map(_audit_one, jobs))
        else:
            results = []
            for k, jb in enumerate(jobs):
                results.append(_audit_one(jb))
                el = time.time() - t_s
                printer(_t("r.progress", s=stratum, k=k + 1, n=len(jobs), m=jb[0], el=f"{el:.0f}", eta=f"{el / (k + 1) * (len(jobs) - k - 1) / 60:.1f}"))
        for rows, urows, warn in results:
            for r in rows + urows:
                r["scale"] = sc["scale"]                       # EN: the scale actually used (log, or raw after a documented fallback)
            T["audit"] += rows; T["utility"] += urows
            if warn:
                warnings.append(warn)
        warnings += low_resample_warnings(T["audit"], stratum)
        # ---- sensitivity to the scale (v1.1): the same audit on the other scale, primary estimator, reported next to the primary, never selected
        if (cfg["audit"].get("sensitivity") or {}).get("scale") and task != "classification":
            other = "raw" if sc["scale"] == "log" else "log"
            sc2 = scaled_inputs(vals, targets, controls, cov, ds.target_types, other, stratum, [])
            if sc2["scale"] == other:
                jobs_sc = [(mid, stratum, sc2["vals"][mid], sc2["targets"], sc2["controls"], ds.pairing, acfg, cfg["audit"]["single"], task, groups, None, [], sc2["targets"]) for mid in vecs]
                results_sc = [_audit_one(jb) for jb in jobs_sc]
                prim = {(r["method_id"], r["stratum"], r["target"]): r for r in T["audit"] if r["stratum"] == stratum}
                for rows_sc, _, warn in results_sc:
                    if warn:
                        warnings.append("sensitivity(scale) " + warn); continue
                    for r in rows_sc:
                        pr = prim.get((r["method_id"], r["stratum"], r["target"]))
                        if pr is not None:
                            T["sensitivity_scale"].append({**r, "scale": other, "scale_primary": sc["scale"], "verdict_primary": pr["verdict"], "verdict_changed": r["verdict"] != pr["verdict"],
                                                           "s1_primary": pr["s1_mean"], "s1_delta": r["s1_mean"] - pr["s1_mean"], "s2_primary": pr["s2_mean"], "s2_delta": r["s2_mean"] - pr["s2_mean"]})
        # ---- sensitivity to the estimator (§3.2): same resamples, second estimator, reported next to the primary, never selected
        sens = cfg["audit"].get("sensitivity") or {}
        if sens.get("estimator"):
            if sens.get("nested_tuning"):
                warnings.append(f"{stratum}: sensitivity.nested_tuning requested but not implemented in this version; running the declared estimator with fixed params")
            jobs_s = [(mid, stratum, vals[mid], targets, controls, ds.pairing, acfg, sens, task, groups, None, [], targets) for mid in vecs]
            if cfg["n_jobs"] > 1:
                with ProcessPoolExecutor(max_workers=cfg["n_jobs"]) as ex:
                    results_s = list(ex.map(_audit_one, jobs_s))
            else:
                results_s = [_audit_one(jb) for jb in jobs_s]
            prim = {(r["method_id"], r["stratum"], r["target"]): r for r in T["audit"] if r["stratum"] == stratum}
            for rows_s, _, warn in results_s:
                if warn:
                    warnings.append("sensitivity " + warn); continue
                for r in rows_s:
                    p = prim.get((r["method_id"], r["stratum"], r["target"]))
                    if p is None:
                        continue
                    T["sensitivity"].append({**r, "estimator_primary": p["estimator"], "verdict_primary": p["verdict"], "verdict_changed": r["verdict"] != p["verdict"],
                                             "s1_primary": p["s1_mean"], "s1_delta": r["s1_mean"] - p["s1_mean"], "s2_primary": p["s2_mean"], "s2_delta": r["s2_mean"] - p["s2_mean"],
                                             "disc_primary": p["disc_mean"], "disc_delta": r["disc_mean"] - p["disc_mean"]})
        # ---- combinations (pairs of methods), boosting estimator, same resamples
        if cfg["audit"]["combinations"]:
            ids = list(vecs)
            task_c = task if task != "auto" else ("classification" if ds.target_types[ds.targets[0]] == "classification" else "regression")
            est_c = _estimator(cfg["audit"]["combination"], task_c)
            for hi in ids:
                for ad in ids:
                    if hi == ad:
                        continue
                    rp = pairs[((pairs.a_id == hi) & (pairs.b_id == ad)) | ((pairs.a_id == ad) & (pairs.b_id == hi))]
                    try:
                        rows = combination_gain(hi, ad, stratum, vals[hi], vals[ad], targets, acfg, est_c, groups)
                    except AuditError as e:
                        warnings.append(f"{stratum}/{hi}+{ad}: combination skipped — {e}"); continue
                    for r in rows:
                        r["r_log_predicted"] = float(rp.r_log_predicted.iloc[0]) if len(rp) else np.nan
                    T["combinations"] += rows

    # ---- sensitivity to the verdict thresholds (§3.2, v0.5.1): reclassification of stored S1/S2 under a grid, no refit
    T["threshold_sensitivity"] = verdict_sensitivity(T["audit"], margins=tuple(cfg["audit"]["verdict"].get("sensitivity_margins", (0.02, 0.03, 0.05))),
                                                     p_levels=tuple(cfg["audit"]["verdict"].get("sensitivity_p", (0.90, 0.95, 0.99))),
                                                     default_margin=cfg["audit"]["verdict"]["margin"], default_p=cfg["audit"]["verdict"]["p_specific"])
    tables = {k: (pd.concat(v, ignore_index=True) if v and isinstance(v[0], pd.DataFrame) else pd.DataFrame(v)) for k, v in T.items()}
    if cfg["algebra"]["transfer"] and len(strata) > 1:
        tables["sigma_transfer"] = A.sigma_transfer_table(vecs_by, sig_by, vals_by, design_by_stratum=design_by, identity_ids={e.id for e in cat.entries if e.identity_of},
                                                          tol=cfg["algebra"]["transfer_tol"], B=cfg["algebra"]["transfer_B"],
                                                          seed=cfg["seeds"]["bootstrap"], min_pair_n=cfg["algebra"]["min_pair_n"])
    primary = ds.targets[0]
    tables["screening"] = screening_table(tables["redundancy"], tables["audit"], tables.get("utility"), primary_target=primary) if not tables["audit"].empty else pd.DataFrame()

    # ---- write
    sort_keys = {"algebra": ["stratum", "method_id"], "sigma": ["stratum", "var_i", "var_j"], "pairs": ["stratum", "a_id", "b_id"],
                 "redundancy": ["stratum", "method_id"], "audit": ["stratum", "method_id", "target"], "utility": ["stratum", "method_id", "target"],
                 "combinations": ["stratum", "host_id", "added_id", "target"], "sigma_transfer": ["sigma_from", "observed_in"], "screening": ["stratum", "method_id"],
                 "sensitivity_scale": ["stratum", "method_id", "target"],
                 "sensitivity": ["stratum", "method_id", "target"], "threshold_sensitivity": ["stratum", "method_id", "target", "margin", "p_specific"],
                 "implicit_vectors": ["stratum", "role", "name"], "geometry": ["stratum", "method_id", "target"]}
    for name, df in tables.items():
        write_table(df, out_dir / f"{name}.csv", sort_keys.get(name, []))
    manifest.update(strata_used={s: int(len(fr)) for s, fr in strata}, methods_evaluated=sorted(set(tables["algebra"].method_id)) if not tables["algebra"].empty else [],
                    methods_skipped=skipped_all, warnings=warnings, notes=notes, finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"), wall_seconds=round(time.time() - t0, 1))
    manifest = write_manifest(out_dir, manifest)
    write_summary(out_dir, cfg, tables, manifest)
    if cfg["output"]["figures"]:
        try:
            from .plots import make_all
            make_all(out_dir, tables, cfg)
        except ImportError as e:
            warnings.append(f"figures skipped: {e}")
    from .html import write_report
    write_report(out_dir, cfg, tables, manifest)
    printer(_t("r.done", sec=f"{time.time() - t0:.0f}", out=out_dir))
    rp = (out_dir / "report.html").resolve()
    if rp.exists():
        import platform as _pf
        opener = {"Linux": "xdg-open", "Darwin": "open", "Windows": "start \"\""}.get(_pf.system(), "xdg-open")
        printer(_t("r.report", path=rp))
        printer(_t("r.open", cmd=f"{opener} \"{rp}\""))
        _show_inline(rp)
    return {"tables": tables, "manifest": manifest, "out_dir": out_dir}


def _out_of_validity(entry, frame: pd.DataFrame, ds: Dataset) -> tuple[float, str]:
    """
    EN: §2.2 — fraction of rows outside the method's declared validity (age, bmi, sex) and which fields; never blocks.
        age from group `idade`, bmi from W/H_m² when both exist, sex from group `sexo` (male=1).
    ES/PT: fração de linhas fora da faixa de validade declarada (idade, IMC, sexo); nunca bloqueia.
    """
    v = entry.validity or {}; n = len(frame); bad = np.zeros(n, dtype=bool); fields = []
    if v.get("age") and "idade" in frame:
        lo, hi = v["age"]; a = pd.to_numeric(frame["idade"], errors="coerce").to_numpy(float)
        m = np.zeros(n, dtype=bool)
        if lo is not None: m |= a < lo
        if hi is not None: m |= a > hi
        if m.any(): bad |= m; fields.append("age")
    if v.get("bmi") and {"W", "H"} <= set(frame.columns):
        lo, hi = v["bmi"]; b = frame["W"].to_numpy(float) / (frame["H"].to_numpy(float) / 100) ** 2
        m = np.zeros(n, dtype=bool)
        if lo is not None: m |= b < lo
        if hi is not None: m |= b > hi
        if m.any(): bad |= m; fields.append("bmi")
    if v.get("sex") in ("male", "female") and "sexo" in frame:
        sx = pd.to_numeric(frame["sexo"], errors="coerce").to_numpy(float)
        m = (sx != 1) if v["sex"] == "male" else (sx != 0)
        if m.any(): bad |= m; fields.append("sex")
    return float(bad.mean()) if n else 0.0, "+".join(fields)


def _designed_entry(di):
    """EN: minimal Entry for a designed index so pairs/redundancy can include it (precedence: current year). ES/PT: entrada mínima."""
    import datetime
    from .catalog import Entry
    return Entry(id=di.id, label=di.id, authors="designed", year=datetime.date.today().year, doi=None, kind="index", target=di.target,
                 form="monomial", frequency_khz=(50.0,), validity={}, provenance={"formula_source": "designed", "confidence": "low", "orthogonal_to": di.orthogonal_to},
                 vector={v: float(x) for v, x in zip(di.variables, di.vector_design)})

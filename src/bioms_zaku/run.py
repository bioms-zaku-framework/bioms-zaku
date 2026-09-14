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
    keep = [e for e in cat.entries if (inc == "all" or (inc == "curated" and e.curated) or (isinstance(inc, list) and e.id in inc)) and e.id not in exc]
    return Catalog(cat.version, cat.conventions, keep, cat.source_path)


def _values(cat: Catalog, ds: Dataset, frame: pd.DataFrame) -> tuple[dict[str, np.ndarray], dict[str, str]]:
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
        v = e.evaluate(env, frame[e.branch_group].to_numpy() if e.branch_group else None)
        vals[e.id] = np.asarray(v, float)
    return vals, skipped


def _audit_one(args):
    """EN: worker for one method (picklable). ES/PT: trabalhador por método."""
    mid, stratum, x, targets, controls, pairing, acfg, est_spec, task, groups, cov, cov_names, utility_targets = args
    est = _estimator(est_spec, task if task != "auto" else ("classification" if len(np.unique(next(iter(targets.values()))[np.isfinite(next(iter(targets.values())))])) <= 10 else "regression"))
    try:
        rows = [asdict(r) for r in audit_method(mid, stratum, x, targets, controls, pairing, acfg, est, groups)]
        urows = [asdict(u) for u in utility_method(mid, stratum, x, cov, cov_names, utility_targets, acfg, est, groups)] if cov is not None else []
    except AuditError as e:
        return [], [], f"{stratum}/{mid}: audit skipped — {e}"
    return rows, urows, None


def run(config: dict | str | Path, *, printer: Callable[[str], None] = print) -> dict:
    """
    EN: execute a full run; returns {"tables": {...}, "manifest": {...}, "out_dir": Path}.
    ES/PT: executa uma rodada completa.
    """
    cfg = resolve(config)
    # EN: BLAS/OpenMP threads are limited HERE, after import, so that run() called from Python (tests, notebooks, other
    #     packages) behaves exactly like the CLI: no oversubscription on small matrices. Env vars are also set for workers.
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(k, str(cfg["threads"]))
    # EN: the same pre-flight as `bioms-zaku check` runs here too (contract §3.2, 14/09): blocking problems stop the run with the
    #     check messages instead of producing a report with every audit skipped (found on a 60-row sample in the user simulation).
    from .check import check as _check
    _check(cfg, printer=lambda s: printer(s) if s.startswith(("  ✗", "  ⚠", "check:")) else None)
    with threadpool_limits(limits=int(cfg["threads"])):
        return _run(cfg, printer=printer)


def _run(cfg: dict, *, printer: Callable[[str], None]) -> dict:
    t0 = time.time()
    out_dir = Path(cfg["output"]["dir"]) / cfg["run_name"]; out_dir.mkdir(parents=True, exist_ok=True)
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
    frame = ds.frame
    manifest = {"run_name": cfg["run_name"], "config_resolved": cfg, "config_sha256": sha256_obj(cfg), "catalog_version": cat.version,
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
    designed: dict[str, object] = {}
    if cfg["design"]:
        if (cfg.get("declarations") or {}).get("targets_independent_of_variables") is not True:
            raise ValueError("design requires declarations.targets_independent_of_variables: true (contract v0.4.3: the target must not be computed from any mapped variable)")
        dg = cfg["design"]; tgt = dg["target"]
        has_t = np.isfinite(pd.to_numeric(frame[tgt], errors="coerce").to_numpy(float))
        sub = frame[has_t].reset_index(drop=True)
        if dg.get("split", "holdout") == "holdout":
            strat = sub[ds.strata] if ds.strata else None
            if ds.target_types.get(tgt) == "classification":
                strat = (strat.astype(str) + "|" if strat is not None else "") + sub[tgt].astype(str)
            split = holdout_split(sub, fraction=float(dg.get("fraction", 0.70)), seed=int(dg.get("seed", 42)), stratify=strat, id_col=ds.id)
        else:
            split = by_stratum_split(sub, ds.strata, dg["design_value"], dg["audit_value"])
        dvars = ds.variables + list(cfg["algebra"]["extra_log_variables"])
        did = dg.get("id", f"designed_{tgt}")
        groups_d = sorted(sub[ds.strata].dropna().unique()) if ds.strata else [None]
        man_d = {"target": tgt, "mode": split.mode, "fraction": split.fraction, "seed": split.seed, "stratify_on": split.stratify_on,
                 "design_hash": split.design_hash, "n_with_target": int(has_t.sum()), "n_design": split.n_design, "n_audit": split.n_audit,
                 "variables": list(dvars), "per_stratum": {}}
        for g in groups_d:
            mask = np.ones(len(sub), dtype=bool) if g is None else (sub[ds.strata] == g).to_numpy()
            from .design import Split
            sp = Split(split.design & mask, split.audit & mask, split.mode, split.fraction, split.seed, split.stratify_on, split.design_hash)
            di = design_index(sub, tgt, dvars, sp, index_id=did)
            key = "all" if g is None else str(g)
            designed[key] = di
            man_d["per_stratum"][key] = {"n_design": sp.n_design, "n_audit": sp.n_audit, "vector_design": di.vector_design.tolist(), "r2_design": di.r2_design,
                                         "vector_refit_full": None if di.vector_refit_full is None else di.vector_refit_full.tolist(), "r2_refit_full": di.r2_refit_full}
            if sp.n_audit < 100:
                warnings.append(f"design/{key}: audit partition has n={sp.n_audit} < 100; intervals will be wide")
        manifest["design"] = man_d
        frame = sub[split.audit].reset_index(drop=True)      # EN: everything below runs on the audit partition only

    # ---- per stratum
    lab_map = {str(k): str(v) for k, v in (cfg.get("strata_labels") or {}).items()}
    strata = [(lab_map.get(str(s), str(s)), frame[frame[ds.strata] == s].reset_index(drop=True)) for s in sorted(frame[ds.strata].dropna().unique())] if ds.strata else [("all", frame)]
    T = {k: [] for k in ("algebra", "sigma", "pairs", "redundancy", "audit", "utility", "combinations", "sensitivity", "implicit_vectors", "geometry")}
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
        vals, skipped = _values(cat, ds, fr)
        raw_key = str(fr[ds.strata].iloc[0]) if ds.strata and len(fr) else "all"
        di = designed.get(raw_key) if designed else None
        if di is not None:
            vals[di.id] = di.values(fr)
        skipped_all[stratum] = skipped
        # EN: complete-case fraction warning per method
        for mid, v in vals.items():
            frac = 1 - np.isfinite(v).mean()
            if frac > d["max_missing_frac_warn"]:
                warnings.append(f"{stratum}/{mid}: {frac:.0%} of rows lack the index (complete-case)")
        design_vars = ds.variables + list(cfg["algebra"]["extra_log_variables"])
        S, n_sig = A.log_covariance(fr, design_vars)
        vecs = A.compute_vectors(cat, {k: v for k, v in vals.items() if di is None or k != di.id}, fr, ds.variables, stratum,
                                 extra_log_variables=cfg["algebra"]["extra_log_variables"])
        if di is not None:
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
                       target_kind=(cat[mid].target_kind if mid in cat.ids() else None))
            row.update({f"e_{v}": float(x) for v, x in zip(vf.variables, vf.vector)})
            T["algebra"].append(row)
        for i, vi in enumerate(design_vars):
            for j, vj in enumerate(design_vars):
                T["sigma"].append(dict(stratum=stratum, n=n_sig, var_i=vi, var_j=vj, cov_log=float(S[i, j])))
        pcat = Catalog(cat.version, cat.conventions, list(cat.entries) + ([_designed_entry(di)] if di is not None else []), cat.source_path)
        pairs = A.pairs_table(pcat, vecs, vals, S, stratum, min_pair_n=cfg["algebra"]["min_pair_n"], alpha=cfg["algebra"]["fisher_alpha"])
        red = A.redundancy_table(pcat, pairs, stratum, threshold=cfg["algebra"]["redundancy_threshold"]) if not pairs.empty else pd.DataFrame()
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
        jobs = [(mid, stratum, vals[mid], targets, controls, ds.pairing, acfg, cfg["audit"]["single"], task, groups, cov, ds.covariates, targets)
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
                printer(f"[{stratum}] audit {k + 1}/{len(jobs)} {jb[0]} | {el:.0f}s | ETA {el / (k + 1) * (len(jobs) - k - 1) / 60:.1f} min")
        for rows, urows, warn in results:
            T["audit"] += rows; T["utility"] += urows
            if warn:
                warnings.append(warn)
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
                                                     p_levels=tuple(cfg["audit"]["verdict"].get("sensitivity_p", (0.90, 0.95, 0.99))))
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
                 "sensitivity": ["stratum", "method_id", "target"], "threshold_sensitivity": ["stratum", "method_id", "target", "margin", "p_specific"],
                 "implicit_vectors": ["stratum", "role", "name"], "geometry": ["stratum", "method_id", "target"]}
    for name, df in tables.items():
        write_table(df, out_dir / f"{name}.csv", sort_keys.get(name, []))
    manifest.update(strata_used={s: int(len(fr)) for s, fr in strata}, methods_evaluated=sorted(set(tables["algebra"].method_id)) if not tables["algebra"].empty else [],
                    methods_skipped=skipped_all, warnings=warnings, finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"), wall_seconds=round(time.time() - t0, 1))
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
    printer(f"done in {time.time() - t0:.0f}s → {out_dir}")
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
                 form="monomial", frequency_khz=(50.0,), validity={}, provenance={"formula_source": "designed", "confidence": "low"},
                 vector={v: float(x) for v, x in zip(di.variables, di.vector_design)})

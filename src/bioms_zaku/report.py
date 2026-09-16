"""
EN: Outputs (CONTRATOS.md §4): CSV tables at full precision, manifest with hashes/versions, Markdown summary.
    Outputs never contain row-level data.
ES: Salidas: tablas CSV con precisión completa, manifiesto con hashes/versiones, resumen Markdown. Solo agregados.
PT: Saídas: tabelas CSV com precisão completa, manifesto com hashes/versões, resumo Markdown. Só agregados.
"""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd

from . import SCHEMA_VERSION, __version__


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_obj(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def write_table(df: pd.DataFrame, path: Path, sort_by: list[str]) -> None:
    """EN: deterministic order, full float precision (repr), UTF-8, '.' decimal. ES/PT: ordem determinística, precisão completa."""
    if df is None or df.empty:
        pd.DataFrame(columns=df.columns if df is not None else []).to_csv(path, index=False)
        return
    keys = [k for k in sort_by if k in df.columns]
    df = df.sort_values(keys).reset_index(drop=True) if keys else df
    df.to_csv(path, index=False, float_format="%.17g", encoding="utf-8")


def versions() -> dict:
    import scipy, sklearn
    v = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
         "sklearn": sklearn.__version__, "platform": platform.platform()}
    try:
        import matplotlib; v["matplotlib"] = matplotlib.__version__
    except Exception:
        v["matplotlib"] = None
    return v


def write_manifest(out_dir: Path, manifest: dict) -> Path:
    manifest = dict(manifest)
    manifest.update(package_version=__version__, schema_version=SCHEMA_VERSION, versions=versions())
    manifest["outputs_sha256"] = {p.name: sha256_file(p) for p in sorted(out_dir.glob("*.csv"))}
    p = out_dir / "manifest.json"
    p.write_text(json.dumps(manifest, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return manifest


def write_summary(out_dir: Path, cfg: dict, tables: dict[str, pd.DataFrame], manifest: dict) -> Path:
    """EN: human summary; the only place with rounding (3 decimals). ES/PT: resumo humano; único lugar com arredondamento."""
    L = [f"# BioMS Zaku — {cfg['run_name']}", ""]
    from .i18n import t
    if cfg["preset"] != "full":
        L += [t("s.preset_note", p=cfg["preset"], r=cfg["audit"]["cv"]["repeats"], B=cfg["audit"]["bootstrap"]["B"]), ""]
    L += [t("s.package", v=__version__, cat=manifest.get("catalog_version"), rin=manifest.get("input_rows"), rout=manifest.get("rows_out"), sc=cfg["seeds"]["cv"], sb=cfg["seeds"]["bootstrap"]), ""]
    if (manifest.get("design") or {}).get("n_design"):
        L += [t("s.design_rows", nd=manifest["design"]["n_design"], na=manifest["design"]["n_audit"]), ""]
    L += [t("s.sample"), ""]
    for w in manifest.get("warnings", []):
        L.append(f"- ⚠ {w}")
    if manifest.get("warnings"):
        L.append("")
    alg, red, aud, uti, scr = (tables.get(k) for k in ("algebra", "redundancy", "audit", "utility", "screening"))
    strata = sorted(set(alg.stratum)) if alg is not None and not alg.empty else []
    for s in strata:
        L += [t("s.stratum", s=s), ""]
        a = alg[alg.stratum == s]; r = red[red.stratum == s] if red is not None else None
        L.append(t("s.methods", n=len(a), poor=int(a.poor_monomial.sum())))
        if "proposed" in a and bool(a["proposed"].astype(bool).any()):
            L.append(t("s.proposed", list=", ".join(sorted(a[a["proposed"].astype(bool)].method_id))))
        dz = (manifest.get("design") or {}).get("indices") or {}
        items = []
        for did, spec in dz.items():
            ps = (spec.get("per_stratum") or {}).get(s)
            if ps is None:
                continue
            lo, hi = ps.get("vector_lo") or [], ps.get("vector_hi") or []
            vec = ", ".join(f"{v} {x:+.2f}" + (f" [{l:+.2f}; {h:+.2f}]" if lo and np.isfinite(lo[i]) else "") for i, (v, x) in enumerate(zip(manifest["design"].get("variables", []), ps["vector_design"])) for l, h in [(lo[i] if lo else np.nan, hi[i] if hi else np.nan)])
            items.append(t("s.designed_item", id=did, t=spec["target"], orth=(t("s.designed_orth", c=spec["orthogonal_to"]) if spec.get("orthogonal_to") else ""), vec=vec,
                           r2=f"{ps['r2_design']:.3f}", r2u=(t("s.designed_r2u", r2u=f"{ps['r2_unconstrained']:.3f}") if ps.get("r2_unconstrained") is not None else "")))
        if items:
            L.append(t("s.designed", list="; ".join(items)))
        ss = (manifest.get("sample_statistics") or {}).get(s) or {}
        if ss:
            L.append(t("s.sample_stats", list="; ".join(f"{m}: " + ", ".join(f"{k} = {x:.4g}" for k, x in d.items()) for m, d in sorted(ss.items()))))
        if r is not None and len(r):
            rr = r[r.redundant]
            L.append(t("s.redundant", thr=cfg["algebra"]["redundancy_threshold"], k=len(rr), n=int((~r.identity_of.notna()).sum()))
                     + (" — " + "; ".join(f"{x.method_id}→{x.predecessor_id} ({x.rho_sp_max:.3f})" for x in rr.itertuples()) if len(rr) else ""))
            ids = r[r.identity_of.notna()]
            if len(ids):
                L.append(t("s.identities", list="; ".join(f"{x.method_id}={x.identity_of}" for x in ids.itertuples())))
        if aud is not None and not aud.empty:
            au = aud[aud.stratum == s]
            for tg in sorted(set(au.target)):
                at = au[au.target == tg]; vc = at.verdict.value_counts()
                L.append(t("s.audit", t=tg, c=at.control.iloc[0], metric=str(at.metric.iloc[0]).replace("R2", "R²"), est=at.estimator.iloc[0],
                           sp=vc.get("SPECIFIC", 0), tc=vc.get("TRACKS_CONTROL", 0), bo=vc.get("BOTH", 0), ne=vc.get("NEITHER", 0)))
        if uti is not None and not uti.empty:
            u = uti[uti.stratum == s]
            for tg in sorted(set(u.target)):
                ut = u[u.target == tg]
                L.append(t("s.utility", cov=ut.covariates.iloc[0], t=tg, k=int(ut.useful.sum()), n=len(ut), mg=cfg["audit"]["utility_margin"]))
        L.append("")
    geo = tables.get("geometry")
    if geo is not None and not geo.empty:
        L += [t("s.geo_title"), "", t("s.geo_intro", thr=geo.thresholds.iloc[0].replace(";", " · ")), ""]
        for s in sorted(set(geo.stratum)):
            g = geo[geo.stratum == s]
            for tg in sorted(set(g.target)):
                gt = g[g.target == tg]; r0 = gt.iloc[0]
                coupled = bool(gt.flag_coupled_target_control.any())
                L.append(t("s.geo_line", s=s, t=tg, c=r0.control, cos=f"{r0.cos_target_control:.3f}", r2t=f"{r0.fit_r2_target:.3f}", r2c=f"{r0.fit_r2_control:.3f}")
                         + (t("s.geo_coupled") if coupled else "") + (t("s.geo_poor") if bool(gt.poor_projection.all()) else ""))
                par = gt[gt.flag_parallel_to_control]
                if len(par):
                    L.append(t("s.geo_parallel", list="; ".join(f"{x.method_id} (cos {x.cos_control:+.3f})" for x in par.itertuples())))
                mono = gt[gt.vector_source == "catalog"]
                if len(mono):
                    L.append(t("s.geo_identity", gap=f"{mono.r_log_target_gap.abs().max():.1e}"))
        L.append("")
    if "pairs" in tables and not tables["pairs"].empty:
        p = tables["pairs"]; p = p[~p.identity].nlargest(10, "abs_err_log")
        L += [t("s.gaps_title"), "", t("s.gaps_header"), "|---|---|---|---|---|---|"]
        L += [f"| {x.stratum} | {x.a_id} | {x.b_id} | {x.r_log_predicted:.3f} | {x.r_log_observed:.3f} | {x.abs_err_log:.3f} |" for x in p.itertuples()]
        L.append("")
    ts = tables.get("threshold_sensitivity")
    if ts is not None and not ts.empty:
        n_rows = ts.groupby(["stratum", "method_id", "target"]).ngroups; ch = ts[ts.changed]
        L += [t("s.thr_title"), "", t("s.thr_intro", margins=[round(float(v), 4) for v in sorted(ts.margin.unique())], ps=[round(float(v), 4) for v in sorted(ts.p_specific.unique())],
                                      n=n_rows, k=ch.groupby(["stratum", "method_id", "target"]).ngroups), ""]
        if len(ch):
            L += [t("s.thr_header"), "|---|---|---|---|---|---|---|"]
            L += [f"| {x.stratum} | {x.method_id} | {x.target} | {x.margin:g} | {x.p_specific:g} | {x.verdict} | {x.verdict_default} |" for x in ch.itertuples()]
        L.append("")
    se = tables.get("sensitivity")
    if se is not None and not se.empty:
        L += [t("s.est_title"), "", t("s.est_intro", est=se.estimator.iloc[0], prim=se.estimator_primary.iloc[0], k=int(se.verdict_changed.sum()), n=len(se),
                                      d1=f"{se.s1_delta.abs().median():.3f}", d2=f"{se.s2_delta.abs().median():.3f}"), "", t("s.est_header"), "|---|---|---|---|---|---|---|---|---|"]
        L += [f"| {x.stratum} | {x.method_id} | {x.target} | {x.s1_primary:+.3f} | {x.s1_mean:+.3f} | {x.s2_primary:+.3f} | {x.s2_mean:+.3f} | {x.verdict_primary} | {x.verdict} |" for x in se.itertuples()]
        L.append("")
    ss = tables.get("sensitivity_scale")
    if ss is not None and not ss.empty:
        L += [t("s.scale_title"), "", t("s.scale_intro", prim=ss.scale_primary.iloc[0], other=ss.scale.iloc[0], k=int(ss.verdict_changed.sum()), n=len(ss),
                                        d1=f"{ss.s1_delta.abs().median():.3f}", d2=f"{ss.s2_delta.abs().median():.3f}"), "", t("s.scale_header"), "|---|---|---|---|---|---|---|---|---|"]
        L += [f"| {x.stratum} | {x.method_id} | {x.target} | {x.s1_primary:+.3f} | {x.s1_mean:+.3f} | {x.s2_primary:+.3f} | {x.s2_mean:+.3f} | {x.verdict_primary} | {x.verdict} |" for x in ss.itertuples()]
        L.append("")
    if "sigma_transfer" in tables and not tables["sigma_transfer"].empty:
        tr = tables["sigma_transfer"].sort_values(["sigma_from", "observed_in"]).reset_index(drop=True)   # EN: same order as the CSV
        L += [t("s.transfer_title"), "", t("s.transfer_header"), "|---|---|---|---|---|---|---|---|"]
        L += [f"| {x.sigma_from} | {x.observed_in} | {x.type} | {x.pairs} | {x.median_abs_err:.3f} [{x.median_abs_err_lo:.3f}, {x.median_abs_err_hi:.3f}] | {x.p90_abs_err:.3f} | {x.frac_within_tol:.2f} | {x.excess_median:+.3f} [{x.excess_lo:+.3f}, {x.excess_hi:+.3f}] |" for x in tr.itertuples()]
        L.append("")
    if scr is not None and not scr.empty:
        vc = scr["class"].value_counts()
        L += [t("s.screening_title"), "", t("s.screening_header"), "|---|---|"] + [f"| {k} | {v} |" for k, v in vc.items()] + [""]
    p = out_dir / "summary.md"
    p.write_text("\n".join(L), encoding="utf-8")
    return p

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
    if cfg["preset"] != "article":
        L += [f"> **PRESET `{cfg['preset']}`** — reduced resampling ({cfg['audit']['cv']['repeats']}×CV, B={cfg['audit']['bootstrap']['B']}). "
              "Not for reporting.", ""]
    L += [f"Package {__version__} · catalog {manifest.get('catalog_version')} · input rows {manifest.get('input_rows')} → used {manifest.get('rows_out')} · "
          f"seeds cv={cfg['seeds']['cv']} bootstrap={cfg['seeds']['bootstrap']}", ""]
    L += ["Sample: convenience sample as analysed (survey weights ignored by design); verdicts describe this sample, not a population (§3.2).", ""]
    for w in manifest.get("warnings", []):
        L.append(f"- ⚠ {w}")
    if manifest.get("warnings"):
        L.append("")
    alg, red, aud, uti, scr = (tables.get(k) for k in ("algebra", "redundancy", "audit", "utility", "screening"))
    strata = sorted(set(alg.stratum)) if alg is not None and not alg.empty else []
    for s in strata:
        L += [f"## Stratum `{s}`", ""]
        a = alg[alg.stratum == s]; r = red[red.stratum == s] if red is not None else None
        L.append(f"- methods evaluated: {len(a)} (poor monomial fit: {int(a.poor_monomial.sum())})")
        if r is not None and len(r):
            rr = r[r.redundant]
            L.append(f"- redundant with an earlier method (|ρ_s| ≥ {cfg['algebra']['redundancy_threshold']}): {len(rr)} of {int((~r.identity_of.notna()).sum())}"
                     + (" — " + "; ".join(f"{x.method_id}→{x.predecessor_id} ({x.rho_sp_max:.3f})" for x in rr.itertuples()) if len(rr) else ""))
            ids = r[r.identity_of.notna()]
            if len(ids):
                L.append(f"- identities (exact transformations, not counted): " + "; ".join(f"{x.method_id}={x.identity_of}" for x in ids.itertuples()))
        if aud is not None and not aud.empty:
            au = aud[aud.stratum == s]
            for t in sorted(set(au.target)):
                at = au[au.target == t]; vc = at.verdict.value_counts()
                L.append(f"- audit `{t}` vs `{at.control.iloc[0]}` ({at.metric.iloc[0]}, {at.estimator.iloc[0]}; conditional control, v0.5): "
                         f"SPECIFIC {vc.get('SPECIFIC', 0)} · TRACKS_CONTROL {vc.get('TRACKS_CONTROL', 0)} · BOTH {vc.get('BOTH', 0)} · NEITHER {vc.get('NEITHER', 0)}")
        if uti is not None and not uti.empty:
            u = uti[uti.stratum == s]
            for t in sorted(set(u.target)):
                ut = u[u.target == t]
                L.append(f"- utility over {ut.covariates.iloc[0]} for `{t}`: useful {int(ut.useful.sum())} of {len(ut)} (margin {cfg['audit']['utility_margin']})")
        L.append("")
    if "pairs" in tables and not tables["pairs"].empty:
        p = tables["pairs"]; p = p[~p.identity].nlargest(10, "abs_err_log")
        L += ["## Largest predicted−observed gaps (Pearson of logs)", "", "| stratum | a | b | predicted | observed | gap |", "|---|---|---|---|---|---|"]
        L += [f"| {x.stratum} | {x.a_id} | {x.b_id} | {x.r_log_predicted:.3f} | {x.r_log_observed:.3f} | {x.abs_err_log:.3f} |" for x in p.itertuples()]
        L.append("")
    ts = tables.get("threshold_sensitivity")
    if ts is not None and not ts.empty:
        n_rows = ts.groupby(["stratum", "method_id", "target"]).ngroups; ch = ts[ts.changed]
        L += ["## Sensitivity of verdicts to the thresholds", "",
              f"Grid: margin {[float(v) for v in sorted(ts.margin.unique())]} × P {[float(v) for v in sorted(ts.p_specific.unique())]}; {n_rows} verdicts reclassified without refit. "
              f"Verdicts that change somewhere in the grid: {ch.groupby(['stratum', 'method_id', 'target']).ngroups} of {n_rows}. "
              "A verdict that changes only at the extremes of the grid sits near a threshold (S1 or S2 close to the margin) and should be read as borderline.", ""]
        if len(ch):
            L += ["| stratum | method | target | margin | P | verdict | default |", "|---|---|---|---|---|---|---|"]
            L += [f"| {x.stratum} | {x.method_id} | {x.target} | {x.margin} | {x.p_specific} | {x.verdict} | {x.verdict_default} |" for x in ch.itertuples()]
        L.append("")
    se = tables.get("sensitivity")
    if se is not None and not se.empty:
        L += ["## Sensitivity to the estimator (same resamples)", "",
              f"Estimator: {se.estimator.iloc[0]} vs primary {se.estimator_primary.iloc[0]}. Verdicts that change: {int(se.verdict_changed.sum())} of {len(se)}. "
              f"Median |ΔS1| {se.s1_delta.abs().median():.3f}, median |ΔS2| {se.s2_delta.abs().median():.3f}.", "",
              "| stratum | method | target | S1 primary | S1 alt | S2 primary | S2 alt | verdict primary | verdict alt |", "|---|---|---|---|---|---|---|---|---|"]
        L += [f"| {x.stratum} | {x.method_id} | {x.target} | {x.s1_primary:+.3f} | {x.s1_mean:+.3f} | {x.s2_primary:+.3f} | {x.s2_mean:+.3f} | {x.verdict_primary} | {x.verdict} |" for x in se.itertuples()]
        L.append("")
    if "sigma_transfer" in tables and not tables["sigma_transfer"].empty:
        t = tables["sigma_transfer"]
        L += ["## Σ transfer between strata", "", "| Σ from | observed in | type | pairs | median |err| [95% boot] | p90 |err| | within ±tol | excess over own Σ [95% boot] |", "|---|---|---|---|---|---|---|---|"]
        L += [f"| {x.sigma_from} | {x.observed_in} | {x.type} | {x.pairs} | {x.median_abs_err:.3f} [{x.median_abs_err_lo:.3f}, {x.median_abs_err_hi:.3f}] | {x.p90_abs_err:.3f} | {x.frac_within_tol:.2f} | {x.excess_median:+.3f} [{x.excess_lo:+.3f}, {x.excess_hi:+.3f}] |" for x in t.itertuples()]
        L.append("")
    if scr is not None and not scr.empty:
        L += ["## Screening classes", "", scr["class"].value_counts().to_string(), ""]
    p = out_dir / "summary.md"
    p.write_text("\n".join(L), encoding="utf-8")
    return p

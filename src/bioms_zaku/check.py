"""
EN: `bioms-zaku check` — validate a configuration and its data WITHOUT running: rows, strata, targets, classes, controls,
    catalog methods evaluable/skipped, bootstrap feasibility, design partition, circularity declaration. Exit code ≠ 0 on error.
ES/PT: valida configuração e dados SEM rodar; código de saída ≠ 0 em erro.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from .audit import resamples
from .catalog import BUILTIN_PATH
from .config import resolve
from .io import InputError, read_table
from .run import _load_catalog, _values


class CheckError(ValueError):
    pass


def check(config: str | Path | dict, *, printer: Callable[[str], None] = print) -> dict:
    """EN: returns a report dict; raises CheckError on blocking problems. ES/PT: relatório; erro quando bloqueante."""
    rep: dict = {"errors": [], "warnings": [], "info": []}
    cfg = resolve(config)
    d = cfg["data"]; cols = dict(d["columns"])
    if cfg["strata"] is not None:
        if cols.get("strata") not in (None, cfg["strata"]):
            rep["errors"].append(f"strata declared twice and differently ({cfg['strata']!r} vs {cols.get('strata')!r})")
        cols["strata"] = cfg["strata"]
    try:
        ds = read_table(d["path"], cols, sep=d["sep"], decimal=d["decimal"], encoding=d["encoding"],
                        drop_nonpositive=d["drop_nonpositive"], min_n=d["min_n"], min_per_class=d["min_per_class"])
    except InputError as e:
        rep["errors"].append(f"input: {e}")
        _emit(rep, printer); raise CheckError("input contract violated")
    rep["info"].append(f"input: {ds.info['rows_in']} rows → {ds.info['rows_out']} usable · sep={ds.info.get('sep_used')!r} decimal={ds.info.get('decimal_used')!r}")
    rep["warnings"] += ds.info["warnings"]
    for k, v in ds.info["rows_dropped"].items():
        if v:
            rep["info"].append(f"rows dropped ({k}): {v}")
    # targets / controls / pairing
    for name, tt in ds.target_types.items():
        s = ds.frame[name]
        if tt == "classification":
            vc = s.dropna().astype(int).value_counts().sort_index().to_dict()
            rep["info"].append(f"{name}: classification, classes {vc}")
            if min(vc.values()) < d["min_per_class"]:
                rep["errors"].append(f"{name}: smallest class {min(vc.values())} < min_per_class {d['min_per_class']}")
        else:
            rep["info"].append(f"{name}: regression, n={int(s.notna().sum())}, median {s.median():.3g}, range [{s.min():.3g}, {s.max():.3g}]")
    for t, c in ds.pairing.items():
        rep["info"].append(f"pairing: {t} vs control {c}")
        if ds.target_types[t] == "regression":
            ok = ds.frame[[t, c]].dropna()
            rho = ok.corr(method="spearman").iloc[0, 1]
            if abs(rho) > 0.8:
                rep["warnings"].append(f"{t}↔{c}: Spearman {rho:.2f} — control nearly collinear with the target; the contrast will be weak")
    # circularity declaration (contract v0.4.3): required whenever an index is designed; recommended always
    decl = (cfg.get("declarations") or {}).get("targets_independent_of_variables")
    if cfg.get("design") and decl is not True:
        rep["errors"].append("design requires declarations.targets_independent_of_variables: true (the target must not be computed from R, Xc, H, W or any mapped variable)")
    elif decl is not True:
        rep["warnings"].append("declarations.targets_independent_of_variables is not true — confirm no target/control is derived from the mapped variables")
    # strata sizes
    if ds.strata:
        for s, n in ds.frame[ds.strata].value_counts().items():
            rep["info"].append(f"stratum {s}: n={int(n)}")
    # catalog methods
    cat = _load_catalog(cfg)
    vals, skipped = _values(cat, ds, ds.frame)
    inc = cfg["catalog"]["include"]
    if inc == "curated":
        from .catalog import load_catalog as _lc
        full = _lc(None if cfg["catalog"]["path"] in (None, "builtin") else cfg["catalog"]["path"])
        n_nc = sum(1 for e in full.entries if not e.curated and e.status != "excluded")
        rep["info"].append(f"catalog: include = curated ({len(cat.entries)} methods with primary-source reading); {n_nc} non-curated entries exist and are NOT audited (catalog.include: all)")
    rep["info"].append(f"catalog: {len(vals)} methods evaluable, {len(skipped)} skipped")
    hint = {"sexo": "sex", "idade": "age", "C_arm": "arm", "C_waist": "waist", "C_calf": "calf"}
    need: dict[str, list[str]] = {}
    for k, why in skipped.items():
        rep["info"].append(f"  skipped {k}: {why}")
        if why.startswith("missing inputs"):
            for inp in why[len("missing inputs "):].strip("[]").replace("'", "").split(", "):
                need.setdefault(inp, []).append(k)
    for inp, ids in sorted(need.items()):
        if inp in hint:
            how = f"--map {hint[inp]}=<column>  (YAML: data.columns.groups.{inp})"
        elif inp[:1] == "Z" and inp[1:].isdigit():
            how = f"YAML: data.columns.extra_variables.{inp} — a column with |Z| at {inp[1:]} kHz"
        else:
            how = f"YAML: data.columns.groups.{inp} — a categorical column with that meaning (see the catalogue entry)"
        rep["info"].append(f"  → {len(ids)} method(s) need `{inp}`, which is not mapped: {how}")
    for k, v in vals.items():
        frac = 1 - np.isfinite(v).mean()
        if frac > d["max_missing_frac_warn"]:
            rep["warnings"].append(f"{k}: {frac:.0%} of rows lack the index (complete-case)")
    # bootstrap feasibility per stratum (smallest complete-case n)
    B, mo = cfg["audit"]["bootstrap"]["B"], cfg["audit"]["bootstrap"]["min_oob"]
    groups = [("all", ds.frame)] if not ds.strata else [(str(s), g) for s, g in ds.frame.groupby(ds.strata)]
    for s, g in groups:
        n_min = min((int(np.isfinite(vals[k][g.index]).sum()) for k in vals), default=0) if vals else 0
        n_t = int(g[ds.targets[0]].notna().sum())
        n = min(n_min, n_t)
        if n and n < d["min_n"]:
            rep["errors"].append(f"stratum {s}: complete-case n={n} < min_n {d['min_n']}")
        elif n and 0.368 * n < mo:
            rep["errors"].append(f"stratum {s}: expected OOB ≈ {0.368 * n:.0f} < min_oob {mo}; bootstrap impossible — lower min_oob")
        else:
            rep["info"].append(f"stratum {s}: bootstrap feasible (n≈{n}, expected OOB ≈ {0.368 * n:.0f} ≥ {mo}, B={B})")
    # design partition
    if cfg.get("design"):
        dg = cfg["design"]; tgt = dg["target"]
        n_t = int(ds.frame[tgt].notna().sum()); fr = float(dg.get("fraction", 0.70))
        rep["info"].append(f"design: target {tgt}, holdout {fr:.0%} of {n_t} rows with target → audit ≈ {int(round((1 - fr) * n_t))} rows")
        if (1 - fr) * n_t < 100:
            rep["warnings"].append("design: audit partition < 100 rows; intervals will be wide")
    task = cfg["audit"]["task"] if cfg["audit"]["task"] != "auto" else ds.target_types[ds.targets[0]]
    est = cfg["audit"]["single"]["estimator"]
    if est in ("ridge", "logistic"):
        est = "logistic" if task == "classification" else "ridge"      # EN: effective default per task (§3.2)
    rep["info"].append(f"preset {cfg['preset']}: task {task}; CV {cfg['audit']['cv']['folds']}×{cfg['audit']['cv']['repeats']}, B={B}; estimator {est}")
    _emit(rep, printer)
    if rep["errors"]:
        raise CheckError(f"{len(rep['errors'])} blocking problem(s): " + " | ".join(rep["errors"]))   # EN: reasons travel with the exception (API users)
    return rep


def _emit(rep: dict, printer: Callable[[str], None]) -> None:
    for x in rep["info"]:
        printer(f"  · {x}")
    for x in rep["warnings"]:
        printer(f"  ⚠ {x}")
    for x in rep["errors"]:
        printer(f"  ✗ {x}")
    printer("check: " + ("OK — ready to run" if not rep["errors"] else f"{len(rep['errors'])} error(s); fix before running"))

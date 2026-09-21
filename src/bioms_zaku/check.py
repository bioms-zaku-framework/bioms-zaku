"""
EN: `bioms-zaku check` — validate a configuration and its data WITHOUT running: rows, strata, targets, classes, controls,
    catalog methods evaluable/skipped, bootstrap feasibility, design partition, circularity declaration. Exit code ≠ 0 on error.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from .audit import resamples
from .catalog import BUILTIN_PATH
from .i18n import set_language, t
from .config import resolve
from .io import InputError, read_table
from .run import _load_catalog, _values


class CheckError(ValueError):
    pass


def check(config: str | Path | dict, *, printer: Callable[[str], None] = print) -> dict:
    """EN: returns a report dict; raises CheckError on blocking problems. ES/PT: relatório; erro quando bloqueante."""
    rep: dict = {"errors": [], "warnings": [], "info": []}
    cfg = resolve(config)
    from .i18n import set_language as _sl
    _sl(cfg["language"])   # EN: API and CLI alike: the YAML language applies (as in run(); v0.9)
    d = cfg["data"]; cols = dict(d["columns"])
    if cfg["strata"] is not None:
        if cols.get("strata") not in (None, cfg["strata"]):
            rep["errors"].append(t("c.strata_twice", a=repr(cfg["strata"]), b=repr(cols.get("strata"))))
        cols["strata"] = cfg["strata"]
    try:
        ds = read_table(d["path"], cols, sep=d["sep"], decimal=d["decimal"], encoding=d["encoding"],
                        drop_nonpositive=d["drop_nonpositive"], min_n=d["min_n"], min_per_class=d["min_per_class"])
    except InputError as e:
        rep["errors"].append(t("c.input_err", err=e))
        _emit(rep, printer); raise CheckError("input contract violated")
    rep["info"].append(t("c.input", rin=ds.info["rows_in"], rout=ds.info["rows_out"], sep=repr(ds.info.get("sep_used")), dec=repr(ds.info.get("decimal_used"))))
    st = cfg.get("study") or {}
    rep["info"].append(t("c.study", d=st.get("data_name") or Path(str(cfg["data"]["path"])).stem, r=st.get("researcher") or "—"))
    rep["warnings"] += ds.info["warnings"]
    for k, v in ds.info["rows_dropped"].items():
        if v:
            rep["info"].append(t("c.dropped", k=k, v=v))
    # targets / controls / pairing
    for name, tt in ds.target_types.items():
        s = ds.frame[name]
        if tt == "classification":
            vc = s.dropna().astype(int).value_counts().sort_index().to_dict()
            rep["info"].append(t("c.classif", name=name, vc=vc))
            if min(vc.values()) < d["min_per_class"]:
                rep["errors"].append(t("c.class_small", name=name, n=min(vc.values()), m=d["min_per_class"]))
            from .audit import EPV_MIN, events_per_variable
            p_max = 1 + len(ds.covariates or []) if ds.covariates else 2
            p_max = max(p_max, 2)
            ev, epv = events_per_variable(s.dropna().to_numpy(float), p_max)
            if epv < EPV_MIN:
                rep["warnings"].append(t("c.epv_low", name=name, ev=ev, p=p_max, epv=f"{epv:.1f}"))
            # EN: v1.2 (found 2026-09-16: sex as control AND as stratum passed check) — inside every stratum the label must
            #     vary and each class must reach min_per_class, otherwise the audit there is impossible.
            if ds.strata:
                for sv, g in ds.frame.groupby(ds.strata):
                    vcs = g[name].dropna().astype(int).value_counts().to_dict()
                    if len(vcs) < 2 or min(vcs.values()) < d["min_per_class"]:
                        rep["errors"].append(t("c.class_stratum", name=name, s=sv, vc=vcs, m=d["min_per_class"]))
        else:
            rep["info"].append(t("c.regression", name=name, n=int(s.notna().sum()), med=f"{s.median():.3g}", lo=f"{s.min():.3g}", hi=f"{s.max():.3g}"))
    for tg, c in ds.pairing.items():
        rep["info"].append(t("c.pairing", t=tg, c=c))
        if ds.target_types[tg] == "regression":
            ok = ds.frame[[tg, c]].dropna()
            rho = ok.corr(method="spearman").iloc[0, 1]
            if abs(rho) > 0.8:
                rep["warnings"].append(t("c.collinear", t=tg, c=c, rho=f"{rho:.2f}"))
    # circularity declaration (contract v0.4.3): required whenever an index is designed; recommended always
    decl = (cfg.get("declarations") or {}).get("targets_independent_of_variables")
    for dg in ([cfg["design"]] if isinstance(cfg.get("design"), dict) else list(cfg.get("design") or [])):
        if ds.target_types.get(dg.get("target")) == "classification":
            rep["errors"].append(t("c.design_class", name=dg.get("target")))
    if cfg.get("design") and decl is not True:
        rep["errors"].append(t("c.design_decl"))
    elif decl is not True:
        rep["warnings"].append(t("c.decl_warn"))
    # strata sizes
    if ds.strata:
        for s, n in ds.frame[ds.strata].value_counts().items():
            rep["info"].append(t("c.stratum_n", s={str(k): str(v) for k, v in (cfg.get("strata_labels") or {}).items()}.get(str(s), s), n=int(n)))
    # catalog methods
    cat = _load_catalog(cfg)
    vals, skipped = _values(cat, ds, ds.frame)
    inc = cfg["catalog"]["include"]
    if inc == "curated":
        from .catalog import load_catalog as _lc
        full = _lc(None if cfg["catalog"]["path"] in (None, "builtin") else cfg["catalog"]["path"])
        n_nc = sum(1 for e in full.entries if not e.curated and e.status != "excluded")
        rep["info"].append(t("c.curated", k=len(cat.entries), n=n_nc))
    rep["info"].append(t("c.evaluable", k=len(vals), n=len(skipped)))
    prop = [e.id for e in cat.entries if e.proposed]
    if prop:
        rep["info"].append(t("c.proposed", ids=", ".join(prop)))
    inc_ids = set(inc) if isinstance(inc, list) else set()
    for ue in cfg["catalog"].get("user_entries") or []:
        if isinstance(ue, dict) and (ue.get("provenance") or {}).get("formula_source") == "proposed" and ue.get("id") not in inc_ids and inc != "all" and "all" not in inc_ids:
            rep["warnings"].append(t("c.proposed_not_included", id=ue.get("id")))
    hint = {"sexo": "sex", "idade": "age", "C_arm": "arm", "C_waist": "waist", "C_calf": "calf"}
    need: dict[str, list[str]] = {}
    def _why(w: str) -> str:
        if w.startswith("missing inputs "): return t("c.why_missing", list=w[len("missing inputs "):])
        if w.startswith("excluded: "): return t("c.why_excluded", reason=w[len("excluded: "):])
        if w.startswith("closed method"): return t("c.why_closed")
        return w
    for k, why in skipped.items():
        rep["info"].append(t("c.skipped", k=k, why=_why(why)))
        if why.startswith("missing inputs"):
            for inp in why[len("missing inputs "):].strip("[]").replace("'", "").split(", "):
                need.setdefault(inp, []).append(k)
    for inp, ids in sorted(need.items()):
        if inp in hint:
            how = t("c.hint_map", role=hint[inp], inp=inp)
        elif inp[:1] == "Z" and inp[1:].isdigit():
            how = t("c.hint_z", inp=inp, khz=inp[1:])
        else:
            how = t("c.hint_group", inp=inp)
        rep["info"].append(t("c.need", n=len(ids), inp=inp, how=how))
    for k, v in vals.items():
        frac = 1 - np.isfinite(v).mean()
        if frac > d["max_missing_frac_warn"]:
            rep["warnings"].append(t("c.missing_frac", k=k, frac=f"{frac:.0%}"))
    # bootstrap feasibility per stratum (smallest complete-case n)
    B, mo = cfg["audit"]["bootstrap"]["B"], cfg["audit"]["bootstrap"]["min_oob"]
    groups = [("all", ds.frame)] if not ds.strata else [(str(s), g) for s, g in ds.frame.groupby(ds.strata)]
    lab = {str(k): str(v) for k, v in (cfg.get("strata_labels") or {}).items()}
    # EN: when indices are designed, only the AUDIT partition (1 − fraction) carries every audit number: the feasibility rules apply
    #     to it, per stratum (found on CrossFit, 2026-09-15: 107 rows passed, the 33 audited left one valid resample).
    specs = ([cfg["design"]] if isinstance(cfg["design"], dict) else list(cfg["design"])) if cfg.get("design") else []
    audit_share = (1 - float(specs[0].get("fraction", 0.70))) if specs and specs[0].get("split", "holdout") == "holdout" else 1.0
    for s, g in groups:
        n_min = min((int(np.isfinite(vals[k][g.index]).sum()) for k in vals), default=0) if vals else 0
        n_t = int(g[ds.targets[0]].notna().sum())
        n_full = min(n_min, n_t); n = int(round(audit_share * n_full)); s_lab = lab.get(s, s)
        if n_full and n < d["min_n"]:
            rep["errors"].append(t("c.design_too_small", s=s_lab, na=n, m=d["min_n"]) if specs else t("c.min_n", s=s_lab, n=n, m=d["min_n"]))
        elif n_full and 0.368 * n < mo:
            rep["errors"].append(t("c.design_oob", s=s_lab, na=n, oob=f"{0.368 * n:.0f}", m=mo) if specs else t("c.oob_bad", s=s_lab, oob=f"{0.368 * n:.0f}", m=mo))
        else:
            rep["info"].append(t("c.oob_ok", s=s_lab, n=n, oob=f"{0.368 * n:.0f}", m=mo, B=B))
    # design partition
    if cfg.get("design"):
        specs = [cfg["design"]] if isinstance(cfg["design"], dict) else list(cfg["design"])
        for dg in specs:
            tgt = dg["target"]; orth = dg.get("orthogonal_to")
            if tgt not in ds.frame:
                rep["errors"].append(t("c.design_col", col=tgt)); continue
            if orth is not None and (orth not in ds.frame or orth == tgt):
                rep["errors"].append(t("c.design_orth_bad", col=str(orth), tgt=tgt)); continue
            n_t = int(ds.frame[tgt].notna().sum()) if orth is None else int((ds.frame[tgt].notna() & ds.frame[orth].notna()).sum()); fr = float(dg.get("fraction", 0.70))
            rep["info"].append(t("c.design_info", tgt=tgt, fr=f"{fr:.0%}", n=n_t, na=int(round((1 - fr) * n_t))) + (t("c.design_orth", c=orth) if orth else ""))
            if (1 - fr) * n_t < 100:
                rep["warnings"].append(t("c.design_small"))
            # EN: the audit needs data.min_n complete rows PER STRATUM on the audit partition; below that every method is skipped (v1.0)
    task = ds.target_types[ds.targets[0]]
    est = cfg["audit"]["single"]["estimator"]
    if est in ("ridge", "logistic"):
        est = "logistic" if task == "classification" else "ridge"      # EN: effective default per task (§3.2)
    rep["info"].append(t("c.preset", p=cfg["preset"], task=t(f"task.{task}"), f=cfg["audit"]["cv"]["folds"], r=cfg["audit"]["cv"]["repeats"], B=B, est=est))
    rep["info"].append(t("c.scale", scale=cfg["audit"]["scale"]) if cfg["audit"]["scale"] == "log" else t("c.scale_raw"))
    _emit(rep, printer)
    if rep["errors"]:
        raise CheckError(t("c.blocking", n=len(rep["errors"]), list=" | ".join(rep["errors"])))   # EN: reasons travel with the exception (API users)
    return rep


def _emit(rep: dict, printer: Callable[[str], None]) -> None:
    for x in rep["info"]:
        printer(f"  · {x}")
    for x in rep["warnings"]:
        printer(f"  ⚠ {x}")
    for x in rep["errors"]:
        printer(f"  ✗ {x}")
    printer(t("c.ok") if not rep["errors"] else t("c.errors", n=len(rep["errors"])))

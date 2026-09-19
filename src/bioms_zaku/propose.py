"""
EN: `bioms-zaku propose analise.yaml` (v0.9) — add the researcher's own indices to a configuration, as a common user would:
    one question at a time (id, name, what it measures, formula), each formula validated at once against the grammar and
    evaluated on the data of the YAML (rows, finite, positive, min/median/max), then written to `catalog.user_entries` as a
    proposed entry and listed in `catalog.include`. Nothing is guessed: a rejected formula is asked again; Enter on the id ends.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

import numpy as np
import yaml

from .catalog import BUILTIN_PATH, CatalogError, build_catalog
from .config import resolve
from .expr import ExpressionError, compile_expr
from .i18n import set_language, t
from .io import InputError, read_table

ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
GRAMMAR = "R, Xc, H (cm), H_m (m), W (kg), PhA (°), Z, II · + - * / ** ( ) · log exp sqrt atan abs min max · mean median sd · pi e"


def _dataset(cfg: dict):
    d = cfg["data"]; cols = dict(d["columns"])
    if cfg["strata"] is not None:
        cols["strata"] = cfg["strata"]
    return read_table(d["path"], cols, sep=d["sep"], decimal=d["decimal"], encoding=d["encoding"],
                      drop_nonpositive=d["drop_nonpositive"], min_n=d["min_n"], min_per_class=d["min_per_class"])


def _try_entry(entry: dict, ds, conv: dict) -> tuple[np.ndarray, list]:
    """EN: build a one-entry catalog (same validation as a run) and evaluate it on the data; returns (values, stats used)."""
    cat = build_catalog({"catalog_version": "user", "conventions": conv, "entries": [entry]})
    e = cat.entries[0]
    env = {c: ds.frame[c].to_numpy(float) for c in ds.variables + ds.derived if c in ds.frame}
    missing = sorted(set(e.inputs) - set(env))
    if missing:
        raise ExpressionError(t("p.missing", list=", ".join(missing)))
    rec: list = []
    n = len(next(iter(env.values())))
    v = np.broadcast_to(np.asarray(e.evaluate(env, record=rec), float), (n,)).copy()   # EN: a scalar formula (e.g. mean(W)) becomes a constant column
    return v, rec


def propose(config_path: str | Path, *, ask: Callable[[str, str | None], str], printer: Callable[[str], None] = print, lang: str | None = None) -> Path:
    p = Path(config_path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if lang:
        raw["language"] = lang
    cfg = resolve(raw); set_language(cfg["language"])
    conv = json.loads(BUILTIN_PATH.read_text(encoding="utf-8"))["conventions"]
    try:
        ds = _dataset(cfg)
    except InputError as e:
        raise InputError(t("c.input_err", err=e)) from None
    printer(t("p.intro", n=ds.info["rows_out"])); printer(t("p.grammar", g=GRAMMAR)); printer("")
    cat_block = raw.setdefault("catalog", {}) or {}
    raw["catalog"] = cat_block
    entries = list(cat_block.get("user_entries") or [])
    inc = cat_block.get("include", "curated")
    inc = [inc] if isinstance(inc, str) else list(inc)
    existing = {e.get("id") for e in entries if isinstance(e, dict)}
    from .run import _load_catalog, _values
    from .catalog import load_catalog as _lc
    cat_ids = set(_lc(None if cfg["catalog"]["path"] in (None, "builtin") else cfg["catalog"]["path"]).ids())   # EN: every catalog id, curated or not
    cat_run = _load_catalog(cfg)
    known, _ = _values(cat_run, ds, ds.frame)                       # EN: published indices on these rows, for the neighbor warning
    min_n = int(cfg["data"]["min_n"])
    added = []
    while True:
        printer(t("p.help.id"))
        mid = (ask(t("p.id"), None) or "").strip()
        if not mid:
            break
        if not ID_RE.match(mid) or mid in existing:
            printer(t("p.bad_id", id=mid)); continue
        if mid in cat_ids:
            printer(t("p.id_catalog", id=mid)); continue
        printer(t("p.help.label"))
        label = (ask(t("p.label", id=mid), mid) or "").strip() or mid
        printer(t("p.help.target"))
        target = (ask(t("p.target"), "lean_mass") or "").strip() or "lean_mass"
        entry = None
        for _ in range(3):
            printer(t("p.help.expr"))
            expr = (ask(t("p.expr"), None) or "").strip()
            if not expr:
                break
            cand = {"id": mid, "label": label, "authors": (cfg.get("study") or {}).get("researcher") or "author", "target": target, "expr": expr,
                    "provenance": {"formula_source": "proposed", "note": t("p.note", date=__import__("datetime").date.today().isoformat())}}
            try:
                v, rec = _try_entry(cand, ds, conv)
            except (CatalogError, ExpressionError) as e:
                printer(t("p.rejected", err=str(e))); continue
            fin = np.isfinite(v); pos = fin & (v > 0)
            printer(t("p.evaluated", n=len(v), fin=int(fin.sum()), pos=int(pos.sum()), lo=f"{np.nanmin(v[fin]):.4g}" if fin.any() else "—",
                      med=f"{np.nanmedian(v[fin]):.4g}" if fin.any() else "—", hi=f"{np.nanmax(v[fin]):.4g}" if fin.any() else "—"))
            if rec:
                printer(t("p.stats", list=", ".join(f"{k} = {x:.4g}" for k, x in rec)))
            # EN: rejections found by the user simulation (v1.0): too few auditable values; constant index
            if int(pos.sum()) < min_n:
                printer(t("p.rejected", err=t("p.too_few", k=int(pos.sum()), n=len(v), m=min_n))); continue
            if float(np.nanmax(v[pos])) == float(np.nanmin(v[pos])):          # EN: constant = every value equal (a std test misses 1e-14 rounding)
                printer(t("p.rejected", err=t("p.constant"))); continue
            if pos.sum() < len(v):
                printer(t("p.nonpositive", k=int(len(v) - pos.sum())))
            best, best_id = 0.0, None
            for kid, kv in known.items():
                ok = pos & np.isfinite(kv) & (kv > 0)
                if ok.sum() >= min_n:
                    from scipy.stats import spearmanr
                    rho = abs(float(spearmanr(np.log(kv[ok]), np.log(v[ok])).statistic))
                    if rho > best:
                        best, best_id = rho, kid
            if best_id is not None and best >= float(cfg["algebra"]["redundancy_threshold"]):
                printer(t("p.neighbor", m=best_id, rho=f"{best:.2f}"))
            if (ask(t("p.keep"), "yes") or "yes").strip().lower() in ("yes", "y", "sim", "sí", "si", "s", "true"):
                entry = cand
            break
        if entry is None:
            printer(t("p.skipped", id=mid)); continue
        entries.append(entry); existing.add(mid); added.append(mid)
        if mid not in inc:
            inc.append(mid)
        printer(t("p.added", id=mid))
    if not added:
        printer(t("p.none")); return p
    if "curated" not in inc and "all" not in inc and not any(i not in added and i not in existing for i in inc):
        inc = ["curated"] + inc
    cat_block["include"] = inc; cat_block["user_entries"] = entries
    p.write_text(_keep_header(p.read_text(encoding="utf-8")) + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    printer(t("p.done", n=len(added), out=p, ids=", ".join(added)))
    return p


def _keep_header(text: str) -> str:
    """EN: keep the comment header written by init (lines starting with #) so the file stays self-explaining."""
    head = []
    for line in text.splitlines():
        if line.startswith("#"):
            head.append(line)
        else:
            break
    return ("\n".join(head) + "\n") if head else ""

"""
EN: reading ONE result (contract §4.7). The screening table gives a label per method and stratum; the label abbreviates
    three answers, each relative to a different reference: redundancy (relative to the methods published earlier),
    specificity (relative to the control declared for the run) and added value (relative to the covariates). A reader
    who runs everything can leave with the label and without the size of the increments behind it — the point made by
    an external reviewer on 2026-10-02. This module opens one row: the numbers each answer comes from, the rule applied
    to them, the reference, and the decision.

    It reads, it never computes: every number comes from the tables of a finished run, so the notebook (`api.explain`)
    and the report (`html.py`, section 3) show the same thing, and `render` in another language changes the words and
    not one number. The decisions are rebuilt with the package's own rule functions (`audit._positive`,
    `audit.verdict_conditional`), never rewritten here; when a rebuilt decision differs from the stored one, the
    explanation says so in the open instead of showing either alone.

    Numbers are shown with as many decimals as it takes for the printed value to fall on the same side of every
    threshold it is compared with as the true value does: 0.0287 against a margin of 0.03 never prints as 0.03, and
    −0.00002 against 0 never prints as −0.0000 beside "interval above 0: no".
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from .audit import AuditConfig, _positive, verdict_conditional

LEGACY = {"MEASURES_CONTROL": "TRACKS_CONTROL"}
METRIC = {"R2": "R²", "D_Tjur": "D", "D": "D"}


def _f(v) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return float("nan")
    return x


def _b(v) -> bool:
    """EN: a boolean from a table read in memory (bool) or back from a CSV (bool or the strings 'True'/'False')."""
    if isinstance(v, str):
        return v.strip() == "True"
    try:
        return bool(v) and not (isinstance(v, float) and math.isnan(v))
    except (TypeError, ValueError):
        return False


def _s(v) -> str:
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)


def fmt(v: float, thresholds=(0.0,), min_dec: int = 3, sign: bool = False) -> str:
    """
    EN: the shortest rendering, from `min_dec` decimals up to 12, whose value sits on the same side of every threshold
        (above, below or equal) as `v` itself. NaN prints as an empty dash.
    """
    v = _f(v)
    if math.isnan(v):
        return "—"
    side = lambda x, t: (x > t) - (x < t)
    for d in range(min_dec, 13):
        r = round(v, d)
        if all(side(r, t) == side(v, t) for t in thresholds) and not (r == 0 and v != 0):
            s = f"{r:+.{d}f}" if sign else f"{r:.{d}f}"
            return s
    return f"{v:+.3e}" if sign else f"{v:.3e}"


# ----------------------------------------------------------------------------------------------------------------------
def rows(tables: dict) -> list[tuple[str, str, str, str]]:
    """
    EN: every (method, stratum, target, control) that can be read, in a fixed order: the order of screening.csv
        (stratum, then method), the primary target first; then any row audited but absent from the screening. The first
        element is the one the report opens on — a fixed, declared rule, never chosen by result.
    """
    au = tables.get("audit"); sc = tables.get("screening")
    out: list[tuple[str, str, str, str]] = []
    pairs = []
    if au is not None and not au.empty:
        pairs = list(dict.fromkeys(zip(au.target.astype(str), au.control.astype(str))))
    if sc is not None and not sc.empty:
        for m, s in zip(sc.method_id.astype(str), sc.stratum.astype(str)):
            if pairs:
                out += [(m, s, t, c) for t, c in pairs]
            else:
                out.append((m, s, "", ""))
    if au is not None and not au.empty:
        for m, s, t, c in zip(au.method_id.astype(str), au.stratum.astype(str), au.target.astype(str), au.control.astype(str)):
            if (m, s, t, c) not in out:
                out.append((m, s, t, c))
    return out


def _one(df, **keys):
    if df is None or df.empty:
        return None
    m = pd.Series(True, index=df.index)
    for k, v in keys.items():
        if k not in df:
            return None
        m &= df[k].astype(str) == str(v)
    hit = df[m]
    return None if hit.empty else hit.iloc[0]


def explain_row(tables: dict, cfg: dict, method_id: str, stratum: str, target: str | None = None, control: str | None = None,
                manifest: dict | None = None) -> dict:
    """
    EN: one (method, stratum[, target, control]) read from the tables of a run. Returns plain values at full precision;
        `lines()` turns them into words. Raises KeyError when the method/stratum is in none of the tables.
    """
    method_id, stratum = str(method_id), str(stratum)
    au_cfg = cfg["audit"]; vcfg = au_cfg["verdict"]
    margin, p_spec, ci = float(vcfg["margin"]), float(vcfg["p_specific"]), float(vcfg["ci"])
    thr = float(cfg["algebra"]["redundancy_threshold"])
    au = tables.get("audit"); ut = tables.get("utility"); rd = tables.get("redundancy"); sc = tables.get("screening"); al = tables.get("algebra")
    if target is None or control is None:
        cands = [r for r in rows(tables) if r[0] == method_id and r[1] == stratum]
        if cands:
            target = target if target is not None else cands[0][2]
            control = control if control is not None else cands[0][3]
    known = any(df is not None and not df.empty and ((df.method_id.astype(str) == method_id) & (df.stratum.astype(str) == stratum)).any()
                for df in (au, ut, rd, sc))
    if not known:
        avail = sorted({(m, s) for m, s, _, _ in rows(tables)})
        raise KeyError(f"{method_id!r} in stratum {stratum!r} is in no table of this run; available: "
                       + ", ".join(f"{m}/{s}" for m, s in avail))
    e: dict = dict(method_id=method_id, stratum=stratum, target=target or "", control=control or "",
                   margin=margin, p_specific=p_spec, ci=ci, redundancy_threshold=thr)
    # ---- 1 redundancy
    r = _one(rd, method_id=method_id, stratum=stratum)
    if r is None:
        e["redundancy"] = None
    else:
        ident = _s(r.get("identity_of"))
        rho = _f(r.get("rho_sp_max"))
        stored = _b(r.get("redundant"))
        rebuilt = bool(not math.isnan(rho) and rho >= thr and not ident)
        e["redundancy"] = dict(rho=rho, predecessor=_s(r.get("predecessor_id")), year=_s(r.get("predecessor_year")).split(".")[0],
                               identity_of=ident, redundant=stored, rebuilt=rebuilt)
    # ---- 2 specificity, conditional on the declared control
    a = _one(au, method_id=method_id, stratum=stratum, target=target, control=control) if target else None
    if a is None or math.isnan(_f(a.get("s1_mean"))):
        e["audit"] = None
    else:
        acfg = AuditConfig(specificity_margin=margin, p_specific=p_spec)
        side = {}
        for k in ("s1", "s2"):
            c = dict(mean=_f(a[f"{k}_mean"]), lo=_f(a[f"{k}_lo"]), hi=_f(a[f"{k}_hi"]), p=_f(a[f"p_{k}"]), n=1)
            side[k] = dict(c, checks=(c["mean"] > margin, c["lo"] > 0, c["p"] >= p_spec), present=_positive(c, acfg))
        side["s1"].update(base=_f(a.get("score_oob_control_to_target")), full=_f(a.get("score_oob_idx_control_to_target")), metric=_s(a.get("metric")))
        side["s2"].update(base=_f(a.get("score_oob_target_to_control")), full=_f(a.get("score_oob_idx_target_to_control")),
                          metric=_s(a.get("metric_control")) or _s(a.get("metric")))
        rebuilt = verdict_conditional(side["s1"], side["s2"], acfg)
        fam = _s(a.get("verdict_family"))
        e["audit"] = dict(side, n=int(_f(a["n"])), B_eff=int(_f(a["B_eff"])), scale=_s(a.get("scale")),
                          verdict=LEGACY.get(_s(a["verdict"]), _s(a["verdict"])), rebuilt=rebuilt,
                          family=(LEGACY.get(fam, fam) if fam and int(_f(a.get("k_methods")) or 1) > 1 else ""),
                          ci_family=_f(a.get("ci_family")), k_methods=int(_f(a.get("k_methods")) or 1),
                          epv_low=_b(a.get("epv_low")))
    # ---- 3 added value over the covariates
    u = _one(ut, method_id=method_id, stratum=stratum, target=target) if target else None
    if u is None:
        e["utility"] = None
    else:
        lo, mg = _f(u["delta_lo"]), _f(u["margin"])
        e["utility"] = dict(covariates=_s(u["covariates"]).replace("+", " + "), metric=_s(u.get("metric")),
                            base=_f(u["score_base"]), full=_f(u["score_with"]), mean=_f(u["delta_mean"]), lo=lo,
                            hi=_f(u["delta_hi"]), p=_f(u["p_delta"]), margin=mg, useful=_b(u["useful"]), rebuilt=bool(lo > mg))
    s = _one(sc, method_id=method_id, stratum=stratum)
    e["class"] = _s(s["class"]) if s is not None else ""
    g = _one(al, method_id=method_id, stratum=stratum)
    e["designed"] = bool(g is not None and "designed" in g and _b(g["designed"]))
    why = ((manifest or {}).get("methods_skipped") or {}).get(stratum, {}).get(method_id) if manifest else None
    e["not_audited_because"] = _s(why)
    e["consistent"] = all([e["redundancy"] is None or e["redundancy"]["rebuilt"] == e["redundancy"]["redundant"],
                           e["audit"] is None or e["audit"]["rebuilt"] == e["audit"]["verdict"],
                           e["utility"] is None or e["utility"]["rebuilt"] == e["utility"]["useful"]])
    return e


# ----------------------------------------------------------------------------------------------------------------------
def lines(e: dict) -> list[tuple[str, str]]:
    """
    EN: the explanation as (kind, text) in the current language; kind ∈ {head, q, p, rule, decision, note, warn}. The
        same list is printed by the notebook and laid out by the report.
    """
    from .i18n import t
    yn = lambda ok: t("x.yes") if ok else t("x.no")
    mg, pp, ci = e["margin"], e["p_specific"], f"{e['ci']:.0%}"
    out: list[tuple[str, str]] = []
    A = e["audit"]
    head = t("x.head", m=e["method_id"], s=e["stratum"], t=e["target"] or "—", c=e["control"] or "—")
    if A is not None:
        head += " · " + t("x.head_n", n=A["n"], B=A["B_eff"], scale=A["scale"] or "—")
    out.append(("head", head))
    if e["designed"]:
        out.append(("note", t("x.designed")))
    # 1
    out.append(("q", t("x.q1")))
    R = e["redundancy"]
    if R is None:
        out.append(("p", t("x.r.absent")))
    elif R["identity_of"]:
        out.append(("p", t("x.r.ident", p=R["identity_of"])))
    elif not R["predecessor"]:
        out.append(("p", t("x.r.none")))
        out.append(("rule", t("x.r.orig")))
    else:
        out.append(("p", t("x.r.pred", p=R["predecessor"], y=R["year"], rho=fmt(R["rho"], (e["redundancy_threshold"],)), thr=f"{e['redundancy_threshold']:g}")))
        out.append(("rule", t("x.r.red", p=R["predecessor"]) if R["redundant"] else t("x.r.orig")))
    # 2
    out.append(("q", t("x.q2", c=e["control"] or "—")))
    if A is None:
        from .check import why_skipped
        out.append(("p", t("x.notaudited", why=why_skipped(e["not_audited_because"]) if e["not_audited_because"] else t("x.why_unknown"))))
    else:
        out.append(("p", t("x.s.note", B=A["B_eff"])))
        if "D" in (METRIC.get(A["s1"]["metric"]), METRIC.get(A["s2"]["metric"])):
            out.append(("note", t("x.d_note")))
        for k, tgt, ctl in (("s1", e["target"], e["control"]), ("s2", e["control"], e["target"])):
            S = A[k]; m = METRIC.get(S["metric"], S["metric"])
            c1, c2, c3 = S["checks"]
            out.append(("p", t(f"x.{k}", metric=m, t=e["target"], c=e["control"], a=fmt(S["base"], min_dec=4), b=fmt(S["full"], min_dec=4),
                               mean=fmt(S["mean"], (0.0, mg), 4, True), ci=ci, lo=fmt(S["lo"], (0.0,), 4, True), hi=fmt(S["hi"], (0.0,), 4, True),
                               p=fmt(S["p"], (pp,)))))
            out.append(("rule", t("x.rule", mg=f"{mg:g}", pp=f"{pp:g}", c1=yn(c1), c2=yn(c2), c3=yn(c3), out=t("x.present") if S["present"] else t("x.absent"))))
        out.append(("decision", t("x.decide", a=t("x.present") if A["s1"]["present"] else t("x.absent"),
                                  b=t("x.present") if A["s2"]["present"] else t("x.absent"), v=A["verdict"])))
        out.append(("note", t("x.relative", c=e["control"])))
        if A["family"]:
            out.append(("note", t("x.family", lvl=f"{A['ci_family']:.4f}", k=A["k_methods"], v=A["family"])))
        if A["epv_low"]:
            out.append(("note", t("x.epv")))
        if A["rebuilt"] != A["verdict"]:
            out.append(("warn", t("x.mismatch", rebuilt=A["rebuilt"], stored=A["verdict"])))
    # 3
    U = e["utility"]
    out.append(("q", t("x.q3", cov=U["covariates"] if U else "—")))
    if U is None:
        out.append(("p", t("x.u.none")))
    else:
        m = METRIC.get(U["metric"], U["metric"])
        out.append(("p", t("x.u.levels", metric=m, t=e["target"], cov=U["covariates"], a=fmt(U["base"], min_dec=4), b=fmt(U["full"], min_dec=4))))
        out.append(("p", t("x.u.gain", mean=fmt(U["mean"], (0.0, U["margin"]), 4, True), ci=ci, lo=fmt(U["lo"], (0.0, U["margin"]), 4, True),
                           hi=fmt(U["hi"], (0.0,), 4, True), p=fmt(U["p"], (pp,)))))
        out.append(("rule", t("x.u.rule", mg=f"{U['margin']:g}", c=yn(U["lo"] > U["margin"]), out=t("x.useful") if U["useful"] else t("x.notuseful"))))
        if U["rebuilt"] != U["useful"]:
            out.append(("warn", t("x.mismatch", rebuilt=U["rebuilt"], stored=U["useful"])))
    if R is not None and R["rebuilt"] != R["redundant"]:
        out.append(("warn", t("x.mismatch", rebuilt=R["rebuilt"], stored=R["redundant"])))
    # 4
    if e["class"]:
        out.append(("q", t("x.q4")))
        out.append(("p", t("x.class", cls=e["class"])))
    return out


def text(e: dict) -> str:
    """EN: the explanation as plain text (notebook, terminal)."""
    rule = {"rule": "    ", "decision": "  ⇒ ", "note": "  · ", "warn": "  ! ", "p": "  "}
    out = []
    for kind, s in lines(e):
        if kind == "q":
            out.append("")
            out.append(s)
        elif kind == "head":
            out.append(s)
            out.append("─" * min(len(s), 100))
        else:
            out.append(rule.get(kind, "  ") + s)
    return "\n".join(out)


class Explanation:
    """EN: what `api.explain` returns: prints as text; `.data` holds every value at full precision."""

    def __init__(self, data: dict):
        self.data = data

    def __str__(self) -> str:
        return text(self.data)

    __repr__ = __str__


def explain(result, method_id: str, stratum: str, target: str | None = None, control: str | None = None) -> Explanation:
    """
    EN: open ONE result of a finished run — the numbers behind its label, the rule applied, the reference, the decision.
        `result` is what `run()` returned, or the run's output folder. Reads the saved tables and manifest; computes
        nothing; follows the language chosen with `set_language`.
    """
    import json
    from .run import read_tables
    out_dir = Path(result["out_dir"] if isinstance(result, dict) else result)
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    return Explanation(explain_row(read_tables(out_dir), manifest["config_resolved"], method_id, stratum, target, control, manifest))

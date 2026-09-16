"""
EN: `bioms-zaku start dados.csv` (v1.0, PLANO_v1.0_fluxo.md) — ONE guided path through the three uses:
      screen 1  who and what (language, data name, researcher)
      screen 2  the columns (same questions as `init`, same suggestions, same validation)
      screen 3  the standard run: how the published indices behave on these data  → the standard use ends here
      screen 4  "suggestions for your target?": the Zaku designs an index per target and stratum on a design partition, prints
                each one in plain words (formula, R² on the design rows, nearest published neighbour, suggested name) and asks
                accept / edit (name, rounding) / no — nothing about verdicts is shown before accepting
      screen 5  "an index of your own?": paste the formula (the `propose` questions)
      final run only if something was accepted or proposed: published + accepted + own, validated on the rows never used to design.
    Navigation in every question: `<` back (previous answer becomes the suggestion), `?` help again, Enter accepts the suggestion,
    `none` refuses a suggested column. At the end of a screen: numbered summary and "correct a line?". The YAML is written after
    each screen, so the whole session is reproducible without questions: `bioms-zaku run analise.yaml` gives the same tables.
    `--map role=column ... --yes`: no questions at all (scripts, CI).
ES: un solo camino guiado.  PT: um só caminho guiado.  IT: un solo percorso guidato.
"""
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import yaml

from .i18n import LANGS, set_language, t
from .io import InputError
from .wizard import GROUP_ROLES, HEADER, build_config, detect, suggest

BACK, HELP, NONE = "<", "?", "none"
COLUMN_KEYS = ("R", "Xc", "H", "W", "target", "control", "strata", "id") + tuple(GROUP_ROLES)


# ----------------------------------------------------------------------------------------------------------- question engine
@dataclass
class Q:
    key: str
    prompt: Callable[[dict], str]
    help: Callable[[dict], str | None] = lambda a: None
    default: Callable[[dict], str | None] = lambda a: None
    validate: Callable[[str, dict], str | None] = lambda v, a: None      # EN: returns an error text, or None when valid
    required: bool = False
    skip: Callable[[dict], bool] = lambda a: False
    secret_default: bool = False                                         # EN: default shown but not stored as an "answer"


class Screen:
    """EN: a list of questions with back/help/summary/correct-a-line navigation. Answers persist across back moves."""

    def __init__(self, questions: list[Q], ask: Callable[[str, str | None], str] | None, printer: Callable[[str], None], answers: dict):
        self.q, self.ask, self.printer, self.a = questions, ask, printer, answers

    def _default(self, q: Q) -> str | None:
        return self.a[q.key] if q.key in self.a else q.default(self.a)

    def _visible(self) -> list:
        return [q for q in self.q if not q.skip(self.a)]

    def _one(self, q: Q) -> str:
        """EN: ask one question until valid; returns BACK when the user typed `<`. Interactive: a blank line and "question k of n" first."""
        d = self._default(q)
        h = q.help(self.a)
        if self.ask is not None:                                       # EN: k = position among ALL questions of the screen (skipped ones simply do not appear)
            self.printer(""); self.printer(t("st.qnum", k=self.q.index(q) + 1, n=len(self.q)))
        if h:
            self.printer(h)
        while True:
            if self.ask is None:                                          # EN: scripted (--map/--yes): the default is the answer
                v = d or ""
            else:
                raw = self.ask(q.prompt(self.a) + (f" [{d}]" if d else ""), d) or ""
                raw = raw.strip()
                if raw == BACK:
                    return BACK
                if raw == HELP:
                    self.printer(h or t("st.nohelp")); continue
                v = raw or (d or "")
            if v.lower() == NONE:
                v = ""
            if q.required and not v:
                if self.ask is None:
                    raise InputError(t("w.required", role=q.key))
                self.printer(t("w.required", role=q.key)); continue
            err = q.validate(v, self.a)
            if err:
                if self.ask is None:
                    raise InputError(err)
                self.printer(err); continue
            self.a[q.key] = v
            return v

    def run(self) -> dict:
        i = 0
        while i < len(self.q):
            q = self.q[i]
            if q.skip(self.a):
                i += 1; continue
            r = self._one(q)
            if r == BACK:
                j = i - 1
                while j >= 0 and self.q[j].skip(self.a):
                    j -= 1
                i = max(j, 0)
                continue
            i += 1
        if self.ask is not None:
            self._summary_and_correct()
        return self.a

    def _summary_and_correct(self) -> None:
        while True:
            shown = [q for q in self.q if not q.skip(self.a)]
            self.printer(t("st.summary"))
            for k, q in enumerate(shown, 1):
                v = self.a.get(q.key) or ""
                self.printer(f"  {k:2d}. {q.key:12s} ← {v if v else (t('w.not_mapped') if q.key in COLUMN_KEYS else '—')}")
            raw = (self.ask(t("st.correct"), None) or "").strip()
            if not raw:
                return
            if raw.isdigit() and 1 <= int(raw) <= len(shown):
                self._one(shown[int(raw) - 1]); continue
            self.printer(t("st.correct_bad", n=len(shown)))


# ----------------------------------------------------------------------------------------------------------- screens 1 and 2
def _screen_1(ask, printer, answers: dict, lang: str | None, p: Path) -> dict:
    """EN: language, data name, researcher — ONE screen. The language takes effect as soon as it is answered (prompts are
    rendered lazily), so the next questions already come in that language; `<` from the data name returns to the language."""
    def ask_lang(v, a):
        if v.lower() not in LANGS:
            return t("st.lang_bad")
        set_language(v.lower()); return None
    if ask is None:
        answers.setdefault("lang", lang or "en"); set_language(answers["lang"].lower())
    qs = [Q("lang", lambda a: "Language / Idioma / Língua / Lingua — en · es · pt · it", default=lambda a: lang or "en", validate=ask_lang, required=True),
          Q("data_name", lambda a: t("w.data_name"), help=lambda a: t("w.help.data_name"), default=lambda a: p.stem),
          Q("researcher", lambda a: t("w.researcher"), help=lambda a: t("w.help.researcher"))]
    return Screen(qs, ask, printer, answers).run()


def _screen_2(ask, printer, answers: dict, cols: list[str], numeric: list[str]) -> dict:
    sug = suggest(cols)
    def in_cols(v, a):
        return None if (not v or v in cols) else t("w.notin_again", col=repr(v), cols=", ".join(cols))
    def not_target(v, a):
        e = in_cols(v, a)
        if e: return e
        return t("w.control_same_again", col=repr(v)) if v == a.get("target") else None
    def unit(opts):
        return lambda v, a: None if v in opts else t("w.units_bad")
    def covs(v, a):
        bad = [x.strip() for x in v.split(",") if x.strip() and x.strip() not in cols]
        return t("w.cov_notin", col=repr(bad[0])) if bad else None
    def labels_ok(v, a):
        if not v: return None
        for pair in v.split(","):
            if "=" not in pair: return t("st.labels_bad")
        return None
    def yes_no(v, a):
        return None if v.lower() in ("yes", "y", "sim", "sí", "si", "no", "n", "não", "nao") else t("st.yesno_bad")
    qs = [Q(r, (lambda r: lambda a: t("w.col_for", role=r, meaning=t(f"w.mean.{r}")))(r), help=(lambda a: t("w.help.vars")) if r == "R" else (lambda a: None),
            default=(lambda r: lambda a: sug.get(r))(r), validate=in_cols, required=True) for r in ("R", "Xc", "H", "W")]
    qs += [Q("H_unit", lambda a: t("w.unit_H"), default=lambda a: "cm", validate=unit(("cm", "m")), required=True),
           Q("W_unit", lambda a: t("w.unit_W"), default=lambda a: "kg", validate=unit(("kg", "g")), required=True),
           Q("target", lambda a: t("w.target"), help=lambda a: t("w.help.target"), default=lambda a: sug.get("target"), validate=in_cols, required=True),
           Q("control", lambda a: t("w.control"), help=lambda a: t("w.help.control"), default=lambda a: sug.get("control"), validate=not_target, required=True),
           Q("covariates", lambda a: t("w.covariates"), help=lambda a: t("w.help.cov"), default=lambda a: f"{a['W']},{a['H']}", validate=covs),
           Q("strata", lambda a: t("w.strata"), help=lambda a: t("w.help.strata"), default=lambda a: sug.get("strata"), validate=in_cols),
           Q("labels", lambda a: t("w.labels"), help=lambda a: t("w.help.labels"), validate=labels_ok, skip=lambda a: not a.get("strata")),
           Q("id", lambda a: t("w.id"), help=lambda a: t("w.help.id"), default=lambda a: sug.get("id"), validate=in_cols)]
    def _group_default(role):
        def d(a):
            v = a.get("strata") if role == "sex" and a.get("strata") else sug.get(role)
            taken = {a.get("target"), a.get("control")} | {x.strip() for x in (a.get("covariates") or "").split(",")}
            return None if v in taken else v            # EN: never suggest the target/control/covariate as a catalogue input (found on CrossFit)
        return d
    qs += [Q(role, (lambda role: lambda a: t("w.group_col", role=f"{role} ({t('w.role.' + role)})"))(role), help=(lambda a: t("w.help.groups")) if role == "sex" else (lambda a: None),
             default=_group_default(role), validate=in_cols) for role in GROUP_ROLES]
    qs += [Q("independent", lambda a: t("w.independent"), help=lambda a: t("w.help.indep"), default=lambda a: "no", validate=yes_no, required=True)]
    return Screen(qs, ask, printer, answers).run()


def _yes(v: str | None) -> bool:
    return (v or "").strip().lower() in ("yes", "y", "sim", "sí", "si", "s", "true")


def _no(v: str | None) -> bool:
    return (v or "").strip().lower() in ("no", "n", "não", "nao", "false")


def _ask_yes_no(ask, printer, prompt: str, default: str) -> bool:
    """EN: a yes/no question that repeats until the answer is yes or no (an invalid answer is never read as 'no')."""
    while True:
        v = (ask(prompt + f" [{default}]", default) or default).strip()
        if _yes(v): return True
        if _no(v): return False
        printer(t("st.yesno_bad"))


def _config_from_answers(p: Path, a: dict, sep: str, dec: str, encoding: str, cols: list[str]) -> dict:
    mapping = {r: a[r] for r in ("R", "Xc", "H", "W")}
    covariates = [x.strip() for x in (a.get("covariates") or "").split(",") if x.strip()]
    groups = {GROUP_ROLES[r]: a[r] for r in GROUP_ROLES if a.get(r)}
    strata = a.get("strata") or None
    if strata and "sexo" not in groups:
        groups["sexo"] = strata
    cfg = build_config(p, mapping, units={"H": a["H_unit"], "W": a["W_unit"]}, targets={a["target"]: a["target"]}, controls={a["control"]: a["control"]},
                       covariates=covariates, strata=strata, id_col=a.get("id") or None, sep=sep, decimal=dec, run_name=p.stem,
                       independent=_yes(a.get("independent")), groups=groups, encoding=encoding, language=a["lang"].lower(),
                       study={"data_name": a.get("data_name") or p.stem, "researcher": a.get("researcher") or None})
    if a.get("labels"):
        cfg["strata_labels"] = {k.strip(): v.strip() for k, v in (pair.split("=", 1) for pair in a["labels"].split(","))}
    return cfg


def _write(cfg: dict, out: Path) -> None:
    out.write_text(HEADER + yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")


# ----------------------------------------------------------------------------------------------------------- screen 4: suggestions
def _compact(variables, vec) -> str:
    return " · ".join(f"{v}^{x:+.2f}" for v, x in zip(variables, vec))


def _reading(variables, vec) -> str:
    """EN: plain words: which variables weigh most (|exponent|), which barely enter; positive = grows with, negative = decreases with."""
    order = sorted(zip(variables, vec), key=lambda kv: -abs(kv[1]))
    main = ", ".join(f"{v} ({x:+.2f})" for v, x in order if abs(x) >= 0.15)
    weak = ", ".join(v for v, x in order if abs(x) < 0.15)
    return t("st.reading", main=main or "—", weak=(t("st.reading_weak", list=weak) if weak else ""))


def suggestions(cfg: dict, printer: Callable[[str], None]) -> list[dict]:
    """
    EN: design one index per (target, stratum) on the design partition — the SAME function and partition the final run will use —
        and describe each one with numbers that come only from the design rows: vector, R², nearest published neighbour (Spearman
        on the design rows). No verdict is computed here.
    """
    from .config import resolve
    from .io import read_table
    from .run import _load_catalog, _values, design_all
    from scipy.stats import spearmanr
    rc = resolve(cfg)
    d = rc["data"]; cols = dict(d["columns"])
    if rc["strata"] is not None:
        cols["strata"] = rc["strata"]
    ds = read_table(d["path"], cols, sep=d["sep"], decimal=d["decimal"], encoding=d["encoding"], drop_nonpositive=d["drop_nonpositive"], min_n=d["min_n"], min_per_class=d["min_per_class"])
    tgt = ds.targets[0]; ctl = ds.controls[0]
    # EN: v1.2 — a class label cannot be designed (ln of a label); design only the continuous ones, refuse when none.
    cont = [x for x in (tgt, ctl) if ds.target_types.get(x) != "classification"]
    if not cont:
        printer(t("st.sug_class", names=", ".join(dict.fromkeys((tgt, ctl))))); return []
    rc["design"] = [{"target": x, "id": f"designed_{x}"} for x in cont]
    rc["data"]["columns"]["targets"] = {tgt: tgt, ctl: ctl}; rc["data"]["columns"]["controls"] = {ctl: ctl, tgt: tgt}
    warnings: list = []; manifest: dict = {}
    designed, audit_frame = design_all(rc, ds, ds.frame, warnings, manifest)
    cat = _load_catalog(rc)
    lab = {str(k): str(v) for k, v in (rc.get("strata_labels") or {}).items()}
    out = []
    for raw_key, dis in designed.items():
        st = lab.get(raw_key, raw_key)
        for did, di in dis.items():
            sp = di.split
            # EN: rows of the design partition of this stratum, taken from the frame the design saw (same order as `sub` inside design_all)
            need = manifest["design"]["columns_required"]
            has = np.ones(len(ds.frame), bool)
            for c in need:
                has &= np.isfinite(pd.to_numeric(ds.frame[c], errors="coerce").to_numpy(float))
            sub = ds.frame[has].reset_index(drop=True)
            fr = sub[sp.design].reset_index(drop=True)
            vals, _ = _values(cat, ds, fr)
            mine = di.values(fr)
            best, best_id = 0.0, None
            for mid, v in vals.items():
                ok = np.isfinite(v) & np.isfinite(mine)
                if ok.sum() >= 10:
                    rho = abs(float(spearmanr(v[ok], mine[ok]).statistic))
                    if rho > best:
                        best, best_id = rho, mid
            ps = manifest["design"]["indices"][did]["per_stratum"][st]
            out.append({"id": did, "target": di.target, "stratum": st, "raw_stratum": raw_key, "variables": list(di.variables), "vector": [float(x) for x in di.vector_design],
                        "vector_lo": None if di.vector_lo is None else [float(x) for x in di.vector_lo], "vector_hi": None if di.vector_hi is None else [float(x) for x in di.vector_hi],
                        "r2": float(di.r2_design), "n_design": ps["n_design"], "n_audit": ps["n_audit"], "neighbour": best_id, "rho": best,
                        "name": _suggest_name(di.target, st, tgt, ctl)})
    order = {tgt: 0, ctl: 1}
    out.sort(key=lambda sg: (order.get(sg["target"], 9), sg["stratum"]))
    return out


LEAN_KW = ("magra", "lean", "ffm", "lmi", "muscle", "muscul", "alm", "meso", "smm", "bcm", "cell")
FAT_KW = ("gord", "fat", "fmi", "fm_", "fm%", "endo", "adip", "grasa", "grass")


def _suggest_name(target: str, stratum: str, tgt: str, ctl: str) -> str:
    """EN: Zaku_LM / Zaku_FM when the target column name says lean or fat; otherwise Zaku_<column> (never a wrong guess)."""
    low = target.lower()
    if any(k in low for k in LEAN_KW): kind = "LM"
    elif any(k in low for k in FAT_KW) or low in ("fm", "fmp"): kind = "FM"
    else: kind = re.sub(r"[^A-Za-z0-9_]", "_", target)[:24]
    return f"Zaku_{kind}_{stratum}" if stratum != "all" else f"Zaku_{kind}"


def _print_suggestion(k: int, sg: dict, printer) -> None:
    printer(t("st.sug_head", k=k, t=sg["target"], s=sg["stratum"], n=sg["n_design"]))
    printer("  " + t("st.sug_formula", f=_compact(sg["variables"], sg["vector"]), r2=f"{sg['r2']:.2f}"))
    printer("  " + _reading(sg["variables"], sg["vector"]))
    if sg.get("vector_lo") and all(np.isfinite(sg["vector_lo"])):
        printer("  " + t("st.sug_ci", ci=" · ".join(f"{v} [{l:+.2f}; {h:+.2f}]" for v, l, h in zip(sg["variables"], sg["vector_lo"], sg["vector_hi"]))))
    if sg["neighbour"]:
        printer("  " + t("st.sug_neighbour", m=sg["neighbour"], rho=f"{sg['rho']:.2f}", note=(t("st.sug_repeats") if sg["rho"] >= 0.95 else t("st.sug_original"))))
    printer("  " + t("st.sug_name", name=sg["name"]))


def _too_small_for_design(cfg: dict) -> list[str]:
    """EN: the same rule `check` applies: the audit partition of every stratum must keep data.min_n rows; else no suggestion is shown."""
    from .config import resolve
    from .io import read_table
    rc = resolve(cfg); d = rc["data"]; cols = dict(d["columns"])
    if rc["strata"] is not None:
        cols["strata"] = rc["strata"]
    ds = read_table(d["path"], cols, sep=d["sep"], decimal=d["decimal"], encoding=d["encoding"], drop_nonpositive=d["drop_nonpositive"], min_n=d["min_n"], min_per_class=d["min_per_class"])
    tgt, ctl = ds.targets[0], ds.controls[0]; fr = 0.70
    if all(ds.target_types.get(x) == "classification" for x in (tgt, ctl)):
        return [t("st.sug_class", names=", ".join(dict.fromkeys((tgt, ctl))))]
    both = ds.frame[tgt].notna() & ds.frame[ctl].notna()
    counts = ds.frame[both].groupby(ds.strata).size() if ds.strata else pd.Series({"all": int(both.sum())})
    lab = {str(k): str(v) for k, v in (rc.get("strata_labels") or {}).items()}
    mo = int(rc["audit"]["bootstrap"]["min_oob"])
    out = []
    for g, n_g in counts.items():
        na = (1 - fr) * float(n_g)
        if na < d["min_n"]:
            out.append(t("c.design_too_small", s=lab.get(str(g), g), na=int(round(na)), m=d["min_n"]))
        elif 0.368 * na < mo:
            out.append(t("c.design_oob", s=lab.get(str(g), g), na=int(round(na)), oob=f"{0.368 * na:.0f}", m=mo))
    return out


def _answers_from_yaml(cfg: dict) -> dict:
    """EN: previous answers as suggestions for a new session on the same file (columns, units, study, strata, labels, groups)."""
    a: dict = {}
    c = (cfg.get("data") or {}).get("columns") or {}
    for k, v in (c.get("variables") or {}).items(): a[k] = v
    for k, v in (c.get("units") or {}).items(): a[f"{k}_unit"] = v
    if c.get("targets"): a["target"] = list(c["targets"].values())[0]
    if c.get("controls"): a["control"] = list(c["controls"].values())[0]
    if c.get("covariates") is not None: a["covariates"] = ",".join(c["covariates"])
    if cfg.get("strata"): a["strata"] = cfg["strata"]
    if cfg.get("strata_labels"): a["labels"] = ",".join(f"{k}={v}" for k, v in cfg["strata_labels"].items())
    if c.get("id"): a["id"] = c["id"]
    for role, g in GROUP_ROLES.items():
        if (c.get("groups") or {}).get(g): a[role] = c["groups"][g]
    st = cfg.get("study") or {}
    if st.get("data_name"): a["data_name"] = st["data_name"]
    if st.get("researcher"): a["researcher"] = st["researcher"]
    if cfg.get("language"): a["lang"] = cfg["language"]
    decl = (cfg.get("declarations") or {}).get("targets_independent_of_variables")
    if decl is not None: a["independent"] = "yes" if decl else "no"
    return a


def _screen_4(cfg: dict, ask, printer, accept_all: bool) -> tuple[list[dict], list[dict]]:
    """EN: returns (design specs accepted with their names, proposed entries from edited exponents)."""
    blocked = _too_small_for_design(cfg)
    if blocked:
        printer(t("st.blocked_sug"))
        for msg in blocked:
            printer("  ✗ " + msg)
        return [], []
    sugs = suggestions(cfg, printer)
    specs: dict[str, dict] = {}; proposed: list[dict] = []
    for k, sg in enumerate(sugs, 1):
        _print_suggestion(k, sg, printer)
        if accept_all or ask is None:
            ans = "yes"
        else:
            while True:
                ans = (ask(t("st.accept"), "yes") or "yes").strip().lower()
                if ans in ("yes", "y", "sim", "sí", "si", "s", "edit", "e", "editar", "no", "n", "não", "nao"):
                    break
                printer(t("st.yesno_bad"))
        name = sg["name"]; vec = list(sg["vector"])
        if ans in ("no", "n", "não", "nao"):
            printer("  " + t("st.discarded")); continue
        if ans in ("edit", "e", "editar"):
            name = (ask(t("st.edit_name", name=name), name) or name).strip() or name
            raw = (ask(t("st.edit_round"), "") or "").strip()
            if raw:
                try:
                    nd = int(raw); vec = [round(x, nd) for x in vec]
                except ValueError:
                    printer(t("st.edit_round_bad")); vec = list(sg["vector"])
            if vec != list(sg["vector"]):
                expr = " * ".join(f"{v}**({x})" for v, x in zip(sg["variables"], vec))
                proposed.append({"id": name, "label": f"{name} ({sg['stratum']}; rounded from the design)", "authors": (cfg.get("study") or {}).get("researcher") or "author",
                                 "target": sg["target"], "form": "monomial", "expr": expr, "vector": {v: x for v, x in zip(sg["variables"], vec)},
                                 "provenance": {"formula_source": "proposed", "note": t("st.note_rounded", d=datetime.date.today().isoformat(), s=sg["stratum"])}})
                printer("  " + t("st.became_proposed", name=name)); continue
        # EN: accepted as designed: one design spec per target; the name applies to the index (all strata share the id)
        spec = specs.setdefault(sg["target"], {"target": sg["target"], "id": name.rsplit("_", 1)[0] if sg["stratum"] != "all" and name.endswith("_" + sg["stratum"]) else name})
        printer("  " + t("st.accepted", name=spec["id"]))
    return list(specs.values()), proposed


# ----------------------------------------------------------------------------------------------------------- the guided path
def start(csv: str, out: str | None = None, *, ask: Callable[[str, str | None], str] | None = None, map_flags: dict[str, str] | None = None,
          yes: bool = False, sep: str = "auto", decimal: str = "auto", encoding: str = "utf-8", printer: Callable[[str], None] = print,
          lang: str | None = None, runner: Callable | None = None) -> Path:
    """
    EN: the guided path. `ask` = None with `map_flags` → scripted (no questions). `runner` (default: run.run) receives the YAML path.
    """
    from .run import run as _run_cfg
    from .check import CheckError, check
    runner = runner or (lambda path: _run_cfg(str(path), printer=printer, preflight=False))   # EN: the check is printed once, by start
    p = Path(csv)
    if not p.exists():
        raise InputError(f"{p}: not found")
    answers: dict = dict(map_flags or {})
    outp = Path(out) if out else p.with_suffix(".zaku.yaml")
    previous = yaml.safe_load(outp.read_text(encoding="utf-8")) if outp.exists() else None    # EN: a previous session on this file
    if previous and not answers:
        answers.update(_answers_from_yaml(previous))
        printer(t("st.existing", out=outp))
    if ask is not None and not map_flags:
        from .banner import banner
        printer(banner(full=False))
    # ---- screen 1
    _screen_1(ask, printer, answers, lang or answers.get("lang"), p)
    if sep != "auto" and decimal != "auto":
        df = pd.read_csv(p, sep=sep, decimal=decimal, encoding=encoding); s_, d_ = sep, decimal
    else:
        df, s_, d_ = detect(p, encoding)
    cols = [str(c).strip() for c in df.columns]; numeric = [c for c, raw in zip(cols, df.columns) if pd.api.types.is_numeric_dtype(df[raw])]
    printer(t("w.file", name=p.name, rows=len(df), cols=len(cols), sep=repr(s_), dec=repr(d_))); printer(t("w.numeric", cols=", ".join(numeric)))
    if ask is not None:
        printer(""); printer(t("st.nav")); printer("")
    # ---- screen 2
    _screen_2(ask, printer, answers, cols, numeric)
    cfg = _config_from_answers(p, answers, s_, d_, encoding, cols)
    cfg["run_name"] = outp.name.split(".")[0]
    prev_own = [e for e in ((previous or {}).get("catalog") or {}).get("user_entries") or [] if isinstance(e, dict)]
    if prev_own and (ask is None or _ask_yes_no(ask, printer, t("st.keep_own", n=len(prev_own), out=outp, ids=", ".join(e["id"] for e in prev_own)), "yes")):
        cfg["catalog"] = {"include": ["curated"] + [e["id"] for e in prev_own], "user_entries": prev_own}   # EN: never lose typed formulas silently
    _write(cfg, outp); printer(t("st.wrote", out=outp))
    # ---- screen 3: the standard run
    printer(""); printer(t("st.run_std"))
    try:
        check(str(outp), printer=printer)
    except CheckError:
        raise InputError(t("st.check_failed", out=outp)) from None
    runner(outp)
    # ---- screen 4: suggestions?
    want = yes or (ask is not None and _ask_yes_no(ask, printer, t("st.want_sug"), "no"))
    specs, proposed = ([], [])
    if want:
        printer(t("st.sug_intro"))
        if not _yes(answers.get("independent")):
            printer(t("c.design_decl")); want = False
        else:
            specs, proposed = _screen_4(cfg, ask, printer, accept_all=yes)
    # ---- screen 5: own index?
    own = False
    if ask is not None and not yes and _ask_yes_no(ask, printer, t("st.want_own"), "no"):
        from .propose import propose
        propose(outp, ask=ask, printer=printer, lang=answers["lang"].lower())
        own = True
    if not (specs or proposed or own):
        printer(t("st.done_std", out=outp)); return outp
    # ---- final run: published + accepted + own, validated on the never-seen rows
    cfg = yaml.safe_load(outp.read_text(encoding="utf-8"))
    if specs:
        tgt = answers["target"]; ctl = answers["control"]
        cfg["design"] = specs
        cfg["data"]["columns"]["targets"] = {tgt: tgt, ctl: ctl}; cfg["data"]["columns"]["controls"] = {ctl: ctl, tgt: tgt}
        cfg["data"]["columns"]["pairing"] = {tgt: ctl, ctl: tgt}
    if proposed:
        cat = cfg.setdefault("catalog", {"include": "curated"})
        inc = cat.get("include", "curated"); inc = [inc] if isinstance(inc, str) else list(inc)
        cat["user_entries"] = list(cat.get("user_entries") or []) + proposed
        cat["include"] = inc + [e["id"] for e in proposed if e["id"] not in inc]
    _write(cfg, outp); printer(""); printer(t("st.run_final", out=outp))
    try:
        check(str(outp), printer=printer)                  # EN: the configuration changed (design, pairing, own indices): checked again before running
    except CheckError:
        raise InputError(t("st.check_failed", out=outp)) from None
    runner(outp)
    printer(t("st.done_expert", out=outp))
    return outp


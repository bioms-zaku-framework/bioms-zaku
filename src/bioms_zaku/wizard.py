"""
EN: `bioms-zaku init` — build a configuration from a CSV, interactively or from explicit flags. Suggests, never decides:
    every column assignment is confirmed by the user (or given explicitly with --map). Writes a commented YAML.
ES: `init` — construye la configuración desde un CSV; sugiere, nunca decide.
PT: `init` — constrói a configuração a partir de um CSV; sugere, nunca decide.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

import pandas as pd
import yaml

from .i18n import LANGS, set_language, t
from .io import SEP_DECIMAL_TRIALS, InputError

# EN: name patterns used only to SUGGEST a column for each role (case-insensitive). ES/PT: padrões só para sugerir.
SUGGEST = {
    "R": r"^(r|res|resist|resistance|resistencia|resistência)(_?ohm|50|_50)?$|resist",
    "Xc": r"^(xc|react|reactance|reatancia|reatância|reactancia)(_?ohm|50|_50)?$|react|reat|reatt",
    "H": r"^(h|ht|height|estatura|altura|talla|stature)(_?cm|_?m)?$|height|estatura|altura|talla",
    "W": r"^(w|wt|weight|peso|massa|mass|masa|body_?mass|bodymass)(_?(corporal|corporea|body|total))?(_?kg)?$|weight|peso|massa|mass|body_?mass",
    "strata": r"^(sex|sexo|gender|genero|género)(_.*)?$",
    "id": r"^(id|seqn|subject|participant|paciente|patient)(_.*)?$",
    # EN: optional columns that the catalogue EQUATIONS need (age, sex, circumferences); suggested, never assumed
    "sex": r"^(sex|sexo|gender|genero|género)(_.*)?$",
    "age": r"^(age|idade|edad|years|anos|años)(_.*)?$|^age|^idade|^edad",
    "arm": r"arm|braco|braço|brazo",
    "waist": r"waist|cintura",
    "calf": r"calf|panturrilha|pantorrilla",
}
# EN: role flag → column name inside the catalogue (inputs of the equations)
GROUP_ROLES = {"sex": "sexo", "age": "idade", "arm": "C_arm", "waist": "C_waist", "calf": "C_calf"}


def detect(path: Path, encoding: str = "utf-8") -> tuple[pd.DataFrame, str, str]:
    """EN: same fixed-order detection as the input contract (§1.2), on all columns. ES/PT: mesma detecção do contrato."""
    try:
        text = path.read_text(encoding=encoding).lstrip("﻿")
    except UnicodeDecodeError as e:
        raise InputError(t("w.decode", name=path.name, enc=encoding, err=e)) from None
    valid = []
    for s, d in SEP_DECIMAL_TRIALS:
        try:
            df = pd.read_csv(pd.io.common.StringIO(text), sep=s, decimal=d, engine="python")
        except Exception:
            continue
        if len(df.columns) >= 2:
            num = sum(pd.api.types.is_numeric_dtype(df[c]) for c in df.columns)
            valid.append((num, s, d, df))
    if not valid:
        raise InputError(t("w.noparse"))
    valid.sort(key=lambda t: -t[0])
    if len(valid) > 1 and valid[0][0] == valid[1][0]:
        raise InputError(t("w.ambig", pairs=[(v[1], v[2]) for v in valid[:2]]))
    num, s, d, df = valid[0]
    return df, s, d


def suggest(columns: list[str]) -> dict[str, str | None]:
    """EN: suggest a column per role only when unambiguous. Two tiers: an ANCHORED match on the whole name (e.g. massa_corporal_kg)
    wins over loose matches (massa_magra_dxa_kg also contains 'massa'); if no tier gives exactly one hit, no suggestion."""
    out: dict[str, str | None] = {}
    for role, pat in SUGGEST.items():
        anchored = pat.split("|^")[0] if pat.startswith("^") else None
        strict = [c for c in columns if anchored and re.fullmatch(anchored.lstrip("^").rstrip("$"), str(c).strip().lower())]
        loose = [c for c in columns if re.search(pat, str(c).strip().lower())]
        out[role] = strict[0] if len(strict) == 1 else (loose[0] if len(loose) == 1 else None)
    return out


def build_config(csv: Path, mapping: dict[str, str], *, units: dict[str, str], targets: dict[str, str], controls: dict[str, str],
                 covariates: list[str], strata: str | None, id_col: str | None, sep: str, decimal: str, run_name: str,
                 preset: str = "full", independent: bool = False, groups: dict[str, str] | None = None, encoding: str = "utf-8", language: str = "en") -> dict:
    cfg = {
        "run_name": run_name,
        "language": language,
        "data": {"path": str(csv), "sep": sep, "decimal": decimal, "encoding": encoding,
                 "columns": {"variables": {k: mapping[k] for k in ("R", "Xc", "H", "W") if k in mapping},
                             "units": units, "targets": targets, "controls": controls, "covariates": covariates,
                             "groups": dict(groups or {}), "id": id_col}},
        "strata": strata,
        # EN: CURATED methods only (the ones whose primary source was read and approved; §2.1). "all" audits the non-curated
        #     equations too, marked * in every output. This is a design decision, written in the YAML so the user sees it.
        "catalog": {"include": "curated"},
        "declarations": {"targets_independent_of_variables": bool(independent)},
        "preset": preset,
        "output": {"dir": "./zaku_out", "figures": True},
    }
    if strata and "sexo" not in cfg["data"]["columns"]["groups"]:
        cfg["data"]["columns"]["groups"]["sexo"] = strata
    return cfg


HEADER = """# BioMS Zaku configuration — generated by `bioms-zaku init`. Edit freely; run `bioms-zaku check` before `run`.
# EN: `declarations.targets_independent_of_variables` must be true only if NO target/control is computed from the mapped variables.
# ES: debe ser true solo si NINGÚN objetivo/control se calcula a partir de las variables mapeadas.
# PT: deve ser true só se NENHUM alvo/controle é calculado a partir das variáveis mapeadas.
# catalog.include: "curated" = only methods whose primary source was critically read (default); "all" = every catalogue
#   entry, including predictive equations not yet curated (marked * in the outputs); or a list of method ids.
"""


def init(csv: str, out: str | None = None, *, ask: Callable[[str, str | None], str] | None = None, map_flags: dict[str, str] | None = None,
         sep: str = "auto", decimal: str = "auto", encoding: str = "utf-8", printer: Callable[[str], None] = print, lang: str | None = None) -> Path:
    """
    EN: interactive when `ask` is given; otherwise fully specified by `map_flags` (R, Xc, H, W, H_unit, W_unit, target, control,
        covariates (comma list), strata, id, independent (yes/no), and the optional equation inputs sex, age, arm, waist, calf).
        Never guesses silently.
    ES/PT: interativo com `ask`; senão, totalmente especificado por `map_flags`. Nunca adivinha em silêncio.
    """
    p = Path(csv)
    # EN: language first — asked interactively when not given, so every later prompt is already in that language
    lang_origin = "flag" if lang else ("flag" if (map_flags or {}).get("lang") else "default")
    if lang is None and ask is not None:
        a = (ask("Language / Idioma / Língua / Lingua — en (English) · es (Español) · pt (Português) · it (Italiano) [en]", "en") or "").strip().lower()
        lang, lang_origin = (a or "en"), ("answer" if a else "default")
    lang = set_language(lang or (map_flags or {}).get("lang") or "en")
    if sep != "auto" and decimal != "auto":
        df = pd.read_csv(p, sep=sep, decimal=decimal, encoding=encoding); s, d = sep, decimal
    else:
        df, s, d = detect(p, encoding)
    cols = [str(c).strip() for c in df.columns]
    numeric = [c for c, raw in zip(cols, df.columns) if pd.api.types.is_numeric_dtype(df[raw])]
    printer(t("w.file", name=p.name, rows=len(df), cols=len(cols), sep=repr(s), dec=repr(d)))
    printer(t("w.numeric", cols=", ".join(numeric)))
    def help_(key: str) -> None:   # EN: one explanatory line before a question, interactive mode only
        if ask is not None:
            printer(t(key))
    if ask is not None:
        printer(""); printer(t("w.intro")); printer("")
    sug = suggest(cols)
    flags = dict(map_flags or {})
    origin: dict[str, str] = {}   # EN: role -> "flag" | "answer" | "suggested" | "default"; printed at the end so nothing is silent

    def get(role: str, prompt: str, default: str | None, required: bool = True) -> str | None:
        if role in flags:
            v = flags[role]; origin[role] = "flag"
            if str(v).strip().lower() in ("none", "-"):
                return None                      # EN: explicit refusal of a suggestion
        elif ask is not None:
            v = ask(prompt + (f" [{default}]" if default else ""), default); origin[role] = "answer" if (v or "").strip() else "suggested"
        else:
            v = default; origin[role] = "suggested" if default else "default"
        v = (v or "").strip() or (default or "")
        if required and not v:
            raise InputError(t("w.required", role=role))
        return v or None

    def col(role: str, prompt: str, required: bool = True, default: str | None = None) -> str | None:
        d = default if default is not None else sug.get(role)
        for attempt in range(3):
            v = get(role, prompt, d, required)
            if not v or v in cols:
                return v
            if ask is None or role in flags:
                raise InputError(t("w.notin", role=role, col=repr(v), cols=cols))
            printer(t("w.notin_again", col=repr(v), cols=", ".join(cols)))   # EN: interactive: ask again, never abort on a typo
        raise InputError(t("w.noattempts", role=role))

    help_("w.help.vars")
    mapping = {r: col(r, t("w.col_for", role=r, meaning=t(f"w.mean.{r}"))) for r in ("R", "Xc", "H", "W")}
    units = {"H": get("H_unit", t("w.unit_H"), "cm"), "W": get("W_unit", t("w.unit_W"), "kg")}
    if units["H"] not in ("cm", "m") or units["W"] not in ("kg", "g"):
        raise InputError(t("w.units_bad"))
    help_("w.help.target")
    tgt = col("target", t("w.target"))
    help_("w.help.control")
    for attempt in range(3):
        c = col("control", t("w.control"))
        if c != tgt:
            break
        if ask is None or "control" in flags:
            raise InputError(t("w.control_same", col=repr(c)))
        printer(t("w.control_same_again", col=repr(c)))
    else:
        raise InputError(t("w.control_3"))
    help_("w.help.cov")
    cov = get("covariates", t("w.covariates"), f"{mapping['W']},{mapping['H']}", required=False)
    covariates = [x.strip() for x in (cov or "").split(",") if x.strip()]
    for x in covariates:
        if x not in cols:
            raise InputError(t("w.cov_notin", col=repr(x)))
    help_("w.help.strata")
    strata = col("strata", t("w.strata"), required=False)
    help_("w.help.id")
    id_col = col("id", t("w.id"), required=False)
    # EN: optional columns the catalogue equations need; empty = not mapped (check will list which methods are skipped and why)
    groups: dict[str, str] = {}
    help_("w.help.groups")
    for role, gname in GROUP_ROLES.items():
        v = col(role, t("w.group_col", role=f"{role} ({t('w.role.' + role)})"), required=False,
                default=(strata if role == "sex" and strata else None))
        if v:
            groups[gname] = v
    help_("w.help.indep")
    indep_raw = get("independent", t("w.independent"), "no") or "no"
    indep = indep_raw.lower() in ("yes", "y", "sim", "sí", "si", "true")
    tname = re.sub(r"\W+", "_", tgt).upper(); cname = re.sub(r"\W+", "_", c).upper()
    cfg = build_config(p, mapping, units=units, targets={tname: tgt}, controls={cname: c}, covariates=covariates, strata=strata, id_col=id_col,
                       sep=s, decimal=d, run_name=p.stem, independent=indep, groups=groups, encoding=encoding, language=lang)
    outp = Path(out) if out else p.with_suffix(".zaku.yaml")
    cfg["run_name"] = outp.name.split(".")[0]   # EN: the run is named after the YAML, not the CSV: two analyses of one file get two folders
    outp.write_text(HEADER + yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    printer(t("w.mapping"))
    printer(f"  {t('w.lang_shown'):11s} ← {lang}   [{t('w.origin.' + lang_origin)}]")
    for role, v in (("R", mapping["R"]), ("Xc", mapping["Xc"]), ("H", mapping["H"]), ("W", mapping["W"]), ("target", tgt), ("control", c),
                    ("covariates", ",".join(covariates) or None), ("strata", strata), ("id", id_col),
                    *[(r, groups.get(g)) for r, g in GROUP_ROLES.items()], ("independent", "yes" if indep else "no")):
        printer(f"  {role:11s} ← {v if v else t('w.not_mapped')}" + (f"   [{t('w.origin.' + origin[role])}]" if v and role in origin else ""))
    if not indep:
        printer(t("w.indep_no"))
    printer(t("w.catalogue"))
    printer(t("w.wrote", out=outp))
    return outp

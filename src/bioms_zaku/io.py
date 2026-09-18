"""
EN: Input contract (CONTRATOS.md §1): reading, separator/decimal detection, column mapping, validation, derived variables.
"""
from __future__ import annotations

import io as _io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# EN: fixed trial order (§1.2). ES: orden fijo de prueba. PT: ordem fixa de tentativa.
SEP_DECIMAL_TRIALS: tuple[tuple[str, str], ...] = ((",", "."), (";", ","), (";", "."), ("\t", "."), ("\t", ","))
UNIT_FACTORS = {("H", "cm"): 1.0, ("H", "m"): 100.0, ("W", "kg"): 1.0, ("W", "g"): 0.001}
DEFAULT_FREQ_KHZ = 50.0


class InputError(ValueError):
    """EN: input contract violation. ES: violación del contrato de entrada. PT: violação do contrato de entrada."""


@dataclass
class Mapping:
    """
    EN: user's column mapping (§1.3). Keys are canonical names; values are column names in the file.
    """
    variables: dict[str, str]
    targets: dict[str, str]
    controls: dict[str, str]
    units: dict[str, str] = field(default_factory=dict)
    frequency_khz: dict[str, float] = field(default_factory=dict)
    pairing: dict[str, str] = field(default_factory=dict)
    covariates: list[str] = field(default_factory=list)
    strata: str | None = None
    groups: dict[str, str] = field(default_factory=dict)
    id: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Mapping":
        d = dict(d)
        for k in ("variables", "targets", "controls"):
            if k not in d or not isinstance(d[k], dict) or not d[k]:
                raise InputError(f"columns.{k} is required and must be a non-empty mapping")
        return cls(variables=dict(d["variables"]), targets=dict(d["targets"]), controls=dict(d["controls"]),
                   units=dict(d.get("units") or {}), frequency_khz={k: float(v) for k, v in (d.get("frequency_khz") or {}).items()},
                   pairing=dict(d.get("pairing") or {}), covariates=list(d.get("covariates") or []),
                   strata=d.get("strata"), groups=dict(d.get("groups") or {}), id=d.get("id"))


@dataclass
class Dataset:
    """
    EN: validated data in canonical names + bookkeeping for the manifest. Never exposes row-level data in outputs.
    """
    frame: pd.DataFrame                  # canonical columns: variables (+derived), targets, controls, covariates, strata, groups, id
    variables: list[str]
    derived: list[str]
    targets: list[str]
    controls: list[str]
    pairing: dict[str, str]
    covariates: list[str]
    strata: str | None
    groups: list[str]
    id: str | None
    target_types: dict[str, str]         # "regression" | "classification"
    info: dict[str, Any]                 # sep_used, decimal_used, encoding_used, rows_in, rows_dropped {...}, warnings [...]


# ----------------------------------------------------------------------------------------------
def read_table(source: str | os.PathLike | pd.DataFrame, mapping: Mapping | dict, *, sep: str = "auto",
               decimal: str = "auto", encoding: str = "utf-8", drop_nonpositive: bool = False,
               min_n: int = 30, min_per_class: int = 20) -> Dataset:
    """
    EN: Read a CSV/TSV or DataFrame, apply the mapping, validate (§1.4), derive variables. Fails early with named columns/rows.
    """
    m = mapping if isinstance(mapping, Mapping) else Mapping.from_dict(mapping)
    info: dict[str, Any] = {"warnings": [], "rows_dropped": {}}
    needed_cols = _needed_columns(m)

    if isinstance(source, pd.DataFrame):
        df = source.copy()
        info.update(sep_used=None, decimal_used=None, encoding_used=None, input_path=None)
    else:
        text = _read_text(Path(source), encoding)
        numeric_cols = list(m.variables.values()) + list(m.targets.values()) + list(m.controls.values())
        df, sep_used, dec_used = _parse_with_detection(text, needed_cols, numeric_cols, sep, decimal)
        info.update(sep_used=sep_used, decimal_used=dec_used, encoding_used=encoding, input_path=str(source))

    if df.columns.duplicated().any():
        raise InputError(f"duplicated column names: {sorted(set(df.columns[df.columns.duplicated()]))}")
    stripped = {c: c.strip() for c in df.columns if isinstance(c, str) and c != c.strip()}
    if stripped:
        df = df.rename(columns=stripped); info["warnings"].append(f"stripped whitespace from column names: {sorted(stripped)}")
    missing = [c for c in needed_cols if c not in df.columns]
    if missing:
        raise InputError(f"mapped columns not found in input: {missing}")
    info["rows_in"] = int(len(df))

    # EN: build canonical frame. ES: construye el marco canónico. PT: monta a tabela canônica.
    out = pd.DataFrame(index=df.index)
    var_names: list[str] = []
    for canon, col in m.variables.items():
        name = _canonical_variable_name(canon, m.frequency_khz.get(canon))
        vals = pd.to_numeric(df[col], errors="coerce")
        bad = ~np.isfinite(vals.to_numpy(dtype=float)) & df[col].notna().to_numpy()
        if bad.any():
            raise InputError(f"column {col!r} ({name}): non-numeric values at rows {_rows(df.index[bad])}")
        factor = _unit_factor(canon, m.units)
        out[name] = vals * factor
        var_names.append(name)
    for canon, col in {**m.targets, **m.controls}.items():
        out[canon] = pd.to_numeric(df[col], errors="coerce")
        bad = ~np.isfinite(out[canon].to_numpy(dtype=float)) & df[col].notna().to_numpy()
        if bad.any():
            raise InputError(f"column {col!r} ({canon}): non-numeric values at rows {_rows(df.index[bad])}")
    for col in m.covariates:
        out[col] = pd.to_numeric(df[col], errors="coerce")
    for canon, col in m.groups.items():
        out[canon] = df[col]
    if m.strata:
        out[m.strata] = df[m.strata]
    if m.id:
        out[m.id] = df[m.id]

    # EN: positivity (§1.4). ES: positividad. PT: positividade.
    V = out[var_names].to_numpy(dtype=float)
    nonpos = np.zeros(len(out), dtype=bool)
    present = ~np.isnan(V)
    nonpos[present.any(axis=1)] = ((V <= 0) & present)[present.any(axis=1)].any(axis=1)
    if nonpos.any():
        if not drop_nonpositive:
            raise InputError(f"non-positive values in variables {var_names} at rows {_rows(out.index[nonpos])}; "
                             f"logarithms require > 0 (set drop_nonpositive=True to drop them)")
        info["rows_dropped"]["nonpositive"] = int(nonpos.sum())
        info["warnings"].append(f"dropped {int(nonpos.sum())} rows with non-positive variables")
        out = out.loc[~nonpos]
    miss_var = out[var_names].isna().any(axis=1)
    info["rows_dropped"]["missing_variables_algebra"] = int(miss_var.sum())   # EN: excluded from algebra only

    # EN: derived variables (§1.3). ES: derivadas. PT: derivadas.
    derived: list[str] = []
    if {"R", "Xc", "H", "W"} <= set(var_names):
        out["H_m"] = out["H"] / 100.0
        out["PhA"] = np.degrees(np.arctan(out["Xc"] / out["R"]))
        out["II"] = out["H"] ** 2 / out["R"]
        out["Z"] = np.sqrt(out["R"] ** 2 + out["Xc"] ** 2)
        derived = ["H_m", "PhA", "II", "Z"]

    # EN: targets/controls typing and pairing. ES: tipos y emparejamiento. PT: tipos e pareamento.
    ttypes: dict[str, str] = {}
    for name in list(m.targets) + list(m.controls):
        ttypes[name] = _target_type(out[name], name)
    pairing = dict(m.pairing) or {t: next(iter(m.controls)) for t in m.targets}
    for t, c in pairing.items():
        if t not in m.targets or c not in m.controls:
            raise InputError(f"pairing {t!r} -> {c!r}: unknown target or control")
        # EN: v1.2 — a class target may be paired with a continuous control (and vice versa): gains in Tjur's D and in R² live
        #     on the same explained-variation scale (Tjur 2009), so no type restriction (decision of 2026-09-16).
    for name in list(m.targets) + list(m.controls):
        info["rows_dropped"][f"missing_{name}"] = int(out[name].isna().sum())
    # EN: rows with a missing value in a mapped column are excluded and counted per reason (above); results describe the
    #     people who remain. No imputation, no comparison with the excluded rows: the framework describes the analysed
    #     sample, it does not estimate a population (decision of 2026-09-16).
    # EN: strata / class minimums. ES: mínimos por estrato/clase. PT: mínimos por estrato/classe.
    if m.strata:
        counts = out[m.strata].value_counts(dropna=False)
        small = counts[counts < min_n]
        if len(small):
            info["warnings"].append(f"strata ignored (n < {min_n}): {dict(small)}")
            out = out[~out[m.strata].isin(small.index)]
    for name, tt in ttypes.items():
        if tt == "classification":
            groups = [out] if not m.strata else [g for _, g in out.groupby(m.strata)]
            for g in groups:
                vc = g[name].dropna().value_counts()
                if len(vc) and vc.min() < min_per_class:
                    info["warnings"].append(f"{name}: a class has < {min_per_class} cases in a stratum; audit will skip it there")
    if m.id and out[m.id].duplicated().any():
        # EN: v1.2 (decision of 2026-09-16): one row per person. The bootstrap resamples rows as independent persons, so repeated
        #     measurements would give intervals that are too narrow; a cluster bootstrap (Field & Welsh 2007) is future work.
        dup = out.loc[out[m.id].duplicated(), m.id].nunique()
        raise InputError(f"repeated id in {m.id!r} ({dup} ids with more than one row): the audit needs ONE row per person — "
                         f"aggregate repeated measurements (e.g. the mean per person, or one visit) before running")
    info["rows_out"] = int(len(out))
    out = out.reset_index(drop=True)
    return Dataset(frame=out, variables=var_names, derived=derived, targets=list(m.targets), controls=list(m.controls),
                   pairing=pairing, covariates=list(m.covariates), strata=m.strata, groups=list(m.groups), id=m.id,
                   target_types=ttypes, info=info)


# ----------------------------------------------------------------------------------------------
def _needed_columns(m: Mapping) -> list[str]:
    cols = list(m.variables.values()) + list(m.targets.values()) + list(m.controls.values()) + list(m.covariates) + list(m.groups.values())
    if m.strata: cols.append(m.strata)
    if m.id: cols.append(m.id)
    return list(dict.fromkeys(cols))


def _read_text(path: Path, encoding: str) -> str:
    try:
        return path.read_text(encoding=encoding)   # EN: strict decoding — errors raise, never replaced silently
    except UnicodeDecodeError as e:
        raise InputError(f"cannot decode {path} as {encoding}: {e}. Pass encoding='latin-1' or 'cp1252' if appropriate.") from None


def _parse_with_detection(text: str, needed_cols: list[str], numeric_cols: list[str], sep: str, decimal: str):
    """
    EN: §1.2 — try fixed (sep, decimal) pairs; exactly one valid → use it; else error.
    """
    text = text.lstrip("﻿")
    if sep != "auto" and decimal != "auto":
        return pd.read_csv(_io.StringIO(text), sep=sep, decimal=decimal), sep, decimal
    if sep != "auto" or decimal != "auto":
        raise InputError("pass both sep and decimal, or leave both as 'auto'")
    valid = []
    for s, d in SEP_DECIMAL_TRIALS:
        try:
            df = pd.read_csv(_io.StringIO(text), sep=s, decimal=d, engine="python")
        except Exception:
            continue
        # (a) same number of columns in every line: the python engine raises on ragged rows; (b) mapped columns present
        df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
        if len(df.columns) < 2 or not all(c in df.columns for c in needed_cols):
            continue
        # (b) every mapped numeric column must convert without error under this (sep, decimal)
        try:
            for c in numeric_cols:
                col = df[c]
                if col.dtype == object:
                    pd.to_numeric(col.dropna().astype(str).str.strip(), errors="raise")
        except (ValueError, TypeError):
            continue
        valid.append((s, d, df))
    if len(valid) == 1:
        s, d, df = valid[0]
        return df, s, d
    if not valid:
        raise InputError("could not detect separator/decimal: no (sep, decimal) pair yields all mapped columns; pass sep= and decimal= explicitly")
    raise InputError(f"ambiguous separator/decimal: {[(s, d) for s, d, _ in valid]} all parse; pass sep= and decimal= explicitly")


def _canonical_variable_name(canon: str, freq: float | None) -> str:
    # EN: R/Xc at 50 kHz keep the bare name; other frequencies get the kHz suffix (§0, §1.3).
    if canon in ("R", "Xc"):
        f = DEFAULT_FREQ_KHZ if freq is None else float(freq)
        if f == DEFAULT_FREQ_KHZ:
            return canon
        return f"{canon}{int(f) if float(f).is_integer() else f}"
    return canon


def _unit_factor(canon: str, units: dict[str, str]) -> float:
    if canon in ("H", "W"):
        if canon not in units:
            raise InputError(f"units.{canon} is required ({'cm|m' if canon == 'H' else 'kg|g'})")
        key = (canon, units[canon])
        if key not in UNIT_FACTORS:
            raise InputError(f"unsupported unit {units[canon]!r} for {canon}; allowed: {[u for (c, u) in UNIT_FACTORS if c == canon]}")
        return UNIT_FACTORS[key]
    return 1.0


def _target_type(s: pd.Series, name: str) -> str:
    v = s.dropna().unique()
    if len(v) == 0:
        raise InputError(f"target/control {name!r} has no values")
    if len(v) <= 10 and np.all(np.mod(v, 1) == 0):
        if len(v) < 2:
            raise InputError(f"target/control {name!r} has a single value")
        return "classification"
    return "regression"


def _rows(idx) -> str:
    idx = list(idx)
    return str(idx[:10]) + (f" … (+{len(idx) - 10})" if len(idx) > 10 else "")

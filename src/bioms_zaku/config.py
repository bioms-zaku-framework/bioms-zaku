"""
EN: Run configuration (CONTRATOS.md §3): defaults = `full` preset; `quick` preset for examples/tests; resolved config
    is what the manifest records.
ES: Configuración de ejecución: valores por defecto = preset `full`; `quick` para ejemplos/pruebas.
PT: Configuração de execução: padrões = preset `full`; `quick` para exemplos/testes.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "run_name": "run",
    "data": {"path": None, "encoding": "utf-8", "sep": "auto", "decimal": "auto", "columns": {},
             "drop_nonpositive": False, "impute": False, "max_missing_frac_warn": 0.10, "min_n": 30, "min_per_class": 20},
    "catalog": {"path": "builtin", "include": "all", "exclude": [], "user_entries": []},
    "strata": None,
    "strata_labels": {},   # EN: optional display names for stratum values, e.g. {0: F, 1: M}
    "algebra": {"fit_affine": True, "extra_log_variables": [], "min_fit_r2": 0.90, "redundancy_threshold": 0.95,
                "min_pair_n": 30, "transfer": True, "fisher_alpha": 0.05,
                "transfer_tol": 0.05, "transfer_B": 200},   # EN: v0.5 Σ-transfer: fixed tolerance and person-bootstrap size
    "audit": {"task": "auto",
              "single": {"estimator": "ridge", "params": {"alpha": 1.0}},
              "combination": {"estimator": "hgb", "params": {"max_depth": 3, "learning_rate": 0.05, "max_iter": 300}},
              "sensitivity": {"estimator": None, "params": {}, "nested_tuning": False},
              "cv": {"folds": 5, "repeats": 50, "stratified": "auto"},
              "bootstrap": {"B": 2000, "min_oob": 20, "max_attempts_factor": 6},
              "utility_margin": 0.03, "verdict": {"p_specific": 0.95, "p_control": 0.05, "ci": 0.95, "margin": 0.03,
                          "sensitivity_margins": [0.02, 0.03, 0.05], "sensitivity_p": [0.90, 0.95, 0.99]},   # EN: v0.5 verdict margin + threshold grid (v0.5.1)
              "multiplicity": "none", "combinations": False},
    "design": None,
    "declarations": {"targets_independent_of_variables": None,
                     "target_kinds": {}},   # EN: optional {column: lean_mass|fat_mass|body_water|hydration|cell_mass|other} for targets/controls   # EN: circularity rule (contract v0.4.3); required true with design   # {"target": ..., "split": "holdout", "fraction": 0.70, "seed": 42, "id": "designed_<target>"}
    "seeds": {"cv": 42, "bootstrap": 42},
    "preset": "full",
    "threads": 1,
    "n_jobs": 1,
    "output": {"dir": "./zaku_out", "figures": True, "supplementary_figures": False, "format": "csv"},
    # EN: figure customisation (all optional). language: en | es | pt (axis labels, legends, captions).
    # ES/PT: personalização das figuras (tudo opcional).
    "figures": {"title": None, "subtitle": None, "language": "en", "labels": "full",   # labels: full | short (author year)
                "palette": "default",   # "default" (validated blue/orange) | "brand" (BioMS violet/green) | {specific:, control:, muted:}
                "font": "DejaVu Sans", "font_size": 8.5, "dpi": 300, "formats": ["png", "pdf"], "footer": True,
                "captions": False},   # EN: in-figure explanatory legends off by default; the report/documentation text explains each figure
}
PRESETS = {"quick": {"audit": {"cv": {"repeats": 5}, "bootstrap": {"B": 200}}}, "full": {}}


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def resolve(cfg: dict | str | Path) -> dict:
    """
    EN: merge user config over defaults, then apply the preset (preset overrides cv/bootstrap sizes). Validates keys.
    ES/PT: mescla a configuração do usuário sobre os padrões e aplica o preset; valida chaves.
    """
    if not isinstance(cfg, dict):
        cfg = yaml.safe_load(Path(cfg).read_text(encoding="utf-8")) or {}
    unknown = set(cfg) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown top-level config keys: {sorted(unknown)}")
    r = _merge(DEFAULTS, cfg)
    if r["preset"] not in PRESETS:
        raise ValueError(f"preset must be one of {sorted(PRESETS)}")
    r = _merge(r, PRESETS[r["preset"]])
    if not r["data"]["columns"]:
        raise ValueError("data.columns is required")
    return r

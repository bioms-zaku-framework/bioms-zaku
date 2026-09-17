"""
EN: Build THE example dataset of BioMS Zaku (v1.2, decision of 2026-09-17): one SYNTHETIC file that serves every use —
    regression (lean/fat indices and masses), classification with a known answer (`label_synthetic`) and a diabetes label
    (`diabetes`). Rows are drawn from a multivariate log-normal whose mean vector and log-covariance Σ were estimated in
    NHANES 1999–2004 (adults 18–49 y, measured DXA, 50 kHz BIA, complete cases, doctor-diagnosed diabetes DIQ010 = 1 vs 2)
    SEPARATELY for each cell sex × diabetes. Drawing within cells keeps each cell's means, variances and covariances and,
    through the cell means, the association between diabetes and every variable. Only aggregates (μ, Σ, n per cell) leave
    the source; no real row is copied. The parameters are published next to the CSV and ARE the generating parameters
    (μ rounded to 6 decimals, Σ to 8), so the CSV is reproducible from the JSON alone.

    Design: 200 persons per sex, 70 of them with diabetes (35 %, case-enriched on purpose, declared: prevalence is NOT that of
    NHANES), so the classification audit has ≥ 20 cases per class per sex. `label_synthetic` = Bernoulli(logistic(b0 +
    b1·z(ln FMI) + b2·z(ln age))), z on the sex-level (both classes) moments: it depends on FMI and age only, so a
    classification audit with FMI as control has a known answer (no index should add beyond FMI). Masses in kg are derived
    (index × (H/100)²), not drawn — do not use them as targets while H is mapped (circularity).

Usage:
  python tools/make_zaku_example.py --from-params examples/zaku_exemplo_params.json <out_dir>     # reproduces the shipped CSV
  python tools/make_zaku_example.py --from-source <nhanes_limpo.csv> --diq-dir <folder with DIQ*.xpt> <out_dir>   # maintainers
ES/PT: a base de exemplo ÚNICA, sintética, gerada por célula sexo × diabetes a partir do NHANES; reproduzível pelos parâmetros.
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

import numpy as np
import pandas as pd

VARS = ["R", "Xc", "H_cm", "W", "idade", "BMXARMC", "BMXWAIST", "BMXCALF", "LMI_DXA", "ALMI_DXA", "FMI_DXA"]
ROUND = {"R": 2, "Xc": 2, "H_cm": 1, "W": 1, "idade": 0, "BMXARMC": 1, "BMXWAIST": 1, "BMXCALF": 1, "LMI_DXA": 2, "ALMI_DXA": 2, "FMI_DXA": 2}
DERIVED = {"LMI_DXA": "lean_kg", "ALMI_DXA": "alm_kg", "FMI_DXA": "fat_kg"}
LABEL = {"name": "label_synthetic", "b0": -2.0, "b1": 1.2, "b2": 0.5,
         "note": "synthetic outcome with a known answer: depends on ln FMI and ln age only (z on sex-level moments)"}
N_PER_SEX, N_DIAB_PER_SEX, SEED = 200, 70, 20260917


def estimate(pool: Path, diq_dir: Path) -> dict:
    d = pd.concat([pd.read_sas(diq_dir / f)[["SEQN", "DIQ010"]] for f in ("DIQ.xpt", "DIQ_B.xpt", "DIQ_C.xpt")])
    d["SEQN"] = d.SEQN.astype(int)
    p = pd.read_csv(pool).merge(d, on="SEQN", how="left")
    ok = p[VARS].notna().all(axis=1) & (p[VARS] > 0).all(axis=1) & p.DIQ010.isin([1.0, 2.0])
    p = p[ok]
    cells, sexlevel = {}, {}
    for sex in (0, 1):
        ps = p[p.sexo == sex]
        L = np.log(ps[VARS].to_numpy(float))
        sexlevel[str(sex)] = {"n": int(len(ps)), "mu_log": L.mean(axis=0).round(6).tolist(), "sd_log": L.std(axis=0, ddof=1).round(8).tolist()}
        for dia, code in ((1, 1.0), (0, 2.0)):
            L = np.log(ps[ps.DIQ010 == code][VARS].to_numpy(float))
            cells[f"sex{sex}_diabetes{dia}"] = {"sexo": sex, "diabetes": dia, "n_source": int(len(L)),
                                                "mu_log": L.mean(axis=0).round(6).tolist(), "sigma_log": np.cov(L.T, ddof=1).round(8).tolist()}
    return {"generator": "tools/make_zaku_example.py", "date": datetime.date.today().isoformat(), "seed": SEED,
            "n_per_sex": N_PER_SEX, "n_diabetes_per_sex": N_DIAB_PER_SEX, "variables": VARS, "label": LABEL,
            "source": "NHANES 1999-2004 public-use files (CDC): adults 18-49 y with measured DXA and 50 kHz BIA (HYDRA 4200), complete "
                      "positive cases on the variables, DIQ010 = 1 (doctor-diagnosed diabetes) or 2; convenience sample, survey weights "
                      "ignored. Only μ and Σ of the logs per cell sex × diabetes left the source; no real row is reproduced.",
            "design": "case-enriched on purpose (35 % diabetes per sex); prevalence is not that of NHANES",
            "cells": cells, "sex_level_moments_for_label": sexlevel}


def draw(params: dict) -> pd.DataFrame:
    rng = np.random.default_rng(params["seed"])
    V = params["variables"]; lab = params["label"]; frames = []
    for sex in (0, 1):
        sl = params["sex_level_moments_for_label"][str(sex)]
        mu_s, sd_s = np.array(sl["mu_log"]), np.array(sl["sd_log"])
        for dia, n in ((1, params["n_diabetes_per_sex"]), (0, params["n_per_sex"] - params["n_diabetes_per_sex"])):
            c = params["cells"][f"sex{sex}_diabetes{dia}"]
            Z = rng.multivariate_normal(np.array(c["mu_log"]), np.array(c["sigma_log"]), size=n, method="cholesky")
            X = pd.DataFrame(np.exp(Z), columns=V)
            for col, r in ROUND.items():
                X[col] = X[col].round(r)
            X["idade"] = X["idade"].clip(18, 49).astype(int)
            for src, kg in DERIVED.items():
                X[kg] = (X[src] * (X["H_cm"] / 100.0) ** 2).round(2)
            z_f = (Z[:, V.index("FMI_DXA")] - mu_s[V.index("FMI_DXA")]) / sd_s[V.index("FMI_DXA")]
            z_a = (Z[:, V.index("idade")] - mu_s[V.index("idade")]) / sd_s[V.index("idade")]
            pr = 1 / (1 + np.exp(-(lab["b0"] + lab["b1"] * z_f + lab["b2"] * z_a)))
            X[lab["name"]] = (rng.uniform(size=n) < pr).astype(int)
            X["diabetes"] = dia
            X.insert(0, "sexo", sex); frames.append(X)
    df = pd.concat(frames, ignore_index=True)
    df = df.iloc[np.random.default_rng(params["seed"] + 1).permutation(len(df))].sort_values("sexo", kind="stable").reset_index(drop=True)
    df.insert(0, "id", np.arange(1, len(df) + 1))
    return df


def main() -> None:
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-params", metavar="PARAMS_JSON"); g.add_argument("--from-source", metavar="POOL_CSV")
    ap.add_argument("--diq-dir", default=None); ap.add_argument("out_dir")
    a = ap.parse_args(); out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    if a.from_params:
        params = json.loads(Path(a.from_params).read_text(encoding="utf-8"))
    else:
        params = estimate(Path(a.from_source), Path(a.diq_dir or Path(a.from_source).parent))
        (out / "zaku_exemplo_params.json").write_text(json.dumps(params, indent=1) + "\n", encoding="utf-8")
    df = draw(params)
    df.to_csv(out / "zaku_exemplo.csv", index=False, lineterminator="\n")
    g2 = df.groupby("sexo")
    print(f"{len(df)} rows → {out / 'zaku_exemplo.csv'}; diabetes per sex {g2.diabetes.sum().to_dict()}; "
          f"label_synthetic per sex {g2[LABEL['name']].sum().to_dict()}")


if __name__ == "__main__":
    main()

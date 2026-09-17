"""
EN: Build the package's example dataset: SYNTHETIC rows drawn from a multivariate log-normal whose mean vector and
    log-covariance Σ are estimated, per sex, from a convenience sample of NHANES 1999-2004 (adults 18-49, measured DXA,
    complete cases). Only aggregates (μ, Σ, n) leave the source; no real row is copied. The parameters are written next
    to the CSV so that anyone can decompose Σ by hand and reproduce the file.
ES: datos SINTÉTICOS de una log-normal multivariante con μ y Σ estimadas por sexo en una muestra por conveniencia de NHANES.
PT: dados SINTÉTICOS de uma log-normal multivariada com μ e Σ estimadas por sexo numa amostra por conveniência do NHANES.

Usage:
  python tools/make_example_data.py --from-params examples/example_data_params.json <out_dir>   # anyone: reproduces the shipped CSV
  python tools/make_example_data.py --from-source <source.csv> <out_dir> [--n-per-sex 4000] [--seed 20260913]   # maintainers: re-estimate μ, Σ
The published parameters (mu_log rounded to 6 decimals, sigma_log to 8) ARE the generating parameters: the sampler uses
the rounded values, so the CSV is reproducible from the JSON alone.
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew

VARS = ["R", "Xc", "H_cm", "W", "idade", "BMXARMC", "BMXWAIST", "BMXCALF", "LMI_DXA", "ALMI_DXA", "FMI_DXA"]
ROUND = {"R": 2, "Xc": 2, "H_cm": 1, "W": 1, "idade": 0, "BMXARMC": 1, "BMXWAIST": 1, "BMXCALF": 1, "LMI_DXA": 2, "ALMI_DXA": 2, "FMI_DXA": 2}
# EN: synthetic binary label (declared, not a clinical outcome): logit = b0 + b1·z(log FMI) + b2·z(log age), Bernoulli.
DERIVED = {"LMI_DXA": "lean_kg", "ALMI_DXA": "alm_kg", "FMI_DXA": "fat_kg"}   # EN: kg = index × (H_cm/100)², rounded to 2 decimals
LABEL = {"name": "label_synthetic", "b0": -2.0, "b1": 1.2, "b2": 0.5, "note": "synthetic outcome for classification demos; depends on FMI and age only"}


def main() -> None:
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-params", metavar="PARAMS_JSON"); g.add_argument("--from-source", metavar="SOURCE_CSV")
    ap.add_argument("out_dir"); ap.add_argument("--n-per-sex", type=int, default=4000); ap.add_argument("--seed", type=int, default=20260913)
    a = ap.parse_args(); out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    if a.from_params:
        params = json.loads(Path(a.from_params).read_text(encoding="utf-8"))
        seed, n_per_sex = params["seed"], params["n_per_sex"]
        est = {k: (np.array(v["mu_log"]), np.array(v["sigma_log"])) for k, v in params["per_sex"].items()}
    else:
        src = pd.read_csv(a.from_source); seed, n_per_sex = a.seed, a.n_per_sex; est = {}
    rng = np.random.default_rng(seed)
    if not a.from_params:
      params = {"generator": "tools/make_example_data.py", "date": datetime.date.today().isoformat(), "seed": seed, "n_per_sex": n_per_sex,
                "source": "NHANES 1999-2004, adults 18-49 y with measured DXA and 50 kHz BIA (HYDRA 4200), complete cases on the listed variables; "
                          "a CONVENIENCE sample (survey weights ignored). Only μ and Σ of the logs were used; no individual row is reproduced.",
                "model": "multivariate log-normal per sex: log(x) ~ N(mu, Sigma) with mu, Sigma AS PUBLISHED (rounded); values exponentiated and rounded",
                "variables": VARS, "label": LABEL,
                "derived_columns": {kg: f"{src} * (H_cm/100)**2, rounded to 2 decimals (v0.6; absolute-mass targets as an option)" for src, kg in DERIVED.items()},
                "per_sex": {}}
    frames = []
    for sex, name in ((0, "F"), (1, "M")):
        if a.from_params:
            mu, S = est[name]
        else:
            d = src[src.sexo == sex][VARS].dropna(); d = d[(d > 0).all(axis=1)]
            L = np.log(d.to_numpy(float)); mu = L.mean(axis=0).round(6); S = np.cov(L.T, ddof=1).round(8)   # EN: rounded BEFORE sampling = published values
            params["per_sex"][name] = {"sexo": sex, "n_source": int(len(d)), "mu_log": mu.tolist(), "sigma_log": S.tolist(),
                                       "skew_log": skew(L, axis=0).round(3).tolist(), "excess_kurtosis_log": kurtosis(L, axis=0).round(3).tolist(),
                                       "note": "skew/kurtosis of the source logs are reported so the log-normal approximation can be judged"}
        Z = rng.multivariate_normal(mu, S, size=n_per_sex, method="cholesky")
        X = pd.DataFrame(np.exp(Z), columns=VARS)
        for c, r in ROUND.items():
            X[c] = X[c].round(r)
        X["idade"] = X["idade"].clip(18, 49).astype(int)
        # EN: v0.6 — absolute-mass targets DERIVED from the indices and height (no new draw): index × (H/100)²
        for src_col, kg_col in DERIVED.items():
            X[kg_col] = (X[src_col] * (X["H_cm"] / 100.0) ** 2).round(2)
        z_f = (Z[:, VARS.index("FMI_DXA")] - mu[VARS.index("FMI_DXA")]) / np.sqrt(S[VARS.index("FMI_DXA"), VARS.index("FMI_DXA")])
        z_a = (Z[:, VARS.index("idade")] - mu[VARS.index("idade")]) / np.sqrt(S[VARS.index("idade"), VARS.index("idade")])
        p = 1 / (1 + np.exp(-(LABEL["b0"] + LABEL["b1"] * z_f + LABEL["b2"] * z_a)))
        X[LABEL["name"]] = (rng.uniform(size=len(X)) < p).astype(int)
        X.insert(0, "sexo", sex); frames.append(X)
    df = pd.concat(frames, ignore_index=True); df.insert(0, "id", np.arange(1, len(df) + 1))
    df.to_csv(out / "example_data.csv", index=False)
    # EN: v1.2 — a test-sized cut: the first 200 rows of each sex (independent draws, so a random sample of the same file);
    #     labelled cases per sex stay above the classification minimum (20).
    df.groupby("sexo", sort=True).head(200).to_csv(out / "example_data_400.csv", index=False)
    if not a.from_params:
        (out / "example_data_params.json").write_text(json.dumps(params, indent=1), encoding="utf-8")
    print(f"{len(df)} rows → {out/'example_data.csv'}; label prevalence F {df[df.sexo==0][LABEL['name']].mean():.3f} M {df[df.sexo==1][LABEL['name']].mean():.3f}")


if __name__ == "__main__":
    main()

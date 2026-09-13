"""
EN: Build the package's example dataset: SYNTHETIC rows drawn from a multivariate log-normal whose mean vector and
    log-covariance Σ are estimated, per sex, from a convenience sample of NHANES 1999-2004 (adults 18-49, measured DXA,
    complete cases). Only aggregates (μ, Σ, n) leave the source; no real row is copied. The parameters are written next
    to the CSV so that anyone can decompose Σ by hand and reproduce the file.
ES: datos SINTÉTICOS de una log-normal multivariante con μ y Σ estimadas por sexo en una muestra por conveniencia de NHANES.
PT: dados SINTÉTICOS de uma log-normal multivariada com μ e Σ estimadas por sexo numa amostra por conveniência do NHANES.

Usage: python tools/make_synthetic_nhanes.py <nhanes_limpo.csv> <out_dir> [--n-per-sex 4000] [--seed 20260913]
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
LABEL = {"name": "label_synthetic", "b0": -2.0, "b1": 1.2, "b2": 0.5, "note": "synthetic outcome for classification demos; depends on FMI and age only"}


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("source"); ap.add_argument("out_dir"); ap.add_argument("--n-per-sex", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=20260913); a = ap.parse_args()
    src = pd.read_csv(a.source); out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    params = {"generator": "tools/make_synthetic_nhanes.py", "date": datetime.date.today().isoformat(), "seed": a.seed,
              "source": "NHANES 1999-2004, adults 18-49 y with measured DXA and 50 kHz BIA (HYDRA 4200), complete cases on the listed variables; "
                        "a CONVENIENCE sample (survey weights ignored). Only μ and Σ of the logs were used; no individual row is reproduced.",
              "model": "multivariate log-normal per sex: log(x) ~ N(mu, Sigma); values exponentiated and rounded",
              "variables": VARS, "label": LABEL, "per_sex": {}}
    frames = []
    for sex, name in ((0, "F"), (1, "M")):
        d = src[src.sexo == sex][VARS].dropna(); d = d[(d > 0).all(axis=1)]
        L = np.log(d.to_numpy(float)); mu = L.mean(axis=0); S = np.cov(L.T, ddof=1)
        params["per_sex"][name] = {"sexo": sex, "n_source": int(len(d)), "mu_log": mu.round(6).tolist(), "sigma_log": S.round(8).tolist(),
                                   "skew_log": skew(L, axis=0).round(3).tolist(), "excess_kurtosis_log": kurtosis(L, axis=0).round(3).tolist(),
                                   "note": "skew/kurtosis of the source logs are reported so the log-normal approximation can be judged"}
        Z = rng.multivariate_normal(mu, S, size=a.n_per_sex, method="cholesky")
        X = pd.DataFrame(np.exp(Z), columns=VARS)
        for c, r in ROUND.items():
            X[c] = X[c].round(r)
        X["idade"] = X["idade"].clip(18, 49).astype(int)
        z_f = (Z[:, VARS.index("FMI_DXA")] - mu[VARS.index("FMI_DXA")]) / np.sqrt(S[VARS.index("FMI_DXA"), VARS.index("FMI_DXA")])
        z_a = (Z[:, VARS.index("idade")] - mu[VARS.index("idade")]) / np.sqrt(S[VARS.index("idade"), VARS.index("idade")])
        p = 1 / (1 + np.exp(-(LABEL["b0"] + LABEL["b1"] * z_f + LABEL["b2"] * z_a)))
        X[LABEL["name"]] = (rng.uniform(size=len(X)) < p).astype(int)
        X.insert(0, "sexo", sex); frames.append(X)
    df = pd.concat(frames, ignore_index=True); df.insert(0, "id", np.arange(1, len(df) + 1))
    df.to_csv(out / "nhanes_sintetico.csv", index=False)
    (out / "nhanes_sintetico_params.json").write_text(json.dumps(params, indent=1), encoding="utf-8")
    print(f"{len(df)} rows → {out/'nhanes_sintetico.csv'}; label prevalence F {df[df.sexo==0][LABEL['name']].mean():.3f} M {df[df.sexo==1][LABEL['name']].mean():.3f}")


if __name__ == "__main__":
    main()

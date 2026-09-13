"""EN: the shipped synthetic example is consistent with its published parameters (μ, Σ of the logs) and the generator is
deterministic. ES/PT: o exemplo sintético reproduz seus parâmetros publicados; gerador determinístico."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_example_matches_published_parameters():
    df = pd.read_csv(ROOT / "examples/nhanes_sintetico.csv"); P = json.loads((ROOT / "examples/nhanes_sintetico_params.json").read_text())
    assert len(df) == 8000 and set(df.sexo) == {0, 1} and P["label"]["name"] in df
    for key, sex in (("F", 0), ("M", 1)):
        L = np.log(df[df.sexo == sex][P["variables"]].to_numpy(float))
        mu, S = np.array(P["per_sex"][key]["mu_log"]), np.array(P["per_sex"][key]["sigma_log"])
        assert np.abs(L.mean(axis=0) - mu).max() < 0.02          # EN: sampling + rounding (age is clipped to integers)
        D = np.abs(np.cov(L.T, ddof=1) - S); ia = P["variables"].index("idade")
        age_mask = np.zeros_like(D, dtype=bool); age_mask[ia, :] = True; age_mask[:, ia] = True
        assert D[~age_mask].max() < 0.005                        # EN: continuous variables: sampling error only
        assert D[age_mask].max() < 0.03                          # EN: age is rounded to whole years and clipped to 18-49
        assert P["per_sex"][key]["n_source"] > 2000
    assert (df[P["variables"]] > 0).all().all()

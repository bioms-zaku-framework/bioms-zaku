"""
EN: Generate the bundled SYNTHETIC example (examples/minimal_data.csv): 150 rows, deterministic (seed 2026). Values are
    plausible for adults but do not come from any person. For demonstrating the pipeline only.
ES/PT: gera o exemplo SINTÉTICO embarcado (150 linhas, semente 2026). Só para demonstrar o fluxo.
"""
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(2026); n = 150
sexo = rng.integers(0, 2, n); idade = rng.integers(18, 50, n)
H = np.where(sexo == 1, rng.normal(175, 7, n), rng.normal(162, 6, n)); W = np.where(sexo == 1, rng.normal(82, 14, n), rng.normal(68, 13, n))
R = np.where(sexo == 1, rng.normal(480, 60, n), rng.normal(560, 65, n)); Xc = R * rng.uniform(0.10, 0.14, n)
lean = 0.42 * W * (H / 170) ** 0.4 * (500 / R) ** 0.45 * np.where(sexo == 1, 1.15, 1.0) * np.exp(rng.normal(0, 0.05, n)); fat = np.clip(W - lean, 5, None)
df = pd.DataFrame(dict(seqn=np.arange(1, n + 1), sexo=sexo, idade_anos=idade, estatura_cm=H.round(1), massa_kg=W.round(1), resistencia_ohm=R.round(1),
                       reatancia_ohm=Xc.round(1), lmi_dxa=(lean / (H / 100) ** 2).round(2), fmi_dxa=(fat / (H / 100) ** 2).round(2),
                       diab=(fat / W > np.quantile(fat / W, 0.85)).astype(int)))
out = Path(__file__).resolve().parents[1] / "examples" / "minimal_data.csv"
df.to_csv(out, index=False, sep=";", decimal=",")
print(f"{len(df)} rows -> {out}")

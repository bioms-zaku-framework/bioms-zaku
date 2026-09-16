"""
EN: Build the bundled REAL example `examples/nhanes_diabetes_400.csv` from NHANES 1999–2004 public-use files (CDC, public
    domain): adults 18–49 y with measured DXA and 50 kHz BIA (HYDRA 4200), complete cases on every column below, plus the
    diabetes questionnaire DIQ010 ("Doctor told you have diabetes"). Case-ENRICHED convenience sample: every diagnosed
    diabetic with complete data (DIQ010 = 1) and a seeded random draw of non-diabetics (DIQ010 = 2) up to N rows.
    Borderline (3), refused (7/9) and missing answers are excluded and counted. Survey weights are ignored by design.
    Not representative of prevalence: it exists to demonstrate the classification audit (≥ 20 per class per sex).
    Inputs: the cleaned pool `nhanes_limpo.csv` (local, produced by the article pipeline: one row per participant with
    R, Xc, H, W, circumferences and DXA masses) and DIQ.xpt / DIQ_B.xpt / DIQ_C.xpt (downloaded from the CDC when absent).
    Output: the CSV (English column names that the guided flow recognises; R and Xc are at 50 kHz; W = body mass; 4 decimals) and `examples/nhanes_diabetes_400_provenance.json` (seed,
    counts, exclusions, SHA-256). Deterministic.
ES/PT: gera o exemplo REAL embarcado (NHANES, domínio público); amostra enriquecida em casos; determinístico.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

CDC = {"DIQ.xpt": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/1999/DataFiles/DIQ.xpt",
       "DIQ_B.xpt": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2001/DataFiles/DIQ_B.xpt",
       "DIQ_C.xpt": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2003/DataFiles/DIQ_C.xpt"}
COLS = {"SEQN": "id", "sexo": "sex_1M_0F", "idade": "age_years", "R": "resistance_ohm", "Xc": "reactance_ohm", "H_cm": "height_cm",
        "W": "body_mass_kg", "BMXWAIST": "waist_cm", "BMXARMC": "arm_cm", "BMXCALF": "calf_cm", "LM_DXA_kg": "lean_dxa_kg",
        "FM_DXA_kg": "fat_dxa_kg", "ALM_DXA_kg": "alm_dxa_kg"}


def fetch(dirp: Path, name: str) -> Path:
    p = dirp / name
    if not p.exists() or not p.read_bytes().startswith(b"HEADER RECORD"):
        req = urllib.request.Request(CDC[name], headers={"User-Agent": "Mozilla/5.0"})
        p.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    assert p.read_bytes().startswith(b"HEADER RECORD"), f"{p} is not a SAS transport file"
    return p


def main(pool: Path, diq_dir: Path, out: Path, n: int, seed: int) -> None:
    d = pd.concat([pd.read_sas(fetch(diq_dir, k))[["SEQN", "DIQ010"]] for k in CDC]); d["SEQN"] = d.SEQN.astype(int)
    p = pd.read_csv(pool)[list(COLS)].merge(d, on="SEQN", how="left")
    n_pool = len(p)
    excl = {"missing_any_measurement": int(p[list(COLS)].isna().any(axis=1).sum())}
    p = p.dropna(subset=list(COLS))
    vc = p.DIQ010.value_counts(dropna=False)
    excl.update({"diq010_borderline_3": int(vc.get(3.0, 0)), "diq010_refused_or_dont_know_7_9": int(vc.get(7.0, 0) + vc.get(9.0, 0)),
                 "diq010_missing": int(p.DIQ010.isna().sum())})
    p = p[p.DIQ010.isin([1.0, 2.0])]
    cases, ctrl = p[p.DIQ010 == 1.0], p[p.DIQ010 == 2.0]
    rng = np.random.default_rng(seed)
    take = min(n - len(cases), len(ctrl))
    ctrl = ctrl.iloc[np.sort(rng.choice(len(ctrl), size=take, replace=False))]
    s = pd.concat([cases, ctrl]).sort_values("SEQN")
    s = s.rename(columns=COLS); s["diabetes_1Y_0N"] = (s.pop("DIQ010") == 1.0).astype(int)
    s["sex_1M_0F"] = s["sex_1M_0F"].astype(int); s["age_years"] = s["age_years"].astype(int); s["id"] = s["id"].astype(int)
    s = s.round(4)
    out.parent.mkdir(parents=True, exist_ok=True); s.to_csv(out, index=False, lineterminator="\n")
    prov = {"generator": "tools/make_nhanes_example.py", "seed": seed, "n_requested": n, "n_rows": int(len(s)),
            "source": "NHANES 1999-2004 public-use files (CDC, public domain): DEMO, BMX, BIX (50 kHz BIA, HYDRA 4200), DXA and DIQ; "
                      "adults 18-49 y with measured DXA; complete cases on every column; convenience sample, survey weights ignored",
            "design": "case-enriched: every participant with DIQ010 = 1 (doctor-diagnosed diabetes) and complete data, plus a seeded "
                      "random draw of DIQ010 = 2 up to n_requested; NOT representative of prevalence",
            "pool_rows": n_pool, "excluded": excl,
            "counts": {"diabetes_1Y_0N": {str(k): int(v) for k, v in s.diabetes_1Y_0N.value_counts().sort_index().items()},
                       "by_sex": {f"sex_{k}": {str(kk): int(vv) for kk, vv in g.diabetes_1Y_0N.value_counts().sort_index().items()} for k, g in s.groupby("sex_1M_0F")}},
            "columns": list(s.columns), "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
    out.with_name(out.stem + "_provenance.json").write_text(json.dumps(prov, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(prov["counts"]), prov["sha256"][:16], "->", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1].strip())
    ap.add_argument("--pool", type=Path, default=Path.home() / "Desktop/bioms_2/nhanes/nhanes_limpo.csv")
    ap.add_argument("--diq-dir", type=Path, default=Path.home() / "Desktop/bioms_2/nhanes")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "examples" / "nhanes_diabetes_400.csv")
    ap.add_argument("--n", type=int, default=400); ap.add_argument("--seed", type=int, default=20260916)
    a = ap.parse_args(); main(a.pool, a.diq_dir, a.out, a.n, a.seed)

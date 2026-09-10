"""
EN: Screening matrix (CONTRATOS.md §4.1): redundant × specific × useful per method and stratum, with identity and
    validity flags. Classes are enumerated and fixed.
ES: Matriz de cribado: redundante × específico × útil por método y estrato.
PT: Matriz de triagem: redundante × específico × útil por método e estrato.
"""
from __future__ import annotations

import pandas as pd


def screening_table(redundancy: pd.DataFrame, audit: pd.DataFrame, utility: pd.DataFrame | None, *,
                    primary_target: str | None = None) -> pd.DataFrame:
    """
    EN: one row per (method, stratum). `specific` comes from the audit verdict on `primary_target` (default: the
        first target in `audit`); `useful` from `utility` on the same target (False when utility was not run).
    ES/PT: uma linha por (método, estrato); específico pelo veredito no alvo primário; útil pela utilidade no mesmo alvo.
    """
    if audit.empty:
        return pd.DataFrame(columns=["method_id", "stratum", "redundant", "specific", "useful", "identity", "class"])
    tgt = primary_target or audit["target"].iloc[0]
    a = audit[audit.target == tgt][["method_id", "stratum", "verdict"]]
    r = redundancy[["method_id", "stratum", "redundant", "identity_of"]]
    df = r.merge(a, on=["method_id", "stratum"], how="left")
    if utility is not None and not utility.empty:
        u = utility[utility.target == tgt][["method_id", "stratum", "useful"]]
        df = df.merge(u, on=["method_id", "stratum"], how="left")
    else:
        df["useful"] = False
    df["useful"] = df["useful"].fillna(False).astype(bool)
    df["identity"] = df["identity_of"].notna()
    df["specific"] = df["verdict"].map({"SPECIFIC": True, "MEASURES_CONTROL": False})   # NaN when inconclusive/absent
    df["class"] = [_cls(i, rd, sp, us) for i, rd, sp, us in zip(df["identity"], df["redundant"], df["specific"], df["useful"])]
    return df[["method_id", "stratum", "redundant", "specific", "useful", "identity", "class"]].sort_values(["stratum", "method_id"]).reset_index(drop=True)


def _cls(identity: bool, redundant: bool, specific, useful: bool) -> str:
    if identity:
        return "identity"
    if specific is None or (isinstance(specific, float) and specific != specific):
        return "inconclusive"
    return f"{'redundant' if redundant else 'original'}-{'specific' if specific else 'nonspecific'}-{'useful' if useful else 'notuseful'}"

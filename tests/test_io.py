"""EN: input contract (§1). ES: contrato de entrada. PT: contrato de entrada."""
import numpy as np
import pandas as pd
import pytest
from bioms_zaku.io import InputError, read_table

MAP = {"variables": {"R": "resistencia_ohm", "Xc": "reatancia_ohm", "H": "estatura_cm", "W": "massa_kg"},
       "units": {"H": "cm", "W": "kg"}, "targets": {"LMI_DXA": "lmi_dxa"}, "controls": {"FMI_DXA": "fmi_dxa"},
       "covariates": ["massa_kg", "estatura_cm"], "strata": "sexo", "groups": {"sexo": "sexo"}, "id": "seqn"}

ROWS = [(1, 1, 178.3, 92.5, 467.7, 54.9, 19.44, 9.19), (2, 0, 162.0, 63.4, 513.0, 58.1, 15.10, 9.02),
        (3, 1, 171.2, 70.1, 520.4, 61.0, 17.02, 5.33), (4, 0, 158.7, 55.0, 601.2, 66.3, 14.05, 6.90)]
COLS = ["seqn", "sexo", "estatura_cm", "massa_kg", "resistencia_ohm", "reatancia_ohm", "lmi_dxa", "fmi_dxa"]


def _frame():
    return pd.DataFrame(ROWS, columns=COLS)


def _write(tmp_path, sep, dec, name="d.csv", encoding="utf-8"):
    df = _frame()
    p = tmp_path / name
    p.write_text(df.to_csv(index=False, sep=sep, decimal=dec), encoding=encoding)
    return p


def test_brazilian_csv_semicolon_comma(tmp_path):
    ds = read_table(_write(tmp_path, ";", ","), MAP, min_n=1, min_per_class=1)
    assert ds.info["sep_used"] == ";" and ds.info["decimal_used"] == ","
    assert abs(ds.frame.loc[0, "R"] - 467.7) < 1e-12
    assert ds.derived == ["H_m", "PhA", "II", "Z"]
    assert abs(ds.frame.loc[0, "II"] - 178.3 ** 2 / 467.7) < 1e-9


def test_standard_csv_comma_dot(tmp_path):
    ds = read_table(_write(tmp_path, ",", "."), MAP, min_n=1, min_per_class=1)
    assert (ds.info["sep_used"], ds.info["decimal_used"]) == (",", ".")


def test_ambiguous_or_undetectable_requires_explicit(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a|b\n1|2\n")
    with pytest.raises(InputError):
        read_table(p, MAP, min_n=1)


def test_units_are_required_and_converted():
    m = dict(MAP); del m["units"]
    with pytest.raises(InputError, match="units.H"):
        read_table(_frame(), m, min_n=1, min_per_class=1)
    m = dict(MAP); m["units"] = {"H": "m", "W": "kg"}
    df = _frame(); df["estatura_cm"] = df["estatura_cm"] / 100
    ds = read_table(df, m, min_n=1, min_per_class=1)
    assert abs(ds.frame.loc[0, "H"] - 178.3) < 1e-9


def test_nonpositive_variable_is_an_error_unless_dropped():
    df = _frame(); df.loc[1, "reatancia_ohm"] = 0.0
    with pytest.raises(InputError, match="non-positive"):
        read_table(df, MAP, min_n=1, min_per_class=1)
    ds = read_table(df, MAP, drop_nonpositive=True, min_n=1, min_per_class=1)
    assert ds.info["rows_dropped"]["nonpositive"] == 1 and len(ds.frame) == 3


def test_missing_target_rows_are_counted():
    df = _frame(); df.loc[2, "lmi_dxa"] = np.nan
    ds = read_table(df, MAP, min_n=1, min_per_class=1)
    assert ds.info["rows_dropped"]["missing_LMI_DXA"] == 1


def test_missing_mapped_column_is_named():
    with pytest.raises(InputError, match="fmi_dxa"):
        read_table(_frame().drop(columns=["fmi_dxa"]), MAP, min_n=1)


def test_pairing_may_mix_a_class_target_with_a_continuous_control():
    """EN: v1.2 — gains in Tjur's D and in R² share the explained-variation scale, so mixed pairs are allowed."""
    df = _frame(); df["diab"] = [0, 1, 0, 1]
    m = dict(MAP); m["targets"] = {"DIAB": "diab"}; m["controls"] = {"FMI_DXA": "fmi_dxa"}
    ds = read_table(df, m, min_n=1, min_per_class=1)
    assert ds.target_types["DIAB"] == "classification" and ds.target_types["FMI_DXA"] == "regression" and ds.pairing == {"DIAB": "FMI_DXA"}


def test_frequency_suffix_and_multiple_frequencies():
    df = _frame(); df["r5"] = df["resistencia_ohm"] * 1.2; df["xc5"] = df["reatancia_ohm"] * 0.5
    m = dict(MAP); m["variables"] = {**MAP["variables"], "R5": "r5", "Xc5": "xc5"}
    ds = read_table(df, m, min_n=1, min_per_class=1)
    assert set(ds.variables) == {"R", "Xc", "H", "W", "R5", "Xc5"}
    m2 = dict(MAP); m2["frequency_khz"] = {"R": 5, "Xc": 5}
    ds2 = read_table(_frame(), m2, min_n=1, min_per_class=1)
    assert set(ds2.variables) == {"R5", "Xc5", "H", "W"} and ds2.derived == []


def test_small_strata_are_ignored_with_warning():
    ds = read_table(_frame(), MAP, min_n=3, min_per_class=1)
    assert len(ds.frame) == 0 and any("strata ignored" in w for w in ds.info["warnings"])


def test_bad_encoding_is_an_error(tmp_path):
    p = _write(tmp_path, ";", ",", name="latin.csv", encoding="latin-1")
    p.write_bytes(p.read_bytes().replace(b"seqn", b"seq\xe7"))
    with pytest.raises(InputError, match="decode"):
        read_table(p, MAP)

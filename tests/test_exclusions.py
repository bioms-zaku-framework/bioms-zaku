"""EN: missing values — excluded and counted per reason; the results describe the people who remain (no imputation, no
comparison with the excluded rows; the framework describes the analysed sample, it does not estimate a population)."""
import numpy as np
import pandas as pd

from bioms_zaku.io import read_table
from test_design_orthogonal import _frame

MAP = {"variables": {"R": "R", "Xc": "Xc", "H": "H", "W": "W"}, "units": {"H": "cm", "W": "kg"}, "targets": {"lean": "lean"}, "controls": {"fat": "fat"}, "covariates": ["W", "H"]}


def test_missing_rows_are_counted_per_reason_and_nothing_else_is_inferred():
    df = _frame(n=300, seed=9); df.loc[:29, "lean"] = np.nan; df.loc[290:, "Xc"] = np.nan
    ds = read_table(df, MAP)
    assert ds.info["rows_dropped"]["missing_lean"] == 30 and ds.info["rows_dropped"]["missing_variables_algebra"] == 10
    assert "exclusions" not in ds.info and not any("random" in w for w in ds.info["warnings"])
    assert ds.frame["lean"].isna().sum() == 30                       # kept in the frame: excluded from that audit only, never imputed

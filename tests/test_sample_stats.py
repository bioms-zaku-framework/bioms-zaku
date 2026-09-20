"""EN: sample statistics in formulas (v0.9), exercised end to end through proposed entries.

Until 2026-09-20 the vehicle was examples/bioms_mota_proposed.yaml, the author's own eight indices; that file left the
repository with the rest of what is not the tool, so the catalogue below is declared INSIDE the test. The guarantees are
unchanged and none of them was ever about those eight formulas: a proposed index runs end to end and is marked
`proposed`; `uses_sample_stats` marks exactly the index whose formula reduces over rows; the statistic is recomputed per
stratum, recorded in the manifest, warned about, and shown in the summary and in the report; and a proposal never takes
precedence over a published method."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from bioms_zaku.expr import ExpressionError, compile_expr
from bioms_zaku.i18n import set_language

ROOT = Path(__file__).resolve().parents[1]


def test_mean_median_sd_reduce_over_rows_and_are_recorded():
    x = np.array([1.0, 2.0, 4.0, np.nan])
    ce = compile_expr("x - mean(x)", ["x"]); rec = []
    out = ce.evaluate({"x": x}, rec)
    assert ce.uses_sample_stats and rec == [("mean(x)", 7 / 3)] and np.allclose(out[:3], x[:3] - 7 / 3) and np.isnan(out[3])
    rec = []; ce2 = compile_expr("(x - median(x)) / sd(x)", ["x"]); ce2.evaluate({"x": x}, rec)
    assert dict(rec) == {"median(x)": 2.0, "sd(x)": float(np.nanstd(x, ddof=1))}
    assert not compile_expr("x ** e", ["x"]).uses_sample_stats and compile_expr("x ** e", ["x"]).evaluate({"x": 2.0}) == 2.0 ** np.e
    with pytest.raises(ExpressionError):
        compile_expr("mean(x, y)", ["x", "y"])                                      # arity is fixed
    assert float(compile_expr("mean(x)", ["x"]).evaluate({"x": 3.0})) == 3.0          # scalar input (check_example path)


# EN: three proposed indices. Prop_B is the one that matters: its sigmoid centres PhA on the SAMPLE mean of PhA, so its
#     value depends on who else is in the stratum — exactly the case the manifest must record and the report must show.
#     The other two use no sample statistic, and are here so the flag has something to be false about.
PROPOSED = {
    "include": ["curated", "Prop_A", "Prop_B", "Prop_C"],
    "user_entries": [
        {"id": "Prop_A", "label": "Prop_A, PhA x H_m^2 / R", "authors": "Test", "target": "lean_mass",
         "expr": "PhA * H_m**2 / R", "provenance": {"formula_source": "proposed"}},
        {"id": "Prop_B", "label": "Prop_B, LMI x sigmoid of PhA around its sample mean", "authors": "Test",
         "target": "lean_mass", "expr": "(PhA * H / R) * (1 / (1 + exp(-(PhA - mean(PhA)))))",
         "provenance": {"formula_source": "proposed", "note": "sample mean of PhA, per stratum"}},
        {"id": "Prop_C", "label": "Prop_C, sqrt(PhA) x W / H_m^2", "authors": "Test", "target": "lean_mass",
         "expr": "sqrt(PhA) * W / H_m**2", "provenance": {"formula_source": "proposed"}},
    ],
}


def _cfg(tmp_path, name, **over):
    cfg = yaml.safe_load((ROOT / "tests/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "tests/minimal_data.csv"); cfg["output"] = {"dir": str(tmp_path), "figures": over.pop("figures", False)}; cfg["run_name"] = name
    cfg["audit"] = {"bootstrap": {"min_oob": 10}, "cv": {"folds": 3}}; cfg["language"] = "pt"; cfg["strata"] = "sexo"; cfg["strata_labels"] = {0: "F", 1: "M"}
    cfg["data"]["columns"]["groups"] = {"sexo": "sexo"}
    cfg["catalog"] = PROPOSED
    cfg.update(over)
    return cfg


def test_proposed_entries_run_and_the_sample_statistic_is_recorded_per_stratum(tmp_path):
    from bioms_zaku.run import run
    from bioms_zaku.check import check
    lines = []; check(_cfg(tmp_path, "c"), printer=lines.append)
    assert lines[-1].startswith("check: OK") and any("propostos" in l and "Prop_A" in l and "Prop_C" in l for l in lines)
    res = run(_cfg(tmp_path, "b", figures=True), printer=lambda s: None); alg = res["tables"]["algebra"]
    ids = {"Prop_A", "Prop_B", "Prop_C"}
    assert ids <= set(alg.method_id) and alg[alg.method_id.isin(ids)].proposed.all()
    assert alg[alg.method_id == "Prop_B"].uses_sample_stats.all() and not alg[~alg.method_id.isin(["Prop_B"])].uses_sample_stats.any()
    # the mean recorded per stratum equals the mean of PhA over that stratum's rows, recomputed here from the input file
    m = res["manifest"]; df = pd.read_csv(ROOT / "tests/minimal_data.csv", sep=m["sep_used"], decimal=m["decimal_used"])
    df = df[(df[["resistencia_ohm", "reatancia_ohm", "estatura_cm", "massa_kg"]] > 0).all(axis=1)]
    ss = res["manifest"]["sample_statistics"]
    for code, lab in ((0, "F"), (1, "M")):
        sub = df[df.sexo == code]; expected = float(np.degrees(np.arctan(sub.reatancia_ohm / sub.resistencia_ohm)).mean())
        assert ss[lab] == {"Prop_B": {"mean(PhA)": pytest.approx(expected, abs=1e-9)}}, lab
    assert any("F/Prop_B: formula uses sample statistics" in w and "mean(PhA) =" in w for w in res["manifest"]["warnings"])
    summ = (res["out_dir"] / "summary.md").read_text(encoding="utf-8"); assert "estatísticas amostrais usadas em fórmulas" in summ and "Prop_B: mean(PhA) =" in summ
    txt = (res["out_dir"] / "report.html").read_text(encoding="utf-8"); assert "<td>Estatísticas amostrais usadas em fórmulas (por estrato)</td><td>F: Prop_B: mean(PhA) =" in txt
    # every proposed value is finite and positive on this data (logarithms are taken downstream)
    for mid in ids:
        assert (alg[alg.method_id == mid].n_nonpositive_pred == 0).all(), mid
    red = res["tables"]["redundancy"]
    assert not red[~red.method_id.isin(ids)].predecessor_id.isin(ids).any()          # proposals never precede published methods
    set_language("en")

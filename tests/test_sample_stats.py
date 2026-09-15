"""EN: sample statistics in formulas (v0.9) and the eight BioMS indices of the author as proposed entries."""
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


def _cfg(tmp_path, name, **over):
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); cfg["output"] = {"dir": str(tmp_path), "figures": over.pop("figures", False)}; cfg["run_name"] = name
    cfg["audit"] = {"bootstrap": {"min_oob": 10}, "cv": {"folds": 3}}; cfg["language"] = "pt"; cfg["strata"] = "sexo"; cfg["strata_labels"] = {0: "F", 1: "M"}
    cfg["data"]["columns"]["groups"] = {"sexo": "sexo"}
    cfg["catalog"] = yaml.safe_load((ROOT / "examples/bioms_mota_proposed.yaml").read_text(encoding="utf-8"))["catalog"]
    cfg.update(over)
    return cfg


def test_the_eight_bioms_indices_run_as_proposed_entries_and_the_sample_mean_is_recorded(tmp_path):
    from bioms_zaku.run import run
    from bioms_zaku.check import check
    lines = []; check(_cfg(tmp_path, "c"), printer=lines.append)
    assert lines[-1].startswith("check: OK") and any("propostos" in l and "BioMS_1" in l and "BioMS_9" in l for l in lines)
    res = run(_cfg(tmp_path, "b", figures=True), printer=lambda s: None); alg = res["tables"]["algebra"]
    ids = {"BioMS_1", "BioMS_2", "BioMS_4", "BioMS_5", "BioMS_6R", "BioMS_7", "BioMS_8", "BioMS_9"}
    assert ids <= set(alg.method_id) and alg[alg.method_id.isin(ids)].proposed.all()
    assert alg[alg.method_id == "BioMS_2"].uses_sample_stats.all() and not alg[~alg.method_id.isin(["BioMS_2"])].uses_sample_stats.any()
    # the mean recorded per stratum equals the mean of PhA over that stratum's rows, recomputed here from the input file
    m = res["manifest"]; df = pd.read_csv(ROOT / "examples/minimal_data.csv", sep=m["sep_used"], decimal=m["decimal_used"])
    df = df[(df[["resistencia_ohm", "reatancia_ohm", "estatura_cm", "massa_kg"]] > 0).all(axis=1)]
    ss = res["manifest"]["sample_statistics"]
    for code, lab in ((0, "F"), (1, "M")):
        sub = df[df.sexo == code]; expected = float(np.degrees(np.arctan(sub.reatancia_ohm / sub.resistencia_ohm)).mean())
        assert ss[lab] == {"BioMS_2": {"mean(PhA)": pytest.approx(expected, abs=1e-9)}}, lab
    assert any("F/BioMS_2: formula uses sample statistics" in w and "mean(PhA) =" in w for w in res["manifest"]["warnings"])
    summ = (res["out_dir"] / "summary.md").read_text(encoding="utf-8"); assert "estatísticas amostrais usadas em fórmulas" in summ and "BioMS_2: mean(PhA) =" in summ
    txt = (res["out_dir"] / "report.html").read_text(encoding="utf-8"); assert "<td>Estatísticas amostrais usadas em fórmulas (por estrato)</td><td>F: BioMS_2: mean(PhA) =" in txt
    # every BioMS value is finite and positive on this data (logarithms are taken downstream)
    for mid in ids:
        assert (alg[alg.method_id == mid].n_nonpositive_pred == 0).all(), mid
    red = res["tables"]["redundancy"]
    assert not red[~red.method_id.isin(ids)].predecessor_id.isin(ids).any()          # proposals never precede published methods
    set_language("en")

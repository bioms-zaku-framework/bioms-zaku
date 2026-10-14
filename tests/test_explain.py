"""EN: reading one result (contract §4.7; v1.2, 2026-10-02). An external reviewer ran the example notebook and wrote that a
reader who only executes it leaves with the label and without the size of S1 and S2, or the reference each answer is
relative to. `explain.py` opens one row; this file guards what it promises: the decision it shows is rebuilt with the
package's own rule and equals the stored one on every row of real runs, in the four languages; the rule holds at its
edges; a printed number never contradicts the check printed beside it; the CSVs are read back exactly; the report
carries the reading for every row, opens on a fixed row, names what was not audited, and `render` reproduces it."""
import csv
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from bioms_zaku import explain as X
from bioms_zaku.i18n import LANGS, set_language

ROOT = Path(__file__).resolve().parents[1]


def _cfg(tmp_path, name, **over):
    cfg = yaml.safe_load((ROOT / "tests/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "tests/minimal_data.csv"); cfg["output"] = {"dir": str(tmp_path), "figures": False}
    cfg["run_name"] = name
    for k, v in over.items():
        cfg[k] = v
    return cfg


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    """EN: three runs that between them reach every branch of the reading: regression with an equation and a method
    skipped for a missing input; a class target with a continuous control (D on one side, R² on the other); strata
    a designed index (audit partition only; without strata, because 150 rows split 70/30 inside two strata leave
    about 23 per stratum, which `check` rightly refuses). Strata are exercised by the notebook test."""
    from bioms_zaku.run import run
    d = tmp_path_factory.mktemp("x")
    quiet = lambda s: None
    inc = ["Lukaski1985_II", "Baumgartner1988_PhA", "Piccoli1994_RH", "Piccoli1994_XcH", "LMI", "Kyle2001_FFM", "Hoffer1969_H2Z"]
    reg = run(_cfg(d, "reg", catalog={"include": inc}), printer=quiet)
    cls_cfg = _cfg(d, "cls")
    cls_cfg["data"]["columns"]["targets"] = {"diab": "diab"}; cls_cfg["data"]["columns"]["pairing"] = {"diab": "FMI_DXA"}
    cls = run(cls_cfg, printer=quiet)
    des_cfg = _cfg(d, "des", design=[{"target": "LMI_DXA", "id": "Zaku_LMI"}],
                   declarations={"targets_independent_of_variables": True})
    des_cfg["audit"] = {"bootstrap": {"min_oob": 10, "max_attempts_factor": 6}, "cv": {"folds": 3}}
    des = run(des_cfg, printer=quiet)
    set_language("en")
    return {"reg": reg, "cls": cls, "des": des}


def _tables(res):
    from bioms_zaku.run import read_tables
    import json
    m = json.loads((res["out_dir"] / "manifest.json").read_text(encoding="utf-8"))
    return read_tables(res["out_dir"]), m["config_resolved"], m


# ---------------------------------------------------------------------------------------------------------------- the rule
def _one_row_tables(s1, s2, util_lo=0.05, margin_u=0.03):
    a = pd.DataFrame([dict(method_id="m", stratum="all", target="y", control="c", n=100, B_eff=200, scale="log", metric="R2",
                           metric_control="R2", verdict="?", verdict_family="", k_methods=1, ci_family=float("nan"), epv_low=False,
                           score_oob_control_to_target=0.5, score_oob_idx_control_to_target=0.5 + s1[0],
                           score_oob_target_to_control=0.5, score_oob_idx_target_to_control=0.5 + s2[0],
                           s1_mean=s1[0], s1_lo=s1[1], s1_hi=s1[2], p_s1=s1[3], s2_mean=s2[0], s2_lo=s2[1], s2_hi=s2[2], p_s2=s2[3])])
    u = pd.DataFrame([dict(method_id="m", stratum="all", target="y", covariates="W+H", metric="R2", score_base=0.8, score_with=0.85,
                           delta_mean=0.06, delta_lo=util_lo, delta_hi=0.09, p_delta=1.0, margin=margin_u, useful=bool(util_lo > margin_u))])
    cfg = {"audit": {"verdict": {"margin": 0.03, "p_specific": 0.95, "ci": 0.95}}, "algebra": {"redundancy_threshold": 0.95}}
    return {"audit": a, "utility": u}, cfg


@pytest.mark.parametrize("s1, present", [
    ((0.03, 0.01, 0.05, 1.0), False),        # mean exactly the margin: "mean > margin" is strict
    ((0.031, 0.0, 0.05, 1.0), False),        # lower end exactly 0: "interval above 0" is strict
    ((0.031, 0.001, 0.05, 0.95), True),      # P exactly 0.95: "P ≥ p_specific" is inclusive
    ((0.031, 0.001, 0.05, 0.949), False),
    ((0.2, 0.1, 0.3, 1.0), True),
])
def test_an_increment_is_present_exactly_when_the_contract_says(s1, present):
    tables, cfg = _one_row_tables(s1, (0.0, -0.01, 0.01, 0.5))
    e = X.explain_row(tables, cfg, "m", "all")
    assert e["audit"]["s1"]["present"] is present
    assert all(e["audit"]["s1"]["checks"]) is present, "the three checks shown must add up to the decision"
    assert e["audit"]["rebuilt"] == ("SPECIFIC" if present else "NEITHER")


@pytest.mark.parametrize("lo, useful", [(0.03, False), (0.0300001, True), (0.029, False)])
def test_useful_needs_the_lower_end_strictly_above_the_margin(lo, useful):
    tables, cfg = _one_row_tables((0.0, -0.01, 0.01, 0.5), (0.0, -0.01, 0.01, 0.5), util_lo=lo)
    tables["audit"].loc[0, "verdict"] = "NEITHER"                                   # the audit side is not under test here
    e = X.explain_row(tables, cfg, "m", "all")
    assert e["utility"]["rebuilt"] is useful and e["utility"]["useful"] is useful and e["consistent"]


def test_a_stored_decision_the_rule_does_not_reproduce_is_said_in_the_open():
    tables, cfg = _one_row_tables((0.2, 0.1, 0.3, 1.0), (0.0, -0.01, 0.01, 0.5))
    tables["audit"].loc[0, "verdict"] = "NEITHER"                                   # a table that disagrees with its own numbers
    e = X.explain_row(tables, cfg, "m", "all")
    assert not e["consistent"]
    assert any(k == "warn" and "SPECIFIC" in s and "NEITHER" in s for k, s in X.lines(e))


# ---------------------------------------------------------------------------------------------------------------- the numbers
def test_a_printed_number_never_lands_on_the_other_side_of_a_threshold():
    """EN: 0.0287 against 0.03 must not print as 0.03, nor −0.00002 against 0 as −0.0000 — beside a check that says the
    opposite. Thousands of values drawn right at the edges of 0, 0.03, 0.95 and 0.95 of Spearman."""
    rng = np.random.default_rng(20261002)
    side = lambda x, t: (x > t) - (x < t)
    for th in (0.0, 0.03, 0.95):
        for v in np.concatenate([th + rng.normal(0, 1e-3, 3000), th + rng.normal(0, 1e-7, 3000), [th, th + 1e-12, th - 1e-12]]):
            s = X.fmt(v, (0.0, th), 4, True)
            assert side(float(s), th) == side(float(v), th) and side(float(s), 0.0) == side(float(v), 0.0), (v, th, s)


def test_tables_are_read_back_exactly_as_written(runs):
    """EN: pandas' default CSV parser returns about half of the floats one unit in the last place away (measured
    2026-10-02: 1,719 of 3,536). `read_tables` must return the float that was written."""
    from bioms_zaku.run import read_tables
    out = runs["reg"]["out_dir"]
    tables = read_tables(out)
    checked = 0
    for name, df in tables.items():
        if df.empty:
            continue
        with open(out / f"{name}.csv", encoding="utf-8", newline="") as fh:
            raw = list(csv.DictReader(fh))
        for c in df.columns:
            if df[c].dtype.kind != "f":
                continue
            for i, txt in enumerate(r[c] for r in raw):
                if txt == "":
                    assert math.isnan(df[c].iloc[i]); continue
                assert df[c].iloc[i] == float(txt), (name, c, i, txt, repr(df[c].iloc[i])); checked += 1
    assert checked > 500


# ---------------------------------------------------------------------------------------------------------------- real runs
@pytest.mark.parametrize("which", ["reg", "cls", "des"])
def test_every_row_of_a_real_run_is_rebuilt_to_the_stored_decision_in_every_language(runs, which):
    tables, cfg, m = _tables(runs[which])
    keys = X.rows(tables)
    assert keys, "a run with audits has rows to read"
    for lang in LANGS:
        set_language(lang)
        for k in keys:
            e = X.explain_row(tables, cfg, *k, manifest=m)
            assert e["consistent"], (lang, k)
            txt = X.text(e)
            A = e["audit"]
            if A is not None:
                for side_ in ("s1", "s2"):
                    S = A[side_]
                    assert abs((S["full"] - S["base"]) - S["mean"]) < 1e-9, \
                        (k, side_, "the two scores shown must differ by exactly the gain shown beside them")
                    for v, th in ((S["mean"], (0.0, cfg["audit"]["verdict"]["margin"])), (S["lo"], (0.0,)), (S["hi"], (0.0,))):
                        assert X.fmt(v, th, 4, True) in txt, (k, side_, v)
                assert A["verdict"] in txt
            sc = tables["screening"]; row = sc[(sc.method_id == k[0]) & (sc.stratum == k[1])]
            if len(row):
                assert row["class"].iloc[0] in txt
    set_language("en")


def test_classification_shows_d_on_the_target_side_and_r2_on_the_control_side(runs):
    tables, cfg, m = _tables(runs["cls"])
    e = X.explain_row(tables, cfg, *X.rows(tables)[0], manifest=m)
    assert e["audit"]["s1"]["metric"] == "D_Tjur" and e["audit"]["s2"]["metric"] == "R2"
    txt = X.text(e)
    assert "D(diab | FMI_DXA)" in txt and "R²(FMI_DXA | diab)" in txt
    from bioms_zaku.i18n import t
    assert t("x.d_note") in txt, "D is named for what it is, including its one-vs-rest average with three or more classes"
    reg = _tables(runs["reg"]); assert t("x.d_note") not in X.text(X.explain_row(reg[0], reg[1], *X.rows(reg[0])[0], manifest=reg[2]))


def test_a_designed_index_is_read_on_the_audit_partition_and_says_so(runs):
    tables, cfg, m = _tables(runs["des"])
    rows = [k for k in X.rows(tables) if k[0] == "Zaku_LMI"]
    assert len(rows) == 1
    e = X.explain_row(tables, cfg, *rows[0], manifest=m)
    assert e["designed"] and e["audit"]["n"] <= m["design"]["n_audit"], "the designed index is judged on the audit partition only"
    from bioms_zaku.i18n import t
    assert ("note", t("x.designed")) in X.lines(e)
    other = X.explain_row(tables, cfg, "Lukaski1985_II", "all", manifest=m)
    assert not other["designed"] and ("note", t("x.designed")) not in X.lines(other)


def test_the_oldest_method_has_nothing_to_repeat_and_an_unknown_row_is_refused_with_the_list(runs):
    tables, cfg, m = _tables(runs["reg"])
    e = X.explain_row(tables, cfg, "Lukaski1985_II", "all", manifest=m)
    assert e["redundancy"]["predecessor"] == "" and not e["redundancy"]["redundant"]
    with pytest.raises(KeyError, match="Lukaski1985_II/all"):
        X.explain_row(tables, cfg, "NoSuchMethod", "all", manifest=m)


def test_the_api_reads_a_finished_run_from_its_result_or_its_folder(runs):
    from bioms_zaku.api import explain
    a = str(explain(runs["reg"], "LMI", "all")); b = str(explain(runs["reg"]["out_dir"], "LMI", "all"))
    assert a == b and "S1" in a and "S2" in a and "LMI" in a
    set_language("pt")
    assert "Mede o alvo além do controle?" in str(explain(runs["reg"], "LMI", "all"))
    set_language("en")


# ---------------------------------------------------------------------------------------------------------------- the report
def _section(html_text: str) -> str:
    i = html_text.index("<section id='read'"); j = html_text.index("</section>", i)
    return html_text[i:j]


def test_the_report_carries_the_reading_between_key_numbers_and_summary_for_every_row(runs):
    res = runs["reg"]; txt = (res["out_dir"] / "report.html").read_text(encoding="utf-8")
    assert txt.index("<section id='key'>") < txt.index("<section id='read'") < txt.index("<section id='summary'>")
    assert "<a href='#read'>" in txt
    tables, cfg, m = _tables(res)
    keys = X.rows(tables); sec = _section(txt)
    assert sec.count("<option ") == len(keys) == sec.count("class='xrow'")
    assert sec.count("class='xrow' data-k='0'>") == 1 and sec.count(" hidden>") == len(keys) - 1, "only the first row is open"
    sc = tables["screening"]
    assert keys[0][:2] == (sc.method_id.iloc[0], sc.stratum.iloc[0]), "it opens on the first row of screening.csv"
    assert "Hoffer1969_H2Z" in sec, "a method not audited is named, with its reason, not dropped in silence"
    assert all(f"<h2 id='{a}'><span class='n'>{n}</span>" in txt for n, a in
               ((2, "key"), (3, "read"), (4, "summary"), (5, "figures"), (6, "results"), (7, "rigor"), (8, "assump"), (9, "refs"), (10, "manifest")))


def test_render_writes_the_same_reading_as_the_run_and_another_language_changes_only_the_words(runs, tmp_path):
    import shutil
    from bioms_zaku.run import render
    src = runs["reg"]["out_dir"]; dst = tmp_path / "copy"; shutil.copytree(src, dst)
    before = _section((src / "report.html").read_text(encoding="utf-8"))
    render(dst, "en", printer=lambda s: None)
    assert _section((dst / "report.html").read_text(encoding="utf-8")) == before, "render must reproduce the run's own reading byte for byte"
    render(dst, "pt", printer=lambda s: None)
    pt = _section((dst / "report.html").read_text(encoding="utf-8"))
    num = lambda s: re.findall(r"[+-]?\d+\.\d+", s)
    assert num(pt) == num(before), "a language changes words, never a number"
    assert "Lendo um resultado" in pt and "present only when" not in pt
    set_language("en")


def test_a_skipped_method_is_named_in_the_language_of_the_report(runs, tmp_path):
    """EN: the reason is recorded in the manifest in English ("missing inputs ['Z100']"); section 3 must say it in the
    report's language, through the same translator `check` uses — found by an existing guarantee (no "missing inputs" in
    a Portuguese report) that the new section would have broken for any run with a skipped method."""
    import shutil
    from bioms_zaku.run import render
    dst = tmp_path / "pt"; shutil.copytree(runs["reg"]["out_dir"], dst)
    render(dst, "pt", printer=lambda s: None)
    sec = _section((dst / "report.html").read_text(encoding="utf-8"))
    assert "Hoffer1969_H2Z (faltam as entradas" in sec and "missing inputs" not in sec
    set_language("en")

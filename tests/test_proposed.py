"""EN: proposed indices (v0.9) — the researcher's own formula audited beside the published methods: no DOI needed, never curated,
never precedence, marked ◇ everywhere, included only when listed."""
from pathlib import Path

import pytest
import yaml

from bioms_zaku.catalog import CatalogError, build_catalog, BUILTIN_PATH
from bioms_zaku.i18n import set_language
import json

ROOT = Path(__file__).resolve().parents[1]
SP = "/tmp/claude-1000/-home-omota-Desktop-redeeixo/d1d0f193-69c4-4a01-868d-6ecba1948d04/scratchpad"


def _cfg(tmp_path, name, entries, include, **over):
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); cfg["output"] = {"dir": str(tmp_path), "figures": over.pop("figures", False)}; cfg["run_name"] = name
    cfg["catalog"] = {"include": include, "user_entries": entries}; cfg["audit"] = {"bootstrap": {"min_oob": 10}, "cv": {"folds": 3}}; cfg["language"] = over.pop("language", "pt")
    cfg.update(over)
    return cfg


MINE = {"id": "meu_indice", "label": "H²·Xc/R (Mota, proposta)", "authors": "Mota", "target": "lean_mass", "expr": "H**2 * Xc / R",
        "provenance": {"formula_source": "proposed", "note": "hipótese"}}
ATAN = {"id": "meu_atan", "authors": "Mota", "target": "cell_mass", "expr": "atan(Xc / R) * H", "provenance": {"formula_source": "proposed"}}


def _raw(entries):
    raw = json.loads(BUILTIN_PATH.read_text(encoding="utf-8")); raw["entries"] = list(raw["entries"]) + entries; return raw


def test_proposed_entry_needs_no_doi_and_gets_explicit_defaults():
    cat = build_catalog(_raw([MINE, ATAN]))
    e = cat["meu_indice"]; assert e.proposed and not e.curated and e.doi is None and e.form == "composite" and e.kind == "index" and e.frequency_khz == (50.0,)
    assert e.validity == {"age": None, "bmi": None, "sex": None, "population": None} and e.provenance["confidence"] == "high"
    assert cat["meu_atan"].label == "meu_atan" and cat["meu_atan"].form == "composite"
    order = [x.id for x in cat.sorted_by_precedence()]
    assert order[-2:] == ["meu_atan", "meu_indice"] or order[-2:] == ["meu_indice", "meu_atan"]        # after every published method
    old = {**MINE, "id": "velho", "year": 1900}
    assert [x.id for x in build_catalog(_raw([old])).sorted_by_precedence()][-1] == "velho"           # even with an earlier year


def test_proposed_entry_rejections():
    with pytest.raises(CatalogError, match="cannot be curated"):
        build_catalog(_raw([{**MINE, "curated": True}]))
    with pytest.raises(CatalogError, match="needs `expr`"):
        build_catalog(_raw([{k: v for k, v in MINE.items() if k != "expr"}]))
    with pytest.raises(CatalogError):
        build_catalog(_raw([{**MINE, "expr": "H**2 * Xc / Rr"}]))                                    # unknown variable: circularity guard
    with pytest.raises(CatalogError):
        build_catalog(_raw([{**MINE, "vector": {"R": -1, "Xc": 1, "H": 1, "W": 0}}]))                # declared vector must be exact
    e = build_catalog(_raw([{**MINE, "vector": {"R": -1, "Xc": 1, "H": 2, "W": 0}}]))["meu_indice"]
    assert e.form == "monomial" and e.vector == {"R": -1, "Xc": 1, "H": 2, "W": 0}


def test_include_semantics_and_run_marks(tmp_path):
    from bioms_zaku.run import run
    from bioms_zaku.check import check
    lines = []; check(_cfg(tmp_path, "c", [MINE], "curated"), printer=lines.append)
    assert any("meu_indice" in l and "include: [curated, meu_indice]" in l for l in lines)            # declared but not included → warning with the fix
    res = run(_cfg(tmp_path, "r", [MINE, ATAN], ["curated", "meu_indice", "meu_atan"], figures=True), printer=lambda s: None)
    alg = res["tables"]["algebra"]; ids = set(alg.method_id)
    assert {"meu_indice", "meu_atan", "Lukaski1985_II"} <= ids and alg[alg.method_id == "meu_indice"].proposed.all() and not alg[alg.method_id == "Lukaski1985_II"].proposed.any()
    assert alg[alg.method_id == "meu_indice"].vector_source.iloc[0] == "fitted" and float(alg[alg.method_id == "meu_indice"].fit_r2.iloc[0]) > 0.999   # a product: fitted vector is exact
    red = res["tables"]["redundancy"]
    published = ~red.method_id.isin(["meu_indice", "meu_atan"])
    assert not red[published].predecessor_id.isin(["meu_indice", "meu_atan"]).any()                   # a proposal never precedes a published method (it may precede another proposal)
    summ = (res["out_dir"] / "summary.md").read_text(encoding="utf-8"); assert "propostos pelo pesquisador (não publicados, ◇): meu_atan, meu_indice" in summ
    txt = (res["out_dir"] / "report.html").read_text(encoding="utf-8")
    assert "2 propostos ◇" in txt and "Mota. H²·Xc/R (Mota, proposta). Índice proposto pelo pesquisador, não publicado (◇)." in txt
    assert (res["out_dir"] / "figures" / "scorecard_all.png").exists() or any(p.name.startswith("scorecard") for p in (res["out_dir"] / "figures").glob("*.png"))
    res2 = run(_cfg(tmp_path, "r2", [MINE], "curated"), printer=lambda s: None)
    assert "meu_indice" not in set(res2["tables"]["algebra"].method_id)                              # default include never audits a proposal
    set_language("en")

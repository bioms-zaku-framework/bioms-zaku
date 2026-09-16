"""EN: v1.1 — the report's assumptions-and-thresholds section: every state read from the run, every threshold from the configuration."""
from pathlib import Path

import yaml

from bioms_zaku.i18n import LANGS, set_language
from test_design_orthogonal import _frame

ROOT = Path(__file__).resolve().parents[1]


def _cfg(tmp_path, lang="pt"):
    p = tmp_path / "a.csv"; _frame(n=500, seed=41).to_csv(p, index=False)
    return {"run_name": "a", "language": lang, "preset": "quick", "data": {"path": str(p), "columns": {"variables": {"R": "R", "Xc": "Xc", "H": "H", "W": "W"},
            "units": {"H": "cm", "W": "kg"}, "targets": {"lean": "lean"}, "controls": {"fat": "fat"}, "covariates": ["W", "H"], "id": "seqn"}},
            "catalog": {"include": ["Lukaski1985_II", "Baumgartner1988_PhA", "Piccoli1994_XcH"]}, "output": {"dir": str(tmp_path), "figures": False},
            "algebra": {"redundancy_threshold": 0.93, "transfer_tol": 0.07}, "audit": {"bootstrap": {"min_oob": 20, "B": 60}, "cv": {"folds": 3, "repeats": 1}, "verdict": {"margin": 0.04}}}


def test_section_states_follow_the_run_and_thresholds_follow_the_configuration(tmp_path):
    from bioms_zaku.run import run, render
    res = run(_cfg(tmp_path), printer=lambda s: None); txt = (res["out_dir"] / "report.html").read_text(encoding="utf-8")
    a = res["tables"]["audit"]
    assert "Pressupostos e limiares" in txt and txt.index("id='rigor'") < txt.index("id='assump'") < txt.index("id='refs'") < txt.index("id='manifest'")
    assert "Redundância por Spearman ≥ 0.93" in txt and "<td class='num'>0.04</td>" in txt and "<td class='num'>0.07</td>" in txt      # thresholds = the resolved configuration
    assert f"reamostras válidas por estrato: {int(a.B_eff.min())} de {int(a.B.max())}" in txt and "escala usada: log" in txt
    assert "k = 3; nível de família 1 − 0,05/k = 0.9833" in txt and "ancorado na literatura" in txt and "Lafontant 2026" in txt and "Cohen 1988" in txt
    assert "excluídas por motivo" in txt and "sem imputação" in txt
    for L in LANGS:
        render(res["out_dir"], L, printer=lambda s: None); t2 = (res["out_dir"] / "report.html").read_text(encoding="utf-8")
        assert "id='assump'" in t2 and ("anchored in the literature" in t2 or "anclado" in t2 or "ancorado" in t2 or "ancorato" in t2)
    set_language("en")

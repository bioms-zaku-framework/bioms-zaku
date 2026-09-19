"""EN: findings of the CrossFit run (2026-09-15): a 33-row audit partition left ONE valid bootstrap resample → zero-width intervals
and spurious verdicts. Guarantees: the audit refuses an unreliable bootstrap; check and start apply the same rule to the audit
partition per stratum; many dropped resamples are warned about; designed indices are named from the target; suggestions never
offer the target/control as a catalog input; the check is printed once; the input text says how many rows went to the design."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from sklearn.linear_model import Ridge

from bioms_zaku.audit import AuditConfig, AuditError, oob_scores
from bioms_zaku.i18n import set_language
from test_design_orthogonal import _frame

ROOT = Path(__file__).resolve().parents[1]


def test_oob_bootstrap_refuses_when_too_few_valid_resamples():
    rng = np.random.default_rng(0); n = 33
    X = rng.normal(size=(n, 1)); Y = (X[:, 0] + rng.normal(size=n)).reshape(-1, 1)
    cfg = AuditConfig(B=200, min_oob=20, seed_bootstrap=42)
    with pytest.raises(AuditError, match="bootstrap (unreliable|impossible)"):     # 33 rows: no or almost no valid resample — refused either way
        oob_scores({"a": X}, Y, "regression", Ridge(), cfg)
    n = 300; X = rng.normal(size=(n, 1)); Y = (X[:, 0] + rng.normal(size=n)).reshape(-1, 1)
    st, b_eff, _ = oob_scores({"a": X}, Y, "regression", Ridge(), AuditConfig(B=100, min_oob=20, seed_bootstrap=42))
    assert b_eff == 100 and st["a"].shape == (100, 1)
    with pytest.raises(AuditError, match="bootstrap unreliable: only 100 of 100"):    # the minimum-valid-resamples rule itself (min_B_eff may exceed B only when forced)
        oob_scores({"a": X}, Y, "regression", Ridge(), AuditConfig(B=100, min_oob=20, seed_bootstrap=42, min_B_eff=101))


def _cfg(tmp_path, n, design=True, **audit):
    p = tmp_path / f"d{n}.csv"; _frame(n=n, seed=2).to_csv(p, index=False)
    cfg = {"run_name": f"d{n}", "language": "pt", "preset": "quick", "data": {"path": str(p), "columns": {"variables": {"R": "R", "Xc": "Xc", "H": "H", "W": "W"},
           "units": {"H": "cm", "W": "kg"}, "targets": {"lean": "lean"}, "controls": {"fat": "fat"}, "covariates": ["W", "H"], "id": "seqn", "groups": {"sexo": "sexo"}}},
           "strata": "sexo", "strata_labels": {0: "F", 1: "M"}, "catalog": {"include": ["Lukaski1985_II", "Piccoli1994_XcH"]},
           "declarations": {"targets_independent_of_variables": True}, "output": {"dir": str(tmp_path), "figures": False},
           "audit": {"bootstrap": {"min_oob": 20, "B": 200, **audit}, "cv": {"folds": 3, "repeats": 1}}}
    if design:
        cfg["design"] = [{"target": "lean", "id": "Zaku_LM"}]
    return cfg


def test_check_and_start_block_a_design_whose_audit_partition_cannot_bootstrap(tmp_path):
    from bioms_zaku.check import CheckError, check
    from bioms_zaku.start import _too_small_for_design
    lines = []
    with pytest.raises(CheckError):                              # 300 rows, 2 sexes → 45 to audit per sex → expected OOB ≈ 17 < 20
        check(_cfg(tmp_path, 300), printer=lines.append)
    assert sum("fora da bolsa esperado ≈" in l and "< min_oob = 20" in l for l in lines) == 2 and any("rodada padrão (sem desenho) não é afetada" in l for l in lines)
    assert any("estrato F deixaria" in l for l in lines) and any("estrato M deixaria" in l for l in lines)   # labelled strata in the message
    msgs = _too_small_for_design(_cfg(tmp_path, 300, design=False)); assert len(msgs) == 2 and all("fora da bolsa esperado" in m for m in msgs)
    lines = []; check(_cfg(tmp_path, 900), printer=lines.append); assert lines[-1].startswith("check: OK")   # 135 to audit per sex → OOB ≈ 50
    assert any(l.strip().startswith("· estrato F: n=") for l in lines) and not any("estrato 0" in l for l in lines)   # labelled count lines
    assert _too_small_for_design(_cfg(tmp_path, 900, design=False)) == []
    lines = []; check(_cfg(tmp_path, 300, design=False), printer=lines.append); assert lines[-1].startswith("check: OK")   # the standard run is fine
    set_language("en")


def test_low_resample_warning_is_raised_per_stratum_only_when_more_than_half_were_dropped():
    from bioms_zaku.run import low_resample_warnings
    rows = [dict(method_id="A", stratum="F", B_eff=787, B=2000), dict(method_id="B", stratum="F", B_eff=1990, B=2000), dict(method_id="A", stratum="M", B_eff=1500, B=2000)]
    w = low_resample_warnings(rows, "F"); assert len(w) == 1 and "only 787–787 of 2000" in w[0] and "1 method(s)" in w[0]
    assert low_resample_warnings(rows, "M") == []


def test_designed_indices_are_named_from_the_target_column():
    from bioms_zaku.start import _suggest_name
    assert _suggest_name("FM_pct", "all", "FM_pct", "x") == "Zaku_FM" and _suggest_name("massa_gorda_dxa_kg", "F", "x", "y") == "Zaku_FM_F"
    assert _suggest_name("massa_magra_dxa_kg", "M", "x", "y") == "Zaku_LM_M" and _suggest_name("FFM%", "all", "x", "y") == "Zaku_LM"
    assert _suggest_name("braco_corrigido_cm", "all", "x", "y") == "Zaku_braco_corrigido_cm"   # unknown meaning: the column name, never a guess


def test_group_inputs_never_suggest_the_target_control_or_covariates(tmp_path):
    from bioms_zaku.start import start
    from bioms_zaku.wizard import init
    df = _frame(n=120, seed=1).rename(columns={"fat": "braco_cm"}); p = tmp_path / "g.csv"; df.to_csv(p, index=False)
    flags = {"R": "R", "Xc": "Xc", "H": "H", "W": "W", "target": "lean", "control": "braco_cm", "independent": "yes", "lang": "pt"}
    out = start(str(p), str(tmp_path / "g.yaml"), ask=None, map_flags=flags, printer=lambda s: None, runner=lambda q: None)
    assert "C_arm" not in yaml.safe_load(out.read_text(encoding="utf-8"))["data"]["columns"]["groups"]     # 'braco_cm' matches the arm pattern but is the control
    out = init(str(p), str(tmp_path / "i.yaml"), map_flags={k: v for k, v in flags.items() if k != "lang"}, lang="pt", printer=lambda s: None)
    assert "C_arm" not in yaml.safe_load(out.read_text(encoding="utf-8"))["data"]["columns"]["groups"]
    set_language("en")


def test_start_prints_the_check_once_and_the_input_text_reports_the_design_rows(tmp_path, monkeypatch):
    import bioms_zaku.start as S
    from bioms_zaku import run as R
    seen = {}
    real = R.run
    def spy(config, *, printer=print, preflight=True):
        seen["preflight"] = preflight; return real(config, printer=printer, preflight=preflight)
    monkeypatch.setattr(R, "run", spy)
    p = tmp_path / "b.csv"; _frame(n=900, seed=4).to_csv(p, index=False); printed = []
    flags = {"R": "R", "Xc": "Xc", "H": "H", "W": "W", "target": "lean", "control": "fat", "strata": "sexo", "labels": "0=F,1=M", "independent": "yes", "lang": "pt"}
    def fast(path):                                               # EN: the default runner, made quick
        cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8")); cfg["preset"] = "quick"; cfg["audit"] = {"bootstrap": {"min_oob": 20, "B": 60}, "cv": {"folds": 3, "repeats": 1}}
        cfg["output"] = {"dir": str(tmp_path), "figures": False}; return R.run(cfg, printer=printed.append, preflight=False)
    S.start(str(p), str(tmp_path / "b.yaml"), ask=None, map_flags=flags, yes=True, printer=printed.append, runner=fast)
    assert seen["preflight"] is False and sum(l.startswith("check: OK") for l in printed) == 2     # one per run (standard + final), never doubled
    txt = (tmp_path / "b_2" / "report.html").read_text(encoding="utf-8")      # v1.2: the final run of start goes to a numbered folder
    assert "usadas só para desenhar os índices; todo número de auditoria vem das outras" in txt
    set_language("en")

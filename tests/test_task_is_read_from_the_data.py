"""
EN: the type of every target and control is READ FROM THE DATA and cannot be declared (decision of 2026-09-21).

`audit.task` used to let a run declare one task for everything. It was applied to EVERY column, so a class target with
a continuous control — which the contract explicitly permits — put stratified folds over a continuous column and
crashed inside scikit-learn, minutes into the run, after `check` had said "OK, ready to run". The key existed only for
the rare case of an integer score that its owner wanted treated as a number; the framework now always decides, and
`check` prints the decision per column before the run costs anything.

What these tests pin: the key is REFUSED rather than silently ignored (nested config keys are merged without
validation, so acceptance would drop the declaration in silence); the inference rule itself, including the case that
looks like an escape hatch and is not; and the scale sensitivity, whose gate could only ever close for the deleted key.

The mixed-type audit itself is covered in test_tjur_classification.py.
"""
import numpy as np
import pytest
import yaml

from pathlib import Path

from bioms_zaku.audit import infer_task
from bioms_zaku.config import resolve

ROOT = Path(__file__).resolve().parents[1]


def test_the_removed_key_is_refused_instead_of_silently_ignored():
    base = yaml.safe_load((ROOT / "tests/minimal.yaml").read_text(encoding="utf-8"))
    base["audit"] = {**base.get("audit", {}), "task": "classification"}
    with pytest.raises(ValueError) as e:
        resolve(base)
    msg = str(e.value)
    assert "audit.task" in msg and "check" in msg          # says what is gone and where the type can be seen
    del base["audit"]["task"]
    resolve(base)                                          # EN: without the key the same configuration resolves


def test_the_type_is_read_from_the_values_and_decimals_do_not_disguise_them():
    """EN: up to 10 whole numbers = a class, anything else a number. Writing a score as 0.0, 1.0, 2.0 does NOT make it a
    number: the rule reads the VALUE, not the dtype, and pandas erases that difference anyway (one missing cell turns an
    integer column into a float one). Pinned so nobody is told otherwise."""
    escore = [0, 1, 2, 3, 4, 5] * 20
    assert infer_task(np.array(escore)) == "classification"                  # integers
    assert infer_task(np.array(escore, dtype=float)) == "classification"     # the same values written with decimals
    assert infer_task(np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5] * 20)) == "regression"
    assert infer_task(np.array([0, 1] * 60)) == "classification"             # binary
    assert infer_task(np.arange(11.0)) == "regression"                       # 11 whole numbers: over the limit
    assert infer_task(np.random.default_rng(0).normal(10, 2, 120)) == "regression"
    assert infer_task(np.array([0.0, 1.0, np.nan] * 40)) == "classification"  # a missing cell changes nothing


def test_a_classification_run_still_reports_the_scale_sensitivity(tmp_path):
    """EN: the gate that skipped this block read the run-level task, and "auto" is never "classification", so it never
    closed — it could only close for the deleted key. Contract §4 promises the block whenever it is enabled, with no
    exception for classification. Run end to end on a class target with a continuous control."""
    from bioms_zaku.run import run
    cfg = yaml.safe_load((ROOT / "tests/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "tests/minimal_data.csv")
    cfg["data"]["columns"]["targets"] = {"diab": "diab"}
    cfg["data"]["columns"]["controls"] = {"FMI_DXA": "fmi_dxa"}
    cfg["strata"] = None
    cfg["preset"] = "full"                       # EN: the quick preset forces sensitivity.scale off; sizes cut by hand
    cfg["audit"] = {"bootstrap": {"B": 60, "min_oob": 10, "min_B_eff": 20}, "cv": {"folds": 3, "repeats": 2},
                    "sensitivity": {"scale": True}}
    cfg["output"] = {"dir": str(tmp_path), "figures": False}
    cfg["run_name"] = "cls_scale"
    res = run(cfg, printer=lambda s: None)

    aud = res["tables"]["audit"]
    assert (aud["task"] == "classification").all() and (aud["control_task"] == "regression").all()
    assert (aud["metric"] == "D_Tjur").all() and (aud["metric_control"] == "R2").all()

    sens = res["tables"]["sensitivity_scale"]
    assert sens is not None and not sens.empty, "a classification run must still report the other scale"
    assert set(sens["method_id"]) <= set(aud["method_id"]) and (sens["scale"] != sens["scale_primary"]).all()

"""EN: v1.2 — ONE example base (zaku_exemplo, synthetic, generated per sex × diabetes from NHANES) reachable after installation
(API and `bioms-zaku examples`), copied by default without ever overwriting; technical files only on request."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bioms_zaku.datasets import EXAMPLES, copy_examples, example_path, list_examples, load_example

ROOT = Path(__file__).resolve().parents[1]


def test_the_one_example_is_listed_by_default_and_the_technical_files_only_with_all():
    main = list_examples()
    assert [r["name"] for r in main] == ["zaku_exemplo"] and main[0]["kind"] == "synthetic" and main[0]["rows"] == 400
    rows = {r["name"]: r for r in list_examples(all=True)}
    assert list(rows) == list(EXAMPLES) and rows["nhanes_diabetes_400"]["kind"] == "real"
    for name in EXAMPLES:
        assert len(load_example(name)) == rows[name]["rows"] and example_path(name).exists()
    with pytest.raises(KeyError):
        load_example("nope")


def test_the_one_example_serves_regression_classification_with_a_known_answer_and_diabetes():
    df = load_example("zaku_exemplo")
    need = {"id", "sexo", "R", "Xc", "H_cm", "W", "idade", "BMXARMC", "BMXWAIST", "BMXCALF", "LMI_DXA", "ALMI_DXA", "FMI_DXA",
            "lean_kg", "alm_kg", "fat_kg", "label_synthetic", "diabetes"}
    assert need <= set(df.columns) and df.id.is_unique and df.sexo.value_counts().to_dict() == {0: 200, 1: 200}
    g = df.groupby("sexo")
    assert g.diabetes.sum().to_dict() == {0: 70, 1: 70}
    for col in ("diabetes", "label_synthetic"):                         # ≥ 20 per class per sex (classification minimum)
        assert (g[col].sum() >= 20).all() and ((g[col].count() - g[col].sum()) >= 20).all()
    assert (df[["R", "Xc", "H_cm", "W", "LMI_DXA", "FMI_DXA"]] > 0).all().all()


def test_the_one_example_is_reproduced_byte_for_byte_from_its_published_parameters(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "tools/make_zaku_example.py"), "--from-params", str(ROOT / "examples/zaku_exemplo_params.json"), str(tmp_path)],
                   check=True, capture_output=True)
    assert (tmp_path / "zaku_exemplo.csv").read_bytes() == (ROOT / "examples/zaku_exemplo.csv").read_bytes()
    P = json.loads((ROOT / "examples/zaku_exemplo_params.json").read_text(encoding="utf-8"))
    assert set(P["cells"]) == {"sex0_diabetes0", "sex0_diabetes1", "sex1_diabetes0", "sex1_diabetes1"}
    for c in P["cells"].values():                                        # every cell covariance is a valid covariance
        S = np.array(c["sigma_log"]); assert np.allclose(S, S.T) and np.linalg.eigvalsh(S).min() > 0 and c["n_source"] >= 60


def test_copy_never_overwrites_and_technical_yaml_checks_from_its_folder(tmp_path, monkeypatch):
    f1 = copy_examples(tmp_path / "ex"); f2 = copy_examples(tmp_path / "ex", ["minimal"])
    assert f1.name == "ex" and sorted(p.name for p in f1.iterdir()) == ["zaku_exemplo.csv", "zaku_exemplo.ipynb", "zaku_exemplo_params.json"]
    assert f2.name == "ex_2" and sorted(p.name for p in f2.iterdir()) == ["minimal.yaml", "minimal_data.csv"]
    assert "path: minimal_data.csv" in (f2 / "minimal.yaml").read_text(encoding="utf-8")
    monkeypatch.chdir(f2)
    from bioms_zaku.check import check
    assert not check("minimal.yaml", printer=lambda s: None)["errors"]


def test_examples_command_lists_and_copies_the_one_example(tmp_path, monkeypatch, capsys):
    from bioms_zaku.cli import main
    monkeypatch.chdir(tmp_path)
    assert main(["--lang", "pt", "examples"]) == 0
    out = capsys.readouterr().out
    assert "zaku_exemplo" in out and "synthetic_8000" not in out and "--all" in out
    assert main(["--lang", "pt", "examples", "--all"]) == 0 and "REAL" in capsys.readouterr().out
    assert main(["--lang", "pt", "examples", "--copy"]) == 0
    assert sorted(p.name for p in (tmp_path / "zaku_exemplos").iterdir()) == ["zaku_exemplo.csv", "zaku_exemplo.ipynb", "zaku_exemplo_params.json"]
    assert "bioms-zaku start zaku_exemplo.csv" in capsys.readouterr().out


def test_the_installed_package_carries_only_the_one_base(tmp_path, monkeypatch):
    """EN: the wheel ships zaku_exemplo only (2026-09-19): 700 KB of technical files were reaching every installation
    for data the researcher never uses. Listing must not crash when they are absent, and copying one must say where it
    is. Simulated by pointing the example folder at one holding only the base."""
    import bioms_zaku.datasets as D
    for n in ("zaku_exemplo.csv", "zaku_exemplo_params.json", "zaku_exemplo.ipynb"):
        shutil.copy(ROOT / "examples" / n, tmp_path / n)
    monkeypatch.setattr(D, "examples_dir", lambda: tmp_path)
    nomes = [r["name"] for r in D.list_examples(all=True)]
    assert nomes == ["zaku_exemplo"], f"listing must skip what the package does not ship: {nomes}"
    destino = D.copy_examples(tmp_path / "saida")
    assert sorted(p.name for p in destino.iterdir()) == ["zaku_exemplo.csv", "zaku_exemplo.ipynb", "zaku_exemplo_params.json"]
    with pytest.raises(FileNotFoundError, match="repository"):
        D.copy_examples(tmp_path / "outra", ["minimal"])

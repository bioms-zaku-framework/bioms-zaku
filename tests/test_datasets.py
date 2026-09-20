"""EN: ONE example base (zaku_exemplo, synthetic, generated per sex × diabetes from NHANES moments) reachable after
installation — through the API and `bioms-zaku examples` — and copied without ever overwriting. The base is the only
one the tool ships: the older 8000-row synthetic example, the spreadsheet-format file and the real NHANES sample were
removed on 2026-09-20 (the tool needs one example that covers regression and classification, and this one does)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from bioms_zaku.datasets import EXAMPLES, copy_examples, example_path, list_examples, load_example

ROOT = Path(__file__).resolve().parents[1]
FILES = ["zaku_exemplo.csv", "zaku_exemplo.ipynb", "zaku_exemplo_params.json"]


def test_there_is_exactly_one_example_and_it_is_listed():
    rows = list_examples()
    assert [r["name"] for r in rows] == ["zaku_exemplo"] == list(EXAMPLES)
    assert rows[0]["kind"] == "synthetic" and rows[0]["rows"] == 400
    assert len(load_example("zaku_exemplo")) == 400 and example_path("zaku_exemplo").exists()
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


def test_copy_never_overwrites_an_existing_folder(tmp_path):
    f1 = copy_examples(tmp_path / "ex")
    f2 = copy_examples(tmp_path / "ex")
    assert f1.name == "ex" and f2.name == "ex_2"
    assert sorted(p.name for p in f1.iterdir()) == FILES == sorted(p.name for p in f2.iterdir())


def test_examples_command_lists_and_copies_the_one_example(tmp_path, monkeypatch, capsys):
    from bioms_zaku.cli import main
    monkeypatch.chdir(tmp_path)
    assert main(["--lang", "pt", "examples"]) == 0
    out = capsys.readouterr().out
    assert "zaku_exemplo" in out and "sintético" in out
    assert main(["--lang", "pt", "examples", "--copy"]) == 0
    assert sorted(p.name for p in (tmp_path / "zaku_exemplos").iterdir()) == FILES
    assert "bioms-zaku start zaku_exemplo.csv" in capsys.readouterr().out


def test_copying_says_where_the_files_are_when_they_are_absent(tmp_path, monkeypatch):
    """EN: the failure a user meets with a broken installation — the message must name where the files live."""
    import bioms_zaku.datasets as D
    monkeypatch.setattr(D, "examples_dir", lambda: tmp_path)
    with pytest.raises(FileNotFoundError, match="repository"):
        D.copy_examples(tmp_path / "saida")
    for n in FILES:                                                      # EN: present again → copying works
        shutil.copy(ROOT / "examples" / n, tmp_path / n)
    assert sorted(p.name for p in D.copy_examples(tmp_path / "ok").iterdir()) == FILES

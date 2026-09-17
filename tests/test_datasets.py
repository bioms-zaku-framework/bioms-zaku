"""EN: v1.2 — the bundled example data are reachable after installation (API and `bioms-zaku examples`), labelled synthetic or real,
copied without ever overwriting, and the copied YAMLs run from their own folder."""
import pandas as pd
import pytest

from bioms_zaku.datasets import EXAMPLES, copy_examples, example_path, list_examples, load_example


def test_every_example_is_listed_with_its_kind_and_loads():
    rows = {r["name"]: r for r in list_examples()}
    assert list(rows) == list(EXAMPLES)
    assert rows["nhanes_diabetes_400"]["kind"] == "real" and {rows[k]["kind"] for k in ("synthetic_400", "synthetic_8000", "minimal")} == {"synthetic"}
    assert (rows["synthetic_400"]["rows"], rows["synthetic_8000"]["rows"], rows["minimal"]["rows"], rows["nhanes_diabetes_400"]["rows"]) == (400, 8000, 150, 400)
    for name in EXAMPLES:
        df = load_example(name); assert len(df) == rows[name]["rows"] and example_path(name).exists()
    with pytest.raises(KeyError):
        load_example("nope")


def test_the_400_row_cut_is_the_first_200_per_sex_of_the_published_synthetic_file_and_keeps_20_cases_per_class():
    full = load_example("synthetic_8000"); cut = load_example("synthetic_400")
    pd.testing.assert_frame_equal(cut.reset_index(drop=True), full.groupby("sexo", sort=True).head(200).reset_index(drop=True))
    assert (cut.groupby("sexo").label_synthetic.agg(["sum", "count"]).assign(neg=lambda d: d["count"] - d["sum"])[["sum", "neg"]] >= 20).all().all()


def test_copy_never_overwrites_and_the_copied_yaml_checks_from_its_folder(tmp_path, monkeypatch):
    f1 = copy_examples(tmp_path / "ex"); f2 = copy_examples(tmp_path / "ex", ["minimal"])
    assert f1.name == "ex" and f2.name == "ex_2" and sorted(p.name for p in f2.iterdir()) == ["minimal.yaml", "minimal_data.csv"]
    assert "path: minimal_data.csv" in (f1 / "minimal.yaml").read_text(encoding="utf-8")
    monkeypatch.chdir(f1)
    from bioms_zaku.check import check
    rep = check("minimal.yaml", printer=lambda s: None)
    assert not rep["errors"]


def test_examples_command_lists_and_copies(tmp_path, monkeypatch, capsys):
    from bioms_zaku.cli import main
    monkeypatch.chdir(tmp_path)
    assert main(["--lang", "pt", "examples"]) == 0
    out = capsys.readouterr().out
    assert "synthetic_400" in out and "REAL" in out and "bioms-zaku examples --copy" in out
    assert main(["--lang", "pt", "examples", "--copy", "--name", "synthetic_400"]) == 0
    assert (tmp_path / "zaku_exemplos" / "example_data_400.csv").exists() and "cd zaku_exemplos" in capsys.readouterr().out

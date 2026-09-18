"""EN: the example notebook ships with the package and runs from a plain `pip install`: the data come from inside the
package (no download, no path to fix), and `examples --copy` hands it over together with the CSV."""
import json

from bioms_zaku.datasets import copy_examples, examples_dir

NB = "zaku_exemplo.ipynb"


def _nb() -> dict:
    return json.loads((examples_dir() / NB).read_text(encoding="utf-8"))


def test_notebook_ships_with_the_package_and_is_a_valid_notebook():
    nb = _nb()
    assert nb["nbformat"] == 4 and nb["cells"], "the notebook must ship inside the package (bioms_zaku/examples)"


def test_first_code_cell_installs_the_package_the_standard_way():
    first = next(c for c in _nb()["cells"] if c["cell_type"] == "code")
    assert "pip install" in "".join(first["source"]) and "bioms-zaku" in "".join(first["source"])


def test_the_data_come_from_the_package_never_from_a_download():
    src = "\n".join("".join(c["source"]) for c in _nb()["cells"] if c["cell_type"] == "code")
    assert "load_example" in src and "example_path" in src
    for forbidden in ("wget", "curl", "urlretrieve", "read_csv('http", 'read_csv("http', "files.upload"):
        assert forbidden not in src, f"the notebook must not need {forbidden}: the data ship with the package"


def test_ships_no_stored_outputs():
    for c in _nb()["cells"]:
        assert not c.get("outputs"), "the notebook ships clean: the reader runs it and sees their own numbers"


def test_copy_examples_hands_over_data_and_notebook_together(tmp_path):
    folder = copy_examples(tmp_path / "exemplos")
    names = {p.name for p in folder.iterdir()}
    assert {"zaku_exemplo.csv", NB} <= names

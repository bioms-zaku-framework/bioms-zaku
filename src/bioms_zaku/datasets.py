"""
EN: The bundled example data, available after `pip install` (v1.2). The files live in `bioms_zaku/examples` inside the installed
    package (copied from the repository's `examples/` at build time) or, in a source checkout, in `examples/` at the repository
    root. Nothing is downloaded.

    Python:
        from bioms_zaku.datasets import list_examples, example_path, load_example, copy_examples
        df = load_example("zaku_exemplo")             # pandas DataFrame (the one example)
        folder = copy_examples("my_folder")           # CSVs + ready YAMLs, never overwriting (my_folder_2, …)
    Terminal:
        bioms-zaku examples [--all]                   # list (the one example; --all adds the technical files)
        bioms-zaku examples --copy [FOLDER]           # copy, then: cd FOLDER && bioms-zaku start zaku_exemplo.csv

    Two kinds, always said aloud: SYNTHETIC files are draws from a log-normal whose μ and Σ were estimated on NHANES 1999–2004
    (no real row); the REAL file holds NHANES 1999–2004 public-use rows (public domain), with its provenance JSON.
"""
from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

import pandas as pd

# EN: name -> main CSV, reading options, companion files, kind. Order = order shown to the user.
EXAMPLES: dict[str, dict] = {
    # EN: THE example (decision of 2026-09-17): one synthetic base for every use — copied by default.
    "zaku_exemplo": {"csv": "zaku_exemplo.csv", "sep": ",", "decimal": ".", "kind": "synthetic", "main": True,
                     "files": ["zaku_exemplo.csv", "zaku_exemplo_params.json", "zaku_exemplo.ipynb"]},
    # EN: technical files (reproducibility of the older synthetic example, spreadsheet format, the real NHANES sample):
    #     listed and copied only on request (`--all` / `--name`).
    "synthetic_8000": {"csv": "example_data.csv", "sep": ",", "decimal": ".", "kind": "synthetic", "main": False,
                       "files": ["example_data.csv", "example_data_params.json", "example_quick.yaml", "example_full.yaml", "example_kg.yaml"]},
    "minimal": {"csv": "minimal_data.csv", "sep": ";", "decimal": ",", "kind": "synthetic", "main": False,
                "files": ["minimal_data.csv", "minimal.yaml"]},
    "nhanes_diabetes_400": {"csv": "nhanes_diabetes_400.csv", "sep": ",", "decimal": ".", "kind": "real", "main": False,
                            "files": ["nhanes_diabetes_400.csv", "nhanes_diabetes_400_provenance.json"]},
}


def examples_dir() -> Path:
    """EN: the folder holding the example files (installed package first, then a source checkout)."""
    try:
        p = resources.files("bioms_zaku").joinpath("examples")
        if p.is_dir():
            return Path(str(p))
    except (ModuleNotFoundError, TypeError):
        pass
    p = Path(__file__).resolve().parents[2] / "examples"
    if p.is_dir():
        return p
    raise FileNotFoundError("example data not found: reinstall bioms-zaku (the wheel ships bioms_zaku/examples)")


def list_examples(all: bool = False) -> list[dict]:
    """EN: one dict per example (the main one; all=True adds the technical files): name, kind, rows, columns, files, description."""
    from .i18n import t
    d = examples_dir(); out = []
    for name, e in EXAMPLES.items():
        if not (all or e["main"]):
            continue
        if not (d / e["csv"]).exists():
            continue        # EN: technical file not shipped in the wheel (2026-09-19); it lives in the repository
        df = pd.read_csv(d / e["csv"], sep=e["sep"], decimal=e["decimal"])
        out.append({"name": name, "kind": e["kind"], "main": bool(e["main"]), "rows": int(len(df)), "columns": list(df.columns), "csv": e["csv"],
                    "files": list(e["files"]), "description": t(f"ex.{name}")})
    return out


def example_path(name: str) -> Path:
    """EN: absolute path of the main CSV of an example."""
    if name not in EXAMPLES:
        raise KeyError(f"unknown example {name!r}; choose one of {sorted(EXAMPLES)}")
    return examples_dir() / EXAMPLES[name]["csv"]


def load_example(name: str) -> pd.DataFrame:
    """EN: the main CSV of an example as a DataFrame."""
    e = EXAMPLES.get(name)
    if e is None:
        raise KeyError(f"unknown example {name!r}; choose one of {sorted(EXAMPLES)}")
    return pd.read_csv(examples_dir() / e["csv"], sep=e["sep"], decimal=e["decimal"])


def _free_folder(base: Path) -> Path:
    if not base.exists() or not any(base.iterdir()):
        return base
    k = 2
    while (base.parent / f"{base.name}_{k}").exists() and any((base.parent / f"{base.name}_{k}").iterdir()):
        k += 1
    return base.parent / f"{base.name}_{k}"


def copy_examples(dest: str | Path | None = None, names: list[str] | None = None) -> Path:
    """
    EN: copy the example files (default: the one example; `names` for technical files) into `dest` (default ./zaku_exemplos); an existing non-empty folder is never touched — the copy
        goes to dest_2, dest_3, … The YAML files are rewritten to read their CSV from the same folder (run them from inside it).
        Returns the folder actually used.
    """
    src = examples_dir()
    names = list(names or [n for n, e in EXAMPLES.items() if e["main"]])      # EN: default = the one example
    bad = [n for n in names if n not in EXAMPLES]
    if bad:
        raise KeyError(f"unknown example(s) {bad}; choose among {sorted(EXAMPLES)}")
    faltando = [n for n in names if not (src / EXAMPLES[n]["csv"]).exists()]
    if faltando:
        raise FileNotFoundError(
            f"example(s) {faltando} are not shipped in the installed package (only 'zaku_exemplo' is): "
            "they live in the repository, under examples/ — clone it or download them from the project page")
    folder = _free_folder(Path(dest or "zaku_exemplos"))
    folder.mkdir(parents=True, exist_ok=True)
    for n in names:
        for f in EXAMPLES[n]["files"]:
            if f.endswith(".yaml"):
                txt = (src / f).read_text(encoding="utf-8").replace("path: examples/", "path: ")
                (folder / f).write_text(txt, encoding="utf-8")
            else:
                shutil.copyfile(src / f, folder / f)
    return folder

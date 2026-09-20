"""
EN: The bundled example data, available after `pip install`. ONE base (the decision of 2026-09-17, made exclusive on
    2026-09-20): `zaku_exemplo.csv`, synthetic, drawn per sex × diabetes from means and covariances estimated on
    NHANES 1999–2004 — no real row — and serving every use the tool has: regression, classification with a known
    answer, and a class target from a medical diagnosis. The files live in `bioms_zaku/examples` inside the installed
    package (copied from the repository's `examples/` at build time) or, in a source checkout, in `examples/` at the
    repository root. Nothing is downloaded.

    Python:
        from bioms_zaku.datasets import list_examples, example_path, load_example, copy_examples
        df = load_example("zaku_exemplo")             # pandas DataFrame
        folder = copy_examples("my_folder")           # CSV + parameters + notebook, never overwriting (my_folder_2, …)
    Terminal:
        bioms-zaku examples                           # list it
        bioms-zaku examples --copy [FOLDER]           # copy, then: cd FOLDER && bioms-zaku start zaku_exemplo.csv
"""
from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

import pandas as pd

# EN: name -> main CSV, reading options, companion files, kind. Said aloud: the base is SYNTHETIC — a draw from a
#     log-normal whose μ and Σ were estimated on NHANES 1999–2004, holding no real person's row.
EXAMPLES: dict[str, dict] = {
    "zaku_exemplo": {"csv": "zaku_exemplo.csv", "sep": ",", "decimal": ".", "kind": "synthetic",
                     "files": ["zaku_exemplo.csv", "zaku_exemplo_params.json", "zaku_exemplo.ipynb"]},
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


def list_examples() -> list[dict]:
    """EN: one dict per example: name, kind, rows, columns, files, description."""
    from .i18n import t
    d = examples_dir(); out = []
    for name, e in EXAMPLES.items():
        df = pd.read_csv(d / e["csv"], sep=e["sep"], decimal=e["decimal"])
        out.append({"name": name, "kind": e["kind"], "rows": int(len(df)), "columns": list(df.columns),
                    "csv": e["csv"], "files": list(e["files"]), "description": t(f"ex.{name}")})
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
    EN: copy the example files into `dest` (default ./zaku_exemplos); an existing non-empty folder is never touched —
        the copy goes to dest_2, dest_3, … Returns the folder actually used.
    """
    src = examples_dir()
    names = list(names or EXAMPLES)
    bad = [n for n in names if n not in EXAMPLES]
    if bad:
        raise KeyError(f"unknown example(s) {bad}; choose among {sorted(EXAMPLES)}")
    missing = [n for n in names if not (src / EXAMPLES[n]["csv"]).exists()]
    if missing:
        raise FileNotFoundError(f"example(s) {missing} not found in {src}: reinstall bioms-zaku, or run from a clone "
                                "of the repository, where they live under examples/")
    folder = _free_folder(Path(dest or "zaku_exemplos"))
    folder.mkdir(parents=True, exist_ok=True)
    for n in names:
        for f in EXAMPLES[n]["files"]:
            shutil.copyfile(src / f, folder / f)
    return folder

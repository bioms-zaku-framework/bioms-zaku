"""EN: the public API lives in `bioms_zaku.api` and is callable: `from bioms_zaku import run` handed back the MODULE,
so run(config) raised TypeError (found writing the example notebook, 2026-09-18). It is a module of its own because
`run` and `check` share their names with `run.py` and `check.py` — exported on the package, the same attribute would
mean the function or the module depending on import order, and two tests broke exactly that way. This file guards
both: the surface is callable, and the package never shadows its own modules."""
import os
import subprocess
import sys
import types
from pathlib import Path

import bioms_zaku
import bioms_zaku.api as api

SURFACE = ("check", "run", "render", "set_language", "load_example", "example_path", "list_examples", "copy_examples")


def test_the_names_a_notebook_needs_are_functions_not_modules():
    for name in SURFACE:
        obj = getattr(api, name)
        assert callable(obj) and not isinstance(obj, types.ModuleType), f"bioms_zaku.api.{name} must be the function"


def test_all_declares_the_surface_and_the_version():
    assert set(SURFACE) | {"__version__", "SCHEMA_VERSION"} <= set(api.__all__)


def test_the_package_never_shadows_its_own_modules():
    """EN: `bioms_zaku.run` and `bioms_zaku.check` must stay the modules — an attribute that changes meaning with
    import order is a defect, not a convenience (2026-09-18)."""
    import bioms_zaku.check, bioms_zaku.run      # noqa: F401
    for name in ("run", "check"):
        assert isinstance(getattr(bioms_zaku, name), types.ModuleType), f"bioms_zaku.{name} must be the module"


def test_a_fresh_interpreter_imports_without_a_circular_import():
    src = Path(__file__).resolve().parents[1] / "src"          # EN: the code under test, not an older install
    r = subprocess.run([sys.executable, "-c", "from bioms_zaku.api import run, check, render; run; check; render"],
                       capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(src)})
    assert r.returncode == 0, r.stderr

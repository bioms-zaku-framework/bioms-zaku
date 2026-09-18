"""
EN: the public surface in ONE place: `from bioms_zaku.api import check, run, load_example` and nothing else to learn.
    It is a module of its own, and not names on the package, because the functions `run` and `check` share their names
    with the modules `run.py` and `check.py`: exported on the package, `bioms_zaku.run` would mean the function or the
    module depending on which import happened first. Found on 2026-09-18, writing the example notebook, where
    `from bioms_zaku import run` handed back the module and `run(config)` raised TypeError.
ES: la superficie pública en UN lugar (los nombres run/check chocan con sus módulos, por eso no van en el paquete).
PT: a superfície pública em UM lugar (os nomes run/check colidem com seus módulos, por isso não vão no pacote).
IT: la superficie pubblica in UN posto (i nomi run/check collidono con i loro moduli, quindi non vanno nel pacchetto).
"""
from . import SCHEMA_VERSION, __version__
from .check import check
from .datasets import copy_examples, example_path, list_examples, load_example
from .i18n import set_language
from .run import render, run

__all__ = ["__version__", "SCHEMA_VERSION", "check", "run", "render", "set_language",
           "load_example", "example_path", "list_examples", "copy_examples"]

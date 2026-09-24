import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest


@pytest.fixture(autouse=True)
def _idioma_limpo():
    """
    EN: every test starts from English. Several tests loop over the four languages and leave the last one set; that was
        harmless while `resolve()` overwrote the language with the configuration's default on every run, and stopped
        being harmless on 2026-09-24, when a configuration that does NOT declare a language began keeping the one
        already chosen — the fix for an API that silently discarded `set_language()`. The leak was always there; it
        simply had nothing to break. Resetting here removes the whole class, not the one case that surfaced.
    """
    from bioms_zaku.i18n import set_language
    set_language("en")
    yield
    set_language("en")

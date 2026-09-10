"""EN: migration is deterministic and yields 31 entries. ES/PT: migración/migração determinística, 31 entradas."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = Path.home() / "Desktop/bioms_2/catalogo/metodos_bia.json"


def test_migration_is_deterministic_and_matches_shipped_catalog(tmp_path):
    if not LEGACY.exists():
        import pytest; pytest.skip("legacy catalog not on this machine")
    out = tmp_path / "cat.json"
    subprocess.run([sys.executable, str(ROOT / "tools/migrate_catalog.py"), str(LEGACY), str(out)], check=True, capture_output=True)
    a = json.loads(out.read_text(encoding="utf-8")); b = json.loads((ROOT / "data/catalog_v1.json").read_text(encoding="utf-8"))
    assert len(a["entries"]) == 31 and a == b

"""EN: migration is deterministic and reproduces the frozen 31-entry snapshot of 2026-09-08 (the shipped catalog has since
evolved by curation; see `history` in data/catalog_v1.json). ES/PT: migração determinística contra a fixture congelada."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = Path.home() / "Desktop/bioms_2/catalogo/metodos_bia.json"


FROZEN = ROOT / "tests/fixtures/catalog_v1_migrated_2026-09-08.json"


def test_migration_is_deterministic_and_matches_frozen_snapshot(tmp_path):
    if not LEGACY.exists():
        import pytest; pytest.skip("legacy catalog not on this machine")
    out = tmp_path / "cat.json"
    subprocess.run([sys.executable, str(ROOT / "tools/migrate_catalog.py"), str(LEGACY), str(out)], check=True, capture_output=True)
    a = json.loads(out.read_text(encoding="utf-8")); b = json.loads(FROZEN.read_text(encoding="utf-8"))
    assert len(a["entries"]) == 31 and a == b

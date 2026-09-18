"""EN: the contract must not promise what the code refuses. Found on 2026-09-18: §1.1 and §1.4 still described a
'cluster mode' for a repeated id, while the decision of 2026-09-16 (§3.2) refuses it and `io.py` raises. A normative
document that contradicts itself is worse than none, so this test pins the pair that was wrong."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_repeated_id_is_refused_everywhere_it_is_described():
    contract = (ROOT / "CONTRATOS.md").read_text(encoding="utf-8")
    code = (ROOT / "src/bioms_zaku/io.py").read_text(encoding="utf-8")
    assert "repeated id in" in code, "io.py no longer refuses a repeated id: the contract must be revisited"
    assert "modo cluster" not in contract, "the contract promises a cluster mode the code refuses"
    assert "uma linha por pessoa" in contract.lower()

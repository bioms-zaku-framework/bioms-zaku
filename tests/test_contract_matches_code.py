"""EN: the contract must not promise what the code refuses. Found on 2026-09-18: §1.1 and §1.4 still described a
'cluster mode' for a repeated id, while the decision of 2026-09-16 (§3.2) refuses it and `io.py` raises. A normative
document that contradicts itself is worse than none, so this test pins the pair that was wrong.

The assertions read the NORMATIVE sections only (§0 to §5). Section 6 is the dated record, and it legitimately names
what was removed — checking it too would flag the record of a correction as the defect it describes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _normative() -> str:
    """EN: the contract up to the change log — what the tool promises today, without its history."""
    text = (ROOT / "CONTRACTS.md").read_text(encoding="utf-8")
    return text[:text.index("## 6. Change log")].lower()


def test_repeated_id_is_refused_everywhere_it_is_described():
    contract = _normative()
    code = (ROOT / "src/bioms_zaku/io.py").read_text(encoding="utf-8")
    assert "repeated id in" in code, "io.py no longer refuses a repeated id: the contract must be revisited"
    assert "cluster mode" not in contract, "the contract promises a cluster mode the code refuses"
    assert "one row per person" in contract

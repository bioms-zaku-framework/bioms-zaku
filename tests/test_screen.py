"""EN: screening classes are fixed and complete. ES/PT: classes de triagem fixas e completas."""
import pandas as pd
from bioms_zaku.screen import screening_table


def test_screening_classes():
    red = pd.DataFrame([dict(method_id=m, stratum="s", redundant=r, identity_of=i) for m, r, i in
                        [("A", False, None), ("B", True, None), ("C", False, None), ("D", False, "A"), ("E", True, None)]])
    aud = pd.DataFrame([dict(method_id=m, stratum="s", target="t", verdict=v) for m, v in
                        [("A", "SPECIFIC"), ("B", "SPECIFIC"), ("C", "TRACKS_CONTROL"), ("D", "SPECIFIC"), ("E", "INCONCLUSIVE")]])
    uti = pd.DataFrame([dict(method_id=m, stratum="s", target="t", useful=u) for m, u in [("A", True), ("B", False), ("C", True), ("D", True), ("E", True)]])
    out = screening_table(red, aud, uti).set_index("method_id")["class"].to_dict()
    assert out == {"A": "original-specific-useful", "B": "redundant-specific-notuseful", "C": "original-tracks-control-useful",
                   "D": "identity", "E": "inconclusive"}                      # E: no real verdict → the only inconclusive
    # EN: BOTH and NEITHER are conclusive verdicts of the conditional rule (found on a real report, 2026-09-15)
    aud2 = pd.DataFrame([dict(method_id=m, stratum="s", target="t", verdict=v) for m, v in [("A", "BOTH"), ("B", "NEITHER")]])
    red2 = red[red.method_id.isin(["A", "B"])]; uti2 = uti[uti.method_id.isin(["A", "B"])]
    out2 = screening_table(red2, aud2, uti2).set_index("method_id")["class"].to_dict()
    assert out2 == {"A": "original-both-useful", "B": "redundant-no-signal-notuseful"}


def test_screening_without_utility():
    red = pd.DataFrame([dict(method_id="A", stratum="s", redundant=False, identity_of=None)])
    aud = pd.DataFrame([dict(method_id="A", stratum="s", target="t", verdict="SPECIFIC")])
    assert screening_table(red, aud, None)["class"].iloc[0] == "original-specific-notuseful"

"""EN: report v0.9 — references are verified records, tied to the result blocks and to the methods of the run."""
import json
import re
from pathlib import Path

from bioms_zaku import references as R
from bioms_zaku.catalog import BUILTIN_PATH
from bioms_zaku.html import BLOCKS

ROOT = Path(__file__).resolve().parents[1]


def test_every_catalog_doi_has_a_verified_record():
    cat = json.loads(BUILTIN_PATH.read_text(encoding="utf-8"))
    dois = {e["doi"] for e in cat["entries"] if e.get("doi")}
    missing = sorted(d for d in dois if d not in R.RECORDS)
    assert not missing, missing
    for e in cat["entries"]:
        if e.get("curated"):
            assert e["doi"] in R.RECORDS and R.RECORDS[e["doi"]]["title"], e["id"]


def test_records_are_clean_and_keys_resolve():
    for k, r in {**R.RECORDS, **R.RECORDS_NO_DOI}.items():
        assert r["authors"] and r["title"] and r["journal"] and isinstance(r["year"], int), k
        assert "&amp;" not in json.dumps(r) and "\n" not in json.dumps(r), k
    assert "10.1097/ede.0b013e3181e4bfd7" not in R.RECORDS            # the erratum DOI of Lipsitch 2010 — rejected at verification
    assert R.RECORDS["10.1097/ede.0b013e3181d61eeb"]["title"].startswith("Negative Controls")
    assert "10.1111/sms.12780" not in R.RECORDS                        # not an allometry reference — rejected
    for k, blocks in R.METHOD_REFS:
        assert R.record(k) is not None, k
        assert set(blocks) <= {b for b, _ in BLOCKS}, (k, blocks)
    for k in R.SOFTWARE_REFS:
        assert R.record(k) is not None, k
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", R.VERIFIED_ON)


def test_cite_format_and_links():
    txt, url = R.cite("10.1097/ede.0b013e3181d61eeb")
    assert txt == "Lipsitch M, Tchetgen Tchetgen E, Cohen T. Negative Controls: A Tool for Detecting Confounding and Bias in Observational Studies. Epidemiology. 2010;21(3):383-388."
    assert url == "https://doi.org/10.1097/ede.0b013e3181d61eeb"
    txt, url = R.cite("bengio2004"); assert url.startswith("https://www.jmlr.org/") and "2004;5:1089-1105." in txt
    for k in list(R.RECORDS) + list(R.RECORDS_NO_DOI):
        t, _ = R.cite(k); assert "et al.." not in t and "  " not in t and t.endswith("."), t


def test_bia_references_group_by_source_and_follow_the_catalog_year():
    class E:  # EN: minimal stand-in for catalog.Entry
        def __init__(s, id, label, authors, year, doi): s.id, s.label, s.authors, s.year, s.doi = id, label, authors, year, doi
    ents = [E("Piccoli1994_XcH", "Xc/H", "Piccoli", 1994, "10.1038/ki.1994.305"), E("Piccoli1994_RH", "R/H", "Piccoli", 1994, "10.1038/ki.1994.305"),
            E("Lukaski1985_II", "II", "Lukaski", 1985, "10.1093/ajcn/41.4.810"), E("user_x", "X", "Someone", 2001, None)]
    out = R.bia_references(ents)
    assert [o[2] for o in out] == ["II", "R/H, Xc/H", "X"]                       # one line per source, ids joined, sorted by year
    assert out[1][0].startswith("Piccoli A, Rossi B, Pillon L, Bucciante G. A new method") and out[1][1] == "https://doi.org/10.1038/ki.1994.305"
    assert out[2] == ("Someone. 2001.", "", "X")


def test_threshold_anchors_are_verified_records_tied_to_their_blocks():
    for doi, blocks in (("10.2478/joeb-2026-0010", ("m.redund",)), ("10.3390/life13051119", ("m.redund",)), ("10.4324/9780203771587", ("m.spec", "m.util"))):
        assert doi in R.RECORDS and dict(R.METHOD_REFS)[doi] == blocks
    txt, url = R.cite("10.4324/9780203771587"); assert txt.startswith("Cohen J. Statistical Power Analysis") and url.endswith("9780203771587")


def test_hanley_mcneil_supports_classification_blocks_and_the_sentence_appears_only_for_classification(tmp_path):
    """EN: citation review of the classification audit (2026-09-16): AUROC = P(case > non-case) = Wilcoxon (Hanley & McNeil 1982)."""
    import bioms_zaku.references as R
    assert "10.1148/radiology.143.1.7063747" in R.RECORDS and dict(R.METHOD_REFS)["10.1148/radiology.143.1.7063747"] == ("m.spec", "m.util")
    txt, url = R.cite("10.1148/radiology.143.1.7063747"); assert txt.startswith("Hanley JA, McNeil BJ.") and "1982;143(1):29-36" in txt
    from bioms_zaku.i18n import LANGS, t, set_language
    for lang in LANGS:
        set_language(lang); assert "Hanley & McNeil 1982" in t("m.spec.auroc") and "Hanley & McNeil 1982" in t("a.t.minclass.s")


def test_classification_only_references_are_listed_only_when_a_label_is_audited(tmp_path):
    """EN: a reference is never listed without a citation in the text (found 2026-09-16 in a regression report)."""
    import pandas as pd
    import bioms_zaku.references as R
    from bioms_zaku.html import _references
    from bioms_zaku.i18n import set_language
    set_language("en")
    cfg = {"catalog": {"include": "curated"}}
    reg = {"audit": pd.DataFrame(dict(method_id=["a"], task=["regression"]))}
    cls = {"audit": pd.DataFrame(dict(method_id=["a"], task=["classification"]))}
    from bioms_zaku.run import _load_catalog
    from bioms_zaku.config import resolve
    import yaml
    from pathlib import Path
    c = resolve(yaml.safe_load((Path(__file__).resolve().parents[1] / "examples/minimal.yaml").read_text(encoding="utf-8")))
    cat = _load_catalog(c)
    h_reg = _references(c, reg, cat, {}); h_cls = _references(c, cls, cat, {})
    for key in R.CLASSIFICATION_ONLY:
        first_author = R.record(key)["authors"].split(",")[0]
        assert first_author not in h_reg and first_author in h_cls, key
    assert "Tjur T" in h_reg and "Kohavi R" in h_reg          # cited in the thresholds table of every run

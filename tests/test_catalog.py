"""Catalog contract (§2)."""
import copy
import json
import re
from pathlib import Path

import pytest
from bioms_zaku.catalog import CatalogError, build_catalog, load_catalog

BASE = {
    "catalog_version": "t", "conventions": {"units": {}},
    "entries": [{
        "id": "X1", "label": "X1", "authors": "A", "year": 2000, "doi": "10.1000/x", "kind": "index", "target": "t",
        "form": "monomial", "frequency_khz": 50, "vector": {"R": -1, "Xc": 0, "H": 2, "W": 0}, "expr": "H**2/R",
        "validity": {"age": None, "bmi": None, "sex": None, "population": None},
        "provenance": {"formula_source": "pdf_table", "source_detail": "T1", "verified_by": "t", "verified_on": "2026-09-10"},
    }],
}


def _with(**changes):
    raw = copy.deepcopy(BASE)
    raw["entries"][0].update(changes)
    return raw


def test_builtin_catalog_loads_with_curated_entries():
    c = load_catalog()
    assert len(c.entries) == 32
    h = c["Hoffer1969_H2Z"]
    assert h.form == "monomial" and h.year == 1969 and h.confidence == "high" and "Z100" in h.inputs
    assert c["Baumgartner1988_PhA"].form == "composite" and c["LMI"].form == "composite"
    assert c["Schifferli2020_FFM_adj"].identity_of == "Schifferli2011_FFM"
    assert c["Segal1988_spec_LBM"].branch_group == "fat_class"


def test_target_kind_is_validated():
    with pytest.raises(CatalogError, match="target_kind"):
        build_catalog(_with(target_kind="muscle"))
    assert build_catalog(_with(target_kind="fat_mass"))["X1"].target_kind == "fat_mass"
    assert load_catalog()["Rsp"].target_kind == "fat_mass"


def test_non_monomial_derived_names_cannot_be_vectors():
    # EN: §2.3 exactness — atan(Xc/R) and sqrt(R²+Xc²) are not monomials; declaring them as such is refused.
    with pytest.raises(CatalogError, match="composite"):
        build_catalog(_with(expr="atan(Xc / R) * 180 / pi", vector={"PhA": 1}))
    with pytest.raises(CatalogError, match="composite"):
        build_catalog(_with(expr="H**2 / Z", vector={"Z": -1, "H": 2}))
    with pytest.raises(CatalogError, match="exact"):
        build_catalog(_with(vector_tol=0.03))
    build_catalog(_with(expr="atan(Xc / R) * 180 / pi", form="composite", vector=None))  # ok as composite


def test_vector_consistency_is_checked():
    build_catalog(BASE)  # ok
    with pytest.raises(CatalogError, match="inconsistent"):
        build_catalog(_with(vector={"R": -1, "Xc": 0, "H": 1, "W": 0}))


def test_derived_names_in_vector_are_accepted():
    build_catalog(_with(expr="R / H_m", vector={"R": 1, "H_m": -1}))
    build_catalog(_with(expr="II", vector={"II": 1}))


def test_check_example_is_enforced():
    ok = _with(form="composite", vector=None, expr="8.867*sexo + 0.369*W + 0.477*II + 0.037*R - 22.426",
               group_coding={"sexo": {"male": 1, "female": 0}},
               check_example={"inputs": {"sexo": 0, "W": 63.4, "H": 162, "R": 513}, "expected": 44.45, "tol": 0.15})
    del ok["entries"][0]["vector"]
    build_catalog(ok)
    bad = copy.deepcopy(ok); bad["entries"][0]["check_example"]["expected"] = 50.0
    with pytest.raises(CatalogError, match="check_example failed"):
        build_catalog(bad)


def test_confidence_cannot_exceed_source():
    raw = _with(provenance={"formula_source": "abstract", "source_detail": "", "verified_by": "t", "verified_on": "2026-09-10", "confidence": "high"})
    with pytest.raises(CatalogError, match="exceeds"):
        build_catalog(raw)


def test_malicious_expression_rejected_at_load():
    with pytest.raises(CatalogError):
        build_catalog(_with(expr="__import__('os').system('echo pwned')", form="composite", vector=None))


def test_branch_group_must_be_declared():
    raw = _with(form="composite", vector=None)
    del raw["entries"][0]["expr"]; del raw["entries"][0]["vector"]
    raw["entries"][0]["expr_by_group"] = {"sexo": {"1": "R", "0": "Xc"}}
    with pytest.raises(CatalogError, match="branch group"):
        build_catalog(raw)


def test_identity_of_must_exist():
    with pytest.raises(CatalogError, match="identity_of"):
        build_catalog(_with(identity_of="nope"))


def test_doi_or_pmid_required():
    with pytest.raises(CatalogError, match="doi is required"):
        build_catalog(_with(doi=None))
    build_catalog(_with(doi=None, pmid=123))


def test_precedence_order_is_fixed():
    raw = copy.deepcopy(BASE)
    e2 = copy.deepcopy(raw["entries"][0]); e2.update(id="X2", year=2000, doi="10.1000/a")
    e3 = copy.deepcopy(raw["entries"][0]); e3.update(id="X3", year=1999, doi="10.1000/z")
    raw["entries"] += [e2, e3]
    assert [e.id for e in build_catalog(raw).sorted_by_precedence()] == ["X3", "X2", "X1"]


def test_inputs_include_branch_group():
    c = load_catalog()
    assert "fat_class" in c["Segal1988_spec_LBM"].inputs
    assert "sexo" in c["Sun2003_FFM"].inputs


def test_excluded_entries_require_reason_and_builtin_marks_heitmann_tbw():
    c = load_catalog()
    e = c["Heitmann1990_TBW"]
    assert e.status == "excluded" and e.exclusion_reason
    with pytest.raises(CatalogError, match="exclusion_reason"):
        build_catalog(_with(status="excluded"))


def test_curated_default_is_the_eight_read_entries_and_is_locked():
    # EN: DESIGN DECISION (10/09, reaffirmed 14/09 after a wrong change): only curated methods are audited by default.
    from bioms_zaku.config import DEFAULTS, resolve
    from bioms_zaku.run import _load_catalog
    c = load_catalog()
    cur = sorted(e.id for e in c.entries if e.curated)
    assert cur == sorted(["Hoffer1969_H2Z", "Lukaski1985_II", "Baumgartner1988_PhA", "Piccoli1994_RH", "Piccoli1994_XcH", "LMI", "Rsp", "Xcsp"])
    assert all(c[i].curation_record and c[i].confidence == "high" for i in cur)
    assert DEFAULTS["catalog"]["include"] == "curated"
    base = {"data": {"columns": {"variables": {"R": "r", "Xc": "x", "H": "h", "W": "w"}, "targets": {"t": "t"}, "controls": {"c": "c"}}}}
    assert sorted(e.id for e in _load_catalog(resolve(base)).entries) == cur                       # default → the 8
    assert len(_load_catalog(resolve({**base, "catalog": {"include": "all"}})).entries) == len(c.entries)
    with pytest.raises(ValueError):
        resolve({**base, "catalog": {"include": "everything"}})
    with pytest.raises(CatalogError):                                                                # curated without a record is refused
        build_catalog(_with(curated=True))


def test_builtin_catalog_ships_inside_the_package():
    # EN: an installed wheel must find the catalog: it has to live under the package directory (Colab finding, 2026-09-14)
    import bioms_zaku
    from pathlib import Path
    from bioms_zaku.catalog import BUILTIN_PATH
    pkg = Path(bioms_zaku.__file__).resolve().parent
    assert BUILTIN_PATH.exists() and pkg in BUILTIN_PATH.parents


def test_every_curated_entry_points_at_a_section_that_exists_in_the_record():
    """The contract (§2.1) says a curated entry has its critical reading recorded in docs/LEITURAS.md, and the READMEs
    repeat the claim. Publishing the claim without the record, or with a record that does not cover the eight methods,
    would be an assertion without evidence — this checks that every cited section is really there (2026-09-19)."""
    root = Path(__file__).resolve().parents[1]
    registro = (root / "docs" / "LEITURAS.md").read_text(encoding="utf-8")
    secoes = {m.group(1) for m in re.finditer(r"^## (\d+)\.", registro, re.M)}
    catalogo = json.loads((root / "src" / "bioms_zaku" / "data" / "catalog_v1.json").read_text(encoding="utf-8"))
    curados = [e for e in catalogo["entries"] if e.get("curated")]
    assert len(curados) >= 8, f"expected the eight curated methods, found {len(curados)}"
    for e in curados:
        citadas = set(re.findall(r"§\s*(\d+)", e.get("curation_record") or ""))
        assert citadas, f"{e['id']}: curated without naming a section of the record"
        faltam = citadas - secoes
        assert not faltam, f"{e['id']} cites sections {sorted(faltam)}, absent from docs/LEITURAS.md"

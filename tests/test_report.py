"""EN: contract §4.6 (v0.8) — the report as the product. Guarantees T1–T8 of PLANO_v0.8_relatorio.md."""
import base64
import builtins
import html.parser
import re
from pathlib import Path

import pandas as pd
import pytest
import yaml

from bioms_zaku.i18n import set_language

ROOT = Path(__file__).resolve().parents[1]


def _cfg(tmp_path, name, **over):
    cfg = yaml.safe_load((ROOT / "examples/minimal.yaml").read_text(encoding="utf-8"))
    cfg["data"]["path"] = str(ROOT / "examples/minimal_data.csv"); cfg["output"] = {"dir": str(tmp_path), "figures": True}; cfg["run_name"] = name
    cfg["catalog"] = {"include": ["Lukaski1985_II", "Piccoli1994_RH", "Baumgartner1988_PhA"]}; cfg["audit"] = {"bootstrap": {"min_oob": 10}, "cv": {"folds": 3}}
    for k, v in over.items():
        cfg[k] = v
    return cfg


@pytest.fixture(scope="module")
def run_pt(tmp_path_factory):
    from bioms_zaku.run import run
    res = run(_cfg(tmp_path_factory.mktemp("r"), "rep", language="pt"), printer=lambda s: None)
    set_language("en")
    return res, (res["out_dir"] / "report.html").read_text(encoding="utf-8")


def test_T1_csv_links_are_byte_identical_to_the_hashed_files(run_pt):
    res, txt = run_pt
    links = dict(re.findall(r"download='([^']+\.csv)' href='data:text/csv;charset=utf-8;base64,([^']+)'", txt))
    assert len(links) >= 8
    for name, b64 in links.items():
        assert base64.b64decode(b64) == (res["out_dir"] / name).read_bytes(), name
    assert set(res["manifest"]["outputs_sha256"]) >= set(links)     # every linked table is a hashed output


def test_T2_sizes_within_browser_limits(run_pt):
    res, txt = run_pt
    for name, b64 in re.findall(r"download='([^']+\.csv)' href='data:text/csv;charset=utf-8;base64,([^']+)'", txt):
        assert len(b64) < 1_000_000, name
    assert (res["out_dir"] / "report.html").stat().st_size < 5_000_000


def test_T3_excel_optional(tmp_path, monkeypatch):
    from bioms_zaku.html import write_excel
    tables = {"a": pd.DataFrame({"x": [1, 2]}), "b": pd.DataFrame({"y": [3.5]}), "empty": pd.DataFrame()}
    real_import = builtins.__import__
    def no_openpyxl(name, *a, **k):
        if name == "openpyxl":
            raise ImportError("simulated absence")
        return real_import(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", no_openpyxl)
    assert write_excel(tmp_path, tables) is None                    # without openpyxl: no file, no error
    monkeypatch.setattr(builtins, "__import__", real_import)
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        pytest.skip("openpyxl not installed in this environment; the with-openpyxl path runs in CI's [excel] job")
    p = write_excel(tmp_path, tables)
    assert p is not None and set(pd.ExcelFile(p).sheet_names) == {"a", "b"}


def test_T4_method_text_follows_the_configuration(tmp_path):
    from bioms_zaku.run import run
    cfg = _cfg(tmp_path, "cfg", language="en"); cfg["preset"] = "full"
    cfg["audit"] = {"bootstrap": {"min_oob": 10, "B": 37}, "cv": {"folds": 3, "repeats": 2}, "verdict": {"margin": 0.07}, "utility_margin": 0.11}
    cfg["geometry"] = {"parallel_to_control": 0.93, "coupled_target_control": 0.77, "min_fit_r2": 0.55}
    res = run(cfg, printer=lambda s: None); txt = (res["out_dir"] / "report.html").read_text(encoding="utf-8")
    assert "3-fold cross-validation repeated 2 times" in txt and "from 37 paired out-of-bag" in txt and "its mean exceeds 0.07" in txt
    assert "exceeds 0.11" in txt and "≥ 0.93" in txt and "≥ 0.77" in txt and "R² ≥ 0.55" in txt
    assert f"{res['manifest']['input_rows']} rows read, {res['manifest']['rows_out']} usable" in txt


def test_T5_inline_only_in_notebooks(tmp_path, monkeypatch):
    # EN: IPython may be absent in the test environment: a fake `IPython.display` is injected, so both paths run everywhere.
    import sys, types
    from bioms_zaku import run as R
    shown = []
    class FakeIP:
        config = {"IPKernelApp": {}}
    class HTML:
        def __init__(self, data): self.data = data
    class IFrame:
        def __init__(self, src, width, height): self.src = src
    fake_display = types.SimpleNamespace(display=lambda x: shown.append(x), HTML=HTML, IFrame=IFrame)
    monkeypatch.setitem(sys.modules, "IPython", types.SimpleNamespace(display=fake_display))
    monkeypatch.setitem(sys.modules, "IPython.display", fake_display)
    monkeypatch.setattr(builtins, "get_ipython", lambda: FakeIP(), raising=False)
    (tmp_path / "report.html").write_text("<p>x</p>", encoding="utf-8")
    monkeypatch.chdir(tmp_path.parent)                                   # report BELOW the notebook folder → relative IFrame (no 404)
    R._show_inline(tmp_path / "report.html"); assert len(shown) == 1 and isinstance(shown[0], IFrame) and not shown[0].src.startswith("/")
    monkeypatch.chdir(tmp_path.parent.parent if tmp_path.parent.parent != tmp_path.parent else "/")
    other = tmp_path / "elsewhere"; other.mkdir(); (other / "report.html").write_text("<p>y</p>", encoding="utf-8")
    monkeypatch.chdir(other); R._show_inline(tmp_path / "report.html")   # report OUTSIDE the notebook folder → embedded srcdoc
    assert len(shown) == 2 and isinstance(shown[1], HTML) and "srcdoc=" in shown[1].data and "&lt;p&gt;x&lt;/p&gt;" in shown[1].data
    monkeypatch.delattr(builtins, "get_ipython", raising=False)
    R._show_inline(tmp_path / "report.html"); assert len(shown) == 2                  # outside a notebook: nothing new


def test_T6_html_is_well_formed(run_pt):
    _, txt = run_pt
    class P(html.parser.HTMLParser):
        def __init__(self): super().__init__(); self.stack = []; self.bad = 0
        def handle_starttag(self, t, a):
            if t not in ("br", "img", "meta", "link", "input", "hr"): self.stack.append(t)
        def handle_endtag(self, t):
            if self.stack and self.stack[-1] == t: self.stack.pop()
            else: self.bad += 1
    p = P(); p.feed(txt); assert p.bad == 0 and p.stack == []


def test_T7_text_agrees_with_tables(run_pt):
    res, txt = run_pt
    aud = res["tables"]["audit"]; vc = aud.verdict.value_counts()
    for k in ("SPECIFIC", "TRACKS_CONTROL", "BOTH", "NEITHER"):                # summary line: pills keep the verdict token and its count
        assert f">{k} {vc.get(k, 0)}</span>" in txt, k
    assert f"métodos avaliados: {len(res['tables']['algebra'])}" in txt
    # key numbers read from the tables and the manifest
    assert f"<div class='v'>{res['manifest']['rows_out']}</div><div class='l'>pessoas analisadas</div>" in txt
    assert f"<div class='v'>{res['tables']['algebra'].method_id.nunique()}</div><div class='l'>métodos avaliados</div>" in txt
    assert f"Específico {vc.get('SPECIFIC', 0)}</span>" in txt and f"Acompanha ctrl {vc.get('TRACKS_CONTROL', 0)}</span>" in txt
    for name in ("audit", "algebra", "geometry"):
        assert res["manifest"]["outputs_sha256"][f"{name}.csv"] in txt      # rigour section lists every hash


def test_T8_no_english_leak_in_pt_report(run_pt):
    _, txt = run_pt
    for en in ("How it was computed", "How to read it", "Rigour applied", "download CSV", "Rigour of this run", ">Results<", "not curated", "Key numbers", "Verdict sheet", "measured variables", "click to enlarge", ">References<"):
        assert en not in txt, en
    for pt in ("Como foi calculado", "Como ler", "Rigor aplicado", "baixar CSV", "Rigor desta execução", "Resultados", "Números-chave", "Ficha de vereditos", "variáveis medidas", "Referências"):
        assert pt in txt, pt


def test_run_name_follows_the_yaml_and_overwrite_is_announced(tmp_path):
    from bioms_zaku.wizard import init
    from bioms_zaku.run import run
    flags = {"R": "resistencia_ohm", "Xc": "reatancia_ohm", "H": "estatura_cm", "W": "massa_kg", "target": "lmi_dxa", "control": "fmi_dxa", "independent": "yes"}
    out = init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "analise_A.yaml"), map_flags=flags, printer=lambda s: None)
    assert yaml.safe_load(out.read_text(encoding="utf-8"))["run_name"] == "analise_A"          # named after the YAML, not the CSV
    cfg = _cfg(tmp_path, "same", language="en")
    lines = []; run(cfg, printer=lines.append); assert not any("already holds" in l for l in lines)
    lines = []; res = run(cfg, printer=lines.append)
    assert any("already holds a previous run" in l for l in lines) and any("already holds" in w for w in res["manifest"]["notes"])
    assert not any("already holds" in w for w in res["manifest"]["warnings"])           # operational note, not a scientific warning
    summ = (res["out_dir"] / "summary.md").read_text(encoding="utf-8"); assert "already holds" not in summ
    txt = (res["out_dir"] / "report.html").read_text(encoding="utf-8"); assert "Estimator sensitivity (not requested)" in txt
    set_language("en")


def test_nine_content_fixes_of_2026_09_15(tmp_path):
    # EN: line-by-line review by the user: no internal references, clean Σ-transfer header, R², empty tables marked, an
    #     'about' section with a citation equal to CITATION.cff, strata labels and original column names from init.
    from bioms_zaku.run import run
    from bioms_zaku.wizard import init
    from bioms_zaku.html import CITATION
    cfg = _cfg(tmp_path, "nine", language="en"); cfg["strata"] = "sexo"; cfg["strata_labels"] = {0: "F", 1: "M"}
    cfg["data"]["columns"]["groups"] = {"sexo": "sexo"}
    res = run(cfg, printer=lambda s: None); txt = (res["out_dir"] / "report.html").read_text(encoding="utf-8")
    summ = (res["out_dir"] / "summary.md").read_text(encoding="utf-8")
    assert "§" not in txt and "§" not in summ and ", v0.5" not in txt and "v0.6" not in txt
    assert "| median abs. error [95% boot] |" in summ and "|err|" not in summ
    assert "(R², Ridge; conditional control)" in summ
    empties = [f"{n}.csv" for n, df in res["tables"].items() if df is None or df.empty]
    assert empties and all(f"{n}: {res['manifest']['outputs_sha256'][n]} (empty)" in txt for n in empties)   # every empty table is marked
    assert "About this report" in txt and "How to cite" in txt and CITATION["title"] in txt
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert CITATION["title"] in cff and CITATION["repo"] in cff and all(n in cff for n in ("Mota", "Martins", "Oliveira Gonçalves"))
    assert "## Stratum `F`" in summ and "## Stratum `M`" in summ                     # labels reach the report
    flags = {"R": "resistencia_ohm", "Xc": "reatancia_ohm", "H": "estatura_cm", "W": "massa_kg", "target": "lmi_dxa", "control": "fmi_dxa",
             "strata": "sexo", "labels": "0=F,1=M", "independent": "yes"}
    printed = []; out = init(str(ROOT / "examples/minimal_data.csv"), str(tmp_path / "lab.yaml"), map_flags=flags, printer=printed.append)
    c2 = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert c2["strata_labels"] == {"0": "F", "1": "M"} and c2["data"]["columns"]["targets"] == {"lmi_dxa": "lmi_dxa"}
    assert any(l.strip().startswith("labels") and "0=F,1=M" in l for l in printed)
    set_language("en")


def test_v09_structure_accordion_diagram_and_references(run_pt):
    # EN: v0.9 (2026-09-15): sticky contents, eight numbered sections in a fixed order, result blocks as an exclusive accordion
    #     (one open at a time, the first open by default), figures grouped by family with translated titles, the Zaku method
    #     diagram inline and on disk, references restricted to the methods of the run, no external resource, print + lightbox.
    res, txt = run_pt; out = res["out_dir"]
    anchors = ["about", "key", "summary", "figures", "results", "rigor", "refs", "manifest"]
    assert all(f"href='#{a}'" in txt for a in anchors)
    pos = [txt.index(f"id='{a}'") for a in anchors]; assert pos == sorted(pos)          # sections in reading order
    blocks = re.findall(r"<details class='block' name='results'( open)?>", txt)
    assert len(blocks) >= 5 and blocks[0] == " open" and sum(b == " open" for b in blocks) == 1
    figs = re.findall(r"<details class='block' name='figures'( open)?><summary><span class='n'>4\.\d</span>([^<]+)", txt)
    assert figs and figs[0][0] == " open" and figs[0][1] == "Ficha de vereditos" and "Mapa do controle negativo condicional" in [f[1] for f in figs]
    assert "Zaku: o método numa imagem" in txt and "<svg xmlns='http://www.w3.org/2000/svg'" in txt
    svg = (out / "figures" / "zaku_method.svg").read_text(encoding="utf-8"); assert svg in txt          # same diagram inline and on disk
    assert "variáveis medidas" in svg and "measured variables" not in svg
    # references: exactly the sources of the methods evaluated, each linked; the statistical block tagged with block titles
    from bioms_zaku.run import _load_catalog
    cat = _load_catalog(res["manifest"]["config_resolved"]); used = set(res["tables"]["algebra"].method_id)
    for e in cat.entries:
        assert (f"https://doi.org/{e.doi}" in txt) == (e.id in used), e.id
    assert "https://doi.org/10.1152/jappl.1969.27.4.531" not in txt                      # Hoffer 1969 not in this run
    assert "doi.org/10.1097/ede.0b013e3181d61eeb" in txt and "ede.0b013e3181e4bfd7" not in txt
    assert "<span class='tag'>Especificidade (controle negativo condicional)</span>" in txt
    assert "verificados em 2026-" in txt
    assert not re.search(r"(src|href)=['\"]https?://(?!doi\.org|www\.jmlr\.org|jmlr\.org|github\.com)", txt)   # nothing loaded from the network
    assert "beforeprint" in txt and "id='lb'" in txt and "<meta name='viewport'" in txt
    assert ">r(a,b) = aᵀΣb / √(aᵀΣa · bᵀΣb)</text>" in svg and "<span class='brand'>BioMS Zaku</span>" in txt   # formula on its own line (bounds: tests/test_diagram.py); grey header, brand in gradient

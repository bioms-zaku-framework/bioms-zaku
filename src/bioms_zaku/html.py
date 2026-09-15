"""
EN: Single-file HTML report (v0.9): header, sticky table of contents, about + the Zaku method diagram, key numbers, text
    summary, figures grouped by family (one open at a time), result blocks as an accordion (method text: how · read ·
    rigour; tables with CSV/Excel download), rigour of the run, references (verified records), manifest. Opens from disk,
    travels by e-mail, contains only aggregates. No external resource: CSS, JS (lightbox, print) and images are inline.
    Brand identity: biomspro.com violet→green; verdict colours identical to the figures.
ES: Informe HTML en un solo archivo.  PT: Relatório HTML em um único arquivo.  IT: Rapporto HTML in un unico file.
"""
from __future__ import annotations

import base64
import html
import json
import re
from pathlib import Path

import pandas as pd

LOGO = Path(__file__).resolve().parent / "data" / "logo.svg"   # EN: ships inside the package (an installed wheel has no docs/)
MAX_ROWS = 1000                                                 # EN: rows rendered per table; the embedded CSV is always complete
CSS = """
:root{--violet:#9333ea;--green:#22c55e;--both:#52514e;--none:#9a9893;--ink:#1d1d1f;--ink2:#52514e;--line:#e6e5e1;--bg:#fcfcfb;--panel:#f6f5f9;--code:#f4f6fc}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:56px}
body{margin:0;font-family:Inter,"Segoe UI","DejaVu Sans",Arial,sans-serif;color:var(--ink);background:var(--bg);line-height:1.55;font-size:15px}
header{background:#f3f3f1;color:var(--ink);padding:26px 28px 18px;display:flex;flex-direction:column;align-items:center;text-align:center;gap:4px;border-bottom:1px solid var(--line)}
header img{height:110px;margin-bottom:6px}header .brand{font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;background:linear-gradient(90deg,var(--violet),var(--green));-webkit-background-clip:text;background-clip:text;color:transparent;display:inline-block}
header h1{font-size:23px;margin:2px 0 0;font-weight:650;letter-spacing:-.01em}header h1 span{color:var(--ink2);font-weight:500}header p{margin:2px 0 0;color:var(--ink2);font-size:14px}
header .chips{display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin-top:8px}.chip{background:#fff;border:1px solid var(--line);border-radius:999px;padding:2px 10px;font-size:12px;color:var(--ink2)}
nav.toc{position:sticky;top:0;z-index:5;background:rgba(252,252,251,.96);backdrop-filter:blur(4px);border-bottom:1px solid var(--line);padding:8px 28px;display:flex;gap:4px 18px;flex-wrap:wrap;justify-content:center;font-size:13px}
nav.toc a{color:var(--ink2);text-decoration:none;font-weight:600}nav.toc a:hover{color:var(--violet)}
main{max-width:1080px;margin:0 auto;padding:18px 28px 40px}
h2{font-size:18px;margin:34px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line);display:flex;align-items:baseline;gap:10px}
h2 .n,summary .n{color:var(--violet);font-weight:700;font-size:13px;font-variant-numeric:tabular-nums}
h3{font-size:15.5px;margin:18px 0 8px}
p{margin:8px 0}.hint{font-size:12.5px;color:var(--ink2)}li.sub{margin-left:18px;list-style:circle}code{background:var(--code);padding:0 4px;border-radius:3px;font-size:.92em}
.about{background:var(--panel);border-radius:10px;padding:8px 18px 12px;margin:14px 0}.about h2{border:0;margin:6px 0 4px}
figure{margin:12px 0}figure img{max-width:100%;border:1px solid var(--line);border-radius:6px;cursor:zoom-in;background:#fff}
figcaption{font-size:12.5px;color:var(--ink2);margin-top:6px}figure.diagram{background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 12px 6px}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:12px 0}
.kpi .card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px}.card .v{font-size:26px;font-weight:700;line-height:1.1;font-variant-numeric:tabular-nums}
.card .l{font-size:12.5px;color:var(--ink2);margin-top:2px}.card .s{font-size:12px;color:var(--ink2);margin-top:6px;line-height:1.5}
.pill{display:inline-block;padding:1px 9px;border-radius:999px;font-size:11.5px;font-weight:650;color:#fff;white-space:nowrap;line-height:1.5}
.pill.sp{background:var(--green)}.pill.tc{background:var(--violet)}.pill.bo{background:var(--both)}.pill.ne{background:var(--none)}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;background:#fee2e2;color:#991b1b;margin-left:8px}
details.block{background:#fff;border:1px solid var(--line);border-radius:10px;margin:10px 0;padding:0 16px}
details.block>summary{cursor:pointer;font-weight:650;font-size:15px;padding:12px 0;display:flex;align-items:baseline;gap:10px;list-style:none}
details.block>summary::-webkit-details-marker{display:none}details.block>summary::before{content:"▸";color:var(--violet);font-size:12px;transition:transform .15s}
details.block[open]>summary::before{transform:rotate(90deg)}details.block>summary .hint{font-weight:400;margin-left:auto}
details.block>.body{padding:0 0 14px}
.method{background:#f7f5fb;border-left:3px solid var(--violet);padding:8px 14px;margin:6px 0 12px;font-size:14px;border-radius:0 6px 6px 0}.method b{color:var(--violet)}
details.tbl{margin:8px 0;border:1px solid var(--line);border-radius:8px;padding:0 12px}details.tbl>summary{cursor:pointer;font-weight:600;font-size:13px;padding:8px 0}
.tw{overflow-x:auto;margin:6px 0 10px}table{border-collapse:collapse;font-size:12.5px;width:100%}
th,td{border-bottom:1px solid var(--line);padding:4px 9px;text-align:left;white-space:nowrap;vertical-align:top}th{background:var(--code);position:sticky;top:0;font-weight:650}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}
.kv td:first-child{font-weight:600;white-space:nowrap}.kv td{white-space:normal;word-break:break-all}
.dl{display:inline-block;margin:4px 8px 4px 0;padding:3px 11px;border:1px solid var(--violet);border-radius:6px;color:var(--violet);text-decoration:none;font-size:12.5px;font-weight:600}
.dl:hover{background:var(--violet);color:#fff}
.refs ol{padding-left:22px;font-size:13.5px}.refs li{margin:5px 0}.refs a{color:var(--violet);text-decoration:none;word-break:break-all}.refs .tag{font-size:11px;color:var(--ink2);background:var(--panel);border-radius:4px;padding:0 6px;margin-left:6px;white-space:nowrap}
pre{background:var(--code);padding:10px;font-size:11px;overflow-x:auto;border-radius:6px}
footer{color:var(--ink2);font-size:11.5px;padding:18px 28px;border-top:1px solid var(--line)}
.lb{position:fixed;inset:0;background:rgba(20,20,22,.88);display:flex;align-items:center;justify-content:center;z-index:50;cursor:zoom-out;padding:24px}.lb img{max-width:100%;max-height:100%;background:#fff;border-radius:6px}.lb[hidden]{display:none}
@media print{nav.toc,.lb,.dl,.hint.zoom{display:none!important}body{background:#fff}details.block,figure.diagram{break-inside:avoid}}
"""
JS = """
(function(){var lb=document.getElementById('lb');
document.addEventListener('click',function(e){var i=e.target.closest('figure img');if(!i)return;lb.querySelector('img').src=i.src;lb.hidden=false;});
lb.addEventListener('click',function(){lb.hidden=true;});
document.addEventListener('keydown',function(e){if(e.key==='Escape')lb.hidden=true;});
var st=[];window.addEventListener('beforeprint',function(){var d=document.querySelectorAll('details');st=[];d.forEach(function(x){st.push(x.open);x.open=true;});});
window.addEventListener('afterprint',function(){document.querySelectorAll('details').forEach(function(x,i){x.open=st[i];});});})();
"""
VERDICT_CLASS = {"SPECIFIC": "sp", "TRACKS_CONTROL": "tc", "MEASURES_CONTROL": "tc", "BOTH": "bo", "NEITHER": "ne"}
FIG_FAMILIES = ("scorecard", "lineage", "target_control", "exponents", "board", "predicted_observed", "sigma_transfer", "combination_gain", "compass")


def _img(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _svg(path: Path) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode("ascii") if path.exists() else ""


def _pills(s: str) -> str:
    """EN: verdict tokens in already-escaped text become coloured pills; the text itself is unchanged (tested against the tables)."""
    return re.sub(r"\b(SPECIFIC|TRACKS_CONTROL|MEASURES_CONTROL|BOTH|NEITHER)( \d+)?\b",
                  lambda m: f"<span class='pill {VERDICT_CLASS[m.group(1)]}'>{m.group(1)}{m.group(2) or ''}</span>", s)


def _inline(s: str) -> str:
    """EN: escape, then **bold**, `code` and verdict pills — the only inline Markdown the summary uses."""
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return _pills(s)


def _md_to_html(md: str) -> str:
    """EN: minimal Markdown (headings, lists incl. indented, blockquote, tables, paragraphs) — no external dependency."""
    out, in_table, in_list = [], False, False
    for raw in md.splitlines():
        line = raw.strip() if raw.lstrip().startswith("- ") else raw
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            if not in_table:
                out.append("<div class='tw'><table>"); in_table = True
            tag = "th" if out[-1] == "<div class='tw'><table>" else "td"
            out.append("<tr>" + "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        if in_table:
            out.append("</table></div>"); in_table = False
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li class='{'sub' if raw.startswith(' ') else ''}'>{_inline(line[2:])}</li>"); continue
        if in_list:
            out.append("</ul>"); in_list = False
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            out.append(f"<h3>{html.escape(line[3:])}</h3>")
        elif line.startswith("> "):
            out.append(f"<p><span class='badge'>{html.escape(line[2:].replace('**', ''))}</span></p>")
        elif line.strip():
            out.append(f"<p>{_inline(line)}</p>")
    if in_table: out.append("</table></div>")
    if in_list: out.append("</ul>")
    return "\n".join(out)


def _csv_link(name: str, df: pd.DataFrame, out_dir: Path, label: str) -> str:
    """EN: download link with the CSV embedded (base64 data URI). The bytes are the file on disk when it exists (identical to
    the hashed output); otherwise the frame is serialised the same way `write_table` does."""
    f = Path(out_dir) / f"{name}.csv"
    raw = f.read_bytes() if f.exists() else df.to_csv(index=False).encode("utf-8")
    return f"<a class='dl' download='{name}.csv' href='data:text/csv;charset=utf-8;base64,{base64.b64encode(raw).decode('ascii')}'>{html.escape(label)}</a>"


def write_excel(out_dir: Path, tables: dict[str, pd.DataFrame]) -> Path | None:
    """EN: one workbook, one sheet per non-empty table; needs openpyxl (extra `[excel]`). Returns None when unavailable."""
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        return None
    p = Path(out_dir) / "tables.xlsx"
    with pd.ExcelWriter(p, engine="openpyxl") as xw:
        for name, df in tables.items():
            if df is not None and not df.empty:
                df.to_excel(xw, sheet_name=name[:31], index=False)
    return p


def _fmt(v) -> str:
    """EN: readable cell: floats to 4 decimals (tiny values in scientific notation), NaN empty; the CSV keeps full precision."""
    if v is None or (isinstance(v, float) and v != v):
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        r = round(v, 4)
        return f"{r:g}" if r != 0 or v == 0 else f"{v:.2e}"
    return str(v)


def _table_html(df: pd.DataFrame) -> str:
    from .i18n import t
    num = {c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])}
    head = "".join(f"<th{' class=num' if c in num else ''}>{html.escape(str(c))}</th>" for c in df.columns)
    rows = []
    for rec in df.head(MAX_ROWS).itertuples(index=False):
        rows.append("<tr>" + "".join(f"<td{' class=num' if c in num else ''}>{html.escape(_fmt(v))}</td>" for c, v in zip(df.columns, rec)) + "</tr>")
    cap = f"<p class='hint'>{html.escape(t('h.rows_capped', n=MAX_ROWS, m=len(df)))}</p>" if len(df) > MAX_ROWS else ""
    return f"<div class='tw'><table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>{cap}"


def _method_block(key: str, **kw) -> str:
    from .i18n import t
    return ("<div class='method'>" + "".join(f"<p><b>{html.escape(t(h))}.</b> {html.escape(t(f'{key}.{k}', **kw))}</p>"
                                              for h, k in (("h.how", "how"), ("h.read", "read"), ("h.rig", "rigor"))) + "</div>")


def _tables_block(names: list[str], tables: dict, out_dir: Path, group: str) -> str:
    from .i18n import t
    parts = []
    for name in names:
        df = tables.get(name)
        if df is None or df.empty:
            continue
        parts.append(f"<details class='tbl' name='tables-{group}'><summary>{name}.csv · {len(df)} {t('h.rows')} &nbsp; {_csv_link(name, df, out_dir, t('h.download_csv'))}</summary>"
                     + _table_html(df) + "</details>")
    return "\n".join(parts)


# EN: result blocks in reading order: (key of the method text, tables shown under it, function building the text kwargs)
def _block_kwargs(cfg: dict, manifest: dict, tables: dict) -> dict[str, dict]:
    from .i18n import t
    au = cfg["audit"]; g = cfg.get("geometry") or {}; al = cfg["algebra"]
    est = str(tables["audit"].estimator.iloc[0]) if "audit" in tables and not tables["audit"].empty else au["single"]["estimator"]
    ut = tables.get("utility"); cov = str(ut.covariates.iloc[0]).replace("+", " + ") if ut is not None and not ut.empty else "—"
    se = tables.get("sensitivity"); est_alt = str(se.estimator.iloc[0]) if se is not None and not se.empty else t("m.sens.none")
    return {
        "m.input": dict(sep=repr(manifest.get("sep_used")), dec=repr(manifest.get("decimal_used")), rin=manifest.get("input_rows"),
                        rout=str(manifest.get("rows_out")) + (t("m.input.design_note", nd=manifest["design"]["n_design"], na=manifest["design"]["n_audit"]) if (manifest.get("design") or {}).get("n_design") else ""),
                        strata=", ".join(f"{k} (n={v})" for k, v in (manifest.get("strata_used") or {}).items()) or "—"),
        "m.redund": dict(thr=al["redundancy_threshold"]),
        "m.spec": dict(est=est, f=au["cv"]["folds"], r=au["cv"]["repeats"], B=au["bootstrap"]["B"], mg=au["verdict"]["margin"], p=au["verdict"]["p_specific"], ci=f"{au['verdict']['ci']:.0%}"),
        "m.util": dict(cov=cov, mg=au["utility_margin"]),
        "m.geo": dict(pc=g.get("parallel_to_control"), cc=g.get("coupled_target_control"), r2=g.get("min_fit_r2")),
        "m.transfer": dict(tol=al["transfer_tol"], Bt=al["transfer_B"]),
        "m.sens": dict(margins=list(au["verdict"].get("sensitivity_margins", [])), ps=list(au["verdict"].get("sensitivity_p", [])), est_alt=est_alt),
        "m.screen": {},
        "m.design": (lambda dz: dict(ids=", ".join(dz.get("indices", {})), fr=f"{(dz.get('fraction') or 0):.0%}" if dz.get("fraction") else dz.get("mode", ""), seed=dz.get("seed"), na=dz.get("n_audit")))(manifest.get("design") or {}),
    }


BLOCKS = (("m.input", ["sigma"]), ("m.design", []), ("m.redund", ["algebra", "pairs", "redundancy"]), ("m.spec", ["audit"]), ("m.util", ["utility"]),
          ("m.geo", ["implicit_vectors", "geometry"]), ("m.transfer", ["sigma_transfer"]), ("m.sens", ["threshold_sensitivity", "sensitivity"]),
          ("m.screen", ["screening", "combinations"]))


CITATION = {"title": "BioMS Zaku: an algebraic and predictive framework to decompose, audit and design bioimpedance indices and equations",
            "authors": "Mota T, Martins C, Oliveira Gonçalves LC", "repo": "https://github.com/bioms-zaku-framework/bioms-zaku"}   # EN: kept equal to CITATION.cff (tested)


def _catalog(cfg: dict):
    """EN: the catalogue as resolved for this configuration; None when it cannot be loaded (e.g. a user file absent at render time)."""
    try:
        from .run import _load_catalog
        return _load_catalog(cfg)
    except Exception:
        return None


def _h2(n: int, anchor: str, title: str) -> str:
    return f"<h2 id='{anchor}'><span class='n'>{n}</span>{html.escape(title)}</h2>"


def _about(cfg: dict, manifest: dict) -> str:
    from .i18n import t
    from .diagram import zaku_svg
    v = manifest.get("package_version", ""); c = manifest.get("catalog_version", "")
    cite = f"{CITATION['authors']}. {CITATION['title']}. Version {v}. {CITATION['repo']}"
    return (f"<section class='about' id='about'><h2><span class='n'>1</span>{t('h.about_title')}</h2><p>{html.escape(t('h.about', version=v, catalog=c))}</p>"
            f"<p class='hint'><b>{t('h.cite')}:</b> {html.escape(cite)} · {html.escape(t('h.license'))}</p>"
            f"<p class='hint'>{html.escape(t('h.name_note'))}</p>"
            f"<figure class='diagram'>{zaku_svg()}<figcaption><b>{html.escape(t('fig.zaku_method'))}</b> — {html.escape(t('h.diagram_caption'))}</figcaption></figure></section>")


def _kpi(cfg: dict, manifest: dict, tables: dict, cat) -> str:
    """EN: key numbers, every one read from the tables/manifest (tested against them): people, strata, methods, verdicts, added value, coupling."""
    from .i18n import t
    alg = tables.get("algebra"); aud = tables.get("audit"); uti = tables.get("utility"); geo = tables.get("geometry")
    strata = manifest.get("strata_used") or {}
    dz = manifest.get("design") or {}
    n_people = sum(strata.values()) if strata else manifest.get("rows_out", "")     # EN: rows the audits actually used (the audit partition when indices were designed)
    sub = " · ".join(f"{k} (n={v})" for k, v in strata.items()) or "—"
    if dz.get("n_design"):
        sub = t("k.audited", nd=dz["n_design"]) + " · " + sub
    cards = [(str(n_people), t("k.people"), sub)]
    n_methods = len(alg.method_id.unique()) if alg is not None and not alg.empty else 0
    n_cur = sum(1 for e in (cat.entries if cat is not None else []) if e.curated and alg is not None and not alg.empty and e.id in set(alg.method_id)) if cat is not None else None
    n_prop = sum(1 for e in (cat.entries if cat is not None else []) if e.proposed and alg is not None and not alg.empty and e.id in set(alg.method_id))
    n_des = int(alg.drop_duplicates("method_id")["designed"].astype(bool).sum()) if alg is not None and not alg.empty and "designed" in alg else 0
    cards.append((str(n_methods), t("k.methods"), (t("k.curated", k=n_cur) if n_cur is not None else "—") + (f" · {t('k.proposed', k=n_prop)}" if n_prop else "") + (f" · {t('k.designed', k=n_des)}" if n_des else "")))
    if aud is not None and not aud.empty:
        tgt = aud.target.iloc[0]; a = aud[aud.target == tgt]; vc = a.verdict.replace({"MEASURES_CONTROL": "TRACKS_CONTROL"}).value_counts()
        pills = " ".join(f"<span class='pill {VERDICT_CLASS[k]}'>{html.escape(t('v.' + k))} {int(vc.get(k, 0))}</span>" for k in ("SPECIFIC", "TRACKS_CONTROL", "BOTH", "NEITHER"))
        per = " · ".join(f"{s}: " + "/".join(str(int((a[a.stratum == s].verdict.replace({'MEASURES_CONTROL': 'TRACKS_CONTROL'}) == k).sum())) for k in ("SPECIFIC", "TRACKS_CONTROL", "BOTH", "NEITHER")) for s in sorted(set(a.stratum)))
        cards.append((pills, t("k.verdicts", t=tgt), per))
        if uti is not None and not uti.empty:
            u = uti[uti.target == tgt]
            cards.append((t("k.ratio", k=int(u.useful.sum()), n=len(u)), t("k.useful", cov=str(u.covariates.iloc[0]).replace("+", " + ")), " · ".join(f"{s}: {int(u[u.stratum == s].useful.sum())}/{len(u[u.stratum == s])}" for s in sorted(set(u.stratum)))))
        else:
            cards.append(("—", t("k.useful_none"), ""))
        if geo is not None and not geo.empty:
            g = geo[geo.target == tgt]
            lines = [f"{s}: {t('k.yes') if bool(g[g.stratum == s].flag_coupled_target_control.any()) else t('k.no')} (cos_Σ {float(g[g.stratum == s].cos_target_control.iloc[0]):.2f})" for s in sorted(set(g.stratum))]
            anyc = bool(g.flag_coupled_target_control.any())
            cards.append((t("k.yes") if anyc else t("k.no"), t("k.coupled"), " · ".join(lines)))
    body = "".join(f"<div class='card'><div class='v'>{v}</div><div class='l'>{html.escape(l)}</div><div class='s'>{s}</div></div>" for v, l, s in cards)
    return f"<section id='key'>{_h2(2, 'key', t('n.key'))}<div class='kpi'>{body}</div></section>"


def _figures(fd: Path, captions: dict) -> str:
    from .i18n import t
    figs = sorted(fd.glob("*.png")) if fd.exists() else []
    fam: dict[str, list[Path]] = {}
    for f in figs:
        key = next((k for k in sorted(FIG_FAMILIES, key=len, reverse=True) if f.stem == k or f.stem.startswith(k + "_")), f.stem)
        fam.setdefault(key, []).append(f)
    order = [k for k in FIG_FAMILIES if k in fam] + [k for k in fam if k not in FIG_FAMILIES]
    parts = [_h2(4, "figures", t("h.figures"))]
    for i, key in enumerate(order):
        title = t(f"fig.{key}") if f"fig.{key}" in _MSG() else key
        cap = captions.get(key, "")
        inner = [f"<p class='hint'>{html.escape(cap)}</p>"] if cap else []
        for f in fam[key]:
            st = f.stem[len(key) + 1:] if f.stem != key else ""
            label = f"{title} · {t('fig.stratum', s=st)}" if st else title
            inner.append(f"<figure><img src='{_img(f)}' alt='{html.escape(label, quote=True)}'><figcaption><b>{html.escape(label)}</b> "
                         f"<span class='hint'>· {t('fig.file')} {f.name} · {t('fig.zoom')}</span></figcaption></figure>")
        parts.append(f"<details class='block' name='figures'{' open' if i == 0 else ''}><summary><span class='n'>4.{i + 1}</span>{html.escape(title)}"
                     f"<span class='hint'>{len(fam[key])} × {key}</span></summary><div class='body'>{''.join(inner)}</div></details>")
    return "\n".join(parts)


def _MSG():
    from .i18n import MSG
    return MSG


def _references(cfg: dict, tables: dict, cat, manifest: dict | None = None) -> str:
    manifest = manifest or {}
    from .i18n import t
    from . import references as R
    blocks = {k: t("b." + k.split(".")[1]) for k, _ in BLOCKS}
    def li(txt: str, url: str, tag: str = "") -> str:
        link = f" <a href='{html.escape(url, quote=True)}'>{html.escape(url.replace('https://', ''))}</a>" if url else ""
        return f"<li>{html.escape(txt)}{link}{('<span class=' + chr(39) + 'tag' + chr(39) + '>' + html.escape(tag) + '</span>') if tag else ''}</li>"
    meth = "".join(li(*R.cite(k), tag=" · ".join(blocks[b] for b in bl if b in blocks)) for k, bl in R.METHOD_REFS)
    alg = tables.get("algebra")
    if cat is not None and alg is not None and not alg.empty:
        used = set(alg.method_id); ents = [e for e in cat.entries if e.id in used]
        bia = "".join(li(txt, url, ids) for txt, url, ids in R.bia_references(ents, proposed_text=t("h.ref_proposed"))) or f"<li class='hint'>—</li>"
    else:
        bia = f"<li class='hint'>{html.escape(t('h.refs_none'))}</li>"
    for did, dz in ((manifest.get("design") or {}).get("indices") or {}).items():
        bia += li(t("h.ref_designed", t=dz.get("target"), orth=(t("h.ref_designed_orth", c=dz.get("orthogonal_to")) if dz.get("orthogonal_to") else "")), "", did)
    soft = "".join(li(*R.cite(k)) for k in R.SOFTWARE_REFS)
    return (f"<section class='refs' id='refs'>{_h2(7, 'refs', t('h.refs_title'))}<p class='hint'>{html.escape(t('h.refs_note', date=R.VERIFIED_ON))}</p>"
            f"<h3>{html.escape(t('h.refs_bia'))}</h3><ol>{bia}</ol><h3>{html.escape(t('h.refs_methods'))}</h3><ol>{meth}</ol>"
            f"<h3>{html.escape(t('h.refs_software'))}</h3><ol>{soft}</ol></section>")


def _rigor_section(cfg: dict, manifest: dict, out_dir: Path | None = None, tables: dict | None = None) -> str:
    from .i18n import t
    v = manifest.get("versions") or {}
    def _hash_line(k: str, x: str) -> str:
        df = (tables or {}).get(k[:-4] if k.endswith(".csv") else k)
        empty = df is None or df.empty                       # EN: "empty" = no data rows (the file still carries its header)
        return f"{k}: {x}" + (f" ({t('h.empty')})" if empty else "")
    st = manifest.get("study") or cfg.get("study") or {}
    rows = [(t("h.data"), st.get("data_name") or Path(str(cfg["data"].get("path") or "")).stem), (t("h.researcher"), st.get("researcher") or "—"),
            (t("h.rigor.preset"), f"{manifest.get('preset')} — CV {cfg['audit']['cv']['folds']}×{cfg['audit']['cv']['repeats']}, B={cfg['audit']['bootstrap']['B']}"),
            (t("h.rigor.seeds"), f"cv={cfg['seeds']['cv']}, bootstrap={cfg['seeds']['bootstrap']} · {manifest.get('resampling_scheme', '')}"),
            (t("h.rigor.versions"), f"bioms-zaku {manifest.get('package_version')} · catalog {manifest.get('catalog_version')} · " + " · ".join(f"{k} {x}" for k, x in v.items() if k != "platform")),
            (t("h.rigor.input"), f"{manifest.get('input_path')} · {manifest.get('input_rows')} → {manifest.get('rows_out')} · {manifest.get('input_sha256')}"),
            (t("h.rigor.outputs"), "<br>".join(_hash_line(k, x) for k, x in (manifest.get("outputs_sha256") or {}).items())),
            (t("h.rigor.time"), f"{manifest.get('wall_seconds')} s · {manifest.get('started_at')} → {manifest.get('finished_at')}"),
            (t("h.rigor.threads"), f"{manifest.get('threads')} / {manifest.get('n_jobs')}"),
            (t("h.rigor.decl"), str((cfg.get("declarations") or {}).get("targets_independent_of_variables"))),
            (t("h.rigor.samplestats"), "<br>".join(html.escape(f"{st}: {m}: " + ", ".join(f"{k} = {x:.4g}" for k, x in d.items())) for st, dd in (manifest.get("sample_statistics") or {}).items() for m, d in dd.items()) or "—"),
            (t("h.rigor.warnings"), "<br>".join(html.escape(w) for w in manifest.get("warnings") or []) or "—"),
            (t("h.rigor.notes"), "<br>".join(html.escape(w) for w in manifest.get("notes") or []) or "—")]
    body = "".join(f"<tr><td>{html.escape(k)}</td><td>{x if k in (t('h.rigor.outputs'), t('h.rigor.warnings'), t('h.rigor.notes'), t('h.rigor.samplestats')) else html.escape(str(x))}</td></tr>" for k, x in rows)
    head = f"{manifest.get('preset')} · CV {cfg['audit']['cv']['folds']}×{cfg['audit']['cv']['repeats']} · B={cfg['audit']['bootstrap']['B']} · seeds cv={cfg['seeds']['cv']} bootstrap={cfg['seeds']['bootstrap']}"
    return (f"{_h2(6, 'rigor', t('h.rigor_title'))}<details class='block' open><summary><span class='n'>6.1</span>{html.escape(t('h.rigor_title'))}<span class='hint'>{html.escape(head)}</span></summary>"
            f"<div class='body'><div class='tw'><table class='kv'>{body}</table></div><p class='hint'>{html.escape(t('h.rigor.determinism'))}</p></div></details>")


def write_report(out_dir: Path, cfg: dict, tables: dict[str, pd.DataFrame], manifest: dict) -> Path:
    from .i18n import t, get_language
    out_dir = Path(out_dir); fd = out_dir / "figures"
    study = cfg.get("study") or {}
    data_name = study.get("data_name") or Path(str((cfg.get("data") or {}).get("path") or cfg["run_name"])).stem
    researcher = study.get("researcher") or ""
    title = f"BioMS Zaku — {data_name}"
    fig_title = (cfg.get("figures") or {}).get("title") or ""
    sub = (cfg.get("figures") or {}).get("subtitle") or ""
    summary_md = (out_dir / "summary.md").read_text(encoding="utf-8") if (out_dir / "summary.md").exists() else ""
    captions = {}
    rm = fd / "README.md"
    if rm.exists():
        cur = None
        for line in rm.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "): cur = line[3:].strip()
            elif cur and line.startswith("**") and cur not in captions: captions[cur] = line.split("— ", 1)[-1]
    xlsx = write_excel(out_dir, tables)
    kw = _block_kwargs(cfg, manifest, tables)
    cat = _catalog(cfg)
    lang = cfg.get("language") or get_language()
    parts = [f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title><style>{CSS}</style></head><body>"]
    logo = _svg(LOGO)
    chips = "".join(f"<span class='chip'>{html.escape(str(x))}</span>" for x in (f"preset {manifest.get('preset', '')}", f"bioms-zaku {manifest.get('package_version', '')}", lang, str(manifest.get('finished_at', ''))[:10]) if x)
    from .i18n import t as _t
    who = f"<p><b>{html.escape(_t('h.researcher'))}:</b> {html.escape(researcher)}</p>" if researcher else ""
    extra = "".join(f"<p>{html.escape(x)}</p>" for x in (fig_title, sub) if x)
    parts.append(f"<header>{'<img src=' + chr(34) + logo + chr(34) + ' alt=BioMS-Zaku>' if logo else ''}<span class='brand'>BioMS Zaku</span>"
                 f"<h1><span>{html.escape(_t('h.data'))}:</span> {html.escape(data_name)}</h1>{who}{extra}<div class='chips'>{chips}</div></header>")
    nav = (("about", t("n.about")), ("key", t("n.key")), ("summary", t("n.summary")), ("figures", t("h.figures")), ("results", t("h.results")),
           ("rigor", t("h.rigor_title")), ("refs", t("h.refs_title")), ("manifest", t("h.manifest")))
    parts.append("<nav class='toc'>" + "".join(f"<a href='#{a}'>{html.escape(l)}</a>" for a, l in nav) + "</nav><main>")
    parts.append(_about(cfg, manifest))
    parts.append(_kpi(cfg, manifest, tables, cat))
    parts.append(f"<section id='summary'>{_h2(3, 'summary', t('n.summary'))}<details class='block'><summary><span class='n'>3.1</span>{html.escape(t('h.summary_text'))}</summary>"
                 f"<div class='body summary'>{_md_to_html(summary_md)}</div></details></section>")
    parts.append(f"<section id='figures'>{_figures(fd, captions)}</section>")
    # ---- results: method text + tables per block, one block open at a time
    parts.append(f"<section id='results'>{_h2(5, 'results', t('h.results'))}")
    if xlsx is not None:
        parts.append(f"<p><a class='dl' href='{xlsx.name}' download='{xlsx.name}'>{html.escape(t('h.download_xlsx'))}</a></p>")
    else:
        parts.append(f"<p class='hint'>{html.escape(t('h.xlsx_hint'))}</p>")
    shown = set(); i = 0
    for key, names in BLOCKS:
        present = [n for n in names if tables.get(n) is not None and not tables[n].empty]
        if key == "m.design" and not (manifest.get("design") or {}).get("indices"):
            continue                                            # EN: the block exists only when indices were designed
        if not present and key not in ("m.input", "m.design"):
            continue
        i += 1
        parts.append(f"<details class='block' name='results'{' open' if i == 1 else ''}><summary><span class='n'>5.{i}</span>{html.escape(t('b.' + key.split('.')[1]))}"
                     f"<span class='hint'>{html.escape(', '.join(present))}</span></summary><div class='body'>")
        parts.append(_method_block(key, **kw[key]))
        parts.append(_tables_block(present, tables, out_dir, key.split(".")[1]) + "</div></details>"); shown.update(present)
    rest = [n for n, df in tables.items() if n not in shown and df is not None and not df.empty]
    if rest:
        i += 1
        parts.append(f"<details class='block' name='results'><summary><span class='n'>5.{i}</span>{html.escape(t('h.tables'))}<span class='hint'>{html.escape(', '.join(rest))}</span></summary><div class='body'>"
                     + _tables_block(rest, tables, out_dir, "rest") + "</div></details>")
    parts.append("</section>")
    # ---- rigour + references + manifest
    parts.append(_rigor_section(cfg, manifest, out_dir, tables))
    parts.append(_references(cfg, tables, cat, manifest))
    parts.append(f"{_h2(8, 'manifest', t('h.manifest'))}<details class='block'><summary><span class='n'>8.1</span>manifest.json</summary><div class='body'><pre>" + html.escape(json.dumps(manifest, indent=1, ensure_ascii=False, default=str)) + "</pre></div></details>")
    parts.append(f"</main><div class='lb' id='lb' hidden><img alt=''></div><footer>BioMS Zaku {manifest.get('package_version', '')} · {html.escape(data_name)}{(' · ' + html.escape(researcher)) if researcher else ''} · preset {manifest.get('preset', '')} · {manifest.get('finished_at', '')} · "
                 f"seeds cv={cfg['seeds']['cv']} bootstrap={cfg['seeds']['bootstrap']} · input sha256 {str(manifest.get('input_sha256', ''))[:12]}… · aggregates only, no row-level data</footer><script>{JS}</script></body></html>")
    p = out_dir / "report.html"
    p.write_text("\n".join(parts), encoding="utf-8")
    return p

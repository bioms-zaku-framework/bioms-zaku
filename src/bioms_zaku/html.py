"""
EN: Single-file HTML report: logo, title, summary, the official figures (embedded), tables (collapsible), manifest.
    Opens in any browser, travels by e-mail, contains only aggregates. Brand identity: biomspro.com violet→green.
ES: Informe HTML en un solo archivo.  PT: Relatório HTML em um único arquivo.
"""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path

import pandas as pd

LOGO = Path(__file__).resolve().parent / "data" / "logo.svg"   # EN: ships inside the package (an installed wheel has no docs/)
CSS = """
:root{--violet:#9333ea;--green:#22c55e;--vl:#c084fc;--gl:#4ade80;--ink:#1d1d1f;--ink2:#52514e;--line:#e6e5e1;--bg:#fcfcfb}
*{box-sizing:border-box}body{margin:0;font-family:Inter,"DejaVu Sans",Arial,sans-serif;color:var(--ink);background:var(--bg);line-height:1.45}
header{background:linear-gradient(90deg,var(--violet),var(--green));color:#fff;padding:22px 28px;display:flex;align-items:center;gap:22px}
header img{height:56px}header h1{font-size:20px;margin:0;font-weight:600}header p{margin:4px 0 0;opacity:.92;font-size:13px}
main{max-width:1180px;margin:0 auto;padding:22px 28px}h2{font-size:16px;margin:28px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;background:#fee2e2;color:#991b1b;margin-left:8px}
figure{margin:12px 0}figure img{max-width:100%;border:1px solid var(--line);border-radius:6px}figcaption{font-size:12px;color:var(--ink2);margin-top:6px}
details{margin:10px 0}summary{cursor:pointer;font-weight:600}table{border-collapse:collapse;font-size:12px;width:100%;overflow-x:auto;display:block}
th,td{border-bottom:1px solid var(--line);padding:4px 8px;text-align:left;white-space:nowrap}th{background:#f4f6fc;position:sticky;top:0}
pre{background:#f4f6fc;padding:10px;font-size:11px;overflow-x:auto}footer{color:var(--ink2);font-size:11px;padding:18px 28px;border-top:1px solid var(--line)}
.summary p,.summary li{font-size:14px}
.method{background:#f7f5fb;border-left:3px solid var(--violet);padding:8px 12px;margin:8px 0 12px;font-size:13px}.method b{color:var(--violet)}
.dl{display:inline-block;margin:4px 8px 4px 0;padding:3px 10px;border:1px solid var(--violet);border-radius:6px;color:var(--violet);text-decoration:none;font-size:12px}
.dl:hover{background:var(--violet);color:#fff}.hint{font-size:12px;color:var(--ink2)}.kv td:first-child{font-weight:600;white-space:nowrap}
"""


def _img(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _svg(path: Path) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode("ascii") if path.exists() else ""


def _md_to_html(md: str) -> str:
    """EN: minimal Markdown (headings, lists, blockquote, tables, paragraphs) — no external dependency."""
    out, in_table, in_list = [], False, False
    for line in md.splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            if not in_table:
                out.append("<table>"); in_table = True
            tag = "th" if not any("<tr>" in x for x in out[-3:]) and out[-1] == "<table>" else "td"
            out.append("<tr>" + "".join(f"<{tag}>{html.escape(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        if in_table:
            out.append("</table>"); in_table = False
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{html.escape(line[2:])}</li>"); continue
        if in_list:
            out.append("</ul>"); in_list = False
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            out.append(f"<h3>{html.escape(line[3:])}</h3>")
        elif line.startswith("> "):
            out.append(f"<p><span class='badge'>{html.escape(line[2:].replace('**', ''))}</span></p>")
        elif line.strip():
            out.append(f"<p>{html.escape(line)}</p>")
    if in_table: out.append("</table>")
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


def _method_block(key: str, **kw) -> str:
    from .i18n import t
    return ("<div class='method'>" + "".join(f"<p><b>{html.escape(t(h))}.</b> {html.escape(t(f'{key}.{k}', **kw))}</p>"
                                              for h, k in (("h.how", "how"), ("h.read", "read"), ("h.rig", "rigor"))) + "</div>")


def _tables_block(names: list[str], tables: dict, out_dir: Path, xlsx: Path | None) -> str:
    from .i18n import t
    parts = []
    for name in names:
        df = tables.get(name)
        if df is None or df.empty:
            continue
        parts.append(f"<details><summary>{name}.csv · {len(df)} {t('h.rows')} &nbsp; {_csv_link(name, df, out_dir, t('h.download_csv'))}</summary>"
                     + df.round(4).to_html(index=False, border=0, escape=True) + "</details>")
    return "\n".join(parts)


# EN: result blocks in reading order: (key of the method text, tables shown under it, function building the text kwargs)
def _block_kwargs(cfg: dict, manifest: dict, tables: dict) -> dict[str, dict]:
    from .i18n import t
    au = cfg["audit"]; g = cfg.get("geometry") or {}; al = cfg["algebra"]
    est = str(tables["audit"].estimator.iloc[0]) if "audit" in tables and not tables["audit"].empty else au["single"]["estimator"]
    ut = tables.get("utility"); cov = str(ut.covariates.iloc[0]).replace("+", " + ") if ut is not None and not ut.empty else "—"
    se = tables.get("sensitivity"); est_alt = str(se.estimator.iloc[0]) if se is not None and not se.empty else t("m.sens.none")
    return {
        "m.input": dict(sep=repr(manifest.get("sep_used")), dec=repr(manifest.get("decimal_used")), rin=manifest.get("input_rows"), rout=manifest.get("rows_out"),
                        strata=", ".join(f"{k} (n={v})" for k, v in (manifest.get("strata_used") or {}).items()) or "—"),
        "m.redund": dict(thr=al["redundancy_threshold"]),
        "m.spec": dict(est=est, f=au["cv"]["folds"], r=au["cv"]["repeats"], B=au["bootstrap"]["B"], mg=au["verdict"]["margin"], p=au["verdict"]["p_specific"], ci=f"{au['verdict']['ci']:.0%}"),
        "m.util": dict(cov=cov, mg=au["utility_margin"]),
        "m.geo": dict(pc=g.get("parallel_to_control"), cc=g.get("coupled_target_control"), r2=g.get("min_fit_r2")),
        "m.transfer": dict(tol=al["transfer_tol"], Bt=al["transfer_B"]),
        "m.sens": dict(margins=list(au["verdict"].get("sensitivity_margins", [])), ps=list(au["verdict"].get("sensitivity_p", [])), est_alt=est_alt),
        "m.screen": {},
    }


BLOCKS = (("m.input", ["sigma"]), ("m.redund", ["algebra", "pairs", "redundancy"]), ("m.spec", ["audit"]), ("m.util", ["utility"]),
          ("m.geo", ["implicit_vectors", "geometry"]), ("m.transfer", ["sigma_transfer"]), ("m.sens", ["threshold_sensitivity", "sensitivity"]),
          ("m.screen", ["screening", "combinations"]))


def _rigor_section(cfg: dict, manifest: dict) -> str:
    from .i18n import t
    v = manifest.get("versions") or {}
    rows = [(t("h.rigor.preset"), f"{manifest.get('preset')} — CV {cfg['audit']['cv']['folds']}×{cfg['audit']['cv']['repeats']}, B={cfg['audit']['bootstrap']['B']}"),
            (t("h.rigor.seeds"), f"cv={cfg['seeds']['cv']}, bootstrap={cfg['seeds']['bootstrap']} · {manifest.get('resampling_scheme', '')}"),
            (t("h.rigor.versions"), f"bioms-zaku {manifest.get('package_version')} · catalog {manifest.get('catalog_version')} · " + " · ".join(f"{k} {x}" for k, x in v.items() if k != "platform")),
            (t("h.rigor.input"), f"{manifest.get('input_path')} · {manifest.get('input_rows')} → {manifest.get('rows_out')} · {manifest.get('input_sha256')}"),
            (t("h.rigor.outputs"), "<br>".join(f"{k}: {x}" for k, x in (manifest.get("outputs_sha256") or {}).items())),
            (t("h.rigor.time"), f"{manifest.get('wall_seconds')} s · {manifest.get('started_at')} → {manifest.get('finished_at')}"),
            (t("h.rigor.threads"), f"{manifest.get('threads')} / {manifest.get('n_jobs')}"),
            (t("h.rigor.decl"), str((cfg.get("declarations") or {}).get("targets_independent_of_variables"))),
            (t("h.rigor.warnings"), "<br>".join(html.escape(w) for w in manifest.get("warnings") or []) or "—")]
    body = "".join(f"<tr><td>{html.escape(k)}</td><td>{x if k in (t('h.rigor.outputs'), t('h.rigor.warnings')) else html.escape(str(x))}</td></tr>" for k, x in rows)
    return f"<h2>{t('h.rigor_title')}</h2><table class='kv'>{body}</table><p class='hint'>{html.escape(t('h.rigor.determinism'))}</p>"


def write_report(out_dir: Path, cfg: dict, tables: dict[str, pd.DataFrame], manifest: dict) -> Path:
    from .i18n import t
    out_dir = Path(out_dir); fd = out_dir / "figures"
    title = (cfg.get("figures") or {}).get("title") or f"BioMS Zaku — {cfg['run_name']}"
    sub = (cfg.get("figures") or {}).get("subtitle") or ""
    summary_md = (out_dir / "summary.md").read_text(encoding="utf-8") if (out_dir / "summary.md").exists() else ""
    captions = {}
    rm = fd / "README.md"
    if rm.exists():
        cur = None
        for line in rm.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "): cur = line[3:].strip()
            elif cur and line.startswith("**") and cur not in captions: captions[cur] = line.split("— ", 1)[-1]
    figs = sorted(fd.glob("*.png")) if fd.exists() else []
    xlsx = write_excel(out_dir, tables)
    kw = _block_kwargs(cfg, manifest, tables)
    parts = [f"<!doctype html><html lang='{cfg.get('language', 'en')}'><head><meta charset='utf-8'><title>{html.escape(title)}</title><style>{CSS}</style></head><body>"]
    logo = _svg(LOGO)
    parts.append(f"<header>{'<img src=' + chr(34) + logo + chr(34) + ' alt=BioMS-Zaku>' if logo else ''}<div><h1>{html.escape(title)}</h1><p>{html.escape(sub)}</p></div></header><main>")
    parts.append("<section class='summary'>" + _md_to_html(summary_md) + "</section>")
    # ---- figures
    parts.append(f"<h2>{t('h.figures')}</h2>")
    for f in figs:
        key = next((k for k in sorted(captions, key=len, reverse=True) if f.stem == k or f.stem.startswith(k + "_")), f.stem)
        parts.append(f"<figure><img src='{_img(f)}' alt='{f.stem}'><figcaption><b>{f.stem}</b> — {html.escape(captions.get(key, ''))}</figcaption></figure>")
    # ---- results: method text + tables per block
    parts.append(f"<h2>{t('h.results')}</h2>")
    if xlsx is not None:
        parts.append(f"<p><a class='dl' href='{xlsx.name}' download='{xlsx.name}'>{html.escape(t('h.download_xlsx'))}</a></p>")
    else:
        parts.append(f"<p class='hint'>{html.escape(t('h.xlsx_hint'))}</p>")
    shown = set()
    for key, names in BLOCKS:
        present = [n for n in names if tables.get(n) is not None and not tables[n].empty]
        if not present and key != "m.input":
            continue
        parts.append(f"<h3>{html.escape(t('b.' + key.split('.')[1]))} <span class='hint'>({html.escape(', '.join(present))})</span></h3>")
        parts.append(_method_block(key, **kw[key]))
        parts.append(_tables_block(present, tables, out_dir, xlsx)); shown.update(present)
    rest = [n for n, df in tables.items() if n not in shown and df is not None and not df.empty]
    if rest:
        parts.append(f"<h3>{html.escape(t('h.tables'))}</h3>" + _tables_block(rest, tables, out_dir, xlsx))
    # ---- rigour + manifest
    parts.append(_rigor_section(cfg, manifest))
    parts.append(f"<h2>{t('h.manifest')}</h2><details><summary>manifest.json</summary><pre>" + html.escape(json.dumps(manifest, indent=1, ensure_ascii=False, default=str)) + "</pre></details>")
    parts.append(f"</main><footer>BioMS Zaku {manifest.get('package_version', '')} · preset {manifest.get('preset', '')} · {manifest.get('finished_at', '')} · "
                 f"seeds cv={cfg['seeds']['cv']} bootstrap={cfg['seeds']['bootstrap']} · input sha256 {str(manifest.get('input_sha256', ''))[:12]}… · aggregates only, no row-level data</footer></body></html>")
    p = out_dir / "report.html"
    p.write_text("\n".join(parts), encoding="utf-8")
    return p

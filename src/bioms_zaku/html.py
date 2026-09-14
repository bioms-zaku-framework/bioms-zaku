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

LOGO = Path(__file__).resolve().parents[2] / "docs" / "assets" / "logo.svg"
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


def write_report(out_dir: Path, cfg: dict, tables: dict[str, pd.DataFrame], manifest: dict) -> Path:
    fd = Path(out_dir) / "figures"
    title = (cfg.get("figures") or {}).get("title") or f"BioMS Zaku — {cfg['run_name']}"
    sub = (cfg.get("figures") or {}).get("subtitle") or ""
    summary_md = (Path(out_dir) / "summary.md").read_text(encoding="utf-8") if (Path(out_dir) / "summary.md").exists() else ""
    captions = {}
    rm = fd / "README.md"
    if rm.exists():
        cur = None
        for line in rm.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "): cur = line[3:].strip()
            elif cur and line.startswith("**") and cur not in captions: captions[cur] = line.split("— ", 1)[-1]
    figs = sorted(fd.glob("*.png")) if fd.exists() else []
    parts = [f"<!doctype html><html lang='{(cfg.get('figures') or {}).get('language', 'en')}'><head><meta charset='utf-8'><title>{html.escape(title)}</title><style>{CSS}</style></head><body>"]
    logo = _svg(LOGO)
    parts.append(f"<header>{'<img src=' + chr(34) + logo + chr(34) + ' alt=BioMS-Zaku>' if logo else ''}<div><h1>{html.escape(title)}</h1><p>{html.escape(sub)}</p></div></header><main>")
    parts.append("<section class='summary'>" + _md_to_html(summary_md) + "</section>")
    from .i18n import t
    parts.append(f"<h2>{t('h.figures')}</h2>")
    for f in figs:
        key = f.stem.split("_")[0]
        parts.append(f"<figure><img src='{_img(f)}' alt='{f.stem}'><figcaption><b>{f.stem}</b> — {html.escape(captions.get(key, ''))}</figcaption></figure>")
    parts.append(f"<h2>{t('h.tables')}</h2>")
    for name, df in tables.items():
        if df is None or df.empty:
            continue
        parts.append(f"<details><summary>{name}.csv · {len(df)} {t('h.rows')}</summary>" + df.round(4).to_html(index=False, border=0, escape=True) + "</details>")
    parts.append(f"<h2>{t('h.manifest')}</h2><details><summary>manifest.json</summary><pre>" + html.escape(json.dumps(manifest, indent=1, ensure_ascii=False, default=str)) + "</pre></details>")
    parts.append(f"</main><footer>BioMS Zaku {manifest.get('package_version', '')} · preset {manifest.get('preset', '')} · {manifest.get('finished_at', '')} · "
                 f"seeds cv={cfg['seeds']['cv']} bootstrap={cfg['seeds']['bootstrap']} · input sha256 {str(manifest.get('input_sha256', ''))[:12]}… · aggregates only, no row-level data</footer></body></html>")
    p = Path(out_dir) / "report.html"
    p.write_text("\n".join(parts), encoding="utf-8")
    return p

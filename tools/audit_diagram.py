"""
EN: Audit of the Zaku diagram (v0.9): renders figures/zaku_method.svg in headless Chrome for every language and several font
    families, measures every <text> with getBBox() and checks that it lies inside its enclosing box (the column rects, the
    pills, or the canvas) with a 2 px tolerance. Exit code 1 on any overflow. Run: python tools/audit_diagram.py
    Not a unit test (needs Chrome); the unit test checks the generator's own bounds (tests/test_diagram.py).
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bioms_zaku.diagram import zaku_svg  # noqa: E402
from bioms_zaku.i18n import LANGS, set_language  # noqa: E402

CHROME = next((c for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c)), None)
FONTS = ["", "DejaVu Sans", "Liberation Sans", "Noto Sans", "DejaVu Serif", "Verdana", "Arial", "monospace"]   # EN: "" = the page's own stack
JS = """
<script>
window.addEventListener('load',function(){
  var out=[];var svg=document.querySelector('svg');
  var boxes=[].slice.call(svg.querySelectorAll('rect')).filter(function(r){return +r.getAttribute('rx')>=9;});
  var vb=svg.viewBox.baseVal;
  [].slice.call(svg.querySelectorAll('text')).forEach(function(t){
    var b=t.getBBox(); var x=+t.getAttribute('x');
    var box=null;
    boxes.forEach(function(r){var rx=+r.getAttribute('x'),ry=+r.getAttribute('y'),rw=+r.getAttribute('width'),rh=+r.getAttribute('height');
      if(x>=rx&&x<=rx+rw&&b.y>=ry-1&&b.y<=ry+rh){ if(!box||rw<+box.getAttribute('width')) box=r; }});
    var L=box?+box.getAttribute('x'):0, R=box?L+ +box.getAttribute('width'):vb.width, T=box?+box.getAttribute('y'):0, B=box?T+ +box.getAttribute('height'):vb.height;
    var over=Math.max(b.x+b.width-(R-2), (L+2)-b.x, b.y+b.height-(B-1), 0);
    if(over>0) out.push([t.textContent, over.toFixed(1), b.x.toFixed(1), (b.x+b.width).toFixed(1), L, R].join(' | '));
  });
  document.getElementById('out').textContent = out.length ? out.join('\\n') : 'OK';
});
</script>"""


def main() -> int:
    if CHROME is None:
        print("no Chrome/Chromium found; audit skipped"); return 0
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        for lang in LANGS:
            set_language(lang); svg = zaku_svg()
            for font in FONTS:
                css = f"<style>svg text{{font-family:{font} !important}}</style>" if font else ""
                page = Path(td) / f"{lang}_{font or 'default'}.html"
                page.write_text(f"<!doctype html><html><head><meta charset='utf-8'>{css}{JS}</head><body>{svg}<pre id='out'></pre></body></html>", encoding="utf-8")
                r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=2000", "--dump-dom", page.as_uri()],
                                   capture_output=True, text=True, timeout=90)
                m = re.search(r"<pre id=\"out\">(.*?)</pre>", r.stdout, re.S)
                res = html.unescape(m.group(1)) if m else "NO RESULT"
                status = "OK" if res == "OK" else "OVERFLOW"
                if res != "OK": bad += 1
                print(f"{lang} · {font or 'default stack':16s} {status}" + ("" if res == "OK" else "\n    " + res.replace("\n", "\n    ")))
    print("\nresult:", "all texts inside their boxes" if bad == 0 else f"{bad} page(s) with overflow")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

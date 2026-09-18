"""EN: the quality gate, LOCAL. Reproduces step by step what the CI workflow did, on this machine and this Python.
Why it exists: GitHub Actions is billed on a private repository and was switched off on 2026-09-18 (see
.github/workflows/ci.yml). The steps are the CI steps, not a weaker substitute: build + twine check, install the
wheel like a user in a CLEAN virtual environment (an editable install once hid that the catalogue was not shipped),
the whole suite, an example run repeated to compare output hashes, and init/check/run from a directory outside the
repository. What is NOT covered here and only a matrix can give: Python versions other than the one running this.

ES: puerta de calidad local — los pasos del CI en esta máquina.  PT: portão de qualidade local — os passos do CI aqui.

    python tools/gate.py [--reuse-venv] [-n 10]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = ("build + twine check", "clean venv + install the wheel", "test suite",
         "example run is deterministic", "external user outside the repository")
t0 = time.time()


def say(i: int, msg: str) -> None:
    """EN: progress with elapsed time and an estimate, from the first step (never a silent run)."""
    el = time.time() - t0
    eta = (el / max(i - 1, 1)) * (len(STEPS) - i + 1) if i > 1 else 0.0
    tail = f" | ETA {eta / 60:.1f} min" if i > 1 else ""
    print(f"[gate] {i}/{len(STEPS)} {msg} | {el:.0f}s{tail}", flush=True)


def run(cmd: list[str], cwd: Path | None = None, env_extra: dict | None = None) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-4000:]); print(r.stderr[-4000:], file=sys.stderr)
        raise SystemExit(f"[gate] FAILED: {' '.join(cmd[:4])}…")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse-venv", action="store_true", help="keep the previous environment (faster, less faithful)")
    ap.add_argument("-n", default="10", help="parallel test workers (needs pytest-xdist); 1 = serial, as the CI ran")
    a = ap.parse_args()
    dist, venv = ROOT / "dist", ROOT / ".gate-venv"

    say(1, STEPS[0])
    shutil.rmtree(dist, ignore_errors=True)
    run([sys.executable, "-m", "build"], cwd=ROOT)
    run([sys.executable, "-m", "twine", "check", *[str(p) for p in dist.iterdir()]], cwd=ROOT)

    say(2, STEPS[1])
    if not (a.reuse_venv and venv.exists()):
        shutil.rmtree(venv, ignore_errors=True)
        run([sys.executable, "-m", "venv", str(venv)])
    py = venv / "bin" / "python"
    wheel = next(dist.glob("*.whl"))
    pkgs = [str(wheel), "matplotlib", "pytest", "openpyxl"] + (["pytest-xdist"] if a.n != "1" else [])
    run([str(py), "-m", "pip", "install", "--quiet", "--upgrade", *pkgs])

    say(3, STEPS[2])
    run([str(py), "-m", "pytest", "-q"] + ([] if a.n == "1" else ["-n", a.n, "--dist", "loadfile"]), cwd=ROOT)

    say(4, STEPS[3])
    zaku = venv / "bin" / "bioms-zaku"
    out = ROOT / "zaku_out" / "minimal"
    shutil.rmtree(out, ignore_errors=True)
    run([str(zaku), "run", "examples/minimal.yaml"], cwd=ROOT)
    first = json.loads((out / "manifest.json").read_text())["outputs_sha256"]
    shutil.rmtree(out)
    run([str(zaku), "run", "examples/minimal.yaml"], cwd=ROOT)
    if json.loads((out / "manifest.json").read_text())["outputs_sha256"] != first:
        raise SystemExit("[gate] FAILED: two identical runs gave different outputs")
    print(f"[gate]   deterministic: {len(first)} output files", flush=True)

    say(5, STEPS[4])
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        shutil.copy(ROOT / "examples/minimal_data.csv", d / "meus_dados.csv")
        run([str(zaku), "init", "meus_dados.csv", "-o", "estudo.yaml", "--map",
             "R=resistencia_ohm", "Xc=reatancia_ohm", "H=estatura_cm", "W=massa_kg", "target=lmi_dxa",
             "control=fmi_dxa", "covariates=massa_kg,estatura_cm", "strata=sexo", "id=seqn", "independent=yes"], cwd=d)
        run([str(zaku), "check", "estudo.yaml"], cwd=d)
        import yaml
        c = yaml.safe_load((d / "estudo.yaml").read_text())
        c["preset"] = "quick"; c.setdefault("audit", {}).setdefault("bootstrap", {})["min_oob"] = 10
        (d / "estudo.yaml").write_text(yaml.safe_dump(c))
        run([str(zaku), "run", "estudo.yaml"], cwd=d)
        made = list((d / "zaku_out").rglob("report.html")) + list((d / "zaku_out").rglob("geometry.csv"))
        if len(made) < 2:
            raise SystemExit("[gate] FAILED: the external user did not get a report and a geometry table")

    print(f"[gate] ALL {len(STEPS)} STEPS PASSED in {(time.time() - t0) / 60:.1f} min "
          f"(Python {sys.version.split()[0]} only — other versions need the matrix)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

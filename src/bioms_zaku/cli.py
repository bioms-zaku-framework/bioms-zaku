"""
EN: `bioms-zaku run config.yaml` — sets BLAS thread limits BEFORE numpy is imported (determinism), then runs.
ES: fija los hilos BLAS antes de importar numpy, luego ejecuta.  PT: fixa threads BLAS antes de importar numpy, depois roda.
"""
from __future__ import annotations

import argparse
import os
import sys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="bioms-zaku", description="BioMS Zaku — decompose, audit and design indices")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run a configuration file (YAML)")
    r.add_argument("config"); r.add_argument("--threads", type=int, default=None)
    sub.add_parser("version")
    a = ap.parse_args(argv)
    if a.cmd == "version":
        from . import __version__; print(__version__); return 0
    threads = a.threads
    if threads is None:
        import yaml
        threads = int((yaml.safe_load(open(a.config, encoding="utf-8")) or {}).get("threads", 1))
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[k] = str(threads)
    from .run import run
    run(a.config)
    return 0


if __name__ == "__main__":
    sys.exit(main())

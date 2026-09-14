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
    i = sub.add_parser("init", help="build a configuration from a CSV (interactive; or --map role=column ...)")
    i.add_argument("csv"); i.add_argument("-o", "--out", default=None); i.add_argument("--sep", default="auto"); i.add_argument("--decimal", default="auto")
    i.add_argument("--encoding", default="utf-8"); i.add_argument("--map", nargs="*", default=None, help="role=column pairs, e.g. R=resistencia Xc=reatancia H=estatura W=massa_corporal target=lmi control=fmi independent=yes")
    c = sub.add_parser("check", help="validate configuration and data without running")
    c.add_argument("config")
    a = ap.parse_args(argv)
    if a.cmd == "version":
        from . import __version__; print(__version__); return 0
    if a.cmd == "init":
        from .wizard import init
        flags = dict(kv.split("=", 1) for kv in (a.map or [])) or None
        ask = None if flags else (lambda prompt, default: input(prompt + ": "))
        from .io import InputError
        try:
            init(a.csv, a.out, ask=ask, map_flags=flags, sep=a.sep, decimal=a.decimal, encoding=a.encoding)
        except InputError as e:
            print(f"init: {e}", file=sys.stderr); return 2
        return 0
    if a.cmd == "check":
        from .check import CheckError, check
        try:
            check(a.config)
        except CheckError:
            return 2
        return 0
    threads = a.threads
    if threads is None:
        import yaml
        threads = int((yaml.safe_load(open(a.config, encoding="utf-8")) or {}).get("threads", 1))
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[k] = str(threads)
    from .run import run
    from .check import CheckError
    from .io import InputError
    try:
        run(a.config)
    except (CheckError, InputError) as e:
        print(f"run: stopped — {e}", file=sys.stderr); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

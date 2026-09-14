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
    ap.add_argument("--lang", default=None, choices=["en", "es", "pt", "it"], help="language of messages, prompts, summary and figures (default: YAML `language`, else en)")
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
    from .i18n import set_language, t
    if a.lang:
        set_language(a.lang)
    if a.cmd == "version":
        from . import __version__; print(__version__); return 0
    if a.cmd == "init":
        from .wizard import init
        flags = dict(kv.split("=", 1) for kv in (a.map or [])) or None
        ask = None if flags else (lambda prompt, default: input(prompt + ": "))
        from .io import InputError
        try:
            init(a.csv, a.out, ask=ask, map_flags=flags, sep=a.sep, decimal=a.decimal, encoding=a.encoding, lang=a.lang)
        except InputError as e:
            print(t("cli.init_err", e=e), file=sys.stderr); return 2
        return 0
    if a.cmd == "check":
        from .check import CheckError, check
        if not a.lang:
            import yaml
            set_language((yaml.safe_load(open(a.config, encoding="utf-8")) or {}).get("language", "en"))
        try:
            check(a.config)
        except CheckError:
            return 2
        return 0
    threads = a.threads
    import yaml
    _y = yaml.safe_load(open(a.config, encoding="utf-8")) or {}
    if threads is None:
        threads = int(_y.get("threads", 1))
    if not a.lang:
        set_language(_y.get("language", "en"))
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[k] = str(threads)
    from .run import run
    from .check import CheckError
    from .io import InputError
    try:
        run(a.config)
    except (CheckError, InputError) as e:
        print(t("cli.run_stopped", e=e), file=sys.stderr); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

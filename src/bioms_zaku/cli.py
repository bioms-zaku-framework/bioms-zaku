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
    ap.add_argument("--version", action="store_true", help="show the welcome banner and the version")
    sub = ap.add_subparsers(dest="cmd", required=False)   # EN: no command → welcome banner (v0.9); `version` stays plain for scripts
    r = sub.add_parser("run", help="run a configuration file (YAML)")
    r.add_argument("config"); r.add_argument("--threads", type=int, default=None)
    sub.add_parser("version")
    i = sub.add_parser("init", help="build a configuration from a CSV (interactive; or --map role=column ...)")
    i.add_argument("csv"); i.add_argument("-o", "--out", default=None); i.add_argument("--sep", default="auto"); i.add_argument("--decimal", default="auto")
    i.add_argument("--encoding", default="utf-8"); i.add_argument("--map", nargs="*", default=None, help="role=column pairs, e.g. R=resistencia Xc=reatancia H=estatura W=massa_corporal target=lmi control=fmi independent=yes")
    c = sub.add_parser("check", help="validate configuration and data without running")
    c.add_argument("config")
    rd = sub.add_parser("render", help="re-write summary, figures and report of a finished run in another language (no recomputation)")
    rd.add_argument("out_dir")
    pr = sub.add_parser("propose", help="add your own indices to a configuration, one question at a time (formula checked on your data)")
    pr.add_argument("config")
    st = sub.add_parser("start", help="the guided path: columns → standard run → suggestions (accept/edit/no) → your own index → final report")
    st.add_argument("csv"); st.add_argument("-o", "--out", default=None); st.add_argument("--sep", default="auto"); st.add_argument("--decimal", default="auto")
    st.add_argument("--encoding", default="utf-8"); st.add_argument("--map", nargs="*", default=None, help="role=column pairs (no questions)")
    st.add_argument("--yes", action="store_true", help="accept every suggestion (scripts, CI)")
    ex = sub.add_parser("examples", help="list the bundled example data; --copy FOLDER copies them (never overwriting)")
    ex.add_argument("--copy", nargs="?", const="zaku_exemplos", default=None, metavar="FOLDER")
    ex.add_argument("--name", nargs="*", default=None, help="only these examples")
    ex.add_argument("--all", action="store_true", help="also list the technical files (older synthetic example, spreadsheet format, real NHANES sample)")
    a = ap.parse_args(argv)
    from .i18n import set_language, t
    if a.lang:
        set_language(a.lang)
    if a.cmd is None or a.version:                       # EN: a person at the terminal: welcome + the three commands
        from .banner import banner
        print(banner(full=True)); return 0
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
    if a.cmd == "start":
        from .start import start
        from .io import InputError
        flags = dict(kv.split("=", 1) for kv in (a.map or [])) or None
        ask = None if flags else (lambda prompt, default: input(prompt + ": "))
        try:
            start(a.csv, a.out, ask=ask, map_flags=flags, yes=a.yes, sep=a.sep, decimal=a.decimal, encoding=a.encoding, lang=a.lang)
        except InputError as e:
            print(t("cli.start_err", e=e), file=sys.stderr); return 2
        return 0
    if a.cmd == "propose":
        from .propose import propose
        from .io import InputError
        try:
            propose(a.config, ask=lambda prompt, default: input(prompt + (f" [{default}]" if default else "") + ": "), lang=a.lang)
        except InputError as e:
            print(t("cli.propose_err", e=e), file=sys.stderr); return 2
        return 0
    if a.cmd == "examples":
        from .datasets import copy_examples, list_examples
        rows = [r for r in list_examples(all=bool(a.all or a.name)) if not a.name or r["name"] in a.name]
        for r in rows:
            print(t("ex.line", name=r["name"], kind=t("ex.kind." + r["kind"]), n=r["rows"], csv=r["csv"], desc=r["description"]))
        if a.copy is not None:
            folder = copy_examples(a.copy, a.name)
            print(t("ex.copied", dir=folder.resolve()))
            print(t("ex.next", dir=folder))
        else:
            print(t("ex.hint"))
        if not (a.all or a.name):
            print(t("ex.more"))
        return 0
    if a.cmd == "render":
        from .run import render
        render(a.out_dir, a.lang)
        return 0
    def _with_lang(path: str):
        """EN: --lang overrides the YAML `language` by writing it into the configuration (manifest and report follow it)."""
        if not a.lang:
            return path
        import yaml
        y = yaml.safe_load(open(path, encoding="utf-8")) or {}
        y["language"] = a.lang
        return y
    if a.cmd == "check":
        from .check import CheckError, check
        try:
            check(_with_lang(a.config))
        except CheckError:
            return 2
        print(t("cli.next_run", cmd=f"bioms-zaku{' --lang ' + a.lang if a.lang else ''} run {a.config}"))   # EN: the run command, ready to paste (v0.9)
        return 0
    threads = a.threads
    import yaml
    _y = yaml.safe_load(open(a.config, encoding="utf-8")) or {}
    if threads is None:
        threads = int(_y.get("threads", 1))
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[k] = str(threads)
    from .run import run
    from .check import CheckError
    from .io import InputError
    try:
        run(_with_lang(a.config))
    except (CheckError, InputError) as e:
        print(t("cli.run_stopped", e=e), file=sys.stderr); return 2
    return 0


def entry() -> int:
    """EN: console entry point: Ctrl+C ends cleanly (exit code 130, the shell convention) instead of a traceback."""
    try:
        return main()
    except KeyboardInterrupt:
        print("\ninterrupted — nothing else was written", file=sys.stderr); return 130


if __name__ == "__main__":
    sys.exit(entry())

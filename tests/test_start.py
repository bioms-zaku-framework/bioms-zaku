"""EN: the guided path `bioms-zaku start` (contract §3.5): navigation, the three uses, reproducibility without questions,
independence of the validation from what was accepted, `--yes`, no English leak in pt."""
import hashlib
from pathlib import Path

import pandas as pd
import pytest
import yaml

from bioms_zaku.i18n import set_language
from bioms_zaku.start import Q, Screen, start

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "tests/minimal_data.csv"
FLAGS = {"R": "resistencia_ohm", "Xc": "reatancia_ohm", "H": "estatura_cm", "W": "massa_kg", "target": "lmi_dxa", "control": "fmi_dxa",
         "strata": "sexo", "labels": "0=F,1=M", "id": "seqn", "independent": "yes", "lang": "pt", "researcher": "Thalles Mota"}
# EN: the interactive answers for screens 1–2 (Enter = accept suggestion), then "correct a line?" → Enter
S12 = ["pt", "", "Thalles Mota", "",                  # lang, data name, researcher, correct a line? → Enter
       "", "", "", "", "", "",                        # R Xc H W (suggested), units
       "lmi_dxa", "fmi_dxa", "", "sexo", "0=F,1=M", "",   # target, control, covariates, strata, labels, id
       "", "", "", "", "",                            # sex age arm waist calf
       "yes", ""]                                     # independent, correct a line? → Enter


def _big_csv(tmp_path) -> Path:
    """EN: 900 rows with known structure (test_design_orthogonal._frame): enough for design (70 %) + audit (30 %) per sex."""
    from test_design_orthogonal import _frame
    p = tmp_path / "big.csv"; _frame(n=900, seed=11).to_csv(p, index=False); return p


# EN: answers for the big CSV (explicit columns; no suggestions relied upon), screens 1–2
SBIG = ["pt", "", "Thalles Mota", "",
        "R", "Xc", "H", "W", "", "",
        "lean", "fat", "", "sexo", "0=F,1=M", "seqn",
        "", "", "", "", "",
        "yes", ""]
FBIG = {"R": "R", "Xc": "Xc", "H": "H", "W": "W", "target": "lean", "control": "fat", "strata": "sexo", "labels": "0=F,1=M", "id": "seqn",
        "independent": "yes", "lang": "pt", "researcher": "Thalles Mota"}


def _ask(answers, log=None):
    """EN: scripted answers; prompts are appended to `log` (they are shown to the user, so leak tests must see them)."""
    it = iter(answers)
    def ask(prompt, default):
        if log is not None:
            log.append(prompt)
        try:
            return next(it)
        except StopIteration:
            raise AssertionError(f"ran out of scripted answers at prompt: {prompt!r}")
    return ask


def _quick(path):
    """EN: test runner: make the written YAML fast (quick preset, small folds) and run the real pipeline on it."""
    from bioms_zaku.run import run
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    cfg["preset"] = "quick"; cfg["audit"] = {"bootstrap": {"min_oob": 10, "B": 40}, "cv": {"folds": 3, "repeats": 1}}
    cfg["output"] = {"dir": str(Path(path).parent / "out"), "figures": False}
    Path(path).write_text(Path(path).read_text(encoding="utf-8").split("\n")[0] + "\n" + yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return run(cfg, printer=lambda s: None)


# ---------------------------------------------------------------- (h) navigation engine
def test_engine_back_help_correct_line_and_answers_persist():
    printed = []
    qs = [Q("a", lambda x: "A", help=lambda x: "help A", default=lambda x: "1"), Q("b", lambda x: "B", default=lambda x: "2"),
          Q("c", lambda x: "C", validate=lambda v, x: None if v != "bad" else "  c cannot be bad", required=True)]
    # answer a=1 (Enter), b=5, c: '?' shows help text (none → generic), '<' back to b (default now 5), keep 5, c=bad rejected, c=9; summary; correct line 2 → 7; Enter
    ans = _ask(["", "5", "?", "<", "", "bad", "9", "2", "7", ""])
    out = Screen(qs, ans, printed.append, {}).run()
    assert out == {"a": "1", "b": "7", "c": "9"}
    assert "help A" in printed and "  c cannot be bad" in printed and any("(no extra help" in p or "sem ajuda" in p for p in printed)
    # summary was printed with numbered lines, and the previous answer reappeared as the suggestion after '<'
    assert any(p.strip().startswith("1.") for p in printed) and any(p.strip().startswith("3.") for p in printed)


def test_two_back_and_forth_paths_with_the_same_final_answers_write_the_same_yaml(tmp_path):
    calls = []
    runner = lambda p: calls.append(p)
    a = start(str(CSV), str(tmp_path / "a.yaml"), ask=_ask(S12 + ["no", "no"]), printer=lambda s: None, runner=runner)
    # path 2: control = target (rejected, asked again), covariates accepted, then '<' back to the control, keep it, forward again
    b = start(str(CSV), str(tmp_path / "b.yaml"), ask=_ask(["pt", "", "Thalles Mota", "", "", "", "", "", "", "", "lmi_dxa", "lmi_dxa", "fmi_dxa", "<", "", "",
                                                             "sexo", "0=F,1=M", "", "", "", "", "", "", "yes", "", "no", "no"]), printer=lambda s: None, runner=runner)
    ya = yaml.safe_load(a.read_text(encoding="utf-8")); yb = yaml.safe_load(b.read_text(encoding="utf-8"))
    ya["run_name"] = yb["run_name"] = "x"
    assert ya == yb and len(calls) == 2                                                    # same answers → same YAML; one standard run each
    set_language("en")


# ---------------------------------------------------------------- (a) the three uses, (d) 'no' everywhere = standard
def test_standard_use_runs_once_and_writes_a_reproducible_yaml(tmp_path):
    calls = []
    p = start(str(CSV), str(tmp_path / "s.yaml"), ask=_ask(S12 + ["no", "no"]), printer=lambda s: None, runner=lambda q: calls.append(q))
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert calls == [p] and "design" not in cfg and cfg["study"]["researcher"] == "Thalles Mota" and cfg["strata_labels"] == {"0": "F", "1": "M"}
    assert cfg["data"]["columns"]["targets"] == {"lmi_dxa": "lmi_dxa"} and cfg["catalog"] == {"include": "curated"}
    assert p.read_text(encoding="utf-8").startswith("# BioMS Zaku configuration")
    set_language("en")


def test_expert_use_shows_suggestions_without_verdicts_then_validates_on_never_seen_rows(tmp_path):
    printed = []
    # accept suggestion 1 (yes), edit suggestion 2 (name + round to 1 decimal → becomes proposed), accept 3, discard 4; no own index
    ans = SBIG + ["yes", "yes", "edit", "Meu_LM_M", "1", "yes", "no", "no"]
    p = start(str(_big_csv(tmp_path)), str(tmp_path / "e.yaml"), ask=_ask(ans), printer=printed.append, runner=_quick)
    txt = "\n".join(printed)
    assert "sugestão 1" in txt and "R² nas linhas de desenho" in txt and "vizinho" in txt and "nome sugerido: Zaku_LM_F" in txt
    for word in ("SPECIFIC", "TRACKS", "específico", "veredito"):
        assert word not in txt.split("rodada final")[0].split("sugestão 1")[1]              # nothing about verdicts before accepting
    assert "expoentes alterados à mão" in txt and "descartado" in txt and "rodada final" in txt
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert [d["id"] for d in cfg["design"]] == ["Zaku_LM", "Zaku_FM"] and cfg["data"]["columns"]["pairing"] == {"lean": "fat", "fat": "lean"}
    ue = cfg["catalog"]["user_entries"]; assert len(ue) == 1 and ue[0]["id"] == "Meu_LM_M" and ue[0]["provenance"]["formula_source"] == "proposed" and ue[0]["form"] == "monomial"
    out = tmp_path / "out" / (p.name.split(".")[0] + "_2")        # v1.2: standard run in <name>, final run in <name>_2
    alg = pd.read_csv(out / "algebra.csv")
    assert {"Zaku_LM", "Zaku_FM", "Meu_LM_M"} <= set(alg.method_id) and alg[alg.method_id == "Meu_LM_M"].proposed.all() and alg[alg.method_id == "Zaku_LM"].designed.all()
    man = yaml.safe_load((out / "manifest.json").read_text(encoding="utf-8"))
    assert set(man["design"]["indices"]) == {"Zaku_LM", "Zaku_FM"} and man["design"]["n_audit"] + man["design"]["n_design"] == man["design"]["n_with_target"]
    set_language("en")


def test_own_index_use_goes_through_propose_and_the_final_run(tmp_path):
    calls = []
    ans = S12 + ["no", "yes", "Meu", "", "", "Xc / H_m", "yes", ""]                        # no suggestions; own index: id, name, target, formula, keep, finish
    p = start(str(CSV), str(tmp_path / "o.yaml"), ask=_ask(ans), printer=lambda s: None, runner=lambda q: calls.append(q))
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert len(calls) == 2 and cfg["catalog"]["user_entries"][0]["id"] == "Meu" and cfg["catalog"]["include"] == ["curated", "Meu"] and "design" not in cfg
    set_language("en")


# ---------------------------------------------------------------- (b) reproduction without questions, (c) independence, (f) --yes
def test_yes_mode_needs_no_questions_and_the_yaml_reproduces_the_tables_byte_for_byte(tmp_path):
    p = start(str(_big_csv(tmp_path)), str(tmp_path / "y.yaml"), ask=None, map_flags=dict(FBIG), yes=True, printer=lambda s: None, runner=_quick)
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert [d["id"] for d in cfg["design"]] == ["Zaku_LM", "Zaku_FM"] and "user_entries" not in cfg.get("catalog", {})
    out = tmp_path / "out" / (p.name.split(".")[0] + "_2")        # the final run (the one the YAML describes)
    h1 = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in out.glob("*.csv")}
    from bioms_zaku.run import run
    cfg["output"]["dir"] = str(tmp_path / "again"); run(cfg, printer=lambda s: None)      # the written YAML, run again, no questions
    h2 = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in (tmp_path / "again" / p.name.split(".")[0]).glob("*.csv")}
    assert h1 == h2
    set_language("en")


def test_validation_numbers_do_not_depend_on_accepted_names_or_order(tmp_path):
    big = _big_csv(tmp_path)
    a = start(str(big), str(tmp_path / "n1.yaml"), ask=_ask(SBIG + ["yes", "yes", "yes", "yes", "yes", "no"]), printer=lambda s: None, runner=_quick)
    b = start(str(big), str(tmp_path / "n2.yaml"), ask=_ask(SBIG + ["yes", "edit", "Alfa_F", "", "edit", "Alfa_M", "", "edit", "Beta_F", "", "edit", "Beta_M", "", "no"]), printer=lambda s: None, runner=_quick)
    ra = pd.read_csv(tmp_path / "out" / "n1_2" / "audit.csv"); rb = pd.read_csv(tmp_path / "out" / "n2_2" / "audit.csv")   # final runs
    pub = lambda df: df[~df.method_id.isin(["Zaku_LM", "Zaku_FM", "Alfa", "Beta"])].sort_values(["stratum", "method_id", "target"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(pub(ra), pub(rb))                                       # published methods: identical numbers
    da = ra[ra.method_id == "Zaku_LM"].sort_values(["stratum", "target"]).drop(columns="method_id").reset_index(drop=True)
    db = rb[rb.method_id == "Alfa"].sort_values(["stratum", "target"]).drop(columns="method_id").reset_index(drop=True)
    pd.testing.assert_frame_equal(da, db)                                                 # the same designed index under another name: identical numbers
    set_language("en")


# ---------------------------------------------------------------- (g) no English leak in pt
def test_no_english_leak_in_the_portuguese_screens(tmp_path):
    printed = []
    start(str(_big_csv(tmp_path)), str(tmp_path / "l.yaml"), ask=_ask(SBIG + ["yes", "no", "no", "no", "no", "no"], log=printed), printer=printed.append, runner=lambda q: None)
    txt = "\n".join(printed)
    for en in ("suggestion ", "accept?", "reading   weighs", "do you want", "summary of this screen", "correct a line?"):
        assert en not in txt, en
    for pt in ("sugestão 1", "aceitar?", "leitura   pesa mais", "quer sugestões", "resumo desta tela", "corrigir alguma linha?"):
        assert pt in txt, pt
    set_language("en")


def test_cli_start_with_map_and_yes(tmp_path, monkeypatch):
    from bioms_zaku.cli import main
    import bioms_zaku.start as S
    calls = []
    monkeypatch.setattr(S, "start", lambda *a, **k: calls.append(k) or tmp_path / "z.yaml")
    assert main(["--lang", "pt", "start", str(CSV), "--map", "R=resistencia_ohm", "--yes"]) == 0
    assert calls and calls[0]["yes"] is True and calls[0]["map_flags"] == {"R": "resistencia_ohm"} and calls[0]["ask"] is None


# ---------------------------------------------------------------- findings of the user simulation (2026-09-15)
def test_invalid_yes_no_is_asked_again_never_read_as_no(tmp_path):
    printed = []
    start(str(CSV), str(tmp_path / "g.yaml"), ask=_ask(S12 + ["talvez", "no", "no"], log=printed), printer=printed.append, runner=lambda q: None)
    txt = "\n".join(printed)
    assert txt.count("responda yes ou no") == 1 and "sugestão 1" not in txt
    set_language("en")


def test_small_data_blocks_suggestions_before_showing_any(tmp_path):
    printed = []
    start(str(CSV), str(tmp_path / "b.yaml"), ask=_ask(S12 + ["yes", "no"], log=printed), printer=printed.append, runner=lambda q: None)
    txt = "\n".join(printed)
    assert "não é possível sugerir índices com estes dados" in txt and "deixaria ≈ 23 linhas" in txt and "sugestão 1" not in txt and "aceitar?" not in txt
    set_language("en")


def test_restart_on_the_same_file_offers_previous_answers_and_keeps_own_indices_when_told(tmp_path):
    from bioms_zaku.propose import propose
    out = tmp_path / "r.yaml"
    start(str(CSV), str(out), ask=_ask(S12 + ["no", "no"]), printer=lambda s: None, runner=lambda q: None)
    it = iter(["Meu", "", "", "Xc / H_m", "yes", ""]); propose(out, ask=lambda p, d: next(it), printer=lambda s: None, lang="pt")
    # second session: every question answered with Enter (the previous answers are the suggestions), keep the own index
    printed = []
    start(str(CSV), str(out), ask=_ask(["", "", "", ""] + [""] * 6 + [""] * 13 + ["yes", "no", "no"], log=printed), printer=printed.append, runner=lambda q: None)
    cfg = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert any("já existe" in l for l in printed) and cfg["data"]["columns"]["targets"] == {"lmi_dxa": "lmi_dxa"} and cfg["strata_labels"] == {"0": "F", "1": "M"}
    assert [e["id"] for e in cfg["catalog"]["user_entries"]] == ["Meu"] and cfg["catalog"]["include"] == ["curated", "Meu"]
    assert any("[Thalles Mota]" in l for l in printed)                                   # the previous researcher shown as the suggestion
    # third session: drop it when told
    start(str(CSV), str(out), ask=_ask(["", "", "", ""] + [""] * 6 + [""] * 13 + ["no", "no", "no"]), printer=lambda s: None, runner=lambda q: None)
    assert "user_entries" not in yaml.safe_load(out.read_text(encoding="utf-8")).get("catalog", {})
    set_language("en")


def test_ctrl_c_ends_cleanly_with_exit_code_130(monkeypatch, capsys):
    from bioms_zaku import cli
    def boom(prompt): raise KeyboardInterrupt
    monkeypatch.setattr("builtins.input", boom)
    monkeypatch.setattr("sys.argv", ["bioms-zaku", "--lang", "pt", "start", str(CSV)])
    assert cli.entry() == 130 and "interrupted" in capsys.readouterr().err
    set_language("en")


def test_questions_are_numbered_and_separated(tmp_path):
    printed = []
    start(str(CSV), str(tmp_path / "q.yaml"), ask=_ask(S12 + ["no", "no"], log=printed), printer=printed.append, runner=lambda q: None)
    nums = [l for l in printed if l.startswith("pergunta ")]
    assert [l for l in printed if l.startswith(("pergunta ", "question "))][:3] == ["question 1 of 3", "pergunta 2 de 3", "pergunta 3 de 3"]   # screen 1: the language question comes before the language is known
    assert "pergunta 1 de 18" in nums and "pergunta 18 de 18" in nums and nums.count("pergunta 11 de 18") == 1   # screen 2 with labels (18 questions)
    idx = printed.index("pergunta 1 de 18"); assert printed[idx - 1] == ""                      # a blank line before every question
    set_language("en")


def test_english_circumference_names_are_suggested_and_the_control_never_is():
    from bioms_zaku.wizard import suggest
    cols = ["ID", "SEX", "HEIGHT", "WEIGHT", "R", "Xc", "FM_pct", "braco_corrigido_cm", "Biceps_cm", "Waist_cm", "Calf_cm"]
    sug = suggest(cols)
    assert sug["waist"] == "Waist_cm" and sug["calf"] == "Calf_cm" and sug["arm"] is None      # two arm candidates → no suggestion (ambiguous)
    sug2 = suggest([c for c in cols if c != "braco_corrigido_cm"]); assert sug2["arm"] == "Biceps_cm"

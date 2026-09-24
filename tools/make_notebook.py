"""EN: generates examples/zaku_exemplo.ipynb — ONE notebook, narration in ENGLISH ONLY (user decision, 2026-09-24),
and a single line at the top (`LANG`) that makes the TOOL speak English, Spanish, Portuguese or Italian. The rule is
the one the documentation follows since 2026-09-21: what you read ABOUT the tool is English; what the tool SAYS to you
is in your language — messages, figures and the report. Written by a generator so the notebook always ships without
outputs and so a fact is written once.

    python tools/make_notebook.py [examples/zaku_exemplo.ipynb]
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "docs/assets/logo_small.png"      # EN: the small one on purpose — base64 of the large
                                                #     logo would add 634 KB to the notebook

CELLS: list[tuple[str, str]] = []
md = lambda s: CELLS.append(("md", s))
code = lambda s: CELLS.append(("code", s))

# ----------------------------------------------------------------------------------------------------------------
# Opening: what this is, before anything is configured or run.
# ----------------------------------------------------------------------------------------------------------------
_logo = base64.b64encode(LOGO.read_bytes()).decode()
md(f'<p align="center"><img src="data:image/png;base64,{_logo}" width="360" alt="BioMS Zaku"></p>'
   "\n\n# BioMS Zaku\n\n"
   "### The problem\n\n"
   "Bioimpedance has accumulated dozens of indices and predictive equations. Two difficulties follow, and neither is "
   "anyone's fault.\n\n"
   "**Many of them are the same thing under different names,** and there is no practical way to know which. An index "
   "published in 1994 can rank people almost exactly as one published in 1985 does; whoever proposes the second has "
   "no way of checking against every index that exists.\n\n"
   "**Validation usually stops at a correlation.** \"My index correlates with lean mass\" proves little, because "
   "larger people have more of every tissue: body size pushes everything up together, and an index that measures "
   "nothing but size will correlate with lean mass, with fat mass, and with almost any outcome you try.\n\n"
   "### What this tool does about it\n\n"
   "**It writes every index as a vector of exponents** and, from the covariance of the measured variables alone, "
   "**predicts which indices are redundant with which — before computing any of them.** That is algebra, not a "
   "simulation: the prediction is exact.\n\n"
   "**It makes you declare, before seeing any result, a target and a negative control** — something the index should "
   "predict, and something it should NOT predict if it measures what it claims. Then it tests, out of sample, "
   "whether the index predicts the target *beyond* what the control already predicts. When it does not, it says so.\n\n"
   "### Three things you can do with it\n\n"
   "1. **Audit an index that already exists** — is it new, does it measure what it claims, does it add anything?\n"
   "2. **Let the tool design an index from your data** — and then refuse it, if it does not survive the same audit.\n"
   "3. **Test a formula of your own** — written by you, judged by the same rule as a published method.\n\n"
   "This notebook does all three, in that order, on data that travel inside the package. There is nothing to "
   "download and nothing to upload. Run every cell (in Colab: **Runtime → Run all**); it takes about a minute.\n\n"
   "> The narration is in English. The **tool** speaks English, Spanish, Portuguese and Italian: change `LANG` in "
   "section 1 and every message, figure and the report itself come out in that language.")

code("%pip install -q bioms-zaku")

# ----------------------------------------------------------------------------------------------------------------
# 1. The data
# ----------------------------------------------------------------------------------------------------------------
md("## 1. The data in this example\n\n"
   "1400 people, **synthetic**. They were drawn from the means and covariances of NHANES 1999-2004, estimated "
   "separately for each cell of sex × doctor-diagnosed diabetes, so the association of diabetes with every variable "
   "is preserved. No real person is in this file; only μ and Σ left the source. The parameters are published beside "
   "the CSV, and `tools/make_zaku_example.py` reproduces it byte for byte.\n\n"
   "`load_example` reads the file from inside the installed package: no download, no upload, no path to fix.")

code('''LANG = "en"        # en · es · pt · it — the language the TOOL speaks (messages, figures, report)

from bioms_zaku.api import load_example, set_language

set_language(LANG)
df = load_example("zaku_exemplo")
print(df.shape)
df.head()''')

md("### The columns\n\n"
   "| column | what it is |\n|---|---|\n"
   "| `R`, `Xc` | resistance and reactance, bioimpedance at 50 kHz |\n"
   "| `H_cm`, `W` | stature and body mass |\n"
   "| `idade`, `sexo` | age and sex (0 = F, 1 = M) |\n"
   "| `BMXARMC`, `BMXWAIST`, `BMXCALF` | arm, waist and calf circumferences |\n"
   "| `LMI_DXA`, `ALMI_DXA`, `FMI_DXA` | lean, appendicular lean and fat mass indices by DXA — **the reference** |\n"
   "| `lean_kg`, `alm_kg`, `fat_kg` | the same three in kg, derived as index × stature² |\n"
   "| `label_synthetic` | a label built from **fat mass and age only** |\n"
   "| `diabetes` | the doctor-diagnosed answer of the source survey |\n\n"
   "**`label_synthetic` deserves a word: it is a known answer, built to check the tool.** No bioimpedance variable "
   "enters it. So if you declare it as the target with `FMI_DXA` as the control, **no index may come out specific** — "
   "and if one does, the tool is lying. That test travels inside the example.\n\n"
   "### Using your own data\n\n"
   "Point `data.path` at your CSV and rename the columns in `data.columns.variables` — that is all. Everything else "
   "in the configuration keeps working. The full list of what you can change is in the last section.")

# ----------------------------------------------------------------------------------------------------------------
# 2. Redundancy
# ----------------------------------------------------------------------------------------------------------------
md("## 2. Redundancy, predicted before anything is computed\n\n"
   "An index that is a product of powers is a **vector of exponents**. Over the variables `R, Xc, H, W`: the "
   "impedance index `H²/R` is `(-1, 0, +2, 0)` and the body mass index `W/H²` is `(0, 0, -2, +1)`.\n\n"
   "With **Σ**, the covariance of the *logarithms* of the measured variables, the Pearson correlation of the "
   "logarithms of any two indices is\n\n"
   "$$\\rho_{\\log}(a,b) = \\frac{a^{\\mathsf T}\\Sigma b}{\\sqrt{a^{\\mathsf T}\\Sigma a \\cdot b^{\\mathsf T}\\Sigma b}}$$\n\n"
   "an identity that holds for any distribution. **Neither index has to be computed.** Below, the prediction is "
   "compared with what the data show.")

code('''import numpy as np
from scipy.stats import spearmanr

from bioms_zaku.algebra import log_covariance, pearson_to_spearman, predicted_pearson_log

variables = ["R", "Xc", "H_cm", "W"]
ii  = np.array([-1, 0,  2, 0])      # H² / R
bmi = np.array([ 0, 0, -2, 1])      # W / H²

for sex, label in ((0, "F"), (1, "M")):
    d = df[df.sexo == sex]
    sigma, n = log_covariance(d, variables)
    predicted = pearson_to_spearman(predicted_pearson_log(ii, bmi, sigma))
    observed = spearmanr(d.H_cm ** 2 / d.R, d.W / d.H_cm ** 2).statistic
    print(f"{label} (n={n}):  predicted {predicted:+.3f}   observed {observed:+.3f}   difference {abs(predicted - observed):.3f}")''')

md("The prediction came out of Σ alone. Now the same two indices with women and men **mixed together**:")

code('''sigma, n = log_covariance(df, variables)
predicted = pearson_to_spearman(predicted_pearson_log(ii, bmi, sigma))
observed = spearmanr(df.H_cm ** 2 / df.R, df.W / df.H_cm ** 2).statistic
print(f"mixed (n={n}):  predicted {predicted:+.3f}   observed {observed:+.3f}")''')

md("About half of the value found inside each sex — and the algebra predicts that too. **Redundancy is a property of "
   "the population, not of the formulas:** mixing two populations changes Σ, and with it every correlation. That is "
   "why everything below is computed inside a stratum and never across strata.")

# ----------------------------------------------------------------------------------------------------------------
# 3. The audit
# ----------------------------------------------------------------------------------------------------------------
md("## 3. The audit: does the index measure what it claims?\n\n"
   "The question is not whether an index correlates with lean mass — almost everything does. It is whether it "
   "predicts lean mass **beyond** what a fat mass index already predicts. So the run declares, before seeing any "
   "result: target `LMI_DXA` (lean mass by DXA) and negative control `FMI_DXA` (fat mass by DXA). An index is "
   "*specific* only when it predicts the target beyond the control, and *tracks the control* when its apparent "
   "success is explained by the control. Everything is declared in the configuration — nothing is chosen after.\n\n"
   "**Regression or classification is read from the data, not declared.** A continuous target is a regression; a "
   "target with a few whole values is a classification. There is no key for it: point `targets` at `diabetes` "
   "instead of `LMI_DXA` and the whole analysis changes with it.\n\n"
   "**There is no `design` key below, so every row is audited:** 700 people per stratum. Keep that number — "
   "section 5 declares a design and it becomes 210.")

code('''from bioms_zaku.api import check, example_path, run

config = {
    "run_name": "notebook",
    "data": {
        "path": str(example_path("zaku_exemplo")),          # your own CSV goes here
        "columns": {
            "variables": {"R": "R", "Xc": "Xc", "H": "H_cm", "W": "W"},
            "units": {"H": "cm", "W": "kg"},
            "covariates": ["W", "H_cm"],
            # the three circumferences are in the example file and two curated methods need them (Rsp, Xcsp):
            # leaving them unmapped would silently reduce the catalogue from 7 evaluable methods to 5.
            "groups": {"sexo": "sexo", "idade": "idade",
                       "C_arm": "BMXARMC", "C_waist": "BMXWAIST", "C_calf": "BMXCALF"},
            "id": "id",
            "targets": {"LMI_DXA": "LMI_DXA"},
            "controls": {"FMI_DXA": "FMI_DXA"},
            "pairing": {"LMI_DXA": "FMI_DXA"},
        },
    },
    "strata": "sexo",
    "strata_labels": {0: "F", 1: "M"},
    # every CURATED method — the ones whose primary source was read in the original. 7 of the 8 run on these
    # columns; Hoffer 1969 is skipped and says why (it needs |Z| at 100 kHz, which this device does not record).
    "catalog": {"include": "curated"},
    "declarations": {
        "targets_independent_of_variables": True,           # DXA is not computed from R, Xc, H, W
        "target_kinds": {"LMI_DXA": "lean_mass", "FMI_DXA": "fat_mass"},
    },
    "preset": "quick",                                      # "full" for the publication-grade run
    "output": {"dir": "./zaku_out", "figures": True},
}

check(config)''')

md("`check` validates the configuration and the data and runs nothing. It is what tells you, before a run costs its "
   "minutes, how many methods are evaluable, which are skipped and why, whether each stratum can carry the bootstrap, "
   "and whether anything will be silently missing from the output.")

code("res = run(config)")

# ----------------------------------------------------------------------------------------------------------------
# 4. The verdicts
# ----------------------------------------------------------------------------------------------------------------
md("## 4. The verdicts\n\n"
   "One row per index and stratum. Five columns answer five different questions:\n\n"
   "| column | the question it answers |\n|---|---|\n"
   "| `redundant` | does an index published EARLIER already carry the same information? (Spearman ≥ 0.95; "
   "precedence goes to the older publication) |\n"
   "| `specific` | does it predict the target **beyond the negative control**? |\n"
   "| `useful` | does it add anything over body mass and stature alone? |\n"
   "| `identity` | is it the same formula as another index, up to a constant? (not merely similar — identical) |\n"
   "| `class` | the four above in one label, e.g. `redundant-specific-useful` |\n\n"
   "Read them together: an index can be specific and useless, redundant and still useful, or neither. The full "
   "numbers behind each — increments, intervals, sample sizes — are in `audit.csv` and in the report.")

code('''import pandas as pd

pd.read_csv(f"{res['out_dir']}/screening.csv")''')

# ----------------------------------------------------------------------------------------------------------------
# 5. The tool proposes
# ----------------------------------------------------------------------------------------------------------------
md("## 5. The tool proposes new indices\n\n"
   "The audit above judged what already exists. This is the other direction: from the SAME data the tool builds an "
   "index of its own.\n\n"
   "**This is where the data get split, and it is worth understanding before you run it.** Judging indices that "
   "already exist uses every row, because nothing is fitted and therefore nothing has to be held back. Building an "
   "index is different — an index fitted on rows and then judged on the same rows always looks good — so declaring "
   "`design` cuts the file **once**: 70 % of each stratum fits the exponents, and the other 30 % judges them. From "
   "that point the whole run is judged on that 30 %, the new index and the published methods alike, which is what "
   "makes them comparable. Expect the intervals to widen: n fell from 700 per stratum to 210.\n\n"
   "The design is not a shortcut past the audit. It produces a candidate, which then has to survive the same "
   "negative control.\n\n"
   "`expr` below is yours to change: any formula you write enters the same run beside the published methods, marked "
   "◇, with no DOI and never precedence over a publication.")

code('''import copy

config2 = copy.deepcopy(config)
config2["run_name"] = "proposals"
# the design cuts the file ONCE. The three keys below are the defaults, written out so the cut is visible.
# seed 42 makes the cut reproducible and the manifest records its hash. `fraction` accepts only 0.60, 0.70 or 0.75.
config2["design"] = [{"target": "LMI_DXA", "id": "Zaku_LMI",
                      "split": "holdout", "fraction": 0.70, "seed": 42}]
config2["catalog"] = {
    "include": ["curated", "my_index"],                              # the curated methods PLUS your formula
    "user_entries": [{
        "id": "my_index",
        "label": "H²·Xc/R (proposed)",
        "authors": "you",
        "target": "lean_mass",                                       # what it intends to measure
        "expr": "H**2 * Xc / R",                                     # <- write your own formula here
        "provenance": {"formula_source": "proposed"},
    }],
}

res2 = run(config2)

d = res2["manifest"]["design"]                        # what the cut actually did, from the manifest
print(f"fitted on {d['n_design']} rows, judged on {d['n_audit']} rows | {d['mode']}"
      f" fraction={d['fraction']} seed={d['seed']} stratified_by={d['stratify_on']} cut={d['design_hash']}")''')

md("The exponents the tool fitted, and the verdict each new index earned out of sample. `designed` marks the index "
   "the tool built (△); the proposed formula (◇) sits beside it and beside the published methods, judged by the same "
   "rule.\n\n"
   "**Watch what happens here.** The designed index reaches the target's own direction almost exactly — cos_Σ ≈ "
   "0.999 in the geometry table — and STILL does not come out specific. The tool is refusing its own proposal. The "
   "Geometry block of the report says why in one number: the flag `COUPLED_TARGET_CONTROL` is lit, because the lean "
   "and fat indices come from a single DXA scan and point nearly the same way in the measured space, so pointing at "
   "the target **is** pointing at the control. That is the framework working on itself, and it is why a designed "
   "index is audited and not trusted.")

code('''novos = pd.read_csv(f"{res2['out_dir']}/algebra.csv")
novos = novos[novos["method_id"].isin(["Zaku_LMI", "my_index"])]
display(novos[["method_id", "stratum", "vector_source", "fit_r2", "e_R", "e_Xc", "e_H", "e_W"]])

vereditos = pd.read_csv(f"{res2['out_dir']}/screening.csv")
vereditos[vereditos["method_id"].isin(["Zaku_LMI", "my_index"])]''')

# ----------------------------------------------------------------------------------------------------------------
# 6. The report
# ----------------------------------------------------------------------------------------------------------------
md("## 6. The report\n\n"
   "**This notebook produced two runs, so there are two reports:** `zaku_out/notebook/report.html` from section 3, "
   "on every row, and `zaku_out/proposals/report.html` from section 5, on the 30 % held back. Comparing them is the "
   "cheapest way to see what the split costs.\n\n"
   "Each `report.html` holds every number above with the method text beside it — how it was computed, how to read "
   "it, what rigour was applied — and a download for every table. It is one file: send it, archive it, cite it.\n\n"
   "To read a finished run in another language without recomputing anything: `render(res[\"out_dir\"], \"pt\")`.\n\n"
   "In a terminal, the same analysis without writing any Python: `bioms-zaku start my_data.csv` asks the questions "
   "one at a time. What the tool guarantees, and under which assumptions, is in `CONTRACTS.md`.")

md("### Opening the report in Colab\n\n"
   "In Colab the file sits on a machine in Google's cloud, not on yours: there is no desktop to double-click and no "
   "terminal. The tool detects that and, at the end of each run above, printed where the file is and how to fetch "
   "it — the folder icon on the left of Colab, then `zaku_out` → the run's folder → the three dots on "
   "`report.html` → Download.\n\n"
   "The cell below does the same thing without leaving the notebook: uncomment a line and the browser downloads "
   "the file. It is 2 MB and self-contained — the figures travel inside it, so one file is the whole report. "
   "Running this notebook on your own machine, ignore the cell: the report is displayed inline above, and the "
   "file is where the tool said it is.")

code('''# Colab only — remove the # from the lines below and run the cell.
# from google.colab import files
# files.download(f"{res['out_dir']}/report.html")          # section 3, all rows
# files.download(f"{res2['out_dir']}/report.html")         # section 5, the 30 % held back''')

# ----------------------------------------------------------------------------------------------------------------
# 7. Reference
# ----------------------------------------------------------------------------------------------------------------
md("## 7. Where to change what\n\n"
   "Everything you edit lives in the two configuration cells: `config` in section 3, `config2` in section 5.\n\n"
   "| where | what it changes |\n|---|---|\n"
   "| `LANG` (section 1) | the language the TOOL speaks: messages, figures, report |\n"
   "| `data.path` | your CSV |\n"
   "| `data.columns.variables` | what your columns are called |\n"
   "| `targets`, `controls`, `pairing` | **the question**: what to predict, and what to be protected against |\n"
   "| `strata` | the groups judged separately (here: sex) |\n"
   "| `covariates` | what *useful* is measured against (here: body mass and stature) |\n"
   "| `catalog.include` | which methods are audited: `curated`, `all`, or a list |\n"
   "| `preset` | `quick` to demonstrate · `full` to publish (2000 resamples, 5×50 cross-validation) |\n"
   "| `config2[\"design\"]` | asks the tool to BUILD an index — **this line, and only this line, creates the 70/30 "
   "split** |\n"
   "| `expr` | your own formula: any expression in `R`, `Xc`, `H`, `W` |\n\n"
   "Two things that are read and never declared: **the type of the analysis** (continuous target → regression; a few "
   "whole values → classification) and **the type of every control**, which may differ from the target's.")

nb = nbf.v4.new_notebook()
nb["cells"] = [nbf.v4.new_markdown_cell(s) if kind == "md" else nbf.v4.new_code_cell(s) for kind, s in CELLS]
nb.metadata.kernelspec = {"name": "python3", "display_name": "Python 3", "language": "python"}
nb.metadata.language_info = {"name": "python"}
out = Path(sys.argv[1] if len(sys.argv) > 1 else "examples/zaku_exemplo.ipynb")
nbf.write(nb, str(out))
print(f"written: {out} | {len(CELLS)} cells | narration: English only")

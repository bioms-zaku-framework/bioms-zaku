# Changelog

## 0.1.0.dev0 — 2026-09-10 (unreleased)
- Fix (2026-09-16, found by the user on a rerun): the figures folder belongs to the current run — figure files left by an
  earlier run in the same output folder (other strata) were being listed in the report; they are now removed before
  drawing (`make_all`), in `run` and `render` alike. Regression test added.
- Banner (2026-09-16): the welcome box now leads with `bioms-zaku start dados.csv` (questions, run, report), then `run`
  (repeat without questions) and `render` (another language); suggestions and the own index are named as living inside
  `start`; `init`, `check` and `propose` appear in one dim expert line. Four languages; tests updated.
- Citation audit (2026-09-16): every statistical and algebraic reference was read in the original (PDFs in
  `catalogo/fontes_primarias_indices/`; Efron 1979 by OCR) and each is now cited only for what it supports, with a sentence in
  the method text of the block it supports, in four languages, and the same wording in the contract. Kronmal 1993 and Atchley
  1976 leave the geometry block; Atchley also supports utility (dividing by size does not remove size); Nevill & Holder 1995
  and Heymsfield 2007 support the design block (log-linear fit of the exponents; powers derived in the sample, Benn principle);
  Spearman 1904 states why ranks and adds attenuation to the 0.95 anchor; the anchor now quotes the observed within-session
  ICC(2,1) 0.986–1.00 at 50 kHz (Lafontant 2026) and the two-model, three-posture, two-lead agreement with a level offset up
  to 1° (Yang 2023), so 0.95 is a floor below repeatability; Lipsitch 2010 declared by analogy (the conditional two-way form is
  this tool's extension) and its U-comparability criterion added to the control help; Hoerl & Kennard 1970 (standardized
  predictors, fixed α = 1 by design), Stone 1974 (fixed prescription, no nested validation), Bengio & Grandvalet 2004 (fold
  dispersion never used for inference; tag removed from sensitivity), Efron 1979 (principle only; pages 1–26) and the new
  Efron 1983 (out-of-bag ε₀; paired differences, .632 not applied); Cohen 1988 Case 1 with A = control and B = index, record
  year 1988; Cover 1974 as the reason screening classes are per index. Page ranges completed for JSTOR records; author
  spelling of Yang 2023 fixed. Software references verified unchanged.
- Declared assumptions and anchored thresholds (2026-09-16, contract §3.6, PLANO_v1.1_pressupostos.md): person-bootstrap
  interval for the observed Pearson of logs (Fisher removed; coverage tested); the audit runs on the logarithmic scale by default
  with the raw scale reported as sensitivity (`audit.scale`, `sensitivity_scale.csv`); the family-level interval 1 − 0.05/k on the
  same resamples (`verdict_family`, `ci_level` in the threshold sensitivity), identical to the primary when k = 1; missing values
  excluded and counted, results describe the people who remain, no imputation and no inference about the excluded; bootstrap
  intervals for the designed exponents (manifest, summary, suggestions); a report section "Assumptions and thresholds" in four
  languages, every state read from the run and every threshold with value, origin and support; three verified records anchor
  the redundancy threshold (Lafontant 2026; Yang 2023) and the verdict margin (Cohen 1988).
- Bootstrap validity (2026-09-15, found on a 33-row audit partition): the audit refuses a method when fewer than max(20, 10 % of B)
  resamples are valid (never a zero-width interval); `check`/`start` apply min_n and the out-of-bag rule to the AUDIT partition per
  stratum when indices are designed, with labels and the way out; warning when more than half of the resamples were dropped.
  Guided screens: "question k of n" and a blank line between questions; `Biceps_cm`-style names suggested for the arm; stratum
  labels in the check's count lines; designed indices named from the target column; the final configuration of `start` is
  checked again; the report's input text says how many rows went to the design.
- v1.0 guided path (2026-09-15, PLANO_v1.0_fluxo.md): `bioms-zaku start dados.csv` — one path through the three uses (standard,
  suggestions with accept/edit/no, own index); `<` back, `?` help, numbered summary and "correct a line?"; the YAML is written
  after each screen and reproduces the tables byte for byte with `run`; `--map … --yes` for scripts; Ctrl+C exits 130 cleanly;
  `init` no longer asks about design. The design stage of `run` is a shared function (`design_all`) so suggestions and the final
  run see the same vectors. Findings of a scripted user simulation, all fixed and tested: invalid yes/no answers are asked again;
  suggestions are refused before being shown when a stratum's audit partition would fall below `data.min_n`; `propose` rejects
  formulas with fewer than `min_n` positive finite values, constant formulas (also from `mean()`), ids of the catalogue, and warns
  when a formula orders people like a published method; a second `start` on the same file offers the previous answers and asks
  before dropping own indices; scalar formulas become columns; the audit never skips a method silently for lack of rows (warning),
  and `check` blocks a design whose audit partition per stratum is too small, with the way out. `GUIA_10_MINUTOS.md` (pt).
- Design of several indices, one shared partition, optional Σ-orthogonality (2026-09-15): `design` takes a list; all designed
  indices are audited on the same never-seen rows; `init` asks `design: none|target|control|both`; designed indices marked △
  everywhere, never precedence, with a method block in the report. Recorded and tested theorem: the OLS vector is conditionally
  orthogonal to the control's projection, so the plain design is the cleaned index for the conditional negative control; the
  marginal `orthogonal_to` (closed form) serves nuisance columns and tends to track the column conditionally (shown on a
  constructed case). Manifest `design.indices[id].per_stratum` keyed by stratum labels.
- `bioms-zaku propose analise.yaml` (2026-09-15): a common user adds own indices question by question (id, name, what it
  measures, formula); every formula is validated at once with the same catalogue rules as a run and evaluated on the data
  (finite/positive counts, min/median/max, sample statistics used); invalid ids and formulas are asked again; entries are
  written as proposed and listed in `catalog.include`; init's header is kept. `--lang` now overrides the YAML language for
  `check` and `run` by writing it into the configuration (so the manifest records the language actually used). Tested.
- Sample statistics in formulas (2026-09-15): `mean`, `median`, `sd` (and the constant `e`) in the expression grammar; each
  value used is recorded per stratum in the manifest, warned about, listed in the summary and in the rigour section;
  `algebra.uses_sample_stats`. `check()` from the API now applies the YAML language like `run()`. The author's eight BioMS
  indices ship as proposed entries in `examples/bioms_mota_proposed.yaml` (tested end to end, mean verified against the data).
- Proposed indices (2026-09-15): a researcher's own formula enters the audit as a `user_entries` item with
  `provenance.formula_source: proposed` — no DOI needed, explicit defaults recorded, never curated, never precedence over a
  published method, marked ◇ in tables, figures, summary, key numbers and references; audited only when listed in
  `catalog.include` (`[curated, my_id]` = curated ∪ ids); `check` warns when declared but not included. Tested (defaults,
  rejections, exact-vector check, precedence, include semantics, marks).
- Study identity (2026-09-15): `init` asks the data set name (default: file name) and the researcher responsible; both go
  to `study:` in the YAML, hence into the configuration SHA-256, the manifest (`study`), the `check` output, the report
  header (logo centred, "Data: <name>", "Researcher: <name>"), the rigour table and the footer. Tested: same data with a
  different researcher → different config hash, identical tables.
- Diagram texts bound to their boxes (2026-09-15, after two overflows found by the user): every text element knows its box;
  a conservative glyph-width estimate reduces the font and pins `textLength` when needed, so no font substitution can push a
  text past the edge. Unit test on the generator's bounds (tests/test_diagram.py) and a headless-Chrome measurement of every
  text against its box in four languages × eight font stacks (tools/audit_diagram.py, all inside; the audit is proven to flag
  an injected overflow). Report header: light grey, logo kept, brand name in the gradient; `check` ends with the `run` command.
- Terminal welcome (2026-09-15): `bioms-zaku` with no command and `bioms-zaku --version` print the letters in the brand
  gradient, the name attribution and the three commands, in the chosen language; the interactive `init` opens with the short
  form. Never in `run`, `check`, `render`, `init --map` or the plain `version` subcommand; colour only on a terminal
  (NO_COLOR and TERM=dumb respected). Tested.
- Report structure and references (2026-09-15, contract v0.9 §4.6): sticky table of contents; eight numbered sections; key
  numbers read from the tables (people, strata, methods, verdict pills, added value, target↔control coupling); figures grouped
  by family with translated titles, one family open at a time, click to enlarge; result blocks as an exclusive accordion (native
  `<details name>`, no library); tables with right-aligned numerics (1000 rows shown, CSV always complete); the Zaku method
  diagram (fixed SVG in the run language, inline and in `figures/zaku_method.svg`); a References section built from Crossref
  metadata verified on 2026-09-15 (`references.py`: the bioimpedance sources of the methods actually evaluated, the statistical
  and algebraic antecedents tagged by result block, the software executed) — two candidate DOIs were rejected at verification
  (the Lipsitch 2010 erratum, a waist-girth paper); print stylesheet that opens every section; verdict colours identical to the
  figures. Tests: structure and order, exclusive accordion, diagram inline = on disk, references = methods of the run, every
  catalogue DOI has a verified record, no external resource, no English leak in pt (new strings included).
- Content review of the report, nine fixes (2026-09-15): screening classes carry the four conditional verdicts (BOTH and
  NEITHER were wrongly 'inconclusive'); Σ-transfer table header without inner pipes; no contract references (§, v0.x) in
  user text; the overwrite note is an operational note (manifest `notes`, rigour section), not a scientific warning; R² in
  the audit line; empty tables marked in the hash list; `init` asks labels for the stratum values (`labels=0=F,1=M`) and
  keeps the original column names as target/control keys; an 'About this report' section with citation (equal to
  CITATION.cff, tested) and licence.
- Summary formatting (2026-09-15): thresholds shown with fixed precision after a CSV round-trip (0.03, not 0.0299…);
  the Σ-transfer block keeps the CSV order in both `run` and `render`.
- `render` (2026-09-14): re-write summary, figures and report of a finished run in another language from the saved tables,
  no recomputation, tables and manifest untouched (tested). Lineage captions in es/pt completed (the 'family tree' half
  was missing); caption length parity across languages is now tested.
- Notebook inline report (2026-09-14): relative IFrame when the report lies under the notebook folder (Jupyter served an
  absolute path as 404), embedded srcdoc otherwise; no IPython warning.
- Runs are named after the YAML, not the CSV (two analyses of one file no longer overwrite each other); `run` announces
  when an output folder already holds a previous run (printed and in the manifest); 'Estimator sensitivity (not requested)'
  when no second estimator was configured (2026-09-14).
- Self-explaining `init` (2026-09-14): an intro and one help line before each question, in four languages, interactive mode
  only (`--map` stays quiet).
- Usability (2026-09-14, evening): `init` asks the language as a clear first question and prints it in the mapping with its
  origin; `run` ends with the absolute report path and the exact open command for the platform ('paste this in the terminal').
  Bug fixed: a run with a single evaluable method crashed (empty redundancy table without columns).
- Report as the product (2026-09-14, contract v0.8 §4.6, PLANO_v0.8_relatorio.md): per-block method text (how · read ·
  rigour) in en/es/pt/it with numbers from the resolved configuration; CSV download buttons embedded (base64, offline);
  optional `tables.xlsx` (extra `[excel]`); 'Rigour of this run' section; report path printed by `run`, inline in notebooks;
  logo shipped inside the package. Tests: links equal the hashed files, sizes, Excel with/without openpyxl, text follows
  the configuration, inline only in notebooks, balanced HTML, text = tables, no English leak in pt.
- Terminal simulation, report inspection (2026-09-14): figure captions matched by longest name (target_control had none);
  scorecard column headers in two lines with truncation (long column names no longer overlap), coupling note in the footer;
  '‡ coupled' and the panel note in the catalogue (4 languages); skipped-method reasons, task names, role meanings and the
  screening table translated; metric shown as R².
- Language selector (2026-09-14, contract v0.7): one message catalogue in en/es/pt/it (98 keys; identical keys and placeholders
  tested), `--lang` on the CLI and `language:` in the YAML (asked first by `init`); prompts, check/run messages, summary, report
  headings, figure texts and captions follow it. Machine-readable names (CSV columns, YAML keys, verdicts, flags) stay in English.
- Terminal simulation (2026-09-14, interactive `init`): a typo in a column name re-asks instead of aborting; control equal to the
  target is refused; the independence answer is printed in the mapping (with a warning when `no`); the suggester recognises
  `reatancia`/`reatt` and `body_mass`/`massa`; prompts state the physical meaning of R, Xc, H, W. W is BODY MASS in kg (a scale
  measures mass, not weight); the symbol W stays as the BIA literature's convention, the wording changes everywhere.
- External-user audit on real subsamples (2026-09-14): `run` now performs the `check` pre-flight and stops on blocking problems
  (a 60-row sample produced a report with every audit skipped); `init` records `data.encoding` and, when the file is not
  utf-8, says which `--encoding` to pass instead of a traceback; CLI exit code 2 with a one-line message on input/validation errors.
  Hollow markers and * in figures now mean NOT CURATED (§2.1), not 'provenance not high'; `algebra.csv` carries `curated`.
- External-user simulation, Colab (2026-09-14) — three defects found and fixed at the root: (1) the catalogue JSON was outside
  the package and a pip-installed user had none (`FileNotFoundError`); it now ships inside `bioms_zaku/data/` and CI installs
  from the built wheel, never editable, with an 'external user' step run outside the repository, on Python 3.10–3.13.
  (2) `init` silently wrote `catalog.include` with five indices; it now includes the whole catalogue. (3) `init` could not map
  the columns the equations need; new optional roles `sex`, `age`, `arm`, `waist`, `calf` (suggested, never assumed), and
  `check` now says, per skipped method, which column is missing and how to map it. DESIGN RULE restated after a wrong change
  the same day: only CURATED methods are audited by default (`catalog.include: curated`, written in the YAML by `init`; catalog
  1.4.0 adds `curated` + `curation_record` to the 8 entries whose primary source was critically read); `all` is an explicit choice.
- CI fix (2026-09-14): the dashed outline of flagged bars is only set on flagged bars; matplotlib 3.10 (Python 3.10 job)
  rejects a dash pattern with linewidth 0. First real CI run on GitHub: 3.11 and 3.12 green, 3.10 fixed here.
- Scorecard layout (2026-09-14, after inspection): method labels wrap to two lines inside their column; the "repeats" note
  is two short lines (predecessor / ρ). No text runs into a pill any more.
- Geometry of target and control (2026-09-14, contract v0.6, §3.3): implicit exponent vectors of every continuous target and
  control (OLS of the logs, with fit R²), Σ-cosines index–target, index–control and target–control, the exact identity
  r_log = cos_Σ·√R² for monomial indices (gap reported for fitted vectors), and two flags with declared thresholds:
  PARALLEL_TO_CONTROL (‡ on the scorecard, dashed outline on the target–control figure) and COUPLED_TARGET_CONTROL
  (‡ in the panel title). Flags annotate, never change, a verdict. New tables `implicit_vectors.csv`, `geometry.csv`;
  block in `summary.md`. Lesson 12 in the notebook (hand-calculated, tested to 1e-9); constructed-data tests; gate test on
  the shipped example (hand cosines 0.899/0.928 F, 0.855/0.909 M). Example data gain derived `lean_kg`, `alm_kg`,
  `fat_kg` (index × H², no new draw; CSV regenerated, parameters unchanged) and `examples/example_kg.yaml` shows absolute
  masses as targets. Motivated by external feedback on definitional coupling (lean + fat + bone = weight; both / H²).
- Threads (2026-09-14): `run()` now limits BLAS/OpenMP threads itself (`threadpoolctl`, declared dependency), so the Python
  API behaves like the CLI. Controlled A/B on the boosting sensitivity path (3 methods, 150 rows, 20-core machine):
  without the limit 25.7 s wall / 314 s CPU; with it 17.4 s wall / 17.4 s CPU; identical output hashes. The minimal example
  now audits 6 methods (was 24; 30 s → 8 s) and its YAML no longer carries B/repeats that the preset overrides; the
  sensitivity test uses 3 methods. Whole suite ~2 min (91 tests).
- Self-contained (2026-09-14, contract v0.5.2): no test reads data outside the repository. Removed the NHANES-bound
  equivalence tests, the catalog migration test/fixture/tool and `sigma_transfer_table_legacy`; `slow` marker gone.
  The example generator samples from the ROUNDED (published) μ, Σ and gains `--from-params`, so the shipped CSV is
  reproducible byte for byte from `example_data_params.json` (the CSV was regenerated; parameters unchanged). Three
  known-truth tests on the example (reproduction, μ/Σ, published Σ predicts observed ρ). Pre-commit runs the whole suite.
- Naming (2026-09-14): the full-resampling preset is now `full` (was `article`; a tool preset must not carry the name of
  one paper). Example files renamed to say what they are: `examples/example_data.csv` + `example_data_params.json`
  (was `nhanes_sintetico*`; the synthetic origin stays documented in the README and in the parameters file),
  `example_quick.yaml` / `example_full.yaml`, `minimal_data.csv` + `minimal.yaml` (was `sintetico.csv` / `minimo.yaml`);
  generators `tools/make_example_data.py` and `tools/make_minimal_data.py`; orphan `examples/minimo.csv` removed.
- Sensitivity implemented (2026-09-13, contract v0.5.1): estimator sensitivity on identical resamples (`sensitivity.csv`),
  threshold sensitivity by reclassification over a margin × P grid (`threshold_sensitivity.csv`), both summarised in
  `summary.md`. Documentation page rewritten as tool documentation (reading guide per figure); figures without in-figure
  legends by default (`figures.captions`), width capped; example dataset `examples/example_data.csv` (synthetic,
  parameters published). Quick vs full presets agree on all 28 verdicts of the example (median |ΔS1| 0.0005).
- Conditional negative control (2026-09-13, contract v0.5): the control enters as a predictor; S1 = gain for the target
  beyond the control, S2 = gain for the control beyond the target; verdicts SPECIFIC / TRACKS_CONTROL / BOTH / NEITHER;
  the marginal rule stays as `verdict_marginal`. Σ transfer in an n-fair metric (own vs transferred error, excess with a
  person bootstrap, fixed tolerance); Spearman conversion and Fisher-CI fraction removed from official outputs.
- Figures redefined (2026-09-11): lineage tree, negative-control map, exponents + Σ, scorecard as the official set; logo palette by default; `target_kind` in algebra.csv with an orientation warning.
- Catalog 1.1.0 (2026-09-11): exactness rule for monomial vectors (PhA and Z never in `vector`; PhA and LMI are now
  composite with fitted vectors and fit R²); Hoffer 1969 H²/|Z| (100 kHz) added from the primary source as the
  antecedent of Lukaski 1985; `history` field; migration test against a frozen snapshot.
- Catalog 1.1.1 → 1.3.3 (2026-09-11, curation on primary sources): Lukaski 1985, Baumgartner 1988, Piccoli 1994,
  Levi Micheli 2022 (LMI) and Marini 2013 / Buffa 2013 (specific BIVA) re-verified on the primary PDFs (provenance
  pdf_text/high); `derivation_sample` separated from `validity`; `target_kind` per entry; impedance ratio relabelled
  (commercial origin, Mulasi 2015 as source, confidence low). The catalog file is at 1.3.3 with 11 history entries;
  the message of commit 0d0c3cf says "catalog 1.3.4" by mistake (no 1.3.4 exists; nothing is missing).
- Framework end to end: input contract, catalog (31 methods migrated, validated at load), safe expression parser, algebra
  (exponent vectors, Σ, exact prediction, redundancy with precedence, Σ transfer), audit (paired OOB bootstrap, repeated
  CV, negative control, utility, combination gain, multiclass), index design with mandatory partition, report
  (tables, manifest, summary), CLI, three official figures + supplementary, trilingual captions.
- Equivalence with the previous analysis engine (NHANES 2026-09-09) was verified at 1e-9 on 2026-09-10 as a transition gate
  and removed on 2026-09-14 (the previous engine was a pilot; see 2026-09-14 entry).

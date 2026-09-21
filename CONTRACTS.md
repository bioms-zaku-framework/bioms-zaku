# BioMS Zaku — contracts of v1.0.0rc1 (change log in section 6)

Principle of v1.0: **the simplest possible version, without errors**. It covers the method; it does not cover every
context. What is left out is listed in section 0 and is a decision of scope, not an oversight.
Five contracts: input, catalog, configuration, outputs, reproducibility. Each one ends in **Justification**.

---

## 0. Scope of v1.0 (decisions of 2026-09-10)
- **The outcome belongs to the researcher.** The framework defines neither target, nor control, nor reference criterion;
  it requires only that labeled columns exist. It holds for lean mass, fat, sprint, sit-to-stand, any continuous or
  categorical label.
- **Reactance is mandatory.** Devices that do not deliver Xc are out.
- **Declared frequency, minimal.** The user declares the frequency of each R/Xc pair; more than one frequency can be
  mapped if available (each becomes its own variable: `R50`, `Xc50`, `R5`…). No comparison against the catalog, no
  device flags.
- **Out:** metadata of the reference criterion (DXA brand and so on); indices pre-computed by the device; segmental
  variables; sampling weights and survey design (we decompose signal inside a group, for that group; we do not estimate
  a population); Excel as input.
- **Two transversal rules:** every run prints progress and an estimated finish; no output contains individual row-level
  data, only aggregates.

---

## 1. INPUT contract

### 1.1 Shape
One table, **one row per person** (§3.2): a repeated `id` is refused at input, with the instruction to aggregate first.
CSV/TSV (`encoding` utf-8 by default; `latin-1`/`cp1252` by parameter; a decoding failure → error) or a
`pandas.DataFrame`.

### 1.2 Separator and decimal mark
Fixed order of attempts: `(",", ".")`, `(";", ",")`, `(";", ".")`, `("\t", ".")`, `("\t", ",")`.
A valid pair = the same number of columns on every row **and** every mapped numeric column converts.
Exactly one valid → it is used and written to the manifest; zero or more than one → an error asking for
`sep`/`decimal`. Duplicated names → error.

### 1.3 Mapping
| role | required | requirement |
|---|---|---|
| `variables` | yes, ≥ 2 | numeric, strictly positive (logarithm). For BIA: `R<f>`, `Xc<f>`, `H`, `W`; `<f>` = declared kHz; `R`/`Xc` without a suffix = 50 kHz |
| `units` | yes for `H`, `W` | `{H: cm|m, W: kg|g}`; only these conversions |
| `targets` | yes | continuous (regression) or categorical with 2..k classes (classification). **The type is read from the data and cannot be declared** (decision of 2026-09-21): a column with at most 10 distinct values, all whole numbers → a class; anything else → a number. Writing the same values with decimals (`0.0`, `1.0`) changes nothing, because the rule reads the value, not the format. `check` prints the type chosen for each column before the run costs anything |
| `controls` | yes | **of any type, independently of the paired target**; the type is read from the data in the same way. A class target with a continuous control, and the reverse, is permitted and audited with a metric per column (§3.2) |
| `pairing` | no | target → control; default: each target × the first control |
| `covariates` | no | numeric; the baseline of utility (if absent, utility does not run) |
| `strata` | no | categorical; Σ, redundancy and audit per stratum |
| `groups` | no | columns used by the catalog's `group_coding` (e.g. sex) |
| `id` | no | identifier |

Automatic derived variables when the canonical ones exist: `H_m`, `PhA = atan(Xc/R)·180/π`, `II = H_cm²/R`,
`Z = sqrt(R²+Xc²)`.

Example:
```yaml
columns:
  variables: {R: resistencia_ohm, Xc: reatancia_ohm, H: estatura_cm, W: massa_kg}
  frequency_khz: {R: 50, Xc: 50}
  units: {H: cm, W: kg}
  targets:  {LMI_DXA: lmi_dxa}
  controls: {FMI_DXA: fmi_dxa}
  covariates: [massa_kg, estatura_cm]
  strata: sexo
  groups: {sexo: sexo}
  id: seqn
```

### 1.4 Validation (fails early; the message names the column and the rows)
| situation | action |
|---|---|
| a mapped column is absent | error |
| a variable ≤ 0, non-numeric or infinite | error with the rows; `drop_nonpositive=true` removes them, warns, and counts them in the manifest |
| missing value in `variables`, or an index that cannot be computed | the row leaves the algebraic part **and** the audit of that method (complete case per method; `n` reported). Imputation only with `impute=true`, explicit and recorded in the manifest |
| missing value in `targets`/`controls` | the row leaves that target; counted in the manifest |
| n per stratum < `min_n` (30) | the stratum is ignored, with a warning |
| a class with fewer than `min_per_class` (20) cases in the stratum | the audit of that target does not run in the stratum, with a warning |
| repeated `id` | error, naming how many ids have more than one row and asking for aggregation (§3.2) |

### 1.4c Examples bundled in the package, and numbered outputs (v1.2, 2026-09-16)
`examples/` goes into the wheel as `bioms_zaku/examples` (nothing is downloaded). API `bioms_zaku.datasets`
(`list_examples`, `example_path`, `load_example`, `copy_examples`) and the command
`bioms-zaku examples [--copy FOLDER]`; the example is labeled **synthetic**; the copy never touches an existing folder
(`_2`, `_3`, …).
**One example base (decision of 2026-09-17):** `zaku_exemplo.csv`, synthetic, 200 per sex, drawn from log-normals whose
μ and Σ were estimated in NHANES 1999–2004 per cell sex × diabetes (DIQ010 1 vs 2; source n 79/2696 women, 60/2960
men); 70 with diabetes per sex (enriched, declared); `label_synthetic` depends only on ln FMI and ln age (a known
answer). Validation: in a large draw from the same parameters, the 12 × 12 correlation matrix (11 ln variables +
diabetes) differs from the reweighted NHANES one at 35 % by at most 0.013. Generator `tools/make_zaku_example.py` and
published parameters (byte-for-byte reproduction, tested). It is the only file copied by default; the others are
technical (`--all`). **Outputs**: if `output.dir/run_name` already holds a `manifest.json`, the run goes to
`run_name_2`, `_3`, …; `output.overwrite: true` replaces and the warning stays in the manifest;
`manifest.output_folder` records the folder.

### 1.5 Minimal example (synthetic; `;` and `,`)
```
seqn;sexo;estatura_cm;massa_kg;resistencia_ohm;reatancia_ohm;lmi_dxa;fmi_dxa
1;1;178,3;92,5;467,7;54,9;19,44;9,19
2;0;162,0;63,4;513,0;58,1;15,10;9,02
3;1;171,2;70,1;520,4;61,0;17,02;5,33
4;0;158,7;55,0;601,2;66,3;14,05;6,90
5;1;182,0;105,3;409,8;48,2;20,10;11,80
6;0;165,4;71,9;540,0;60,2;15,60;10,10
7;1;175,0;64,0;560,1;68,9;16,80;4,10
8;0;160,2;80,5;470,3;51,0;16,00;13,50
9;1;169,8;78,4;488,0;57,7;18,20;7,70
10;0;170,5;58,3;575,6;70,4;14,90;5,20
```

**Justification.** An explicit mapping makes the framework generic and eliminates a swapped column. Positivity is a
requirement of the logarithm. The frequency as part of the variable name is the minimum that prevents adding R at 5 kHz
to R at 50 kHz. Separator detection with a fixed order and "exactly one valid" fails instead of reading wrongly. CV and
bootstrap need independent rows, which is why one row per person is required.

---

## 2. CATALOG contract

### 2.1 Entry (one per method; per-group variants in `expr_by_group`)
| field | required | content |
|---|---|---|
| `id`, `label`, `authors`, `year`, `doi` | yes | a resolvable DOI (tested at load, cached; no network → warning) |
| `kind` | yes | `index` \| `equation` |
| `target` | yes | what the method declares it measures (descriptive) |
| `form` | yes | `monomial` \| `affine` \| `other` (listed, not evaluated) |
| `vector` | if monomial | exponents; **validated numerically against `expr`** (2.3) |
| `expr` / `expr_by_group` | yes | grammar 2.4; a branch only by columns of `groups`, never by target/control/covariate |
| `group_coding` | if a group is used | e.g. `{sexo: {male: 1, female: 0}}` |
| `frequency_khz` | yes | the frequency for which the formula was derived (informative) |
| `validity` | yes | applicability **stated or tested by the author**: `{age, bmi, sex, population}`, `null` where the author states nothing (no flag); outside the range → flag †, **never a block** — the researcher may apply any method to any context; the figure only warns |
| `target_kind` | no | the category of what the author says it measures: `lean_mass` \| `fat_mass` \| `body_water` \| `hydration` \| `cell_mass` \| `other`. Compared with `declarations.target_kinds` of the configuration (§3.2): a fat index audited against a lean-mass target receives the warning "tracks the control by design; swap target and control" — a warning, never a block |
| `derivation_sample` | no | who was used to fit it: `{n, sex, age, condition, country}`; descriptive, never raises a flag. Distinct from `validity` (Hoffer 1969: derived in 20 healthy men, tested and proposed for patients of both sexes, 18–77 years) |
| `provenance` | yes | `{formula_source: pdf_table|pdf_text|pmc_text|abstract|review_table, source_detail, verified_by, verified_on, confidence}`; default map pdf/pmc → high, abstract → medium, review → low |
| `check_example` | required for contributions | `{inputs, expected, tol}` with a published value; tested at load |
| `identity_of` | no | an exact transformation of another method → comes out as `identity`, excluded from the prediction statistics |
| `curated`, `curation_record` | no (default `false`) | **curated** = the primary source was read critically, with a record in `docs/LEITURAS.md`, and the entry approved. Requires `confidence: high` and a formula from a PDF. **Only curated methods enter the audit by default** (`catalog.include: curated`, §3.2). High confidence alone is NOT curation: a formula copied correctly from a PDF may not have gone through the reading. On 2026-09-14: 8 curated (Hoffer 1969, Lukaski 1985, Baumgartner 1988, Piccoli 1994 R/H and Xc/H, LMI, Rsp, Xcsp); the predictive equations stay in the catalog without curation until they are read one by one |
| `n`, `r2`, `see`, `device`, `reference_method`, `notes` | no | `null` when not informed; never invented |

### 2.2 Precedence
The smaller `year`; a tie → `date` (if informed) → the DOI lexicographically. A fixed rule.

### 2.3 Numerical validation at load
A monomial `vector`: 1,000 random positive vectors → evaluate `expr` → log-linear fit → the coefficients = `vector`
with |error| < `vector_tol` (default 1e-6; maximum 1e-4, numerical slack, not a budget for approximation).
**Exactness rule (v0.4.5):** the catalog's vector is exact or it is not a vector. Derived names that are not
monomials in the base variables (`PhA` = atan(Xc/R); `Z` = √(R²+Xc²)) are accepted in `expr`, never in `vector`; the
method is `composite`, receives a vector fitted per stratum, and the `fit_r2` goes into the table and the figure (the
old "linearise atan with a tolerance of 0.03" was removed: PhA and LMI became `composite`). `II` and `H_m` remain exact
re-expressions.
`check_example`: |expr(inputs) − expected| ≤ tol. A failure → an error at load.
Version and history: `catalog_version` (semantic) and `history` (one line per curation event: version, date, author,
change). Version 1.0.0 was born from the migration of the pilot's catalog (2026-09-08); since then the catalog
evolves only through curation, recorded in `history`.

### 2.4 Grammar (syntax tree, whitelist)
Numbers; the canonical names of the mapped and derived variables; the names in `groups`; `+ - * / ** ( )`;
`log exp sqrt atan atan2 abs min max`; `pi`, `e`. **Sample statistics (v0.9):** `mean(x)`, `median(x)`, `sd(x)` reduce
the argument over the evaluated rows (one stratum, the complete cases that enter the algebra) to a single number,
applied to every row (`sd` with ddof=1; NaN ignored). An index that uses them is not a fixed formula: its values change
in each sample. Therefore: every value used is recorded in the manifest (`sample_statistics[stratum][method]`), raises
a warning during the run, appears in the summary and in the rigor section of the report; `algebra.uses_sample_stats`
marks the method. They never use the target or the control (only mapped variables), so they leak no information from
the target into the cross-validation. Nothing else. A violation → an error at load.

### 2.5 Rule for a non-positive index
An `affine` equation with a value ≤ 0 on a row: the row leaves the algebraic part of that method
(`n_nonpositive_pred` in `algebra.csv`); in the audit the row stays.

### 2.6 Migration
`metodos_bia.json` → **31 entries** (8 indices + 23 equations; per-sex halves merged). Script tested.

### 2.7 Designing indices for a context (v0.4)
A new index may be built for a target (e.g. VO2max): a regression of ln(target) on ln(variables) in the **design** set;
the coefficients are the exponent vector of the new index. Mandatory rule: **design and audit on disjoint sets**.
- `design.split`: `holdout` (default) with `fraction: 0.70` (declared options 0.60, 0.75), `seed`, stratified by
  `strata` and, in classification, by class; or `by_stratum` (design in one stratum, audit in another; tests transfer).
- The reported numbers (Σ, redundancy, audit, utility) come **only from the audit partition**.
- The final vector for practical use is refitted on 100 % of the data and comes out labeled `refit_full=true`, with the
  design vector and the R² of both recorded in the manifest.
- A warning in the summary when the audit partition has n < 100 (wide intervals).
- The designed index enters the run's catalog as a `user_entry` with `provenance.formula_source = "designed"`,
  `confidence = "low"` and the hash of the design partition — it never goes into the built-in catalog without curation.
- Variables beyond BIA (e.g. heart rate per stage) enter as positive `variables` and enlarge Σ; a designed index may
  combine BIA and functional signals.
- The exponents are derived in the sample, never assumed (Benn's principle; Heymsfield 2007 shows β ≈ 2 for stature when
  stature is the only predictor). With W, R and Xc in the same fit, the exponent of H comes out below 2 (e.g. 1.05–1.27
  in NHANES), because part of size is absorbed by the other variables; this does not contradict Heymsfield, it is the
  same model with more predictors.

**Justification.** Auditing on the same set where the index was fitted measures fit, not validity. The partition is
standard machine-learning practice and it is what allows telling a strength coach "this index predicts VO2max in people
it has never seen". The final refit is what one does with any delivered model.

**Justification.** One entry per method is what precedence and redundancy require. `validity` marks without blocking.
`identity_of` prevents identities from inflating redundancy and accuracy. A branch only by `groups` closes the leak of
the sex-specific Segal equation. Numerical validation and `check_example` make a wrong formula fail at load, not in the
paper. A whitelist replaces `eval`.

---

## 3. CONFIGURATION contract

### 3.1 Full example (defaults = the analysis of the paper)
```yaml
run_name: my_study
data: {path: my_data.csv, encoding: utf-8, sep: auto, decimal: auto, columns: {…},
       drop_nonpositive: false, impute: false, max_missing_frac_warn: 0.10, min_n: 30, min_per_class: 20}
catalog: {path: builtin, include: curated, exclude: [], user_entries: []}   # curated (default) | all | [ids]
strata: sexo
algebra:
  fit_affine: true
  extra_log_variables: []        # e.g. [idade] to include it in the log-linear fit (default: only variables)
  min_fit_r2: 0.90               # below → poor_monomial
  redundancy_threshold: 0.95     # on |observed Spearman|
  min_pair_n: 30
  transfer: true
audit:
  single:                        # a single index
    estimator: ridge             # ridge | logistic | "module:Class"
    params: {alpha: 1.0}
  combination:                   # combination of axes (if combinations: true)
    estimator: hgb               # hgb (sklearn HistGradientBoosting) | xgboost (optional) | "module:Class"
    params: {max_depth: 3, learning_rate: 0.05, max_iter: 300}   # fixed, declared beforehand
  sensitivity: {estimator: null, params: {}, nested_tuning: false}   # same draws; reported alongside
  cv: {folds: 5, repeats: 50, stratified: auto}   # classification: stratified by class
  bootstrap: {B: 2000, min_oob: 20, max_attempts_factor: 6}
  utility_margin: 0.03
  verdict: {p_specific: 0.95, p_control: 0.05, ci: 0.95}
  multiplicity: none             # none | bh  (bh = Benjamini–Hochberg across methods, as a sensitivity)
  combinations: false
geometry:                        # v0.6 — target↔control diagnosis in the space of the mapped variables
  enabled: true
  parallel_to_control: 0.90      # |cos_Σ(index, control^)| ≥ → PARALLEL_TO_CONTROL
  coupled_target_control: 0.80   # |cos_Σ(target^, control^)| ≥ → COUPLED_TARGET_CONTROL
  min_fit_r2: 0.50               # a projection with R² below this → cosines reported, flags do NOT light (poor_projection)
seeds: {cv: 42, bootstrap: 42}
preset: full                     # quick (cv 5x5, B 200) | full
threads: 1
n_jobs: auto                   # auto = cores − 1 (v1.2); any integer ≥ 1; never changes a number
output: {dir: ./zaku_out, figures: true}
```

### 3.2 Rules
- **A valid bootstrap or none (v1.0, 2026-09-15; the case: CrossFit, 107 men, the design left 33 to audit → 1 valid
  resample in 2,000 → intervals of zero width and spurious verdicts).** (a) The audit of a method is refused, with a
  warning in the manifest, when the number of valid resamples (≥ `min_oob` out of the bag) falls below
  `max(20, 10 % of B)`, never above B; no degenerate interval is ever published. (b) `check` and `start` evaluate
  `min_n` and the feasibility of the bootstrap **on the audit partition** of each stratum when there is a design
  (`(1 − fraction) · n`), with labels, and block with the way out (more rows or no strata; the standard run is not
  affected). Practical consequence: designing indices with a valid audit requires ≈ 55 audited people per stratum
  (≈ 185 per stratum at 70/30). (c) A warning in the manifest when more than half of the resamples were discarded in a
  stratum. Tested.
- **`run` validates before running (2026-09-14).** The same verification as `check` runs at the start of `run` (CLI and
  API); a blocking problem stops the run with the messages of `check` and exit code 2. A report is never produced with
  every audit skipped. `init` records `data.encoding` and, if it cannot decode, says which `--encoding` to try (no
  traceback).
- **Catalog by default = curated only (design decision, 09-10, reaffirmed 09-14).** `catalog.include: curated` is the
  default of the package and of `init`; `all` is an explicit choice by the user and marks every output of a non-curated
  method with *; a list of ids is an explicit choice. Record of the error: on 09-14 the default was switched to `all`
  inside a bug fix, without consultation; reverted the same day and locked by tests (`tests/test_catalog.py`,
  `tests/test_init_check.py`). Working rule: a design decision never changes inside a fix.
- **Conditional negative control (v0.5).** Besides score(target | index) and score(control | index), the audit fits, on
  the SAME resamples, the control as a predictor of the target (with and without the index) and the target as a
  predictor of the control (with and without the index). Two paired increments: **S1** = score(target | control + index)
  − score(target | control), the signal about the target that the control does not carry; **S2** =
  score(control | target + index) − score(control | target), the signal about the control that the target does not
  explain. An increment is *present* when the mean > `verdict.margin` (0.03), the 95 % CI excludes 0 and
  P(d>0) ≥ `p_specific`. Verdicts: `SPECIFIC` (S1 present, S2 absent) · `TRACKS_CONTROL` (S2 present, S1 absent) ·
  `BOTH` (both: the index carries information that neither target nor control explains, e.g. body size) · `NEITHER`
  (none). The earlier rule (the marginal difference `disc`) stays in `verdict_marginal`, descriptive, for a side-by-side
  comparison with the conditional one. Justification: target and control are correlated (0.7 in NHANES); the marginal
  difference credited the index for the part of the target that the control also carries; the conditional one asks what
  the index adds.
- **Convenience sample.** The framework does not estimate population parameters: sampling weights are ignored by design
  and the verdicts describe the analyzed sample. The summary states this.
- `declarations.target_kinds` (optional): `{column: lean_mass|fat_mass|body_water|hydration|cell_mass|other}` for
  targets and controls. When the `target_kind` of a method matches the type of the control and differs from the type of
  the target, the summary and the report receive an orientation warning (v0.4.6). Without the declaration, nothing
  changes.
- The estimator is declared beforehand; no selection by result. `sensitivity` runs on the same draws and goes to
  `sensitivity.csv`; `nested_tuning: true` (Optuna, optional) only in that mode, with a warning about its cost.
- Pipeline: `StandardScaler` → estimator, over the **complete case**: in the audit of an index, the rows where the index
  and the target/control exist; in utility and in the combination, the rows complete on the **union** of the columns of
  the two compared configurations (the same people on both sides of the contrast). `impute: true` inserts
  `SimpleImputer(median)` before the standardization and is recorded in the manifest. Regression default `Ridge`;
  classification default `LogisticRegression(l2, C=1, lbfgs, max_iter=1000)`; multiclass: one-vs-rest.
- Metrics (v1.2, citation review of 2026-09-16): regression `r2_score`; classification **Tjur's D** = the mean of p̂ in
  the cases − the mean in the non-cases (Tjur 2009; the quantity that Pencina's 2008 IDI compares), asymptotically a
  fraction of variation explained, which is why the gains ΔD share the 0.03 margin of R² by declared analogy;
  multiclass: macro one-vs-rest D (an extension of this tool, declared). ΔAUROC is NOT a gain (insensitive even to
  strong markers, Pencina 2008); AUROC (Hanley & McNeil 1982) is reported as descriptive
  (`auroc_cv_target_full`, `auroc_cv_control_full`, `auroc_cv_with`); in the multiclass case, macro one-vs-rest AUROC is
  the only descriptive one (balanced accuracy, promised before and never implemented, was withdrawn on 2026-09-16: it
  depends on a probability cut-off, like F1; Brodersen 2010 read and judged dispensable). **Mixed types**: a class
  target with a continuous control (and vice versa) is allowed — task and estimator per column (L2 logistic for a class,
  ridge for a continuous one) on the same resamples; S1 in ΔD and S2 in ΔR², the same margin; `control_task` and
  `metric_control` in `audit.csv`. An estimator declared with parameters or as `module:Class` holds for every column.
  Under an L2 penalty the predicted probabilities shrink towards the base rate and D comes out smaller than without the
  penalty; since the gains are paired differences under the same shrinkage, the comparison between models is fair
  (declared; Tjur 2009, Le Cessie 1992). An OOB with a single class → the resample is discarded (`B_dropped`). `check`
  refuses a label that is constant or has a class below `min_per_class` inside a stratum (a label used as control cannot
  also be the stratum).
- **Events per variable (Peduzzi 1996), declared and never a barrier** (decision of 2026-09-16): for each classification
  model, `events_min_class` (the smaller class in the complete rows) and `epv_train` = 0.632 × smaller class ÷
  predictors (2 in the audit, covariates + 1 in utility; 0.632 = the distinct fraction of a bootstrap resample,
  Efron 1983); `epv_low` below 10. `check` warns; the report marks; the verdict comes out. The minimum per class stays
  at 20 (operational). A second classifier (hgb/xgboost) enters only as `sensitivity`, alongside, never chosen —
  boosting needs more data than the logistic model.
- **Resamples shared per stratum**: `default_rng(seeds.bootstrap)`, `integers(0, n, n)` until B resamples with an OOB ≥
  `min_oob`; used by every method, target, control, configuration and estimator. CV
  `RepeatedKFold`/`RepeatedStratifiedKFold(random_state=seeds.cv)`. `n_jobs` changes no number.
- **One row per person (v1.2, decision of 2026-09-16).** A repeated `id` is refused at input with the instruction to
  aggregate first (a mean per person, or one visit). Reason: the bootstrap resamples draw rows as independent people;
  repeated measurements would give intervals that are too narrow and optimistic verdicts. **Future work, to be
  rethought**: a cluster bootstrap (draw people and take all of their rows; out of the bag = the people not drawn),
  reference Field & Welsh 2007, JRSS B 69(3):369–390, 10.1111/j.1467-9868.2007.00593.x — it would open the pre/post
  case, common in BIA.
- **What the out-of-bag bootstrap is, and what it is not**: the resamples are also dependent on each other; the
  percentile interval is not an unbiased estimator of the variance. It is a procedure without a distributional
  hypothesis that resamples the whole pipeline per person (Efron 1979). Scoring each resample on the people not drawn is
  Efron's ε₀ estimator (Efron 1983, JASA 78:316–331): pessimistic for an absolute score (hence his .632), used here only
  in paired differences of nested models on the same rows, where the pessimism cancels; the .632 correction does not
  apply. The dispersion between the folds of the cross-validation never enters the inference, because no unbiased
  estimator of its variance exists (Bengio & Grandvalet 2004).
- `threads: 1` fixes OMP/OpenBLAS/MKL before importing numpy.
- Verdicts are **descriptive**: the bootstrap P is not a p-value; `multiplicity: bh` is a sensitivity.

**Justification.** With one index (one column), a flexible model can only capture monotone non-linearity and pays for it
in variance, inflating the score of the control in part of the resamples; the paired contrast requires a conservative estimator on both sides. Optimizing hyperparameters by result inside the bootstrap would break the pairing (different
choices for target and control) and would cost days; that is why it is a sensitivity mode, nested, declared. In the
combination of axes (several columns, interactions) boosting is justified, with fixed and declared hyperparameters.
Shared resamples reproduce the behavior of the reference and satisfy the condition of pairing.

---

### 3.3 Target↔control geometry (v0.6 — approved by Thalles on 2026-09-14)

**The problem it solves.** Target and control usually come from the same reference measurement and the same
normalization (e.g. lean mass/H² and fat mass/H² from the same DXA scan; lean + fat + bone = body mass, with H and W
mapped). In the space of the mapped variables they can point almost the same way. In that case an index close to that
direction (e.g. W/H²) predicts both by arithmetic, and the verdict of the negative control is right for the wrong
reason. v0.6 measures this and prints it beside the verdict. **It never changes a verdict**: the verdict is empirical
(out of sample); the geometry explains why.

**Definitions (per stratum, complete case, the same variables as the space of the indices: `variables` +
`extra_log_variables`).**
1. The *implicit vector* of a target or control y: the coefficients of the linear regression of ln y on the
   log-variables, with an intercept (`fit_log_linear`, the same function used by `composite` methods and by the design
   of §2.7). The R² of the fit is recorded. It is the best monomial approximation of y in the measured space; it is
   not y.
2. The *cosine under Σ* of two vectors a, b: cos_Σ(a, b) = aᵀΣb / √(aᵀΣa · bᵀΣb) — the same formula as
   `r_log_predicted` (§4.1). It is the Pearson correlation (in the logs) between the two linear combinations.
3. For each index i, target t and control c (pairs declared in `pairing`): cos_Σ(i, t^), cos_Σ(i, c^) and
   cos_Σ(t^, c^).
4. **Verification identity (exact, in-sample):** since a MONOMIAL index belongs to the subspace spanned by the
   log-variables and the residual ln y − ln y^ is orthogonal to that subspace, r_log(i, y) = cos_Σ(i, y^) · √R²_y. The
   table records the observed r_log(i, y), the predicted product and the gap; for indices with an exact vector
   (`vector_source = catalog`) the gap must be < 1e-9 (tested; in the example it comes out at ~1e-15). For composite
   indices (PhA, LMI, Rsp, Xcsp: fitted vector) the gap is the residual of the projection of the index itself and is
   reported, not tested. Everything for an index is computed on the complete rows of (index > 0, target > 0,
   control > 0, variables), so that the identity is exact by construction.

**Flags (fixed names; thresholds declared in the YAML and recorded in the manifest).**
- `PARALLEL_TO_CONTROL`: |cos_Σ(i, c^)| ≥ `parallel_to_control` (default 0.90 = 81 % of variance shared with the
  projection of the control). Reading: the index points where the control points; "tracks the control" or "both" was
  expected from the geometry.
- `COUPLED_TARGET_CONTROL`: |cos_Σ(t^, c^)| ≥ `coupled_target_control` (default 0.80 = 64 %). Reading: the whole
  contrast is weak by construction; it lights BEFORE the other one because the consequence is larger (it holds for
  every index).
- `poor_projection`: the R² of the projection < `min_fit_r2` (default 0.50) for t or c. The cosines stay in the table;
  the flags do not light, because the cosine between poor projections speaks of noise.
- The thresholds are reading aids, not hypothesis tests: the cosines always go into the table, at full precision.

**Where it appears.** `implicit_vectors.csv` and `geometry.csv` (§4.1); the "Geometry" block in the summary (§4.3:
target–control cosine per stratum, the list of flagged indices); the ‡ marker on the scorecard and the dashed outline on
the target×control map (§4.4); `report.html` inherits the tables. Zero new computation: `fit_log_linear`,
`log_covariance` and `predicted_pearson_log` are reused.

**Targets in kilograms (an option, not a rule).** A target in kg (absolute lean mass) instead of an index (mass/H²)
removes stature from both sides and reduces cos_Σ(t^, c^); it does NOT remove the coupling through W (lean + fat +
bone = body mass) and it makes the target more "size", which favors volume indices (H²/R). It is a declared choice of
the researcher; the framework accepts any column and prints the geometry of each choice. The bundled example therefore
carries `lean_kg`, `alm_kg` and `fat_kg`, derived as index × (H/100)² in the generator (columns recorded in
`zaku_exemplo_params.json` as derived; no new draw).

**Justification.** The criticism "target and control are arithmetic on the reference measurement" is the one a reviewer
would make. The scientific answer is neither to deny it nor to try to "decouple everything": it is to measure the
coupling with the algebra the method already uses and print it beside the verdict, so the researcher decides with the
number in hand. The utility axis (§3.2, the gain over W and H) remains what conditions on size; the geometry says how
much of the verdict is geometry.

**Known truths required (gate):** lesson 12 of the notebook (the cosine under Σ by hand, 1e-9); a target built as a
monomial ⇒ the implicit vector recovers the exact exponents and cos = 1 (1e-9); a control built parallel to the target ⇒
the flag lights, orthogonal ⇒ it stays off; the identity of item 4 on the bundled example (1e-9); the cosines of the
example (F: target–control 0.90; Rsp–control 0.93 · M: 0.86; 0.91, computed by hand on 09-14) reproduced by the table;
determinism and hash.

---

### 3.4 Language (v0.7, 2026-09-14)
- A single catalog of messages (`i18n.py`), four languages: `en`, `es`, `pt`, `it`. A test requires the same keys and
  the same format fields in all four; no message is left untranslated in silence.
- The choice in one place only: `--lang` on the CLI (valid for `init`, `check`, `run`) or `language:` in the YAML (`init`
  asks for the language first and records it). `figures.language` follows `language` unless declared. The API
  (`run(cfg)`) reads `language` from the YAML.
- Translated: the questions of `init`, the messages of `check` and `run`, `summary.md`, the headings of `report.html`,
  the texts of the figures and the captions of `figures/README.md`. **Declared exception (2026-09-19):** three
  SUPPLEMENTARY figures — `sigma_transfer`, `combination_gain` and `compass` — keep their title and axis labels in
  English; they are support material, produced only on request (`output.supplementary_figures`), and translating them
  would cost new keys for no return. The five official figures and the other supplementary ones follow the language of
  the run. NOT translated, for reproducibility between users:
  the column names of the CSVs, the YAML keys, the method ids, the verdicts (`SPECIFIC`, `TRACKS_CONTROL`, `BOTH`,
  `NEITHER`) and the names of the flags.
- Justification: the tool is for researchers; reading in one's own language is part of being intuitive. What is for the
  machine stays stable.

---

### 3.6 Declared assumptions and thresholds with an origin (v1.1, 2026-09-16)
Every report carries the section **Assumptions and thresholds**, generated from the run: each procedure with the
assumption it carries and its state in that run (by construction · verified, with the number · declared limitation), and
each threshold with its value, origin and support. The adjustments of assumption in this version:
- **Pairs:** a person bootstrap interval for the Pearson correlation of the logs (`r_log_lo`, `r_log_hi`, level
  `pair_ci_level`), with no distributional assumption; the Fisher interval (bivariate normality, rejected in NHANES) was
  removed. Coverage tested.
- **Scale of the audit:** `audit.scale: log` by default — the index, the continuous targets/controls and the covariates
  enter as logarithms, the scale of the algebra; classification labels are never transformed; a non-positive value in a
  target/control/covariate makes the stratum fall back to the raw scale with a warning (`audit.scale` recorded per
  row). The other scale is audited and reported in `sensitivity_scale.csv` (`audit.sensitivity.scale`, on in the `full`
  preset), never chosen.
- **k methods, one rule:** the verdict rule is per method, without correction, and the report says so; on the same
  resamples the interval at the family level 1 − 0.05/k is computed (`ci_family`, `verdict_family`, columns `*_fam`) and
  the threshold sensitivity gains one row per method with `ci_level` = the family level; with k = 1 it is identical to
  the default. Reported, never chosen.
- **Missing values:** rows with a missing value in the mapped columns are excluded and counted by reason; the results
  describe the people who remained; no imputation and no comparison with the excluded ones (the framework describes the
  analyzed sample, it does not estimate a population — decision of 2026-09-16).
- **Designed exponents:** a person bootstrap interval per exponent (`vector_lo`, `vector_hi`, B = `transfer_B`) in the
  manifest, in the summary and on the suggestions screen; the vector used is still the fit of the whole partition.

| threshold | value | origin | support |
|---|---|---|---|
| redundancy, \|Spearman\| ≥ | 0.95 | anchored in the literature | 0.95 sits below the within-session repeatability of the raw variables: ICC(2,1) at 50 kHz from 0.986 to 1.00 for R, Xc and PhA across four devices, ten seconds apart (Lafontant 2026, 10.2478/joeb-2026-0010), and PhA between two models of the same manufacturer, three postures and two electrodes ICC 0.993, with a systematic level offset of up to 1° (Yang 2023, 10.3390/life13051119: the order is preserved, the level shifts — hence rank correlation); two indices at 0.95 differ more than the repeated measurement does — a conservative floor; reliability holds per brand and model (data sets from different devices are never merged); the observable agreement between two indices of the same measurement is limited by √(ICC_a·ICC_b) (attenuation, Spearman 1904, 10.2307/1412159) — an anchor by analogy, declared as such; fixed sensitivity |
| verdict margin, gain in R² (regression) or in Tjur's D (classification) | 0.03 | anchored in the literature | Case 1 of ch. 9 of Cohen 1988 (2nd ed.; DOI of the reprint 10.4324/9780203771587): f² = ΔR²/(1 − R²_total), A = the control (or W and H), B = the index; a small f² = 0.02 ⇒ ΔR² ≤ 0.02 for any baseline, so 0.03 sits above it; Cohen's values are population values and the gain here is out of sample (a conservative margin); Cohen calls the convention a compromise to be rejected when it does not serve — hence a sensitivity grid; classification: the gain in Tjur's D, asymptotically a fraction of variation explained (exact relations with the quadratic R², Tjur 2009, 10.1198/tast.2009.08210), the same margin by declared analogy; ΔAUROC would be insensitive (Pencina 2008, 10.1002/sim.2929) |
| P(gain > 0) ≥ | 0.95 | convention | the mirror of the one-sided 5 % |
| level of the interval | 95 % | convention | universal; the family level 1 − 0.05/k is reported |
| margin of the added value | 0.03 | anchored | the same anchor as the verdict margin |
| cos parallel / coupled / projection R² | 0.90 / 0.80 / 0.50 | decision of the framework | descriptive flags; cosines and R² published in full |
| tolerance of the Σ transfer | 0.05 | decision of the framework | a fixed tolerance in r, fair with respect to n |
| bootstrap B | 2,000 | convention | stable percentiles (Efron 1979) |
| cross-validation | 5 × 50 | convention | repeated CV for the point estimate (Stone 1974), stratified by class in classification (Kohavi 1995); the dispersion between folds is never used for inference, with no unbiased estimator of the variance (Bengio & Grandvalet 2004); intervals from the person bootstrap (Efron 1979) |
| design partition | 70/30 | convention | declared options 60 and 75 |
| minimum n / out of the bag / valid resamples | 30 / 20 / max(20, 10 % of B) | decision of the framework | operational minima (a ridge with one predictor; a scorable resample; a non-degenerate interval) |

## 4. OUTPUTS contract

### 4.1 Tables (CSV UTF-8, `,` and `.`, full precision, deterministic ordering; **aggregates only**)
| file | one row per | columns |
|---|---|---|
| `algebra.csv` | method × stratum | `method_id, label, year, kind, form, stratum, n, n_nonpositive_pred, fit_r2, poor_monomial, e_<var>…, vector_source, out_of_validity_frac, provenance_confidence` |
| `sigma.csv` | stratum × pair of variables | `stratum, n, var_i, var_j, cov_log` |
| `pairs.csv` | pair × stratum | `a_id, b_id, stratum, n_pair, r_log_predicted, r_log_observed (Pearson in the logs; exact identity), rho_sp_observed, rho_sp_converted, identity` |
| `redundancy.csv` | method × stratum | `method_id, stratum, rho_sp_max, predecessor_id, predecessor_year, redundant, identity_of` |
| `sigma_transfer.csv` | source × destination | `sigma_from, observed_in, type, pairs, median_abs_err, p90_abs_err, max_abs_err, frac_within_tol, tol, own_median_abs_err, excess_median, median_abs_err_lo, median_abs_err_hi, excess_lo, excess_hi, boot_B` — the error in Pearson of the logs; `own` = the Σ of the stratum itself (exactly 0 for monomials, by the identity); `excess` = transferred − own, pair by pair; CI by a bootstrap of the PEOPLE of the observed stratum (`algebra.transfer_B`, seed `seeds.bootstrap`); `frac_within_tol` with the fixed tolerance `algebra.transfer_tol` (0.05), independent of n. The fraction "within Fisher's CI" and the Σ→Spearman conversion left the official outputs (v0.5; legacy only in the equivalence test, §5) |
| `audit.csv` | method × stratum × target | `method_id, stratum, target, control, task, metric, estimator, n, B, B_eff, B_dropped, score_cv_target, score_cv_control, score_oob_target_mean, score_oob_control_mean, disc_mean, disc_lo, disc_hi, p_disc, verdict` (conditional, v0.5), `verdict_marginal, score_oob_control_to_target, score_oob_idx_control_to_target, score_oob_target_to_control, score_oob_idx_target_to_control, s1_mean, s1_lo, s1_hi, p_s1, s2_mean, s2_lo, s2_hi, p_s2` |
| `utility.csv` | method × stratum × target | `…, covariates, score_base, score_with, delta_mean, delta_lo, delta_hi, p_delta, margin, useful` |
| `combinations.csv` | ordered pair × stratum × target | `host_id, added_id, r_log_predicted, score_host, score_pair, gain_mean, gain_lo, gain_hi, p_gain` |
| `sensitivity.csv` | as `audit.csv` | + `estimator_primary, verdict_primary, verdict_changed, s1_primary, s1_delta, s2_primary, s2_delta, disc_primary, disc_delta` |
| `threshold_sensitivity.csv` | method × stratum × target × margin × P | `verdict, verdict_default, changed` (reclassification, without refitting) |
| `screening.csv` | method × stratum | `method_id, stratum, redundant, specific, useful, identity, class`; `class` = {original\|redundant}-{specific\|tracks-control\|both\|no-signal}-{useful\|notuseful}, `identity`, or `inconclusive` ONLY when the audit gave no verdict (09-15: BOTH and NEITHER are conclusive; before they fell into inconclusive) |
| `implicit_vectors.csv` (v0.6) | stratum × role × name | `stratum, role (target/control), name, n, fit_r2, poor_projection, e_<var>…` |
| `geometry.csv` (v0.6) | method × stratum × target | `method_id, stratum, target, control, n, vector_source, cos_target, cos_control, cos_target_control, r_log_target_observed, r_log_target_identity, r_log_target_gap, r_log_control_observed, r_log_control_identity, r_log_control_gap, fit_r2_target, fit_r2_control, poor_projection, flag_parallel_to_control, flag_coupled_target_control, thresholds` |

**The primary verification of the algebra = Pearson in the logarithms**, predicted × observed: an algebraic identity,
with no distributional assumption (in the logs, a monomial is an exact linear combination; linearity is guaranteed by
construction). **Redundancy = observed Spearman** (of ranks, invariant to monotone transformations; it requires no
linearity). The Σ→Spearman conversion by (6/π)·asin(ρ/2) requires bivariate normality of the logs, rejected in NHANES
(Stage P), and **appears in no official output** since v0.5.

### 4.2 Manifest (`manifest.json`)
`package_version, catalog_version, catalog_sha256, config_sha256, config_resolved, preset, seeds_used,
resampling_scheme, versions {python, numpy, pandas, scipy, sklearn, matplotlib}, platform, threads, n_jobs,
started_at, finished_at, wall_seconds, input_sha256, input_rows, sep_used, decimal_used, encoding_used,
rows_dropped {…}, strata_used {…}, methods_evaluated, methods_skipped {id: reason}, warnings,
outputs_sha256 {…}, schema_version`.

### 4.3 Summary (`summary.md`)
The preset (a warning if `quick`); per stratum: n, methods, those redundant with a predecessor, specific / track the
control / inconclusive, useful; flags; the 10 pairs with the largest predicted×observed error; 3 decimal places only
here. The target↔control correlation per stratum, with a warning above 0.8 (a control nearly collinear with the target).

### 4.4 Figures (`figures/`, PNG 300 dpi + PDF; from the tables; a fixed seed in the jitter)
1 `compass` (arrows in the space of exponents) · 2 `predicted_observed` (Pearson in the logs; identities excluded) ·
3 `precedence_tree` · 4 `specificity_quadrant` (control score × target score; any metric) · 5 `screening_map`
(the signature) · 6 `sigma_transfer` · 7 `combination_gain`.
**Gate:** inspection of every figure by Thalles before v1.0 is closed.

### 4.6 Report (`report.html`, v0.8 — plan approved on 2026-09-14; v0.9 — structure and references, 2026-09-15)
- **It is the main output.** A single file, self-contained (figures and tables embedded), which opens from disk with no
  server. Terminal: the last line of `run` is the path of the report and how to open it. Notebook: `run()` shows the
  report inline.
- **Sections, in this order:** the header (title, preset, a warning if `quick`); the summary; for each result block —
  input and sample, redundancy and precedence, specificity (conditional control), utility, target↔control geometry, Σ
  transfer, sensitivity, screening — three fixed paragraphs **how it was computed · how to read it · rigor applied**,
  whose numbers (folds, repeats, B, margins, thresholds, seeds, estimator) come from the resolved configuration and from
  the manifest, never from fixed text; figures with captions; tables with **CSV** buttons (embedded in base64, works
  offline) and **Excel** (a `tables.xlsx` file beside it, one sheet per table, generated only if `openpyxl` is installed
  — extra `bioms-zaku[excel]`; without it, a warning and the CSV); the section **Rigor of this run** (preset, seeds,
  versions, hash of the input, hash of every output, time, warnings, the declaration of independence); the manifest.
- **The report recomputes nothing:** it reads the tables, the manifest and the configuration. One source of truth.
  Consequence: `bioms-zaku --lang xx render <folder>` (or `render(folder, lang)` in the API) re-writes the summary, the
  figures and the report of a finished run in another language, without touching the tables or the manifest (tested: the
  hashes of the tables unchanged). The WARNINGS recorded in the manifest are a record of the moment of the run and stay
  in the language of that run, even inside a re-rendered report.
- **Determinism:** `report.html` carries a date and time and does NOT enter `outputs_sha256`; the embedded CSVs are byte
  for byte the hashed files (tested). Out of scope: interactive charts, filters, switching language inside the page (the
  `render` command resolves the language).
- **Structure (v0.9, 2026-09-15).** Eight numbered sections, in this order, with a sticky table of contents at the top:
  1 About (text, citation, the attribution of the name, and the **Zaku diagram** — a fixed SVG of the method in four
  columns: measured variables → decomposition (exact example vectors H²/R, Xc/H, R/H; a schematic Σ; the identity
  r = aᵀΣb/√(aᵀΣa·bᵀΣb)) → out-of-sample audit → verdicts; also written to `figures/zaku_method.svg`, in the language of
  the run); 2 Key numbers (people, strata, methods and curated ones, the verdicts of the primary target as colored
  seals, added value k of n, target↔control coupling per stratum — all read from the tables, tested); 3 Summary in text
  (`summary.md`, folded); 4 Figures, grouped by family (the verdict card open; the others closed; one open at a time; a
  human translated title, the caption once per family, a click enlarges); 5 Results, one foldable block per result
  block, **one open at a time** (native `<details name>`, no library), with the method text and the tables (numerics
  right-aligned; at most 1000 rows shown, the embedded CSV is always complete); 6 Rigor; 7 References; 8 Manifest. The
  colors of the verdicts are identical to the figures. Printing opens every section (a print stylesheet + `beforeprint`).
  No external resource: CSS, JS and images embedded.
- **References (v0.9).** A fixed section, in three parts: (a) the bioimpedance methods evaluated IN THIS run, one line
  per source (catalog entries grouped by DOI; year and authors from the catalog, title and journal from the verified
  record); (b) the statistical and algebraic methods, a fixed list tagged with the block it supports — Kronmal 1993
  (indices that share components correlate by construction; only in the redundancy block) and Atchley 1976 (the induced
  correlation grows with the variability of the shared variable, the diagonal of Σ; dividing by size does not remove
  size, the reason utility is measured over the covariates; redundancy and utility blocks), Nevill & Holder 1995 (the
  log-linear fit of the exponents is the allometric model that provides the ratio standard appropriate to the target;
  design and redundancy blocks), Heymsfield 2007 (lean mass and fat scale with stature with powers ≈ 2, so targets of
  mass/stature² are independent of stature; the power is derived in the population, Benn's principle; design and utility
  blocks), Spearman 1904 (rank correlation: invariant to monotone transformations, insensitive to extremes; attenuation
  by measurement error as support for the 0.95), Lipsitch 2010 (negative control outcome: it shares with the target the
  sources of spurious association and is analyzed by the same procedure; by analogy — the conditional and reciprocal
  form S1/S2 and the quantitative rule are an extension of this tool), Hoerl & Kennard 1970 (ridge over standardized
  predictors, correlation form; α = 1 fixed and equal for every index, not tuned by design — the authors state there is
  no automatic choice of k; it acts only when index and control are nearly collinear), Stone 1974 (cross-validatory
  assessment, here in K parts, of a fixed prescription: nothing is chosen by the data in the audit, hence no nested
  validation; the choice of the designed exponents is made on a partition never used in the assessment), Bengio &
  Grandvalet 2004 (the errors of the K parts are dependent; no unbiased estimator of the variance; why the dispersion
  between folds never enters the inference), Efron 1979 (the bootstrap principle: resampling people from the empirical
  distribution, Monte Carlo with B replicates; it establishes neither the percentile interval nor out-of-bag scoring —
  percentile summaries are descriptive), Efron 1983 (ε₀: scoring on the people not drawn, out of the bag; only in paired
  differences, without .632), Kohavi 1995 (cross-validation stratified by class: less bias and variance; 10 folds is for
  model selection, which there is none of; the same blocks), Le Cessie & van Houwelingen 1992 (logistic with an L2
  penalty: finite and stable coefficients with few events or correlated predictors; a free intercept; a fixed penalty;
  choosing by classification error is unstable — hence no cut-off metrics; specificity and utility blocks), Peduzzi 1996
  (below 10 events per variable the logistic model is biased and unstable; EPV computed per model and marked, never a
  barrier; specificity and utility blocks), Tjur 2009 (the coefficient of discrimination D; classification gains in ΔD;
  specificity and utility blocks), Pencina 2008 (ΔAUROC insensitive; IDI = ΔD; a bootstrap to test; the same blocks),
  Hanley & McNeil 1982 (AUROC = the probability that a drawn case exceeds a drawn non-case = Wilcoxon, with no
  distributional hypothesis; the standard error depends on both classes; a paired comparison on the same people; the
  sentence only in classification; specificity and utility blocks), Cover 1974 (the best pair is not the pair of the two
  best, even without redundancy: the screening classes are per index, combinations are never inferred from them, pairs
  are judged only when audited as pairs); (c) the software executed (NumPy, SciPy, pandas, scikit-learn, Matplotlib).
  Rule: **no DOI enters without resolving on Crossref**; the records (`references.py`) were generated from Crossref
  metadata on 2026-09-15, not typed; entries are listed as published, without translation. In the verification two
  candidates were refused: the DOI 10.1097/ede.0b013e3181e4bfd7 (it is the erratum of Lipsitch 2010; the article is
  10.1097/ede.0b013e3181d61eeb) and 10.1111/sms.12780 (a paper on waist, not a general reference on allometry). Tested:
  every DOI of the catalog has a record; the erratum does not enter; the references of the report are exactly those of
  the methods of the run.

### 4.5 Progress
The CLI and the API print, per stratum and method, the count, the elapsed time and an estimated finish, from the first
method onwards.

**Justification.** Full precision allows equivalence at 1e-9. Pearson in the logs as the primary verification removes
the only assumption of the algebraic part. Publishing only aggregates is what allows running on data that cannot leave (a container at a partner institution). Figures from the tables guarantee agreement.

---

## 5. REPRODUCIBILITY contract
- **Determinism:** the same input + configuration + versions ⇒ the same `outputs_sha256`, for any `n_jobs`.
- **Autonomy:** every quality criterion runs from the repository alone. No test reads a file outside it; nothing is
  skipped for "missing data". The community runs the whole suite in ~2 min and sees the same result.
- **Known truths (what replaces any "the same as the pilot"):**
  1. the hand calculations of the notebook (`caderno/licoes_metodo_bioms_a_mao.md`): Var, Cov, Σ, aᵀΣa, aᵀΣb, ρ,
     out-of-sample R², bootstrap, conditional control — tolerance 1e-9;
  2. exact algebraic identities on random data (Pearson of the logs predicted by Σ = observed, 1e-12; invariances of
     scale and power);
  3. synthetic data with a constructed answer: a specific index × a size index, a combination gain only with new
     information, the design partition recovers the generating vector;
  4. **the bundled example with published parameters:** `examples/zaku_exemplo.csv` is reproducible byte for byte from
     `examples/zaku_exemplo_params.json`; on the shipped rows the identity ρ_log = aᵀΣb/√(aᵀΣa·bᵀΣb) is EXACT with the
     sample Σ (1e-12) — that is the gate. The PUBLISHED μ and Σ are recovered only within sampling error, and that
     error is large on this base: 400 people in four cells of 70 and 130, so the published Σ misses the observed
     correlation by up to 0.129 (measured 2026-09-20; on the 8000-row base retired that day the same deviation was
     < 0.02). Stated here because the corresponding test is a **smoke check, not a gate**: it refuses a Σ that is
     wrong, not a Σ that is subtly wrong;
  5. the numerical examples of the primary sources in the catalog (`check_example`), checked at load;
  6. determinism of the examples (equal hashes in two runs; checked by `tools/gate.py`, which runs the steps the
     continuous-integration workflow ran — the workflow was switched off on 2026-09-18, see
     `.github/workflows/ci.yml`).
- **The earlier engine (scripts of 2026-09-08/09) was a PILOT.** The paper is produced by the framework; the NHANES CSVs
  of 09-09 are the reference of nothing. The equivalence at 1e-9 verified on 09-10 was a transition gate, fulfilled and
  withdrawn on 09-14 (v0.5.2), together with the legacy function `sigma_transfer_table_legacy` and the `slow` marker.
- Presets: `quick` (5×5, B 200) for development and demonstration; `full` (5×50, B 2000) for reporting. On the bundled
  example the two give the same 28 verdicts (median |ΔS1| 0.0005).

**Justification.** A criterion that runs on one machine only is not a scientific criterion: nobody can contest it. Known
truths (a hand calculation, an identity, a published parameter) can be contested by any reader with a pencil. Simple and
fast is a condition for other researchers to use it and improve it.

---

## 6. Change log
From v1.0.0rc1 this document **has no version of its own**: it carries the package version, declared once in
`src/bioms_zaku/__init__.py` and written into `manifest.json` as `package_version`. Before that the contract was
versioned separately, and the earlier entries keep the document's historical numbers — they are a dated record and are
not rewritten. **Read with care:** from `v0.3` to `v1.0.0-rc1 (2026-09-15)` the numbers are the DOCUMENT's and do not
correspond to package versions; in particular the `v1.0.0-rc1` of 09-15 is the contract, not this release. From there
on the number is the package's, in the canonical PEP 440 form (`1.0.0rc1`, no hyphen), which also tells the two series
apart at a glance.

*This record was written in Portuguese until 2026-09-21 and translated into English on that date, when the contract
became a single English document (entry below). The translation changed no content, no date and no decision; it is the
same record in another language.*

This section records what changed in what the tool **promises**. [`CHANGELOG.md`](CHANGELOG.md) is a different record:
what changed for someone who **uses** the tool, per released version. Two records, two questions; the development path
itself is the git history.

- **v1.0.0rc1 (2026-09-21)** — **one language for the documentation: English (the user's decision).** The repository
  carried the same facts in up to eleven files — two contracts, four READMEs, four ten-minute guides and a
  documentation page in four languages — so a single change had to be written eleven times and one copy was bound to
  fall behind; on 09-20 removing three example data sets meant editing seven files to say the same thing seven times.
  Removed: `CONTRATOS.md` and the Spanish, Portuguese and Italian READMEs and guides. `CONTRACTS.md` stops being a
  declared translation and becomes THE contract, carrying section 6. **The four languages the researcher reads while
  USING the tool are untouched** — report, terminal messages, figures, the example notebook and the catalogue still
  speak English, Spanish, Portuguese and Italian, and they live in `i18n.py`, one fact per key with the four
  translations side by side, which is a design that cannot drift. What was removed was duplicated prose in separate
  files, not the tool's languages.

- **v1.0.0rc1 (2026-09-21)** — **the type of every target and every control is read from the data; `audit.task` was
  removed (the user's decision).** The key declared ONE task for the whole run and was applied to EVERY column,
  including a control of the other kind — which §3.2 permits. In practice: a class target with a continuous control,
  the key declared as `classification`, and the stratified cross-validation fell on the continuous column;
  `scikit-learn` stopped the run with `Supported target types are: ('binary', 'multiclass'). Got 'continuous' instead`,
  minutes after `check` had said "OK — ready to run". Found on 2026-09-20 through the API, in the round of tests of the
  three ways the tool is used; no test covered the key declared together with mixed types.

  **Why removed instead of repaired.** The key existed only to overrule a rule the tool already applies correctly on
  its own, and its one legitimate use — an integer score of few levels that the researcher wants treated as a number —
  is rare; whoever needs it exports the tables and analyses them elsewhere. `init` and `start` never wrote it, and it
  appeared in no README and no guide: only in this contract. Repairing it would have meant a new format, new validation
  and new documentation for a case almost nobody has.

  **Refusal instead of silence.** `resolve()` validates top-level keys only; everything under `audit` is merged without
  validation, so an old file would have been accepted and the declaration dropped in silence. The key is now refused
  with a message that says what is gone and where to see the type of each column.

  **Declared side effect.** The gate that skipped the scale sensitivity for classification read the run-level task; as
  the real value was always `auto`, it never closed, and it could only ever close because of this key. It was removed
  with it: no run changes behaviour, and §4 promises that block without exception when it is enabled.

  **Contradiction corrected.** §1 said a control is "of the same type as the paired target", while §3.2 permits mixed
  types and the code audits them. §1 now states the real rule, and the inference rule was written there in full — at
  most 10 distinct whole values = a class — because, without the key, it is unappealable and has to be predictable
  before a run. `check` already announces the type chosen for every target and every control.

- **v1.0.0rc1 (2026-09-20)** — **one example base, and only it (the user's decision).** The repository carried four
  bases; the installed package had carried only one since 09-19. Removed from the repository: the 8000-row synthetic
  example (`example_data.csv`, 677 KB) with its parameters, generator and the three YAML files that served only it
  (`example_quick`, `example_full`, `example_kg`); the REAL NHANES sample (`nhanes_diabetes_400.csv`, with its
  provenance and generator), whose subsection §1.4b was removed from this contract; and `bioms_mota_proposed.yaml`, the
  author's eight indices, which belong to another project. `zaku_exemplo.csv` stays, covering regression,
  classification with a known answer and diabetes. Declared reason: the synthetic base descends from NHANES through μ
  and Σ, and real data enters through the paper that cites the tool, not inside it. `minimal_data.csv`/`minimal.yaml`
  stopped being an example and moved to `tests/`, which is what they always were — the fixture of 13 test files and of
  steps 4 and 5 of `tools/gate.py`. The `examples` command lost `--all` and `--name`, which existed only for the
  technical files, and `datasets.py` lost the notion of a "main" and a "technical" example. **What lost discriminating
  power — a TEST, not the tool:** gate 4 of §5 moved from a base of 8000 rows to one of 400, and with it the check
  "the published Σ predicts the observed correlation" fell from < 0.02 to 0.129 — that is sampling error, not a defect,
  and the test now declares itself a smoke check rather than a gate; what remains a gate is the exact identity (1e-12),
  which does not depend on the size of the base. The sample-statistics test lost its vehicle (the author's eight
  indices) and now declares a minimal proposed catalogue inside the test itself, with the seven guarantees intact.
  Nothing in `src/` changed behaviour: the method, the verdicts, the thresholds and the guarantees are the same, and
  for whoever installs with `pip` this entry changes nothing.

- **v1.0.0rc1 (2026-09-16/19)** — *this entry said `v1.1.0-rc1`, the document's numbering running ahead of the
  package's; corrected on 2026-09-19 when the two lines became one.*

  **One version line (2026-09-19):** the contract, `CITATION.cff` and the package say the same number, so that a
  reviewer holding a `manifest.json` knows which contract produced that result. **The contract in English
  (2026-09-18):** `CONTRACTS.md` was a declared translation; `CONTRATOS.md` remained the original, written and reviewed
  in Portuguese, and prevailed. (Superseded on 2026-09-21: see the entry above.) **Continuous integration switched off
  (2026-09-18, the user's decision):** GitHub Actions is billed on a private repository; rigour moves to
  `tools/gate.py`, which repeats the CI steps on this machine — build, installing the wheel the way a user installs it
  in a clean environment, the whole suite, a repeated run with hash comparison, and an external user outside the
  repository. What only a matrix gives, other Python versions, is declared as not covered. **One example base
  (2026-09-17, the user's decision):** `zaku_exemplo.csv`, synthetic, drawn per cell sex × diabetes from NHANES means
  and covariances, serves regression, classification with a known answer and diabetes; the technical files stay in the
  repository and outside the installation. **Language of the source (2026-09-18):** docstrings and comments in English
  only; what the researcher reads stays in four languages. **Repeated id (2026-09-18):** §1.1 and §1.4 still described a
  "cluster mode" that the decision of 09-16 (§3.2) refuses; the rule is now stated once, pinned by a test.

  **Declared assumptions and thresholds with an origin (§3.6, 2026-09-16):** bootstrap interval on the pairs (Fisher
  removed), audit on the logarithmic scale with the raw scale as sensitivity, family level 1 − 0.05/k reported, the
  missing-value rule declared, bootstrap intervals for the designed exponents, an "Assumptions and thresholds" section
  in the report (4 languages), three records verified in Crossref for the anchors (Lafontant 2026, Yang 2023, Cohen
  1988). Efron 1983 added on 2026-09-16 after reading the original (citation audit). Property tests (coverage, scale,
  k = 1, determinism).

- **v1.0.0-rc1 (2026-09-15)** — §3.5 the guided path `start` (PLANO_v1.0_fluxo.md): five screens, navigation (`<`, `?`,
  summary, correct a line), suggestions without a verdict before acceptance, accept/edit/no, the researcher's own
  index, a final run on rows never seen; YAML written per screen and reproducible with `run`; `--map --yes`; Ctrl+C
  130. `init` stops asking about `design`. Rigour added by the user simulation: the audit never skips a method in
  silence; `check` blocks a design whose audit partition is below `min_n` per stratum; `propose` refuses a formula with
  no auditable value, a constant, or a catalogue id, and warns about repeating a published method; a second session on
  the same file reuses the answers and asks before discarding the researcher's own indices; an invalid yes/no answer is
  asked again. Shared design stage (`design_all`). Ten-minute guide.

- **v0.9.0 (2026-09-15)** — §4.6 report structure: fixed table of contents, eight numbered sections, key numbers,
  figures by family and result blocks as an accordion (one open at a time), the Zaku method diagram (fixed SVG, 4
  languages, also in `figures/`), a References section with records verified in Crossref (the run's methods +
  statistical methods + software), tables with aligned numerals, printing and enlarging figures without an external
  resource. Terminal welcome (`banner.py`): only on `bioms-zaku` with no command, on `--version` and at the start of
  the interactive `init`; never on `run`/`check`/`render`/`init --map`; colour only on a terminal (NO_COLOR, TERM=dumb
  respected). Test. Diagram margin guarantee: every text declares the box containing it; a conservative width estimate
  reduces the font and pins `textLength` when needed (unit test) and `tools/audit_diagram.py` measures each text in
  Chrome in 4 languages × 8 fonts. Report header in light grey, centred logo, gradient name, the titles "Data: <name>"
  and "Researcher: <name>"; `check` ends with the `run` command ready to paste. Study identity (`study.data_name`,
  `study.researcher`): asked in `init`, written into the YAML (therefore into the configuration's SHA-256) and into the
  manifest; it changes the configuration hash, never the tables.

- **Proposed indices (v0.9, approved 2026-09-15).** A `user_entries` entry with `provenance.formula_source: proposed`:
  the researcher's own index. It needs no DOI, year, validity or frequency (explicit defaults: current year, 50 kHz,
  null validity, high confidence because the formula is the author's own text, verifier = author, date = the run); it
  requires `id`, `authors`, `target`, `expr`. Never curated (an error if `curated: true`); never takes precedence over
  a published method, whatever the year (ordering key `(proposed, year, date, DOI)`); marked ◇ in tables
  (`algebra.proposed`), figures and captions, summary, key numbers and references ("index proposed by the researcher,
  not published"). It enters the audit only when listed in `catalog.include` (the list may contain `curated` = the
  curated ones ∪ ids); `check` warns when one is declared and not included. Form: `monomial` if `vector` is given
  (verified exact), otherwise `composite` (fitted vector + R²). Circularity: `expr` accepts only mapped variables.
  Tests. The command `bioms-zaku propose <yaml>` (§3, v0.9): adds the researcher's own indices one question at a time;
  every formula goes through the same validation as the catalogue and is evaluated on the YAML's data before being
  accepted (count of finite/positive values, min/median/max, sample statistics used); an invalid or repeated id and a
  refused formula are asked again; nothing is guessed. `--lang` on the CLI overrides the YAML's `language` in `check`
  and `run` by writing it into the configuration (the manifest records the language used).

- **Designing several indices and orthogonality (v0.9, approved 2026-09-15; see §2.7).** `design` accepts a list of
  blocks `{target, id, orthogonal_to?}`; ONE partition (the seed of the first block, rows with every target/control
  finite, stratified) serves every designed index, and they are audited on the same never-seen rows; manifest
  `design.indices[id].per_stratum` (keys = stratum labels) with the vector, the design R², and, if orthogonal, the
  control's vector, cos_Σ and the unconstrained R². Marked △ in tables (`algebra.designed`), figures, summary, key
  numbers and references; never precedence over a published method. **Theorem recorded and tested:** the OLS vector of
  the target, t̂, satisfies t̂ᵀΣ(ĉ − βt̂) = 0 with β = t̂ᵀΣĉ/t̂ᵀΣt̂ — the best predictor of the target is, by construction,
  conditionally uninformative about the projection of the control. Therefore the **simple design is the "clean" index**
  in the sense of the conditional negative control (S2 ≈ 0 out of sample in the constructed case, verdict SPECIFIC).
  `orthogonal_to` imposes cos_Σ = 0 **marginally** with one column (closed form:
  a = a_OLS − (ĉᵀΣa_OLS/ĉᵀΣĉ)·ĉ); it serves nuisances (body size), and conditioned on the target such an index tends to
  track that column (S2 rises in the constructed case) — the report says so. `init` asks
  `design: none | target | control | both` and writes simple designs; `orthogonal_to` only through the YAML. With
  `control` or `both`, `init` writes the pairing in both directions (the control becomes a target too): every method is
  audited in both senses and the index designed for the control is audited against its own target; the screening keeps
  the first target as primary.

- **v0.8.0 (2026-09-14)** — §4.6 the report as the product: method texts per block (4 languages, numbers from the
  configuration), CSV/Excel buttons, a rigour section, inline in the notebook; the logo moves inside the package.

- **v0.7.0 (2026-09-14)** — §3.4 language: a single catalogue in en/es/pt/it, `--lang` and `language:`; figures and
  captions in Italian.

- **v0.6.1 (2026-09-14)** — external user simulation in Colab: the catalogue moves INSIDE the package (a wheel install
  could not find it); CI installs the wheel (never editable) and runs an external-user step outside the repository,
  Python 3.10–3.13; `init` maps sex/age/circumferences (roles `sex`, `age`, `arm`, `waist`, `calf`; suggested, printed
  with their origin, `none` refuses) and writes `catalog.include: curated` in plain sight; `check` names every missing
  entry and how to map it, and says how many non-curated ones exist without running. Catalogue 1.4.0: the `curated`
  field + `curation_record` on the 8 that were read. A design mistake made and reverted the same day (§3.2).

- **v0.6.0 (2026-09-14, approved)** — §3.3 target↔control geometry: implicit vectors, cosines under Σ, the identity
  r_log = cos·√R², the flags `PARALLEL_TO_CONTROL` / `COUPLED_TARGET_CONTROL` / `poor_projection`, the tables
  `implicit_vectors.csv` and `geometry.csv`, markers on the figures; targets in kg as a documented option; kg columns
  in the example (derived). Motivation: external feedback about definitional coupling (lean + fat + bone = body mass;
  both /H²).

- **v0.5.2 (2026-09-14)** — the user's decision: the earlier engine was a PILOT; the framework depends on no local
  data. §5 rewritten around known truths; the equivalence tests against the local NHANES, the migration test and the
  pilot's catalogue fixture, the migration tool and `sigma_transfer_table_legacy` removed; the `slow` marker dropped.
  The example generator draws from the ROUNDED parameters (the published ones) and gains `--from-params`: the bundled
  CSV is reproducible byte for byte from the JSON; three known-truth tests over the example. The preset `article`
  renamed `full`; the examples renamed (`example_data`, `example_quick`, `example_full`, `minimal`).

- **v0.5.1 — quick × full verification (2026-09-13, synthetic example, 7 indices, 2 strata, 2 targets):** 28 identical
  verdicts; median |ΔS1| 0.0005 (max 0.0015); median width of the S1 interval 0.032 (quick) vs 0.033 (full); identical
  redundancy; identical utility. Conclusion: `quick` serves development and demonstration; `full` serves reporting, as
  the contract already said; the intervals from 200 resamples are already stable at this n (8 000).

- **v0.5.1 (2026-09-13)** — the sensitivity mode **implemented** (before, only declared):
  `audit.sensitivity.estimator` runs the second estimator on the same resamples and writes `sensitivity.csv` (primary
  and alternative S1/S2/verdict, deltas; it never selects); `nested_tuning` remains unimplemented and raises a warning.
  Threshold sensitivity (`threshold_sensitivity.csv`): reclassification of the recorded S1/S2 under the grid
  `verdict.sensitivity_margins` × `verdict.sensitivity_p` (default 0.02/0.03/0.05 × 0.90/0.95/0.99), with no refit; the
  summary lists the verdicts that change at some point of the grid. Both enter `summary.md`.

- **v0.5.0 (2026-09-13)** — the user's decisions: (1) **conditional negative control** (§3.2): S1/S2 with the control
  and the target as predictors on the same resamples; verdicts `SPECIFIC` · `TRACKS_CONTROL` · `BOTH` · `NEITHER`; the
  marginal rule preserved in `verdict_marginal`; the target × control map becomes S2 × S1 with a margin; the card shows
  S1 and S2. (2) **Σ transfer in an n-fair metric** (§4.1): own error × transferred error, pairwise excess, interval by
  person bootstrap, fraction within a fixed tolerance; the fraction inside the Fisher interval and the Σ→Spearman
  conversion leave the official outputs (legacy only in the equivalence test). (3) Convenience sample declared.
  (4) Index design and combinations remain capabilities, marked experimental until validated in use.

- **v0.4.7 (2026-09-11)** — official figures redefined (the user's decision): `lineage` (a family tree: root by year,
  redundant ones hanging with ρ, colour = verdict, declared type beside the root), `target_control` (the negative
  control map: score on the control × score on the target, diagonal, interval bar), `exponents` (matrix grouped by
  lineage + declared type/R² + the stratum's Σ), `scorecard`. `predicted_observed` becomes supplementary. Default
  palette = the logo's colours (green specific, violet control); `classic` = blue/orange. Column `target_kind` in
  `algebra.csv`.

- **v0.4.6 (2026-09-11)** — `target_kind` in the catalogue and `declarations.target_kinds` in the configuration: an
  orientation warning when an index declared for one kind (e.g. fat) is audited against a target of another kind (e.g.
  lean mass); catalogue 1.2.x with `derivation_sample` separated from `validity` (v1.2.0), PhA/LMI re-verified, Piccoli
  as BIVA components, Rsp/Xcsp on the published scale (Ω·cm, L = 1.1·H).

- **v0.4.5 (2026-09-11)** — catalogue 1.1.0 (curation by primary source): the vector exactness rule (§2.3; PhA and Z
  forbidden in `vector`; `vector_tol` ≤ 1e-4); PhA (Baumgartner 1988) and LMI (Levi Micheli 2022) become `composite`
  with a fitted vector and R²; the entry `Hoffer1969_H2Z` (H²/|Z| at 100 kHz, primary source read, the numerical
  example of Table 1) as the antecedent of Lukaski 1985; `Z100` among the extra variables; `history` in the catalogue;
  a migration test against a frozen fixture.

- **v0.4.4 (2026-09-10)** — user experience: `bioms-zaku init` (builds the YAML from the CSV; suggests columns by name
  only when there is no ambiguity and requires confirmation; never guesses in silence) and `bioms-zaku check`
  (validates data + configuration without running: rows, strata, classes, pairing, target↔control collinearity,
  evaluable/skipped methods, bootstrap feasibility, the design partition, the circularity declaration; a non-zero exit
  code blocks). The block `declarations.targets_independent_of_variables` is required to be `true` for `design`.

- **v0.4.3 (2026-09-10)** — input rule (§1.3): **the target cannot be computed from any mapped variable**
  (circularity). The negative control detects confounding, not circularity; the responsibility is the researcher's and
  the declaration goes into the manifest (`targets_independent_of_variables: true`, a required field in the YAML when
  there is a `design`). The case that motivated it: the NHANES estimated VO2max is computed by the CDC from the stage
  heart rates; the recovery heart rate correlates 0.92 with the stage-2 heart rate and produced a "specific" index by
  circularity; with the warm-up heart rate (0.39) the index goes back to "tracks the control".

- **v0.4.2 (2026-09-10)** — decision: the framework has **three official figures** (the exponent map; predicted ×
  observed; the verdict board). Precedence bands, Σ transfer, combination gain and the compass are supplementary,
  generated only with `output.supplementary_figures: true`.

- **v0.4.1 (2026-09-10)** — catalogue: the `status` field (`active` | `excluded` with a required `exclusion_reason`; an
  excluded entry is never evaluated and leaves in `methods_skipped`); `strata` has a single source (the top of the
  configuration; a conflict with `columns.strata` → error); figures revised after inspection (§4.4): the verdict board
  (`board`, the signature figure) replaces the quadrant and the map; the exponent heatmap replaces the compass above 10
  methods; the precedence tree in bands by lineage, with no randomness; validated palette (2 colours: blue specific,
  orange tracks-control; grey = de-emphasis; identity = shape/label; non-curated (§2.1) = hollow marker / *).

- **v0.4 (2026-09-10)** — §2.7 index design with a mandatory partition (70:30 holdout by default, `by_stratum`
  optional), the final refit labelled, a warning for n<100, a `designed` entry in the run's catalogue.

- **v0.3.2 (2026-09-10)** — no imputation by default (the user's decision): complete case per method; utility and
  combination on the complete case over the union of the columns; `max_missing_frac_warn` in the summary; `impute` only
  when explicit. On the NHANES reference the imputer never acted (rows without an index were removed before the model),
  so the equivalence does not change.

- **v0.3.1 (2026-09-10)** — §5: separate tolerances for rank statistics (1e-6) and counts (±1 pair), with the cause
  verified; `form` ∈ {monomial, composite, closed} (the old "affine" is a case of composite; the specific BIVA is
  neither a sum nor a product and receives the same log-linear fit); `doi` may be `null` only with a `pmid` (works
  without a DOI); `frequency_khz` accepts a list (multifrequency).

- **v0.3** — simplification (the user's decisions): the outcome is the researcher's; Xc required; the frequency
  declared and minimal, several allowed; out: the reference criterion/DXA, pre-computed values, segmental variables,
  sampling weights, Excel. Two default estimators per role (alone: Ridge/logistic; combination: HistGradientBoosting
  fixed; XGBoost optional); Optuna only in nested sensitivity; multiclass (AUROC OvR macro + balanced accuracy); CV
  stratified in classification; descriptive verdicts + optional BH; **Pearson of the logs as the primary check**
  (exact) and Spearman as redundancy (non-parametric); progress required; only aggregates in the outputs;
  `extra_log_variables` for age; target↔control diagnosis in the summary.

- v0.2 — rigour review (CV by id, deterministic separator, units, pairing, numerical validation of `vector`,
  `check_example`, shared resamples, threads=1, full precision, hashes, 31 entries).

- v0.1 — first version.

## 7. Approval
Thalles reads, marks disagreements, answers "approved" or gives a list of changes. Only then does stage 2 begin.

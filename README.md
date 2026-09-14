<p align="center"><img src="docs/assets/logo.svg" alt="BioMS Zaku" width="360"></p>

# BioMS Zaku

**EN** — Algebraic decomposition and predictive audit of indices and predictive equations. Demonstrated on bioimpedance.
**ES** — Descomposición algebraica y auditoría predictiva de índices y ecuaciones predictivas. Demostrado en bioimpedancia.
**PT** — Decomposição algébrica e auditoria preditiva de índices e equações preditivas. Demonstrado em bioimpedância.

*zaku* is a verb of the Juruna (Yudjá) language, Tupi family, Xingu, Mato Grosso, Brazil: "to see / to care for / to wait"
(Lima, S. *A estrutura argumental dos verbos na língua Juruna (Yudjá)*, MSc dissertation, USP, 2008, item 290).
The method looks at an index before accepting it, cares for its validity, and waits for the out-of-sample result.

Status: pre-alpha · License: MIT · Contracts: `CONTRATOS.md` · Plan: `PROJETO.md` · Cite: `CITATION.cff`

## What it does / Qué hace / O que faz

1. **Decomposition.** Every index or equation is written as a product of powers of the measured variables and represented
   by its **vector of exponents**. The covariance matrix Σ of the log-variables in a population predicts the Pearson
   correlation of the logs between any two indices *before either is computed*: aᵀΣb / √(aᵀΣa · bᵀΣb), an identity that
   holds for any distribution. Observed redundancy is measured with Spearman's rank correlation (threshold 0.95) and the
   earlier publication keeps precedence. Indices that are not exact products get a fitted vector with its fit R².
2. **Conditional negative control (contract v0.5).** The researcher declares a target and a negative control. On identical
   out-of-bag resamples the framework fits the control as a predictor of the target with and without the index (gain S1),
   and the target as a predictor of the control with and without the index (gain S2). Verdicts: *specific* (S1 present,
   S2 absent), *tracks the control* (the reverse), *measures both*, *no signal*; a gain is present when its mean exceeds
   0.03, its 95 % interval excludes 0 and P(d > 0) ≥ 0.95. Plus **added value** over basic covariates.
3. **Transfer of Σ.** The Σ of one stratum applied to another, reported as own error vs transferred error, pair-wise
   excess with a person bootstrap, and the fraction of pairs within a fixed tolerance (none of it depends on n).
4. **Design (experimental).** A new index is fitted on a design partition and audited on a disjoint one; requires the
   declaration that the target is not computed from the mapped variables.

Outputs are aggregate tables (full precision), a manifest (hashes, versions, seeds), a summary, four figures
(`lineage` family tree, `target_control` paired bars, `exponents` + Σ, `scorecard`) and a single-file `report.html`.
Row-level data never leave the run. Figures accept `figures: {title, subtitle, language: en|es|pt, palette, captions}`.
How to read each figure: `docs/index.html`, section 3.

## Install / Instalar

```bash
pip install bioms-zaku            # after the first release; until then:
pip install -e ".[plots,dev]"     # from a clone of this repository
```

Python ≥ 3.10. Dependencies: numpy, pandas, scipy, scikit-learn, pyyaml (+ matplotlib for figures).

## Example data / Datos de ejemplo / Dados de exemplo

`examples/example_data.csv` — 8 000 **synthetic** rows (4 000 per sex). They are draws from a multivariate log-normal
whose mean vector and log-covariance Σ were estimated, per sex, from a **convenience sample** of NHANES 1999–2004 (adults
18–49 y, measured DXA, 50 kHz BIA; n = 2 792 women, 3 036 men). No real row is reproduced; only μ and Σ left the source, and
they are published in `examples/example_data_params.json` (with the skew and kurtosis of the source logs, so the
log-normal approximation can be judged) together with the generator `tools/make_example_data.py` and its seed. The
file carries R, Xc, height, weight, age, three circumferences, DXA lean/appendicular/fat indices and one declared
synthetic binary label. Use it to learn the method, to test the tool, and to decompose Σ by hand.

```bash
bioms-zaku run examples/example_quick.yaml      # 7 curated indices, preset quick, ~20 s
bioms-zaku run examples/example_full.yaml       # same data, preset full (5×50 CV, B = 2000), for reporting
bioms-zaku run examples/minimal.yaml            # 150 rows, the smallest possible run
ls zaku_out/example_quick                       # algebra sigma pairs redundancy sigma_transfer audit utility combinations screening sensitivity threshold_sensitivity (.csv) manifest.json summary.md report.html figures/
```

The file also carries `lean_kg`, `alm_kg`, `fat_kg` (index × height², derived, no new draw) so that absolute masses can be
used as targets: `bioms-zaku run examples/example_kg.yaml`. See *Geometry* below before choosing.

Your own data — three commands / tres comandos / três comandos:

```bash
bioms-zaku init my_data.csv          # asks which column is R, Xc, H, W, target, control, and optionally sex, age, arm/waist/calf (suggests, never guesses) → my_data.zaku.yaml
bioms-zaku check my_data.zaku.yaml   # validates data + configuration WITHOUT running: rows, classes, methods, bootstrap, circularity
bioms-zaku run   my_data.zaku.yaml   # the analysis
```

Non-interactive `init`: `bioms-zaku init my_data.csv --map R=resistance Xc=reactance H=height W=weight target=lmi control=fmi independent=yes`,
optionally adding `strata=sex id=subject age=age arm=arm_c waist=waist_c calf=calf_c` so that the catalogue equations that need
sex, age or circumferences can be evaluated; `check` lists every method it cannot evaluate and which column it needs.
The YAML maps columns to roles (see `CONTRATOS.md` §1): `variables` (R, Xc, H, W at the declared frequency), `units`,
`targets`, `controls`, optional `covariates`, `strata`, `groups`, `id`, and `declarations.targets_independent_of_variables`
(true only if no target/control is computed from the mapped variables — the circularity rule).

```yaml
run_name: my_study
data:
  path: my_data.csv
  columns:
    variables: {R: resistance_ohm, Xc: reactance_ohm, H: height_cm, W: weight_kg}
    units: {H: cm, W: kg}
    targets:  {LMI: lean_mass_index}
    controls: {FMI: fat_mass_index}
    covariates: [weight_kg, height_cm]
strata: sex
preset: full             # 5×50 CV, B = 2000 (quick = 5×5, B = 200, for demos only)
```

## Rules the code enforces / Reglas / Regras

- everything out of sample; every contrast paired on identical resamples; resampling is a deterministic function of
  (rows, seed, B, min_oob) — `n_jobs` never changes a number;
- no imputation by default (complete case per method; union complete-case for paired contrasts);
- estimator declared before the data (Ridge / logistic for single indices; boosting for combinations); no selection by result;
- catalog expressions parsed by a whitelist AST (no `eval`); catalog vectors validated numerically; published numeric
  examples checked at load; methods with invalid transcriptions carry `status: excluded` and are never evaluated;
- verdicts are descriptive (bootstrap P is not a p-value); thresholds fixed in the contracts;
- outputs never contain row-level data (safe to run inside a partner's environment).

## Catalog / Catálogo

Eight public bioimpedance indices, each re-verified on its primary source (`catalogo/fontes_primarias_indices/LEITURAS.md`):
H²/|Z| at 100 kHz (Hoffer 1969), impedance index H²/R (Lukaski 1985), whole-body phase angle (Baumgartner 1988), the BIVA
components R/H and Xc/H (Piccoli 1994), specific resistivity and reactivity Rsp/Xcsp (Marini 2013; validated on NHANES by
Buffa 2013) and LMI (Levi Micheli 2022); the impedance ratio Z200/Z5 is listed with low confidence (commercial origin, no
derivation paper). Each entry records the derivation sample separately from the author-stated validity (outside it the
framework flags †, never blocks), the declared kind of target (`target_kind`: a fat-mass index audited against a lean-mass
target gets an orientation warning), and every curation event in the catalog `history`. Phase angle and LMI contain atan
and are therefore `composite`: their exponent vector is fitted per stratum and the fit R² is reported (exactness rule,
`CONTRATOS.md` §2.3). **Only curated entries are audited by default** (`catalog.include: curated`, the value `init` writes): the
eight whose primary source was critically read (`curated: true`, with `curation_record`). The predictive equations stay in the
catalog without curation and are audited only with `catalog.include: all`, marked * in every output.

## Geometry of target and control / Geometría / Geometria (v0.6)

Target and control often come from the same reference measurement and the same normalisation (lean/H² and fat/H² from one
DXA scan; lean + fat + bone = weight, with H and W among the mapped variables). In the space of the mapped variables they
can point almost the same way, and then an index close to that direction (W/H²-like) predicts both by arithmetic. The
framework measures this with the algebra it already uses: the *implicit vector* of each target and control (OLS of the
logs), the Σ-cosines index–target, index–control and target–control, and the exact identity r_log = cos_Σ·√R² for
monomial indices. Two flags with declared thresholds annotate the verdicts and never change them: PARALLEL_TO_CONTROL
(‡ next to the index) and COUPLED_TARGET_CONTROL (‡ in the panel title). Tables `implicit_vectors.csv` and
`geometry.csv`; block in `summary.md`. On the shipped example the target–control cosine is 0.90 (women) and 0.86 (men)
for LMI vs FMI. Using absolute masses (kg) removes height from both sides and lowers the coupling but does not remove the
coupling through weight, and it makes the target more "size", which favours volume indices (H²/R): a declared choice,
not a fix. Lesson 12 of the notebook works the whole thing by hand on four people.

## Reproducibility / Reproducibilidad / Reprodutibilidade

`manifest.json` records the resolved configuration, seeds, package/library versions, input hash and the SHA-256 of every
output. Two identical runs give identical hashes (tested in CI). Every quality check runs from the repository alone:
hand-calculated lessons, exact algebraic identities, synthetic cases with a constructed answer, and the shipped example,
which is reproducible byte for byte from its published parameters (`tools/make_example_data.py --from-params`). No test
depends on data outside the repository.

## Development / Desarrollo / Desenvolvimento

```bash
pytest -q                   # whole suite, ~2 min, self-contained
python -m build && twine check dist/*
```

A pre-commit hook refuses commits when the fast suite fails.

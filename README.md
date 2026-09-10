# BioMS Zaku

**EN** — Algebraic decomposition and predictive audit of indices and predictive equations. Demonstrated on bioimpedance.
**ES** — Descomposición algebraica y auditoría predictiva de índices y ecuaciones predictivas. Demostrado en bioimpedancia.
**PT** — Decomposição algébrica e auditoria preditiva de índices e equações preditivas. Demonstrado em bioimpedância.

*zaku* is a verb of the Juruna (Yudjá) language, Tupi family, Xingu, Mato Grosso, Brazil: "to see / to care for / to wait"
(Lima, S. *A estrutura argumental dos verbos na língua Juruna (Yudjá)*, MSc dissertation, USP, 2008, item 290).
The method looks at an index before accepting it, cares for its validity, and waits for the out-of-sample result.

Status: pre-alpha · License: MIT · Contracts: `CONTRATOS.md` · Plan: `PROJETO.md` · Cite: `CITATION.cff`

## What it does / Qué hace / O que faz

1. **Algebraic part.** Every index or equation is written as a product of powers of the measured variables and represented
   by its **vector of exponents**. The covariance matrix Σ of the log-variables in a population predicts the correlation
   between any two indices *before either is computed* — an exact identity for the Pearson correlation of the logs.
   This reveals **redundancy** (with publication precedence) and shows how it depends on the population (Σ transfer).
2. **Predictive part.** Each index is audited out of sample against a **target** and a **negative control** with a paired
   bootstrap (same resamples on both sides): *specific* if it predicts the target and not the control; *measures the
   control* if the opposite; plus **added value** over covariates and **gain** from combining indices.
3. **Design.** A new index for a context (e.g. VO₂max) is fitted on a design partition and audited on a disjoint one.

Outputs are aggregate tables (full precision), a manifest (hashes, versions, seeds), a summary, and three figures:
`exponents`, `predicted_observed`, `board`. Row-level data never leave the run.

## Install / Instalar

```bash
pip install bioms-zaku            # after the first release; until then:
pip install -e ".[plots,dev]"     # from a clone of this repository
```

Python ≥ 3.10. Dependencies: numpy, pandas, scipy, scikit-learn, pyyaml (+ matplotlib for figures).

## Five-line example / Ejemplo / Exemplo

```bash
bioms-zaku run examples/minimo.yaml      # 150 synthetic rows, preset quick, ~15 s
ls zaku_out/minimo                        # algebra.csv pairs.csv redundancy.csv audit.csv utility.csv screening.csv manifest.json summary.md figures/
```

Your own data — three commands / tres comandos / três comandos:

```bash
bioms-zaku init my_data.csv          # asks which column is R, Xc, H, W, target, control… (suggests, never guesses) → my_data.zaku.yaml
bioms-zaku check my_data.zaku.yaml   # validates data + configuration WITHOUT running: rows, classes, methods, bootstrap, circularity
bioms-zaku run   my_data.zaku.yaml   # the analysis
```

Non-interactive `init`: `bioms-zaku init my_data.csv --map R=resistance Xc=reactance H=height W=weight target=lmi control=fmi independent=yes`.
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
preset: article          # 5×50 CV, B = 2000 (quick = 5×5, B = 200, for demos only)
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

31 published bioimpedance methods (indices and equations) with DOI, provenance and confidence level, in
`data/catalog_v1.json`. Curation is ongoing and entry by entry; contributions require DOI, formula source, a published
numeric example and review (`CONTRATOS.md` §2). Multi-frequency methods need the corresponding variables mapped.

## Reproducibility / Reproducibilidad / Reprodutibilidade

`manifest.json` records the resolved configuration, seeds, package/library versions, input hash and the SHA-256 of every
output. Two identical runs give identical hashes (tested in CI). Equivalence tests against the previous analysis engine
(NHANES 1999–2004) are marked `slow` and run locally: `pytest -m slow`.

## Development / Desarrollo / Desenvolvimento

```bash
pytest -q -m "not slow"     # fast suite (~2 min)
pytest -q -m slow           # equivalence with the previous engine (needs local reference data)
python -m build && twine check dist/*
```

A pre-commit hook refuses commits when the fast suite fails.

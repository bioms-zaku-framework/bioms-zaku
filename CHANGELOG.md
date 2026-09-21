# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning
2.0.0](https://semver.org/spec/v2.0.0.html), written in the canonical PEP 440 form (`1.0.0rc1`, no hyphen).

**What belongs here:** what changed for someone who *uses* the tool — a number that can come out different, an
interface that moved, a dependency that matters. The dated record of changes to what the tool *promises* is section 6
of [`CONTRACTS.md`](CONTRACTS.md), the normative document. The development path itself is the git history, and stays
there: this file is not a diary.

## 1.0.0rc1 — unreleased

First release candidate. Nothing before it was published, so there is no earlier version to compare against; what
follows describes what the tool does, once.

### The audit
- Out-of-sample predictive audit of bioimpedance indices: paired out-of-bag bootstrap (B = 2000 in the `full` preset)
  and repeated stratified cross-validation (5 × 50), on a 70/30 partition, per stratum.
- **Conditional negative control.** The control enters as a predictor: S1 is the gain for the target beyond the
  control, S2 the gain for the control beyond the target. Verdicts `SPECIFIC`, `TRACKS_CONTROL`, `BOTH`, `NEITHER`,
  with a declared margin of 0.03. For a class target the gain is Tjur's coefficient of discrimination.
- **Redundancy** between methods at ρ ≥ 0.95, with precedence for the published antecedent, and Σ transfer measured
  in an n-fair metric.
- **Geometry.** Exponent vectors of every method, Σ-cosines index–target, index–control and target–control, and the
  exact identity r_log = cos_Σ·√R² for monomial indices. The flags `PARALLEL_TO_CONTROL` and `COUPLED_TARGET_CONTROL`
  annotate a result; they never change a verdict.
- **Index design** for a context, fitted on a mandatory design partition and audited on rows it never saw.
- Assumptions and thresholds are declared in the report, each with its value, origin and support; a method is refused
  when fewer than max(20, 10 % of B) resamples are valid, so no interval is ever reported at zero width.

### The catalogue
- 32 published methods. Eight are **curated**: their primary source was read in the original, and each carries a
  `curation_record` pointing at the section of [`docs/LEITURAS.md`](docs/LEITURAS.md) that records the reading. Only
  curated methods are audited by default; `all` is an explicit choice.
- A researcher's own formula enters as a **proposed** index — marked ◇, never curated, never taking precedence over a
  published method.

### What you run
- `bioms-zaku start data.csv` is one guided path through the three uses; `run` repeats a saved analysis without
  questions, `render` rewrites a finished run in another language without recomputing, `check` inspects a
  configuration before it costs anything, `propose` adds own indices, `examples` copies the example data.
- A Python API on `bioms_zaku.api`, and an example notebook that runs in Jupyter and in Colab.
- The report is the product: one HTML file, eight numbered sections, figures, every table downloadable inside it,
  optionally an `.xlsx` (extra `[excel]`).
- English, Spanish, Portuguese and Italian, everywhere a researcher reads. Machine-readable names — CSV columns, YAML
  keys, verdicts, flags — stay in English.

### Reproducibility
- The same input, configuration and versions give the same `outputs_sha256`, for any `n_jobs`.
- `manifest.json` records the hashes, `package_version`, `catalog_version` and `schema_version`, so a result can be
  traced back to the code and the contract that produced it.
- A finished run is never overwritten; a second run of the same name becomes `name_2`.
- The whole quality gate runs from the repository alone (`tools/gate.py`): build, install of the wheel the way a user
  installs it in a clean environment, the full suite, a repeated run compared by hash, and an external user outside
  the repository.

### Not covered
- What v1.0 deliberately leaves out is listed in section 0 of [`CONTRACTS.md`](CONTRACTS.md), as a decision of scope.
- The package declares Python ≥ 3.10, but the local gate verifies only the interpreter it runs on (3.11). Other
  versions need a matrix, which needs continuous integration.

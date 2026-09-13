# Changelog

## 0.1.0.dev0 — 2026-09-10 (unreleased)
- Sensitivity implemented (2026-09-13, contract v0.5.1): estimator sensitivity on identical resamples (`sensitivity.csv`),
  threshold sensitivity by reclassification over a margin × P grid (`threshold_sensitivity.csv`), both summarised in
  `summary.md`. Documentation page rewritten as tool documentation (reading guide per figure); figures without in-figure
  legends by default (`figures.captions`), width capped; example dataset `examples/nhanes_sintetico.csv` (synthetic,
  parameters published). Quick vs article presets agree on all 28 verdicts of the example (median |ΔS1| 0.0005).
- Conditional negative control (2026-09-13, contract v0.5): the control enters as a predictor; S1 = gain for the target
  beyond the control, S2 = gain for the control beyond the target; verdicts SPECIFIC / TRACKS_CONTROL / BOTH / NEITHER;
  the marginal rule stays as `verdict_marginal`. Σ transfer in an n-fair metric (own vs transferred error, excess with a
  person bootstrap, fixed tolerance); Spearman conversion and Fisher-CI fraction removed from official outputs.
- Figures redefined (2026-09-11): lineage tree, negative-control map, exponents + Σ, scorecard as the official set; logo palette by default; `target_kind` in algebra.csv with an orientation warning.
- Catalog 1.1.0 (2026-09-11): exactness rule for monomial vectors (PhA and Z never in `vector`; PhA and LMI are now
  composite with fitted vectors and fit R²); Hoffer 1969 H²/|Z| (100 kHz) added from the primary source as the
  antecedent of Lukaski 1985; `history` field; migration test against a frozen snapshot.
- Framework end to end: input contract, catalog (31 methods migrated, validated at load), safe expression parser, algebra
  (exponent vectors, Σ, exact prediction, redundancy with precedence, Σ transfer), audit (paired OOB bootstrap, repeated
  CV, negative control, utility, combination gain, multiclass), index design with mandatory partition, report
  (tables, manifest, summary), CLI, three official figures + supplementary, trilingual captions.
- Equivalence with the previous analysis engine (NHANES 2026-09-09): fitted exponents/R² and audit contrasts at 1e-9;
  rank statistics at 1e-6 (documented cause).

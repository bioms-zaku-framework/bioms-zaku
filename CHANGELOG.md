# Changelog

## 0.1.0.dev0 — 2026-09-10 (unreleased)
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

# BioMS Zaku in ten minutes

**English** · [Español](GUIDE_10_MINUTES.es.md) · [Português](GUIDE_10_MINUTES.pt.md) · [Italiano](GUIDE_10_MINUTES.it.md)

You have a spreadsheet with bioimpedance (R and Xc at 50 kHz), stature, body mass and a reference measurement, such as lean or
fat mass by DXA. You want to know how the published indices behave on your data, and perhaps to build your own. Everything is
done in a terminal, with one command that leads you through questions. Nothing is decided in silence: every answer is written to
a YAML file, and the same analysis can be repeated without questions.

## 1. Install (once)

```
pip install "bioms-zaku[plots,excel]"
bioms-zaku --lang en
```

The second line prints the banner and the three commands. If it appeared, it is installed.

## 2. Prepare the spreadsheet

A `.csv` file with one row per person and numeric columns for R, Xc, stature, body mass and the reference. Separator and decimal
mark are detected. Column names are free; Zaku suggests the mapping and you confirm it.

## 3. Run

```
bioms-zaku --lang en start data.csv
```

At any question: **Enter** accepts the suggestion between [brackets], **`<`** goes back to the previous question, **`?`** repeats
the help, **`none`** refuses a suggested column. At the end of each screen a numbered summary appears, with "correct any line?".

What it asks, in order:

1. **language, name of the data, researcher** — they go into the report header and into the record of the run;
2. **the columns** — R, Xc, H, W and their units; the **target** (what the indices should predict, measured by an independent
   method); the **negative control** (what they should NOT predict, for instance fat mass when the target is lean mass);
   covariates (body mass and stature, suggested); stratum (sex) and labels (`0=F,1=M`); identifier; optional columns for sex, age
   and circumferences for the methods that use them; and the declaration that target and control were **not computed** from
   R, Xc, H, W;
3. **standard run** — `check` verifies everything and Zaku runs. The last line says where the report is and how to open it.

If that is all you need, you can stop here. This is the **standard use**.

4. **"would you like suggestions of designed indices?"** — if you say `yes`, Zaku fits one index to the target and one to the
   control, per stratum, using 70 % of the rows, and shows each one: formula, R² on those rows, the closest published index, a
   suggested name. You answer `yes`, `edit` (change the name, round the exponents) or `no`. No verdict appears before you decide,
   on purpose. An exponent changed by hand becomes a **proposed** index (◇), not a designed one (△).
5. **"do you have an index of your own to test?"** — type the formula in R, Xc, H, W (`H_m` stature in meters, `PhA` phase angle
   in degrees, `mean(PhA)` sample mean). It is checked at once on your data: how many finite and positive values, minimum,
   median, maximum; if it is constant, has no auditable value or equals a published method, you learn that before accepting it.
6. **final run** — only if something was accepted or proposed: published + accepted + yours, validated on the 30 % of rows the
   design never saw.

## 4. Read the report

Open `report.html` in the browser (the command is on the last line of the terminal). Reading order:

- **Key numbers**: people audited, methods, verdicts as colored seals, how many add value, whether target and control are
  coupled in your data.
- **Verdict card** (one per stratum): each method in three columns — original or repeats an earlier method; specific, tracks the
  control, measures both or no signal; adds value beyond body mass and stature or not. ◇ = yours; △ = designed.
- **Assumptions and thresholds**: each procedure with the assumption it carries and its state in this run; each threshold with
  its value, origin and support. This is where a reviewer checks that nothing was improvised.
- **References**: the sources of the methods evaluated and of the statistical methods, with DOI.

Reading rules that always hold: every number describes **this** sample; an index "repeats" another only in this sample and for
this target; "useful" means it went beyond body mass and stature alone.

## 5. Repeat, change language, another data set

```
bioms-zaku run data.zaku.yaml               # the same analysis, without questions, tables identical byte for byte
bioms-zaku --lang pt render zaku_out/data   # the same report in another language, without recomputing
bioms-zaku propose other.zaku.yaml          # type an index (for instance, a vector designed here) to validate on another data set
```

To validate an index designed on another data set, copy the vector shown in the summary (for example `R −0.49, Xc +0.11,
H +1.27, W +0.42`) and type it into `propose` as `R**(-0.49) * Xc**(0.11) * H**(1.27) * W**(0.42)`.

## 6. When something goes wrong

- **"not in the file"**: a column name with a typo; the question is asked again with the list.
- **"the control is the target itself"**: control and target must be different measurements.
- **"would leave ≈ N rows to audit, below data.min_n"**: too few people per stratum to design indices; use more rows or run
  without strata. The standard run is not affected.
- **"the inputs [...] are missing"**: a catalog method needs a column you do not have (for instance |Z| at 100 kHz); it is
  skipped and the report says so.
- **Ctrl+C** stops without writing anything further.

## 7. Three real cases, and what each one taught (2026-09-15)

- **NHANES sample, 300 people, target lean mass by DXA.** Lukaski and R/H specific in both sexes; Rsp and Xcsp track the control
  (they are fat indices, and the report says so). Lesson: to **design** indices per sex you need some 185 people per stratum;
  with fewer, `start` blocks the suggestions before showing them, because the audit would have no valid bootstrap.
- **CrossFit, 107 men, target fat by skinfolds, control corrected arm circumference.** Rsp was the only one specific for fat,
  exactly what its authors designed. The indices designed on NHANES for fat became "measures both" in athletes: where the extra
  mass is muscle, an index close to W²/H² reads muscle. Lesson: transfer between populations is read through the geometry (the
  cosine with the control) before any verdict.
- **Track and field, 61 athletes, target jump height, control sprint time.** Everything "no signal", and the reason showed up in
  one number: the cosine between target and control was −0.98. Jump and sprint are the same direction in the space of BIA.
  Lesson: the negative control must be a construct **different** from the target; another performance measurement does not
  serve. The phase angle added the most over body mass and stature (+0.38), with a wide interval.

## Example data, and results that are never overwritten

Zaku ships **one** example base, synthetic, which serves every use:

```bash
bioms-zaku examples --copy     # copies to ./zaku_exemplos (if it already exists: zaku_exemplos_2, …)
cd zaku_exemplos
```

`zaku_exemplo.csv`: 400 people (200 per sex), drawn from the means and covariances of NHANES estimated separately for each
combination of sex and diabetes; no real person. What you can test with it:

| test | target | control | expected answer |
|---|---|---|---|
| regression | `LMI_DXA` | `FMI_DXA` | lean mass indices carry the target |
| classification with a known answer | `label_synthetic` | `FMI_DXA` | **no** index specific: the label depends only on FMI and age |
| diabetes | `diabetes` | `FMI_DXA` or `LMI_DXA` | an open question, as in a real study |

Use `-o` to name each test (`bioms-zaku start zaku_exemplo.csv -o regression.yaml`). The masses in kg (`lean_kg`, `fat_kg`) are
computed from stature: do not use them as target while stature is mapped. Technical files (the older 8000-row example,
spreadsheet format, a real NHANES sample): `bioms-zaku examples --all`.

Every run writes to `zaku_out/<name>`; if the folder already holds a finished run, the new one goes to `<name>_2`, `<name>_3`, …
In `start`, the standard run and the final run (with the accepted indices) land in separate folders. Nothing is overwritten.

## How many people do I need?

Zaku describes your sample and warns when it is too small to support a verdict; it does not estimate a population. The minima are operational, and
the report says, in each case, what it was able to compute.

| what you want | minimum | why |
|---|---|---|
| standard run, continuous target (e.g. lean mass from DXA) | 30 people per stratum | a ridge with one predictor and resamples with ≥ 20 people out of the bag |
| classification (e.g. diabetes yes/no) | 20 people in the smaller class, per stratum | below that the bootstrap has no valid resample; between 20 and ~32 the report marks *events per variable < 10* and the verdict is exploratory |
| suggestions of indices (design) | ≈ 185 people per stratum | 70 % go to the design; the remaining 30 % must keep ≥ 20 out of the bag |
| strata (e.g. by sex) | each stratum meets the minima above | otherwise Zaku audits without strata, or warns |
| repeated measurements of the same person (pre/post) | **one row per person** | aggregate first (a mean, or one visit); Zaku refuses a repeated `id` in this version |

With few data, prefer: no strata, no suggestions, a continuous target. The verdicts come out with wide intervals, and the report
says so; that is information, not a defect.

## Classification with few cases, and a second classifier

The main estimator for classification is logistic regression with an L2 penalty: it is the most stable when there are few events.
The report computes, for each model, the **events per variable** of a training resample (`epv_train`) and marks it below 10
(Peduzzi 1996): read those verdicts as exploratory. The minimum per class stays 20; Zaku describes your sample and warns when it
is too small, instead of refusing.

If you want to see whether the verdict survives a machine classifier (boosting), declare it as a **sensitivity**: it runs on the
same resamples, comes out beside the main one and is never chosen by the result:

```yaml
audit:
  sensitivity: {estimator: hgb, params: {max_depth: 3, learning_rate: 0.05, max_iter: 300}}
```

`xgboost` is also accepted if installed. Boosting needs more data than the logistic model, not less: with a few dozen events,
expect unstable gains, and that is exactly what the side-by-side comparison shows.

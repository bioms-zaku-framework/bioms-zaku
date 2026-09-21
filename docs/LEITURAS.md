# Readings of the primary sources of the indices — BioMS Zaku

One entry per paper, in the order they were read. Each entry records what the paper actually says (with the page), what
that implies for the catalogue and for the method, and the decisions taken from it.

This is the record that the contract (`CONTRACTS.md` §2.1) requires of every entry marked `curated`: the
`curation_record` field of each catalogue method points at the corresponding section here. The PDFs that were read are
**not redistributed**, for copyright; every entry carries the DOI, and the record is verifiable against the original
paper by any reader who obtains it.

*Written in Portuguese, the language in which the readings were made, and translated into English on 2026-09-21, when
the documentation became English only. The translation changed no number, no page reference and no decision.*

---

## 1. Hoffer EC, Meador CK, Simpson DC (1969). Correlation of whole-body impedance with total body water volume. J Appl Physiol 27(4):531-534. DOI 10.1152/jappl.1969.27.4.531

**File:** hoffer1969.pdf (4 p., scanned, OCR text).

**What the paper does.**
- Measures whole-body impedance |Z| at 100 kHz, 100 µA, tetrapolar right hand–left foot, supine (p. 531-532). It does not separate R and Xc: only the modulus Z = E/I.
- Derives the index from conductor physics: Z = ρL/A → V = ρL²/Z (eq. 1-3, p. 531). It uses stature T as L. This is the theoretical origin of the exponent +2 on stature and −1 on impedance.
- Sample: 20 male medical students, healthy (Table 1, individual data: body mass, stature, TBW by tritium dilution, Z), plus 34 patients with abnormal hydration (congestive heart failure, renal failure, Cushing, obesity; Table 2, individual data).
- Table 3 (p. 533), correlations with TBW in the 20 normals / 34 patients: body mass 0.83 / 0.74; Z 0.70 / 0.86; T/Z 0.84 / 0.91; T²/Z 0.92 / 0.93; "ionic mass" vs T²/Z 0.92 / 0.93.
- The equation TBW = A·T²/Z + B, fitted on the 20 normals and applied to the 34 patients: r 0.92, standard deviation of the error 3.89 L (p. 534).
- It acknowledges its antecedents: Thomasset 1962-1965 (needles, 1 kHz) and Nyboer 1959.

**How it fits into Zaku.**
- **Precedence.** The monomial H²/Z is from 1969. The catalogue today attributes H²/R to Lukaski 1985. By the framework's precedence rule, H²/Z (Hoffer 1969) is the antecedent; H²/R at 50 kHz (Lukaski 1985) is the resistance version. At 50 kHz, with a typical phase angle of 5-8°, Z = R/cos φ differs from R by 0.4-1 %; in logs, ln Z = ln R − ln cos φ, almost an identity. The two indices are redundant (ρ ≈ 1) and the framework, with both in the catalogue, would point at Lukaski 1985 as redundant with Hoffer 1969.
- **Theoretical vector vs fitted vector.** The physics gives the vector (H: +2, Z: −1). Zaku's design stage fits exponents to the data. Comparing the vector fitted on NHANES with the physical vector (2, −1) is a sanity check on the design that the 1969 paper supplies for free.
- **Table 3 is a screening of exponents done by hand.** Hoffer compares T⁰/Z, T¹/Z, T²/Z: he varied the exponent of stature and chose the one with the highest correlation. That is exactly the operation the exponent vector formalizes. There is no negative control, and "improvement over body mass" (0.83 → 0.92) is the 1969 version of "value added over covariates".
- **Transfer between populations.** Fitted on 20 normals, applied to 34 patients with abnormal hydration. It is the first transfer test in the BIA literature; Zaku formalizes it with Σ per stratum and the transfer table.
- **Frequency.** 100 kHz, not 50 kHz. Any catalogue entry for Hoffer must record `frequency_khz: 100` and the variable Z, not R.
- **Published individual data.** Tables 1 and 2 carry 54 individuals with body mass, stature, TBW and Z. They serve as a numerical `check_example` for the catalogue and as a hand-calculation lesson (the Σ of the 20 normals in logs).

**Pending decisions (Thalles).**
1. Create the entry `Hoffer1969_H2Z` in the catalogue (variable Z at 100 kHz, vector H +2, Z −1, high confidence, primary source checked) and mark `Lukaski1985_II` as the resistance version of the same monomial, or keep Hoffer only as a precedence note on Lukaski's label. Technical remark: Z is not a mapped variable in Zaku; if the user has only R and Xc, Z = √(R² + Xc²) enters as a composite form with a fit R², not as an exact monomial.
2. Use Tables 1-2 as the numerical verification example of the entry.

**Done (2026-09-11):** the entry `Hoffer1969_H2Z` created in catalogue 1.1.0 (Z100 at 100 kHz, vector H +2 / Z100 −1,
high confidence, numerical example from Table 1: 181.6 cm and 427 Ω → 77.233 cm²/Ω). Three weaknesses of the schema
were corrected first: the vector exactness rule (PhA and Z never in `vector`; PhA and LMI become `composite` with a
fitted vector and R²), the frozen migration fixture (the catalogue may evolve) and the variable `Z100` in the
conventions.

---

## 2. Lukaski HC, Johnson PE, Bolonchuk WW, Lykken GI (1985). Assessment of fat-free mass using bioelectrical impedance measurements of the human body. Am J Clin Nutr 41(4):810-817. DOI 10.1093/ajcn/41.4.810

**File:** lukaski1985.pdf (8 p.).

**What the paper does.**
- Sample: 37 apparently healthy men, 19-42 years, stature 163.1-194.8 cm, body mass 51.8-135.4 kg, fat 7.8-43.0 % (Table 1, p. 812). References: FFM by hydrodensitometry (Brozek), TBW by D₂O dilution, TBK by ⁴⁰K counting.
- Measurement: RJL four-terminal plethysmograph, 800 µA at 50 kHz, tetrapolar hand-foot, supine, ~2 h after a meal; R and Xc measured separately (note 5, p. 813); Z = √(R² + Xc²) (note 3, p. 811). It uses the lowest R among four electrode configurations (p. 813), the right side in most cases (dominant).
- Derivation (p. 811): it starts from V = ρL²/Z (Nyboer) and assumes Xc is small relative to R → V = ρL²/R (eq. 4). It justifies this empirically: r(R, Z) = 0.99 against r(Xc, Z) = 0.70 (p. 813). This is where Hoffer's |Z| becomes R.
- Reliability: CV of R over 5 days 0.9-3.4 % (mean 2 %); test-retest 0.99; maximum difference between electrode placements 1.5 % (Tables 2-3).
- Table 4 (p. 814, n = 37), correlations: Ht²/R with FFM 0.98, TBW 0.95, TBK 0.96, body mass 0.86, FM 0.49, % fat −0.22 (n.s.), M/Ht² 0.73. R alone: FFM −0.86. Xc: FFM −0.54. M/Ht² (BMI): FFM 0.79, FM 0.89, % fat 0.65.
- Regression equations (Fig. 2, p. 815, x in cm²/Ω): FFM = 3.04 + 0.85·Ht²/R (SEE 2.61 kg, r 0.98); TBW = 2.03 + 0.63·Ht²/R (SEE 2.09 L); TBK = −23.09 + 2.56·Ht²/R (SEE 10.70 g).
- It cites Hoffer 1969 (ref. 13) and Nyboer 1943/1972 as antecedents; the declared contribution is validation against three references, the reliability of the measurement and the use of R at 50 kHz.

**How it fits into Zaku.**
- **Precedence confirmed in the source.** The paper itself attributes the Z-TBW relation to Hoffer. The catalogue now records Lukaski 1985 as the R version (50 kHz) of Hoffer's monomial (|Z|, 100 kHz).
- **Table 4 is a negative control in correlation.** Ht²/R: 0.98 with FFM and 0.49 with FM (−0.22 with % fat). M/Ht² (BMI): 0.79 with FFM and 0.89 with FM. In 1985 the data already showed that Ht²/R is specific for fat-free mass and that BMI tracks fat. Zaku turns that reading of a table into a predictive verdict, out of sample, with an interval.
- **Exact vector.** Ht²/R is an exact monomial (H +2, R −1); the decision to swap Z for R is explicitly an approximation (Xc << R), and the framework now treats Z as a non-monomial, consistent with what the paper assumes.
- **Published Σ correlations.** r(R, Z) = 0.99, r(Xc, Z) = 0.70, r(R, Xc) = 0.71, r(stature, body mass) = 0.63: fragments of a log-covariance matrix for healthy men, useful as an external comparison for the Σ of the male NHANES.
- **Limits of validity.** Men only, 19-42 years, healthy. The paper itself asks for validation in abnormal compositions (renal, oncological) and in physical training. Applying it to women or to 8-18 year olds is outside the declared validity (flag †).
- **No individual numerical example.** There is no table of individuals. The mean stature (180.7 cm) and the mean lowest R (443.0 Ω) give 73.70 cm²/Ω, within the range of Fig. 2 (≈55-110), recorded as a `consistency_note`, not as a `check_example`.

**Done (2026-09-11):** `Lukaski1985_II` re-verified against the primary source: provenance pdf_text/high (the asterisk leaves the scorecard), validity (men, 19-42), device, reference methods, n = 37, antecedents; catalogue 1.1.1.

**Pending (Thalles's decision).** The three equations of Fig. 2 are predictive equations (kind `equation`) and are left to the equations stage.

---

**Schema correction (2026-09-11, Thalles's decision).** The catalogue now separates `derivation_sample` (who was used to
fit; descriptive, never raising a flag) from `validity` (applicability asserted or tested by the author; outside it the
framework marks † and never blocks). Hoffer 1969: derived on 20 healthy men aged 21-38, but tested and proposed for
patients of both sexes, 18-77 years, with abnormal hydration → validity corrected to both sexes, 18-77. Lukaski 1985:
derivation and validity coincide (healthy men 19-42; the authors say validity in women and in abnormal compositions is
not established). Catalogue 1.2.0. From here on every reading records both pieces of information.

---

## 3. Baumgartner RN, Chumlea WC, Roche AF (1988). Bioelectric impedance phase angle and body composition. Am J Clin Nutr 48(1):16-23. DOI 10.1093/ajcn/48.1.16

**File:** baumgartner1988.pdf (8 p.).

**What the paper does.**
- Derivation sample: 53 men (9-62 years) and 69 women (9-58 years), white, Ohio, not selected by body composition; 48 under 18; fat from < 5 % to > 50 % (Table 1, p. 18). Reference: hydrodensitometry (Siri, with fat-free mass density corrections for under 25) and skinfolds.
- Measurement: RJL BIA 101, 800 µA at 50 kHz, right side, 12 h fast, supine; whole body **and** segments (arm, leg, trunk), with electrode positions described (p. 17).
- Definition (eq. 3, p. 18): φ = atan(Xc/R) in radians, × 57.297 for degrees. It also computes S²/R as an FFM index, W/S² as a total adiposity index and the mean of the logs of three skinfolds (MSK).
- Results (Table 7, p. 20, age-adjusted correlations, whole body): φ with % fat −0.34 in men and −0.46 in women; with FFM +0.50 in men and not significant in women; with S²/R +0.52 in men. S²/R with FFM 0.89-0.91; W/S² with % fat 0.42 (M) and 0.67 (W).
- Regression of % fat (Table 8): age + skinfolds + W/S² + **trunk φ**; the trunk phase angle adds R² 0.10 (men) and 0.15 (women). Sex + age + trunk φ explain 55.8 % of the variance; with whole-body φ only 31.5 %. Phase angles add nothing to the prediction of FFM after age and S²/R (p. 20).
- Table 5: whole-body r(R, Xc) varies by group: boys 0.76, girls 0.56, men 0.38, women 0.71.
- Fig. 3: an Xc × R plot of the trunk with lines by fat group, the graphical precursor of BIVA.
- Antecedents cited: Brazier 1935 and Barnett 1936-1937 (the impedance angle for thyroid function), Hoffer 1970, Lukaski 1985.

**How it fits into Zaku.**
- **The paper's index is the trunk phase angle, not the whole-body one.** The catalogue evaluates the whole-body one (segmental measurement is outside the framework's scope). The label becomes "PhA whole body (Baumgartner 1988)" and the note records that the authors report the whole-body one as the weaker predictor. A reviewer in the field would ask for exactly this.
- **It is not a monomial.** atan is not a product of powers; today's decision (fitted vector with R²) is consistent with the published definition. Rank equivalence with Xc/R is noted.
- **A negative-control reading already present.** S²/R: strong with FFM, weak or null with % fat. Whole-body φ: weak with both in men, only with fat in women. It is the same pattern NHANES showed in Zaku (PhA specific but with little added value).
- **Σ conditional on the stratum, with 1988 numbers.** r(R, Xc) goes from 0.38 (men) to 0.76 (boys). It explains why the framework requires Σ per stratum and why the transfer between sexes failed on NHANES.
- **Precedence.** The phase angle as a physiological measurement is from the 1930s; Baumgartner 1988 is the first use for body composition. The catalogue's precedence rule is relative to the catalogue, and the note records the antecedents.
- **Declared validity:** both sexes, 9-62 years, white, the whole range of adiposity. Derivation and validity coincide.
- **No individual numerical example;** only means of φ per group (Table 2). Recorded as a `consistency_note`.

**Done (2026-09-11):** `Baumgartner1988_PhA` re-verified: label, provenance pdf_text/high, derivation sample, validity, device, reference, precedence and the trunk caveat; catalogue 1.2.1.

**Pending (Thalles's decision).** The % fat equation of Table 8 uses the trunk (segmental) phase angle and is outside the current scope.

**Thalles's decision (2026-09-11) on Lukaski 1985 and Baumgartner 1988:** the five and the six proposed points were approved; the edits already made to the catalogue stand as they are (1.2.0 and 1.2.1).

---

## 4. Piccoli A, Rossi B, Pillon L, Bucciante G (1994). A new method for monitoring body fluid variation by bioimpedance analysis: the RXc graph. Kidney Int 46(2):534-539. DOI 10.1038/ki.1994.305

**File:** piccoli1994.pdf (6 p., technical note).

**What the paper does.**
- Aim: to monitor fluid variation in the individual patient without assumptions about body composition and without estimating volumes in litres. A hydration method, not a body-composition index.
- Sample: 217 Caucasian adults (Padua): 86 healthy controls (38 men, 48 women, 16-66 years), 55 with chronic renal failure, 36 with nephrotic syndrome, 40 obese (BMI > 31); 16-75 years.
- Measurement: RJL/Akern BIA-109, 800 µA at 50 kHz, tetrapolar right hand-foot; CV 1 % within a day, 3 % weekly, 2 % between operators.
- Definition: R/H and Xc/H in Ω/m (stature in metres). Bivariate treatment: 95 % confidence ellipses (group means) and 75 %/95 % tolerance ellipses (individuals), under bivariate normality. Direction = phase angle; length = hydration.
- No body-composition reference method; clinical validation (oedema, group). The lower pole of the 75 % ellipse identifies 28/29 renal patients with oedema.
- Table 1: healthy, men R/H 292.6 and Xc/H 30.2 Ω/m; women 374.3 and 36.6. Table 2: r(R/H, Xc/H) healthy 0.48 (men 0.32, women 0.33), renal 0.56, nephrotic 0.67, obese 0.71. No correlation with age in the healthy.
- Explicit warning (p. 537): because of the mutual correlation between R and Xc, the authors are cautious about accepting that isolated components reflect specific compartments; different ethnicities may have different ellipses.

**How it fits into Zaku.**
- R/H and Xc/H were not proposed as isolated indices; the catalogue evaluates them as exact monomials (R +1, H −1) and (Xc +1, H −1). The label and the note record this. On NHANES, R/H came out redundant with H²/R (ρ 0.96), consistent with Piccoli's warning.
- Σ conditional on clinical state, not only on sex (0.32 to 0.71). A "stratum" may be a clinical condition.
- No composition reference: auditing R/H against lean mass is outside what the paper proposed; the note says so.
- Unit Ω/m: the catalogue expression now uses H_m.
- No individual numerical example; the means of Table 1 as a consistency note.

**Thalles's decision (2026-09-11):** keep R/H and Xc/H in the catalogue as components audited individually, with the explicit caveat. Six points applied; catalogue 1.2.2.

---

## 5. Levi Micheli M, Cannataro R, Gulisano M, Mascherini G (2022). Proposal of a new parameter for evaluating muscle mass in footballers through bioimpedance analysis. Biology 11(8):1182. DOI 10.3390/biology11081182

**File:** levimicheli2022.pdf (7 p., open access).

**What the paper does.**
- Sample: 664 male Italian footballers, Caucasian, 18-35 years (24.5 ± 5.8), divisions A-D, in season, the same operator. Elite 241, high 223, medium 200.
- Measurement: Akern BIA-101, 800 µA at 50 kHz, right side, supine, daily calibration (380 Ω / 47 Ω).
- Definition (p. 3): LMI = (PA × H)/R, PA in degrees, H in cm; °·cm·Ω⁻¹. Means (Table 2): elite 3.08, high 2.87, medium 2.71; it discriminates levels with an effect size up to 1.04.
- Validation (Table 3): r 0.908 with BCM, 0.925 with BCMI, 0.704 with PA, 0.035 with fat mass. BCM and fat mass come from the Kotler 1996 equation, itself derived from BIA; there is no independent reference method, and the authors admit it (p. 5-6).
- Declared limits: hand-foot at 50 kHz only; one country; uses in children, the malnourished and the elderly are future directions.
- Data on request from the corresponding author (Mascherini, Florence).

**How it fits into Zaku.**
- An exemplary case of the framework's thesis: the LMI-BCM correlation is largely algebraic (the same R, Xc, H), predictable from Σ. The "control" (fat mass) is also derived from BIA: the declaration that the target is independent of the variables would be false.
- The approximate form Xc·H/R² = (Xc/H)/(R/H)², a monomial in Piccoli's components; not exact because of the arctan → `composite` with a fitted vector and R² (decision of 09-11).
- No antecedent in the catalogue; on NHANES (DXA criterion) it was original (max ρ 0.86) and the most specific of the five: a good index with circular validation at its origin; independent validation is what the demonstration offers.
- Validity: Caucasian male footballers 18-35, hand-foot 50 kHz.
- Numerical example: group means give 3.06 vs 3.08 and 2.67 vs 2.71; a consistency note, not a `check_example` (a mean of ratios ≠ a ratio of means).

**Thalles's decision (2026-09-11):** approved with maximum rigour; six points applied; catalogue 1.2.3. Separate note: contacting Mascherini could be framed as an independent audit of LMI against DXA.

---

## 6. Buffa R, Saragat B, Cabras S, Rinaldi AC, Marini E (2013). Accuracy of specific BIVA for the assessment of body composition in the United States population. PLoS ONE 8(3):e58533. DOI 10.1371/journal.pone.0058533

**File:** buffa2013.pdf (10 p., open access).

**What the paper does.**
- Sample: NHANES 2003-2004, 1,590 adults (836 men, 754 women), 21-49 years, ethnicities pooled, only perfect fits to the Cole model (BIDFIT = 0). HYDRA 4200; DXA Hologic QDR-4500A. The same data source as Zaku's demonstration; the base is deposited at veprints.unica.it/809.
- Definition (p. 3-4): Rsp = R·A/L, Xcsp = Xc·A/L; A = 0.45·arm area + 0.10·waist area + 0.45·calf area (C²/4π, m²); L = 1.1·H; ×100 → Ω·cm. Means: men Rsp 402.4, Xcsp 52.5; women 492.0, 55.4.
- Independent reference: DXA (% fat) and BIS (ECW/ICW).
- Table 2: Rsp with % fat 0.85 (men) and 0.87 (women); Xcsp 0.68 and 0.77; classic R/H and Xc/H −0.16 to −0.35; PhA −0.94/−0.92 with ECW/ICW. ROC for fat: specific 0.84-0.92, classic 0.49-0.61 (p = 0.002).
- Table 1: r(R/H, Xc/H) 0.74 in both sexes; r(Rsp, Xcsp) 0.84/0.88.
- Precedence: proposed in Marini 2012 (Italian elderly); specific resistivity in Chumlea, Baumgartner and Roche 1988.

**How it fits into Zaku.**
- Rsp/Xcsp measure fat by design → against a lean-mass target they "track the control"; the correct audit swaps target and control. It motivated the `target_kind` field and the orientation warning.
- External confirmation of Piccoli's warning: R/H and Xc/H on their own are ≈ chance for fat.
- Not a monomial (a weighted sum of squares) → `composite`, R² reported.
- Population-specific Σ: r(R/H, Xc/H) 0.74 (NHANES) vs 0.32 (healthy subjects in Padua).
- Scale: the expression corrected to A/(1.1·H)·100; consistency 404.2 vs 402.4 (men) and 52.5 vs 52.5.

**Thalles's decision (2026-09-11):** the six points and `target_kind` approved. Applied: catalogue 1.3.0; contract v0.4.6 (`target_kind`, `declarations.target_kinds`, orientation warning, never a block); `target_kind` assigned to the seven curated indices.

**To obtain (fundamental):** Marini et al. 2012, J Nutr Health Aging (the original proposal of specific BIVA); Chumlea, Baumgartner & Roche 1988, Am J Clin Nutr 48:7-15 (specific resistivity).

---

## 7. Lukaski HC, Kyle UG, Kondrup J (2017). Assessment of adult malnutrition and prognosis with bioelectrical impedance analysis: phase angle and impedance ratio. Curr Opin Clin Nutr Metab Care 20(5):330-339. DOI 10.1097/MCO.0000000000000387

**File:** lukaski2017.pdf (10 p.). A narrative review; not a primary source.

**What the paper does.** It reviews the phase angle (50 kHz) and the impedance ratio Z200/Z5 as prognostic markers. It defines the ratio in the text (p. 2), attributed to Mulasi 2015; antecedent Jenin 1975 (Z5/Z100). Table 1: 30 observational studies since 2012 with a low angle predicting malnutrition, complications and mortality (cut-offs 4.4°-5.9°); standardized phase angle (z score by sex, age, BMI). Key points: "it is not diagnostic"; hydration and inflammation confound; only phase-sensitive devices; devices (Genton 2017) and electrodes (Nescolarde 2016) shift the values.

**How it fits into Zaku.** It supports "one device per data set"; the z score per stratum is the clinical version of Σ per stratum; hydration as a declared confounder = a natural negative control for the phase angle; the impedance ratio keeps low confidence (secondary source). NHANES BIX has R and Xc at 5, 50 and 200 kHz → the ratio is evaluable in the demonstration by adding Z5 and Z200 to the CSV.

**Thalles's decision (2026-09-11):** the four points approved. Applied: the IR entry (label, target_kind hydration, precedence note, low confidence), a note on PhA, device/electrode references on the page; catalogue 1.3.1. Pending: adding Z5/Z200 to the demonstration CSV.

---

## 8. Marini E, Sergi G, Succa V, Saragat B, Sarti S, Coin A, Manzato E, Buffa R (2013). Efficacy of specific bioelectrical impedance vector analysis (BIVA) for assessing body composition in the elderly. J Nutr Health Aging 17(6):515-521. DOI 10.1007/s12603-012-0411-7

**File:** marini2013.pdf (7 p.). The original proposal of specific BIVA (received in June 2012).

**What the paper does.** The complete formula (p. 516): A = 0.45·arm + 0.10·waist + 0.45·calf (C²/4π), L = 1.1·H, ×100 → Ω·cm; the weights come from the partition of resistance (arms 45 %, legs 45 %, trunk 10 %); the 1.1 from Sardinian anthropometry. Sample: 207 elderly people from Padua (75 men, 132 women), 65-93 years, healthy and active; 5 dehydrated excluded → 202. Akern BIA 101; DXA Hologic QDR 4500W. Classic BIVA distinguishes absolute mass but not % fat (R/H and Xc/H equal across quartiles); the specific values do distinguish it (Table 3). Fig. 3: Rsp 0.75/0.69 and Xcsp 0.53/0.48 with % fat; R/H −0.13/−0.16 n.s. Declared antecedent: Chumlea, Baumgartner and Roche 1988.

**How it fits into Zaku.** It fixes the formula and the precedence at the origin (2013); Buffa 2013 becomes the validation on NHANES. Two published points for Σ transfer (Italian elderly vs American adults: the same sign, magnitudes 0.75 vs 0.85). A third confirmation that R/H on its own does not measure fat. No individual example; the means of Table 1 give 392.6 Ω·cm (between the quartile groups 334.7 and 450.3).

**Thalles's decision (2026-09-11):** approved; five points applied; catalogue 1.3.2.

---

## 9. Mulasi U, Kuchnia AJ, Cole AJ, Earthman CP (2015). Bioimpedance at the bedside: current applications, limitations, and opportunities. Nutr Clin Pract 30(2):180-193. DOI 10.1177/0884533614568155

**File:** mulasi2015.pdf (14 p.). An invited review; not a primary source.

**What the paper does.** It defines the impedance ratio (p. 8) as Z200/Z5, a name introduced by Bodystat (the manufacturer); reference cut-offs ≤0.78 (men) and ≤0.82 (women) from an abstract (Plank 2013); applications in oedema, heart failure and malnutrition, all without a consensus cut-off. Table 1: commercial devices and frequencies. P. 3: the volume-conductor model assumes a single cylinder; single-frequency BIA does not separate intra- from extracellular water; devices are "black boxes".

**How it fits into Zaku.** A curation finding: the 200/5 ratio has no derivation paper; the chain is manufacturer → abstracts → reviews. The scientific antecedent is Jenin 1975 (5/100 kHz), available only as an abstract. Confidence stays low by the contract's rule. Table 1 supports "one device per data set".

**Thalles's decision (2026-09-11):** ok; applied; catalogue 1.3.3.

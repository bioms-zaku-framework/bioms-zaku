"""
EN: Bibliographic records for the report's References section. Every DOI below was resolved on Crossref on 2026-09-15 and
    the record (authors, year, title, journal, volume, pages) was taken from the Crossref metadata, not typed by hand;
    entries are listed as published and are not translated. Two candidates were rejected at verification: the DOI
    10.1097/ede.0b013e3181e4bfd7 (it is the erratum of Lipsitch 2010, not the article) and 10.1111/sms.12780 (a waist-girth
    paper, not a general allometry reference). Statistical references are fixed per result block; bioimpedance references
    are those of the methods actually evaluated in the run (from the catalogue). No network access at run time.
"""
from __future__ import annotations

VERIFIED_ON = "2026-09-16"

# EN: DOI -> record, straight from Crossref (see the module docstring). `pages` may be a first page or an article number.
RECORDS: dict[str, dict] = {
    '10.2478/joeb-2026-0010': {"authors": "Lafontant K, Fukuda DH, Smith S, et al.", "year": 2026, "title": "Examining within-session test-retest reliability of four bioimpedance devices among adults across a wide age range", "journal": "Journal of Electrical Bioimpedance", "volume": "17", "issue": "1", "pages": "67-77"},
    '10.3390/life13051119': {"authors": "Yang J, Kim J, Chun BC, Lee JM", "year": 2023, "title": "Cook with Different Pots, but Similar Taste? Comparison of Phase Angle Using Bioelectrical Impedance Analysis According to Device Type and Examination Posture", "journal": "Life", "volume": "13", "issue": "5", "pages": "1119"},
    '10.4324/9780203771587': {"authors": "Cohen J", "year": 1988, "title": "Statistical Power Analysis for the Behavioral Sciences", "journal": "2nd ed. Lawrence Erlbaum (Routledge reissue 2013)", "volume": "", "issue": "", "pages": ""},
    '10.2307/2983064': {"authors": "Kronmal RA", "year": 1993, "title": "Spurious Correlation and the Fallacy of the Ratio Standard Revisited", "journal": "Journal of the Royal Statistical Society. Series A (Statistics in Society)", "volume": "156", "issue": "3", "pages": "379-392"},
    '10.2307/2412740': {"authors": "Atchley WR, Gaskins CT, Anderson D", "year": 1976, "title": "Statistical Properties of Ratios. I. Empirical Results", "journal": "Systematic Zoology", "volume": "25", "issue": "2", "pages": "137-148"},
    '10.2307/1412159': {"authors": "Spearman C", "year": 1904, "title": "The Proof and Measurement of Association between Two Things", "journal": "The American Journal of Psychology", "volume": "15", "issue": "1", "pages": "72-101"},
    '10.1093/ajcn/86.1.82': {"authors": "Heymsfield SB, Gallagher D, Mayer L, Beetsch J, Pietrobelli A", "year": 2007, "title": "Scaling of human body composition to stature: new insights into body mass index", "journal": "The American Journal of Clinical Nutrition", "volume": "86", "issue": "1", "pages": "82-91"},
    '10.1080/00401706.1970.10488634': {"authors": "Hoerl AE, Kennard RW", "year": 1970, "title": "Ridge Regression: Biased Estimation for Nonorthogonal Problems", "journal": "Technometrics", "volume": "12", "issue": "1", "pages": "55-67"},
    '10.1111/j.2517-6161.1974.tb00994.x': {"authors": "Stone M", "year": 1974, "title": "Cross-Validatory Choice and Assessment of Statistical Predictions", "journal": "Journal of the Royal Statistical Society Series B: Statistical Methodology", "volume": "36", "issue": "2", "pages": "111-133"},
    '10.1214/aos/1176344552': {"authors": "Efron B", "year": 1979, "title": "Bootstrap Methods: Another Look at the Jackknife", "journal": "The Annals of Statistics", "volume": "7", "issue": "1", "pages": "1-26"},
    '10.1002/sim.2929': {"authors": "Pencina MJ, D'Agostino RB Sr, D'Agostino RB Jr, Vasan RS", "year": 2008, "title": "Evaluating the added predictive ability of a new marker: from area under the ROC curve to reclassification and beyond", "journal": "Statistics in Medicine", "volume": "27", "issue": "2", "pages": "157-172"},
    '10.1198/tast.2009.08210': {"authors": "Tjur T", "year": 2009, "title": "Coefficients of Determination in Logistic Regression Models—A New Proposal: The Coefficient of Discrimination", "journal": "The American Statistician", "volume": "63", "issue": "4", "pages": "366-372"},
    '10.1016/S0895-4356(96)00236-3': {"authors": "Peduzzi P, Concato J, Kemper E, Holford TR, Feinstein AR", "year": 1996, "title": "A simulation study of the number of events per variable in logistic regression analysis", "journal": "Journal of Clinical Epidemiology", "volume": "49", "issue": "12", "pages": "1373-1379"},
    '10.2307/2347628': {"authors": "Le Cessie S, Van Houwelingen JC", "year": 1992, "title": "Ridge Estimators in Logistic Regression", "journal": "Applied Statistics", "volume": "41", "issue": "1", "pages": "191-201"},
    '10.1148/radiology.143.1.7063747': {"authors": "Hanley JA, McNeil BJ", "year": 1982, "title": "The Meaning and Use of the Area under a Receiver Operating Characteristic (ROC) Curve", "journal": "Radiology", "volume": "143", "issue": "1", "pages": "29-36"},
    '10.1080/01621459.1983.10477973': {"authors": "Efron B", "year": 1983, "title": "Estimating the Error Rate of a Prediction Rule: Improvement on Cross-Validation", "journal": "Journal of the American Statistical Association", "volume": "78", "issue": "382", "pages": "316-331"},
    '10.1109/tsmc.1974.5408535': {"authors": "Cover TM", "year": 1974, "title": "The Best Two Independent Measurements Are Not the Two Best", "journal": "IEEE Transactions on Systems, Man, and Cybernetics", "volume": "SMC-4", "issue": "1", "pages": "116-117"},
    '10.1038/s41586-020-2649-2': {"authors": "Harris CR, Millman KJ, van der Walt SJ, et al.", "year": 2020, "title": "Array programming with NumPy", "journal": "Nature", "volume": "585", "issue": "7825", "pages": "357-362"},
    '10.1038/s41592-019-0686-2': {"authors": "Virtanen P, Gommers R, Oliphant TE, et al.", "year": 2020, "title": "SciPy 1.0: fundamental algorithms for scientific computing in Python", "journal": "Nature Methods", "volume": "17", "issue": "3", "pages": "261-272"},
    '10.25080/Majora-92bf1922-00a': {"authors": "McKinney W", "year": 2010, "title": "Data Structures for Statistical Computing in Python", "journal": "Proceedings of the Python in Science Conference", "volume": "", "issue": "", "pages": "56-61"},
    '10.1109/MCSE.2007.55': {"authors": "Hunter JD", "year": 2007, "title": "Matplotlib: A 2D Graphics Environment", "journal": "Computing in Science & Engineering", "volume": "9", "issue": "3", "pages": "90-95"},
    '10.1007/s12603-012-0411-7': {"authors": "Marini E, Sergi G, Succa V, Saragat B, Sarti S, Coin A, Manzato E, Buffa R", "year": 2013, "title": "Efficacy of specific bioelectrical impedance vector analysis (BIVA) for assessing body composition in the elderly", "journal": "The Journal of nutrition, health and aging", "volume": "17", "issue": "6", "pages": "515-521"},
    '10.1016/S0261-5614(03)00048-7': {"authors": "Kyle U, Genton L, Hans D, Pichard C", "year": 2003, "title": "Validation of a bioelectrical impedance analysis equation to predict appendicular skeletal muscle mass (ASMM)", "journal": "Clinical Nutrition", "volume": "22", "issue": "6", "pages": "537-543"},
    '10.1016/S0899-9007(00)00553-0': {"authors": "Kyle UG, Genton L, Karsegard L, Slosman DO, Pichard C", "year": 2001, "title": "Single prediction equation for bioelectrical impedance analysis in adults aged 20–94 years", "journal": "Nutrition", "volume": "17", "issue": "3", "pages": "248-253"},
    '10.1016/j.clnu.2014.07.010': {"authors": "Sergi G, De Rui M, Veronese N, et al.", "year": 2015, "title": "Assessing appendicular skeletal muscle mass with bioelectrical impedance analysis in free-living Caucasian older adults", "journal": "Clinical Nutrition", "volume": "34", "issue": "4", "pages": "667-673"},
    '10.1016/j.clnu.2016.04.026': {"authors": "Scafoglieri A, Clarys JP, Bauer JM, et al.", "year": 2017, "title": "Predicting appendicular lean and fat mass with bioelectrical impedance analysis in older adults with physical function decline – The PROVIDE study", "journal": "Clinical Nutrition", "volume": "36", "issue": "3", "pages": "869-875"},
    '10.1016/j.numecd.2025.104281': {"authors": "Campa F, Sampieri A, Spinello G, Moro T, Paoli A", "year": 2026, "title": "Development and validation of a phase-sensitive bioelectrical equation for estimating skeletal muscle mass using DXA as reference", "journal": "Nutrition, Metabolism and Cardiovascular Diseases", "volume": "36", "issue": "1", "pages": "104281"},
    '10.1038/ejcn.2017.27': {"authors": "Bosy-Westphal A, Jensen B, Braun W, Pourhassan M, Gallagher D, Müller MJ", "year": 2017, "title": "Quantification of whole-body and segmental skeletal muscle mass using phase-sensitive 8-electrode medical bioelectrical impedance devices", "journal": "European Journal of Clinical Nutrition", "volume": "71", "issue": "9", "pages": "1061-1067"},
    '10.1038/ki.1994.305': {"authors": "Piccoli A, Rossi B, Pillon L, Bucciante G", "year": 1994, "title": "A new method for monitoring body fluid variation by bioimpedance analysis: The RXc graph", "journal": "Kidney International", "volume": "46", "issue": "2", "pages": "534-539"},
    '10.1093/ajcn/41.4.810': {"authors": "Lukaski H, Johnson P, Bolonchuk W, Lykken G", "year": 1985, "title": "Assessment of fat-free mass using bioelectrical impedance measurements of the human body", "journal": "The American Journal of Clinical Nutrition", "volume": "41", "issue": "4", "pages": "810-817"},
    '10.1093/ajcn/44.3.417': {"authors": "Kushner R, Schoeller D", "year": 1986, "title": "Estimation of total body water by bioelectrical impedance analysis", "journal": "The American Journal of Clinical Nutrition", "volume": "44", "issue": "3", "pages": "417-424"},
    '10.1093/ajcn/47.1.7': {"authors": "Segal K, Van Loan M, Fitzgerald P, Hodgdon A, Van Itallie T", "year": 1988, "title": "Lean body mass estimation by bioelectrical impedance analysis: a four-site cross-validation study", "journal": "The American Journal of Clinical Nutrition", "volume": "47", "issue": "1", "pages": "7-12"},
    '10.1093/ajcn/48.1.16': {"authors": "Baumgartner R, Chumlea W, Roche A", "year": 1988, "title": "Bioelectric impedance phase angle and body composition", "journal": "The American Journal of Clinical Nutrition", "volume": "48", "issue": "1", "pages": "16-23"},
    '10.1093/ajcn/50.2.255': {"authors": "Gray DS, Bray GA, Gemayel N, Kaplan K", "year": 1989, "title": "Effect of obesity on bioelectrical impedance", "journal": "The American Journal of Clinical Nutrition", "volume": "50", "issue": "2", "pages": "255-260"},
    '10.1093/ajcn/77.2.331': {"authors": "Sun SS, Chumlea WC, Heymsfield SB, et al.", "year": 2003, "title": "Development of bioelectrical impedance analysis prediction equations for body composition with the use of a multicomponent model for use in epidemiologic surveys", "journal": "The American Journal of Clinical Nutrition", "volume": "77", "issue": "2", "pages": "331-340"},
    '10.1152/jappl.1969.27.4.531': {"authors": "Hoffer EC, Meador CK, Simpson DC", "year": 1969, "title": "Correlation of whole-body impedance with total body water volume", "journal": "Journal of Applied Physiology", "volume": "27", "issue": "4", "pages": "531-534"},
    '10.1152/jappl.1986.60.4.1327': {"authors": "Lukaski HC, Bolonchuk WW, Hall CB, Siders WA", "year": 1986, "title": "Validation of tetrapolar bioelectrical impedance method to assess human body composition", "journal": "Journal of Applied Physiology", "volume": "60", "issue": "4", "pages": "1327-1332"},
    '10.1152/jappl.1992.72.1.366': {"authors": "Houtkooper LB, Going SB, Lohman TG, Roche AF, Van Loan M", "year": 1992, "title": "Bioelectrical impedance estimation of fat-free body mass in children and youth: a cross-validation study", "journal": "Journal of Applied Physiology", "volume": "72", "issue": "1", "pages": "366-373"},
    '10.1152/jappl.2000.89.2.465': {"authors": "Janssen I, Heymsfield SB, Baumgartner RN, Ross R", "year": 2000, "title": "Estimation of skeletal muscle mass by bioelectrical impedance analysis", "journal": "Journal of Applied Physiology", "volume": "89", "issue": "2", "pages": "465-471"},
    '10.1177/0884533614568155': {"authors": "Mulasi U, Kuchnia AJ, Cole AJ, Earthman CP", "year": 2015, "title": "Bioimpedance at the Bedside: Current Applications, Limitations, and Opportunities", "journal": "Nutrition in Clinical Practice", "volume": "30", "issue": "2", "pages": "180-193"},
    '10.1186/1475-2891-6-18': {"authors": "Macias N, Alemán-Mateo H, Esparza-Romero J, Valencia ME", "year": 2007, "title": "Body fat measurement by bioelectrical impedance and air displacement plethysmography: a cross-validation study to design bioelectrical impedance equations in Mexican adults", "journal": "Nutrition Journal", "volume": "6", "issue": "1", "pages": ""},
    '10.3390/biology11081182': {"authors": "Levi Micheli M, Cannataro R, Gulisano M, Mascherini G", "year": 2022, "title": "Proposal of a New Parameter for Evaluating Muscle Mass in Footballers through Bioimpedance Analysis", "journal": "Biology", "volume": "11", "issue": "8", "pages": "1182"},
    '10.3390/ijerph14070809': {"authors": "Yamada Y, Nishizawa M, Uchiyama T, Kasahara Y, Shindo M, Miyachi M, Tanaka S", "year": 2017, "title": "Developing and Validating an Age-Independent Equation Using Multi-Frequency Bioelectrical Impedance Analysis for Estimation of Appendicular Skeletal Muscle Mass and Establishing a Cutoff for Sarcopenia", "journal": "International Journal of Environmental Research and Public Health", "volume": "14", "issue": "7", "pages": "809"},
    '10.37527/2008.58.4.010': {"authors": "Augustemak de Lima LR, Rech CR, Petroski EL", "year": 2026, "title": "Utilização da impedância bioelétrica para estimativa da massa muscular esquelética em homens idosos", "journal": "Archivos Latinoamericanos de Nutrición", "volume": "58", "issue": "4", "pages": "386-391"},
    '10.4067/S0034-98872011001200002': {"authors": "Schifferli I, Carrasco F, Inostroza J", "year": 2011, "title": "Formulación de una ecuación para predecir la masa grasa corporal a partir de bioimpedanciometría en adultos en un amplio rango de edad e índice de masa corporal", "journal": "Revista médica de Chile", "volume": "139", "issue": "12", "pages": "1534-1543"},
    '10.4067/S0034-98872020001001435': {"authors": "Schifferli I, Orellana-Cáceres JJ, Morales G, Inostroza J, Carrasco F", "year": 2020, "title": "Validación y generación de ecuaciones para estimar masa grasa corporal en adultos chilenos, formuladas a partir de bioimpedanciometría, en un amplio rango de edad e índice de masa corporal", "journal": "Revista médica de Chile", "volume": "148", "issue": "10", "pages": "1435-1443"},
    '10.1097/ede.0b013e3181d61eeb': {"authors": "Lipsitch M, Tchetgen Tchetgen E, Cohen T", "year": 2010, "title": "Negative Controls: A Tool for Detecting Confounding and Bias in Observational Studies", "journal": "Epidemiology", "volume": "21", "issue": "3", "pages": "383-388"},
    '10.1152/jappl.1995.79.3.1027': {"authors": "Nevill AM, Holder RL", "year": 1995, "title": "Scaling, normalizing, and per ratio standards: an allometric modeling approach", "journal": "Journal of Applied Physiology", "volume": "79", "issue": "3", "pages": "1027-1031"},
}

# EN: references without a DOI (JMLR does not assign DOIs): official URL instead, checked on 2026-09-15.
RECORDS_NO_DOI: dict[str, dict] = {
    "bengio2004": {"authors": "Bengio Y, Grandvalet Y", "year": 2004, "title": "No unbiased estimator of the variance of K-fold cross-validation",
                   "journal": "Journal of Machine Learning Research", "volume": "5", "pages": "1089-1105", "url": "https://www.jmlr.org/papers/v5/grandvalet04a.html"},
    "kohavi1995": {"authors": "Kohavi R", "year": 1995, "title": "A study of cross-validation and bootstrap for accuracy estimation and model selection",
                   "journal": "Proceedings of the 14th International Joint Conference on Artificial Intelligence (IJCAI)", "volume": "2", "pages": "1137-1143", "url": "https://www.ijcai.org/Proceedings/95-2/Papers/016.pdf"},
    "pedregosa2011": {"authors": "Pedregosa F, Varoquaux G, Gramfort A, et al.", "year": 2011, "title": "Scikit-learn: Machine Learning in Python",
                      "journal": "Journal of Machine Learning Research", "volume": "12", "pages": "2825-2830", "url": "https://jmlr.org/papers/v12/pedregosa11a.html"},
}

# EN: which statistical/algebraic reference supports which result block (keys of html.BLOCKS). Order = order of citation.
#     The three records dated 2026-09-16 anchor the declared thresholds (contract §3.6): the redundancy threshold 0.95 on the
#     within-session repeatability of R, Xc and PhA (ICC(2,1) 0.986–1.00 at 50 kHz, four devices; 0.95 lies below it, a conservative floor) and the cross-device agreement of PhA (ICC 0.993);
#     the verdict margin 0.03 in R² above Cohen's small effect f² = 0.02 (ΔR² = f²·(1 − R²) ≤ 0.02 for any baseline).
METHOD_REFS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("10.2478/joeb-2026-0010", ("m.redund",)),                # Lafontant 2026 — within-session test-retest of R, Xc, PhA, ICC 0.986–1.00 at 50 kHz (anchor of the 0.95 threshold: a floor below repeatability; reliability is per make and model)
    ("10.3390/life13051119", ("m.redund",)),                  # Yang 2023 — PhA across two models of one maker, three postures, two leads: ICC 0.993 with a level offset up to 1° (anchor of the 0.95 threshold; order preserved, level shifts — why ranks, why devices are never pooled)
    ("10.4324/9780203771587", ("m.spec", "m.util")),          # Cohen 1988 ch. 9 Case 1 — f² = ΔR²/(1 − R²_full), small f² = 0.02 ⇒ ΔR² ≤ 0.02 for any baseline (anchor of the 0.03 margin; population values, our gain is out-of-sample, hence conservative; Cohen: a convention to reject when unsuited → sensitivity grid)
    ("10.2307/2983064", ("m.redund",)),                      # Kronmal 1993 — indices sharing measured components correlate by construction (spurious correlation of ratio standards); Σ quantifies that part
    ("10.2307/2412740", ("m.redund", "m.util")),             # Atchley 1976 — induced correlation grows with the variability of the shared variable (Σ diagonal); dividing by a size variable does not remove its effect (why utility is measured over the covariates)
    ("10.1152/jappl.1995.79.3.1027", ("m.design", "m.redund")),  # Nevill & Holder 1995 — log-linear fit of the exponents = the allometric model that yields the appropriate per-ratio standard (design); indices as power functions (redundancy)
    ("10.1093/ajcn/86.1.82", ("m.design", "m.util")),        # Heymsfield 2007 — lean and fat components scale to height with powers ≈ 2 (index-form targets are stature-independent: utility); the power of height must be derived in the population under study, Benn principle (design)
    ("10.2307/1412159", ("m.redund",)),                      # Spearman 1904 — rank correlation (invariant to monotone transforms, insensitive to extremes); attenuation by measurement error bounds the observable agreement (anchor of the 0.95 threshold)
    ("10.1097/ede.0b013e3181d61eeb", ("m.spec",)),           # Lipsitch 2010 — negative-control outcome: shares the target's sources of spurious association, analysed by the same procedure (by analogy; the conditional two-way form and the quantitative rule are this tool's extension)
    ("10.1080/00401706.1970.10488634", ("m.spec", "m.util")),  # Hoerl & Kennard 1970 — ridge on standardized predictors (correlation form); fixed α = 1 for every index, not tuned by design (they state no automatic choice of k exists); acts only when index and control are nearly collinear
    ("10.1111/j.2517-6161.1974.tb00994.x", ("m.spec", "m.util")),  # Stone 1974 — cross-validatory assessment (K-fold form here) of a fixed prescription: nothing is chosen by the data in the audit, so no nested validation is needed; design exponents are chosen on a partition never used in the assessment
    ("bengio2004", ("m.spec", "m.util")),                    # Bengio & Grandvalet 2004 — K-fold test errors are dependent; no unbiased estimator of their variance; naive estimators underestimate it by the order of the variance itself (why fold dispersion is never used for inference)
    ("10.1214/aos/1176344552", ("m.spec", "m.util", "m.transfer")),  # Efron 1979 — bootstrap principle: resample persons from the empirical distribution, Monte Carlo with B replicates; does NOT establish the percentile interval (its §8 warns about the pivot step) nor out-of-bag scoring
    ("10.1080/01621459.1983.10477973", ("m.spec", "m.util")),  # Efron 1983 — ε₀: score each resample on the persons it did not draw (out-of-bag, ≈36.8 % per resample); pessimistic for an absolute score (hence .632), used here only in paired differences of nested models where the pessimism cancels; .632 not applied
    ("10.1198/tast.2009.08210", ("m.spec", "m.util")),     # Tjur 2009 — coefficient of discrimination D = mean p̂ cases − mean p̂ non-cases; exact relations to the quadratic R² analogues (classification gains are ΔD)
    ("10.1002/sim.2929", ("m.spec", "m.util")),            # Pencina 2008 — ΔAUROC is insensitive even to strong markers; the IDI compares D between models; bootstrap for testing
    ("10.1016/S0895-4356(96)00236-3", ("m.spec", "m.util")),  # Peduzzi 1996 — below 10 events per variable logistic coefficients are biased/unstable; EPV computed per model and flagged, never a barrier
    ("10.2307/2347628", ("m.spec", "m.util")),              # Le Cessie & van Houwelingen 1992 — L2-penalised logistic: finite, stable coefficients with few events or correlated predictors; intercept unpenalised; penalty chosen by classification error is unstable (why no cut-off metrics)
    ("kohavi1995", ("m.spec", "m.util")),                   # Kohavi 1995 — stratified cross-validation: less bias and variance than unstratified; 10 folds recommended for model selection (none here)
    ("10.1148/radiology.143.1.7063747", ("m.spec", "m.util")),  # Hanley & McNeil 1982 — AUROC = P(random case scores above random non-case) = Wilcoxon, distribution-free; SE depends on both class sizes; paired comparison on the same subjects (classification)
    ("10.1109/tsmc.1974.5408535", ("m.screen",)),            # Cover 1974 — the best pair is not the pair of the two best, even without redundancy: screening classes are per index, combinations are never inferred from them, pairs are judged only when audited as pairs
)

# EN: cited only in the classification sentence / row of the report: listed only when the run audits a class label (a reference
#     is never listed without a citation in the text; found 2026-09-16 in a regression report).
CLASSIFICATION_ONLY: frozenset[str] = frozenset({"10.1148/radiology.143.1.7063747", "10.1016/S0895-4356(96)00236-3", "10.2307/2347628"})

# EN: software actually executed in a run (versions are in the manifest).
SOFTWARE_REFS: tuple[str, ...] = ("10.1038/s41586-020-2649-2", "10.1038/s41592-019-0686-2", "10.25080/Majora-92bf1922-00a", "pedregosa2011", "10.1109/MCSE.2007.55")


def record(key: str) -> dict | None:
    return RECORDS.get(key) or RECORDS_NO_DOI.get(key)


def cite(key: str, *, year: int | None = None) -> tuple[str, str]:
    """EN: (formatted reference without link, link URL). Vancouver-like: Authors. Title. Journal. Year;Volume:Pages."""
    r = record(key)
    if r is None:
        raise KeyError(key)
    y = year or r["year"]
    vol = (f";{r['volume']}" if r.get("volume") else "") + (f"({r['issue']})" if r.get("issue") else "")
    pages = f":{r['pages']}" if r.get("pages") else ""
    txt = f"{r['authors'].rstrip('.')}. {r['title']}. {r['journal']}. {y}{vol}{pages}."
    url = r.get("url") or f"https://doi.org/{key}"
    return txt, url


def bia_references(entries: list, *, proposed_text: str = "proposed by the researcher, not published") -> list[tuple[str, str, str]]:
    """
    EN: one line per distinct source among the catalogue entries evaluated in the run: (formatted reference, url, ids).
        Year and authors come from the catalogue (the curated precedence record); title and journal from the verified
        record when the DOI is known, otherwise the catalogue authors and year alone. Sorted by year, then id.
    """
    by_src: dict[str, list] = {}
    for e in entries:
        by_src.setdefault(f"proposed:{e.id}" if getattr(e, "proposed", False) else (e.doi or f"nodoi:{e.id}"), []).append(e)
    out = []
    for src, es in by_src.items():
        es = sorted(es, key=lambda e: e.id); e0 = es[0]
        ids = ", ".join(e.label for e in es)
        r = record(src) if not src.startswith(("nodoi:", "proposed:")) else None
        if src.startswith("proposed:"):
            txt, url = f"{e0.authors}. {e0.label}. {proposed_text}.", ""
        elif r is not None:
            txt, url = cite(src, year=e0.year)
        else:
            txt, url = f"{e0.authors}. {e0.year}." + (f" doi:{e0.doi}." if e0.doi else ""), (f"https://doi.org/{e0.doi}" if e0.doi else "")
        out.append((txt, url, ids, e0.year))
    out.sort(key=lambda x: (x[3], x[2]))
    return [(a, b, c) for a, b, c, _ in out]

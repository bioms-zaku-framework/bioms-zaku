"""
EN: Migrate the legacy catalog (catalogo/metodos_bia.json, 39 records) to the v1 contract (31 entries). Deterministic; nothing invented:
    unknown metadata -> null; sex codings marked 'presumed/verify' in the source lower confidence and are copied to notes.
ES: Migra el catálogo antiguo (39 registros) al contrato v1 (31 entradas). Determinista; nada inventado.
PT: Migra o catálogo antigo (39 registros) para o contrato v1 (31 entradas). Determinístico; nada inventado.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Desktop/bioms_2/catalogo/metodos_bia.json"
DST = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[1] / "data" / "catalog_v1.json"
VERIFIED_ON = "2026-09-08"
BY = "TM"

SOURCE_MAP = {  # EN: legacy verificacao.equacao -> (formula_source, confidence)
    "pdf_lido": ("pdf_table", "high"), "pdf_lido_tabela2": ("pdf_table", "high"), "pdf_lido_tabela4": ("pdf_table", "high"),
    "pdf_lido_tabela5": ("pdf_table", "high"), "pdf_lido_tabela5; sinal do intercepto confirmado nos bytes": ("pdf_table", "high"),
    "pmc_texto": ("pmc_text", "high"), "resumo": ("abstract", "medium"), "resumo_pubmed": ("abstract", "medium"),
    "revisao": ("review_table", "low"), "kyle2004_tabela1; sinais inferidos": ("review_table", "low"),
    "kyle2004_tabela3; sinais inferidos": ("review_table", "low"),
    "gray1989_tabela2; intercepto conferir em Segal Tabela 3": ("review_table", "low"),
    "pagina_scielo; conferir no PDF": ("abstract", "medium"),
    "pdf_lido_tabela5: coeficientes nao publicados": ("pdf_table", "high"),
}
SEX = {"sexo": {"male": 1, "female": 0}}
NULLV = {"age": None, "bmi": None, "sex": None, "population": None}


def prov(v: dict, detail: str, extra_note: str | None = None) -> dict:
    src, conf = SOURCE_MAP[v["equacao"]]
    return {"formula_source": src, "source_detail": detail, "verified_by": BY, "verified_on": VERIFIED_ON, "confidence": conf}


def fix_expr(x: str) -> str:
    return x.replace("H_cm", "H")


def main() -> None:
    old = json.loads(SRC.read_text(encoding="utf-8"))
    eq = {e["id"]: e for e in old["equacoes"]}
    ix = {i["id"]: i for i in old["indices"]}
    entries: list[dict] = []

    # ------------------------------------------------------------------ indices (8)
    def idx(i, label, target, form, vector, expr, extra_inputs=(), vector_tol=1e-6, notes=None, freq=50):
        o = ix[i]
        d = {"id": i if i not in ("II", "PhA", "R_H", "Xc_H") else {"II": "Lukaski1985_II", "PhA": "Baumgartner1988_PhA", "R_H": "Piccoli1994_RH", "Xc_H": "Piccoli1994_XcH"}[i],
             "label": label, "authors": o["autor"], "year": o["ano"], "doi": o["doi"], "kind": "index", "target": target,
             "form": form, "frequency_khz": freq, "expr": expr, "validity": dict(NULLV),
             "provenance": prov(o["verificacao"], "index definition")}
        if vector is not None:
            d["vector"] = vector; d["vector_tol"] = vector_tol
        if extra_inputs:
            d["extra_inputs"] = list(extra_inputs)
        if notes:
            d["notes"] = notes
        return d

    entries.append(idx("II", "II h²/R (Lukaski 1985)", "FFM/TBW", "monomial", {"R": -1, "Xc": 0, "H": 2, "W": 0}, "H**2 / R"))
    entries.append(idx("PhA", "PhA (Baumgartner 1988)", "cell integrity", "monomial", {"R": -1, "Xc": 1, "H": 0, "W": 0},
                       "atan(Xc / R) * 180 / pi", vector_tol=0.03, notes="Monomial only approximately: atan(x) ≈ x for small phase angles; vector_tol relaxed accordingly."))
    entries.append(idx("R_H", "R/H (Piccoli 1994)", "hydration", "monomial", {"R": 1, "Xc": 0, "H": -1, "W": 0}, "R / H_m"))
    entries.append(idx("Xc_H", "Xc/H (Piccoli 1994)", "cell mass", "monomial", {"R": 0, "Xc": 1, "H": -1, "W": 0}, "Xc / H_m"))
    A = "(0.45*(C_arm/100)**2/(4*pi) + 0.10*(C_waist/100)**2/(4*pi) + 0.45*(C_calf/100)**2/(4*pi))"
    entries.append({**idx("Rsp", "Rsp (Marini/Buffa 2013)", "%FM", "composite", None, f"R * {A} / H_m", extra_inputs=("C_arm", "C_waist", "C_calf")),
                    "notes": "Specific BIVA: A = 0.45·arm area + 0.10·waist area + 0.45·calf area (m²), area = C²/4π with C in cm; L = height (m). Requires circumferences C_arm, C_waist, C_calf (cm)."})
    entries.append({**idx("Xcsp", "Xcsp (Marini/Buffa 2013)", "ECW/ICW", "composite", None, f"Xc * {A} / H_m", extra_inputs=("C_arm", "C_waist", "C_calf")),
                    "notes": "Specific BIVA reactance; see Rsp."})
    entries.append(idx("LMI", "LMI (Levi Micheli 2022)", "muscle", "monomial", {"R": -2, "Xc": 1, "H": 1, "W": 0}, "PhA * H / R", vector_tol=0.03,
                       notes="vector assumes PhA ≈ Xc/R (linearised atan); vector_tol relaxed accordingly."))
    entries[-1]["validity"] = {"age": None, "bmi": None, "sex": "male", "population": "footballers"}
    entries.append(idx("IR", "Impedance ratio Z200/Z5 (Lukaski 2017)", "ECW/TBW", "monomial", {"Z200": 1, "Z5": -1}, "Z200 / Z5",
                       extra_inputs=("Z200", "Z5"), notes="Multi-frequency; requires impedance at 200 and 5 kHz mapped as variables Z200, Z5.", freq=[5, 200]))

    # ------------------------------------------------------------------ equations (31 records -> 23 entries)
    def base(e_id, label, target, form="composite", detail="equation", freq=50, validity=None, coding=None, extra=(), notes=None):
        e = eq[e_id]
        d = {"id": e_id, "label": label, "authors": e["autor"], "year": e["ano"], "doi": e.get("doi"), "kind": "equation",
             "target": target, "form": form, "frequency_khz": freq, "validity": validity or dict(NULLV),
             "provenance": prov(e["verificacao"], detail)}
        if e.get("pmid"): d["pmid"] = e["pmid"]
        for k_old, k_new in (("n", "n"), ("r2", "r2"), ("see", "see")):
            if e.get(k_old) is not None: d[k_new] = e[k_old]
        if coding: d["group_coding"] = coding
        if extra: d["extra_inputs"] = list(extra)
        if notes: d["notes"] = notes
        return d

    def single(e_id, label, target, **kw):
        d = base(e_id, label, target, **kw); d["expr"] = fix_expr(eq[e_id]["expr"]); return d

    def by_sex(new_id, m_id, f_id, label, target, **kw):
        d = base(m_id, label, target, **kw); d["id"] = new_id
        d["group_coding"] = SEX
        d["expr_by_group"] = {"sexo": {"1": fix_expr(eq[m_id]["expr"]), "0": fix_expr(eq[f_id]["expr"])}}
        return d

    entries.append(single("Lukaski1986_FFM", "Lukaski 1986 [FFM]", "FFM", detail="Table 4"))
    entries.append(single("Kushner1986_TBW", "Kushner & Schoeller 1986 [TBW]", "TBW", detail="Table 4, eq. 2"))
    seg = by_sex("Segal1988_gen_LBM", "Segal1988_gen_M", "Segal1988_gen_F", "Segal 1988 generalised [LBM]", "LBM",
                 detail="Gray 1989 Table 2 (intercepts to be verified in Segal 1988 Table 3)", extra=("idade",),
                 validity={"age": None, "bmi": None, "sex": "both", "population": "adults, 4 laboratories (n=1567)"},
                 notes="Intercepts transcribed from Gray 1989 Table 2; verify against Segal 1988 Table 3.")
    entries.append(seg)
    segsp = base("Segal1988_M_lean", "Segal 1988 fat-specific [LBM]", "LBM", detail="Table 4", extra=("idade",),
                 validity={"age": None, "bmi": None, "sex": "both", "population": "adults, 4 laboratories (n=1567)"},
                 notes="Branch by fat_class must be built from sex and an anthropometric or BIA-only fatness proxy (e.g. BMI); NEVER from the reference criterion (leakage).")
    segsp["id"] = "Segal1988_spec_LBM"
    segsp["group_coding"] = {"fat_class": {"M_lean": 1, "M_obese": 2, "F_lean": 3, "F_obese": 4}}
    segsp["expr_by_group"] = {"fat_class": {"1": fix_expr(eq["Segal1988_M_lean"]["expr"]), "2": fix_expr(eq["Segal1988_M_obese"]["expr"]),
                                            "3": fix_expr(eq["Segal1988_F_lean"]["expr"]), "4": fix_expr(eq["Segal1988_F_obese"]["expr"])}}
    entries.append(segsp)
    entries.append(by_sex("Gray1989_FFM", "Gray1989_M", "Gray1989_F", "Gray 1989 [FFM]", "FFM", detail="Table 2", extra=("idade",)))
    entries.append(single("Heitmann1990_FFM", "Heitmann 1990 [FFM]", "FFM", detail="Kyle 2004 Table 1 (signs inferred; original PDF not read)",
                          coding=SEX, extra=("idade",), validity={"age": [35, 65], "bmi": None, "sex": "both", "population": "Danish adults"},
                          notes="Sex coding unverified (assumed male=1). Original PDF not consulted."))
    entries.append(single("Heitmann1990_TBW", "Heitmann 1990 [TBW]", "TBW", detail="Kyle 2004 Table 3 (signs inferred; original PDF not read)",
                          coding=SEX, validity={"age": [35, 65], "bmi": None, "sex": "both", "population": "Danish adults"},
                          notes="Transcription judged invalid in the 2026-09-08 audit; excluded from analyses until the original is read."))
    entries.append(single("Deurenberg1991_FFM", "Deurenberg 1991 [FFM]", "FFM", detail="PubMed abstract", coding=SEX, extra=("idade",),
                          validity={"age": [16, None], "bmi": None, "sex": "both", "population": "adults ≥16 y (n=661)"}))
    entries.append(single("Houtkooper1992_FFM", "Houtkooper 1992 [FFM]", "FFM", detail="PubMed abstract",
                          validity={"age": [10, 19], "bmi": None, "sex": "both", "population": "youths 10–19 y"}))
    entries.append(single("Kyle2001_FFM", "Kyle 2001 [FFM]", "FFM", detail="PubMed abstract", coding=SEX,
                          validity={"age": [20, 94], "bmi": None, "sex": "both", "population": "adults 20–94 y"}))
    entries.append(by_sex("Sun2003_FFM", "Sun2003_FFM_M", "Sun2003_FFM_F", "Sun 2003 [FFM]", "FFM", detail="Table 5"))
    entries.append(by_sex("Sun2003_TBW", "Sun2003_TBW_M", "Sun2003_TBW_F", "Sun 2003 [TBW]", "TBW", detail="Table 5"))
    entries.append(single("Macias2007_FFM", "Macias 2007 [FFM]", "FFM", detail="PubMed abstract", extra=("idade",)))
    sch = single("Schifferli2011_FFM", "Schifferli 2011 [FFM]", "FFM", detail="Tabla 3 (2011); numeric example from Tabla 2 (2020)", coding=SEX,
                 validity={"age": [18, 64], "bmi": [18.5, 34.8], "sex": "both", "population": "Chilean adults"})
    sch["device"] = "Biodynamics 310"; sch["reference_method"] = "DXA Lunar DPX-L"
    sch["check_example"] = {"inputs": {"sexo": 0, "W": 63.4, "H": 162, "R": 513}, "expected": 44.45, "tol": 0.15}
    sch["notes"] = "check_example: the paper computes IR rounded to 51.2 cm²/Ω; exact IR gives 44.35 kg (tol 0.15 covers the rounding)."
    entries.append(sch)
    sch20 = single("Schifferli2020_FFM_aj", "Schifferli 2020 [FFM adj]", "FFM", detail="Tabla 2", coding=SEX,
                   validity={"age": [18, 65], "bmi": [18.9, 34.8], "sex": "both", "population": "Chilean adults"})
    sch20["id"] = "Schifferli2020_FFM_adj"; sch20["identity_of"] = "Schifferli2011_FFM"; sch20["device"] = "Bodystat QuadScan 4000"; sch20["reference_method"] = "DXA Lunar Prodigy"
    sch20["check_example"] = {"inputs": {"sexo": 0, "W": 63.4, "H": 162, "R": 513}, "expected": 37.9, "tol": 0.15}
    entries.append(sch20)
    entries.append(single("Janssen2000_SMM", "Janssen 2000 [SMM]", "SMM", detail="PubMed abstract", coding=SEX, extra=("idade",)))
    entries.append(single("Kyle2003_ASMM", "Kyle 2003 [ASMM]", "ASMM", detail="PubMed abstract", coding=SEX, extra=("idade",)))
    lima = single("Lima2008_SMM", "Lima 2008 [SMM]", "SMM", detail="SciELO page (verify in PDF)", extra=("idade",),
                  validity={"age": [60, None], "bmi": None, "sex": "male", "population": "elderly Brazilian men (n=60)"})
    lima["doi"] = "10.37527/2008.58.4.010"   # EN: DOI registered retroactively by ALAN (Crossref, checked 2026-09-10); article is vol. 58 no. 4, 2008
    lima["authors"] = "Augustemak de Lima LR, Rech CR, Petroski EL"
    entries.append(lima)
    entries.append(single("Sergi2015_ASMM", "Sergi 2015 [ASMM]", "ASMM", detail="PubMed abstract", coding=SEX,
                          notes="Sex coding presumed male=1; verify in full text."))
    entries.append(single("Scafoglieri2017_ALM", "Scafoglieri 2017 [ALM]", "ALM", detail="PubMed abstract", coding=SEX,
                          notes="Sex coding to be verified (negative sex coefficient)."))
    yam = by_sex("Yamada2017_ALM", "Yamada2017_ALM_M", "Yamada2017_ALM_F", "Yamada 2017 [ALM]", "ALM", detail="PMC text",
                 extra=("Z5", "Z50", "Z250"), freq=[5, 50, 250], notes="Multi-frequency; requires impedance at 5, 50 and 250 kHz mapped as variables Z5, Z50, Z250.")
    entries.append(yam)
    bw = base("BosyWestphal2017_SMM", "Bosy-Westphal 2017 [SMM]", "SMM", form="closed", detail="Table 5: coefficients not published",
              notes="Closed method (manufacturer); listed, not evaluated.")
    entries.append(bw)
    entries.append(single("Campa2026_SMM", "Campa 2026 [SMM]", "SMM", detail="PubMed abstract", coding=SEX, extra=("idade",),
                          notes="Sex coding presumed male=1; verify in full text."))

    # EN: lower confidence where the legacy notes say 'presumed'/'verify' sex coding.
    for d in entries:
        e = eq.get(d["id"])
        sc = (e or {}).get("sex_coding", "") or ""
        if any(w in sc.upper() for w in ("PRESUMIDO", "CONFERIR")) and d["provenance"]["confidence"] == "high":
            d["provenance"]["confidence"] = "medium"

    out = {"catalog_version": "1.0.0",
           "conventions": {"units": {"R": "ohm", "Xc": "ohm", "H": "cm", "W": "kg", "PhA": "deg", "II": "cm2/ohm", "Z": "ohm"},
                           "frequency_khz_default": 50,
                           "extra_variables": ["Z5", "Z50", "Z200", "Z250", "C_arm", "C_waist", "C_calf"],
                           "plausible": {"R": [200, 1200], "Xc": [10, 150], "H": [100, 230], "W": [25, 250]},
                           "groups": {"sexo": "male=1, female=0", "fat_class": "M_lean=1, M_obese=2, F_lean=3, F_obese=4 — from sex and an anthropometric/BIA-only proxy, never from the reference criterion", "idade": "years"}},
           "entries": entries}
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"legacy records: {len(old['indices']) + len(old['equacoes'])} -> entries: {len(entries)} -> {DST}")


if __name__ == "__main__":
    main()

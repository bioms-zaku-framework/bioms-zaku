"""
EN: Figures (CONTRATOS.md §4.4, revised after inspection on 2026-09-10). Generated ONLY from the output tables.
    Design rules (dataviz method): the reader's job picks the form; ≤ 2 categorical hues (validated: blue #2a78d6 =
    specific, orange #eb6834 = measures control); grey = de-emphasis (inconclusive); identity = marker shape + label,
    never a colour; NOT CURATED (§2.1) = hollow marker / *; one hue light→dark for magnitude; blue/orange + grey midpoint
    for polarity; hairline grid; direct labels selectively; no randomness.
ES: Figuras generadas solo desde las tablas de salida; reglas de diseño arriba.
PT: Figuras geradas só a partir das tabelas de saída; regras de desenho acima.

Set / Conjunto:
  board              — the signature: one row per method (ordered by precedence), three aligned panels
                       [originality | specificity with CI | utility with CI]; replaces quadrant + screening map
  exponents          — heatmap of exponent vectors (rows = methods, columns = variables), diverging colour
  predicted_observed — Σ-predicted vs observed Pearson-of-logs, top gaps labelled
  lineage            — precedence lanes: each root (earliest original) and the methods redundant with it
  sigma_transfer     — heatmap of median |predicted − observed| by (Σ source, observed stratum)
  combination_gain   — gain from adding an index vs predicted orthogonality
  compass            — exponent arrows; only drawn when ≤ 10 methods (teaching figure)
"""
from __future__ import annotations

from pathlib import Path

import re
import textwrap

import numpy as np
import pandas as pd

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
except ImportError as e:  # pragma: no cover
    raise ImportError("plots require matplotlib (pip install 'bioms-zaku[plots]')") from e

C = {"specific": "#22c55e", "control": "#9333ea", "muted": "#9a9893", "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e6e5e1", "surface": "#fcfcfb"}

# EN: user style (from config["figures"]); applied by `apply_style` before drawing. ES/PT: estilo do usuário.
STYLE = {"title": None, "subtitle": None, "language": "en", "labels": "full", "font": "DejaVu Sans", "font_size": 8.5,
         "dpi": 300, "formats": ["png", "pdf"], "footer": True, "captions": False}

# EN: axis/legend texts in three languages. ES/PT: textos dos eixos e legendas.
I18N = {
    "it": {"des": "△ progettato su questi dati (partizione di progetto), verificato sull'altra", "prop": "◇ proposto dal ricercatore, non pubblicato", "board": "Quadro dei verdetti", "stratum": "strato", "target": "target", "control": "controllo", "orig": "originalità\n1 − max |Spearman| con un metodo precedente (log)",
           "spec": "specificità\n{m}(target) − {m}(controllo), intervallo 95%", "util": "valore aggiunto oltre le covariate\nΔ{m}, intervallo 95%",
           "no_util": "utilità non calcolata\n(nessuna covariata dichiarata)", "identity": "identità", "oov": "† = applicato per lo più fuori dalla validità dichiarata",
           "exp_title": "Vettori degli esponenti: come ogni indice dipende da R, Xc, H e W", "po_default": "Correlazione prevista dall'algebra vs misurata nei dati", "fixed": "fisso", "fit": "R² dell'adattamento", "gap": "scarto",
           "po_x": "prevista da Σ (Pearson dei log)", "po_y": "osservata", "po_title": "{s}: {n} coppie, mediana |scarto| {g:.3f}", "footer": "BioMS Zaku {v} · preset {p} · {d} · semi cv={c} bootstrap={b}"},
    "en": {"des": "△ designed on this data (design partition), audited on the other", "prop": "◇ proposed by the researcher, not published", "board": "Verdict board", "stratum": "stratum", "target": "target", "control": "control", "orig": "originality\n1 − max |Spearman| with an earlier method (log)",
           "spec": "specificity\n{m}(target) − {m}(control), 95% interval", "util": "added value over covariates\nΔ{m}, 95% interval",
           "no_util": "utility not run\n(no covariates declared)", "identity": "identity", "oov": "† = applied mostly outside declared validity",
           "exp_title": "Exponent vectors: how each index depends on R, Xc, H and W", "po_default": "Correlation predicted by the algebra vs measured in the data", "fixed": "fixed", "fit": "fit R²", "gap": "gap",
           "po_x": "predicted from Σ (Pearson of logs)", "po_y": "observed", "po_title": "{s}: {n} pairs, median |gap| {g:.3f}", "footer": "BioMS Zaku {v} · preset {p} · {d} · seeds cv={c} bootstrap={b}"},
    "es": {"des": "△ diseñado en estos datos (partición de diseño), auditado en la otra", "prop": "◇ propuesto por el investigador, no publicado", "board": "Cuadro de veredictos", "stratum": "estrato", "target": "objetivo", "control": "control", "orig": "originalidad\n1 − máx |Spearman| con un método anterior (log)",
           "spec": "especificidad\n{m}(objetivo) − {m}(control), intervalo 95%", "util": "valor agregado sobre covariables\nΔ{m}, intervalo 95%",
           "no_util": "utilidad no calculada\n(sin covariables)", "identity": "identidad", "oov": "† = aplicado mayormente fuera de la validez declarada",
           "exp_title": "Vectores de exponentes: cómo cada índice depende de R, Xc, H y W", "po_default": "Correlación predicha por el álgebra vs medida en los datos", "fixed": "fijo", "fit": "ajuste R²", "gap": "brecha",
           "po_x": "predicho desde Σ (Pearson de logs)", "po_y": "observado", "po_title": "{s}: {n} pares, mediana |brecha| {g:.3f}", "footer": "BioMS Zaku {v} · preset {p} · {d} · semillas cv={c} bootstrap={b}"},
    "pt": {"des": "△ desenhado nestes dados (partição de desenho), auditado na outra", "prop": "◇ proposto pelo pesquisador, não publicado", "board": "Quadro de vereditos", "stratum": "estrato", "target": "alvo", "control": "controle", "orig": "originalidade\n1 − máx |Spearman| com um método anterior (log)",
           "spec": "especificidade\n{m}(alvo) − {m}(controle), intervalo 95%", "util": "valor acrescentado sobre covariáveis\nΔ{m}, intervalo 95%",
           "no_util": "utilidade não calculada\n(sem covariáveis)", "identity": "identidade", "oov": "† = aplicado majoritariamente fora da validade declarada",
           "exp_title": "Vetores de expoentes: como cada índice depende de R, Xc, H e W", "po_default": "Correlação prevista pela álgebra vs medida nos dados", "fixed": "fixo", "fit": "ajuste R²", "gap": "lacuna",
           "po_x": "previsto por Σ (Pearson dos logs)", "po_y": "observado", "po_title": "{s}: {n} pares, mediana |lacuna| {g:.3f}", "footer": "BioMS Zaku {v} · preset {p} · {d} · sementes cv={c} bootstrap={b}"},
}


SC = {
    "it": {"des": "△ progettato su questi dati (partizione di progetto), verificato sull'altra", "prop": "◇ proposto dal ricercatore, non pubblicato", "title": "Verdetti", "col_o": "originalità", "col_s": "specificità", "col_u": "valore aggiunto", "method": "metodo",
           "original": "Originale", "repeats": "Ripete", "identical": "Identico a", "specific": "Specifico", "tracks": "Segue il controllo",
           "inconc": "Inconclusivo", "both": "Misura entrambi", "neither": "Nessun segnale", "adds": "Aggiunge valore", "noadd": "Nessun valore aggiunto", "notest": "Non testato", "over": "oltre {c}", "coupled": "‡ target e controllo accoppiati nello spazio misurato",
           "leg1": "Originalità: un indice è originale quando nessun metodo precedente ordina le persone quasi allo stesso modo (|Spearman| < {thr}); altrimenti ripete quel metodo.",
           "leg2": "Specificità (controllo condizionale): barra verde = guadagno in {m} per il target ({t}) quando l'indice si aggiunge al controllo ({c}); barra viola = guadagno per il controllo quando si aggiunge al target. Specifico = verde presente, viola assente; segue il controllo = l'inverso; misura entrambi = entrambe presenti; nessun segnale = nessuna. Numero = barra verde con intervallo bootstrap 95%; margine {mg}.",
           "leg3": "Valore aggiunto: guadagno in {m} quando l'indice si aggiunge a {cov}. † applicato fuori dalla validità dichiarata dal metodo · * formula non curata (fonte primaria senza lettura critica).",
           "po_x": "correlazione prevista dall'algebra (da Σ)", "po_y": "correlazione misurata nei dati", "po_note": "punti sulla linea: previsione confermata",
           "exp_read": "esponente positivo: l'indice cresce con la variabile · negativo: decresce · R² dell'adattamento: quanto un'equazione a somma si comporta come un prodotto (fisso = esatto)"},
    "en": {"des": "△ designed on this data (design partition), audited on the other", "prop": "◇ proposed by the researcher, not published", "title": "Verdicts", "col_o": "originality", "col_s": "specificity", "col_u": "added value", "method": "method",
           "original": "Original", "repeats": "Repeats", "identical": "Identical to", "specific": "Specific", "tracks": "Tracks control",
           "inconc": "Inconclusive", "both": "Measures both", "neither": "No signal", "adds": "Adds value", "noadd": "No added value", "notest": "Not tested", "over": "over {c}", "coupled": "‡ target and control coupled in the measured space",
           "leg1": "Originality: an index is original when no earlier method orders people almost identically (|Spearman| < {thr}); otherwise it repeats that method.",
           "leg2": "Specificity (conditional control): green bar = gain in {m} for the target ({t}) when the index is added to the control ({c}); violet bar = gain for the control when added to the target. Specific = green present, violet absent; tracks control = the reverse; measures both = both present; no signal = neither. Number = green bar with 95% bootstrap interval; margin {mg}.",
           "leg3": "Added value: gain in {m} when the index is added to {cov}. † applied outside the method's declared validity · * formula not curated (primary source not critically read).",
           "po_x": "correlation predicted by the algebra (from Σ)", "po_y": "correlation measured in the data", "po_note": "points on the line: prediction confirmed",
           "exp_read": "positive exponent: the index grows with the variable · negative: it decreases · fit R²: how closely a sum-type equation behaves as a product (fixed = exact)"},
    "es": {"des": "△ diseñado en estos datos (partición de diseño), auditado en la otra", "prop": "◇ propuesto por el investigador, no publicado", "title": "Veredictos", "col_o": "originalidad", "col_s": "especificidad", "col_u": "valor agregado", "method": "método",
           "original": "Original", "repeats": "Repite", "identical": "Idéntico a", "specific": "Específico", "tracks": "Sigue control",
           "inconc": "No concluyente", "both": "Mide los dos", "neither": "Sin señal", "adds": "Agrega valor", "noadd": "No agrega valor", "notest": "No evaluado", "over": "sobre {c}", "coupled": "‡ objetivo y control acoplados en el espacio medido",
           "leg1": "Originalidad: un índice es original cuando ningún método anterior ordena a las personas casi igual (|Spearman| < {thr}); si no, repite ese método.",
           "leg2": "Especificidad (control condicional): barra verde = ganancia en {m} para el objetivo ({t}) al añadir el índice al control ({c}); barra violeta = ganancia para el control al añadirlo al objetivo. Específico = verde presente, violeta ausente; sigue control = lo inverso; mide los dos = ambas presentes; sin señal = ninguna. Número = barra verde con intervalo bootstrap 95%; margen {mg}.",
           "leg3": "Valor agregado: ganancia en {m} al añadir el índice a {cov}. † aplicado fuera de la validez declarada · * fórmula no curada (fuente primaria sin lectura crítica).",
           "po_x": "correlación predicha por el álgebra (desde Σ)", "po_y": "correlación medida en los datos", "po_note": "puntos sobre la línea: predicción confirmada",
           "exp_read": "exponente positivo: el índice crece con la variable · negativo: decrece · fit R²: cuán bien una ecuación aditiva se comporta como producto (fijo = exacto)"},
    "pt": {"des": "△ desenhado nestes dados (partição de desenho), auditado na outra", "prop": "◇ proposto pelo pesquisador, não publicado", "title": "Vereditos", "col_o": "originalidade", "col_s": "especificidade", "col_u": "valor acrescentado", "method": "método",
           "original": "Original", "repeats": "Repete", "identical": "Idêntico a", "specific": "Específico", "tracks": "Acompanha ctrl",
           "inconc": "Inconclusivo", "both": "Mede os dois", "neither": "Sem sinal", "adds": "Acrescenta valor", "noadd": "Não acrescenta", "notest": "Não avaliado", "over": "sobre {c}", "coupled": "‡ alvo e controle acoplados no espaço medido",
           "leg1": "Originalidade: um índice é original quando nenhum método anterior ordena as pessoas quase igual (|Spearman| < {thr}); senão, repete esse método.",
           "leg2": "Especificidade (controle condicional): barra verde = ganho em {m} para o alvo ({t}) ao juntar o índice ao controle ({c}); barra violeta = ganho para o controle ao juntá-lo ao alvo. Específico = verde presente, violeta ausente; acompanha controle = o inverso; mede os dois = as duas presentes; sem sinal = nenhuma. Número = barra verde com intervalo bootstrap 95%; margem {mg}.",
           "leg3": "Valor acrescentado: ganho em {m} ao juntar o índice a {cov}. † aplicado fora da validade declarada · * fórmula não curada (fonte primária sem leitura crítica).",
           "po_x": "correlação prevista pela álgebra (a partir de Σ)", "po_y": "correlação medida nos dados", "po_note": "pontos sobre a linha: previsão confirmada",
           "exp_read": "expoente positivo: o índice cresce com a variável · negativo: decresce · fit R²: o quanto uma equação de soma se comporta como produto (fixo = exato)"},
}


def T(key: str, **kw) -> str:
    return I18N.get(STYLE["language"], I18N["en"])[key].format(**kw)


def S(key: str, **kw) -> str:
    return SC.get(STYLE["language"], SC["en"])[key].format(**kw)


# EN: named palettes. "default" = validated blue/orange (CONTRATOS §4.4). "brand" = biomspro.com violet/green — validated
#     for CVD (ΔE 33.8 deutan, 46.3 normal); the green sits below 3:1 contrast on light surfaces, which the direct labels
#     on every mark compensate (relief rule). ES/PT: paletas nomeadas; "brand" = identidade BioMS.
PALETTES = {"default": {"specific": "#22c55e", "control": "#9333ea", "muted": "#9a9893"},   # EN: logo colours (green specific, violet control), CVD-validated
            "brand": {"specific": "#22c55e", "control": "#9333ea", "muted": "#9a9893"},
            "classic": {"specific": "#2a78d6", "control": "#eb6834", "muted": "#9a9893"}}
BRAND = {"violet": "#9333ea", "green": "#22c55e", "violet_light": "#c084fc", "green_light": "#4ade80", "ink": "#1d1d1f"}


def apply_style(figcfg: dict | None) -> None:
    """EN: merge user figure settings and push font/palette into matplotlib. `palette` may be a name or a dict of hex."""
    global DIV
    figcfg = figcfg or {}
    for k in STYLE:
        if figcfg.get(k) is not None:
            STYLE[k] = figcfg[k]
    pal = figcfg.get("palette")
    if isinstance(pal, str):
        if pal not in PALETTES:
            raise ValueError(f"figures.palette must be one of {sorted(PALETTES)} or a dict of hex colours")
        pal = PALETTES[pal]
    for k, v in (pal or {}).items():
        if k in C and isinstance(v, str) and v.startswith("#"):
            C[k] = v
    DIV = LinearSegmentedColormap.from_list("div", [C["control"], "#f0f0ee", C["specific"]])
    plt.rcParams.update({"font.family": STYLE["font"], "font.size": STYLE["font_size"]})


def _margins(meta: dict | None, caption: bool) -> tuple[float, float]:
    """EN: vertical space (inches) reserved above the axes for title/subtitle and below them for caption/footer.
    ES: espacio vertical (pulgadas) reservado sobre los ejes (título/subtítulo) y debajo (leyenda/pie).
    PT: espaço vertical (polegadas) reservado acima dos eixos (título/subtítulo) e abaixo (legenda/rodapé).
    Computed before the figure exists so the figure height can include it; drawn afterwards by `_frame`."""
    caption = bool(caption) and bool(STYLE["captions"])
    head = 0.12 + 0.26 + (0.22 if STYLE["subtitle"] else 0.0) + 0.10
    foot = 0.08 + (0.22 if (STYLE["footer"] and meta) else 0.0) + (0.22 if caption else 0.0)
    return head, foot


def _frame(fig, default_title: str, meta: dict | None, caption: str | None = None) -> None:
    """EN: draw title, subtitle, caption and footer at fixed inch offsets from the figure edges (never over the axes).
    PT: desenha título, subtítulo, legenda e rodapé a distâncias fixas em polegadas das bordas (nunca sobre os eixos)."""
    H = fig.get_size_inches()[1]
    y = 0.12
    fig.text(0.01, 1 - y / H, STYLE["title"] or default_title, fontsize=10.5, color=C["ink"], ha="left", va="top"); y += 0.26
    if STYLE["subtitle"]:
        fig.text(0.01, 1 - y / H, STYLE["subtitle"], fontsize=8.5, color=C["ink2"], ha="left", va="top")
    b = 0.06
    if STYLE["footer"] and meta:
        fig.text(0.01, b / H, T("footer", v=meta.get("version", ""), p=meta.get("preset", ""), d=meta.get("date", ""), c=meta.get("seed_cv", ""), b=meta.get("seed_boot", "")),
                 fontsize=6, color=C["ink2"], ha="left", va="bottom"); b += 0.22
    if caption and STYLE["captions"]:
        fig.text(0.01, b / H, caption, fontsize=6.8, color=C["ink2"], ha="left", va="bottom")


def _footer(fig, meta: dict | None) -> None:
    if not STYLE["footer"] or not meta:
        return
    fig.text(0.01, 0.04 / fig.get_size_inches()[1], T("footer", v=meta.get("version", ""), p=meta.get("preset", ""), d=meta.get("date", ""), c=meta.get("seed_cv", ""), b=meta.get("seed_boot", "")),
             fontsize=6, color=C["ink2"], ha="left", va="bottom")


def _title(fig, default: str) -> None:
    t = STYLE["title"] or default
    H = fig.get_size_inches()[1]
    fig.text(0.01, 1 - 0.18 / H, t, fontsize=10.5, color=C["ink"], ha="left", va="top")
    if STYLE["subtitle"]:
        fig.text(0.01, 1 - 0.42 / H, STYLE["subtitle"], fontsize=8.5, color=C["ink2"], ha="left", va="top")


DIV = LinearSegmentedColormap.from_list("div", ["#9333ea", "#f0f0ee", "#22c55e"])
SEQ = LinearSegmentedColormap.from_list("seq", ["#f0f0ee", "#2a78d6"])
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": C["grid"], "axes.labelcolor": C["ink2"], "xtick.color": C["ink2"], "ytick.color": C["ink2"],
                     "grid.color": C["grid"], "grid.linewidth": 0.6, "figure.facecolor": C["surface"], "axes.facecolor": C["surface"]})

# EN: three new/revised official figures for BioMS Zaku — appended to plots.py by the patch script.
# ES/PT: três figuras oficiais novas/revistas — anexadas a plots.py.

# ---------- i18n additions ----------
FIG = {
    "it": {"des": "△ progettato su questi dati (partizione di progetto), verificato sull'altra", "prop": "◇ proposto dal ricercatore, non pubblicato", "tc_title": "Che cosa aggiunge ogni indice: al target oltre il controllo, e al controllo oltre il target", "tc_xbar": "guadagno in {m} fuori campione quando si aggiunge l'indice", "tc_key1": "aggiunge alla previsione del TARGET ({t}) oltre il controllo ({c})", "tc_key2": "aggiunge alla previsione del CONTROLLO ({c}) oltre il target ({t})", "tc_note": "baffi = intervallo bootstrap 95 % (ricampionamenti appaiati) · tratteggiata = margine {mg} · * non curato",
           "lin_title": "Albero genealogico degli indici: chi è venuto prima, chi ripete chi, chi è specifico", "lin_x": "anno di pubblicazione",
           "lin_l1": "Ogni riga inizia con un indice originale (pieno); gli indici successivi che ordinano le persone quasi allo stesso modo (|Spearman| ≥ {thr}) pendono da esso, con la correlazione sul ramo.",
           "lin_l2": "Colore = verdetto di specificità per il target ({t}) rispetto al controllo ({c}): verde specifico · viola segue il controllo · grigio scuro entrambi · grigio chiaro nessun segnale. Bordo vuoto = non curato · † fuori dalla validità dichiarata · ◆ identità.",
           "ex_title": "Vettori degli esponenti e covarianza dei log Σ dello strato", "ex_read": "righe raggruppate per lignaggio (l'originale, poi gli indici ridondanti con esso) · a destra: che cosa dicono gli autori che misura, e R² dell'adattamento quando l'indice non è un prodotto esatto",
           "ex_sigma": "correlazione dei log (Σ)", "fixed": "prodotto esatto", "approx": "≈ prodotto, R² {r:.2f}", "kind": {"lean_mass": "massa magra", "fat_mass": "massa grassa", "body_water": "acqua corporea", "hydration": "idratazione", "cell_mass": "massa cellulare", "other": "altro", None: "—"}},
    "en": {"des": "△ designed on this data (design partition), audited on the other", "prop": "◇ proposed by the researcher, not published", "tc_title": 'What each index adds: to the target beyond the control, and to the control beyond the target', "tc_xbar": 'gain in out-of-sample {m} when the index is added', "tc_key1": 'adds to the prediction of the TARGET ({t}) beyond the control ({c})', "tc_key2": 'adds to the prediction of the CONTROL ({c}) beyond the target ({t})', "tc_note": 'whiskers = 95 % bootstrap interval (paired resamples) · dashed = margin {mg} · * not curated',
           "lin_title": "Family tree of the indices: who came first, who repeats whom, who is specific", "lin_x": "year of publication",
           "lin_l1": "Each row starts with an original index (filled); later indices that order people almost identically (|Spearman| ≥ {thr}) hang from it, with the correlation on the branch.",
           "lin_l2": "Colour = specificity verdict for the target ({t}) against the control ({c}): green specific · violet tracks the control · dark grey both · light grey no signal. Hollow edge = not curated · † outside declared validity · ◆ identity.",
           "ex_title": "Exponent vectors and the log-covariance Σ of the stratum", "ex_read": "rows grouped by lineage (original, then the indices redundant with it) · right: what the authors say it measures, and fit R² when the index is not an exact product",
           "ex_sigma": "correlation of logs (Σ)", "fixed": "exact product", "approx": "≈ product, R² {r:.2f}", "kind": {"lean_mass": "lean mass", "fat_mass": "fat mass", "body_water": "body water", "hydration": "hydration", "cell_mass": "cell mass", "other": "other", None: "—"}},
    "es": {"des": "△ diseñado en estos datos (partición de diseño), auditado en la otra", "prop": "◇ propuesto por el investigador, no publicado", "tc_title": 'Qué añade cada índice: al objetivo más allá del control, y al control más allá del objetivo', "tc_xbar": 'ganancia en {m} fuera de muestra al añadir el índice', "tc_key1": 'añade a la predicción del OBJETIVO ({t}) más allá del control ({c})', "tc_key2": 'añade a la predicción del CONTROL ({c}) más allá del objetivo ({t})', "tc_note": 'bigotes = intervalo bootstrap 95 % (remuestras pareadas) · discontinua = margen {mg} · * no curada',
           "lin_title": "Árbol genealógico de los índices: quién vino primero, quién repite a quién, quién es específico", "lin_x": "año de publicación",
           "lin_l1": "Cada fila empieza con un índice original (relleno); los índices posteriores que ordenan a las personas casi igual (|Spearman| ≥ {thr}) cuelgan de él, con la correlación en la rama.",
           "lin_l2": "Color = veredicto de especificidad para el objetivo ({t}) contra el control ({c}): verde específico · violeta sigue el control · gris oscuro ambos · gris claro sin señal. Borde hueco = no curada · † fuera de la validez · ◆ identidad.",
           "ex_title": "Vectores de exponentes y la covarianza de logs Σ del estrato", "ex_read": "filas agrupadas por linaje (original, luego los índices redundantes con él) · derecha: qué dicen los autores que mide, y R² de ajuste cuando no es un producto exacto",
           "ex_sigma": "correlación de logs (Σ)", "fixed": "producto exacto", "approx": "≈ producto, R² {r:.2f}", "kind": {"lean_mass": "masa magra", "fat_mass": "masa grasa", "body_water": "agua corporal", "hydration": "hidratación", "cell_mass": "masa celular", "other": "otro", None: "—"}},
    "pt": {"des": "△ desenhado nestes dados (partição de desenho), auditado na outra", "prop": "◇ proposto pelo pesquisador, não publicado", "tc_title": 'O que cada índice acrescenta: ao alvo além do controle, e ao controle além do alvo', "tc_xbar": 'ganho em {m} fora da amostra ao juntar o índice', "tc_key1": 'acrescenta à predição do ALVO ({t}) além do controle ({c})', "tc_key2": 'acrescenta à predição do CONTROLE ({c}) além do alvo ({t})', "tc_note": 'bigodes = intervalo bootstrap 95 % (reamostras pareadas) · tracejado = margem {mg} · * não curada',
           "lin_title": "Árvore genealógica dos índices: quem veio antes, quem repete quem, quem é específico", "lin_x": "ano de publicação",
           "lin_l1": "Cada linha começa com um índice original (cheio); os índices posteriores que ordenam as pessoas quase igual (|Spearman| ≥ {thr}) pendem dele, com a correlação no ramo.",
           "lin_l2": "Cor = veredito de especificidade para o alvo ({t}) contra o controle ({c}): verde específico · violeta acompanha o controle · cinza escuro ambos · cinza claro sem sinal. Borda vazada = não curada · † fora da validade · ◆ identidade.",
           "ex_title": "Vetores de expoentes e a covariância dos logs Σ do estrato", "ex_read": "linhas agrupadas por linhagem (original, depois os índices redundantes com ele) · à direita: o que os autores dizem que mede, e R² do ajuste quando não é produto exato",
           "ex_sigma": "correlação dos logs (Σ)", "fixed": "produto exato", "approx": "≈ produto, R² {r:.2f}", "kind": {"lean_mass": "massa magra", "fat_mass": "massa gorda", "body_water": "água corporal", "hydration": "hidratação", "cell_mass": "massa celular", "other": "outro", None: "—"}},
}


def F(key: str, **kw):
    v = FIG.get(STYLE["language"], FIG["en"])[key]
    return v.format(**kw) if isinstance(v, str) else v


def _curated_by_method(alg: pd.DataFrame) -> dict:
    """EN: method_id -> curated (bool). Non-curated methods (§2.1) are drawn hollow and labelled *; they appear only with include: all."""
    a = alg.drop_duplicates("method_id")
    return dict(zip(a.method_id, a["curated"].astype(bool))) if "curated" in a else {m: True for m in a.method_id}


def _proposed_by_method(alg: pd.DataFrame) -> dict:
    """EN: method_id -> proposed (the researcher's own index, v0.9): hollow like non-curated, labelled ◇ instead of *."""
    a = alg.drop_duplicates("method_id")
    return dict(zip(a.method_id, a["proposed"].astype(bool))) if "proposed" in a else {}


def _designed_by_method(alg: pd.DataFrame) -> dict:
    """EN: method_id -> designed on this data (v0.9): labelled △ (fitted on the design partition, audited on the other)."""
    a = alg.drop_duplicates("method_id")
    return dict(zip(a.method_id, a["designed"].astype(bool))) if "designed" in a else {}


def _mark(m, conf: dict, prop: dict, des: dict | None = None) -> str:
    if (des or {}).get(m, False): return "△"
    return "◇" if prop.get(m, False) else ("*" if not conf.get(m, True) else "")


def _curated_by_method_stratum(alg: pd.DataFrame) -> dict:
    return dict(zip(zip(alg.method_id, alg.stratum), alg["curated"].astype(bool))) if "curated" in alg else {k: True for k in zip(alg.method_id, alg.stratum)}


def _short(lab: dict[str, str]) -> dict[str, str]:
    """EN: 'II h²/R (Lukaski 1985)' -> 'II h²/R' ; keeps the method name only."""
    return {k: re.sub(r"\s*\([^)]*\)\s*$", "", v).split(" [")[0].split(", ")[0] for k, v in lab.items()}


def _verdict_colour(v: str) -> str:
    return {"SPECIFIC": C["specific"], "TRACKS_CONTROL": C["control"], "MEASURES_CONTROL": C["control"], "BOTH": C["ink2"]}.get(v, C["muted"])


def _lineages(r: pd.DataFrame, order: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """EN: root of each method by following predecessor/identity links; returns (roots in precedence order, root -> members)."""
    def root(m):
        seen = set()
        while m in r.index and m not in seen:
            seen.add(m)
            nxt = r.loc[m, "identity_of"] if pd.notna(r.loc[m, "identity_of"]) else (r.loc[m, "predecessor_id"] if bool(r.loc[m, "redundant"]) else None)
            if not isinstance(nxt, str):
                return m
            m = nxt
        return m
    lanes: dict[str, list[str]] = {}
    for m in order:
        if m in r.index:
            lanes.setdefault(root(m), []).append(m)
    return [m for m in order if m in lanes], lanes


def _geo_flags(geo: pd.DataFrame | None, stratum: str, target: str) -> tuple[set[str], bool]:
    """EN: (indices flagged PARALLEL_TO_CONTROL, whether target and control are COUPLED) for one stratum × target (v0.6 §3.3)."""
    if geo is None or geo.empty or "flag_parallel_to_control" not in geo:
        return set(), False
    g = geo[(geo.stratum == stratum) & (geo.target == target)]
    return set(g[g.flag_parallel_to_control].method_id), bool(g.flag_coupled_target_control.any())


def target_control(aud: pd.DataFrame, alg: pd.DataFrame, out_dir: Path, primary_target: str, meta: dict | None = None, margin: float = 0.03,
                   geo: pd.DataFrame | None = None) -> None:
    """
    EN: the conditional negative-control figure (v0.5) as PAIRED BARS. One row per index, sorted by S1. Green bar = S1,
        what the index adds to the prediction of the TARGET beyond the control; violet bar = S2, what it adds to the
        prediction of the CONTROL beyond the target. Whiskers = 95 % paired-bootstrap interval; dashed line = margin;
        verdict pill at the end of the row. One panel per stratum. Reads without a legend: long green + short violet =
        specific; the reverse = tracks the control; both long = measures both; both short = no signal.
    PT: controle negativo condicional em barras pareadas — verde = acrescenta ao alvo além do controle; violeta =
        acrescenta ao controle além do alvo.
    """
    if aud.empty or alg.empty or "s1_mean" not in aud:
        return
    from matplotlib.patches import FancyBboxPatch
    a = aud[(aud.target == primary_target) & np.isfinite(aud.s1_mean)]
    if a.empty:
        return
    strata = sorted(a.stratum.unique()); lab = _label(alg); short = _short(lab)
    conf = _curated_by_method(alg); prop = _proposed_by_method(alg); des = _designed_by_method(alg)
    n = int(a.groupby("stratum").size().max()); row_h = 0.44
    head, foot = _margins(meta, caption=True); panel_top, panel_bot = 0.30, 0.45
    if STYLE["captions"]:
        head += 0.24
    H = head + panel_top + row_h * n + panel_bot + foot
    ns = len(strata); panel_w = 2.9
    W = min(10.0, 1.6 + ns * (panel_w + 1.6))
    fig, axes = plt.subplots(1, ns, figsize=(W, H), squeeze=False, gridspec_kw={"wspace": 0.9})
    metric = str(a.metric.iloc[0]).replace("R2", "R²"); control = a.control.iloc[0]
    xmax = float(max(a.s1_hi.max(), a.s2_hi.max(), margin * 2)) * 1.12; xmin = float(min(a.s1_lo.min(), a.s2_lo.min(), 0.0)) - 0.02
    words = {"SPECIFIC": (S("specific"), C["specific"]), "TRACKS_CONTROL": (S("tracks"), C["control"]), "MEASURES_CONTROL": (S("tracks"), C["control"]),
             "BOTH": (S("both"), C["ink2"]), "NEITHER": (S("neither"), C["muted"])}
    for ax, st in zip(axes[0], strata):
        q = a[a.stratum == st].sort_values("s1_mean", ascending=True).reset_index(drop=True)
        par, coupled = _geo_flags(geo, st, primary_target)
        ax.axvline(0, color=C["grid"], lw=1.0, zorder=1); ax.axvline(margin, color=C["ink2"], lw=0.8, ls="--", zorder=1)
        ax.grid(axis="x"); ax.set_axisbelow(True)
        for i, row in q.iterrows():
            y = i; hollow = not conf.get(row.method_id, True)
            # S1 (green) above, S2 (violet) below, within the row
            flagged = row.method_id in par   # EN: v0.6 — index parallel to the control in the measured space: dashed outline
            # EN: the dashed style is set ONLY on flagged bars; a dash pattern with linewidth 0 is rejected by older matplotlib
            edge = dict(edgecolor=C["ink"], linestyle="--", linewidth=0.9) if flagged else dict(edgecolor="none", linewidth=0)
            ax.barh(y + 0.19, row.s1_mean, height=0.34, color=C["specific"], alpha=0.35 if hollow else 0.9, zorder=2, **edge)
            ax.barh(y - 0.19, row.s2_mean, height=0.34, color=C["control"], alpha=0.35 if hollow else 0.9, zorder=2, **edge)
            ax.plot([row.s1_lo, row.s1_hi], [y + 0.19, y + 0.19], color=C["ink"], lw=0.9, zorder=3)
            ax.plot([row.s2_lo, row.s2_hi], [y - 0.19, y - 0.19], color=C["ink"], lw=0.9, zorder=3)
            ax.text(max(row.s1_hi, 0) + 0.006, y + 0.19, f"{row.s1_mean:+.2f}", fontsize=6.2, va="center", color=C["ink2"])
            ax.text(max(row.s2_hi, 0) + 0.006, y - 0.19, f"{row.s2_mean:+.2f}", fontsize=6.2, va="center", color=C["ink2"])
            word, col = words.get(row.verdict, (row.verdict, C["muted"]))
            ax.text(1.02, y, word, transform=ax.get_yaxis_transform(), fontsize=7.2, va="center", ha="left", color="white", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.35,rounding_size=0.8", fc=col, ec="none"))
        ax.set_yticks(range(len(q))); ax.set_yticklabels([short.get(m, m) + _mark(m, conf, prop, des) + (" ‡" if m in par else "") for m in q.method_id], fontsize=7.4)
        ax.set_ylim(-0.6, len(q) - 0.4); ax.set_xlim(xmin, xmax); ax.tick_params(axis="y", length=0)
        ax.set_xlabel(F("tc_xbar", m=metric), fontsize=7.5)
        ax.set_title(f"{T('stratum')} {st}" + (" · " + S("coupled") if coupled else ""), fontsize=9, loc="left")
        for sp in ("left", "top", "right"):
            ax.spines[sp].set_visible(False)
    # in-figure key only when captions are requested (default: the documentation text explains the colours)
    kx = 0.01; ky = 1 - (head - 0.12) / H
    if STYLE["captions"]: fig.patches.append(FancyBboxPatch((kx, ky - 0.006), 0.010, 0.012, boxstyle="square,pad=0", fc=C["specific"], ec="none", transform=fig.transFigure, figure=fig))
    if STYLE["captions"]:
        fig.text(kx + 0.014, ky, F("tc_key1", t=primary_target, c=control), fontsize=7.4, va="center", color=C["ink"])
        fig.patches.append(FancyBboxPatch((kx + 0.42, ky - 0.006), 0.010, 0.012, boxstyle="square,pad=0", fc=C["control"], ec="none", transform=fig.transFigure, figure=fig))
        fig.text(kx + 0.434, ky, F("tc_key2", t=primary_target, c=control), fontsize=7.4, va="center", color=C["ink"])
    _frame(fig, F("tc_title"), meta, caption=F("tc_note", mg=margin) + (" · " + F("prop") if any(prop.values()) else "") + (" · " + F("des") if any(des.values()) else ""))
    fig.subplots_adjust(left=0.17, right=0.87, top=1 - (head + panel_top) / H, bottom=(foot + panel_bot) / H)
    _save(fig, out_dir, "target_control")


def lineage_tree(red: pd.DataFrame, alg: pd.DataFrame, aud: pd.DataFrame, out_dir: Path, primary_target: str, threshold: float = 0.95,
                 meta: dict | None = None) -> None:
    """
    EN: the family tree — one row per original index (filled node at its year); redundant indices hang from it with the
        Spearman correlation on the branch. Node colour = specificity verdict; hollow edge = not curated (primary source not critically read);
        † = outside declared validity; ◆ = identity. One figure per stratum.
    PT: árvore genealógica — uma linha por índice original; redundantes pendem dele com o ρ no ramo; cor = veredito.
    """
    if red.empty or alg.empty:
        return
    A = alg.drop_duplicates("method_id").set_index("method_id"); yr = A.year.to_dict(); lab = _label(alg); short = _short(lab); order = _order(alg)
    conf = _curated_by_method_stratum(alg); prop = _proposed_by_method(alg); des = _designed_by_method(alg)
    oovd = alg.set_index(["method_id", "stratum"]).get("out_of_validity_frac", pd.Series(dtype=float)).to_dict()
    kinds = A.get("target_kind", pd.Series(dtype=object)).to_dict() if "target_kind" in A else {}
    for s in sorted(red.stratum.unique()):
        r = red[red.stratum == s].set_index("method_id")
        v = aud[(aud.stratum == s) & (aud.target == primary_target)].set_index("method_id").verdict.to_dict() if not aud.empty else {}
        control = aud[(aud.stratum == s) & (aud.target == primary_target)].control.iloc[0] if not aud.empty and ((aud.stratum == s) & (aud.target == primary_target)).any() else ""
        roots, lanes = _lineages(r, order)
        if not roots:
            continue
        n = len(roots); row_h = 0.62
        head, foot = _margins(meta, caption=False); foot += 0.42 if STYLE["captions"] else 0.0   # two legend lines (captions only)
        H = head + 0.35 + row_h * n + 0.5 + foot
        fig, ax = plt.subplots(figsize=(10, H))
        years = [yr.get(m, np.nan) for m in order if m in r.index]
        x0, x1 = float(np.nanmin(years)) - 3, float(np.nanmax(years)) + 3
        for i, rt in enumerate(roots):
            yy = n - 1 - i; members = lanes[rt]; xs = [yr.get(m, np.nan) for m in members]
            if len(members) > 1:
                ax.plot([min(xs), max(xs)], [yy, yy], color=C["grid"], lw=1.4, zorder=1)
            k = 0
            for m, x in zip(members, xs):
                is_root = m == rt; ident = pd.notna(r.loc[m, "identity_of"]); col = _verdict_colour(v.get(m, ""))
                hollow = not conf.get((m, s), True); flag = "†" if oovd.get((m, s), 0) > 0.5 else ""
                mk = "D" if ident else "o"
                ax.plot(x, yy, mk, ms=8 if is_root else 6, mfc=C["surface"] if hollow else col, mec=col, mew=1.6, zorder=3)
                if is_root:
                    kind = F("kind").get(kinds.get(m), "—") if kinds else ""
                    name = f"{short.get(m, m)} {int(x) if pd.notna(x) else ''}{flag}"
                    if kind and kind != "—":
                        ax.annotate(kind, (x, yy), xytext=(-10, 0), textcoords="offset points", fontsize=7.0, color=C["ink2"], ha="right", va="center")
                        ax.annotate(name + "  ·  ", (x, yy), xytext=(-10 - 4.3 * len(kind), 0), textcoords="offset points", fontsize=7.6, color=C["ink"], ha="right", va="center", fontweight="bold")
                    else:
                        ax.annotate(name, (x, yy), xytext=(-10, 0), textcoords="offset points", fontsize=7.6, color=C["ink"], ha="right", va="center", fontweight="bold")
                else:
                    rho = r.loc[m, "rho_sp_max"]; dy = 0.22 if k % 2 == 0 else -0.22; k += 1
                    ax.annotate(f"{short.get(m, m)} {int(x) if pd.notna(x) else ''}{flag}", (x, yy), xytext=(0, 9 if dy > 0 else -9), textcoords="offset points",
                                fontsize=6.6, color=C["ink2"], ha="center", va="bottom" if dy > 0 else "top")
                    ax.annotate(f"ρ {rho:.2f}" if np.isfinite(rho) else "≡", ((x + yr.get(rt, x)) / 2, yy), xytext=(0, 4), textcoords="offset points",
                                fontsize=7.2, color=C["ink"], ha="center", va="bottom")
        ax.set_yticks([]); ax.set_ylim(-0.6, n - 0.4); ax.set_xlim(x0, x1); ax.grid(axis="x"); ax.set_axisbelow(True)
        ax.set_xlabel(F("lin_x")); ax.set_title(f"{T('stratum')} {s} · {T('target')} {primary_target} vs {T('control')} {control}", fontsize=9, loc="left")
        for sp in ("left", "top", "right"):
            ax.spines[sp].set_visible(False)
        _frame(fig, F("lin_title"), meta)
        if STYLE["captions"]:
            fig.text(0.01, (0.30 + 0.20) / H, F("lin_l1", thr=threshold), fontsize=6.8, color=C["ink2"], va="bottom")
            fig.text(0.01, 0.30 / H, F("lin_l2", t=primary_target, c=control), fontsize=6.8, color=C["ink2"], va="bottom")
        fig.subplots_adjust(left=0.30, right=0.98, top=1 - (head + 0.35) / H, bottom=(foot + 0.5) / H)
        _save(fig, out_dir, f"lineage_{s}")


def exponents_sigma(alg: pd.DataFrame, red: pd.DataFrame, sigma: pd.DataFrame | None, out_dir: Path, meta: dict | None = None) -> None:
    """
    EN: exponent heat-map with rows grouped by lineage, a right-hand column (declared kind · exact / fit R²), and the
        stratum's log-correlation matrix Σ beside it. One panel pair per stratum.
    PT: mapa de expoentes agrupado por linhagem, coluna com tipo declarado e R², e a Σ do estrato ao lado.
    """
    if alg.empty:
        return
    cols = [c for c in alg.columns if c.startswith("e_")]; strata = sorted(alg.stratum.unique()); order = _order(alg); lab = _label(alg); short = _short(lab)
    A = alg.drop_duplicates("method_id").set_index("method_id"); kinds = A.target_kind.to_dict() if "target_kind" in A else {}
    n = len(order); head, foot = _margins(meta, caption=True); panel_top, panel_bot = 0.30, 0.30
    k = len(cols); ns = len(strata)
    row_in = max(0.30 * n, 0.55 * k) + panel_top + panel_bot
    H = head + row_in * ns + foot
    wr = [0.9 * k + 3.4, 0.55 * k + 0.6]
    fig, axes = plt.subplots(ns, 2, figsize=(min(10.0, sum(wr) + 2.2), H), squeeze=False, gridspec_kw={"width_ratios": wr, "wspace": 0.10, "hspace": 0.55})
    for j, s in enumerate(strata):
        ax, axs = axes[j][0], axes[j][1]
        a = alg[alg.stratum == s].set_index("method_id")
        r = red[red.stratum == s].set_index("method_id") if not red.empty else pd.DataFrame()
        roots, lanes = _lineages(r, order) if not r.empty else ([m for m in order if m in a.index], {m: [m] for m in order if m in a.index})
        ids = [m for rt in roots for m in lanes[rt] if m in a.index]
        M = a.loc[ids, cols].to_numpy(float); vmax = float(np.nanmax(np.abs(M))) or 1.0
        ax.imshow(M, cmap=DIV, norm=TwoSlopeNorm(vcenter=0, vmin=-vmax, vmax=vmax), aspect="auto")
        for i in range(M.shape[0]):
            for c in range(M.shape[1]):
                ax.text(c, i, f"{M[i, c]:+.2f}", ha="center", va="center", fontsize=6.5, color=C["ink"])
            src = a.loc[ids[i], "vector_source"]; fr = a.loc[ids[i], "fit_r2"]
            kind = F("kind").get(kinds.get(ids[i]), "—") if kinds else "—"
            ax.text(k - 0.4, i, f"{kind}  ·  " + (F("fixed") if src == "catalog" else F("approx", r=fr)), fontsize=6.2, va="center", ha="left", color=C["ink2"])
        # lineage separators
        pos = 0
        for rt in roots:
            m = len([x for x in lanes[rt] if x in a.index])
            if pos > 0:
                ax.axhline(pos - 0.5, color=C["surface"], lw=2.5)
            pos += m
        ylabels = [(short.get(m, m) + f" {int(a.loc[m, 'year'])}" if pd.notna(a.loc[m, "year"]) else short.get(m, m)) if m in [rt for rt in roots] else "   ↳ " + short.get(m, m) for m in ids]
        ax.set_xticks(range(k)); ax.set_xticklabels([c[2:] for c in cols]); ax.set_yticks(range(len(ids))); ax.set_yticklabels(ylabels, fontsize=7)
        ax.set_xlim(-0.5, k + 4.2); ax.set_title(f"{T('stratum')} {s}", fontsize=9, loc="left"); ax.tick_params(length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
        # Σ as correlation of logs
        if sigma is not None and not sigma.empty and (sigma.stratum == s).any():
            sg = sigma[sigma.stratum == s].pivot(index="var_i", columns="var_j", values="cov_log")
            vs = [c[2:] for c in cols if c[2:] in sg.index]; Sm = sg.loc[vs, vs].to_numpy(float)
            d = np.sqrt(np.diag(Sm)); R = Sm / np.outer(d, d)
            axs.imshow(R, cmap=DIV, norm=TwoSlopeNorm(vcenter=0, vmin=-1, vmax=1), aspect="equal")
            for i in range(len(vs)):
                for c in range(len(vs)):
                    axs.text(c, i, f"{R[i, c]:+.2f}", ha="center", va="center", fontsize=5.8, color=C["ink"])
            axs.set_xticks(range(len(vs))); axs.set_xticklabels(vs, fontsize=6.5); axs.set_yticks(range(len(vs))); axs.set_yticklabels(vs, fontsize=6.5)
            axs.set_title(F("ex_sigma"), fontsize=7.5, loc="left"); axs.tick_params(length=0)
            for sp in axs.spines.values():
                sp.set_visible(False)
        else:
            axs.axis("off")
    _frame(fig, F("ex_title"), meta, caption=F("ex_read"))
    fig.subplots_adjust(left=0.20, right=0.99, top=1 - (head + panel_top) / H, bottom=(foot + panel_bot) / H)
    _save(fig, out_dir, "exponents")


CAPTIONS = {
    "scorecard": ("Verdict sheet. One row per method in publication order; three cells. Originality: original, or repeats an earlier method (with its name and the Spearman correlation). Specificity (conditional control): specific, tracks the control, both, or no signal; S1 = gain for the target when the index is added to the control, S2 = gain for the control when added to the target, with 95% bootstrap intervals. Added value: gain in out-of-sample score when the index is added to the covariates. † applied outside declared validity · * not curated.",
                  "Ficha de veredictos. Una fila por método en orden de publicación; tres celdas. Originalidad: original, o repite un método anterior (con su nombre y la correlación de Spearman). Especificidad (control condicional): específico, sigue el control, ambos, o sin señal; S1 = ganancia para el objetivo al añadir el índice al control, S2 = ganancia para el control al añadirlo al objetivo, con intervalos bootstrap 95%. Valor agregado: ganancia fuera de muestra al añadir el índice a las covariables. † fuera de la validez declarada · * no curada.",
                  "Ficha de vereditos. Uma linha por método em ordem de publicação; três células. Originalidade: original, ou repete um método anterior (com o nome e a correlação de Spearman). Especificidade (controle condicional): específico, acompanha o controle, ambos, ou sem sinal; S1 = ganho para o alvo ao juntar o índice ao controle, S2 = ganho para o controle ao juntá-lo ao alvo, com intervalos bootstrap 95%. Valor acrescentado: ganho fora da amostra ao juntar o índice às covariáveis. † fora da validade declarada · * não curada.",
           "Scheda dei verdetti. Una riga per metodo in ordine di pubblicazione; tre celle. Originalità: originale, oppure ripete un metodo precedente (con il nome e la correlazione di Spearman). Specificità (controllo condizionale): specifico, segue il controllo, entrambi, o nessun segnale; S1 = guadagno per il target quando l'indice si aggiunge al controllo, S2 = guadagno per il controllo quando si aggiunge al target, con intervalli bootstrap 95%. Valore aggiunto: guadagno nel punteggio fuori campione quando l'indice si aggiunge alle covariate. † applicato fuori dalla validità dichiarata · * non curato."),
    "board": ("Verdict board. One row per method, ordered by publication (earliest at top). Left: originality = 1 − max|Spearman| with an earlier method (log scale; left of the dashed line = redundant). Centre: specificity = score(target) − score(control) with 95% bootstrap interval; blue = specific, orange = measures the control, grey = inconclusive. Right: added value over the covariates with interval; dashed = margin. Hollow markers = formula not curated (primary source not critically read). ◆ = exact transformation of another method (identity). † = applied mostly outside the method's declared validity range (age, BMI or sex).",
              "Cuadro de veredictos. Una fila por método, en orden de publicación. Izquierda: originalidad = 1 − máx|Spearman| con un método anterior (escala log; a la izquierda de la línea discontinua = redundante). Centro: especificidad = puntaje(objetivo) − puntaje(control) con intervalo bootstrap 95%; azul = específico, naranja = mide el control, gris = no concluyente. Derecha: valor agregado sobre las covariables con intervalo; discontinua = margen. Marcadores huecos = fórmula no curada (fuente primaria sin lectura crítica). ◆ = transformación exacta de otro método.",
              "Quadro de vereditos. Uma linha por método, em ordem de publicação. Esquerda: originalidade = 1 − máx|Spearman| com um método anterior (escala log; à esquerda da linha tracejada = redundante). Centro: especificidade = escore(alvo) − escore(controle) com intervalo bootstrap 95%; azul = específico, laranja = mede o controle, cinza = inconclusivo. Direita: valor acrescentado sobre as covariáveis com intervalo; tracejada = margem. Marcadores vazados = fórmula não curada (fonte primária sem leitura crítica). ◆ = transformação exata de outro método.",
           "Quadro dei verdetti. Una riga per metodo, in ordine di pubblicazione (il più antico in alto). Sinistra: originalità = 1 − max|Spearman| con un metodo precedente (scala log; a sinistra della linea tratteggiata = ridondante). Centro: specificità = punteggio(target) − punteggio(controllo) con intervallo bootstrap 95%; blu = specifico, arancione = misura il controllo, grigio = inconclusivo. Destra: valore aggiunto oltre le covariate con intervallo; tratteggiata = margine. Marcatori vuoti = formula non curata (fonte primaria senza lettura critica). ◆ = trasformazione esatta di un altro metodo (identità). † = applicato per lo più fuori dall'intervallo di validità dichiarato (età, BMI o sesso)."),
    "exponents": ("Exponent vectors. Each row is a method written as a product of powers of the measured variables; cells show the exponent (blue positive, orange negative). Rows with similar patterns carry the same information; 'fit R²' is how well a sum-type equation behaves as a product (1.00 = exact).",
                  "Vectores de exponentes. Cada fila es un método escrito como producto de potencias de las variables medidas; las celdas muestran el exponente (azul positivo, naranja negativo). Filas con patrones similares llevan la misma información; 'fit R²' indica cuán bien una ecuación aditiva se comporta como producto.",
                  "Vetores de expoentes. Cada linha é um método escrito como produto de potências das variáveis medidas; as células mostram o expoente (azul positivo, laranja negativo). Linhas com padrões parecidos carregam a mesma informação; 'fit R²' é o quanto uma equação de soma se comporta como produto.",
           "Vettori degli esponenti. Ogni riga è un metodo scritto come prodotto di potenze delle variabili misurate; le celle mostrano l'esponente (blu positivo, arancione negativo). Righe con pattern simili portano la stessa informazione; 'R² dell'adattamento' indica quanto un'equazione a somma si comporta come un prodotto (1,00 = esatto)."),
    "predicted_observed": ("Algebraic check. Each point is a pair of methods: the correlation predicted from the covariance of the log-variables (before computing any index) against the correlation observed. Points on the diagonal confirm the prediction; the labelled points are the largest gaps.",
                           "Verificación algebraica. Cada punto es un par de métodos: correlación predicha desde la covarianza de los log-variables (antes de calcular índice alguno) contra la observada. Puntos en la diagonal confirman la predicción; los etiquetados son las mayores brechas.",
                           "Verificação algébrica. Cada ponto é um par de métodos: correlação prevista pela covariância dos log-variáveis (antes de calcular qualquer índice) contra a observada. Pontos na diagonal confirmam a previsão; os rotulados são as maiores lacunas.",
           'Verifica algebrica. Ogni punto è una coppia di metodi: la correlazione prevista dalla covarianza delle log-variabili (prima di calcolare qualunque indice) contro la correlazione osservata. I punti sulla diagonale confermano la previsione; i punti etichettati sono gli scarti maggiori.'),
    "target_control": ("Conditional negative-control map. y = S1, the gain in out-of-sample score for the target when the index is added to a model that already has the control; x = S2, the gain for the control when the index is added to a model that already has the target. Bars = 95 % paired-bootstrap intervals; dashed lines = margin. Upper-left: specific (adds to the target, not to the control). Lower-right: tracks the control. Upper-right: carries information neither explains (e.g. body size). Lower-left: no signal beyond what target and control already share. Colour = verdict; hollow marker = not curated.",
                       "Mapa del control negativo condicional. y = S1, ganancia fuera de muestra para el objetivo al añadir el índice a un modelo que ya tiene el control; x = S2, ganancia para el control al añadir el índice a un modelo que ya tiene el objetivo. Barras = intervalos bootstrap pareados 95 %; discontinuas = margen. Arriba-izquierda: específico. Abajo-derecha: sigue el control. Arriba-derecha: información que ninguno explica (p. ej. tamaño corporal). Abajo-izquierda: sin señal. Color = veredicto; marcador hueco = no curada.",
                       "Mapa do controle negativo condicional. y = S1, ganho fora da amostra para o alvo ao juntar o índice a um modelo que já tem o controle; x = S2, ganho para o controle ao juntar o índice a um modelo que já tem o alvo. Barras = intervalos bootstrap pareados 95 %; tracejado = margem. Alto-esquerda: específico (acrescenta ao alvo, não ao controle). Baixo-direita: acompanha o controle. Alto-direita: informação que nenhum explica (por exemplo tamanho corporal). Baixo-esquerda: sem sinal além do que alvo e controle já compartilham. Cor = veredito; marcador vazado = não curada.",
           "Mappa del controllo negativo condizionale. y = S1, guadagno nel punteggio fuori campione per il target quando l'indice si aggiunge a un modello che contiene già il controllo; x = S2, guadagno per il controllo quando l'indice si aggiunge a un modello che contiene già il target. Barre = intervalli bootstrap appaiati 95 %; linee tratteggiate = margine. In alto a sinistra: specifico (aggiunge al target, non al controllo). In basso a destra: segue il controllo. In alto a destra: porta informazione che nessuno dei due spiega (es. dimensione corporea). In basso a sinistra: nessun segnale oltre ciò che target e controllo già condividono. Colore = verdetto; marcatore vuoto = non curato."),
    "lineage": ("Family tree. One row per original index (filled node at its year); later indices that order people almost identically (|Spearman| ≥ threshold) hang from it with the correlation on the branch. Node colour = specificity verdict for the target against the control (green specific, violet tracks the control, grey inconclusive); hollow edge = not curated (primary source not critically read); † = outside declared validity; ◆ = identity. Next to the root: what its authors say it measures. Precedence lanes. Each lane starts with an original method (leftmost, filled) and lists, by year, the later methods statistically indistinguishable from it (|Spearman| ≥ threshold with that lineage). A method appears in the lane of its earliest predecessor. ◆ = identity.",
                "Árbol genealógico. Una fila por índice original (nodo relleno en su año); los índices posteriores que ordenan a las personas casi igual (|Spearman| ≥ umbral) cuelgan de él con la correlación en la rama. Color del nodo = veredicto de especificidad para el objetivo frente al control (verde específico, violeta sigue el control, gris no concluyente); borde hueco = no curado (fuente primaria sin lectura crítica); † = fuera de la validez declarada; ◆ = identidad. Junto a la raíz: lo que sus autores dicen que mide. Carriles de precedencia. Cada carril empieza con un método original (izquierda, relleno) y lista, por año, los métodos posteriores estadísticamente indistinguibles de él. Un método aparece en el carril de su predecesor más antiguo. ◆ = identidad.",
                "Árvore genealógica. Uma linha por índice original (nó preenchido no seu ano); os índices posteriores que ordenam as pessoas quase igual (|Spearman| ≥ limiar) pendem dele com a correlação no ramo. Cor do nó = veredito de especificidade para o alvo contra o controle (verde específico, violeta acompanha o controle, cinza inconclusivo); borda vazada = não curado (fonte primária sem leitura crítica); † = fora da validade declarada; ◆ = identidade. Ao lado da raiz: o que os autores dizem que mede. Faixas de precedência. Cada faixa começa com um método original (à esquerda, preenchido) e lista, por ano, os métodos posteriores estatisticamente indistinguíveis dele. Um método aparece na faixa do seu antecessor mais antigo. ◆ = identidade.",
           'Albero genealogico. Una riga per indice originale (nodo pieno al suo anno); gli indici successivi che ordinano le persone quasi allo stesso modo (|Spearman| ≥ soglia) pendono da esso con la correlazione sul ramo. Colore del nodo = verdetto di specificità per il target rispetto al controllo (verde specifico, viola segue il controllo, grigio inconclusivo); bordo vuoto = non curato (fonte primaria senza lettura critica); † = fuori dalla validità dichiarata; ◆ = identità. Accanto alla radice: che cosa dicono gli autori che misura. Corsie di precedenza. Ogni corsia inizia con un metodo originale (il più a sinistra, pieno) ed elenca, per anno, i metodi successivi statisticamente indistinguibili da esso (|Spearman| ≥ soglia con quel lignaggio). Un metodo compare nella corsia del suo predecessore più antico. ◆ = identità.'),
    "sigma_transfer": ("Transfer of Σ. Rows: the population whose covariance was used to predict; columns: the population where correlations were observed. Cell = median |predicted − observed|. Small values off the diagonal mean redundancy transfers between populations.",
                       "Transferencia de Σ. Filas: población cuya covarianza se usó para predecir; columnas: población donde se observaron las correlaciones. Celda = mediana |predicho − observado|. Valores pequeños fuera de la diagonal = la redundancia se transfiere.",
                       "Transferência de Σ. Linhas: população cuja covariância foi usada para prever; colunas: população onde as correlações foram observadas. Célula = mediana |previsto − observado|. Valores pequenos fora da diagonal = a redundância transfere.",
           'Trasferimento di Σ. Righe: la popolazione la cui covarianza è stata usata per prevedere; colonne: la popolazione in cui le correlazioni sono state osservate. Cella = mediana |previsto − osservato|. Valori piccoli fuori dalla diagonale indicano che la ridondanza si trasferisce tra popolazioni.'),
    "combination_gain": ("Combining indices. Horizontal: how orthogonal the added index is to the host (0 = carries different information). Vertical: gain in out-of-sample score from adding it, with interval. Gain appears only when the pair is predicted to be non-redundant.",
                         "Combinar índices. Horizontal: cuán ortogonal es el índice agregado al anfitrión (0 = información distinta). Vertical: ganancia en puntaje fuera de muestra al agregarlo, con intervalo. La ganancia aparece solo cuando el par se predice no redundante.",
                         "Combinar índices. Horizontal: quão ortogonal o índice acrescentado é ao hospedeiro (0 = informação distinta). Vertical: ganho no escore fora da amostra ao acrescentá-lo, com intervalo. Ganho aparece só quando o par é previsto como não redundante.",
           "Combinare indici. Orizzontale: quanto l'indice aggiunto è ortogonale all'ospite (0 = porta informazione diversa). Verticale: guadagno nel punteggio fuori campione dall'aggiunta, con intervallo. Il guadagno compare solo quando la coppia è prevista non ridondante."),
    "compass": ("Index compass (≤ 10 methods). Each arrow is a method as a vector of exponents; parallel arrows are redundant, orthogonal arrows carry different information.",
                "Brújula de índices (≤ 10 métodos). Cada flecha es un método como vector de exponentes; flechas paralelas son redundantes, ortogonales aportan información distinta.",
                "Bússola de índices (≤ 10 métodos). Cada seta é um método como vetor de expoentes; setas paralelas são redundantes, ortogonais trazem informação distinta.",
           'Bussola degli indici (≤ 10 metodi). Ogni freccia è un metodo come vettore di esponenti; frecce parallele sono ridondanti, frecce ortogonali portano informazione diversa.'),
}


def _save(fig, out_dir: Path, name: str) -> None:
    for fmt in STYLE["formats"]:
        fig.savefig(out_dir / f"{name}.{fmt}", dpi=STYLE["dpi"], bbox_inches="tight", facecolor=C["surface"])
    plt.close(fig)


def _order(alg: pd.DataFrame) -> list[str]:
    """EN: methods by precedence (year, then id) — the same order everywhere. ES/PT: ordem por precedência."""
    a = alg.drop_duplicates("method_id").copy(); a["year"] = a["year"].fillna(9999)
    return list(a.sort_values(["year", "method_id"]).method_id)


def _label(alg: pd.DataFrame) -> dict[str, str]:
    a = alg.drop_duplicates("method_id")
    full = dict(zip(a.method_id, a.label.fillna(a.method_id)))
    if STYLE["labels"] == "short":
        return {k: v.split(" [")[0].split(" (")[0] + (f" {int(y)}" if pd.notna(y) and str(int(y)) not in v.split(" [")[0].split(" (")[0] else "") for (k, v), y in zip(full.items(), a.year)}
    return full


# ----------------------------------------------------------------------------------------------
def board(alg: pd.DataFrame, red: pd.DataFrame, aud: pd.DataFrame, uti: pd.DataFrame | None, out_dir: Path, primary_target: str,
          threshold: float = 0.95, margin: float = 0.03, meta: dict | None = None) -> None:
    if alg.empty or red.empty or aud.empty:
        return
    strata = sorted(alg.stratum.unique()); order = _order(alg); lab = _label(alg)
    conf = _curated_by_method_stratum(alg); prop = _proposed_by_method(alg); des = _designed_by_method(alg)
    for s in strata:
        r = red[red.stratum == s].set_index("method_id")
        a = aud[(aud.stratum == s) & (aud.target == primary_target)].set_index("method_id")
        u = uti[(uti.stratum == s) & (uti.target == primary_target)].set_index("method_id") if uti is not None and not uti.empty else None
        ids = [m for m in order if m in r.index]
        n = len(ids); y = np.arange(n)[::-1]
        fig, axes = plt.subplots(1, 3, figsize=(11, 0.28 * n + 1.6), sharey=True, gridspec_kw={"width_ratios": [1.0, 1.2, 1.0], "wspace": 0.08})
        for ax in axes:
            ax.set_yticks(y); ax.grid(axis="x"); ax.set_axisbelow(True); ax.tick_params(axis="y", length=0)
        oov = alg[alg.stratum == s].set_index("method_id").get("out_of_validity_frac", pd.Series(dtype=float)).to_dict()
        axes[0].set_yticklabels([lab.get(m, m) + (" †" if oov.get(m, 0) > 0.5 else "") for m in ids], fontsize=7.5, color=C["ink"])
        # --- panel 1: originality
        ax = axes[0]; orig = np.array([1 - r.loc[m, "rho_sp_max"] if np.isfinite(r.loc[m, "rho_sp_max"]) else 1.0 for m in ids])
        orig = np.clip(orig, 1e-3, 1.0)
        for yi, m, o in zip(y, ids, orig):
            ident = r.loc[m, "identity_of"] if pd.notna(r.loc[m, "identity_of"]) else None; redund = bool(r.loc[m, "redundant"])
            if ident:   # EN: identity rows carry no originality bar — they are the same index as their original
                ax.plot(1.2e-3, yi, "D", ms=5, mfc=C["surface"], mec=C["muted"], mew=1.2)
                ax.text(1.6e-3, yi, f"= {lab.get(ident, ident)} ({T('identity')})", fontsize=6, va="center", color=C["ink2"])
                continue
            col = C["muted"] if redund else C["specific"]
            ax.plot([1e-3, o], [yi, yi], color=col, lw=1.4, alpha=0.9)
            ax.plot(o, yi, "o", ms=5, mfc=C["surface"] if not conf.get((m, s), True) else col, mec=col, mew=1.2)
            pred = r.loc[m, "predecessor_id"]
            if redund and isinstance(pred, str):
                txt = lab.get(pred, pred); txt = txt if len(txt) <= 28 else txt[:26] + "…"
                ax.text(1.02 * o, yi, f"≈ {txt}", fontsize=6, va="center", color=C["ink2"], clip_on=True)
        ax.set_xscale("log"); ax.set_xlim(1e-3, 1.2); ax.axvline(1 - threshold, color=C["ink2"], lw=0.8, ls="--")
        ax.set_xlabel(T("orig"))
        # --- panel 2: specificity
        ax = axes[1]
        for yi, m in zip(y, ids):
            if m not in a.index:
                continue
            row = a.loc[m]; col = _verdict_colour(row.verdict)
            ax.plot([row.disc_lo, row.disc_hi], [yi, yi], color=col, lw=1.4, alpha=0.9)
            ax.plot(row.disc_mean, yi, "o", ms=5, mfc=C["surface"] if not conf.get((m, s), True) else col, mec=col, mew=1.2)
        ax.axvline(0, color=C["ink2"], lw=0.8); ax.set_xlabel(T("spec", m=a.metric.iloc[0]))
        # --- panel 3: utility
        ax = axes[2]
        if u is not None:
            for yi, m in zip(y, ids):
                if m not in u.index:
                    continue
                row = u.loc[m]; col = C["specific"] if bool(row.useful) else C["muted"]
                ax.plot([row.delta_lo, row.delta_hi], [yi, yi], color=col, lw=1.4, alpha=0.9)
                ax.plot(row.delta_mean, yi, "o", ms=5, mfc=C["surface"] if not conf.get((m, s), True) else col, mec=col, mew=1.2)
            ax.axvline(margin, color=C["ink2"], lw=0.8, ls="--"); ax.axvline(0, color=C["grid"], lw=0.8)
            ax.set_xlabel(T("util", m=a.metric.iloc[0]))
        else:
            ax.text(0.5, 0.5, T("no_util"), ha="center", va="center", transform=ax.transAxes, color=C["ink2"])
            ax.set_xticks([])
        _title(fig, f"{T('board')} — {T('stratum')} {s} · {T('target')} {primary_target} vs {T('control')} {a.control.iloc[0]}")
        if any(oov.get(m, 0) > 0.5 for m in ids):   # EN: † legend always shown when used, independent of a custom title
            axes[0].text(0.0, 1.01, T("oov"), transform=axes[0].transAxes, fontsize=6.5, color=C["ink2"], ha="left", va="bottom")
        fig.subplots_adjust(top=0.95 if STYLE["subtitle"] else 0.96, bottom=0.08)
        _footer(fig, meta)
        _save(fig, out_dir, f"board_{s}")


def scorecard(alg: pd.DataFrame, red: pd.DataFrame, aud: pd.DataFrame, uti: pd.DataFrame | None, out_dir: Path, primary_target: str,
              threshold: float = 0.95, meta: dict | None = None, margin: float = 0.03, geo: pd.DataFrame | None = None) -> None:
    """
    EN: the readable verdict sheet — one row per method, three cells with a coloured pill and a short technical phrase;
        numbers are evidence, set small. Replaces the board as an official figure (board stays supplementary).
    ES/PT: ficha de vereditos legível — uma linha por método, três células com selo e frase curta.
    """
    if alg.empty or red.empty or aud.empty:
        return
    from matplotlib.patches import FancyBboxPatch
    order = _order(alg); lab = _label(alg); short = _short(lab)
    conf = _curated_by_method_stratum(alg); prop = _proposed_by_method(alg); des = _designed_by_method(alg)
    oovd = alg.set_index(["method_id", "stratum"]).get("out_of_validity_frac", pd.Series(dtype=float)).to_dict()
    for st in sorted(alg.stratum.unique()):
        r = red[red.stratum == st].set_index("method_id")
        a = aud[(aud.stratum == st) & (aud.target == primary_target)].set_index("method_id")
        u = uti[(uti.stratum == st) & (uti.target == primary_target)].set_index("method_id") if uti is not None and not uti.empty else None
        ids = [m for m in order if m in r.index]
        if not ids:
            continue
        par, coupled = _geo_flags(geo, st, primary_target)
        metric = (str(a.metric.iloc[0]) if len(a) else "R2").replace("R2", "R²"); control = a.control.iloc[0] if len(a) else ""
        smax = float(np.nanmax(np.concatenate([aud.s1_hi.to_numpy(float), aud.s2_hi.to_numpy(float)]))) if "s1_hi" in aud else 1.0
        covs = u.covariates.iloc[0].replace("+", " + ") if u is not None and len(u) else ""
        n = len(ids)
        # EN: fixed geometry in inches: header (title+subtitle+column names) 1.25, rows 0.42 each, legend+footer 1.15
        row_h, head_in = 0.42, (1.10 if STYLE["subtitle"] else 0.90) + 0.20   # EN: +0.20 in for the two-line column headers
        foot_in = 1.15 if STYLE["captions"] else 0.45
        W, H = 10.0, head_in + row_h * n + foot_in
        fig = plt.figure(figsize=(W, H))
        ax = fig.add_axes([0.0, foot_in / H, 1.0, row_h * n / H]); ax.set_xlim(0, 100); ax.set_ylim(0, n); ax.axis("off")
        x_m, x_o, x_s, x_u = 1.0, 24.0, 46.0, 77.0; pw = 10.0
        # column headers in TWO lines (figure coords, just above the rows): the label, then target/control or covariates
        #     truncated to the column width, so long column names never run into the next header (user-simulation finding)
        def _trunc(txt: str, n_ch: int) -> str:
            return txt if len(txt) <= n_ch else txt[: n_ch - 1] + "…"
        yh = (foot_in + row_h * n + 0.12) / H; yh2 = (foot_in + row_h * n + 0.30) / H
        sub_s = _trunc(f"{primary_target} vs {control}", 30) + (" ‡" if coupled else "")
        heads = ((x_m, S("method"), ""), (x_o, S("col_o"), ""), (x_s, S("col_s"), sub_s), (x_u, S("col_u"), _trunc(S("over", c=covs), 26) if covs else ""))
        for x, txt, sub in heads:
            fig.text(x / 100, yh2, txt, fontsize=8.5, color=C["ink2"], va="bottom")
            if sub:
                fig.text(x / 100, yh, sub, fontsize=7.0, color=C["ink2"], va="bottom")
        if coupled:   # EN: the coupling note goes under the rows (left), never next to the column headers
            fig.text(0.01, (foot_in - 0.14) / H, S("coupled"), fontsize=7.2, color=C["ink2"], va="bottom")
        fig.add_artist(plt.Line2D([0.0, 1.0], [yh - 0.01, yh - 0.01], color=C["grid"], lw=0.8, transform=fig.transFigure))

        def pill(x, y, word, color):
            ax.add_patch(FancyBboxPatch((x, y - 0.32), pw, 0.64, boxstyle="round,pad=0,rounding_size=0.32", fc=color, ec="none", mutation_aspect=0.04))
            ax.text(x + pw / 2, y, word, fontsize=7.6, color="white", ha="center", va="center", fontweight="bold")

        for i, m in enumerate(ids):
            y = n - i - 0.5
            if i % 2 == 0:
                ax.add_patch(FancyBboxPatch((0, y - 0.5), 100, 1.0, boxstyle="square,pad=0", fc="#f4f6fc", ec="none"))
            flags = (" †" if oovd.get((m, st), 0) > 0.5 else "") + (" " + _mark(m, {m: conf.get((m, st), True)}, prop, des) if _mark(m, {m: conf.get((m, st), True)}, prop, des) else "") + (" ‡" if m in par else "")
            # EN: the method column is 23 % of the sheet; labels longer than that wrap to two lines instead of running into the pill
            wrapped = textwrap.wrap(lab.get(m, m), 30)[:2]
            if len(textwrap.wrap(lab.get(m, m), 30)) > 2:
                wrapped[1] = wrapped[1][:27] + "…"
            ax.text(x_m, y, "\n".join(wrapped) + flags, fontsize=8.2 if len(wrapped) == 1 else 7.4, color=C["ink"], va="center", linespacing=1.05)
            ident = r.loc[m, "identity_of"] if pd.notna(r.loc[m, "identity_of"]) else None
            if ident:
                pill(x_o, y, S("identical"), C["control"]); ax.text(x_o + pw + 0.8, y, f"= {short.get(ident, ident)}", fontsize=6.6, color=C["ink2"], va="center")
            elif bool(r.loc[m, "redundant"]):
                pred = r.loc[m, "predecessor_id"]
                # EN: two short lines (name / ρ) so the note stays inside the originality column (ends at x_s)
                pill(x_o, y, S("repeats"), C["control"]); ax.text(x_o + pw + 0.8, y, f"{short.get(pred, pred)}\nρ {r.loc[m, 'rho_sp_max']:.2f}", fontsize=6.6, color=C["ink2"], va="center", linespacing=1.05)
            else:
                pill(x_o, y, S("original"), C["specific"])
                if np.isfinite(r.loc[m, "rho_sp_max"]):
                    ax.text(x_o + pw + 0.8, y, f"ρ max {r.loc[m, 'rho_sp_max']:.2f}", fontsize=7, color=C["ink2"], va="center")
            if m in a.index:
                row = a.loc[m]; v = row.verdict
                if v == "SPECIFIC": pill(x_s, y, S("specific"), C["specific"])
                elif v in ("TRACKS_CONTROL", "MEASURES_CONTROL"): pill(x_s, y, S("tracks"), C["control"])
                elif v == "BOTH": pill(x_s, y, S("both"), C["ink2"])
                else: pill(x_s, y, S("neither"), C["muted"])
                if np.isfinite(row.s1_mean):
                    # EN: two mini bars in the cell: green = adds to the target beyond the control (S1); violet = adds to the
                    #     control beyond the target (S2); scaled to the largest |gain| in the sheet; number = S1 with its interval.
                    bx = x_s + pw + 1.0; bw = 7.0; sc = bw / max(smax, 1e-9)
                    ax.add_patch(FancyBboxPatch((bx, y + 0.02), max(row.s1_mean, 0) * sc, 0.24, boxstyle="square,pad=0", fc=C["specific"], ec="none"))
                    ax.add_patch(FancyBboxPatch((bx, y - 0.26), max(row.s2_mean, 0) * sc, 0.24, boxstyle="square,pad=0", fc=C["control"], ec="none"))
                    ax.plot([bx + max(row.s1_lo, 0) * sc, bx + max(row.s1_hi, 0) * sc], [y + 0.14, y + 0.14], color=C["ink"], lw=0.6)
                    ax.text(bx + bw + 0.8, y, f"{row.s1_mean:+.2f} [{row.s1_lo:+.2f}, {row.s1_hi:+.2f}]", fontsize=6.2, color=C["ink2"], va="center")
            if u is not None and m in u.index:
                row = u.loc[m]
                pill(x_u, y, S("adds") if bool(row.useful) else S("noadd"), C["specific"] if bool(row.useful) else C["muted"])
                ax.text(x_u + pw + 0.8, y, f"{row.delta_mean:+.2f} [{row.delta_lo:+.2f}, {row.delta_hi:+.2f}]", fontsize=7, color=C["ink2"], va="center")
            else:
                pill(x_u, y, S("notest"), C["muted"])
        for k, txt in enumerate((S("leg1", thr=threshold), S("leg2", m=metric, t=primary_target, c=control, mg=margin), S("leg3", m=metric, cov=covs or "—") + (" · " + S("prop") if any(prop.values()) else "") + (" · " + S("des") if any(des.values()) else ""))):
            if STYLE["captions"]:
                fig.text(0.01, (foot_in - 0.28 - 0.2 * k) / H, txt, fontsize=6.8, color=C["ink2"], va="center")
        _title(fig, f"{S('title')} — {T('stratum')} {st} · {T('target')} {primary_target} vs {T('control')} {control}")
        _footer(fig, meta)
        _save(fig, out_dir, f"scorecard_{st}")


def exponents(alg: pd.DataFrame, out_dir: Path, meta: dict | None = None) -> None:
    if alg.empty:
        return
    cols = [c for c in alg.columns if c.startswith("e_")]
    strata = sorted(alg.stratum.unique()); order = _order(alg); lab = _label(alg)
    head, foot = _margins(meta, caption=True)
    panel_top, panel_bot = 0.30, 0.30          # EN: axes title above / tick labels below, in inches
    body = 0.30 * len(order) + panel_top + panel_bot
    H = head + body + foot
    fig, axes = plt.subplots(1, len(strata), figsize=(0.9 * len(cols) + 3.2 * len(strata), H), squeeze=False, sharey=True)
    for ax, s in zip(axes[0], strata):
        a = alg[alg.stratum == s].set_index("method_id"); ids = [m for m in order if m in a.index]
        M = a.loc[ids, cols].to_numpy(float); vmax = float(np.nanmax(np.abs(M))) or 1.0
        im = ax.imshow(M, cmap=DIV, norm=TwoSlopeNorm(vcenter=0, vmin=-vmax, vmax=vmax), aspect="auto")
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                ax.text(j, i, f"{M[i, j]:+.2f}", ha="center", va="center", fontsize=6.5, color=C["ink"])
            fr = a.loc[ids[i], "fit_r2"]; src = a.loc[ids[i], "vector_source"]
            ax.text(M.shape[1] - 0.4, i, (T("fixed") if src == "catalog" else f"{T('fit')} {fr:.2f}"), fontsize=6, va="center", ha="left", color=C["ink2"])
        ax.set_xticks(range(len(cols))); ax.set_xticklabels([c[2:] for c in cols]); ax.set_yticks(range(len(ids))); ax.set_yticklabels([lab.get(m, m) for m in ids], fontsize=7)
        ax.set_xlim(-0.5, len(cols) + 1.2); ax.set_title(f"{T('stratum')} {s}", fontsize=9); ax.tick_params(length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
    _frame(fig, T("exp_title"), meta, caption=S("exp_read"))
    fig.subplots_adjust(top=1 - (head + panel_top) / H, bottom=(foot + panel_bot) / H, wspace=0.25)
    _save(fig, out_dir, "exponents")


def predicted_observed(pairs: pd.DataFrame, alg: pd.DataFrame, out_dir: Path, meta: dict | None = None) -> None:
    if pairs.empty:
        return
    p = pairs[~pairs.identity]; strata = sorted(p.stratum.unique()); lab = _label(alg) if not alg.empty else {}
    head, foot = _margins(meta, caption=False)
    panel_top, panel_bot = 0.30, 0.55          # EN: axes title above / x label + ticks below, in inches
    side = 2.9                                  # EN: square panel side (inches); width below is sized so the square fits
    body = side + panel_top + panel_bot
    H = head + body + foot
    W = (side * len(strata) + 0.3 * side * (len(strata) - 1)) / 0.88 + 0.2
    fig, axes = plt.subplots(1, len(strata), figsize=(W, H), squeeze=False)
    short = {k: re.sub(r"\s*\([^)]*\)\s*$", "", v) for k, v in lab.items()}   # EN: drop "(Author year)" inside the panel
    for ax, s in zip(axes[0], strata):
        q = p[p.stratum == s]
        ax.plot([-1, 1], [-1, 1], color=C["grid"], lw=1); ax.grid(True); ax.set_axisbelow(True)
        ax.scatter(q.r_log_predicted, q.r_log_observed, s=10, color=C["specific"], alpha=0.55, edgecolor=C["surface"], lw=0.4)
        top = q.nlargest(3, "abs_err_log")
        for k, row in enumerate(top.itertuples(), 1):
            ax.annotate(str(k), (row.r_log_predicted, row.r_log_observed), xytext=(6, -8), textcoords="offset points", fontsize=7, color=C["control"])
        ax.set_xlabel(S("po_x")); ax.set_ylabel(S("po_y"))
        ax.text(0.98, 0.04, S("po_note"), transform=ax.transAxes, fontsize=6.8, color=C["ink2"], ha="right")
        ax.set_title(T("po_title", s=f"{T('stratum')} {s}", n=len(q), g=q.abs_err_log.median()), fontsize=9)
        ax.set_xlim(-1.02, 1.02); ax.set_ylim(-1.02, 1.02); ax.set_aspect("equal")
        txt = "\n".join(f"{k}: {short.get(r.a_id, r.a_id)} × {short.get(r.b_id, r.b_id)} · {T('gap')} {r.abs_err_log:.2f}" for k, r in enumerate(top.itertuples(), 1))
        ax.text(0.02, 0.98, txt, transform=ax.transAxes, fontsize=6, va="top", color=C["ink2"])
    _frame(fig, T("po_default"), meta)
    fig.subplots_adjust(left=0.10, right=0.98, top=1 - (head + panel_top) / H, bottom=(foot + panel_bot) / H, wspace=0.3)
    _save(fig, out_dir, "predicted_observed")


def lineage(red: pd.DataFrame, alg: pd.DataFrame, out_dir: Path) -> None:
    if red.empty or alg.empty:
        return
    yr = alg.drop_duplicates("method_id").set_index("method_id").year.to_dict(); lab = _label(alg); order = _order(alg)
    strata = sorted(red.stratum.unique())
    for s in strata:
        r = red[red.stratum == s].set_index("method_id")
        # EN: root of each method = follow predecessor/identity links to the earliest original
        def root(m):
            seen = set()
            while m in r.index and m not in seen:
                seen.add(m)
                nxt = r.loc[m, "identity_of"] if pd.notna(r.loc[m, "identity_of"]) else (r.loc[m, "predecessor_id"] if bool(r.loc[m, "redundant"]) else None)
                if not isinstance(nxt, str):
                    return m
                m = nxt
            return m
        lanes: dict[str, list[str]] = {}
        for m in order:
            if m in r.index:
                lanes.setdefault(root(m), []).append(m)
        roots = [m for m in order if m in lanes]
        fig, ax = plt.subplots(figsize=(11, 0.75 * len(roots) + 1.4))
        def short(m, dup: bool):
            full = lab.get(m, m); base = full.split(" [")[0].split(" (")[0]
            tag = (" [" + full.split(" [")[1]) if dup and " [" in full else ""
            return (f"{base} {yr.get(m, '')}" if str(yr.get(m, "")) not in base else base) + tag
        for i, rt in enumerate(roots):
            yy = len(roots) - 1 - i
            members = lanes[rt]; xs = [yr.get(m, np.nan) for m in members]
            ax.plot([min(xs), max(xs)], [yy, yy], color=C["grid"], lw=1.2, zorder=1)
            k = 0; levels = (0.20, -0.20, 0.40, -0.40)
            shorts = [lab.get(m, m).split(" [")[0] for m in members]
            for m, x, sh in zip(members, xs, shorts):
                ident = pd.notna(r.loc[m, "identity_of"]); is_root = m == rt
                mk = "D" if ident else "o"; col = C["specific"] if is_root else C["muted"]
                ax.plot(x, yy, mk, ms=6 if is_root else 4.5, mfc=col if is_root else C["surface"], mec=col, mew=1.2, zorder=2)
                if not is_root:
                    dy = levels[k % 4]; k += 1
                    ax.text(x, yy + dy, short(m, shorts.count(sh) > 1), fontsize=5.8, ha="center", va="bottom" if dy > 0 else "top", color=C["ink2"])
        ax.set_yticks(range(len(roots))); ax.set_yticklabels([lab.get(rt, rt) for rt in roots[::-1]], fontsize=7.5, color=C["ink"])
        ax.tick_params(axis="y", length=0); ax.set_ylim(-0.7, len(roots) - 0.3); ax.grid(axis="x"); ax.set_axisbelow(True)
        ax.set_xlabel("year of publication"); ax.set_title(f"Precedence lanes — stratum {s} (row label = original root; hollow = redundant with that root; ◆ = identity)", fontsize=9, loc="left")
        _save(fig, out_dir, f"lineage_{s}")


def sigma_transfer(tr: pd.DataFrame, out_dir: Path) -> None:
    if tr is None or tr.empty:
        return
    m = tr.pivot(index="sigma_from", columns="observed_in", values="median_abs_err")
    fig, ax = plt.subplots(figsize=(1.6 + 0.7 * m.shape[1], 1.2 + 0.6 * m.shape[0]))
    im = ax.imshow(m.values, cmap=SEQ, vmin=0)
    ax.set_xticks(range(m.shape[1])); ax.set_xticklabels(m.columns, rotation=45, ha="right"); ax.set_yticks(range(m.shape[0])); ax.set_yticklabels(m.index)
    vmax = np.nanmax(m.values)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            ax.text(j, i, f"{m.values[i, j]:.3f}", ha="center", va="center", fontsize=6.5, color="white" if m.values[i, j] > vmax * 0.6 else C["ink"])
    ax.set_xlabel("correlations observed in"); ax.set_ylabel("Σ taken from"); ax.set_title("Σ transfer: median |predicted − observed|", fontsize=9, loc="left")
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02); _save(fig, out_dir, "sigma_transfer")


def combination_gain(comb: pd.DataFrame, out_dir: Path) -> None:
    if comb is None or comb.empty:
        return
    fig, ax = plt.subplots(figsize=(4.6, 3.6)); ax.grid(True); ax.set_axisbelow(True)
    ax.axhline(0, color=C["ink2"], lw=0.8)
    x = np.abs(comb.r_log_predicted)
    ax.errorbar(x, comb.gain_mean, yerr=[comb.gain_mean - comb.gain_lo, comb.gain_hi - comb.gain_mean], fmt="o", ms=3.5, color=C["specific"], alpha=0.65, lw=0.7, ecolor=C["specific"])
    ax.set_xlabel("|predicted Spearman| between host and added index (0 = orthogonal)"); ax.set_ylabel("gain from adding (score B − A), 95% interval")
    ax.set_title("Combination gain vs predicted orthogonality", fontsize=9, loc="left")
    _save(fig, out_dir, "combination_gain")


def compass(alg: pd.DataFrame, out_dir: Path) -> None:
    if alg.empty or len(alg.method_id.unique()) > 10 or not {"e_R", "e_Xc", "e_H", "e_W"} <= set(alg.columns):
        return
    strata = sorted(alg.stratum.unique()); lab = _label(alg)
    fig, axes = plt.subplots(len(strata), 2, figsize=(8, 3.6 * len(strata)), squeeze=False)
    for i, s in enumerate(strata):
        a = alg[alg.stratum == s]
        for j, (x, y) in enumerate((("e_R", "e_Xc"), ("e_H", "e_W"))):
            ax = axes[i, j]; ax.axhline(0, color=C["grid"], lw=0.8); ax.axvline(0, color=C["grid"], lw=0.8)
            for r in a.itertuples():
                hollow = not bool(getattr(r, "curated", True))
                ax.annotate("", xy=(getattr(r, x), getattr(r, y)), xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=C["ink2"], lw=1))
                ax.plot(getattr(r, x), getattr(r, y), "o", ms=5, mfc=C["surface"] if hollow else C["specific"], mec=C["specific"])
                ax.text(getattr(r, x), getattr(r, y), lab.get(r.method_id, r.method_id), fontsize=6.5, ha="left", va="bottom")
            ax.set_xlabel(f"exponent of {x[2:]}"); ax.set_ylabel(f"exponent of {y[2:]}"); ax.set_title(f"stratum {s}: {x[2:]}–{y[2:]}", fontsize=9)
    _save(fig, out_dir, "compass")


from .i18n import MSG as _MSG
CAPTIONS["zaku_method"] = tuple(_MSG["h.diagram_caption"][k] for k in ("en", "es", "pt", "it"))   # EN: same text as the report (v0.9)


def write_captions(out_dir: Path) -> None:
    order = {"en": (0, 1, 2, 3), "es": (1, 0, 2, 3), "pt": (2, 0, 1, 3), "it": (3, 0, 1, 2)}[STYLE["language"] if STYLE["language"] in ("en", "es", "pt", "it") else "en"]
    L = ["# Figures — how to read them / cómo leerlas / como ler / come leggerle", "",
         "Official: lineage · target_control · exponents · scorecard · zaku_method (fixed method diagram, SVG). Supplementary (on request): predicted_observed · board · sigma_transfer · combination_gain · compass.", ""]
    for name, caps in CAPTIONS.items():
        tags = ("EN", "ES", "PT", "IT")
        L += [f"## {name}", ""] + [x for i in order for x in (f"**{tags[i]}** — {caps[i]}", "")]
    (out_dir / "README.md").write_text("\n".join(L), encoding="utf-8")


OFFICIAL = ("lineage", "target_control", "exponents", "scorecard", "zaku_method")   # EN: decision 2026-09-11 — tree, negative-control map, exponents+Σ, verdict sheet
SUPPLEMENTARY = ("predicted_observed", "board", "sigma_transfer", "combination_gain", "compass")


def make_all(out_dir: Path, tables: dict, cfg: dict, *, supplementary: bool | None = None) -> None:
    """
    EN: official figures always; supplementary ones only when `output.supplementary_figures` (or the flag) is true.
    ES/PT: figuras oficiais sempre; suplementares só quando solicitadas.
    """
    fd = Path(out_dir) / "figures"; fd.mkdir(exist_ok=True)
    # EN: the folder belongs to THIS run: figures of an earlier run in the same folder (e.g. other strata) are removed first,
    #     because the report lists the folder (found 2026-09-16: stale scorecard_F/M listed in an unstratified rerun).
    import shutil
    for old in fd.iterdir():
        if old.is_file() and old.suffix.lower() in {".png", ".pdf", ".svg"}:
            old.unlink()
    if (fd / "supplementary").is_dir():
        shutil.rmtree(fd / "supplementary")
    apply_style(cfg.get("figures"))
    import datetime
    from . import __version__
    meta = {"version": __version__, "preset": cfg.get("preset", ""), "date": datetime.date.today().isoformat(),
            "seed_cv": cfg.get("seeds", {}).get("cv", ""), "seed_boot": cfg.get("seeds", {}).get("bootstrap", "")}
    alg, red, aud, uti = (tables.get(k, pd.DataFrame()) for k in ("algebra", "redundancy", "audit", "utility"))
    primary = aud.target.iloc[0] if not aud.empty else None
    exponents_sigma(alg, red, tables.get("sigma"), fd, meta)
    if primary:
        lineage_tree(red, alg, aud, fd, primary, threshold=cfg["algebra"]["redundancy_threshold"], meta=meta)
        geo = tables.get("geometry")
        target_control(aud, alg, fd, primary, meta, margin=cfg["audit"]["verdict"]["margin"], geo=geo)
        scorecard(alg, red, aud, uti, fd, primary, threshold=cfg["algebra"]["redundancy_threshold"], meta=meta, margin=cfg["audit"]["verdict"]["margin"], geo=geo)
    if supplementary is None:
        supplementary = bool(cfg.get("output", {}).get("supplementary_figures", False))
    if supplementary:
        sd = fd / "supplementary"; sd.mkdir(exist_ok=True)
        if primary:
            board(alg, red, aud, uti, sd, primary, threshold=cfg["algebra"]["redundancy_threshold"], margin=cfg["audit"]["utility_margin"], meta=meta)
        predicted_observed(tables.get("pairs", pd.DataFrame()), alg, sd, meta); sigma_transfer(tables.get("sigma_transfer"), sd); combination_gain(tables.get("combinations"), sd); compass(alg, sd)
    from .diagram import write_diagram
    write_diagram(fd)                                    # EN: fixed method diagram (SVG, current language) — v0.9
    write_captions(fd)

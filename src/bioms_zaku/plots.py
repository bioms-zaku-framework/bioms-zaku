"""
EN: Figures (CONTRATOS.md §4.4, revised after inspection on 2026-09-10). Generated ONLY from the output tables.
    Design rules (dataviz method): the reader's job picks the form; ≤ 2 categorical hues (validated: blue #2a78d6 =
    specific, orange #eb6834 = measures control); grey = de-emphasis (inconclusive); identity = marker shape + label,
    never a colour; provenance ≠ high = hollow marker; one hue light→dark for magnitude; blue/orange + grey midpoint
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

import numpy as np
import pandas as pd

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
except ImportError as e:  # pragma: no cover
    raise ImportError("plots require matplotlib (pip install 'bioms-zaku[plots]')") from e

C = {"specific": "#2a78d6", "control": "#eb6834", "muted": "#9a9893", "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e6e5e1", "surface": "#fcfcfb"}

# EN: user style (from config["figures"]); applied by `apply_style` before drawing. ES/PT: estilo do usuário.
STYLE = {"title": None, "subtitle": None, "language": "en", "labels": "full", "font": "DejaVu Sans", "font_size": 8.5,
         "dpi": 300, "formats": ["png", "pdf"], "footer": True}

# EN: axis/legend texts in three languages. ES/PT: textos dos eixos e legendas.
I18N = {
    "en": {"board": "Verdict board", "stratum": "stratum", "target": "target", "control": "control", "orig": "originality\n1 − max |Spearman| with an earlier method (log)",
           "spec": "specificity\n{m}(target) − {m}(control), 95% interval", "util": "added value over covariates\nΔ{m}, 95% interval",
           "no_util": "utility not run\n(no covariates declared)", "identity": "identity", "oov": "† = applied mostly outside declared validity",
           "exp_title": "Exponent vectors: how each index depends on R, Xc, H and W", "po_default": "Correlation predicted by the algebra vs measured in the data", "fixed": "fixed", "fit": "fit R²", "gap": "gap",
           "po_x": "predicted from Σ (Pearson of logs)", "po_y": "observed", "po_title": "{s}: {n} pairs, median |gap| {g:.3f}", "footer": "BioMS Zaku {v} · preset {p} · {d} · seeds cv={c} bootstrap={b}"},
    "es": {"board": "Cuadro de veredictos", "stratum": "estrato", "target": "objetivo", "control": "control", "orig": "originalidad\n1 − máx |Spearman| con un método anterior (log)",
           "spec": "especificidad\n{m}(objetivo) − {m}(control), intervalo 95%", "util": "valor agregado sobre covariables\nΔ{m}, intervalo 95%",
           "no_util": "utilidad no calculada\n(sin covariables)", "identity": "identidad", "oov": "† = aplicado mayormente fuera de la validez declarada",
           "exp_title": "Vectores de exponentes: cómo cada índice depende de R, Xc, H y W", "po_default": "Correlación predicha por el álgebra vs medida en los datos", "fixed": "fijo", "fit": "ajuste R²", "gap": "brecha",
           "po_x": "predicho desde Σ (Pearson de logs)", "po_y": "observado", "po_title": "{s}: {n} pares, mediana |brecha| {g:.3f}", "footer": "BioMS Zaku {v} · preset {p} · {d} · semillas cv={c} bootstrap={b}"},
    "pt": {"board": "Quadro de vereditos", "stratum": "estrato", "target": "alvo", "control": "controle", "orig": "originalidade\n1 − máx |Spearman| com um método anterior (log)",
           "spec": "especificidade\n{m}(alvo) − {m}(controle), intervalo 95%", "util": "valor acrescentado sobre covariáveis\nΔ{m}, intervalo 95%",
           "no_util": "utilidade não calculada\n(sem covariáveis)", "identity": "identidade", "oov": "† = aplicado majoritariamente fora da validade declarada",
           "exp_title": "Vetores de expoentes: como cada índice depende de R, Xc, H e W", "po_default": "Correlação prevista pela álgebra vs medida nos dados", "fixed": "fixo", "fit": "ajuste R²", "gap": "lacuna",
           "po_x": "previsto por Σ (Pearson dos logs)", "po_y": "observado", "po_title": "{s}: {n} pares, mediana |lacuna| {g:.3f}", "footer": "BioMS Zaku {v} · preset {p} · {d} · sementes cv={c} bootstrap={b}"},
}


SC = {
    "en": {"title": "Verdicts", "col_o": "originality", "col_s": "specificity", "col_u": "added value", "method": "method",
           "original": "Original", "repeats": "Repeats", "identical": "Identical to", "specific": "Specific", "tracks": "Tracks control",
           "inconc": "Inconclusive", "adds": "Adds value", "noadd": "No added value", "notest": "Not tested", "over": "over {c}",
           "leg1": "Originality: an index is original when no earlier method orders people almost identically (|Spearman| < {thr}); otherwise it repeats that method.",
           "leg2": "Specificity: out-of-sample {m} for the target ({t}) minus {m} for the negative control ({c}); the interval is the 95% bootstrap range.",
           "leg3": "Added value: gain in {m} when the index is added to {cov}. † applied outside the method's declared validity · * formula provenance not high.",
           "po_x": "correlation predicted by the algebra (from Σ)", "po_y": "correlation measured in the data", "po_note": "points on the line: prediction confirmed",
           "exp_read": "positive exponent: the index grows with the variable · negative: it decreases · fit R²: how closely a sum-type equation behaves as a product (fixed = exact)"},
    "es": {"title": "Veredictos", "col_o": "originalidad", "col_s": "especificidad", "col_u": "valor agregado", "method": "método",
           "original": "Original", "repeats": "Repite", "identical": "Idéntico a", "specific": "Específico", "tracks": "Sigue control",
           "inconc": "No concluyente", "adds": "Agrega valor", "noadd": "No agrega valor", "notest": "No evaluado", "over": "sobre {c}",
           "leg1": "Originalidad: un índice es original cuando ningún método anterior ordena a las personas casi igual (|Spearman| < {thr}); si no, repite ese método.",
           "leg2": "Especificidad: {m} fuera de muestra para el objetivo ({t}) menos {m} para el control negativo ({c}); el intervalo es el rango bootstrap 95%.",
           "leg3": "Valor agregado: ganancia en {m} al añadir el índice a {cov}. † aplicado fuera de la validez declarada · * procedencia de la fórmula no alta.",
           "po_x": "correlación predicha por el álgebra (desde Σ)", "po_y": "correlación medida en los datos", "po_note": "puntos sobre la línea: predicción confirmada",
           "exp_read": "exponente positivo: el índice crece con la variable · negativo: decrece · fit R²: cuán bien una ecuación aditiva se comporta como producto (fijo = exacto)"},
    "pt": {"title": "Vereditos", "col_o": "originalidade", "col_s": "especificidade", "col_u": "valor acrescentado", "method": "método",
           "original": "Original", "repeats": "Repete", "identical": "Idêntico a", "specific": "Específico", "tracks": "Acompanha ctrl",
           "inconc": "Inconclusivo", "adds": "Acrescenta valor", "noadd": "Não acrescenta", "notest": "Não avaliado", "over": "sobre {c}",
           "leg1": "Originalidade: um índice é original quando nenhum método anterior ordena as pessoas quase igual (|Spearman| < {thr}); senão, repete esse método.",
           "leg2": "Especificidade: {m} fora da amostra para o alvo ({t}) menos {m} para o controle negativo ({c}); o intervalo é a faixa bootstrap 95%.",
           "leg3": "Valor acrescentado: ganho em {m} ao juntar o índice a {cov}. † aplicado fora da validade declarada · * procedência da fórmula não alta.",
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
PALETTES = {"default": {"specific": "#2a78d6", "control": "#eb6834", "muted": "#9a9893"},
            "brand": {"specific": "#22c55e", "control": "#9333ea", "muted": "#9a9893"}}
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
    if caption:
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


DIV = LinearSegmentedColormap.from_list("div", ["#eb6834", "#f3d9cf", "#f0f0ee", "#cfe0f5", "#2a78d6"])
SEQ = LinearSegmentedColormap.from_list("seq", ["#f0f0ee", "#2a78d6"])
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": C["grid"], "axes.labelcolor": C["ink2"], "xtick.color": C["ink2"], "ytick.color": C["ink2"],
                     "grid.color": C["grid"], "grid.linewidth": 0.6, "figure.facecolor": C["surface"], "axes.facecolor": C["surface"]})

CAPTIONS = {
    "scorecard": ("Verdict sheet. One row per method in publication order; three cells. Originality: original, or repeats an earlier method (with its name and the Spearman correlation). Specificity: specific for the target, tracks the negative control, or inconclusive; the number is score(target) − score(control) with its 95% bootstrap interval. Added value: gain in out-of-sample score when the index is added to the covariates. † applied outside declared validity · * provenance not high.",
                  "Ficha de veredictos. Una fila por método en orden de publicación; tres celdas. Originalidad: original, o repite un método anterior (con su nombre y la correlación de Spearman). Especificidad: específico para el objetivo, sigue el control negativo, o no concluyente; el número es puntaje(objetivo) − puntaje(control) con su intervalo bootstrap 95%. Valor agregado: ganancia fuera de muestra al añadir el índice a las covariables. † fuera de la validez declarada · * procedencia no alta.",
                  "Ficha de vereditos. Uma linha por método em ordem de publicação; três células. Originalidade: original, ou repete um método anterior (com o nome e a correlação de Spearman). Especificidade: específico para o alvo, acompanha o controle negativo, ou inconclusivo; o número é escore(alvo) − escore(controle) com o intervalo bootstrap 95%. Valor acrescentado: ganho fora da amostra ao juntar o índice às covariáveis. † fora da validade declarada · * procedência não alta."),
    "board": ("Verdict board. One row per method, ordered by publication (earliest at top). Left: originality = 1 − max|Spearman| with an earlier method (log scale; left of the dashed line = redundant). Centre: specificity = score(target) − score(control) with 95% bootstrap interval; blue = specific, orange = measures the control, grey = inconclusive. Right: added value over the covariates with interval; dashed = margin. Hollow markers = formula provenance not high. ◆ = exact transformation of another method (identity). † = applied mostly outside the method's declared validity range (age, BMI or sex).",
              "Cuadro de veredictos. Una fila por método, en orden de publicación. Izquierda: originalidad = 1 − máx|Spearman| con un método anterior (escala log; a la izquierda de la línea discontinua = redundante). Centro: especificidad = puntaje(objetivo) − puntaje(control) con intervalo bootstrap 95%; azul = específico, naranja = mide el control, gris = no concluyente. Derecha: valor agregado sobre las covariables con intervalo; discontinua = margen. Marcadores huecos = procedencia de la fórmula no alta. ◆ = transformación exacta de otro método.",
              "Quadro de vereditos. Uma linha por método, em ordem de publicação. Esquerda: originalidade = 1 − máx|Spearman| com um método anterior (escala log; à esquerda da linha tracejada = redundante). Centro: especificidade = escore(alvo) − escore(controle) com intervalo bootstrap 95%; azul = específico, laranja = mede o controle, cinza = inconclusivo. Direita: valor acrescentado sobre as covariáveis com intervalo; tracejada = margem. Marcadores vazados = procedência da fórmula não alta. ◆ = transformação exata de outro método."),
    "exponents": ("Exponent vectors. Each row is a method written as a product of powers of the measured variables; cells show the exponent (blue positive, orange negative). Rows with similar patterns carry the same information; 'fit R²' is how well a sum-type equation behaves as a product (1.00 = exact).",
                  "Vectores de exponentes. Cada fila es un método escrito como producto de potencias de las variables medidas; las celdas muestran el exponente (azul positivo, naranja negativo). Filas con patrones similares llevan la misma información; 'fit R²' indica cuán bien una ecuación aditiva se comporta como producto.",
                  "Vetores de expoentes. Cada linha é um método escrito como produto de potências das variáveis medidas; as células mostram o expoente (azul positivo, laranja negativo). Linhas com padrões parecidos carregam a mesma informação; 'fit R²' é o quanto uma equação de soma se comporta como produto."),
    "predicted_observed": ("Algebraic check. Each point is a pair of methods: the correlation predicted from the covariance of the log-variables (before computing any index) against the correlation observed. Points on the diagonal confirm the prediction; the labelled points are the largest gaps.",
                           "Verificación algebraica. Cada punto es un par de métodos: correlación predicha desde la covarianza de los log-variables (antes de calcular índice alguno) contra la observada. Puntos en la diagonal confirman la predicción; los etiquetados son las mayores brechas.",
                           "Verificação algébrica. Cada ponto é um par de métodos: correlação prevista pela covariância dos log-variáveis (antes de calcular qualquer índice) contra a observada. Pontos na diagonal confirmam a previsão; os rotulados são as maiores lacunas."),
    "lineage": ("Precedence lanes. Each lane starts with an original method (leftmost, filled) and lists, by year, the later methods statistically indistinguishable from it (|Spearman| ≥ threshold with that lineage). A method appears in the lane of its earliest predecessor. ◆ = identity.",
                "Carriles de precedencia. Cada carril empieza con un método original (izquierda, relleno) y lista, por año, los métodos posteriores estadísticamente indistinguibles de él. Un método aparece en el carril de su predecesor más antiguo. ◆ = identidad.",
                "Faixas de precedência. Cada faixa começa com um método original (à esquerda, preenchido) e lista, por ano, os métodos posteriores estatisticamente indistinguíveis dele. Um método aparece na faixa do seu antecessor mais antigo. ◆ = identidade."),
    "sigma_transfer": ("Transfer of Σ. Rows: the population whose covariance was used to predict; columns: the population where correlations were observed. Cell = median |predicted − observed|. Small values off the diagonal mean redundancy transfers between populations.",
                       "Transferencia de Σ. Filas: población cuya covarianza se usó para predecir; columnas: población donde se observaron las correlaciones. Celda = mediana |predicho − observado|. Valores pequeños fuera de la diagonal = la redundancia se transfiere.",
                       "Transferência de Σ. Linhas: população cuja covariância foi usada para prever; colunas: população onde as correlações foram observadas. Célula = mediana |previsto − observado|. Valores pequenos fora da diagonal = a redundância transfere."),
    "combination_gain": ("Combining indices. Horizontal: how orthogonal the added index is to the host (0 = carries different information). Vertical: gain in out-of-sample score from adding it, with interval. Gain appears only when the pair is predicted to be non-redundant.",
                         "Combinar índices. Horizontal: cuán ortogonal es el índice agregado al anfitrión (0 = información distinta). Vertical: ganancia en puntaje fuera de muestra al agregarlo, con intervalo. La ganancia aparece solo cuando el par se predice no redundante.",
                         "Combinar índices. Horizontal: quão ortogonal o índice acrescentado é ao hospedeiro (0 = informação distinta). Vertical: ganho no escore fora da amostra ao acrescentá-lo, com intervalo. Ganho aparece só quando o par é previsto como não redundante."),
    "compass": ("Index compass (≤ 10 methods). Each arrow is a method as a vector of exponents; parallel arrows are redundant, orthogonal arrows carry different information.",
                "Brújula de índices (≤ 10 métodos). Cada flecha es un método como vector de exponentes; flechas paralelas son redundantes, ortogonales aportan información distinta.",
                "Bússola de índices (≤ 10 métodos). Cada seta é um método como vetor de expoentes; setas paralelas são redundantes, ortogonais trazem informação distinta."),
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
    conf = alg.set_index(["method_id", "stratum"]).provenance_confidence.to_dict()
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
            ax.plot(o, yi, "o", ms=5, mfc=C["surface"] if conf.get((m, s), "high") != "high" else col, mec=col, mew=1.2)
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
            row = a.loc[m]; col = {"SPECIFIC": C["specific"], "MEASURES_CONTROL": C["control"]}.get(row.verdict, C["muted"])
            ax.plot([row.disc_lo, row.disc_hi], [yi, yi], color=col, lw=1.4, alpha=0.9)
            ax.plot(row.disc_mean, yi, "o", ms=5, mfc=C["surface"] if conf.get((m, s), "high") != "high" else col, mec=col, mew=1.2)
        ax.axvline(0, color=C["ink2"], lw=0.8); ax.set_xlabel(T("spec", m=a.metric.iloc[0]))
        # --- panel 3: utility
        ax = axes[2]
        if u is not None:
            for yi, m in zip(y, ids):
                if m not in u.index:
                    continue
                row = u.loc[m]; col = C["specific"] if bool(row.useful) else C["muted"]
                ax.plot([row.delta_lo, row.delta_hi], [yi, yi], color=col, lw=1.4, alpha=0.9)
                ax.plot(row.delta_mean, yi, "o", ms=5, mfc=C["surface"] if conf.get((m, s), "high") != "high" else col, mec=col, mew=1.2)
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
              threshold: float = 0.95, meta: dict | None = None) -> None:
    """
    EN: the readable verdict sheet — one row per method, three cells with a coloured pill and a short technical phrase;
        numbers are evidence, set small. Replaces the board as an official figure (board stays supplementary).
    ES/PT: ficha de vereditos legível — uma linha por método, três células com selo e frase curta.
    """
    if alg.empty or red.empty or aud.empty:
        return
    from matplotlib.patches import FancyBboxPatch
    order = _order(alg); lab = _label(alg)
    conf = alg.set_index(["method_id", "stratum"]).provenance_confidence.to_dict()
    oovd = alg.set_index(["method_id", "stratum"]).get("out_of_validity_frac", pd.Series(dtype=float)).to_dict()
    for st in sorted(alg.stratum.unique()):
        r = red[red.stratum == st].set_index("method_id")
        a = aud[(aud.stratum == st) & (aud.target == primary_target)].set_index("method_id")
        u = uti[(uti.stratum == st) & (uti.target == primary_target)].set_index("method_id") if uti is not None and not uti.empty else None
        ids = [m for m in order if m in r.index]
        if not ids:
            continue
        metric = a.metric.iloc[0] if len(a) else "R2"; control = a.control.iloc[0] if len(a) else ""
        covs = u.covariates.iloc[0].replace("+", " + ") if u is not None and len(u) else ""
        n = len(ids)
        # EN: fixed geometry in inches: header (title+subtitle+column names) 1.25, rows 0.42 each, legend+footer 1.15
        row_h, head_in, foot_in = 0.42, 1.25, 1.15
        W, H = 13.0, head_in + row_h * n + foot_in
        fig = plt.figure(figsize=(W, H))
        ax = fig.add_axes([0.0, foot_in / H, 1.0, row_h * n / H]); ax.set_xlim(0, 100); ax.set_ylim(0, n); ax.axis("off")
        x_m, x_o, x_s, x_u = 1.0, 24.0, 49.0, 75.0; pw = 9.0
        # column headers (figure coords, just above the rows)
        yh = (foot_in + row_h * n + 0.12) / H
        for x, txt in ((x_m, S("method")), (x_o, S("col_o")), (x_s, f"{S('col_s')} · {primary_target} vs {control}"), (x_u, f"{S('col_u')} · {S('over', c=covs) if covs else ''}")):
            fig.text(x / 100, yh, txt, fontsize=8.5, color=C["ink2"], va="bottom")
        fig.add_artist(plt.Line2D([0.0, 1.0], [yh - 0.01, yh - 0.01], color=C["grid"], lw=0.8, transform=fig.transFigure))

        def pill(x, y, word, color):
            ax.add_patch(FancyBboxPatch((x, y - 0.32), pw, 0.64, boxstyle="round,pad=0,rounding_size=0.32", fc=color, ec="none", mutation_aspect=0.04))
            ax.text(x + pw / 2, y, word, fontsize=7.6, color="white", ha="center", va="center", fontweight="bold")

        for i, m in enumerate(ids):
            y = n - i - 0.5
            if i % 2 == 0:
                ax.add_patch(FancyBboxPatch((0, y - 0.5), 100, 1.0, boxstyle="square,pad=0", fc="#f4f6fc", ec="none"))
            flags = (" †" if oovd.get((m, st), 0) > 0.5 else "") + (" *" if conf.get((m, st), "high") != "high" else "")
            ax.text(x_m, y, lab.get(m, m) + flags, fontsize=8.2, color=C["ink"], va="center")
            ident = r.loc[m, "identity_of"] if pd.notna(r.loc[m, "identity_of"]) else None
            if ident:
                pill(x_o, y, S("identical"), C["control"]); ax.text(x_o + pw + 0.8, y, lab.get(ident, ident), fontsize=7, color=C["ink2"], va="center")
            elif bool(r.loc[m, "redundant"]):
                pred = r.loc[m, "predecessor_id"]
                pill(x_o, y, S("repeats"), C["control"]); ax.text(x_o + pw + 0.8, y, f"{lab.get(pred, pred)} · ρ {r.loc[m, 'rho_sp_max']:.2f}", fontsize=7, color=C["ink2"], va="center")
            else:
                pill(x_o, y, S("original"), C["specific"])
                if np.isfinite(r.loc[m, "rho_sp_max"]):
                    ax.text(x_o + pw + 0.8, y, f"ρ max {r.loc[m, 'rho_sp_max']:.2f}", fontsize=7, color=C["ink2"], va="center")
            if m in a.index:
                row = a.loc[m]; v = row.verdict
                if v == "SPECIFIC": pill(x_s, y, S("specific"), C["specific"])
                elif v == "MEASURES_CONTROL": pill(x_s, y, S("tracks"), C["control"])
                else: pill(x_s, y, S("inconc"), C["muted"])
                ax.text(x_s + pw + 0.8, y, f"{row.disc_mean:+.2f} [{row.disc_lo:+.2f}, {row.disc_hi:+.2f}]", fontsize=7, color=C["ink2"], va="center")
            if u is not None and m in u.index:
                row = u.loc[m]
                pill(x_u, y, S("adds") if bool(row.useful) else S("noadd"), C["specific"] if bool(row.useful) else C["muted"])
                ax.text(x_u + pw + 0.8, y, f"{row.delta_mean:+.2f} [{row.delta_lo:+.2f}, {row.delta_hi:+.2f}]", fontsize=7, color=C["ink2"], va="center")
            else:
                pill(x_u, y, S("notest"), C["muted"])
        for k, txt in enumerate((S("leg1", thr=threshold), S("leg2", m=metric, t=primary_target, c=control), S("leg3", m=metric, cov=covs or "—"))):
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
    x = np.abs(comb.rho_sp_predicted)
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
                hollow = r.provenance_confidence != "high"
                ax.annotate("", xy=(getattr(r, x), getattr(r, y)), xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=C["ink2"], lw=1))
                ax.plot(getattr(r, x), getattr(r, y), "o", ms=5, mfc=C["surface"] if hollow else C["specific"], mec=C["specific"])
                ax.text(getattr(r, x), getattr(r, y), lab.get(r.method_id, r.method_id), fontsize=6.5, ha="left", va="bottom")
            ax.set_xlabel(f"exponent of {x[2:]}"); ax.set_ylabel(f"exponent of {y[2:]}"); ax.set_title(f"stratum {s}: {x[2:]}–{y[2:]}", fontsize=9)
    _save(fig, out_dir, "compass")


def write_captions(out_dir: Path) -> None:
    order = {"en": (0, 1, 2), "es": (1, 0, 2), "pt": (2, 0, 1)}[STYLE["language"] if STYLE["language"] in ("en", "es", "pt") else "en"]
    L = ["# Figures — how to read them / cómo leerlas / como ler", "",
         "Official (the framework's three): exponents · predicted_observed · scorecard. Supplementary (on request): board · lineage · sigma_transfer · combination_gain · compass.", ""]
    for name, caps in CAPTIONS.items():
        tags = ("EN", "ES", "PT")
        L += [f"## {name}", ""] + [x for i in order for x in (f"**{tags[i]}** — {caps[i]}", "")]
    (out_dir / "README.md").write_text("\n".join(L), encoding="utf-8")


OFFICIAL = ("exponents", "predicted_observed", "scorecard")        # EN: the framework's three figures (decision 2026-09-10, revised)
SUPPLEMENTARY = ("board", "lineage", "sigma_transfer", "combination_gain", "compass")


def make_all(out_dir: Path, tables: dict, cfg: dict, *, supplementary: bool | None = None) -> None:
    """
    EN: official figures always; supplementary ones only when `output.supplementary_figures` (or the flag) is true.
    ES/PT: figuras oficiais sempre; suplementares só quando solicitadas.
    """
    fd = Path(out_dir) / "figures"; fd.mkdir(exist_ok=True)
    apply_style(cfg.get("figures"))
    import datetime
    from . import __version__
    meta = {"version": __version__, "preset": cfg.get("preset", ""), "date": datetime.date.today().isoformat(),
            "seed_cv": cfg.get("seeds", {}).get("cv", ""), "seed_boot": cfg.get("seeds", {}).get("bootstrap", "")}
    alg, red, aud, uti = (tables.get(k, pd.DataFrame()) for k in ("algebra", "redundancy", "audit", "utility"))
    primary = aud.target.iloc[0] if not aud.empty else None
    exponents(alg, fd, meta); predicted_observed(tables.get("pairs", pd.DataFrame()), alg, fd, meta)
    if primary:
        scorecard(alg, red, aud, uti, fd, primary, threshold=cfg["algebra"]["redundancy_threshold"], meta=meta)
    if supplementary is None:
        supplementary = bool(cfg.get("output", {}).get("supplementary_figures", False))
    if supplementary:
        sd = fd / "supplementary"; sd.mkdir(exist_ok=True)
        if primary:
            board(alg, red, aud, uti, sd, primary, threshold=cfg["algebra"]["redundancy_threshold"], margin=cfg["audit"]["utility_margin"], meta=meta)
        lineage(red, alg, sd); sigma_transfer(tables.get("sigma_transfer"), sd); combination_gain(tables.get("combinations"), sd); compass(alg, sd)
    write_captions(fd)

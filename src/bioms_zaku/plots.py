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
           "exp_title": "Exponent vectors (blue +, orange −); right: how well a sum-type equation behaves as a product", "fixed": "fixed", "fit": "fit R²",
           "po_x": "predicted from Σ (Pearson of logs)", "po_y": "observed", "po_title": "{s}: {n} pairs, median |gap| {g:.3f}", "footer": "BioMS Zaku {v} · preset {p} · {d} · seeds cv={c} bootstrap={b}"},
    "es": {"board": "Cuadro de veredictos", "stratum": "estrato", "target": "objetivo", "control": "control", "orig": "originalidad\n1 − máx |Spearman| con un método anterior (log)",
           "spec": "especificidad\n{m}(objetivo) − {m}(control), intervalo 95%", "util": "valor agregado sobre covariables\nΔ{m}, intervalo 95%",
           "no_util": "utilidad no calculada\n(sin covariables)", "identity": "identidad", "oov": "† = aplicado mayormente fuera de la validez declarada",
           "exp_title": "Vectores de exponentes (azul +, naranja −); derecha: cuán bien una ecuación aditiva se comporta como producto", "fixed": "fijo", "fit": "ajuste R²",
           "po_x": "predicho desde Σ (Pearson de logs)", "po_y": "observado", "po_title": "{s}: {n} pares, mediana |brecha| {g:.3f}", "footer": "BioMS Zaku {v} · preset {p} · {d} · semillas cv={c} bootstrap={b}"},
    "pt": {"board": "Quadro de vereditos", "stratum": "estrato", "target": "alvo", "control": "controle", "orig": "originalidade\n1 − máx |Spearman| com um método anterior (log)",
           "spec": "especificidade\n{m}(alvo) − {m}(controle), intervalo 95%", "util": "valor acrescentado sobre covariáveis\nΔ{m}, intervalo 95%",
           "no_util": "utilidade não calculada\n(sem covariáveis)", "identity": "identidade", "oov": "† = aplicado majoritariamente fora da validade declarada",
           "exp_title": "Vetores de expoentes (azul +, laranja −); à direita: o quanto uma equação de soma se comporta como produto", "fixed": "fixo", "fit": "ajuste R²",
           "po_x": "previsto por Σ (Pearson dos logs)", "po_y": "observado", "po_title": "{s}: {n} pares, mediana |lacuna| {g:.3f}", "footer": "BioMS Zaku {v} · preset {p} · {d} · sementes cv={c} bootstrap={b}"},
}


def T(key: str, **kw) -> str:
    return I18N.get(STYLE["language"], I18N["en"])[key].format(**kw)


def apply_style(figcfg: dict | None) -> None:
    """EN: merge user figure settings and push font/palette into matplotlib. ES/PT: aplica o estilo do usuário."""
    figcfg = figcfg or {}
    for k in STYLE:
        if figcfg.get(k) is not None:
            STYLE[k] = figcfg[k]
    for k, v in (figcfg.get("palette") or {}).items():
        if k in C and isinstance(v, str) and v.startswith("#"):
            C[k] = v
    plt.rcParams.update({"font.family": STYLE["font"], "font.size": STYLE["font_size"]})


def _footer(fig, meta: dict | None) -> None:
    if not STYLE["footer"] or not meta:
        return
    fig.text(0.01, 0.002, T("footer", v=meta.get("version", ""), p=meta.get("preset", ""), d=meta.get("date", ""), c=meta.get("seed_cv", ""), b=meta.get("seed_boot", "")),
             fontsize=6, color=C["ink2"], ha="left", va="bottom")


def _title(fig, default: str) -> None:
    t = STYLE["title"] or default
    fig.suptitle(t, fontsize=10.5, color=C["ink"], x=0.01, ha="left", y=0.995)
    if STYLE["subtitle"]:
        fig.text(0.01, 0.975, STYLE["subtitle"], fontsize=8.5, color=C["ink2"], ha="left", va="top")
DIV = LinearSegmentedColormap.from_list("div", ["#eb6834", "#f3d9cf", "#f0f0ee", "#cfe0f5", "#2a78d6"])
SEQ = LinearSegmentedColormap.from_list("seq", ["#f0f0ee", "#2a78d6"])
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": C["grid"], "axes.labelcolor": C["ink2"], "xtick.color": C["ink2"], "ytick.color": C["ink2"],
                     "grid.color": C["grid"], "grid.linewidth": 0.6, "figure.facecolor": C["surface"], "axes.facecolor": C["surface"]})

CAPTIONS = {
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


def exponents(alg: pd.DataFrame, out_dir: Path, meta: dict | None = None) -> None:
    if alg.empty:
        return
    cols = [c for c in alg.columns if c.startswith("e_")]
    strata = sorted(alg.stratum.unique()); order = _order(alg); lab = _label(alg)
    fig, axes = plt.subplots(1, len(strata), figsize=(0.9 * len(cols) + 3.2 * len(strata), 0.27 * len(order) + 1.4), squeeze=False, sharey=True)
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
    _title(fig, T("exp_title")); _footer(fig, meta); fig.subplots_adjust(top=0.93, bottom=0.06)
    _save(fig, out_dir, "exponents")


def predicted_observed(pairs: pd.DataFrame, alg: pd.DataFrame, out_dir: Path, meta: dict | None = None) -> None:
    if pairs.empty:
        return
    p = pairs[~pairs.identity]; strata = sorted(p.stratum.unique()); lab = _label(alg) if not alg.empty else {}
    fig, axes = plt.subplots(1, len(strata), figsize=(3.8 * len(strata), 3.8), squeeze=False)
    for ax, s in zip(axes[0], strata):
        q = p[p.stratum == s]
        ax.plot([-1, 1], [-1, 1], color=C["grid"], lw=1); ax.grid(True); ax.set_axisbelow(True)
        ax.scatter(q.r_log_predicted, q.r_log_observed, s=10, color=C["specific"], alpha=0.55, edgecolor=C["surface"], lw=0.4)
        top = q.nlargest(3, "abs_err_log")
        for k, row in enumerate(top.itertuples(), 1):
            ax.annotate(str(k), (row.r_log_predicted, row.r_log_observed), xytext=(6, -8), textcoords="offset points", fontsize=7, color=C["control"])
        ax.set_xlabel(T("po_x")); ax.set_ylabel(T("po_y"))
        ax.set_title(T("po_title", s=f"{T('stratum')} {s}", n=len(q), g=q.abs_err_log.median()), fontsize=9)
        ax.set_xlim(-1.02, 1.02); ax.set_ylim(-1.02, 1.02); ax.set_aspect("equal")
        txt = "\n".join(f"{k}: {lab.get(r.a_id, r.a_id)} × {lab.get(r.b_id, r.b_id)} ({r.abs_err_log:.2f})" for k, r in enumerate(top.itertuples(), 1))
        ax.text(0.02, 0.98, txt, transform=ax.transAxes, fontsize=6, va="top", color=C["ink2"])
    if STYLE["title"]:
        _title(fig, STYLE["title"]); fig.subplots_adjust(top=0.85)
    _footer(fig, meta); fig.subplots_adjust(bottom=0.16)
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
         "Official (the framework's three): exponents · predicted_observed · board. Supplementary (on request): lineage · sigma_transfer · combination_gain · compass.", ""]
    for name, caps in CAPTIONS.items():
        tags = ("EN", "ES", "PT")
        L += [f"## {name}", ""] + [x for i in order for x in (f"**{tags[i]}** — {caps[i]}", "")]
    (out_dir / "README.md").write_text("\n".join(L), encoding="utf-8")


OFFICIAL = ("exponents", "predicted_observed", "board")            # EN: the framework's three figures (decision 2026-09-10)
SUPPLEMENTARY = ("lineage", "sigma_transfer", "combination_gain", "compass")


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
        board(alg, red, aud, uti, fd, primary, threshold=cfg["algebra"]["redundancy_threshold"], margin=cfg["audit"]["utility_margin"], meta=meta)
    if supplementary is None:
        supplementary = bool(cfg.get("output", {}).get("supplementary_figures", False))
    if supplementary:
        sd = fd / "supplementary"; sd.mkdir(exist_ok=True)
        lineage(red, alg, sd); sigma_transfer(tables.get("sigma_transfer"), sd); combination_gain(tables.get("combinations"), sd); compass(alg, sd)
    write_captions(fd)

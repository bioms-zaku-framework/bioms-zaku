"""
EN: Catalog of indices and predictive equations (CONTRATOS.md §2): loading, validation, precedence.
ES: Catálogo de índices y ecuaciones predictivas (§2): carga, validación, precedencia.
PT: Catálogo de índices e equações preditivas (§2): carga, validação, precedência.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .expr import CompiledExpr, ExpressionError, compile_expr

# EN: canonical variable names always available when the four BIA variables are mapped (50 kHz).
# ES: nombres canónicos disponibles cuando las cuatro variables BIA están mapeadas (50 kHz).
# PT: nomes canônicos disponíveis quando as quatro variáveis BIA estão mapeadas (50 kHz).
CANONICAL_BASE = ("R", "Xc", "H", "W")
DERIVED = ("H_m", "PhA", "II", "Z")
NON_MONOMIAL_DERIVED = ("PhA", "Z")   # EN: usable in expressions, never in a monomial `vector` (§2.3)
VECTOR_TOL_MAX = 1e-4                 # EN: numeric slack for the log-linear identity check only, not an approximation budget
FORMS = ("monomial", "composite", "closed")
KINDS = ("index", "equation")
SOURCES = ("pdf_table", "pdf_text", "pmc_text", "abstract", "review_table", "proposed")   # EN: "proposed" = the researcher's own index, not published (v0.9)
CONFIDENCE = ("high", "medium", "low")
DEFAULT_CONFIDENCE = {"pdf_table": "high", "pdf_text": "high", "pmc_text": "high", "abstract": "medium", "review_table": "low", "proposed": "high"}   # EN: proposed = the author's own formula
REQUIRED = ("id", "label", "authors", "year", "doi", "kind", "target", "form", "frequency_khz", "validity", "provenance")
# EN: what the author says the method measures, as a category the report can compare with the declared kind of the
#     audit target/control (§2.1). A fat index audited against a lean-mass target is expected to "track the control".
# ES/PT: o que o autor diz que o método mede, como categoria comparável ao tipo declarado do alvo/controle da auditoria.
TARGET_KINDS = ("lean_mass", "fat_mass", "body_water", "hydration", "cell_mass", "other")

# EN: the catalogue ships INSIDE the package (src/bioms_zaku/data/), so an installed wheel finds it; found by the Colab
#     simulation of 2026-09-14, when the path pointed outside the package and pip-installed users had no catalogue.
BUILTIN_PATH = Path(__file__).resolve().parent / "data" / "catalog_v1.json"


class CatalogError(ValueError):
    """EN: invalid catalog. ES: catálogo inválido. PT: catálogo inválido."""


@dataclass
class Entry:
    """
    EN: One method. `exprs` maps a branch key to a compiled expression; `None` key = single expression.
    ES: Un método. `exprs` mapea clave de rama -> expresión compilada; clave `None` = expresión única.
    PT: Um método. `exprs` mapeia chave de ramo -> expressão compilada; chave `None` = expressão única.
    """
    id: str
    label: str
    authors: str
    year: int
    doi: str | None
    kind: str
    target: str
    form: str
    frequency_khz: tuple[float, ...]
    validity: dict
    provenance: dict
    vector: dict[str, float] | None = None
    vector_tol: float = 1e-6
    group_coding: dict[str, dict[str, float]] = field(default_factory=dict)
    branch_group: str | None = None          # EN: group column selecting the branch (expr_by_group)
    exprs: dict[str | None, CompiledExpr] = field(default_factory=dict)
    extra_inputs: tuple[str, ...] = ()       # EN: extra continuous inputs (e.g. age) — must be mapped by the user
    identity_of: str | None = None
    status: str = "active"                   # active | excluded (never evaluated; reason in exclusion_reason)
    exclusion_reason: str | None = None
    pmid: int | None = None
    date: str | None = None
    check_example: dict | None = None
    n: int | None = None
    r2: float | None = None
    see: float | None = None
    device: str | None = None
    reference_method: str | None = None
    # EN: who the method was fitted on (descriptive only; never produces a flag). `validity` is the applicability the
    #     author states or tested; outside it the framework flags † and never blocks (§2.1).
    # ES: muestra de derivación (solo descriptiva). `validity` = aplicabilidad declarada o probada; fuera → marca †, nunca bloquea.
    # PT: amostra de derivação (só descritiva). `validity` = aplicabilidade declarada ou testada; fora → marca †, nunca bloqueia.
    derivation_sample: dict | None = None
    target_kind: str | None = None           # EN: one of TARGET_KINDS or None (not declared)
    notes: str | None = None
    # EN: CURATED = the entry went through the documented critical reading of its primary source (catalogo/fontes_primarias_indices/
    #     LEITURAS.md) and was approved; only curated methods are audited by default (`catalog.include: curated`, §2.1/§3).
    #     High provenance confidence alone is NOT curation: a formula copied correctly from a PDF may still lack the reading.
    # ES/PT: curado = passou pela leitura crítica documentada da fonte primária; só curados entram na auditoria por padrão.
    curated: bool = False
    curation_record: str | None = None       # EN: where the reading is recorded (e.g. "LEITURAS.md §2, 2026-09-11")
    proposed: bool = False                   # EN: researcher's own index (provenance.formula_source = "proposed"): no DOI, never curated, never takes precedence, marked ◇

    @property
    def inputs(self) -> frozenset[str]:
        """EN/ES/PT: all names the expressions need (variables, derived, groups, extras)."""
        s: set[str] = set()
        for e in self.exprs.values():
            s |= set(e.names)
        if self.branch_group is not None:
            s.add(self.branch_group)
        return frozenset(s)

    @property
    def confidence(self) -> str:
        return self.provenance.get("confidence", "low")

    @property
    def designed(self) -> bool:
        return self.provenance.get("formula_source") == "designed"

    @property
    def uses_sample_stats(self) -> bool:
        return any(ce.uses_sample_stats for ce in self.exprs.values())

    def evaluate(self, env: Mapping[str, np.ndarray], branch: np.ndarray | None = None, record: list | None = None) -> np.ndarray:
        """
        EN: Evaluate the method on `env` (arrays). With branches, `branch` gives each row's group value.
        ES: Evalúa el método en `env`. Con ramas, `branch` da el valor de grupo por fila.
        PT: Avalia o método em `env`. Com ramos, `branch` dá o valor de grupo por linha.
        """
        if self.form == "closed" or not self.exprs:
            raise CatalogError(f"{self.id}: closed method cannot be evaluated")
        if self.branch_group is None:
            out = self.exprs[None].evaluate(env, record)
            return np.asarray(out, dtype=float)
        if branch is None:
            raise CatalogError(f"{self.id}: branch values for group {self.branch_group!r} are required")
        branch = np.asarray(branch)
        n = len(branch)
        out = np.full(n, np.nan, dtype=float)
        for key, ce in self.exprs.items():
            mask = branch.astype(str) == str(key)
            if mask.any():
                sub = {k: (v[mask] if isinstance(v, np.ndarray) and np.ndim(v) == 1 and len(v) == n else v) for k, v in env.items()}
                out[mask] = np.asarray(ce.evaluate(sub, record), dtype=float)
        return out


@dataclass
class Catalog:
    version: str
    conventions: dict
    entries: list[Entry]
    source_path: str | None = None
    doi_status: dict[str, str] = field(default_factory=dict)

    def __getitem__(self, method_id: str) -> Entry:
        for e in self.entries:
            if e.id == method_id:
                return e
        raise KeyError(method_id)

    def ids(self) -> list[str]:
        return [e.id for e in self.entries]

    def sorted_by_precedence(self) -> list[Entry]:
        """
        EN: precedence order: year, then date (if any), then DOI (lexicographic). Fixed rule (§2.2).
        ES: orden de precedencia: año, fecha (si hay), DOI. Regla fija.
        PT: ordem de precedência: ano, data (se houver), DOI. Regra fixa.
        """
        # EN: proposed (unpublished) indices come after every published method whatever their year (v0.9)
        return sorted(self.entries, key=lambda e: (e.proposed or e.designed, e.year, e.date or "9999-99-99", e.doi or f"pmid:{e.pmid}" if e.doi or e.pmid else e.id))


# ----------------------------------------------------------------------------------------------
def load_catalog(path: str | os.PathLike | None = None, *, resolve_doi: bool = False,
                 cache_path: str | os.PathLike | None = None, rng_seed: int = 0) -> Catalog:
    """
    EN: Load and validate a catalog JSON (default: built-in). Validation is strict and happens here, not at run time.
    ES: Carga y valida un catálogo JSON (por defecto: el incorporado). La validación es estricta y ocurre aquí.
    PT: Carrega e valida um catálogo JSON (padrão: o embutido). A validação é estrita e acontece aqui.
    """
    p = Path(path) if path is not None else BUILTIN_PATH
    raw = json.loads(Path(p).read_text(encoding="utf-8"))
    return build_catalog(raw, source_path=str(p), resolve_doi=resolve_doi, cache_path=cache_path, rng_seed=rng_seed)


def build_catalog(raw: dict, *, source_path: str | None = None, resolve_doi: bool = False,
                  cache_path: str | os.PathLike | None = None, rng_seed: int = 0) -> Catalog:
    for k in ("catalog_version", "conventions", "entries"):
        if k not in raw:
            raise CatalogError(f"catalog missing top-level key {k!r}")
    conv = raw["conventions"]
    extra_canon = tuple(conv.get("extra_variables", []))     # EN: e.g. ["R5","Xc5","R250"] for multi-frequency
    canon = CANONICAL_BASE + DERIVED + extra_canon
    entries: list[Entry] = []
    seen: set[str] = set()
    for i, e in enumerate(raw["entries"]):
        entries.append(_parse_entry(e, i, canon, rng_seed))
        if entries[-1].id in seen:
            raise CatalogError(f"duplicate id {entries[-1].id!r}")
        seen.add(entries[-1].id)
    ids = {e.id for e in entries}
    for e in entries:
        if e.identity_of is not None and e.identity_of not in ids:
            raise CatalogError(f"{e.id}: identity_of {e.identity_of!r} not in catalog")
    cat = Catalog(version=str(raw["catalog_version"]), conventions=conv, entries=entries, source_path=source_path)
    if resolve_doi:
        cat.doi_status = _resolve_dois([e.doi for e in entries if e.doi], cache_path)
    return cat


def _parse_entry(e: dict, i: int, canon: tuple[str, ...], rng_seed: int) -> Entry:
    where = f"entry #{i} ({e.get('id', '?')})"
    proposed = isinstance(e.get("provenance"), dict) and e["provenance"].get("formula_source") == "proposed"
    if proposed:
        # EN: a researcher's own index (v0.9): no publication, so no DOI/year/validity are demanded; defaults are explicit and
        #     recorded. `target` (what it intends to measure), `authors` and `expr` stay required. Never curated, never precedence.
        import datetime as _dt
        if e.get("curated"):
            raise CatalogError(f"{where}: a proposed index cannot be curated")
        if "expr" not in e and "expr_by_group" not in e:
            raise CatalogError(f"{where}: a proposed index needs `expr` (its formula in R, Xc, H, W)")
        e = {"label": e.get("id"), "year": _dt.date.today().year, "doi": None, "kind": "index", "frequency_khz": 50,
             "form": "monomial" if e.get("vector") else "composite", "validity": {"age": None, "bmi": None, "sex": None, "population": None}, **e}
        e["provenance"] = {"confidence": "high", "verified_by": e.get("authors", "author"), "verified_on": _dt.date.today().isoformat(), **e["provenance"]}   # EN: the formula is the author's own text: no transcription uncertainty; verifier = author, date = today
        e["validity"] = {"age": None, "bmi": None, "sex": None, "population": None, **(e["validity"] or {})}
    for k in REQUIRED:
        if k not in e and not (proposed and k == "doi"):
            raise CatalogError(f"{where}: missing required field {k!r}")
    if e["kind"] not in KINDS:
        raise CatalogError(f"{where}: kind must be one of {KINDS}")
    if e["form"] not in FORMS:
        raise CatalogError(f"{where}: form must be one of {FORMS}")
    if not isinstance(e["year"], int):
        raise CatalogError(f"{where}: year must be an integer")
    if not e.get("doi") and not e.get("pmid") and not proposed:
        raise CatalogError(f"{where}: doi is required (pmid accepted only when the work has no DOI)")
    fk = e["frequency_khz"]
    if isinstance(fk, (list, tuple)):
        if not fk or not all(isinstance(x, (int, float)) for x in fk):
            raise CatalogError(f"{where}: frequency_khz list must contain numbers")
    elif not isinstance(fk, (int, float)):
        raise CatalogError(f"{where}: frequency_khz must be a number or a list of numbers")
    prov = e["provenance"]
    for k in ("formula_source", "verified_by", "verified_on"):
        if k not in prov:
            raise CatalogError(f"{where}: provenance missing {k!r}")
    if prov["formula_source"] not in SOURCES:
        raise CatalogError(f"{where}: provenance.formula_source must be one of {SOURCES}")
    prov = dict(prov)
    prov.setdefault("confidence", DEFAULT_CONFIDENCE[prov["formula_source"]])
    if prov["confidence"] not in CONFIDENCE:
        raise CatalogError(f"{where}: provenance.confidence must be one of {CONFIDENCE}")
    # EN: confidence may be lowered by the curator, never raised above the source default.
    # ES: la confianza puede bajarse, nunca subirse por encima del valor por defecto de la fuente.
    # PT: a confiança pode ser rebaixada, nunca elevada acima do padrão da fonte.
    if CONFIDENCE.index(prov["confidence"]) < CONFIDENCE.index(DEFAULT_CONFIDENCE[prov["formula_source"]]):
        raise CatalogError(f"{where}: confidence {prov['confidence']!r} exceeds what source {prov['formula_source']!r} allows")
    if e.get("target_kind") is not None and e["target_kind"] not in TARGET_KINDS:
        raise CatalogError(f"{where}: target_kind must be one of {TARGET_KINDS}")
    if e.get("status", "active") not in ("active", "excluded"):
        raise CatalogError(f"{where}: status must be active or excluded")
    if e.get("status") == "excluded" and not e.get("exclusion_reason"):
        raise CatalogError(f"{where}: excluded entries must state exclusion_reason")
    if e.get("curated", False):
        if prov["confidence"] != "high" or prov["formula_source"] not in ("pdf_text", "pdf_table"):
            raise CatalogError(f"{where}: curated entries must have a primary-source formula (pdf_text/pdf_table) with confidence high")
        if not e.get("curation_record"):
            raise CatalogError(f"{where}: curated entries must cite their curation_record (where the reading is documented)")
    val = e["validity"]
    for k in ("age", "bmi", "sex", "population"):
        if k not in val:
            raise CatalogError(f"{where}: validity missing {k!r} (use null if unknown)")

    group_coding = e.get("group_coding") or {}
    extra_inputs = tuple(e.get("extra_inputs") or ())
    allowed = list(canon) + list(group_coding) + list(extra_inputs)

    exprs: dict[str | None, CompiledExpr] = {}
    branch_group = None
    if e["form"] == "closed":
        if "expr" in e or "expr_by_group" in e:
            raise CatalogError(f"{where}: closed method must not carry an expression")
    else:
        if ("expr" in e) == ("expr_by_group" in e):
            raise CatalogError(f"{where}: exactly one of expr / expr_by_group is required")
        try:
            if "expr" in e:
                exprs[None] = compile_expr(e["expr"], allowed)
            else:
                ebg = e["expr_by_group"]
                if not isinstance(ebg, dict) or len(ebg) != 1:
                    raise CatalogError(f"{where}: expr_by_group must map exactly one group to its branches")
                branch_group = next(iter(ebg))
                if branch_group not in group_coding and branch_group not in extra_inputs:
                    raise CatalogError(f"{where}: branch group {branch_group!r} must be declared in group_coding or extra_inputs")
                for key, src in ebg[branch_group].items():
                    exprs[str(key)] = compile_expr(src, allowed)
        except ExpressionError as ex:
            raise CatalogError(f"{where}: {ex}") from None

    vector = e.get("vector")
    vector_tol = float(e.get("vector_tol", 1e-6))
    if e["form"] == "monomial":
        if not vector:
            raise CatalogError(f"{where}: monomial requires vector")
        if branch_group is not None:
            raise CatalogError(f"{where}: monomial cannot have branches")
        # EN: §2.3 exactness — a catalog vector is exact or it is not a vector. Non-monomial derived names (PhA = atan,
        #     Z = sqrt of a sum) cannot appear in `vector`; such methods are `composite` and get a fitted vector with R².
        # ES: §2.3 exactitud — el vector del catálogo es exacto o no es vector; PhA y Z no pueden aparecer en `vector`.
        # PT: §2.3 exatidão — o vetor do catálogo é exato ou não é vetor; PhA e Z não podem aparecer em `vector`.
        bad = sorted(k for k in vector if k in NON_MONOMIAL_DERIVED)
        if bad:
            raise CatalogError(f"{where}: {bad} are not monomials in the base variables; declare form 'composite' (fitted vector, fit R² reported)")
        if vector_tol > VECTOR_TOL_MAX:
            raise CatalogError(f"{where}: vector_tol {vector_tol} exceeds {VECTOR_TOL_MAX}; a monomial vector must be exact")
        _check_vector(where, exprs[None], vector, vector_tol, rng_seed)
    elif vector:
        raise CatalogError(f"{where}: vector only allowed for monomial")

    ent = Entry(
        id=e["id"], label=e["label"], authors=e["authors"], year=e["year"], doi=e.get("doi"), kind=e["kind"],
        target=e["target"], form=e["form"], frequency_khz=tuple(float(x) for x in (fk if isinstance(fk, (list, tuple)) else [fk])), validity=val, provenance=prov,
        vector=vector, vector_tol=vector_tol, group_coding=group_coding, branch_group=branch_group, exprs=exprs,
        extra_inputs=extra_inputs, identity_of=e.get("identity_of"), status=e.get("status", "active"),
        exclusion_reason=e.get("exclusion_reason"), pmid=e.get("pmid"), date=e.get("date"), derivation_sample=e.get("derivation_sample"),
        check_example=e.get("check_example"), n=e.get("n"), r2=e.get("r2"), see=e.get("see"), target_kind=e.get("target_kind"),
        device=e.get("device"), reference_method=e.get("reference_method"), notes=e.get("notes"),
        curated=bool(e.get("curated", False)), curation_record=e.get("curation_record"), proposed=proposed,
    )
    if ent.check_example is not None:
        _check_example(where, ent)
    return ent


def _check_vector(where: str, ce: CompiledExpr, vector: dict, tol: float, seed: int) -> None:
    """
    EN: §2.3 — evaluate expr on 1000 random positive inputs, fit log-linear, require coefficients == vector.
    ES: §2.3 — evalúa expr en 1000 entradas positivas aleatorias, ajusta log-lineal, exige coeficientes == vector.
    PT: §2.3 — avalia expr em 1000 entradas positivas aleatórias, ajusta log-linear, exige coeficientes == vector.
    """
    rng = np.random.default_rng(seed)
    n = 1000
    names = sorted(ce.names)
    # EN: sample base variables in physiological ranges; derived ones are computed from them.
    base = {"R": rng.uniform(300, 800, n), "Xc": rng.uniform(30, 90, n), "H": rng.uniform(150, 190, n), "W": rng.uniform(45, 120, n)}
    env = dict(base)
    env["H_m"] = env["H"] / 100.0
    env["PhA"] = np.degrees(np.arctan(env["Xc"] / env["R"]))
    env["II"] = env["H"] ** 2 / env["R"]
    env["Z"] = np.sqrt(env["R"] ** 2 + env["Xc"] ** 2)
    for k in names:
        if k not in env:
            env[k] = rng.uniform(0.5, 2.0, n)   # EN: extra multi-frequency variables, positive
    y = np.asarray(ce.evaluate(env), dtype=float)
    if not np.all(np.isfinite(y)) or not np.all(y > 0):
        raise CatalogError(f"{where}: monomial expr must be positive on positive inputs")
    keys = [k for k in ("R", "Xc", "H", "W") if k in env] + [k for k in names if k not in ("R", "Xc", "H", "W", "H_m", "PhA", "II", "Z")]
    X = np.column_stack([np.ones(n)] + [np.log(env[k]) for k in keys])
    beta, *_ = np.linalg.lstsq(X, np.log(y), rcond=None)
    fitted = dict(zip(keys, beta[1:]))
    # EN: derived names in `vector` (H_m, PhA, II, Z) are re-expressed on base variables for the comparison.
    expect = {k: 0.0 for k in keys}
    for k, v in vector.items():
        v = float(v)
        if k == "H_m":
            expect["H"] += v
        elif k == "II":
            expect["H"] += 2 * v; expect["R"] -= v
        elif k in expect:
            expect[k] += v
        else:
            raise CatalogError(f"{where}: vector key {k!r} unknown")
    for k in keys:
        if abs(fitted[k] - expect[k]) > tol:
            raise CatalogError(f"{where}: vector inconsistent with expr for {k!r}: fitted {fitted[k]:.6f} vs declared {expect[k]:.6f} (tol {tol})")


def _check_example(where: str, ent: Entry) -> None:
    """
    EN: §2.3 — published numeric example must be reproduced within `tol`.
    ES: §2.3 — el ejemplo numérico publicado debe reproducirse dentro de `tol`.
    PT: §2.3 — o exemplo numérico publicado deve ser reproduzido dentro de `tol`.
    """
    ex = ent.check_example
    for k in ("inputs", "expected", "tol"):
        if k not in ex:
            raise CatalogError(f"{where}: check_example missing {k!r}")
    env = {k: float(v) for k, v in ex["inputs"].items()}
    if "H" in env:
        env.setdefault("H_m", env["H"] / 100.0)
        if "R" in env:
            env.setdefault("II", env["H"] ** 2 / env["R"])
    if "R" in env and "Xc" in env:
        env.setdefault("PhA", float(np.degrees(np.arctan(env["Xc"] / env["R"]))))
        env.setdefault("Z", float(np.sqrt(env["R"] ** 2 + env["Xc"] ** 2)))
    try:
        if ent.branch_group is None:
            got = float(ent.exprs[None].evaluate(env))
        else:
            key = str(int(env[ent.branch_group])) if float(env[ent.branch_group]).is_integer() else str(env[ent.branch_group])
            got = float(ent.exprs[key].evaluate(env))
    except (ExpressionError, KeyError) as e:
        raise CatalogError(f"{where}: check_example cannot be evaluated: {e}") from None
    if abs(got - float(ex["expected"])) > float(ex["tol"]):
        raise CatalogError(f"{where}: check_example failed: got {got:.4f}, expected {ex['expected']} ± {ex['tol']}")


def _resolve_dois(dois: list[str], cache_path) -> dict[str, str]:
    """
    EN: resolve each DOI at doi.org handle API (responseCode 1 = exists); cached with date; no network -> 'unknown'.
    ES: resuelve cada DOI en la API de doi.org; con caché; sin red -> 'unknown'.
    PT: resolve cada DOI na API do doi.org; com cache; sem rede -> 'unknown'.
    """
    cache_path = Path(cache_path) if cache_path else Path.home() / ".cache" / "bioms_zaku" / "doi_cache.json"
    cache: dict[str, dict] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for d in dois:
        if d in cache:
            out[d] = cache[d]["status"]; continue
        try:
            with urllib.request.urlopen("https://doi.org/api/handles/" + urllib.request.quote(d, safe="/()"), timeout=15) as r:
                code = json.load(r).get("responseCode")
            status = "ok" if code == 1 else "not_found"
        except Exception:
            status = "unknown"
        out[d] = status
        if status != "unknown":
            cache[d] = {"status": status, "checked_on": time.strftime("%Y-%m-%d")}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return out

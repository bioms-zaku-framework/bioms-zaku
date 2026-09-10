"""
EN: Safe expression evaluator (whitelist AST). No `eval`, no attributes, no subscripts, no strings.
ES: Evaluador seguro de expresiones (AST con lista blanca). Sin `eval`, sin atributos, sin índices, sin cadenas.
PT: Avaliador seguro de expressões (AST com lista branca). Sem `eval`, sem atributos, sem colchetes, sem strings.

Grammar / Gramática (CONTRATOS.md §2.4):
  numbers; allowed names; + - * / ** ( ); unary + -; functions log exp sqrt atan atan2 abs min max; constant pi.
"""
from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

import numpy as np

# EN: functions allowed; each maps to a numpy ufunc (works on scalars and arrays).
# ES: funciones permitidas; cada una mapea a una ufunc de numpy (escalares y arreglos).
# PT: funções permitidas; cada uma mapeia para uma ufunc do numpy (escalares e vetores).
_FUNCS: dict[str, Callable] = {
    "log": np.log, "exp": np.exp, "sqrt": np.sqrt, "atan": np.arctan, "atan2": np.arctan2,
    "abs": np.abs, "min": np.minimum, "max": np.maximum,
}
_ARITY = {"log": 1, "exp": 1, "sqrt": 1, "atan": 1, "atan2": 2, "abs": 1, "min": 2, "max": 2}
_CONSTS = {"pi": math.pi}
_BINOPS = {ast.Add: np.add, ast.Sub: np.subtract, ast.Mult: np.multiply, ast.Div: np.divide, ast.Pow: np.power}
_UNOPS = {ast.USub: np.negative, ast.UAdd: np.positive}


class ExpressionError(ValueError):
    """EN: invalid expression under the whitelist grammar. ES: expresión inválida. PT: expressão inválida."""


@dataclass(frozen=True)
class CompiledExpr:
    """
    EN: A validated expression: source text, referenced names, and an evaluator.
    ES: Expresión validada: texto fuente, nombres referenciados y evaluador.
    PT: Expressão validada: texto-fonte, nomes referenciados e avaliador.
    """
    source: str
    names: frozenset[str]
    _tree: ast.AST

    def evaluate(self, env: Mapping[str, np.ndarray | float]) -> np.ndarray | float:
        """
        EN: Evaluate with `env` mapping names to scalars/arrays. Missing name -> ExpressionError.
        ES: Evalúa con `env` (nombre -> escalar/arreglo). Nombre ausente -> ExpressionError.
        PT: Avalia com `env` (nome -> escalar/vetor). Nome ausente -> ExpressionError.
        """
        missing = self.names - set(env)
        if missing:
            raise ExpressionError(f"missing inputs for expression {self.source!r}: {sorted(missing)}")
        return _eval_node(self._tree, env)


def compile_expr(source: str, allowed_names: Sequence[str]) -> CompiledExpr:
    """
    EN: Parse and validate `source` against the whitelist; only `allowed_names` may appear as variables.
    ES: Analiza y valida `source` contra la lista blanca; solo `allowed_names` pueden aparecer como variables.
    PT: Analisa e valida `source` contra a lista branca; só `allowed_names` podem aparecer como variáveis.
    """
    if not isinstance(source, str) or not source.strip():
        raise ExpressionError("expression must be a non-empty string")
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except SyntaxError as e:  # pragma: no cover - message path
        raise ExpressionError(f"syntax error in expression {source!r}: {e.msg}") from None
    allowed = set(allowed_names) | set(_CONSTS)
    names: set[str] = set()
    _validate(tree.body, allowed, names)
    return CompiledExpr(source=source.strip(), names=frozenset(names - set(_CONSTS)), _tree=tree.body)


def _validate(node: ast.AST, allowed: set[str], names: set[str]) -> None:
    # EN: recursive whitelist. ES: lista blanca recursiva. PT: lista branca recursiva.
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ExpressionError(f"only numeric constants are allowed, got {node.value!r}")
        return
    if isinstance(node, ast.Name):
        if node.id in _FUNCS:
            raise ExpressionError(f"function {node.id!r} used without call")
        if node.id not in allowed:
            raise ExpressionError(f"unknown name {node.id!r} (allowed: {sorted(allowed)})")
        names.add(node.id)
        return
    if isinstance(node, ast.BinOp):
        if type(node.op) not in _BINOPS:
            raise ExpressionError(f"operator {type(node.op).__name__} not allowed")
        _validate(node.left, allowed, names); _validate(node.right, allowed, names)
        return
    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in _UNOPS:
            raise ExpressionError(f"unary operator {type(node.op).__name__} not allowed")
        _validate(node.operand, allowed, names)
        return
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise ExpressionError("only whitelisted functions may be called")
        if node.keywords or len(node.args) != _ARITY[node.func.id]:
            raise ExpressionError(f"function {node.func.id!r} expects {_ARITY[node.func.id]} positional argument(s)")
        for a in node.args:
            _validate(a, allowed, names)
        return
    raise ExpressionError(f"construct {type(node).__name__} not allowed")


def _eval_node(node: ast.AST, env: Mapping[str, np.ndarray | float]):
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return _CONSTS[node.id] if node.id in _CONSTS else env[node.id]
    if isinstance(node, ast.BinOp):
        return _BINOPS[type(node.op)](_eval_node(node.left, env), _eval_node(node.right, env))
    if isinstance(node, ast.UnaryOp):
        return _UNOPS[type(node.op)](_eval_node(node.operand, env))
    if isinstance(node, ast.Call):
        return _FUNCS[node.func.id](*[_eval_node(a, env) for a in node.args])
    raise ExpressionError("unreachable")  # pragma: no cover

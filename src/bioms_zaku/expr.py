"""
EN: Safe expression evaluator (whitelist AST). No `eval`, no attributes, no subscripts, no strings.

Grammar / Gramática (CONTRATOS.md §2.4):
  numbers; allowed names; + - * / ** ( ); unary + -; functions log exp sqrt atan atan2 abs min max; sample statistics
  mean median sd (v0.9, recorded); constants pi, e.
"""
from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

import numpy as np

# EN: functions allowed; each maps to a numpy ufunc (works on scalars and arrays).
_FUNCS: dict[str, Callable] = {
    "log": np.log, "exp": np.exp, "sqrt": np.sqrt, "atan": np.arctan, "atan2": np.arctan2,
    "abs": np.abs, "min": np.minimum, "max": np.maximum,
}
# EN: SAMPLE STATISTICS (v0.9): `mean(x)`, `median(x)`, `sd(x)` reduce their argument over the rows being evaluated (one stratum,
#     the complete cases that enter the algebra) to ONE number, broadcast to every row. An index using them is not a fixed
#     formula: its values depend on the sample. Every value used is recorded (see CompiledExpr.evaluate(record=...)), written to
#     the manifest and reported. NaN rows are ignored (nan-aware reductions); sd uses ddof=1.
_STATS: dict[str, Callable] = {"mean": np.nanmean, "median": np.nanmedian, "sd": lambda x: np.nanstd(x, ddof=1)}
_FUNCS.update(_STATS)
_ARITY = {"log": 1, "exp": 1, "sqrt": 1, "atan": 1, "atan2": 2, "abs": 1, "min": 2, "max": 2, "mean": 1, "median": 1, "sd": 1}
_CONSTS = {"pi": math.pi, "e": math.e}
_BINOPS = {ast.Add: np.add, ast.Sub: np.subtract, ast.Mult: np.multiply, ast.Div: np.divide, ast.Pow: np.power}
_UNOPS = {ast.USub: np.negative, ast.UAdd: np.positive}


class ExpressionError(ValueError):
    """EN: invalid expression under the whitelist grammar. ES: expresión inválida. PT: expressão inválida."""


@dataclass(frozen=True)
class CompiledExpr:
    """
    EN: A validated expression: source text, referenced names, and an evaluator.
    """
    source: str
    names: frozenset[str]
    _tree: ast.AST

    @property
    def uses_sample_stats(self) -> bool:
        """EN: True when the expression calls mean/median/sd (its values depend on the sample it is evaluated on)."""
        return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _STATS for n in ast.walk(self._tree))

    def evaluate(self, env: Mapping[str, np.ndarray | float], record: list | None = None) -> np.ndarray | float:
        """
        EN: Evaluate with `env` mapping names to scalars/arrays. Missing name -> ExpressionError. When `record` (a list) is
            given, every sample statistic evaluated is appended to it as (text, value), e.g. ("mean(PhA)", 5.83).
        """
        missing = self.names - set(env)
        if missing:
            raise ExpressionError(f"missing inputs for expression {self.source!r}: {sorted(missing)}")
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):   # EN: 1/0, log(-x), x**200 become inf/nan; callers count and reject them
            return _eval_node(self._tree, env, record)


def compile_expr(source: str, allowed_names: Sequence[str]) -> CompiledExpr:
    """
    EN: Parse and validate `source` against the whitelist; only `allowed_names` may appear as variables.
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


def _eval_node(node: ast.AST, env: Mapping[str, np.ndarray | float], record: list | None = None):
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return _CONSTS[node.id] if node.id in _CONSTS else env[node.id]
    if isinstance(node, ast.BinOp):
        return _BINOPS[type(node.op)](_eval_node(node.left, env, record), _eval_node(node.right, env, record))
    if isinstance(node, ast.UnaryOp):
        return _UNOPS[type(node.op)](_eval_node(node.operand, env, record))
    if isinstance(node, ast.Call):
        args = [_eval_node(a, env, record) for a in node.args]
        if node.func.id in _STATS:
            value = float(_STATS[node.func.id](np.asarray(args[0], dtype=float)))
            if record is not None:
                record.append((f"{node.func.id}({ast.unparse(node.args[0])})", value))
            return value
        return _FUNCS[node.func.id](*args)
    raise ExpressionError("unreachable")  # pragma: no cover

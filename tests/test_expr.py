"""EN: whitelist parser contract (§2.4). ES: contrato del parser. PT: contrato do parser."""
import math
import numpy as np
import pytest
from bioms_zaku.expr import ExpressionError, compile_expr

NAMES = ["R", "Xc", "H", "H_m", "W", "PhA", "II", "sexo", "idade"]


def test_arithmetic_and_functions():
    ce = compile_expr("0.477*II + 0.037*R - 22.426 + sqrt(W) + atan(Xc/R)*180/pi + max(H, 1)", NAMES)
    env = {"II": 51.16, "R": 513.0, "W": 63.4, "Xc": 58.0, "H": 162.0}
    got = float(ce.evaluate(env))
    exp = 0.477 * 51.16 + 0.037 * 513 - 22.426 + math.sqrt(63.4) + math.degrees(math.atan(58 / 513)) + 162
    assert abs(got - exp) < 1e-12
    assert ce.names == frozenset({"II", "R", "W", "Xc", "H"})


def test_vectorised_evaluation():
    ce = compile_expr("H**2 / R", NAMES)
    out = ce.evaluate({"H": np.array([160.0, 180.0]), "R": np.array([500.0, 400.0])})
    assert np.allclose(out, [51.2, 81.0])


@pytest.mark.parametrize("bad", [
    "__import__('os').system('rm -rf /')",   # call to non-whitelisted name
    "R.real", "R[0]", "'a'", "R if R else Xc", "lambda: 1", "R and Xc", "R == Xc", "R % 2", "R // 2",
    "log(R, 2)",          # wrong arity
    "log",                # function without call
    "unknown_var + 1",    # name not allowed
    "True", "None", "",
])
def test_rejects_non_whitelisted(bad):
    with pytest.raises(ExpressionError):
        compile_expr(bad, NAMES)


def test_missing_input_at_evaluation():
    ce = compile_expr("R / H_m", NAMES)
    with pytest.raises(ExpressionError):
        ce.evaluate({"R": 500.0})

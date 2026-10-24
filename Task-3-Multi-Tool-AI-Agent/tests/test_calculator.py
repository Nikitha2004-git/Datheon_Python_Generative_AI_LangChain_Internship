import pytest

from agent.tools.calculator import CalculatorError, calculate, evaluate


@pytest.mark.parametrize("expr,expected", [
    ("1 + 2", 3), ("10 - 4", 6), ("6 * 7", 42), ("9 / 2", 4.5),
    ("2 + 3 * 4", 14), ("(2 + 3) * 4", 20), ("(1250 * 3) + 450", 4200),
    ("2 ** 10", 1024), ("2 ^ 3", 8), ("-5 + 2", -3), ("7 // 2", 3), ("7 % 3", 1),
    ("sqrt(144)", 12), ("abs(-3)", 3), ("max(1, 5, 3)", 5), ("round(2.567, 2)", 2.57),
])
def test_valid_expressions(expr, expected):
    assert evaluate(expr) == pytest.approx(expected)


def test_precedence_and_parentheses():
    assert evaluate("2 + 3 * 4 ** 2") == 50
    assert evaluate("(2 + 3) * 4 ** 2") == 80


def test_constants():
    assert evaluate("pi") == pytest.approx(3.14159265)


def test_calculate_returns_readable_string():
    assert calculate("(1250 * 3) + 450") == "(1250 * 3) + 450 = 4200"
    assert calculate("10 / 4") == "10 / 4 = 2.5"


@pytest.mark.parametrize("expr", ["1 / 0", "5 // 0", "5 % 0", "1 / (2 - 2)"])
def test_division_by_zero(expr):
    with pytest.raises(CalculatorError, match="Division by zero"):
        evaluate(expr)
    assert "Division by zero" in calculate(expr)


@pytest.mark.parametrize("expr", ["", "   ", "2 +", "((1)", "abc def", "1 +* 2", "1,250 * 2"])
def test_invalid_input(expr):
    with pytest.raises(CalculatorError):
        evaluate(expr)
    assert calculate(expr).startswith("Calculator error")


@pytest.mark.parametrize("expr", [
    "__import__('os').system('echo hi')",
    "import os",
    "open('.env').read()",
    "exec('print(1)')",
    "eval('1+1')",
    "().__class__.__bases__",
    "[1,2,3][0]",
    "lambda: 1",
    "'abc' * 3",
    "True + 1",
    "x + 1",
    "sqrt.__call__(4)",
    "os.getcwd()",
    "sqrt(x=4)",
])
def test_code_execution_rejected(expr):
    with pytest.raises(CalculatorError):
        evaluate(expr)
    assert calculate(expr).startswith("Calculator error")


def test_huge_power_rejected():
    with pytest.raises(CalculatorError):
        evaluate("9 ** 9 ** 9")
    with pytest.raises(CalculatorError):
        evaluate("10 ** 5000")


def test_too_long_expression():
    with pytest.raises(CalculatorError, match="too long"):
        evaluate("1+" * 200 + "1")


def test_sqrt_negative_gives_friendly_error():
    assert "Calculator error" in calculate("sqrt(-1)")


def test_non_string_input():
    with pytest.raises(CalculatorError):
        evaluate(None)  # type: ignore[arg-type]

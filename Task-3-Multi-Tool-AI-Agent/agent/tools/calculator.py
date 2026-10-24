"""Safe math calculator based on Python's ``ast`` module.

The expression is parsed into a syntax tree and ONLY whitelisted node types are evaluated.
``eval()``/``exec()`` are never used, so imports, attribute access, indexing, lambdas and
arbitrary function calls are rejected.

Supported: + - * / // % ** , unary +/-, parentheses,
functions: sqrt, abs, round, min, max, floor, ceil, log, log10, exp, sin, cos, tan
constants: pi, e
"""
from __future__ import annotations

import ast
import math
import operator

MAX_EXPRESSION_LENGTH = 200
MAX_EXPONENT = 1000
MAX_RESULT_BITS = 10_000


class CalculatorError(ValueError):
    """Raised for invalid or unsafe expressions (message is beginner-friendly)."""


_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "sqrt": math.sqrt, "abs": abs, "round": round, "min": min, "max": max,
    "floor": math.floor, "ceil": math.ceil, "log": math.log, "log10": math.log10,
    "exp": math.exp, "sin": math.sin, "cos": math.cos, "tan": math.tan,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}


def _check_power(base, exponent):
    if abs(exponent) > MAX_EXPONENT:
        raise CalculatorError(f"Exponent too large (limit is {MAX_EXPONENT}).")
    if isinstance(base, int) and isinstance(exponent, int) and exponent > 0 and abs(base) > 1:
        if exponent * math.log2(abs(base)) > MAX_RESULT_BITS:
            raise CalculatorError("Result would be too large to compute safely.")


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalculatorError("Only numbers are allowed (no text or True/False).")
        return node.value
    if isinstance(node, ast.BinOp):
        op = _BINARY_OPS.get(type(node.op))
        if op is None:
            raise CalculatorError("That operator is not supported.")
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow):
            _check_power(left, right)
        try:
            return op(left, right)
        except ZeroDivisionError:
            raise CalculatorError("Division by zero is not allowed.") from None
        except OverflowError:
            raise CalculatorError("Number is too large.") from None
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise CalculatorError("That operator is not supported.")
        return op(_eval(node.operand))
    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise CalculatorError(f"Unknown name '{node.id}'. Only 'pi' and 'e' are allowed.")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise CalculatorError(
                "Only these functions are allowed: " + ", ".join(sorted(_FUNCTIONS)) + "."
            )
        if node.keywords:
            raise CalculatorError("Keyword arguments are not allowed.")
        args = [_eval(a) for a in node.args]
        try:
            return _FUNCTIONS[node.func.id](*args)
        except (ValueError, TypeError, OverflowError) as exc:
            raise CalculatorError(f"Cannot compute {node.func.id}(): {exc}") from None
    raise CalculatorError(
        "Unsupported expression. Only numbers, operators, parentheses and "
        "approved functions are allowed."
    )


def evaluate(expression: str):
    """Safely evaluate ``expression`` and return an int or float."""
    if not isinstance(expression, str) or not expression.strip():
        raise CalculatorError("Please provide a math expression, e.g. (1250 * 3) + 450.")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise CalculatorError(f"Expression too long (limit {MAX_EXPRESSION_LENGTH} characters).")
    cleaned = expression.strip().replace("^", "**")
    try:
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError:
        raise CalculatorError("Invalid expression: could not understand the syntax.") from None
    except (ValueError, RecursionError, MemoryError):
        raise CalculatorError("Invalid or too complicated expression.") from None
    try:
        result = _eval(tree)
    except RecursionError:
        raise CalculatorError("Expression is nested too deeply.") from None
    if isinstance(result, float) and (math.isnan(result) or math.isinf(result)):
        raise CalculatorError("Result is not a finite number.")
    return result


def format_number(value) -> str:
    if isinstance(value, float):
        if value.is_integer() and abs(value) < 1e15:
            return str(int(value))
        return f"{value:.10g}"
    return str(value)


def calculate(expression: str) -> str:
    """Tool entry point: always returns a string (never raises)."""
    try:
        return f"{expression.strip()} = {format_number(evaluate(expression))}"
    except CalculatorError as exc:
        return f"Calculator error: {exc}"

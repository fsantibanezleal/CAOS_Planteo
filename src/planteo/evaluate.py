"""Numbers from expressions.

The dynamics family integrates a system whose right-hand side is a closed-set expression, so the
representation needs a way to compute one: given a value for every name an expression reads, return
the number it denotes. Every node is covered but the indexed sum, which is refused rather than
approximated, because a map from names to numbers cannot say what a set's members are, and a number
computed without them would be one the document never stated.

Arithmetic errors are not caught here. A division by zero, or a negative base raised to a fractional
power, is a property of the model at that point, and whoever integrates it decides what that means.
"""

from __future__ import annotations

from collections.abc import Mapping

from .expressions import BigSum, Conditional, Constant, Expression, Power, Product, Ref, Sum
from .relations import Compare, ForAll, Logical, Rate, Relation


class NotEvaluable(ValueError):
    """An expression contains a construct the evaluator cannot compute from scalar values."""


def evaluate(expression: Expression, values: Mapping[str, float]) -> float:
    """The number ``expression`` denotes when every name it reads takes its value from ``values``."""
    if isinstance(expression, Constant):
        return float(expression.value)
    if isinstance(expression, Ref):
        try:
            return float(values[expression.name])
        except KeyError:
            raise NotEvaluable(f"no value for {expression.name!r}") from None
    if isinstance(expression, Sum):
        return float(sum(evaluate(term, values) for term in expression.terms))
    if isinstance(expression, Product):
        result = 1.0
        for factor in expression.factors:
            result *= evaluate(factor, values)
        return result
    if isinstance(expression, Power):
        base = evaluate(expression.base, values)
        result = base ** float(expression.exponent)
        if isinstance(result, complex):
            raise ArithmeticError(
                f"a negative base ({base}) raised to the fractional power {expression.exponent}"
            )
        return float(result)
    if isinstance(expression, Conditional):
        chosen = expression.then if holds(expression.when, values) else expression.otherwise
        return evaluate(chosen, values)
    if isinstance(expression, BigSum):
        raise NotEvaluable(
            f"an indexed sum over {expression.index_set!r}: its members are not scalar values"
        )
    raise NotEvaluable(f"unknown expression node {expression.tag!r}")


_COMPARE = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
}


def holds(relation: Relation, values: Mapping[str, float]) -> bool:
    """Whether a comparison or a logical combination of comparisons is true at ``values``."""
    if isinstance(relation, Compare):
        left = evaluate(relation.left, values)
        right = evaluate(relation.right, values)
        return bool(_COMPARE[relation.comparator.value](left, right))
    if isinstance(relation, Logical):
        results = [holds(operand, values) for operand in relation.operands]
        if relation.connective == "and":
            return all(results)
        if relation.connective == "or":
            return any(results)
        if relation.connective == "not":
            return not results[0]
        if relation.connective == "implies":
            return (not results[0]) or results[1]
    if isinstance(relation, (ForAll, Rate)):
        raise NotEvaluable(f"a {relation.tag!r} relation has no truth value at a point")
    raise NotEvaluable(f"unknown relation node {relation.tag!r}")


__all__ = ["NotEvaluable", "evaluate", "holds"]

"""Emit a dynamics problem as a Python module that SciPy's ``solve_ivp`` integrates.

The module is what a reader is shown beside the statement: the states, their initial values, the
range, the right-hand side and one function per query, in plain Python. It is total on valid dynamics
problems or it raises ``NotRepresentable``: an indexed sum has no scalar form, and a loop among
derived quantities is an algebraic system this does not solve.

The oracle does not execute this source; it integrates a right-hand side built from the evaluator
(:mod:`planteo.dynamics`). A test holds the two to the same numbers.
"""

from __future__ import annotations

from ..dynamics import _definitions, _order
from ..evaluate import NotEvaluable
from ..expressions import BigSum, Conditional, Constant, Expression, Power, Product, Ref, Sum
from ..problem import Family, Problem, Role
from ..relations import Compare, Logical, Rate, Relation
from ..validate import validate
from . import NotRepresentable

BACKEND = "scipy"


def _python(expression: Expression, names: dict[str, str]) -> str:
    if isinstance(expression, Constant):
        return repr(float(expression.value))
    if isinstance(expression, Ref):
        return names[expression.name]
    if isinstance(expression, Sum):
        return "(" + " + ".join(_python(t, names) for t in expression.terms) + ")"
    if isinstance(expression, Product):
        return "(" + " * ".join(_python(f, names) for f in expression.factors) + ")"
    if isinstance(expression, Power):
        return f"({_python(expression.base, names)} ** ({expression.exponent.numerator}/{expression.exponent.denominator}))"
    if isinstance(expression, Conditional):
        return (
            f"({_python(expression.then, names)} if {_condition(expression.when, names)} "
            f"else {_python(expression.otherwise, names)})"
        )
    if isinstance(expression, BigSum):
        raise NotRepresentable("an indexed sum", BACKEND, expression.index_set)
    raise NotRepresentable(f"the expression node {expression.tag!r}", BACKEND)


def _condition(relation: Relation, names: dict[str, str]) -> str:
    if isinstance(relation, Compare):
        return f"({_python(relation.left, names)} {relation.comparator.value} {_python(relation.right, names)})"
    if isinstance(relation, Logical):
        parts = [_condition(o, names) for o in relation.operands]
        if relation.connective in ("and", "or"):
            return "(" + f" {relation.connective} ".join(parts) + ")"
        if relation.connective == "not":
            return f"(not {parts[0]})"
        return f"((not {parts[0]}) or {parts[1]})"
    raise NotRepresentable(f"the relation node {relation.tag!r} as a condition", BACKEND)


def emit_source(problem: Problem) -> str:
    """A Python module for ``scipy.integrate.solve_ivp``, from a valid dynamics problem."""
    if problem.family is not Family.DYNAMICS:
        raise NotRepresentable(f"a {problem.family.value} problem", BACKEND)
    validate(problem).raise_if_invalid()

    # Identifiers are positional, with the document's names in comments: a name in a document need
    # not be a Python identifier, and the emitted source must never depend on one being so.
    names = {q.name: f"v{index}" for index, q in enumerate(problem.quantities)}
    (independent,) = problem.by_role(Role.INDEPENDENT)
    states = problem.by_role(Role.STATE)
    rates = {r.state: r.expression for r in problem.relations if isinstance(r, Rate)}
    definitions = _definitions(problem)
    try:
        order = _order(definitions)
    except NotEvaluable as error:
        raise NotRepresentable("a loop among derived quantities", BACKEND, str(error)) from None

    out = [
        '"""A dynamics problem emitted by planteo for scipy.integrate.solve_ivp."""',
        "",
        "# Quantities, by position:",
    ]
    out += [f"#   {names[q.name]} = {q.name} ({q.role.value}, {q.dimension.describe()})" for q in problem.quantities]
    out += [
        "",
        f"STATES = {[s.name for s in states]!r}",
        f"Y0 = {[float(s.value) for s in states]!r}",  # type: ignore[arg-type]
        f"T_SPAN = ({float(independent.lower)!r}, {float(independent.upper)!r})",  # type: ignore[arg-type]
        "",
        "",
        "def _values(t, y):",
        f"    {names[independent.name]} = t",
    ]
    for index, state in enumerate(states):
        out.append(f"    {names[state.name]} = y[{index}]")
    for quantity in problem.by_role(Role.PARAMETER):
        if quantity.value is not None:
            out.append(f"    {names[quantity.name]} = {float(quantity.value)!r}")
    for name in order:
        out.append(f"    {names[name]} = {_python(definitions[name], names)}")
    assigned = [independent.name, *(q.name for q in states)]
    assigned += [q.name for q in problem.by_role(Role.PARAMETER) if q.value is not None]
    assigned += order
    local = ", ".join(f"{names[name]!r}: {names[name]}" for name in assigned)
    out.append(f"    return {{{local}}}")
    out += ["", "", "def rhs(t, y):", "    v = _values(t, y)"]
    rendered = [_python(rates[s.name], {k: f"v[{v!r}]" for k, v in names.items()}) for s in states]
    out.append(f"    return [{', '.join(rendered)}]")
    for index, query in enumerate(problem.queries):
        out += [
            "",
            "",
            f"def query_{index}(t, y):",
            f'    """{query.name}, asked at {query.at}."""',
            "    v = _values(t, y)",
            f"    return {_python(query.expression, {k: f'v[{v!r}]' for k, v in names.items()})}",
        ]
    listed = ", ".join(f"({q.name!r}, {q.at!r}, query_{i})" for i, q in enumerate(problem.queries))
    out += ["", "", f"QUERIES = [{listed}]", ""]
    return "\n".join(out)


__all__ = ["emit_source"]

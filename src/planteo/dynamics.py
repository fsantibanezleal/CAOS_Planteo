"""A dynamics problem as a system an integrator can take.

``system(problem)`` reads a validated dynamics problem into the pieces every ODE integrator needs:
the state names in a fixed order, their initial values, the range, a right-hand side ``rhs(t, y)``
and one function per query. It computes with :func:`planteo.evaluate` and depends on nothing
numerical, so the integrator is the caller's choice; copela uses SciPy's ``solve_ivp``.

Derived quantities are recomputed at every point from the equalities that define them, in an order
where each is computed after what it reads. A loop among them is an algebraic system, which this does
not solve, and is refused by name.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from .evaluate import NotEvaluable, evaluate
from .expressions import Expression, Ref
from .problem import Family, Problem, Role
from .relations import Compare, Rate
from .validate import ValidationError, validate


@dataclass(frozen=True)
class System:
    """What an integrator needs, in the state order ``states``."""

    states: tuple[str, ...]
    independent: str
    t_span: tuple[float, float]
    y0: tuple[float, ...]
    rhs: Callable[[float, Sequence[float]], list[float]]
    #: Query name to (the value of the independent variable it asks at, a function of (t, y)).
    queries: Mapping[str, tuple[float, Callable[[float, Sequence[float]], float]]]
    values: Callable[[float, Sequence[float]], dict[str, float]]


def _definitions(problem: Problem) -> dict[str, Expression]:
    """Each derived quantity and the expression that defines it."""
    out: dict[str, Expression] = {}
    derived = {q.name for q in problem.by_role(Role.DERIVED)}
    for relation in problem.relations:
        if isinstance(relation, Compare) and relation.comparator.value == "==":
            for side, other in ((relation.left, relation.right), (relation.right, relation.left)):
                if isinstance(side, Ref) and side.name in derived and side.name not in other.references():
                    out[side.name] = other
    return out


def _order(definitions: Mapping[str, Expression]) -> list[str]:
    """Derived names ordered so each follows what it reads; a loop is refused."""
    ordered: list[str] = []
    state: dict[str, str] = {}

    def visit(name: str, path: tuple[str, ...]) -> None:
        if state.get(name) == "done":
            return
        if state.get(name) == "active":
            raise NotEvaluable(f"derived quantities form a loop: {' -> '.join((*path, name))}")
        state[name] = "active"
        for dependency in sorted(definitions[name].references() & definitions.keys()):
            visit(dependency, (*path, name))
        state[name] = "done"
        ordered.append(name)

    for name in sorted(definitions):
        visit(name, ())
    return ordered


def system(problem: Problem) -> System:
    """The integrator-ready system of a valid dynamics problem."""
    if problem.family is not Family.DYNAMICS:
        raise ValueError(f"a {problem.family.value} problem is not a dynamics system")
    report = validate(problem)
    if not report.ok:
        raise ValidationError(f"problem is not valid:\n  {report}")

    (independent,) = problem.by_role(Role.INDEPENDENT)
    states = problem.by_role(Role.STATE)
    names = tuple(s.name for s in states)
    rates = {r.state: r.expression for r in problem.relations if isinstance(r, Rate)}
    constants = {q.name: float(q.value) for q in problem.by_role(Role.PARAMETER) if q.value is not None}
    definitions = _definitions(problem)
    order = _order(definitions)

    def values(t: float, y: Sequence[float]) -> dict[str, float]:
        env = dict(constants)
        env[independent.name] = float(t)
        env.update(zip(names, (float(v) for v in y), strict=True))
        for name in order:
            env[name] = evaluate(definitions[name], env)
        return env

    def rhs(t: float, y: Sequence[float]) -> list[float]:
        env = values(t, y)
        return [evaluate(rates[name], env) for name in names]

    def query_function(expression: Expression) -> Callable[[float, Sequence[float]], float]:
        return lambda t, y: evaluate(expression, values(t, y))

    return System(
        states=names,
        independent=independent.name,
        t_span=(float(independent.lower), float(independent.upper)),  # type: ignore[arg-type]
        y0=tuple(float(s.value) for s in states),  # type: ignore[arg-type]
        rhs=rhs,
        queries={q.name: (q.at, query_function(q.expression)) for q in problem.queries},
        values=values,
    )


__all__ = ["System", "system"]

"""The validator. It rejects; it does not coerce.

Five checks, in the order a reader would want them reported: the structure must close before the
dimensions can mean anything, and the family check is last because it is the most specific.

Every finding names the element it is about. A validator that says "invalid" and nothing else pushes
the work back onto the person who has the least context.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from .dimensions import DimensionError
from .problem import Domain, Family, Problem, Role
from .relations import Compare, ForAll, Logical, Rate, Relation
from .spans import SpanError


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Finding:
    check: str
    severity: Severity
    message: str
    element: str = ""

    def __str__(self) -> str:
        where = f" [{self.element}]" if self.element else ""
        return f"{self.severity.value}: {self.check}{where}: {self.message}"


@dataclass(frozen=True, slots=True)
class Report:
    findings: tuple[Finding, ...]

    @property
    def ok(self) -> bool:
        return not any(f.severity is Severity.ERROR for f in self.findings)

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.WARNING)

    def raise_if_invalid(self) -> None:
        if not self.ok:
            joined = "\n  ".join(str(f) for f in self.errors)
            raise ValidationError(f"problem is not valid:\n  {joined}")

    def __str__(self) -> str:
        if not self.findings:
            return "valid, no findings"
        return "\n".join(str(f) for f in self.findings)


class ValidationError(ValueError):
    """Raised by ``Report.raise_if_invalid`` and by emitters handed an invalid problem."""


def validate(problem: Problem) -> Report:
    """Run every check and return all findings, rather than stopping at the first."""
    findings: list[Finding] = []
    findings += _check_names_unique(problem)
    findings += _check_closure(problem)
    findings += _check_spans(problem)
    # Dimensions are only meaningful once every reference resolves.
    if not any(f.check == "closure" and f.severity is Severity.ERROR for f in findings):
        findings += _check_dimensions(problem)
    findings += _check_determinacy(problem)
    findings += _check_family(problem)
    findings += _check_open_questions(problem)
    return Report(tuple(findings))


# -- individual checks ----------------------------------------------------------------


def _check_names_unique(problem: Problem) -> list[Finding]:
    seen: set[str] = set()
    out: list[Finding] = []
    for quantity in problem.quantities:
        if quantity.name in seen:
            out.append(
                Finding(
                    "names",
                    Severity.ERROR,
                    "declared more than once",
                    quantity.name,
                )
            )
        seen.add(quantity.name)
    return out


def _check_closure(problem: Problem) -> list[Finding]:
    """No free symbol: every reference resolves to a declared quantity."""
    declared = {q.name for q in problem.quantities}
    out: list[Finding] = []
    for name in sorted(problem.references() - declared):
        out.append(
            Finding(
                "closure",
                Severity.ERROR,
                "referenced but never declared",
                name,
            )
        )
    return out


def _check_spans(problem: Problem) -> list[Finding]:
    """A span must still cover the text it recorded."""
    out: list[Finding] = []

    def check(span, element: str) -> None:
        if span is None:
            return
        try:
            span.verify(problem.narrative)
        except SpanError as error:
            out.append(Finding("spans", Severity.ERROR, str(error), element))

    for quantity in problem.quantities:
        check(quantity.span, quantity.name)
    for relation in problem.relations:
        check(getattr(relation, "span", None), _label(relation))
    for objective in problem.objectives:
        check(objective.span, objective.name)
    for query in problem.queries:
        check(query.span, query.name)
    for assumption in problem.assumptions:
        check(assumption.span, assumption.statement[:40])
    for question in problem.open_questions:
        check(question.span, question.question[:40])
    return out


def _check_dimensions(problem: Problem) -> list[Finding]:
    scope = problem.scope
    out: list[Finding] = []
    for relation in problem.relations:
        try:
            relation.check_dimensions(scope)
        except DimensionError as error:
            out.append(
                Finding("dimensions", Severity.ERROR, str(error), _label(relation))
            )
    for objective in problem.objectives:
        try:
            objective.dimension(scope)
        except DimensionError as error:
            out.append(
                Finding("dimensions", Severity.ERROR, str(error), objective.name)
            )
    for query in problem.queries:
        try:
            query.dimension(scope)
        except DimensionError as error:
            out.append(Finding("dimensions", Severity.ERROR, str(error), query.name))
    return out


def _check_determinacy(problem: Problem) -> list[Finding]:
    """Every quantity is given, chosen, derived exactly once, or observed."""
    out: list[Finding] = []
    defining = _defining_counts(problem)
    for quantity in problem.quantities:
        if quantity.role is Role.PARAMETER:
            if quantity.value is None and quantity.domain is not Domain.SET:
                out.append(
                    Finding(
                        "determinacy",
                        Severity.WARNING,
                        "is a parameter with no value; it must be supplied before solving",
                        quantity.name,
                    )
                )
        elif quantity.role is Role.VARIABLE:
            if quantity.value is not None:
                out.append(
                    Finding(
                        "determinacy",
                        Severity.ERROR,
                        "is a decision variable and also carries a fixed value",
                        quantity.name,
                    )
                )
        elif quantity.role is Role.STATE:
            if quantity.value is None:
                out.append(
                    Finding(
                        "determinacy",
                        Severity.ERROR,
                        "is a state with no initial value; the system cannot start",
                        quantity.name,
                    )
                )
        elif quantity.role is Role.DERIVED:
            count = defining.get(quantity.name, 0)
            if count == 0:
                out.append(
                    Finding(
                        "determinacy",
                        Severity.ERROR,
                        "is derived but no relation defines it (under-determined)",
                        quantity.name,
                    )
                )
            elif count > 1:
                out.append(
                    Finding(
                        "determinacy",
                        Severity.ERROR,
                        f"is derived by {count} relations (over-determined)",
                        quantity.name,
                    )
                )
    return out


def _defining_counts(problem: Problem) -> dict[str, int]:
    """Count the equalities that could define each quantity.

    A relation defines a quantity when it is an equality and that quantity is alone on one side. This
    is deliberately syntactic: solving for a symbol is not this package's job, and a rule that is
    easy to read is easier to satisfy on purpose than a clever one.
    """
    from .expressions import Ref

    counts: dict[str, int] = {}
    for relation in _walk(problem.relations):
        if not isinstance(relation, Compare):
            continue
        if relation.comparator.value != "==":
            continue
        for side, other in ((relation.left, relation.right), (relation.right, relation.left)):
            if isinstance(side, Ref) and side.name not in other.references():
                counts[side.name] = counts.get(side.name, 0) + 1
    return counts


def _check_family(problem: Problem) -> list[Finding]:
    out: list[Finding] = []
    if problem.family is Family.OPTIMIZATION:
        if not problem.objectives and not problem.feasibility_only:
            out.append(
                Finding(
                    "family",
                    Severity.ERROR,
                    "an optimization problem needs an objective, or must declare "
                    "feasibility_only",
                    "optimization",
                )
            )
        if problem.objectives and problem.feasibility_only:
            out.append(
                Finding(
                    "family",
                    Severity.ERROR,
                    "declares feasibility_only and also carries an objective",
                    "optimization",
                )
            )
        if not problem.by_role(Role.VARIABLE):
            out.append(
                Finding(
                    "family",
                    Severity.ERROR,
                    "an optimization problem needs at least one decision variable",
                    "optimization",
                )
            )
        out += _dynamics_elements_in(problem, "an optimization problem")
    elif problem.family is Family.DYNAMICS:
        out += _check_dynamics(problem)
    # The experiment and learning families gain their checks when their oracles land; declaring
    # them here with no check would be a gate that measures nothing.
    return out


def _dynamics_elements_in(problem: Problem, what: str) -> list[Finding]:
    """A rate, a query, a state or an independent variable outside the dynamics family."""
    out: list[Finding] = []
    for relation in _walk(problem.relations):
        if isinstance(relation, Rate):
            out.append(Finding("family", Severity.ERROR, f"{what} cannot carry a rate", _label(relation)))
    for query in problem.queries:
        out.append(Finding("family", Severity.ERROR, f"{what} cannot carry a query", query.name))
    for quantity in problem.quantities:
        if quantity.role in (Role.STATE, Role.INDEPENDENT):
            out.append(
                Finding("family", Severity.ERROR, f"{what} cannot have a {quantity.role.value} quantity", quantity.name)
            )
    return out


def _check_dynamics(problem: Problem) -> list[Finding]:
    """One bounded independent variable, a rate per state, and queries inside the range."""
    out: list[Finding] = []
    independents = problem.by_role(Role.INDEPENDENT)
    if len(independents) != 1:
        out.append(
            Finding(
                "family",
                Severity.ERROR,
                f"a dynamics problem needs exactly one independent variable, and has {len(independents)}",
                "dynamics",
            )
        )
    independent = independents[0] if len(independents) == 1 else None
    if independent is not None and (independent.lower is None or independent.upper is None):
        out.append(
            Finding(
                "family",
                Severity.ERROR,
                "the independent variable needs both bounds: they are the range to simulate",
                independent.name,
            )
        )
    states = problem.by_role(Role.STATE)
    if not states:
        out.append(Finding("family", Severity.ERROR, "a dynamics problem needs at least one state", "dynamics"))
    rates: dict[str, int] = {}
    for relation in problem.relations:
        if isinstance(relation, Rate):
            rates[relation.state] = rates.get(relation.state, 0) + 1
            if independent is not None and relation.wrt != independent.name:
                out.append(
                    Finding(
                        "family",
                        Severity.ERROR,
                        f"differentiates by {relation.wrt!r}, which is not the independent variable "
                        f"{independent.name!r}",
                        _label(relation),
                    )
                )
            if relation.state not in {s.name for s in states}:
                out.append(
                    Finding("family", Severity.ERROR, f"is a rate of {relation.state!r}, which is not a state", _label(relation))
                )
        elif isinstance(relation, Compare):
            if relation.comparator.value != "==":
                out.append(
                    Finding(
                        "family",
                        Severity.ERROR,
                        "a dynamics problem has no inequality to satisfy; its relations are rates and the "
                        "equalities that define derived quantities",
                        _label(relation),
                    )
                )
        else:
            out.append(
                Finding("family", Severity.ERROR, "a dynamics problem takes rates and equalities only", _label(relation))
            )
    for state in states:
        count = rates.get(state.name, 0)
        if count != 1:
            out.append(
                Finding(
                    "family",
                    Severity.ERROR,
                    "has no rate" if count == 0 else f"has {count} rates; a state has exactly one",
                    state.name,
                )
            )
    if not problem.queries:
        out.append(
            Finding("family", Severity.ERROR, "a dynamics problem needs at least one query: what the statement asks", "dynamics")
        )
    if independent is not None and independent.lower is not None and independent.upper is not None:
        for query in problem.queries:
            if not (independent.lower <= query.at <= independent.upper):
                out.append(
                    Finding(
                        "family",
                        Severity.ERROR,
                        f"asks at {query.at}, outside the range {independent.lower} to {independent.upper}",
                        query.name,
                    )
                )
    if problem.objectives or problem.feasibility_only:
        out.append(Finding("family", Severity.ERROR, "a dynamics problem has no objective", "dynamics"))
    for quantity in problem.by_role(Role.VARIABLE):
        out.append(
            Finding(
                "family",
                Severity.ERROR,
                "a dynamics problem has states, not decision variables",
                quantity.name,
            )
        )
    return out


def _check_open_questions(problem: Problem) -> list[Finding]:
    out: list[Finding] = []
    for question in problem.open_questions:
        if question.is_open:
            out.append(
                Finding(
                    "open-questions",
                    Severity.WARNING,
                    "is unresolved; the formalization is conditional on an answer",
                    question.question[:60],
                )
            )
    return out


# -- helpers --------------------------------------------------------------------------


def _walk(relations: Iterable[Relation]) -> Iterable[Relation]:
    for relation in relations:
        yield relation
        if isinstance(relation, Logical):
            yield from _walk(relation.operands)
        elif isinstance(relation, ForAll):
            yield from _walk([relation.body])


def _label(relation: Relation) -> str:
    return getattr(relation, "name", "") or relation.tag

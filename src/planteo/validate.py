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
from .relations import Compare, ForAll, Logical, Relation
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
    # The other families gain their checks when their emitters land; declaring them here with no
    # check would be a gate that measures nothing.
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

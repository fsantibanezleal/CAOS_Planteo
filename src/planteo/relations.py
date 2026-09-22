"""Relations: the constraints and equations of a problem.

A relation compares two expressions. Its dimensional check is the strict one: the two sides must be
compatible, because comparing metres with seconds is meaningless whatever the solver does with it.

Logical structure (and, or, not, implies) is represented over relations rather than inside the
expression language, so an expression always denotes a quantity and a relation always denotes a
truth. Keeping those apart is what lets the dimensional checker be total.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from .dimensions import Dimension, DimensionError
from .expressions import Expression, expression_from_json
from .spans import Span


class Comparator(str, Enum):
    EQ = "=="
    LE = "<="
    GE = ">="
    LT = "<"
    GT = ">"
    NE = "!="

    @property
    def flipped(self) -> Comparator:
        """The same relation with the sides exchanged, used by canonical form."""
        return {
            Comparator.EQ: Comparator.EQ,
            Comparator.NE: Comparator.NE,
            Comparator.LE: Comparator.GE,
            Comparator.GE: Comparator.LE,
            Comparator.LT: Comparator.GT,
            Comparator.GT: Comparator.LT,
        }[self]


class Relation:
    """Base class for anything that denotes a truth."""

    tag: str = ""

    def check_dimensions(self, scope: Mapping[str, Dimension]) -> None:
        raise NotImplementedError

    def references(self) -> set[str]:
        raise NotImplementedError

    def to_json(self) -> dict[str, object]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class Compare(Relation):
    """``left <comparator> right``, the ordinary constraint."""

    left: Expression
    comparator: Comparator
    right: Expression
    name: str = ""
    span: Span | None = None

    tag = "compare"

    def check_dimensions(self, scope: Mapping[str, Dimension]) -> None:
        left = self.left.dimension(scope)
        right = self.right.dimension(scope)
        if not left.compatible_with(right):
            label = self.name or "relation"
            raise DimensionError(
                f"{label}: left side is {left.describe()} but right side is "
                f"{right.describe()}; they cannot be compared"
            )

    def references(self) -> set[str]:
        return self.left.references() | self.right.references()

    def to_json(self) -> dict[str, object]:
        out: dict[str, object] = {
            "tag": self.tag,
            "left": self.left.to_json(),
            "comparator": self.comparator.value,
            "right": self.right.to_json(),
            "name": self.name,
        }
        if self.span is not None:
            out["span"] = self.span.to_json()
        return out


@dataclass(frozen=True, slots=True)
class Logical(Relation):
    """``and`` / ``or`` / ``not`` / ``implies`` over relations."""

    connective: str
    operands: tuple[Relation, ...]
    name: str = ""
    span: Span | None = None

    tag = "logical"

    _ARITY = {"and": None, "or": None, "not": 1, "implies": 2}

    def __post_init__(self) -> None:
        if self.connective not in self._ARITY:
            raise ValueError(f"unknown connective {self.connective!r}")
        expected = self._ARITY[self.connective]
        if expected is not None and len(self.operands) != expected:
            raise ValueError(
                f"{self.connective!r} takes {expected} operand(s), got {len(self.operands)}"
            )
        if expected is None and not self.operands:
            raise ValueError(f"{self.connective!r} needs at least one operand")

    def check_dimensions(self, scope: Mapping[str, Dimension]) -> None:
        for operand in self.operands:
            operand.check_dimensions(scope)

    def references(self) -> set[str]:
        return set().union(*(operand.references() for operand in self.operands))

    def to_json(self) -> dict[str, object]:
        out: dict[str, object] = {
            "tag": self.tag,
            "connective": self.connective,
            "operands": [operand.to_json() for operand in self.operands],
            "name": self.name,
        }
        if self.span is not None:
            out["span"] = self.span.to_json()
        return out


@dataclass(frozen=True, slots=True)
class ForAll(Relation):
    """``for every index in index_set``, the body holds.

    This is how a family of constraints is written without unrolling it, which matters because the
    emitters need the family, not the expansion, to produce readable models.
    """

    index: str
    index_set: str
    body: Relation
    name: str = ""
    span: Span | None = None

    tag = "forall"

    def check_dimensions(self, scope: Mapping[str, Dimension]) -> None:
        self.body.check_dimensions(scope)

    def references(self) -> set[str]:
        return (self.body.references() - {self.index}) | {self.index_set}

    def to_json(self) -> dict[str, object]:
        out: dict[str, object] = {
            "tag": self.tag,
            "index": self.index,
            "index_set": self.index_set,
            "body": self.body.to_json(),
            "name": self.name,
        }
        if self.span is not None:
            out["span"] = self.span.to_json()
        return out


class Sense(str, Enum):
    MINIMISE = "minimise"
    MAXIMISE = "maximise"


@dataclass(frozen=True, slots=True)
class Objective:
    """What the problem is trying to do, and to what expression."""

    sense: Sense
    expression: Expression
    name: str = "objective"
    span: Span | None = None

    def dimension(self, scope: Mapping[str, Dimension]) -> Dimension:
        return self.expression.dimension(scope)

    def references(self) -> set[str]:
        return self.expression.references()

    def to_json(self) -> dict[str, object]:
        out: dict[str, object] = {
            "sense": self.sense.value,
            "expression": self.expression.to_json(),
            "name": self.name,
        }
        if self.span is not None:
            out["span"] = self.span.to_json()
        return out

    @classmethod
    def from_json(cls, data: Mapping[str, object]) -> Objective:
        span = data.get("span")
        return cls(
            sense=Sense(str(data["sense"])),
            expression=expression_from_json(data["expression"]),  # type: ignore[arg-type]
            name=str(data.get("name", "objective")),
            span=Span.from_json(span) if isinstance(span, Mapping) else None,
        )


def relation_from_json(data: Mapping[str, object]) -> Relation:
    tag = str(data.get("tag", ""))
    span_data = data.get("span")
    span = Span.from_json(span_data) if isinstance(span_data, Mapping) else None
    name = str(data.get("name", ""))
    if tag == "compare":
        return Compare(
            left=expression_from_json(data["left"]),  # type: ignore[arg-type]
            comparator=Comparator(str(data["comparator"])),
            right=expression_from_json(data["right"]),  # type: ignore[arg-type]
            name=name,
            span=span,
        )
    if tag == "logical":
        return Logical(
            connective=str(data["connective"]),
            operands=tuple(relation_from_json(o) for o in data["operands"]),  # type: ignore[union-attr]
            name=name,
            span=span,
        )
    if tag == "forall":
        return ForAll(
            index=str(data["index"]),
            index_set=str(data["index_set"]),
            body=relation_from_json(data["body"]),  # type: ignore[arg-type]
            name=name,
            span=span,
        )
    raise ValueError(f"unknown relation node {tag!r}; the node set is closed")

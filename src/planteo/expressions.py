"""The expression language.

The node set is small and closed. That is the design, not a limitation waiting to be lifted: a closed
set is what makes dimensional checking total and canonical comparison decidable. When a corpus needs
a construct that is not here, the node set is extended by an explicit design change with its own
requirement and gate, never by an escape hatch that accepts arbitrary code.

Every node knows how to report its own dimension, and that computation is where the dimensional
errors surface: a ``Sum`` whose terms disagree cannot produce a dimension, so it raises.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

from .dimensions import Dimension, DimensionError, product

if TYPE_CHECKING:
    from .relations import Relation

__all__ = [
    "Expression",
    "Constant",
    "Ref",
    "Sum",
    "Product",
    "Power",
    "BigSum",
    "Conditional",
    "Node",
]


class Expression:
    """Base class. Subclasses are the closed node set."""

    #: Node tag used in serialisation and in canonical form.
    tag: str = ""

    def dimension(self, scope: Scope) -> Dimension:
        raise NotImplementedError

    def references(self) -> set[str]:
        """Every quantity name this expression reads."""
        raise NotImplementedError

    def to_json(self) -> dict[str, object]:
        raise NotImplementedError


#: Anything that can resolve a quantity name to its dimension.
Scope = Mapping[str, Dimension]


@dataclass(frozen=True, slots=True)
class Constant(Expression):
    """A literal with a stated dimension.

    The dimension is required. A bare number is representable only as a dimensionless constant, which
    has to say so.
    """

    value: float
    unit: Dimension

    tag = "const"

    def dimension(self, scope: Scope) -> Dimension:
        return self.unit

    def references(self) -> set[str]:
        return set()

    def to_json(self) -> dict[str, object]:
        return {"tag": self.tag, "value": self.value, "unit": self.unit.to_json()}


@dataclass(frozen=True, slots=True)
class Ref(Expression):
    """A reference to a declared quantity, by name."""

    name: str

    tag = "ref"

    def dimension(self, scope: Scope) -> Dimension:
        try:
            return scope[self.name]
        except KeyError:
            raise DimensionError(
                f"reference to undeclared quantity {self.name!r}"
            ) from None

    def references(self) -> set[str]:
        return {self.name}

    def to_json(self) -> dict[str, object]:
        return {"tag": self.tag, "name": self.name}


@dataclass(frozen=True, slots=True)
class Sum(Expression):
    """A sum of terms. Every term must share a dimension; that check is the point."""

    terms: tuple[Expression, ...]

    tag = "sum"

    def dimension(self, scope: Scope) -> Dimension:
        if not self.terms:
            raise DimensionError("an empty sum has no dimension")
        first = self.terms[0].dimension(scope)
        for index, term in enumerate(self.terms[1:], start=1):
            other = term.dimension(scope)
            if not first.compatible_with(other):
                raise DimensionError(
                    f"sum term {index} is {other.describe()} but term 0 is {first.describe()}"
                )
        return first

    def references(self) -> set[str]:
        return set().union(*(term.references() for term in self.terms))

    def to_json(self) -> dict[str, object]:
        return {"tag": self.tag, "terms": [t.to_json() for t in self.terms]}


@dataclass(frozen=True, slots=True)
class Product(Expression):
    """A product of factors. Dimensions multiply, so anything goes here dimensionally."""

    factors: tuple[Expression, ...]

    tag = "product"

    def dimension(self, scope: Scope) -> Dimension:
        if not self.factors:
            raise DimensionError("an empty product has no dimension")
        return product(factor.dimension(scope) for factor in self.factors)

    def references(self) -> set[str]:
        return set().union(*(f.references() for f in self.factors))

    def to_json(self) -> dict[str, object]:
        return {"tag": self.tag, "factors": [f.to_json() for f in self.factors]}


@dataclass(frozen=True, slots=True)
class Power(Expression):
    """A base raised to a rational exponent.

    The exponent is a number, not an expression. A dimensioned quantity raised to a variable power
    has no well-defined dimension, so the representation does not admit it.
    """

    base: Expression
    exponent: Fraction

    tag = "power"

    def dimension(self, scope: Scope) -> Dimension:
        return self.base.dimension(scope) ** self.exponent

    def references(self) -> set[str]:
        return self.base.references()

    def to_json(self) -> dict[str, object]:
        return {
            "tag": self.tag,
            "base": self.base.to_json(),
            "exponent": str(self.exponent),
        }


@dataclass(frozen=True, slots=True)
class BigSum(Expression):
    """An indexed sum: sum over ``index`` in ``index_set`` of ``body``.

    ``index_set`` names a set-valued quantity. The body's dimension is the sum's dimension, because
    summing over an index does not change what is being added up.
    """

    index: str
    index_set: str
    body: Expression

    tag = "bigsum"

    def dimension(self, scope: Scope) -> Dimension:
        return self.body.dimension(scope)

    def references(self) -> set[str]:
        # The bound index is not a free reference; the set being summed over is.
        return (self.body.references() - {self.index}) | {self.index_set}

    def to_json(self) -> dict[str, object]:
        return {
            "tag": self.tag,
            "index": self.index,
            "index_set": self.index_set,
            "body": self.body.to_json(),
        }


@dataclass(frozen=True, slots=True)
class Conditional(Expression):
    """``when`` holds, take ``then``, else take ``otherwise``.

    Both branches must share a dimension: a value that is metres on one branch and seconds on the
    other is the error this representation is built to catch.
    """

    when: Relation
    then: Expression
    otherwise: Expression

    tag = "conditional"

    def dimension(self, scope: Scope) -> Dimension:
        left = self.then.dimension(scope)
        right = self.otherwise.dimension(scope)
        if not left.compatible_with(right):
            raise DimensionError(
                f"conditional branches disagree: {left.describe()} and {right.describe()}"
            )
        return left

    def references(self) -> set[str]:
        return (
            self.when.references()
            | self.then.references()
            | self.otherwise.references()
        )

    def to_json(self) -> dict[str, object]:
        return {
            "tag": self.tag,
            "when": self.when.to_json(),
            "then": self.then.to_json(),
            "otherwise": self.otherwise.to_json(),
        }


Node = Constant | Ref | Sum | Product | Power | BigSum | Conditional

_NODES: dict[str, type] = {}


def _register() -> None:
    for cls in (Constant, Ref, Sum, Product, Power, BigSum, Conditional):
        _NODES[cls.tag] = cls


_register()


def expression_from_json(data: Mapping[str, object]) -> Expression:
    """Rebuild an expression. Rejects an unknown tag rather than guessing."""
    tag = str(data.get("tag", ""))
    if tag not in _NODES:
        raise ValueError(f"unknown expression node {tag!r}; the node set is closed")
    if tag == "const":
        return Constant(
            value=float(data["value"]),  # type: ignore[arg-type]
            unit=Dimension.from_json(data["unit"]),  # type: ignore[arg-type]
        )
    if tag == "ref":
        return Ref(name=str(data["name"]))
    if tag == "sum":
        return Sum(tuple(expression_from_json(t) for t in data["terms"]))  # type: ignore[union-attr]
    if tag == "product":
        return Product(tuple(expression_from_json(f) for f in data["factors"]))  # type: ignore[union-attr]
    if tag == "power":
        return Power(
            base=expression_from_json(data["base"]),  # type: ignore[arg-type]
            exponent=Fraction(str(data["exponent"])),
        )
    if tag == "bigsum":
        return BigSum(
            index=str(data["index"]),
            index_set=str(data["index_set"]),
            body=expression_from_json(data["body"]),  # type: ignore[arg-type]
        )
    from .relations import relation_from_json  # local import, cyclic by nature

    return Conditional(
        when=relation_from_json(data["when"]),  # type: ignore[arg-type]
        then=expression_from_json(data["then"]),  # type: ignore[arg-type]
        otherwise=expression_from_json(data["otherwise"]),  # type: ignore[arg-type]
    )


def flatten_terms(sequence: Sequence[Expression]) -> tuple[Expression, ...]:
    """Fold nested sums into one level, used by canonical form."""
    out: list[Expression] = []
    for item in sequence:
        if isinstance(item, Sum):
            out.extend(flatten_terms(item.terms))
        else:
            out.append(item)
    return tuple(out)

"""Physical dimensions as first-class data.

A number without a dimension is how a published result gets broken. On this account a set of
anchor-slice constants expressed as 0-to-1 fractions were applied to quantities in MW, TWh and
metres; four methods broke and two had already been published. So in this representation a quantity
cannot exist without a dimension, and ``dimensionless`` is a dimension that must be stated rather
than a default that happens when nobody thought about it.

The dimension vector is the seven SI base exponents plus two slots that matter for the problems this
package represents and that SI does not cover: ``currency`` (money is not a physical dimension but
adding dollars to tonnes is the same class of error) and ``count`` (a dimensionless count of items
behaves differently from a true ratio when a relation is checked).

Exponents are ``Fraction`` rather than ``int`` because square roots of dimensioned quantities are
ordinary in engineering relations.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from fractions import Fraction

#: The ordered axes of the dimension vector.
AXES: tuple[str, ...] = (
    "length",
    "mass",
    "time",
    "current",
    "temperature",
    "amount",
    "luminosity",
    "currency",
    "count",
)

_SI_SYMBOL: Mapping[str, str] = {
    "length": "m",
    "mass": "kg",
    "time": "s",
    "current": "A",
    "temperature": "K",
    "amount": "mol",
    "luminosity": "cd",
    "currency": "¤",
    "count": "#",
}


class DimensionError(ValueError):
    """Raised when an operation is not defined for the dimensions involved."""


def _as_fraction(value: object) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        return Fraction(value)
    if isinstance(value, float):
        # A float exponent is almost always a mistake (0.5 is the exception and is exact).
        return Fraction(value).limit_denominator(12)
    raise TypeError(f"cannot read {value!r} as a dimension exponent")


@dataclass(frozen=True, slots=True)
class Dimension:
    """A dimension vector, with the unit string it was written as.

    ``symbol`` is the human unit the quantity was stated in ("MW", "t/h", "USD/t"). It is carried for
    display and for provenance; it is never used for comparison. Two quantities are dimensionally
    compatible when their exponent vectors match, whatever they were written as, which is exactly the
    check that a string comparison of unit labels would fail.
    """

    exponents: tuple[Fraction, ...] = field(default=tuple(Fraction(0) for _ in AXES))
    symbol: str = ""

    def __post_init__(self) -> None:
        if len(self.exponents) != len(AXES):
            raise DimensionError(
                f"a dimension has {len(AXES)} exponents, got {len(self.exponents)}"
            )
        object.__setattr__(
            self, "exponents", tuple(_as_fraction(e) for e in self.exponents)
        )

    # -- construction ---------------------------------------------------------------

    @classmethod
    def of(cls, symbol: str = "", **axes: object) -> Dimension:
        """Build a dimension by naming its axes.

        ``Dimension.of("MW", mass=1, length=2, time=-3)`` is power. Unnamed axes are zero.
        """
        unknown = set(axes) - set(AXES)
        if unknown:
            raise DimensionError(f"unknown dimension axes: {sorted(unknown)}")
        return cls(
            tuple(_as_fraction(axes.get(name, 0)) for name in AXES), symbol=symbol
        )

    @classmethod
    def dimensionless(cls, symbol: str = "1") -> Dimension:
        """The stated absence of a dimension. Not a default; a declaration."""
        return cls.of(symbol)

    # -- algebra --------------------------------------------------------------------

    def __mul__(self, other: Dimension) -> Dimension:
        return Dimension(
            tuple(a + b for a, b in zip(self.exponents, other.exponents, strict=True)),
            symbol=_join(self.symbol, other.symbol, "*"),
        )

    def __truediv__(self, other: Dimension) -> Dimension:
        return Dimension(
            tuple(a - b for a, b in zip(self.exponents, other.exponents, strict=True)),
            symbol=_join(self.symbol, other.symbol, "/"),
        )

    def __pow__(self, exponent: object) -> Dimension:
        e = _as_fraction(exponent)
        return Dimension(
            tuple(a * e for a in self.exponents),
            symbol=f"({self.symbol})^{e}" if self.symbol else "",
        )

    # -- predicates -----------------------------------------------------------------

    @property
    def is_dimensionless(self) -> bool:
        return all(e == 0 for e in self.exponents)

    def compatible_with(self, other: Dimension) -> bool:
        """True when the two may be added, subtracted or compared."""
        return self.exponents == other.exponents

    def require_compatible(self, other: Dimension, context: str) -> None:
        if not self.compatible_with(other):
            raise DimensionError(
                f"{context}: {self.describe()} is not compatible with {other.describe()}"
            )

    # -- display --------------------------------------------------------------------

    def describe(self) -> str:
        """A readable form: the written symbol when there is one, else the SI signature."""
        if self.symbol:
            return self.symbol
        return self.si_signature()

    def si_signature(self) -> str:
        if self.is_dimensionless:
            return "1"
        parts = []
        for axis, exponent in zip(AXES, self.exponents, strict=True):
            if exponent == 0:
                continue
            base = _SI_SYMBOL[axis]
            parts.append(base if exponent == 1 else f"{base}^{exponent}")
        return "·".join(parts)

    def __str__(self) -> str:  # pragma: no cover, convenience only
        return self.describe()

    # -- serialisation ---------------------------------------------------------------

    def to_json(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "exponents": {
                axis: str(exponent)
                for axis, exponent in zip(AXES, self.exponents, strict=True)
                if exponent != 0
            },
        }

    @classmethod
    def from_json(cls, data: Mapping[str, object]) -> Dimension:
        raw = data.get("exponents") or {}
        if not isinstance(raw, Mapping):
            raise DimensionError("exponents must be a mapping of axis to exponent")
        return cls.of(str(data.get("symbol", "")), **dict(raw))


def _join(left: str, right: str, operator: str) -> str:
    if not left or not right:
        return left or right
    return f"{left}{operator}{right}"


def product(dimensions: Iterable[Dimension]) -> Dimension:
    """The dimension of a product of terms."""
    result = Dimension.dimensionless(symbol="")
    for dimension in dimensions:
        result = result * dimension
    return result


# A small set of named dimensions the corpora keep needing. Not exhaustive on purpose: a problem
# states its own units, and this is only a convenience for the ones that recur.
DIMENSIONLESS = Dimension.dimensionless()
COUNT = Dimension.of("#", count=1)
CURRENCY = Dimension.of("¤", currency=1)
LENGTH = Dimension.of("m", length=1)
MASS = Dimension.of("kg", mass=1)
TIME = Dimension.of("s", time=1)
POWER = Dimension.of("W", mass=1, length=2, time=-3)
ENERGY = Dimension.of("J", mass=1, length=2, time=-2)
MASS_RATE = Dimension.of("kg/s", mass=1, time=-1)

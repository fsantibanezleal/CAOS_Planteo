"""Gates for R-004 and the type invariants around it."""

from __future__ import annotations

from fractions import Fraction

import pytest

from planteo import Dimension, DimensionError, Domain, Quantity, Role


def test_quantity_requires_dimension() -> None:
    """R-004: a quantity cannot exist without a dimension."""
    with pytest.raises(TypeError):
        Quantity(name="x", role=Role.VARIABLE, dimension=None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Quantity(name="x", role=Role.VARIABLE, dimension="tonnes")  # type: ignore[arg-type]


def test_dimensionless_must_be_stated_and_is_a_real_dimension() -> None:
    d = Dimension.dimensionless()
    assert d.is_dimensionless
    assert d.si_signature() == "1"
    q = Quantity(name="ratio", role=Role.PARAMETER, dimension=d, value=0.3)
    assert q.dimension.is_dimensionless


def test_unit_symbol_is_not_used_for_compatibility() -> None:
    """Two spellings of the same dimension are compatible; a string check would say otherwise."""
    tonnes = Dimension.of("t", mass=1)
    kilos = Dimension.of("kg", mass=1)
    assert tonnes.symbol != kilos.symbol
    assert tonnes.compatible_with(kilos)


def test_incompatible_dimensions_are_reported_readably() -> None:
    power = Dimension.of("MW", mass=1, length=2, time=-3)
    energy = Dimension.of("TWh", mass=1, length=2, time=-2)
    assert not power.compatible_with(energy)
    with pytest.raises(DimensionError) as caught:
        power.require_compatible(energy, "anchor slice")
    assert "anchor slice" in str(caught.value)


def test_dimension_algebra() -> None:
    mass = Dimension.of("kg", mass=1)
    time = Dimension.of("s", time=1)
    rate = mass / time
    assert rate.compatible_with(Dimension.of("kg/s", mass=1, time=-1))
    assert (mass * mass).compatible_with(mass ** 2)
    assert (mass ** Fraction(1, 2)).exponents[1] == Fraction(1, 2)


def test_bounds_must_be_ordered() -> None:
    with pytest.raises(ValueError):
        Quantity(
            name="x",
            role=Role.VARIABLE,
            dimension=Dimension.dimensionless(),
            domain=Domain.REAL,
            lower=5.0,
            upper=1.0,
        )

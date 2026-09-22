"""Gate for R-003."""

from __future__ import annotations

from planteo import (
    Comparator,
    Compare,
    Constant,
    Dimension,
    Family,
    Narrative,
    Objective,
    Problem,
    Product,
    Quantity,
    Ref,
    Role,
    Sense,
    Severity,
    Sum,
    validate,
)

TONNE = Dimension.of("t", mass=1)
USD = Dimension.of("USD", currency=1)
COST_PER_TONNE = Dimension.of("USD/t", currency=1, mass=-1)


def _base(relations=(), quantities=()) -> Problem:
    narrative = Narrative("Total cost is the unit cost times the tonnage.")
    return Problem(
        narrative=narrative,
        family=Family.OPTIMIZATION,
        quantities=quantities,
        relations=relations,
        objectives=(Objective(sense=Sense.MINIMISE, expression=Ref("x"), name="least"),),
    )


def test_underdetermined_named() -> None:
    """R-003: a derived quantity with no defining relation is an error naming it."""
    problem = _base(
        quantities=(
            Quantity(name="x", role=Role.VARIABLE, dimension=TONNE),
            Quantity(name="total", role=Role.DERIVED, dimension=USD),
        )
    )
    report = validate(problem)
    assert not report.ok
    errors = [f for f in report.errors if f.check == "determinacy"]
    assert [f.element for f in errors] == ["total"]
    assert "under-determined" in errors[0].message


def test_overdetermined_named() -> None:
    quantities = (
        Quantity(name="x", role=Role.VARIABLE, dimension=TONNE),
        Quantity(name="c", role=Role.PARAMETER, dimension=COST_PER_TONNE, value=5.0),
        Quantity(name="total", role=Role.DERIVED, dimension=USD),
    )
    defining = Compare(
        left=Ref("total"),
        comparator=Comparator.EQ,
        right=Product((Ref("c"), Ref("x"))),
        name="definition",
    )
    again = Compare(
        left=Ref("total"),
        comparator=Comparator.EQ,
        right=Constant(50.0, USD),
        name="also",
    )
    report = validate(_base(relations=(defining, again), quantities=quantities))
    errors = [f for f in report.errors if f.check == "determinacy"]
    assert [f.element for f in errors] == ["total"]
    assert "over-determined" in errors[0].message


def test_exactly_one_defining_relation_is_accepted() -> None:
    quantities = (
        Quantity(name="x", role=Role.VARIABLE, dimension=TONNE),
        Quantity(name="c", role=Role.PARAMETER, dimension=COST_PER_TONNE, value=5.0),
        Quantity(name="total", role=Role.DERIVED, dimension=USD),
    )
    defining = Compare(
        left=Ref("total"),
        comparator=Comparator.EQ,
        right=Product((Ref("c"), Ref("x"))),
        name="definition",
    )
    report = validate(_base(relations=(defining,), quantities=quantities))
    assert report.ok, report


def test_a_self_referential_equality_does_not_count_as_a_definition() -> None:
    """``total == total + x`` defines nothing, and must not be counted as a definition."""
    quantities = (
        Quantity(name="x", role=Role.VARIABLE, dimension=USD),
        Quantity(name="total", role=Role.DERIVED, dimension=USD),
    )
    circular = Compare(
        left=Ref("total"),
        comparator=Comparator.EQ,
        right=Sum((Ref("total"), Ref("x"))),
        name="circular",
    )
    report = validate(_base(relations=(circular,), quantities=quantities))
    errors = [f for f in report.errors if f.check == "determinacy"]
    assert [f.element for f in errors] == ["total"]


def test_variable_with_a_fixed_value_is_a_contradiction() -> None:
    problem = _base(
        quantities=(
            Quantity(name="x", role=Role.VARIABLE, dimension=TONNE, value=3.0),
        )
    )
    report = validate(problem)
    assert any(
        f.check == "determinacy" and f.element == "x" for f in report.errors
    ), report


def test_parameter_without_a_value_is_a_warning_not_an_error() -> None:
    problem = _base(
        quantities=(
            Quantity(name="x", role=Role.VARIABLE, dimension=TONNE),
            Quantity(name="c", role=Role.PARAMETER, dimension=COST_PER_TONNE),
        )
    )
    report = validate(problem)
    assert report.ok, report
    assert any(
        f.severity is Severity.WARNING and f.element == "c" for f in report.warnings
    )

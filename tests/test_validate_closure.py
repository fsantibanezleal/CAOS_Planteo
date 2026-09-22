"""Gate for R-002."""

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
    Quantity,
    Ref,
    Role,
    Sense,
    validate,
)

TONNE = Dimension.of("t", mass=1)


def test_free_symbol_rejected() -> None:
    """R-002: a reference to an undeclared quantity is an error that names it."""
    narrative = Narrative("Ship at most the available tonnage.")
    problem = Problem(
        narrative=narrative,
        family=Family.OPTIMIZATION,
        quantities=(Quantity(name="x", role=Role.VARIABLE, dimension=TONNE),),
        relations=(
            Compare(
                left=Ref("x"),
                comparator=Comparator.LE,
                right=Ref("available"),
                name="capacity",
            ),
        ),
        objectives=(Objective(sense=Sense.MINIMISE, expression=Ref("x"), name="least"),),
    )
    report = validate(problem)
    assert not report.ok
    closure = [f for f in report.errors if f.check == "closure"]
    assert [f.element for f in closure] == ["available"]


def test_dimensional_check_is_skipped_while_closure_fails() -> None:
    """A dimension error on an undeclared symbol would be noise, so it is not reported."""
    narrative = Narrative("Ship at most the available tonnage.")
    problem = Problem(
        narrative=narrative,
        family=Family.OPTIMIZATION,
        quantities=(Quantity(name="x", role=Role.VARIABLE, dimension=TONNE),),
        relations=(
            Compare(
                left=Ref("x"),
                comparator=Comparator.LE,
                right=Ref("ghost"),
                name="capacity",
            ),
        ),
        objectives=(Objective(sense=Sense.MINIMISE, expression=Ref("x"), name="least"),),
    )
    report = validate(problem)
    assert not any(f.check == "dimensions" for f in report.findings), report


def test_duplicate_names_rejected() -> None:
    narrative = Narrative("One name, declared twice.")
    problem = Problem(
        narrative=narrative,
        family=Family.OPTIMIZATION,
        quantities=(
            Quantity(name="x", role=Role.VARIABLE, dimension=TONNE),
            Quantity(name="x", role=Role.PARAMETER, dimension=TONNE, value=1.0),
        ),
        objectives=(Objective(sense=Sense.MINIMISE, expression=Ref("x"), name="least"),),
    )
    report = validate(problem)
    assert any(f.check == "names" for f in report.errors), report


def test_bound_index_is_not_a_free_reference() -> None:
    """A BigSum index is bound; only the set it ranges over is a reference."""
    from planteo import BigSum, Domain

    narrative = Narrative("Total the shipments over every route.")
    problem = Problem(
        narrative=narrative,
        family=Family.OPTIMIZATION,
        quantities=(
            Quantity(name="ship", role=Role.VARIABLE, dimension=TONNE),
            Quantity(
                name="routes",
                role=Role.SET,
                dimension=Dimension.dimensionless(),
                domain=Domain.SET,
            ),
        ),
        relations=(
            Compare(
                left=BigSum(index="r", index_set="routes", body=Ref("ship")),
                comparator=Comparator.LE,
                right=Constant(500.0, TONNE),
                name="fleet_limit",
            ),
        ),
        objectives=(
            Objective(sense=Sense.MINIMISE, expression=Ref("ship"), name="least"),
        ),
    )
    report = validate(problem)
    assert not any(f.check == "closure" for f in report.errors), report

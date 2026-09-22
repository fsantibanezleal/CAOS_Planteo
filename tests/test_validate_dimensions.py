"""Gate for R-001."""

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
    Sum,
    validate,
)

SECOND = Dimension.of("s", time=1)
METRE = Dimension.of("m", length=1)


def _problem(relation) -> Problem:
    narrative = Narrative("A distance and a duration are compared.")
    return Problem(
        narrative=narrative,
        family=Family.OPTIMIZATION,
        quantities=(
            Quantity(name="d", role=Role.VARIABLE, dimension=METRE),
            Quantity(name="t", role=Role.PARAMETER, dimension=SECOND, value=3.0),
        ),
        relations=(relation,),
        objectives=(
            Objective(sense=Sense.MINIMISE, expression=Ref("d"), name="shortest"),
        ),
    )


def test_mismatched_sides_rejected() -> None:
    """R-001: metres compared with seconds is an error, named and located."""
    problem = _problem(
        Compare(left=Ref("d"), comparator=Comparator.LE, right=Ref("t"), name="bad")
    )
    report = validate(problem)
    assert not report.ok
    findings = [f for f in report.errors if f.check == "dimensions"]
    assert findings, report
    assert findings[0].element == "bad"
    assert "m" in findings[0].message and "s" in findings[0].message


def test_matching_sides_accepted() -> None:
    problem = _problem(
        Compare(
            left=Ref("d"),
            comparator=Comparator.LE,
            right=Constant(10.0, METRE),
            name="ok",
        )
    )
    report = validate(problem)
    assert report.ok, report


def test_sum_terms_must_agree() -> None:
    problem = _problem(
        Compare(
            left=Sum((Ref("d"), Ref("t"))),
            comparator=Comparator.LE,
            right=Constant(1.0, METRE),
            name="mixed_sum",
        )
    )
    report = validate(problem)
    assert not report.ok
    assert any("sum term" in f.message for f in report.errors), report


def test_product_mixes_dimensions_freely() -> None:
    """A product is where mixing is legitimate; the checker must not over-reject."""
    from planteo import Product

    speed = Dimension.of("m/s", length=1, time=-1)
    narrative = Narrative("Speed times duration is a distance.")
    problem = Problem(
        narrative=narrative,
        family=Family.OPTIMIZATION,
        quantities=(
            Quantity(name="v", role=Role.VARIABLE, dimension=speed),
            Quantity(name="t", role=Role.PARAMETER, dimension=SECOND, value=3.0),
            Quantity(name="d", role=Role.PARAMETER, dimension=METRE, value=30.0),
        ),
        relations=(
            Compare(
                left=Product((Ref("v"), Ref("t"))),
                comparator=Comparator.EQ,
                right=Ref("d"),
                name="kinematics",
            ),
        ),
        objectives=(Objective(sense=Sense.MINIMISE, expression=Ref("v"), name="slow"),),
    )
    assert validate(problem).ok


def test_objective_dimension_is_checked() -> None:
    narrative = Narrative("Minimise a sum of a distance and a duration.")
    problem = Problem(
        narrative=narrative,
        family=Family.OPTIMIZATION,
        quantities=(
            Quantity(name="d", role=Role.VARIABLE, dimension=METRE),
            Quantity(name="t", role=Role.VARIABLE, dimension=SECOND),
        ),
        objectives=(
            Objective(
                sense=Sense.MINIMISE,
                expression=Sum((Ref("d"), Ref("t"))),
                name="nonsense",
            ),
        ),
    )
    report = validate(problem)
    assert not report.ok
    assert any(f.element == "nonsense" for f in report.errors), report

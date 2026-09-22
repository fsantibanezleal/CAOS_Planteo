"""Shared fixtures.

The narrative used across the tests is a small blending problem, chosen because it has units that
differ per term, which is what makes the dimensional checks worth running.
"""

from __future__ import annotations

import pytest

from planteo import (
    Comparator,
    Compare,
    Dimension,
    Domain,
    Family,
    Narrative,
    Objective,
    Problem,
    Product,
    Quantity,
    Ref,
    Role,
    Sense,
    Span,
    Sum,
)

TONNE = Dimension.of("t", mass=1)
COST_PER_TONNE = Dimension.of("USD/t", currency=1, mass=-1)
USD = Dimension.of("USD", currency=1)


@pytest.fixture
def narrative() -> Narrative:
    return Narrative(
        "A plant blends ore from two pits. Pit A costs 12 USD per tonne and pit B "
        "costs 9 USD per tonne. Together they must deliver at least 100 tonnes. "
        "Minimise the total cost."
    )


@pytest.fixture
def blend(narrative: Narrative) -> Problem:
    """A small, valid optimization problem."""
    quantities = (
        Quantity(
            name="x_a",
            role=Role.VARIABLE,
            dimension=TONNE,
            domain=Domain.REAL,
            lower=0.0,
            description="tonnes taken from pit A",
            span=Span.find(narrative, "Pit A"),
        ),
        Quantity(
            name="x_b",
            role=Role.VARIABLE,
            dimension=TONNE,
            domain=Domain.REAL,
            lower=0.0,
            description="tonnes taken from pit B",
            span=Span.find(narrative, "pit B"),
        ),
        Quantity(
            name="c_a",
            role=Role.PARAMETER,
            dimension=COST_PER_TONNE,
            value=12.0,
            span=Span.find(narrative, "12 USD per tonne"),
        ),
        Quantity(
            name="c_b",
            role=Role.PARAMETER,
            dimension=COST_PER_TONNE,
            value=9.0,
            span=Span.find(narrative, "9 USD per tonne"),
        ),
        Quantity(
            name="demand",
            role=Role.PARAMETER,
            dimension=TONNE,
            value=100.0,
            span=Span.find(narrative, "at least 100 tonnes"),
        ),
    )
    relations = (
        Compare(
            left=Sum((Ref("x_a"), Ref("x_b"))),
            comparator=Comparator.GE,
            right=Ref("demand"),
            name="meet_demand",
            span=Span.find(narrative, "must deliver at least 100 tonnes"),
        ),
    )
    objectives = (
        Objective(
            sense=Sense.MINIMISE,
            expression=Sum(
                (
                    Product((Ref("c_a"), Ref("x_a"))),
                    Product((Ref("c_b"), Ref("x_b"))),
                )
            ),
            name="total_cost",
            span=Span.find(narrative, "Minimise the total cost"),
        ),
    )
    return Problem(
        narrative=narrative,
        family=Family.OPTIMIZATION,
        quantities=quantities,
        relations=relations,
        objectives=objectives,
    )

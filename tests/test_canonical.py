"""Gate for R-008."""

from __future__ import annotations

import dataclasses

from planteo import (
    Comparator,
    Compare,
    Constant,
    Dimension,
    Objective,
    Product,
    Ref,
    Sense,
    Sum,
)
from planteo.canonical import Verdict, compare, digest

TONNE = Dimension.of("t", mass=1)


def test_verdict_vocabulary(blend) -> None:
    """R-008: equal canonical form reports equivalent; anything else is not-proven-equivalent.

    There is deliberately no 'different' verdict, because inequality of canonical form does not
    establish it.
    """
    same = compare(blend, blend)
    assert same.verdict is Verdict.EQUIVALENT
    assert same.equivalent

    changed = dataclasses.replace(
        blend,
        relations=(
            Compare(
                left=Sum((Ref("x_a"), Ref("x_b"))),
                comparator=Comparator.GE,
                right=Constant(250.0, TONNE),
                name="meet_demand",
            ),
        ),
    )
    other = compare(blend, changed)
    assert other.verdict is Verdict.NOT_PROVEN_EQUIVALENT
    assert not other.equivalent
    assert {v.value for v in Verdict} == {"equivalent", "not-proven-equivalent"}


def test_renaming_every_quantity_does_not_change_the_form(blend) -> None:
    renaming = {"x_a": "alpha", "x_b": "beta", "c_a": "p1", "c_b": "p2", "demand": "d"}
    renamed = dataclasses.replace(
        blend,
        quantities=tuple(
            dataclasses.replace(q, name=renaming[q.name]) for q in blend.quantities
        ),
        relations=(
            Compare(
                left=Sum((Ref("alpha"), Ref("beta"))),
                comparator=Comparator.GE,
                right=Ref("d"),
                name="whatever",
            ),
        ),
        objectives=(
            Objective(
                sense=Sense.MINIMISE,
                expression=Sum(
                    (Product((Ref("p1"), Ref("alpha"))), Product((Ref("p2"), Ref("beta"))))
                ),
                name="cost",
            ),
        ),
    )
    assert compare(blend, renamed).equivalent


def test_term_order_does_not_change_the_form(blend) -> None:
    reordered = dataclasses.replace(
        blend,
        relations=(
            Compare(
                left=Sum((Ref("x_b"), Ref("x_a"))),
                comparator=Comparator.GE,
                right=Ref("demand"),
                name="meet_demand",
            ),
        ),
    )
    assert compare(blend, reordered).equivalent


def test_flipping_a_comparator_does_not_change_the_form(blend) -> None:
    flipped = dataclasses.replace(
        blend,
        relations=(
            Compare(
                left=Ref("demand"),
                comparator=Comparator.LE,
                right=Sum((Ref("x_a"), Ref("x_b"))),
                name="meet_demand",
            ),
        ),
    )
    assert compare(blend, flipped).equivalent


def test_provenance_is_not_content(blend) -> None:
    """Two formalizations that recorded different spans are still the same model."""

    stripped = dataclasses.replace(
        blend,
        quantities=tuple(dataclasses.replace(q, span=None, description="") for q in blend.quantities),
    )
    assert compare(blend, stripped).equivalent


def test_a_changed_dimension_changes_the_form(blend) -> None:
    """Units are content, not provenance: the same numbers in different units are a different model."""
    in_kilos = dataclasses.replace(
        blend,
        quantities=tuple(
            dataclasses.replace(q, dimension=Dimension.of("kg", mass=1, length=1))
            if q.name == "x_a"
            else q
            for q in blend.quantities
        ),
    )
    assert not compare(blend, in_kilos).equivalent


def test_digest_is_stable_across_runs(blend) -> None:
    assert digest(blend) == digest(blend)
    assert len(digest(blend)) == 64


def test_nested_sums_flatten(blend) -> None:
    nested = dataclasses.replace(
        blend,
        relations=(
            Compare(
                left=Sum((Sum((Ref("x_a"),)), Ref("x_b"))),
                comparator=Comparator.GE,
                right=Ref("demand"),
                name="meet_demand",
            ),
        ),
    )
    assert compare(blend, nested).equivalent


def test_nested_products_flatten(blend) -> None:
    """R-012: how a product is parenthesised is not content. A cost written c_a * (x_a) inside a
    product of one, or a rate written -(k * m) against -1 * k * m, is the same expression."""
    (objective,) = blend.objectives
    nested_terms = tuple(
        Product((Product((term.factors[0],)), Product(term.factors[1:]))) if isinstance(term, Product) else term
        for term in objective.expression.terms
    )
    nested = dataclasses.replace(
        blend, objectives=(dataclasses.replace(objective, expression=Sum(nested_terms)),)
    )
    assert compare(blend, nested).equivalent

    one = Dimension.dimensionless()
    flat = Product((Constant(-1.0, one), Ref("k"), Ref("m")))
    grouped = Product((Constant(-1.0, one), Product((Ref("k"), Ref("m")))))
    rename = {"k": "q0", "m": "q1"}
    from planteo.canonical import _canonical_expression

    assert _canonical_expression(flat, rename) == _canonical_expression(grouped, rename)
    # A different product is still a different form: flattening folds grouping, not content.
    other = Product((Constant(-2.0, one), Product((Ref("k"), Ref("m")))))
    assert _canonical_expression(flat, rename) != _canonical_expression(other, rename)
